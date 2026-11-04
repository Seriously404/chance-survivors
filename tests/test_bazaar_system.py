"""Headless regression tests for the Bazaar economy and content catalog."""

import unittest
import random

from game.systems.bazaar import BazaarManager, build_extended_catalog
from game.systems.bazaar_service import BazaarService
from game.systems.currency import CurrencyWallet
from game.systems.inventory import Inventory
from game.systems.numbers import LargeNumber


class BazaarSystemTests(unittest.TestCase):
    def make_inventory(self) -> Inventory:
        inventory = Inventory([
            {
                "id": "starter-rapid",
                "name": "Starter Weapon",
                "type": "weapon",
                "rarity": "common",
                "level": 1,
                "stats": {},
                "combinations": [None],
            },
            {
                "id": "laser-sniper",
                "name": "Second Weapon",
                "type": "weapon",
                "rarity": "common",
                "level": 1,
                "stats": {},
                "combinations": [None],
            },
            {
                "id": "starter-vest",
                "name": "Armor",
                "type": "armor",
                "rarity": "common",
                "level": 1,
                "stats": {},
                "combinations": [None],
            },
        ])
        inventory.equip("starter-rapid", "weapons", 0)
        return inventory

    def test_catalog_expands_beyond_starter_content(self) -> None:
        catalog = build_extended_catalog()
        self.assertGreater(len(catalog), 10)
        self.assertTrue(any(item["type"] == "weapon" for item in catalog))
        self.assertTrue(any(item["type"] == "armor" for item in catalog))
        self.assertTrue(any(item["type"] == "misc" for item in catalog))

    def test_rarity_and_level_upgrades_are_supported(self) -> None:
        manager = BazaarManager(build_extended_catalog())
        item = {"id": "upgrade-target", "rarity": "common", "level": 1}
        upgraded = manager.upgrade_rarity(item, luck=30.0, currency_cost=12)
        self.assertIn(upgraded["rarity"], {"uncommon", "rare", "epic"})

        levelled = manager.upgrade_level({"level": 3}, currency_cost=5)
        self.assertEqual(levelled["level"], 4)

    def test_crates_offer_valid_items(self) -> None:
        manager = BazaarManager(build_extended_catalog(), rng=random.Random(11))
        crate = manager.crates[0]
        rolled = manager.roll_crate(crate, luck=12.0)
        self.assertIn(rolled["type"], {"weapon", "ability", "armor", "misc"})
        self.assertIn(rolled["rarity"], {"common", "uncommon", "rare", "epic"})

    def test_seeded_crate_rolls_are_reproducible(self) -> None:
        catalog = build_extended_catalog()
        crate_a = BazaarManager(catalog, rng=random.Random(4))
        crate_b = BazaarManager(catalog, rng=random.Random(4))
        results_a = [crate_a.roll_crate(crate_a.crates[0])["id"] for _ in range(5)]
        results_b = [crate_b.roll_crate(crate_b.crates[0])["id"] for _ in range(5)]
        self.assertEqual(results_a, results_b)

    def test_crate_offers_unlock_and_rotate_on_active_run_time(self) -> None:
        manager = BazaarManager(seed=17)
        initial_ids = {crate.id for crate in manager.crates}

        self.assertEqual(len(initial_ids), 3)
        self.assertFalse(manager.can_manual_refresh(599))

        manager.refresh_crates(600)
        self.assertEqual(len(manager.crates), 4)
        self.assertIn("astral-crate", {crate.id for crate in manager.crates})

        manager.refresh_crates(1200)
        self.assertEqual(len(manager.crates), 4)
        self.assertGreater(
            len({crate.id for crate in manager.crate_catalog}),
            len(manager.crates),
        )
        self.assertTrue(manager.can_manual_refresh(1200))
        before_refresh = {crate.id for crate in manager.crates}
        self.assertTrue(manager.manual_refresh_crates(1200))
        after_refresh = {crate.id for crate in manager.crates}
        self.assertNotEqual(before_refresh, after_refresh)
        self.assertFalse(manager.manual_refresh_crates(1200))

    def test_crate_rotation_and_manual_refresh_restore_deterministically(self) -> None:
        first = BazaarManager(seed=21)
        second = BazaarManager(
            seed=21,
            refresh_count=1,
            last_manual_refresh_cycle=4,
        )
        first.refresh_crates(1500)
        first.manual_refresh_crates(1500)
        second.refresh_crates(1500)

        self.assertEqual(
            {crate.id for crate in first.crates},
            {crate.id for crate in second.crates},
        )
        self.assertEqual(first.refresh_count, second.refresh_count)

    def test_market_and_crate_purchases_charge_once_and_add_unique_items(self) -> None:
        manager = BazaarManager(build_extended_catalog(), rng=random.Random(2))
        service = BazaarService(manager)
        inventory = self.make_inventory()
        wallet = CurrencyWallet()
        wallet.add("Gold", LargeNumber(1000))
        initial_balance = wallet.get("Gold")
        catalog_item = manager.catalog[0]
        price = manager.catalog_price(catalog_item)

        bought = service.buy_catalog_item(
            catalog_item["id"],
            wallet=wallet,
            inventory=inventory,
            item_id="market-1",
        )
        self.assertEqual(bought["id"], "market-1")
        self.assertEqual(wallet.get("Gold"), initial_balance - price)
        self.assertEqual(len(inventory.items), 4)

        crate = manager.crates[0]
        reward = service.buy_crate(
            crate.id,
            wallet=wallet,
            inventory=inventory,
            item_id="shop-2",
            luck=1,
        )
        self.assertEqual(reward["id"], "shop-2")
        self.assertEqual(wallet.get("Gold"), initial_balance - price - crate.cost)

    def test_failed_purchase_does_not_spend_or_mutate_inventory(self) -> None:
        manager = BazaarManager(build_extended_catalog(), rng=random.Random(3))
        service = BazaarService(manager)
        inventory = self.make_inventory()
        wallet = CurrencyWallet()
        before_ids = [item["id"] for item in inventory.items]
        with self.assertRaisesRegex(ValueError, "Not enough Gold"):
            service.buy_crate(
                "starter-crate",
                wallet=wallet,
                inventory=inventory,
                item_id="shop-1",
                luck=0,
            )
        self.assertEqual(wallet.get("Gold"), LargeNumber(0))
        self.assertEqual([item["id"] for item in inventory.items], before_ids)

        wallet.add("Gold", LargeNumber(1000))
        while len(inventory.items) < inventory.CAPACITY:
            inventory.add({
                "id": f"filler-{len(inventory.items)}",
                "name": "Filler",
                "type": "misc",
                "rarity": "common",
                "level": 1,
                "stats": {},
                "combinations": [None],
            })
        balance = wallet.get("Gold")
        with self.assertRaisesRegex(ValueError, "Inventory is full"):
            service.buy_crate(
                "starter-crate",
                wallet=wallet,
                inventory=inventory,
                item_id="shop-full",
                luck=0,
            )
        self.assertEqual(wallet.get("Gold"), balance)

    def test_upgrades_and_sale_validate_ownership_and_equip_state(self) -> None:
        manager = BazaarManager(build_extended_catalog(), rng=random.Random(1))
        service = BazaarService(manager)
        inventory = self.make_inventory()
        wallet = CurrencyWallet()
        wallet.add("Gold", LargeNumber(1000))
        item = inventory.get("starter-rapid")
        balance = wallet.get("Gold")

        service.upgrade_level(
            item["id"],
            wallet=wallet,
            inventory=inventory,
        )
        self.assertEqual(item["level"], 2)
        self.assertEqual(wallet.get("Gold"), balance - 6)

        with self.assertRaisesRegex(ValueError, "Unequip"):
            service.sell_item(item["id"], wallet=wallet, inventory=inventory)
        self.assertIn(item, inventory.items)

        inventory.unequip("weapons", 0)
        inventory.assign_combination("starter-rapid", 0, "laser-sniper")
        for item_id in ("starter-rapid", "laser-sniper"):
            with self.assertRaisesRegex(ValueError, "Remove this item from its combination"):
                service.sell_item(item_id, wallet=wallet, inventory=inventory)
        inventory.assign_combination("starter-rapid", 0, None)
        sold_item = inventory.get("laser-sniper")
        value = service.sell_item(
            sold_item["id"],
            wallet=wallet,
            inventory=inventory,
        )
        self.assertNotIn(sold_item, inventory.items)
        self.assertGreater(value, 0)
        with self.assertRaisesRegex(ValueError, "no longer"):
            service.upgrade_level("missing-item", wallet=wallet, inventory=inventory)

    def test_rarity_attempt_charges_once_and_expands_combination_capacity_on_success(self) -> None:
        manager = BazaarManager(build_extended_catalog(), rng=random.Random(0))
        service = BazaarService(manager)
        inventory = self.make_inventory()
        wallet = CurrencyWallet()
        item = inventory.get("starter-rapid")
        cost = manager.rarity_upgrade_cost(item)
        wallet.add("Gold", LargeNumber(cost * 2))

        upgraded = service.upgrade_rarity(
            item["id"],
            wallet=wallet,
            inventory=inventory,
            luck=0,
        )
        self.assertFalse(upgraded)
        self.assertEqual(item["rarity"], "common")
        self.assertEqual(wallet.get("Gold"), LargeNumber(cost))

        upgraded = service.upgrade_rarity(
            item["id"],
            wallet=wallet,
            inventory=inventory,
            luck=5,
        )
        self.assertTrue(upgraded)
        self.assertEqual(item["rarity"], "uncommon")
        self.assertEqual(len(item["combinations"]), 2)
        self.assertEqual(wallet.get("Gold"), LargeNumber(0))

    def test_mythical_upgrade_starts_ultimate_tier_one(self) -> None:
        manager = BazaarManager(rng=random.Random(1))
        item = {"id": "mythic-item", "rarity": "mythical", "level": 1, "combinations": [None] * 4}

        manager.upgrade_rarity(item, luck=5, currency_cost=100)

        self.assertEqual(item["rarity"], "ultimate")
        self.assertEqual(item["ultimate_tier"], 1)
        self.assertEqual(len(item["combinations"]), 5)

    def test_ultimate_subtiers_advance_to_100_with_increasing_cost(self) -> None:
        manager = BazaarManager(rng=random.Random(2))
        item = {
            "id": "ultimate-item",
            "rarity": "ultimate",
            "ultimate_tier": 1,
            "level": 1,
            "combinations": [None] * 5,
        }

        first_cost = manager.rarity_upgrade_cost(item)
        manager.upgrade_rarity(item, luck=5, currency_cost=first_cost)
        second_cost = manager.rarity_upgrade_cost(item)

        self.assertEqual(item["ultimate_tier"], 2)
        self.assertGreater(second_cost, first_cost)
        for _ in range(98):
            manager.upgrade_rarity(item, luck=5, currency_cost=second_cost)
        self.assertEqual(item["ultimate_tier"], 100)
        self.assertIs(manager.upgrade_rarity(item, luck=100, currency_cost=second_cost), item)
        self.assertEqual(item["ultimate_tier"], 100)

    def test_ultimate_subtier_upgrade_is_a_paid_transaction_and_caps_at_100(self) -> None:
        manager = BazaarManager(build_extended_catalog(), rng=random.Random(3))
        service = BazaarService(manager)
        inventory = Inventory([{
            "id": "ultimate",
            "name": "Ultimate Item",
            "type": "weapon",
            "rarity": "ultimate",
            "ultimate_tier": 1,
            "level": 1,
            "stats": {},
            "combinations": [None] * 5,
        }])
        wallet = CurrencyWallet()
        cost = manager.rarity_upgrade_cost(inventory.get("ultimate"))
        wallet.add("Gold", LargeNumber(cost))

        upgraded = service.upgrade_rarity(
            "ultimate",
            wallet=wallet,
            inventory=inventory,
            luck=5,
        )

        self.assertTrue(upgraded)
        self.assertEqual(inventory.get("ultimate")["ultimate_tier"], 2)
        self.assertEqual(wallet.get("Gold"), LargeNumber(0))
        with self.assertRaisesRegex(ValueError, "Ultimate 100"):
            service.upgrade_rarity(
                "ultimate",
                wallet=wallet,
                inventory=Inventory([{
                    **inventory.get("ultimate"),
                    "ultimate_tier": 100,
                }]),
                luck=5,
            )

    def test_invalid_ultimate_subtier_is_rejected(self) -> None:
        manager = BazaarManager()
        with self.assertRaisesRegex(ValueError, "tier"):
            manager.rarity_upgrade_cost({
                "rarity": "ultimate",
                "ultimate_tier": 101,
                "level": 1,
            })


if __name__ == "__main__":
    unittest.main()
