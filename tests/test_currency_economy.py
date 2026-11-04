import random
import unittest

from game.systems.currency import CurrencyWallet
from game.systems.currency_economy import currency_affinity, rarity_chance, gamble_rarity, exchange_currency, exchange_quote
from game.systems.numbers import LargeNumber


class CurrencyEconomyTests(unittest.TestCase):
    def setUp(self):
        self.item = {'id': 'a', 'type': 'weapon',
                     'rarity': 'common', 'combinations': []}
        self.wallet = CurrencyWallet()
        self.wallet.add('Copper', LargeNumber(1000))

    def test_affinity_and_stacked_difficulty(self):
        self.assertGreater(currency_affinity(self.item, 'Iron Coin'), 1)
        self.assertLess(currency_affinity(self.item, 'Mana Crystal'), 1)
        self.assertGreater(rarity_chance(self.item, 'uncommon', {
                           'Copper': 50}), rarity_chance(self.item, 'legendary', {'Copper': 50}))
        self.assertGreater(rarity_chance(self.item, 'uncommon', {
                           'Copper': 100}), rarity_chance(self.item, 'uncommon', {'Copper': 50}))

    def test_gamble_spends_on_failure_and_increases_slots_on_success(self):
        class Roll:
            def __init__(self, n): self.n = n
            def random(self): return self.n
        self.assertFalse(gamble_rarity(self.item, 'rare', {
                         'Copper': 10}, self.wallet, Roll(0.99)))
        self.assertEqual(self.wallet.get('Copper'), 990)
        self.assertTrue(gamble_rarity(self.item, 'rare', {
                        'Copper': 10}, self.wallet, Roll(0)))
        self.assertEqual(self.item['rarity'], 'rare')
        self.assertGreater(len(self.item['combinations']), 0)

    def test_invalid_pool_does_not_spend(self):
        with self.assertRaises(ValueError):
            gamble_rarity(self.item, 'rare', {
                          'Copper': 1001}, self.wallet, random.Random(1))
        self.assertEqual(self.wallet.get('Copper'), 1000)

    def test_midpoint_gamble_chooses_either_adjacent_tier_after_success(self):
        class Rolls:
            def __init__(self, outcome): self.values = iter([0, outcome])
            def random(self): return next(self.values)
        for roll, expected in ((0.49, 'uncommon'), (0.5, 'rare')):
            item = dict(self.item, combinations=[])
            self.assertTrue(gamble_rarity(item, 'uncommon~rare', {
                            'Copper': 1}, self.wallet, Rolls(roll)))
            self.assertEqual(item['rarity'], expected)
        with self.assertRaises(ValueError):
            rarity_chance(self.item, 'uncommon~legendary', {'Copper': 1})

    def test_exchange_fee_and_atomicity(self):
        self.assertEqual(exchange_quote('Copper', 'Silver', 100), 16)
        self.assertEqual(exchange_currency(
            self.wallet, 'Copper', 'Silver', 100), 16)
        self.assertEqual(self.wallet.get('Copper'), 900)
        self.assertEqual(self.wallet.get('Silver'), 16)
        with self.assertRaises(ValueError):
            exchange_currency(self.wallet, 'Copper', 'Gold', 1)
        self.assertEqual(self.wallet.get('Copper'), 900)

    def test_fractional_target_uses_requested_distribution(self):
        class Rolls:
            def __init__(self, result): self.values = iter([0, result])
            def random(self): return next(self.values)
        pool = {'Copper': 10}
        low = rarity_chance(self.item, 'uncommon', pool)
        high = rarity_chance(self.item, 'rare', pool)
        self.assertAlmostEqual(rarity_chance(
            self.item, 'uncommon~rare~30', pool), .7 * low + .3 * high)
        for roll, expected in ((.69, 'uncommon'), (.70, 'rare')):
            item = dict(self.item, combinations=[])
            self.assertTrue(gamble_rarity(
                item, 'uncommon~rare~30', pool, self.wallet, Rolls(roll)))
            self.assertEqual(item['rarity'], expected)

    def test_high_rarity_timing_and_mythical_requirement_do_not_charge(self):
        with self.assertRaisesRegex(ValueError, '15 minutes'):
            gamble_rarity(self.item, 'epic', {'Copper': 10}, self.wallet, random.Random(
                1), elapsed_seconds=899, luck=100)
        with self.assertRaisesRegex(ValueError, 'mythical'):
            gamble_rarity(self.item, 'ultimate', {'Copper': 10}, self.wallet, random.Random(
                1), elapsed_seconds=3600, luck=100)
        mythic = {**self.item, 'rarity': 'mythical'}
        with self.assertRaisesRegex(ValueError, '30 minutes'):
            gamble_rarity(mythic, 'ultimate', {'Copper': 10}, self.wallet, random.Random(
                1), elapsed_seconds=1799, luck=100)
        self.assertEqual(self.wallet.get('Copper'), 1000)


if __name__ == '__main__':
    unittest.main()
