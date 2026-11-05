"""Numeric supplements grow with investment while unique tags work early."""

import unittest

from game.systems.combinations import CombinationEngine
from game.systems.inventory import _item
from game.systems.items import item_stat
from game.utils.large_number import LargeNumber


class SupplementProgressionTests(unittest.TestCase):
    def test_new_supplement_transfers_35_percent_of_its_standalone_damage(self):
        base = _item('base', 'Base', 'ability', 'common', 1,
                     {'cast_damage': 10})
        supplement = _item('supplement', 'Supplement', 'ability', 'common', 1,
                           {'cast_damage': 20})
        combined = CombinationEngine().evaluate(base, [supplement])
        contribution = combined.stats['cast_damage'] - 10
        self.assertEqual(contribution, 7)
        self.assertLess(contribution, item_stat(supplement, 'cast_damage'))

    def test_transfer_increases_five_points_per_level_and_caps_at_full(self):
        base = _item('base', 'Base', 'ability', 'common', 1,
                     {'cast_damage': 10})
        previous = LargeNumber(0)
        for level, transfer in ((1, '.35'), (3, '.45'), (14, '1'), (30, '1')):
            with self.subTest(level=level):
                supplement = _item('chip', 'Chip', 'ability', 'common', level,
                                   {'cast_damage': 20})
                combined = CombinationEngine().evaluate(base, [supplement])
                contribution = combined.stats['cast_damage'] - 10
                standalone = LargeNumber(item_stat(supplement, 'cast_damage'))
                self.assertEqual(contribution, standalone * LargeNumber(transfer))
                self.assertLessEqual(contribution, standalone)
                self.assertGreater(contribution, previous)
                previous = contribution

    def test_unique_guidance_tag_operates_even_on_a_level_one_supplement(self):
        base = _item('base', 'Base', 'weapon', 'common', 1, {'damage': 10})
        lens = _item('lens', 'Lens', 'relic', 'common', 1, {})
        lens['tags'] = ['homing']
        combined = CombinationEngine().evaluate(base, [lens])
        self.assertIn('homing_guidance', combined.behaviors)
        self.assertGreater(combined.stats['homing_strength'], 0)
