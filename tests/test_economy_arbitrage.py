"""Purchasing and liquidating equipment must not mint exchangeable wealth."""

from copy import deepcopy
import random
import unittest
from unittest.mock import patch

from game.systems.bazaar import BazaarManager
from game.systems.bazaar_service import BazaarService
from game.systems.currency import CurrencyWallet
from game.systems.currency_economy import exchange_currency, gamble_rarity
from game.systems.fusion import FusionManager
from game.systems.inventory import Inventory
from game.systems.items import spawnable_items
from game.systems.liquidation import BASIS_KEY, paid_value_gold
from game.systems.numbers import LargeNumber


class EconomyArbitrageTests(unittest.TestCase):
    def setUp(self):
        self.manager = BazaarManager(spawnable_items(), seed=7,
                                     rng=random.Random(7))
        self.service = BazaarService(self.manager)
        self.wallet = CurrencyWallet()
        self.inventory = Inventory()

    def test_repeated_copper_crates_sale_exchange_is_a_loss(self):
        # Old behavior:35 Copper bought an item guaranteed to sell for9+ Gold;
        # 9 Gold exchanged to202 Copper, so every loop generated free money.
        self.wallet.add('Copper', LargeNumber(350))
        initial = paid_value_gold(self.wallet.amounts)
        for index in range(10):
            item = self.service.buy_crate(
                'starter-crate', wallet=self.wallet, inventory=self.inventory,
                item_id=f'cycle-{index}', luck=1)
            value = self.service.sell_item(
                item['id'], wallet=self.wallet, inventory=self.inventory,
                trader_bonus=1e300)
            self.assertGreater(value, 0)
        gold = int(self.wallet.get('Gold').value)
        exchange_currency(self.wallet, 'Gold', 'Copper', gold)
        self.assertLess(paid_value_gold(self.wallet.amounts), initial)
        self.assertLess(self.wallet.get('Copper'), 350)

    def test_each_crate_sale_is_below_its_multi_currency_cost(self):
        for index, crate in enumerate(self.manager.crate_catalog):
            with self.subTest(crate=crate.id):
                self.manager.crates = [crate]
                for currency, cost in crate.costs.items():
                    self.wallet.add(currency, LargeNumber(cost))
                item = self.service.buy_crate(
                    crate.id, wallet=self.wallet, inventory=self.inventory,
                    item_id=f'crate-{index}', luck=100)
                quote = self.manager.sell_value(item, trader_bonus=1e300)
                self.assertLess(quote, paid_value_gold(crate.costs))
                self.service.sell_item(item['id'], wallet=self.wallet,
                                       inventory=self.inventory)

    def test_paid_level_investment_returns_a_bounded_partial_refund(self):
        self.wallet.add('Copper', LargeNumber(35))
        self.wallet.add('Gold', LargeNumber(6))
        item = self.service.buy_crate(
            'starter-crate', wallet=self.wallet, inventory=self.inventory,
            item_id='level-me', luck=1)
        before = self.manager.sell_value(item)
        self.service.upgrade_level(item['id'], wallet=self.wallet,
                                   inventory=self.inventory)
        after = self.manager.sell_value(item)
        self.assertGreater(after, before)
        self.assertLess(after - before, 6)
        self.assertEqual(LargeNumber(item[BASIS_KEY]), LargeNumber('7.4'))

    def test_currency_alias_pool_cannot_spend_the_same_balance_twice(self):
        item = deepcopy(spawnable_items()[0])
        item['rarity'] = 'common'
        original = deepcopy(item)
        self.wallet.add('Copper', LargeNumber(10))
        with self.assertRaisesRegex(ValueError, 'Not enough'):
            gamble_rarity(item, 'uncommon', {'Copper': 10, 'copper': 10},
                          self.wallet, random.Random(7))
        self.assertEqual(self.wallet.get('Copper'), 10)
        self.assertEqual(item, original)

    def test_free_and_legacy_item_quotes_remain_useful(self):
        item = {'rarity': 'common', 'level': 1}
        self.assertEqual(self.manager.sell_value(item), 9)
        self.assertEqual(self.manager.sell_value(item, trader_bonus=1e300),
                         LargeNumber('13.5'))

    def test_fusion_cannot_launder_the_purchase_budget(self):
        sources = []
        self.wallet.add('Copper', LargeNumber(70))
        for index, kind in enumerate(('weapon', 'armor')):
            template = next(item for item in self.manager.catalog
                            if item['type'] == kind and item['rarity'] == 'common')
            with patch.object(self.manager, 'roll_crate',
                              return_value=deepcopy(template)):
                sources.append(self.service.buy_crate(
                    'starter-crate', wallet=self.wallet, inventory=self.inventory,
                    item_id=f'ingredient-{index}', luck=1))
        result = FusionManager().build_fusion(sources, 'field-rifle')
        self.assertEqual(LargeNumber(result[BASIS_KEY]), LargeNumber('2.8'))
        self.inventory.items.clear()
        self.inventory.add(result)
        value = self.service.sell_item(result['id'], wallet=self.wallet,
                                       inventory=self.inventory, trader_bonus=100)
        self.assertGreater(value, 0)
        self.assertLess(value, paid_value_gold({'Copper': 70}))

    def test_nonfinite_bonus_is_rejected_before_inventory_changes(self):
        item = deepcopy(self.manager.catalog[0])
        self.inventory.add(item)
        for bonus in (float('nan'), float('inf')):
            with self.subTest(bonus=bonus), self.assertRaises(ValueError):
                self.service.sell_item(item['id'], wallet=self.wallet,
                                       inventory=self.inventory, trader_bonus=bonus)
            self.assertEqual(self.wallet.get('Gold'), 0)
            self.assertIn(item, self.inventory.items)


if __name__ == '__main__':
    unittest.main()
