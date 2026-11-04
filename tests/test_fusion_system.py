"""Headless regression tests for the fusion system."""

import unittest

from game.systems.fusion import FusionManager
from game.systems.inventory import Inventory


class FusionSystemTests(unittest.TestCase):
    def test_fusion_unlocks_at_endgame_level_50_only(self) -> None:
        manager = FusionManager()

        self.assertFalse(manager.is_unlocked(49))
        self.assertTrue(manager.is_unlocked(50))
        self.assertTrue(manager.is_unlocked(51))
        self.assertFalse(manager.is_unlocked(True))

    def test_fusion_manager_creates_valid_fused_item(self) -> None:
        manager = FusionManager()
        weapon = {"id": "w1", "name": "Alpha Rifle", "type": "weapon", "rarity": "epic", "level": 3, "tags": ["sniper"], "stats": {"damage": 18, "speed_modifier": 2.2, "bullet_type": "rapid_fire", "element": "frost"}}
        ability = {"id": "a1", "name": "Nova Charm", "type": "ability", "rarity": "epic", "level": 2, "stats": {"cooldown": 8, "damage_pct": 10}}
        fused = manager.build_fusion([weapon, ability], recipe_id="solar-hammer")
        self.assertEqual(fused["name"], "Solar Hammer")
        self.assertEqual(fused["type"], "weapon")
        self.assertIn("fusion_recipe", fused)
        self.assertGreater(fused["level"], 3)
        self.assertEqual(fused["stats"]["bullet_type"], "rapid_fire")
        self.assertEqual(fused["stats"]["element"], "frost")
        self.assertTrue(fused["fusion_only"])
        self.assertEqual(fused["tags"], ["sniper"])

    def test_inventory_fusion_removes_sources_and_keeps_result(self) -> None:
        inventory = Inventory([
            {"id": "w1", "name": "Alpha Rifle", "type": "weapon", "rarity": "epic", "level": 3, "stats": {"damage": 18, "speed_modifier": 2.2}, "combinations": [None] * 3, "status": "normal"},
            {"id": "a1", "name": "Nova Charm", "type": "ability", "rarity": "epic", "level": 2, "stats": {"cooldown": 8, "damage_pct": 10}, "combinations": [None] * 3, "status": "normal"},
            {"id": "c1", "name": "Cinder Plate", "type": "armor", "rarity": "rare", "level": 2, "stats": {"defense": 7}, "combinations": [None] * 3, "status": "normal"},
        ])
        fused = inventory.fuse_items(["w1", "a1"], fusion_manager=FusionManager(), recipe_id="solar-hammer")
        self.assertEqual(len(inventory.items), 2)
        self.assertTrue(any(item["id"] == fused["id"] for item in inventory.items))
        self.assertNotIn("w1", {item["id"] for item in inventory.items})
        self.assertNotIn("a1", {item["id"] for item in inventory.items})

    def test_recipe_rejects_wrong_types_and_below_threshold_sources(self) -> None:
        manager = FusionManager()
        weapon = {"id": "w1", "type": "weapon", "rarity": "rare", "level": 3, "stats": {}}
        ability = {"id": "a1", "type": "ability", "rarity": "epic", "level": 2, "stats": {}}

        with self.assertRaisesRegex(ValueError, "Solar Hammer requires weapon \\+ ability"):
            manager.build_fusion([weapon, {"id": "armor", "type": "armor", "rarity": "epic", "level": 2, "stats": {}}],
                                 recipe_id="solar-hammer")
        with self.assertRaisesRegex(ValueError, "Epic or higher"):
            manager.build_fusion([weapon, ability], recipe_id="solar-hammer")
        with self.assertRaisesRegex(ValueError, "level 2 or higher"):
            manager.build_fusion([
                {**weapon, "rarity": "epic", "level": 1},
                ability,
            ], recipe_id="solar-hammer")

    def test_repeated_fusions_have_distinct_ids_and_preserve_sources_on_failure(self) -> None:
        manager = FusionManager()
        items = [
            {"id": "w1", "type": "weapon", "rarity": "epic", "level": 3, "stats": {}},
            {"id": "a1", "type": "ability", "rarity": "epic", "level": 2, "stats": {}},
            {"id": "w2", "type": "weapon", "rarity": "epic", "level": 3, "stats": {}},
            {"id": "a2", "type": "ability", "rarity": "epic", "level": 2, "stats": {}},
        ]
        first = manager.build_fusion(items[:2], recipe_id="solar-hammer")
        second = manager.build_fusion(items[2:], recipe_id="solar-hammer")
        self.assertNotEqual(first["id"], second["id"])

        inventory = Inventory([
            {**item, "combinations": [None], "status": "normal"}
            for item in items[:2]
        ])
        inventory.get("w1")["combinations"][0] = "a1"
        with self.assertRaisesRegex(ValueError, "Remove fusion sources from combinations"):
            inventory.fuse_items(["w1", "a1"], recipe_id="solar-hammer", fusion_manager=manager)
        self.assertEqual({item["id"] for item in inventory.items}, {"w1", "a1"})

    def test_find_companion_returns_only_a_complete_recipe_pair(self) -> None:
        manager = FusionManager()
        source = {"id": "w1", "type": "weapon", "rarity": "epic", "level": 2, "stats": {}}
        candidates = [
            {"id": "bad-rarity", "type": "ability", "rarity": "rare", "level": 2, "stats": {}},
            {"id": "wrong-type", "type": "armor", "rarity": "ultimate", "level": 5, "stats": {}},
            {"id": "valid", "type": "ability", "rarity": "epic", "level": 2, "stats": {}},
        ]

        self.assertEqual(
            manager.find_companion(source, candidates, "solar-hammer")["id"],
            "valid",
        )


if __name__ == "__main__":
    unittest.main()
