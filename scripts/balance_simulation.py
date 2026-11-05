"""Reproducible automated balance probes; not a substitute for player testing.

Run: python -m scripts.balance_simulation --seconds 900 --seed 7
Policies aim perfectly at the nearest enemy; they cannot plan or dodge shots.
This exercises real systems, not the main loop. It does not model menu time,
manual dash, quests, fusions, selling or strategic loadout replacement. Reported
damage is resolved damage, including overkill; taken damage is actual HP lost.
The module-level random state is restored, so probes do not affect later runs.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import random
import time

from game.ability_scripts.effects import update_summons
from game.config.settings import (
    PIXELS_PER_UNIT, SCREEN_WIDTH, bullet_base_speed, enemy_spawn_delay,
    enemy_types as base_enemy_types, player_max_health,
)
from game.entities.player import Player
from game.systems.abilities import ability_cooldown, cast_ability
from game.systems.bazaar import BazaarManager
from game.systems.bazaar_service import BazaarService
from game.systems.bullets import load_bullet_types
from game.systems.collision import CollisionSystem
from game.systems.currency import CurrencyWallet
from game.systems.enemy_abilities import update_enemy_abilities
from game.systems.enemy_catalog import build_enemy_roster
from game.systems.enemy_ranged import update_ranged_attacks
from game.systems.enemy_scaling import EnemyScaling
from game.systems.elemental_core import armor_core_resistance, core_for_item, tick_lingering
from game.systems.inventory import ARMOR_EQUIPMENT_SLOTS
from game.systems.items import create_initial_inventory, effective_ability, item_stat, player_bonuses, spawnable_items
from game.systems.numbers import LargeNumber
from game.systems.progression import PlayerProgress, award_enemy_kill
from game.systems.score_milestone import score_for_kill
from game.systems.spawner import EncounterDirector, SpawnerSystem
from game.systems.trails import TrailSystem
from game.systems.weapons import projectiles_for_weapon
from game.utils.large_number import LargeNumber as CombatNumber


def source_fingerprint():
    """Hash game logic/assets and this policy harness for replay attribution."""
    root = Path(__file__).resolve().parents[1]
    files = sorted([*root.joinpath('game').rglob('*.py'),
                    *root.joinpath('assets').rglob('*.json'), Path(__file__).resolve()])
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def simulate(policy: str, *, seconds: float = 900, seed: int = 7,
             dt: float = 1 / 30, loadout: str = 'starter') -> dict:
    """Run one policy until death or the requested active duration.

    ``idle`` does nothing; ``stationary`` fires a rifle and fireball while
    standing still; ``kite``
    moves away from the nearest threat; ``shopper`` kites and buys Cheapskate
    Boxes, equipping compatible gear in vacant slots. All use perfect aiming.
    """
    if policy not in {'idle', 'stationary',
                      'kite', 'shopper', 'managed-shopper'}:
        raise ValueError('Unknown policy')
    if loadout not in {'starter', 'summoner', 'upgraded'}:
        raise ValueError('Unknown fixture loadout')
    if (not math.isfinite(seconds) or seconds <= 0
            or not math.isfinite(dt) or not 0 < dt <= .1):
        raise ValueError(
            'Duration must be positive and step must be in (0, 0.1]')
    previous_random_state = random.getstate()
    random.seed(seed)
    try:
        fingerprint = source_fingerprint()
        result = _simulate(policy, seconds, seed, dt, loadout)
        result['source_fingerprint_start'] = fingerprint
        result['source_fingerprint_end'] = source_fingerprint()
        result['source_changed_during_trial'] = fingerprint != result['source_fingerprint_end']
        return result
    finally:
        random.setstate(previous_random_state)


def _simulate(policy, seconds, seed, dt, loadout):
    started = time.perf_counter()
    rng = random.Random(seed)
    roster = build_enemy_roster(base_enemy_types)
    player = Player(health=player_max_health, max_health=player_max_health)
    inventory = create_initial_inventory()
    if loadout == 'summoner':
        ally = deepcopy(next(item for item in spawnable_items()
                             if item['id'] == 'sentinel-summon'))
        inventory.add(ally)
        inventory.equip(ally['id'], 'abilities', 1)
    elif loadout == 'upgraded':
        for item in inventory.items:
            item['level'] = 10
            item['rarity'] = 'legendary'
    wallet = CurrencyWallet()
    progress = PlayerProgress()
    spawner, director, scaling = SpawnerSystem(
        roster, enemy_spawn_delay), EncounterDirector(), EnemyScaling()
    collision = CollisionSystem(PIXELS_PER_UNIT)
    bazaar = BazaarManager(spawnable_items(), rng=rng, seed=seed)
    shop = BazaarService(bazaar)
    definitions = load_bullet_types()
    bullets, enemies, hostile, summons = [], [], [], []
    trails = TrailSystem()
    cooldowns = [0.0] * 10
    weapon_cooldown = elapsed = 0.0
    score = LargeNumber(0)
    kills = spawns = purchases = 0
    drops, checkpoints = [], []
    transactions = []
    next_upgrade_decision = 5.0
    milestones = {}
    damage_dealt = damage_taken = CombatNumber(0)
    peak_enemies = peak_nearby = 0
    count_seconds = 0.0
    cause_of_death = None
    next_checkpoint = 60.0
    applied_health_bonus = 0
    despawn_distance = (SCREEN_WIDTH / 2 / PIXELS_PER_UNIT) * 1.5

    while elapsed < seconds and player.is_alive():
        step = min(dt, seconds - elapsed)
        elapsed += step
        pending_kills = []
        damage_sources = list(enemies)
        bonuses = player_bonuses(inventory)
        health_bonus = int(bonuses['health'])
        if health_bonus != applied_health_bonus:
            player.max_health = CombatNumber(player_max_health + health_bonus)
            player.health = max(CombatNumber(0), min(player.max_health,
                                                     player.health + health_bonus - applied_health_bonus))
            applied_health_bonus = health_bonus
        weapon_cooldown = max(0.0, weapon_cooldown - step)
        cooldowns = [max(0.0, value - step) for value in cooldowns]
        target = min(enemies, key=lambda e: math.hypot(
            e.x - player.x, e.y - player.y), default=None)
        if target is not None and policy != 'idle':
            angle = math.atan2(target.y - player.y, target.x - player.x)
            if weapon_cooldown <= 0:
                weapon = inventory.get(inventory.active_slots['weapons'][0])
                volley, weapon_cooldown, _ = projectiles_for_weapon(
                    player, angle, weapon, 0, definitions, bullet_base_speed,
                    bonuses['damage_pct'], elemental_bonus_pct=bonuses['elemental_dmg'],
                    healing_bonus_pct=bonuses['healing_pct'],
                    critical_chance_bonus=bonuses['crit_chance'])
                bullets.extend(volley)
            for index, item_id in enumerate(
                    inventory.active_slots['abilities']):
                if not item_id or cooldowns[index] > 0:
                    continue
                item = effective_ability(inventory, inventory.get(item_id))
                # This policy does not emulate manual dash targeting.
                if item.get('stats', {}).get('script') in {
                        'dash', 'sandevistan'}:
                    continue
                outcome = cast_ability(item, player, enemies, angle=angle,
                                       base_speed=bullet_base_speed,
                                       enemy_types=roster,
                                       damage_bonus_pct=bonuses['damage_pct'],
                                       elemental_bonus_pct=bonuses['elemental_dmg'],
                                       healing_bonus_pct=bonuses['healing_pct'],
                                       critical_chance=bonuses['crit_chance'],
                                       core=core_for_item(inventory, inventory.get(item_id)))
                if outcome.consumed:
                    cooldowns[index] = ability_cooldown(item)
                    if outcome.projectile:
                        bullets.append(outcome.projectile)
                    if outcome.summon:
                        summons.append(outcome.summon)
                    if outcome.trail_segment:
                        trails.emit_segment(*outcome.trail_segment)
                    pending_kills.extend(outcome.killed_enemies)
        # Spawns and their movement use the same encounter director as
        # gameplay.
        health_fraction = (player.health / player.max_health).to_float()
        spawner.spawn_delay_ms = director.delay_ms(
            scaling.spawn_delay_ms(enemy_spawn_delay, elapsed), len(enemies), health_fraction)
        spawner.update(step)
        if spawner.should_spawn() and director.can_spawn(len(enemies)):
            before = len(enemies)
            spawner.spawn(player.x, player.y, enemies, elapsed_seconds=elapsed,
                          scaling=scaling, max_enemies=director.MAX_ENEMIES)
            spawns += len(enemies) - before
            spawner.reset()
        elif not director.can_spawn(len(enemies)):
            spawner.reset()
        update_enemy_abilities(enemies, roster, step, player.x, player.y,
                               max_enemies=director.MAX_ENEMIES)
        if policy in {'kite', 'shopper',
                      'managed-shopper'} and target is not None:
            player.move(player.x - target.x, player.y - target.y, step,
                        1 + bonuses['speed_pct'] / 100)
        player.update_shield(step)
        bullets.extend(update_summons(summons, enemies,
                       player, step, bullet_base_speed))
        for ally in summons:
            trails.emit(ally, step)
        bullets = [b for b in bullets if not b.should_despawn(
            player.x, player.y, despawn_distance)]
        for bullet in bullets:
            if bullet.homing_strength > 0:
                bullet.steer_towards(enemies, step)
            bullet.move(step)
            trails.emit(bullet, step)
        for enemy in enemies:
            enemy.move_towards_player(
                player.x, player.y, enemy.speed * .5, enemy.turning_speed, step)
        hostile.extend(update_ranged_attacks(
            enemies, roster, step, player.x, player.y))
        hostile = [p for p in hostile if not p.should_despawn(
            player.x, player.y, despawn_distance)]
        for projectile in hostile:
            projectile.move(step)
        health_before = player.health
        hostile, _ = collision.check_enemy_projectile_player_collisions(
            hostile, player, bonuses['defense'])
        damage_taken += max(CombatNumber(0), health_before - player.health)
        if not player.is_alive():
            cause_of_death = 'enemy projectile'
        pending_kills.extend(tick_lingering(enemies, step, roster))
        pending_kills.extend(trails.update(enemies, roster, step))
        bullets, enemies = collision.check_bullet_enemy_collisions(
            bullets, enemies, roster, player)
        seen = set()
        for enemy in [*pending_kills, *collision.killed_enemies]:
            if id(enemy) in seen:
                continue
            seen.add(id(enemy))
            if not enemy.reward_eligible:
                continue
            score += score_for_kill(kills, enemy.score_multiplier)
            kills += 1
            if enemy.currency_drop and enemy.currency_amount > 0:
                currency, _ = wallet.reward_for_enemy(enemy.currency_drop, enemy.currency_amount,
                                                      rng=rng, luck=bonuses['luck'], multiplier=enemy.score_multiplier)
            else:
                currency, _ = wallet.reward_for_kill(rng=rng, luck=bonuses['luck'],
                                                     multiplier=enemy.score_multiplier)
            if currency != 'Gold':
                wallet.gold_bonus_for_kill(rng=rng, luck=bonuses['luck'])
            award_enemy_kill(progress, enemy.xp_reward,
                             multiplier=enemy.score_multiplier)
        seen.clear()
        for enemy in [*damage_sources, *enemies, *
                      pending_kills, *collision.killed_enemies]:
            if id(enemy) not in seen:
                damage_dealt += sum(enemy.damage_events.values(),
                                    CombatNumber(0))
                enemy.damage_events.clear()
                seen.add(id(enemy))
        health_before = player.health
        collision.check_enemy_player_collisions(
            enemies, player, roster, bonuses['defense'], armor_core_resistance(inventory))
        damage_taken += max(CombatNumber(0), health_before - player.health)
        if not player.is_alive() and cause_of_death is None:
            cause_of_death = 'enemy contact'
        nearby = sum(math.hypot(e.x - player.x, e.y - player.y)
                     <= .75 for e in enemies)
        peak_enemies = max(peak_enemies, len(enemies))
        peak_nearby = max(peak_nearby, nearby)
        count_seconds += len(enemies) * step
        if progress.level >= 8:
            milestones.setdefault('main_quest_level', round(elapsed, 2))
        if policy in {'shopper', 'managed-shopper'} and player.is_alive():
            bazaar.refresh_crates(elapsed)
            crate = next(
                crate for crate in bazaar.crates if crate.id == 'starter-crate')
            if (len(inventory.items) < inventory.CAPACITY
                    and all(wallet.get(currency) >= cost for currency, cost in crate.costs.items())):
                item = shop.buy_crate(crate.id, wallet=wallet, inventory=inventory,
                                      item_id=f'sim-{purchases}', luck=bonuses['luck'])
                purchases += 1
                drops.append({'time': round(elapsed, 2), 'name': item.get('name'),
                              'rarity': item.get('rarity'), 'type': item.get('type'),
                              'costs': {name: str(cost) for name, cost in crate.costs.items()}})
                if policy == 'managed-shopper':
                    _manage_reward(inventory, item)
                    active_ids = {item_id for slots in inventory.active_slots.values()
                                  for item_id in slots if item_id is not None}
                    for spare in inventory.items[:]:
                        if spare['id'] in active_ids:
                            continue
                        if spare.get('type') == 'relic' and spare is item:
                            continue
                        value = shop.sell_item(
                            spare['id'], wallet=wallet, inventory=inventory,
                            trader_bonus=bonuses['luck'] * .03)
                        transactions.append({'time': round(elapsed, 2), 'action': 'sell',
                                             'id': spare['id'], 'name': spare['name'], 'gold': str(value)})
                else:
                    _equip_empty(inventory, item)
                milestones.setdefault('first_purchase', round(elapsed, 2))
                if item.get('type') == 'armor':
                    milestones.setdefault('first_armor', round(elapsed, 2))
            if policy == 'managed-shopper' and elapsed >= next_upgrade_decision:
                next_upgrade_decision = elapsed + 5.0
                active_ids = {item_id for slots in inventory.active_slots.values()
                              for item_id in slots if item_id is not None}
                candidates = sorted((inventory.get(item_id) for item_id in active_ids),
                                    key=lambda gear: (gear.get('level', 1), gear['id']))
                if candidates:
                    gear = candidates[0]
                    cost = bazaar.level_upgrade_cost(gear)
                    if wallet.get('Gold') >= cost:
                        shop.upgrade_level(
                            gear['id'], wallet=wallet, inventory=inventory)
                        transactions.append({'time': round(elapsed, 2), 'action': 'level',
                                             'id': gear['id'], 'name': gear['name'],
                                             'level': gear['level'], 'gold': cost})
                        milestones.setdefault(
                            'first_level_upgrade', round(
                                elapsed, 2))
        if elapsed + 1e-9 >= next_checkpoint:
            checkpoints.append({'time': round(elapsed, 2), 'health': str(player.health),
                                'kills': kills, 'spawns': spawns, 'level': progress.level,
                                'purchases': purchases, 'score': str(score),
                                'enemy_count': len(enemies), 'nearby_enemies': nearby,
                                'damage_dealt': str(damage_dealt),
                                'damage_taken': str(damage_taken)})
            next_checkpoint += 60
    return {'policy': policy, 'seed': seed, 'requested_seconds': seconds,
            'fixture_loadout': loadout,
            'injected_fixture': loadout != 'starter',
            'elapsed': round(elapsed, 2), 'survived': player.is_alive(),
            'health': str(player.health), 'max_health': str(player.max_health),
            'kills': kills, 'spawns': spawns, 'level': progress.level,
            'score': str(score), 'purchases': purchases, 'drops': drops,
            'transactions': transactions,
            'inventory_count': len(inventory.items),
            'equipped_items': [{'id': item['id'], 'name': item['name'],
                                'level': item['level'], 'rarity': item['rarity']}
                               for item in inventory.items
                               if any(item['id'] in slots for slots in inventory.active_slots.values())],
            'damage_dealt': str(damage_dealt), 'damage_taken': str(damage_taken),
            'cause_of_death': cause_of_death,
            'peak_enemies': peak_enemies, 'peak_nearby_enemies': peak_nearby,
            'mean_enemy_count': round(count_seconds / elapsed, 3),
            'milestones': milestones,
            'loadout': {category: list(ids) for category, ids in inventory.active_slots.items()},
            'wallet': {name: str(amount) for name, amount in wallet.amounts.items() if amount > 0},
            'checkpoints': checkpoints, 'wall_seconds': round(time.perf_counter() - started, 3)}


def _equip_empty(inventory, item):
    kind = item.get('type')
    if kind == 'armor':
        slot = item.get('armor_slot')
        if slot not in ARMOR_EQUIPMENT_SLOTS:
            return
        category, index = 'armor', ARMOR_EQUIPMENT_SLOTS.index(slot)
    elif kind == 'ability':
        category = 'abilities'
        index = next((i for i, value in enumerate(
            inventory.active_slots[category]) if value is None), None)
        if index is None:
            return
    else:
        return
    if inventory.active_slots[category][index] is None:
        try:
            inventory.equip(item['id'], category, index)
        except ValueError:
            pass


def _manage_reward(inventory, item):
    """Make a declared gear choice, without omniscient build search."""
    kind = item.get('type')
    if kind == 'weapon':
        current = inventory.get(inventory.active_slots['weapons'][0])
        if _gear_value(item) > _gear_value(current):
            inventory.equip(item['id'], 'weapons', 0)
    elif kind == 'armor':
        slot = item.get('armor_slot')
        if slot not in ARMOR_EQUIPMENT_SLOTS:
            return
        index = ARMOR_EQUIPMENT_SLOTS.index(slot)
        current_id = inventory.active_slots['armor'][index]
        if current_id is None or _gear_value(
                item) > _gear_value(inventory.get(current_id)):
            inventory.equip(item['id'], 'armor', index)
    elif kind == 'ability':
        script = item.get('stats', {}).get('script')
        if script in {'dash', 'sandevistan', 'teleport'}:
            return
        # Keep four distinct behaviors rather than fill every slot with copies.
        for index, item_id in enumerate(
                inventory.active_slots['abilities'][:4]):
            if item_id is None:
                inventory.equip(item['id'], 'abilities', index)
                return
            current = inventory.get(item_id)
            if current.get('stats', {}).get('script') == script:
                if _gear_value(item) > _gear_value(current):
                    inventory.equip(item['id'], 'abilities', index)
                return


def _gear_value(item):
    """Policy preference only; this deliberately is not a DPS oracle."""
    if item.get('type') == 'armor':
        return sum(item_stat(item, key) * weight for key, weight in (
            ('health', 1), ('defense', 8), ('speed_pct', .5),
            ('damage_pct', 1), ('luck', 8)))
    keys = ('damage',) if item.get('type') == 'weapon' else (
        'cast_damage', 'heal_amount', 'shield', 'summon_damage')
    return sum(item_stat(item, key) for key in keys) / max(
        .05, item_stat(item, 'cooldown', 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=900)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--dt', type=float, default=1 / 30)
    parser.add_argument('--loadout', choices=('starter', 'summoner', 'upgraded'),
                        default='starter', help='Nonstarter fixtures inject free gear, not an economy prediction')
    parser.add_argument('--seeds', type=int, nargs='+',
                        help='Repeat each policy for these seeds')
    parser.add_argument('--policy', choices=('idle',
                        'stationary', 'kite', 'shopper', 'managed-shopper', 'all'), default='all')
    args = parser.parse_args()
    policies = ('idle', 'stationary', 'kite',
                'shopper', 'managed-shopper') if args.policy == 'all' else (args.policy,)
    print(json.dumps([simulate(policy, seconds=args.seconds, seed=seed, dt=args.dt,
                               loadout=args.loadout)
                      for policy in policies for seed in args.seeds or [args.seed]], indent=2))


if __name__ == '__main__':
    main()
