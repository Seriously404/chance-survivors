"""Engineer objective, active building support and catalog combat regressions."""

import unittest

from game.ability_scripts.effects import update_summons
from game.entities.enemy import Enemy
from game.entities.enemy_projectile import EnemyProjectile
from game.entities.player import Player
from game.systems.abilities import cast_ability, ability_cooldown
from game.systems.bullets import load_bullet_types
from game.systems.collision import CollisionSystem
from game.systems.engineering import EngineeringDefense, engineer_starter_items
from game.systems.fusion import FusionManager
from game.systems.items import create_item_catalog
from game.systems.weapons import projectile_for_weapon
from game.utils.large_number import LargeNumber


class EngineeringTests(unittest.TestCase):
    def setUp(self):
        self.items = {i['id']: i for i in create_item_catalog()}
        self.defense = EngineeringDefense()
        self.player = Player()
        self.types = {'basic': {'size': 30, 'resistances': {}}}

    def cast(self, item_id, cursor=None):
        return cast_ability(
            self.items[item_id], self.player, [], angle=0, base_speed=1,
            enemy_types=self.types, engineering=self.defense,
            cursor_position=cursor,
        )

    def test_starter_records_are_safe_fresh_and_all_executable(self):
        records = engineer_starter_items()
        self.assertEqual(len(records), 5)
        self.assertTrue(all(i['rarity'] == 'common' for i in records))
        records[0]['stats']['damage'] = 999
        self.assertEqual(engineer_starter_items()[0]['stats']['damage'], 0)

    def test_relay_is_target_and_wall_intercepts_until_destroyed(self):
        enemy = Enemy('basic', x=3, y=0, damage=50)
        self.assertIs(self.defense.target_for(enemy), self.defense.objective)
        wall = self.cast('engineer-wall', (1.5, 0)).summon
        self.assertIs(self.defense.target_for(enemy), wall)
        enemy.x = wall.x
        before = self.defense.objective.health
        self.defense.update([enemy], [], .1)
        self.assertEqual(wall.health, wall.max_health - 50)
        self.assertEqual(self.defense.objective.health, before)
        wall.health = 0
        self.assertIs(self.defense.target_for(enemy), self.defense.objective)

    def test_relay_contact_is_repeated_not_a_suicide_and_pause_is_safe(self):
        enemy = Enemy('basic', damage=10)
        self.defense.update([enemy], [], 0)
        self.assertEqual(self.defense.objective.health, 1200)
        self.defense.update([enemy], [], .1)
        self.defense.update([enemy], [], .1)
        self.assertEqual(self.defense.objective.health, 1190)
        self.defense.update([enemy], [], 1)
        self.assertEqual(self.defense.objective.health, 1180)
        self.assertFalse(enemy.is_dead())
        self.assertEqual(self.player.health, 100)

    def test_wall_intercepts_ranged_shot_before_relay(self):
        wall = self.cast('engineer-wall', (1.5, 0)).summon
        shot = EnemyProjectile(x=0, y=0, dx=-1, dy=0, speed=1, damage=25)
        shot.previous_x, shot.previous_y = 3, 0
        remaining = self.defense.update([], [shot], .1)
        self.assertEqual(remaining, [])
        self.assertEqual(wall.health, wall.max_health - 25)
        self.assertEqual(self.defense.objective.health, 1200)

    def test_repair_gun_restores_building_and_never_damages_enemy(self):
        turret = self.cast('engineer-turret', (1.3, 0)).summon
        turret.health = 1
        gun = self.items['engineer-repair-gun']
        shot, _, _ = projectile_for_weapon(
            self.player, 0, gun, 0, load_bullet_types(), 1,
            healing_bonus_pct=100,
        )
        enemy = Enemy('basic', x=0, y=0, health=100)
        CollisionSystem(200).check_bullet_enemy_collisions(
            [shot], [enemy], self.types)
        self.assertEqual(enemy.health, 100)
        shot.previous_x, shot.previous_y = 1, 0
        shot.x, shot.y = 2, 0
        remaining = self.defense.process_repair_shots([shot])
        self.assertEqual(remaining, [])
        self.assertEqual(turret.health, 1 + turret.max_health * .05)

    def test_deployment_limit_overlap_and_range_do_not_consume_failed_cast(self):
        failed = self.cast('engineer-wall', (0, 0))
        self.assertFalse(failed.consumed)
        distant = self.cast('engineer-wall', (100, 0)).summon
        self.assertAlmostEqual(distant.x, 3.5)
        for x, y in ((-2, 0), (0, 2), (0, -2), (2, 2), (-2, -2)):
            self.assertTrue(self.cast('engineer-wall', (x, y)).consumed)
        self.assertFalse(self.cast('engineer-turret', (2, -2)).consumed)
        self.assertEqual(len(self.defense.structures), 6)

    def test_support_requires_targets_and_repair_is_actual_and_capped(self):
        self.assertFalse(self.cast('engineer-overclock').consumed)
        self.assertFalse(self.cast('engineer-repair-pulse').consumed)
        wall = self.cast('engineer-wall', (1.3, 0)).summon
        self.assertFalse(self.cast('engineer-overclock').consumed)
        wall.health = wall.max_health - 1
        self.assertTrue(self.cast('engineer-repair-pulse').consumed)
        self.assertEqual(wall.health, wall.max_health)
        self.assertFalse(self.cast('engineer-repair-pulse').consumed)

    def test_turret_variants_inherit_actual_bounce_explosion_and_piercing(self):
        for item_id, field, minimum in (
            ('engineer-arc-turret', 'bounces_remaining', 2),
            ('engineer-flame-turret', 'explosion_radius', .4),
            ('engineer-frost-turret', 'piercing', 2),
        ):
            with self.subTest(item=item_id):
                self.defense = EngineeringDefense()
                turret = self.cast(item_id, (1.3, 0)).summon
                enemy = Enemy('basic', x=2, health=1000)
                shots = update_summons([turret], [enemy], self.player, .1, 1)
                self.assertGreaterEqual(getattr(shots[0], field), minimum)
                shots[0].x = enemy.x
                shots[0].previous_x = 1.3
                CollisionSystem(200).check_bullet_enemy_collisions(
                    shots, [enemy], self.types)
                self.assertLess(enemy.health, 1000)

    def test_walls_cannot_fire_and_dead_structures_do_not_continue_attacking(self):
        wall = self.cast('engineer-wall', (1.3, 0)).summon
        enemy = Enemy('basic', x=2)
        self.assertEqual(update_summons([wall], [enemy], self.player, .1, 1), [])
        turret = self.cast('engineer-turret', (-1.3, 0)).summon
        turret.health = 0
        self.assertEqual(update_summons([turret], [enemy], self.player, .1, 1), [])
        self.assertEqual(turret.remaining, 0)

    def test_waves_advance_by_kills_preserving_health_fraction(self):
        self.defense.objective.health = LargeNumber(600)
        self.defense.update([], [], 10000)
        self.assertEqual(self.defense.wave, 1)
        self.defense.register_kills(11)
        self.assertEqual(self.defense.completed_waves, 0)
        self.defense.register_kills(1)
        self.assertEqual(self.defense.completed_waves, 1)
        self.assertEqual(self.defense.wave, 2)
        self.assertEqual(self.defense.objective.health,
                         self.defense.objective.max_health * .5)

    def test_engineering_ultimate_is_real_fusion_with_long_recovery(self):
        manager = FusionManager()
        sources = [self.items['engineer-turret'], self.items['engineer-overclock'],
                   self.items['lucky-box']]
        for item in sources:
            item['rarity'] = 'mythical'
            item['level'] = 12
        sources[-1]['fusion_recipe'] = 'elemental-core'
        ultimate = manager.build_fusion(sources, 'architect-protocol')
        self.assertEqual(ultimate['stats']['script'], 'architect_protocol')
        self.assertTrue(ultimate['fusion_only'])
        self.assertGreaterEqual(ability_cooldown(ultimate), 60)
        turret = self.cast('engineer-turret', (1.3, 0)).summon
        outcome = cast_ability(
            ultimate, self.player, [], angle=0, base_speed=1,
            enemy_types=self.types, engineering=self.defense,
        )
        self.assertTrue(outcome.consumed)
        enemy = Enemy('basic', x=2)
        shots = update_summons([turret], [enemy], self.player, .1, 1)
        self.assertEqual(shots[0].damage, turret.damage * 2)
        self.assertAlmostEqual(turret.attack_timer, turret.attack_interval / 2)

    def test_damaged_defense_roundtrip_preserves_buffs_and_large_damage(self):
        import json
        turret = self.cast('engineer-turret', (1.3, 0)).summon
        turret.damage = LargeNumber('1e1000')
        turret.health = LargeNumber('17.5')
        turret.overclock_remaining = 2
        turret.damage_components = [{'element': 'fire', 'damage': LargeNumber('1e999')}]
        self.defense.objective.health = LargeNumber(811)
        self.defense.register_kills(15)
        snapshot = json.loads(json.dumps(self.defense.to_dict()))
        restored = EngineeringDefense.from_dict(snapshot)
        self.assertEqual(restored.to_dict(), snapshot)
        self.assertEqual(restored.objective.health, self.defense.objective.health)
        self.assertEqual(restored.structures[0].damage, LargeNumber('1e1000'))
        self.assertEqual(restored.structures[0].overclock_remaining, 2)
        self.assertEqual(restored.wave_kills, 3)

    def test_malformed_save_is_rejected_instead_of_reviving_relay(self):
        import copy
        valid = self.defense.to_dict()
        for field, value in (('health', '-1'), ('health', '1201'), ('x', float('nan'))):
            with self.subTest(field=field, value=value):
                invalid = copy.deepcopy(valid)
                invalid['objective'][field] = value
                with self.assertRaises(ValueError):
                    EngineeringDefense.from_dict(invalid)
        self.defense.objective.health = 0
        self.defense.support('repair_pulse', self.player)
        self.assertTrue(self.defense.failed)

    def test_overclock_expires_and_does_not_make_damage_permanently_multiply(self):
        turret = self.cast('engineer-turret', (1.3, 0)).summon
        base_damage = turret.damage
        self.assertTrue(self.cast('engineer-overclock').consumed)
        enemy = Enemy('basic', x=2)
        shots = update_summons([turret], [enemy], self.player, .1, 1)
        self.assertEqual(shots[0].damage, base_damage)
        self.assertAlmostEqual(turret.attack_timer, turret.attack_interval / 2)
        update_summons([turret], [], self.player, 5, 1)
        self.assertEqual(turret.overclock_remaining, 0)
        turret.attack_timer = 0
        shots = update_summons([turret], [enemy], self.player, .1, 1)
        self.assertEqual(shots[0].damage, base_damage)
        self.assertAlmostEqual(turret.attack_timer, turret.attack_interval)

    def test_repair_gun_cannot_deal_damage_through_a_trail_supplement(self):
        from game.systems.combinations import CombinationEngine
        from game.systems.inventory import Inventory
        from game.systems.trails import TrailSystem
        inventory = Inventory([self.items['engineer-repair-gun'],
                               self.items['ember-wand']])
        inventory.assign_combination('engineer-repair-gun', 0, 'ember-wand')
        shot, _, _ = projectile_for_weapon(
            self.player, 0, CombinationEngine().evaluate_inventory(
                inventory, 'engineer-repair-gun'), 0, load_bullet_types(), 1)
        shot.move(.1)
        trails = TrailSystem()
        trails.emit(shot, .1)
        self.assertEqual(trails.trails, [])

    def test_engineer_save_preserves_spent_sentry_healing_budget(self):
        import json
        from game.systems.combat_bonuses import HealingBudget
        turret = self.cast('engineer-turret', (1.3, 0)).summon
        turret.healing_budget = HealingBudget('2.5')
        restored = EngineeringDefense.from_dict(
            json.loads(json.dumps(self.defense.to_dict())))
        self.assertEqual(restored.structures[0].healing_budget.remaining,
                         LargeNumber('2.5'))
