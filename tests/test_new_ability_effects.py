"""Exercise the new early-game abilities and their crate availability."""
import unittest

from game.config.settings import enemy_types
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.abilities import cast_ability
from game.ability_scripts.effects import update_summons
from game.systems.bazaar import BazaarManager, build_extended_catalog


class NewAbilityEffectsTests(unittest.TestCase):
    def setUp(self):
        self.manager = BazaarManager(build_extended_catalog(), seed=1)
        self.items = {item['id']: item for item in self.manager.catalog}

    def cast(self, name, player, enemies=None):
        return cast_ability(self.items[name], player, enemies or [], angle=0,
                            base_speed=1, enemy_types=enemy_types)

    def test_projectiles_have_distinct_effects(self):
        player = Player()
        self.assertGreater(
            self.cast('cinder-burst', player).projectile.explosion_radius, 0)
        self.assertGreaterEqual(
            self.cast('frost-needle', player).projectile.piercing, 1)
        self.assertEqual(self.cast('arcane-ricochet',
                         player).projectile.bounces_remaining, 1)

    def test_summon_shots_inherit_healing_and_damage_bonus(self):
        item = {'type': 'ability', 'heal_on_damage': True, 'stats': {
            'script': 'sentinel', 'summon_damage': 10,
            'summon_duration': 5, 'area_radius': .4,
            'homing_strength': 2, 'cast_piercing': 1, 'bounce_count': 1}}
        player = Player()
        enemy = Enemy('basic', x=1, y=0, health=100, max_health=100)
        outcome = cast_ability(item, player, [enemy], angle=0, base_speed=1,
                               enemy_types=enemy_types, damage_bonus_pct=50)
        shots = update_summons([outcome.summon], [enemy], player, .1, 1)
        self.assertEqual(shots[0].damage, 15)
        self.assertTrue(shots[0].heal_on_damage)
        self.assertEqual(shots[0].explosion_radius, .4)
        self.assertEqual(shots[0].homing_strength, 2)
        self.assertEqual(shots[0].piercing, 1)
        self.assertEqual(shots[0].bounces_remaining, 1)

    def test_ward_heals_and_shields_even_at_full_health(self):
        player = Player(health=90, max_health=100)
        outcome = self.cast('menders-ward', player)
        self.assertGreater(outcome.healed, 0)
        self.assertGreater(player.shield, 0)
        self.assertGreater(player.shield_remaining, 0)
        player.health = player.max_health
        player.shield = 0
        self.assertTrue(self.cast('menders-ward', player).consumed)
        self.assertGreater(player.shield, 0)

    def test_siphon_heals_only_when_enemy_is_in_range(self):
        player = Player(health=50, max_health=100)
        enemy = Enemy.create_from_type('basic', enemy_types['basic'], 0.2, 0)
        self.cast('shadow-siphon', player, [enemy])
        self.assertGreater(player.health, 50)
        health = player.health
        enemy = Enemy.create_from_type('basic', enemy_types['basic'], 4, 0)
        self.cast('shadow-siphon', player, [enemy])
        self.assertEqual(player.health, health)

    def test_area_supplement_expands_nova_hit_radius(self):
        from game.systems.inventory import Inventory, _item
        from game.systems.items import effective_ability
        nova = _item('nova', 'Nova', 'ability', 'common', 1, {
            'script': 'nova', 'cast_damage': 5, 'cast_radius': .2})
        burst = _item('burst', 'Burst', 'ability', 'common', 1, {
            'script': 'projectile', 'area_radius': .8})
        inventory = Inventory([nova, burst])
        inventory.assign_combination('nova', 0, 'burst')
        enemy = Enemy('test', x=.25, health=100, max_health=100)
        cast_ability(effective_ability(inventory, inventory.get('nova')),
                     Player(), [enemy], angle=0, base_speed=1,
                     enemy_types={'test': {'resistances': {}}})
        self.assertLess(enemy.health, 100)

    def test_new_abilities_appear_in_their_element_crates(self):
        for crate_id, item_id in [('ember-crate', 'cinder-burst'),
                                  ('arcane-crate', 'arcane-ricochet'),
                                  ('light-crate', 'healing-spark'),
                                  ('nature-crate', 'menders-ward'),
                                  ('shadow-crate', 'shadow-siphon')]:
            crate = next(
                c for c in self.manager.crate_catalog if c.id == crate_id)
            self.assertIn(item_id, [item['id']
                          for item in self.manager.crate_rewards(crate)])
        starter = next(
            c for c in self.manager.crate_catalog if c.id == 'starter-crate')
        self.assertIn('frost-needle', [item['id']
                      for item in self.manager.crate_rewards(starter)])


if __name__ == '__main__':
    unittest.main()
