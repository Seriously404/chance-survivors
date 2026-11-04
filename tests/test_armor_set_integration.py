"""Integration tests for armor set metadata and passive player bonuses."""

import unittest
from unittest.mock import patch

from game.systems.bazaar import BazaarManager, build_extended_catalog
from game.systems.bazaar_service import BazaarService
from game.systems.currency import CurrencyWallet
from game.systems.inventory import Inventory
from game.systems.items import armor_set_status, create_item_catalog, player_bonuses
from game.systems.numbers import LargeNumber


def _armor_piece(item_id: str, set_id: str, armor_slot: str) -> dict:
    return {
        "id": item_id,
        "name": item_id,
        "type": "armor",
        "rarity": "common",
        "level": 1,
        "armor_set": set_id,
        "armor_slot": armor_slot,
        "stats": {},
        "combinations": [None],
    }


class ArmorSetIntegrationTests(unittest.TestCase):
    def test_set_piece_metadata_survives_catalog_and_is_shop_available(self) -> None:
        catalog_items = [
            item for item in create_item_catalog() if item.get("armor_set") == "bulwark"
        ]
        shop_items = [
            item for item in build_extended_catalog() if item.get("armor_set") == "bulwark"
        ]

        self.assertEqual(len(catalog_items), 4)
        self.assertEqual(
            {item["id"] for item in catalog_items},
            {item["id"] for item in shop_items},
        )
        self.assertEqual(
            {item["armor_slot"] for item in catalog_items},
            {"pants", "chestplate", "headpiece", "accessory"},
        )

    def test_purchasing_set_piece_preserves_set_and_slot_metadata(self) -> None:
        manager = BazaarManager(build_extended_catalog())
        service = BazaarService(manager)
        inventory = Inventory([])
        wallet = CurrencyWallet()
        wallet.add("Gold", LargeNumber(1000))

        bought = service.buy_catalog_item(
            "bulwark-helm",
            wallet=wallet,
            inventory=inventory,
            item_id="owned-bulwark-helm",
        )

        self.assertEqual(bought["armor_set"], "bulwark")
        self.assertEqual(bought["armor_slot"], "headpiece")

    def test_catalog_rejects_unknown_set_metadata(self) -> None:
        invalid_item = {
            "id": "bad-armor",
            "name": "Bad Armor",
            "type": "armor",
            "rarity": "common",
            "level": 1,
            "armor_set": "missing-set",
            "armor_slot": "boots",
            "stats": {},
        }

        with patch(
            "game.systems.items.create_item_catalog_from_json",
            return_value=[invalid_item],
        ):
            with self.assertRaisesRegex(ValueError, "Unsupported armor set"):
                create_item_catalog()

    def test_only_equipped_pieces_contribute_set_bonuses(self) -> None:
        inventory = Inventory([
            _armor_piece("bulwark-1", "bulwark", "boots"),
            _armor_piece("bulwark-2", "bulwark", "pants"),
        ])
        inventory.equip("bulwark-1", "armor", 0)

        bonuses = player_bonuses(inventory)
        status = armor_set_status(inventory)

        self.assertEqual(bonuses["defense"], 0)
        self.assertEqual(bonuses["health"], 0)
        self.assertEqual(status[0]["pieces"], 1)

    def test_two_piece_and_four_piece_bonuses_stack(self) -> None:
        armor_slots = ("boots", "pants", "chestplate", "headpiece")
        inventory = Inventory([
            _armor_piece(f"bulwark-{index}", "bulwark", armor_slots[index])
            for index in range(4)
        ])
        for index in range(4):
            inventory.equip(f"bulwark-{index}", "armor", index)

        bonuses = player_bonuses(inventory)

        self.assertEqual(bonuses["defense"], 8)
        self.assertEqual(bonuses["health"], 60)
        self.assertEqual(bonuses["damage_pct"], 8)

    def test_different_set_bonuses_stack_across_equipped_items(self) -> None:
        inventory = Inventory([
            _armor_piece("bulwark-1", "bulwark", "boots"),
            _armor_piece("bulwark-2", "bulwark", "pants"),
            _armor_piece("windrunner-1", "windrunner", "chestplate"),
            _armor_piece("windrunner-2", "windrunner", "headpiece"),
        ])
        for index, item in enumerate(inventory.items):
            inventory.equip(item["id"], "armor", index)

        bonuses = player_bonuses(inventory)

        self.assertEqual(bonuses["defense"], 3)
        self.assertEqual(bonuses["health"], 20)
        self.assertEqual(bonuses["speed_pct"], 8)
        self.assertEqual(bonuses["luck"], 2)

    def test_set_piece_cannot_be_equipped_in_another_armor_slot(self) -> None:
        inventory = Inventory([_armor_piece("bulwark-helm", "bulwark", "headpiece")])

        with self.assertRaisesRegex(ValueError, "belongs in the headpiece slot"):
            inventory.equip("bulwark-helm", "armor", 0)

    def test_set_piece_requires_a_designated_equipment_slot(self) -> None:
        item = _armor_piece("bulwark-helm", "bulwark", "headpiece")
        del item["armor_slot"]
        inventory = Inventory([item])

        with self.assertRaisesRegex(ValueError, "must define an equipment slot"):
            inventory.equip("bulwark-helm", "armor", 3)


if __name__ == "__main__":
    unittest.main()
