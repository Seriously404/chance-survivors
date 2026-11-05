"""Owned relic bonuses remain global exactly once after assignment."""

import unittest

from game.entities.player import Player
from game.systems.bullets import load_bullet_types
from game.systems.combinations import CombinationEngine
from game.systems.inventory import Inventory, _item
from game.systems.items import create_item_catalog, item_stat, player_bonuses
from game.systems.weapons import projectile_for_weapon


class RelicPassiveScopeTests(unittest.TestCase):
    def catalog(self, *ids):
        return Inventory([item for item in create_item_catalog()
                          if item['id'] in ids])

    def test_active_ability_does_not_regrant_owned_relic_passives(self):
        for rarity in ('common', 'legendary', 'ultimate'):
            with self.subTest(rarity=rarity):
                inventory = self.catalog('nature-seed', 'lucky-box')
                ability = inventory.get('nature-seed')
                ability['rarity'] = rarity
                inventory.get('lucky-box')['level'] = 5
                inventory.equip('nature-seed', 'abilities', 0)
                before = player_bonuses(inventory)
                inventory.assign_combination('nature-seed', 0, 'lucky-box')
                self.assertEqual(player_bonuses(inventory), before)

    def test_weapon_relic_keeps_global_luck_and_crit_without_local_duplicate(self):
        inventory = self.catalog('starter-rapid', 'lucky-box')
        inventory.equip('starter-rapid', 'weapons', 0)
        before = player_bonuses(inventory)
        inventory.assign_combination('starter-rapid', 0, 'lucky-box')
        after = player_bonuses(inventory)
        self.assertEqual(after, before)
        self.assertEqual(after['luck'], 1 + item_stat(
            inventory.get('lucky-box'), 'luck'))
        self.assertEqual(after['crit_chance'], item_stat(
            inventory.get('lucky-box'), 'crit_chance'))
        combined = CombinationEngine().evaluate_inventory(
            inventory, 'starter-rapid')
        snapshot = combined.to_dict()
        projectile, _, _ = projectile_for_weapon(
            Player(), 0, combined, 0, load_bullet_types(), 1,
            critical_chance_bonus=after['crit_chance'],
        )
        self.assertEqual(projectile.critical_chance, after['crit_chance'])
        self.assertEqual(combined.to_dict(), snapshot)

    def test_nonpassive_relic_effects_and_weapon_crit_remain_combined(self):
        gun = _item('gun', 'Gun', 'weapon', 'common', 1,
                    {'damage': 10, 'crit_chance': 3})
        relic = _item('relic', 'Relic', 'relic', 'common', 1,
                      {'area_radius': 1, 'crit_chance': 4, 'luck': 2})
        inventory = Inventory([gun, relic])
        inventory.assign_combination('gun', 0, 'relic')
        bonuses = player_bonuses(inventory)
        shot, _, _ = projectile_for_weapon(
            Player(), 0, CombinationEngine().evaluate_inventory(inventory, 'gun'),
            0, load_bullet_types(), 1,
            critical_chance_bonus=bonuses['crit_chance'],
        )
        self.assertEqual(shot.explosion_radius, .35)
        self.assertEqual(shot.critical_chance, 7)
        self.assertEqual(bonuses['luck'], 3)

    def test_nonrelic_ability_supplement_passive_still_transfers(self):
        inventory = self.catalog('nature-seed', 'glass-cascade')
        inventory.equip('nature-seed', 'abilities', 0)
        before = player_bonuses(inventory)['luck']
        inventory.assign_combination('nature-seed', 0, 'glass-cascade')
        self.assertGreater(player_bonuses(inventory)['luck'], before)


if __name__ == '__main__':
    unittest.main()
