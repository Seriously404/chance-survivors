"""Reproducible automated balance probes; not a substitute for player testing.

Run: python -m scripts.balance_simulation --seconds 900 --seed 7
Policies aim perfectly at the nearest enemy; they cannot plan or dodge shots.
"""
from __future__ import annotations

import argparse
import json
import math
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
from game.systems.inventory import ARMOR_EQUIPMENT_SLOTS
from game.systems.items import create_initial_inventory, player_bonuses, spawnable_items
from game.systems.numbers import LargeNumber
from game.systems.progression import PlayerProgress, award_enemy_kill
from game.systems.score_milestone import score_for_kill
from game.systems.spawner import EncounterDirector, SpawnerSystem
from game.systems.weapons import projectiles_for_weapon
from game.utils.large_number import LargeNumber as CombatNumber


def simulate(policy: str, *, seconds: float = 900, seed: int = 7,
             dt: float = 1 / 30) -> dict:
    """Run one policy until death or the requested active duration.

    ``stationary`` fires a rifle and fireball while standing still; ``kite``
    moves away from the nearest threat; ``shopper`` kites and buys Cheapskate
    Boxes, equipping compatible gear in vacant slots. All use perfect aiming.
    """
    if policy not in {'stationary', 'kite', 'shopper'}:
        raise ValueError('Unknown policy')
    if not math.isfinite(seconds) or seconds <= 0 or not 0 < dt <= .1:
        raise ValueError('Duration must be positive and step must be in (0, 0.1]')
    previous_random_state = random.getstate()
    random.seed(seed)
    try:
        return _simulate(policy, seconds, seed, dt)
    finally:
        random.setstate(previous_random_state)


def _simulate(policy, seconds, seed, dt):
    started = time.perf_counter()
    rng = random.Random(seed)
    roster = build_enemy_roster(base_enemy_types)
    player = Player(health=player_max_health, max_health=player_max_health)
    inventory = create_initial_inventory()
    wallet = CurrencyWallet()
    progress = PlayerProgress()
    spawner, director, scaling = SpawnerSystem(roster, enemy_spawn_delay), EncounterDirector(), EnemyScaling()
    collision = CollisionSystem(PIXELS_PER_UNIT)
    bazaar = BazaarManager(spawnable_items(), rng=rng, seed=seed)
    shop = BazaarService(bazaar)
    definitions = load_bullet_types()
    bullets, enemies, hostile, summons = [], [], [], []
    cooldowns = [0.0] * 10
    weapon_cooldown = elapsed = 0.0
    score = LargeNumber(0)
    kills = spawns = purchases = 0
    drops, checkpoints = [], []
    next_checkpoint = 60.0
    applied_health_bonus = 0
    despawn_distance = (SCREEN_WIDTH / 2 / PIXELS_PER_UNIT) * 1.5

    while elapsed < seconds and player.is_alive():
        step = min(dt, seconds - elapsed)
        elapsed += step
        bonuses = player_bonuses(inventory)
        health_bonus = int(bonuses['health'])
        if health_bonus != applied_health_bonus:
            player.max_health = CombatNumber(player_max_health + health_bonus)
            player.health = max(CombatNumber(0), min(player.max_health,
                player.health + health_bonus - applied_health_bonus))
            applied_health_bonus = health_bonus
        weapon_cooldown = max(0.0, weapon_cooldown - step)
        cooldowns = [max(0.0, value - step) for value in cooldowns]
        target = min(enemies, key=lambda e: math.hypot(e.x-player.x, e.y-player.y), default=None)
        if target is not None:
            angle = math.atan2(target.y-player.y, target.x-player.x)
            if weapon_cooldown <= 0:
                weapon = inventory.get(inventory.active_slots['weapons'][0])
                volley, weapon_cooldown, _ = projectiles_for_weapon(
                    player, angle, weapon, 0, definitions, bullet_base_speed,
                    bonuses['damage_pct'])
                bullets.extend(volley)
            for index, item_id in enumerate(inventory.active_slots['abilities']):
                if not item_id or cooldowns[index] > 0:
                    continue
                item = inventory.get(item_id)
                # This policy does not emulate manual dash targeting.
                if item.get('stats', {}).get('script') in {'dash', 'sandevistan'}:
                    continue
                outcome = cast_ability(item, player, enemies, angle=angle,
                                       base_speed=bullet_base_speed,
                                       enemy_types=roster,
                                       damage_bonus_pct=bonuses['damage_pct'])
                if outcome.consumed:
                    cooldowns[index] = ability_cooldown(item)
                    if outcome.projectile:
                        bullets.append(outcome.projectile)
                    if outcome.summon:
                        summons.append(outcome.summon)
                    # Area ability kills are rewarded below alongside projectile kills.
                    for enemy in outcome.killed_enemies:
                        enemy._sim_ability_kill = True
                    ability_kills = outcome.killed_enemies
                    # A policy can have multiple abilities casting on the same frame.
                    pending_kills.extend(ability_kills)
        # Spawns and their movement use the same encounter director as gameplay.
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
        if policy != 'stationary' and target is not None:
            player.move(player.x-target.x, player.y-target.y, step,
                        1 + bonuses['speed_pct'] / 100)
        player.update_shield(step)
        bullets.extend(update_summons(summons, enemies, player, step, bullet_base_speed))
        bullets = [b for b in bullets if not b.should_despawn(player.x, player.y, despawn_distance)]
        for bullet in bullets:
            if bullet.homing_strength > 0:
                bullet.steer_towards(enemies, step)
            bullet.move(step)
        for enemy in enemies:
            enemy.move_towards_player(player.x, player.y, enemy.speed * .5, enemy.turning_speed, step)
        hostile.extend(update_ranged_attacks(enemies, roster, step, player.x, player.y))
        hostile = [p for p in hostile if not p.should_despawn(player.x, player.y, despawn_distance)]
        for projectile in hostile:
            projectile.move(step)
        hostile, _ = collision.check_enemy_projectile_player_collisions(
            hostile, player, bonuses['defense'])
        bullets, enemies = collision.check_bullet_enemy_collisions(
            bullets, enemies, roster, player)
        for enemy in [*pending_kills, *collision.killed_enemies]:
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
            award_enemy_kill(progress, enemy.xp_reward, multiplier=enemy.score_multiplier)
        pending_kills.clear()
        collision.check_enemy_player_collisions(enemies, player, roster, bonuses['defense'])
        if policy == 'shopper' and player.is_alive():
            bazaar.refresh_crates(elapsed)
            crate = next(crate for crate in bazaar.crates if crate.id == 'starter-crate')
            if all(wallet.get(currency) >= cost for currency, cost in crate.costs.items()):
                item = shop.buy_crate(crate.id, wallet=wallet, inventory=inventory,
                    item_id=f'sim-{purchases}', luck=bonuses['luck'])
                purchases += 1
                drops.append({'time': round(elapsed, 2), 'name': item.get('name'),
                              'rarity': item.get('rarity'), 'type': item.get('type')})
                _equip_empty(inventory, item)
        if elapsed + 1e-9 >= next_checkpoint:
            checkpoints.append({'time': round(elapsed, 2), 'health': str(player.health),
                                'kills': kills, 'spawns': spawns, 'level': progress.level,
                                'purchases': purchases, 'score': str(score)})
            next_checkpoint += 60
    return {'policy': policy, 'seed': seed, 'requested_seconds': seconds,
            'elapsed': round(elapsed, 2), 'survived': player.is_alive(),
            'health': str(player.health), 'max_health': str(player.max_health),
            'kills': kills, 'spawns': spawns, 'level': progress.level,
            'score': str(score), 'purchases': purchases, 'drops': drops,
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
        index = next((i for i, value in enumerate(inventory.active_slots[category]) if value is None), None)
        if index is None:
            return
    else:
        return
    if inventory.active_slots[category][index] is None:
        try:
            inventory.equip(item['id'], category, index)
        except ValueError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=900)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--dt', type=float, default=1/30)
    parser.add_argument('--policy', choices=('stationary', 'kite', 'shopper', 'all'), default='all')
    args = parser.parse_args()
    policies = ('stationary', 'kite', 'shopper') if args.policy == 'all' else (args.policy,)
    print(json.dumps([simulate(policy, seconds=args.seconds, seed=args.seed, dt=args.dt)
                      for policy in policies], indent=2))


if __name__ == '__main__':
    main()
