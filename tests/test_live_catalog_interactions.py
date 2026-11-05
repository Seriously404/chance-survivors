"""Exercise real catalog tags through combinations and resisted combat."""

import unittest

from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.abilities import cast_ability
from game.systems.bullets import load_bullet_types
from game.systems.collision import CollisionSystem
from game.systems.combinations import CombinationEngine
from game.systems.inventory import Inventory
from game.systems.items import create_item_catalog, effective_ability, item_stat
from game.systems.relics import build_relic_catalog, relic_effect_summary
from game.utils.large_number import LargeNumber


class LiveCatalogInteractionTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {item['id']: item for item in create_item_catalog()}
        self.player = Player()
        self.types = {'test': {'size': 30, 'resistances': {'nature': .5}}}

    def test_catalog_elemental_damage_abilities_declare_their_element(self):
        for item in self.catalog.values():
            stats = item['stats']
            element = stats.get('element')
            if (item['type'] == 'ability' and stats.get('cast_damage', 0) > 0
                    and element not in (None, 'physical')):
                with self.subTest(item=item['id']):
                    self.assertIn('elemental', item.get('tags', []))
                    self.assertIn(element, item['tags'])

    def test_nature_seed_supplement_keeps_its_element_when_gun_hits(self):
        inventory = Inventory([
            self.catalog['starter-rapid'], self.catalog['nature-seed'],
        ])
        inventory.assign_combination('starter-rapid', 0, 'nature-seed')
        combined = CombinationEngine().evaluate_inventory(
            inventory, 'starter-rapid')
        from game.systems.weapons import projectile_for_weapon
        projectile, _, _ = projectile_for_weapon(
            self.player, 0, combined, 0, load_bullet_types(), 1)
        enemy = Enemy('test', health=1000, max_health=1000)
        CollisionSystem(200).check_bullet_enemy_collisions(
            [projectile], [enemy], self.types, self.player)
        self.assertEqual(
            enemy.damage_events['nature'],
            LargeNumber(item_stat(self.catalog['nature-seed'], 'cast_damage'))
            * LargeNumber('0.35') * .5,
        )
        self.assertGreater(enemy.damage_events['arcane'], 0)
        self.assertEqual(1000 - enemy.health,
                         sum(enemy.damage_events.values(), LargeNumber(0)))

    def test_nature_seed_base_inherits_rifle_as_arcane_damage(self):
        inventory = Inventory([
            self.catalog['nature-seed'], self.catalog['starter-rapid'],
        ])
        inventory.assign_combination('nature-seed', 0, 'starter-rapid')
        enemy = Enemy('test', health=1000, max_health=1000)
        result = cast_ability(
            effective_ability(inventory, inventory.get('nature-seed')),
            self.player, [enemy], angle=0, base_speed=1,
            enemy_types=self.types,
        )
        CollisionSystem(200).check_bullet_enemy_collisions(
            [result.projectile], [enemy], self.types, self.player)
        self.assertEqual(
            enemy.damage_events['arcane'],
            LargeNumber(item_stat(self.catalog['starter-rapid'], 'damage')) * LargeNumber('0.35'),
        )
        self.assertEqual(
            enemy.damage_events['nature'],
            LargeNumber(int(item_stat(
                self.catalog['nature-seed'], 'cast_damage') * .5)),
        )

    def test_inferno_core_catalog_combination_creates_expiring_fire_damage(self):
        from game.systems.trails import TrailSystem
        from game.systems.weapons import projectile_for_weapon

        inventory = Inventory([
            self.catalog['starter-rapid'], self.catalog['inferno-core'],
        ])
        inventory.assign_combination('starter-rapid', 0, 'inferno-core')
        projectile, _, _ = projectile_for_weapon(
            self.player, 0, CombinationEngine().evaluate_inventory(
                inventory, 'starter-rapid'), 0, load_bullet_types(), 1,
        )
        self.assertEqual(projectile.trail_element, 'fire')
        projectile.move(.1)
        trails = TrailSystem()
        trails.emit(projectile, .1)
        enemy = Enemy('test', x=projectile.x, y=projectile.y,
                      health=100, max_health=100)
        enemy_types = {'test': {'resistances': {'fire': .5}}}
        trails.update([enemy], enemy_types, .5)
        self.assertGreater(enemy.damage_events['fire'], 0)
        self.assertLess(enemy.health, 100)
        # Removing the emitter does not make its existing patches immortal.
        trails.update([enemy], enemy_types, 3)
        self.assertEqual(trails.trails, [])
        final_health = enemy.health
        trails.update([enemy], enemy_types, 3)
        self.assertEqual(enemy.health, final_health)

    def test_flame_blaster_catalog_pellets_have_the_advertised_trail(self):
        from game.systems.weapons import projectiles_for_weapon

        shots, _, _ = projectiles_for_weapon(
            self.player, 0, self.catalog['flame-blaster'], 0,
            load_bullet_types(), 1,
        )
        self.assertEqual(len(shots), 6)
        self.assertTrue(all(shot.trail_element == 'fire' for shot in shots))

    def test_relic_factory_matches_live_definitions_and_is_detached(self):
        relics = build_relic_catalog()
        for relic in relics:
            live = self.catalog[relic['id']]
            self.assertEqual(relic['description'], live['description'])
            self.assertEqual(relic.get('tags', []), live.get('tags', []))
        relics[0]['stats']['luck'] = -999
        self.assertNotEqual(build_relic_catalog()[0]['stats']['luck'], -999)

    def test_relic_summary_uses_actual_scaled_stats(self):
        inventory = Inventory([self.catalog['lucky-box']])
        relic = inventory.get('lucky-box')
        relic['level'] = 5
        relic['rarity'] = 'legendary'
        self.assertEqual(
            relic_effect_summary(inventory)['summary']['luck'],
            item_stat(relic, 'luck'),
        )


if __name__ == '__main__':
    unittest.main()
