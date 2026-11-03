"""Headless regression tests for combination slot ownership and type rules."""

from __future__ import annotations

import unittest

from game.systems.inventory import Inventory


def item(item_id: str, kind: str = "misc", slots: int = 3) -> dict:
    return {
        "id": item_id,
        "name": item_id,
        "type": kind,
        "rarity": "rare",
        "level": 1,
        "stats": {},
        "combinations": [None] * slots,
        "status": "normal",
    }


def combo_state(inventory: Inventory) -> dict[str, list[str | None]]:
    return {record["id"]: list(record["combinations"]) for record in inventory.items}


class InventoryCombinationTests(unittest.TestCase):
    def test_armor_pairs_only_with_armor_and_non_armor_with_non_armor(self) -> None:
        inventory = Inventory([
            item("armor-base", "armor"),
            item("armor-supplement", "armor"),
            item("misc-base", "misc"),
            item("misc-supplement", "ability"),
        ])
        inventory.assign_combination("armor-base", 0, "armor-supplement")
        inventory.assign_combination("misc-base", 0, "misc-supplement")
        before = combo_state(inventory)

        with self.assertRaises(ValueError):
            inventory.assign_combination("armor-base", 1, "misc-supplement")
        self.assertEqual(combo_state(inventory), before)
        with self.assertRaises(ValueError):
            inventory.assign_combination("misc-base", 1, "armor-supplement")
        self.assertEqual(combo_state(inventory), before)

    def test_active_item_cannot_become_a_supplement(self) -> None:
        inventory = Inventory([item("base"), item("weapon", "weapon")])
        inventory.equip("weapon", "weapons", 0)
        before = combo_state(inventory)
        with self.assertRaises(ValueError):
            inventory.assign_combination("base", 0, "weapon")
        self.assertEqual(combo_state(inventory), before)
        self.assertEqual(inventory.active_slots["weapons"][0], "weapon")

    def test_supplement_cannot_be_reused_across_bases(self) -> None:
        inventory = Inventory([item("base-a"), item("base-b"), item("supplement")])
        inventory.assign_combination("base-a", 0, "supplement")
        before = combo_state(inventory)
        with self.assertRaises(ValueError):
            inventory.assign_combination("base-b", 0, "supplement")
        self.assertEqual(combo_state(inventory), before)

    def test_self_reference_and_base_supplement_overlap_are_rejected_atomically(self) -> None:
        inventory = Inventory([item("root"), item("middle"), item("leaf")])
        before = combo_state(inventory)
        with self.assertRaises(ValueError):
            inventory.assign_combination("root", 0, "root")
        self.assertEqual(combo_state(inventory), before)

        inventory.assign_combination("root", 0, "middle")
        before = combo_state(inventory)
        # The root is already the middle item's owner; this would form a cycle.
        with self.assertRaises(ValueError):
            inventory.assign_combination("middle", 0, "root")
        self.assertEqual(combo_state(inventory), before)
        # A supplement cannot grow into a base while it remains attached.
        with self.assertRaises(ValueError):
            inventory.assign_combination("middle", 0, "leaf")
        self.assertEqual(combo_state(inventory), before)

    def test_item_that_is_already_a_base_cannot_become_a_supplement(self) -> None:
        inventory = Inventory([item("root"), item("middle"), item("leaf")])
        inventory.assign_combination("middle", 0, "leaf")
        before = combo_state(inventory)
        with self.assertRaises(ValueError):
            inventory.assign_combination("root", 0, "middle")
        self.assertEqual(combo_state(inventory), before)

    def test_same_base_moves_preserve_slot_ownership_and_allow_safe_swaps(self) -> None:
        inventory = Inventory([item("base"), item("one"), item("two")])
        inventory.assign_combination("base", 0, "one")
        inventory.assign_combination("base", 1, "two")

        # Moving one over two swaps the same-base items instead of detaching either.
        inventory.assign_combination("base", 1, "one")
        self.assertEqual(inventory.get("base")["combinations"], ["two", "one", None])

        # Moving a supplement to an empty slot clears its old slot.
        inventory.assign_combination("base", 2, "one")
        self.assertEqual(inventory.get("base")["combinations"], ["two", None, "one"])

    def test_invalid_slot_and_corrupt_initial_graphs_are_rejected(self) -> None:
        inventory = Inventory([item("base"), item("supplement")])
        before = combo_state(inventory)
        with self.assertRaises(IndexError):
            inventory.assign_combination("base", 3, "supplement")
        self.assertEqual(combo_state(inventory), before)
        with self.assertRaises(IndexError):
            inventory.assign_combination("base", True, "supplement")

        cyclic = [item("a"), item("b")]
        cyclic[0]["combinations"][0] = "b"
        cyclic[1]["combinations"][0] = "a"
        with self.assertRaises(ValueError):
            Inventory(cyclic)

        repeated = [item("a"), item("b"), item("c")]
        repeated[0]["combinations"][0] = "c"
        repeated[1]["combinations"][0] = "c"
        with self.assertRaises(ValueError):
            Inventory(repeated)


if __name__ == "__main__":
    unittest.main()
