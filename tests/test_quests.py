"""Regression tests for the data-driven quest system."""

import unittest

from game.systems.items import create_item_catalog
from game.systems.quests import QuestManager


class QuestManagerTests(unittest.TestCase):
    def test_unlocks_side_and_main_quests_and_rewards(self) -> None:
        manager = QuestManager([
            {
                "id": "side-kill-10",
                "name": "Warmup Sweep",
                "description": "Defeat 10 enemies.",
                "quest_type": "side",
                "unlock_level": 1,
                "reward_pct": 5.0,
                "condition": "kills_total",
                "target": 10,
            },
            {
                "id": "main-level-5",
                "name": "The Bastion Run",
                "description": "Reach level 5.",
                "quest_type": "main",
                "unlock_level": 5,
                "reward_pct": 25.0,
                "condition": "level_reached",
                "target": 5,
                "restrictions": ["No sniper weapons"],
            },
        ])

        self.assertEqual(len(manager.active_quests), 1)
        self.assertEqual(manager.active_quests[0].id, "side-kill-10")

        for _ in range(10):
            manager.register_kill("basic")

        self.assertEqual(manager.total_bonus_pct(), 5.0)
        self.assertTrue(any(quest.id == "side-kill-10" for quest in manager.completed_quests))

        manager.register_level(5)
        self.assertIsNotNone(manager.main_quest)
        self.assertTrue(any(quest.id == "main-level-5" for quest in manager.completed_quests))
        self.assertEqual(manager.total_bonus_pct(), 30.0)

    def test_locking_main_quest_enables_restriction_tracking(self) -> None:
        manager = QuestManager([
            {
                "id": "main-no-snipers",
                "name": "No Snipers",
                "description": "Reach level 10 without sniper weapons.",
                "quest_type": "main",
                "unlock_level": 5,
                "reward_pct": 20.0,
                "condition": "level_reached",
                "target": 10,
                "restrictions": ["No sniper weapons"],
            }
        ])

        manager.register_level(5)
        self.assertTrue(manager.main_quest is not None)
        self.assertTrue(manager.lock_main_quest("main-no-snipers"))
        self.assertTrue(manager.main_quest.lock_on_accept)

    def test_locked_main_quest_rejects_tagged_equipment_and_can_be_unlocked(self) -> None:
        manager = QuestManager([
            {
                "id": "main-no-snipers",
                "name": "No Snipers",
                "description": "Reach level 10 without sniper weapons.",
                "quest_type": "main",
                "unlock_level": 5,
                "reward_pct": 20.0,
                "condition": "level_reached",
                "target": 10,
                "restrictions": ["Do not equip sniper weapons"],
                "forbidden_item_tags": ["sniper"],
            }
        ])
        manager.register_level(5)
        sniper = {"id": "sniper-instance", "tags": ["SnIpEr"]}
        rifle = {"id": "rifle-instance", "tags": ["rifle"]}

        self.assertTrue(manager.set_main_quest_lock("main-no-snipers", True))
        self.assertFalse(manager.can_equip(sniper))
        self.assertTrue(manager.can_equip(rifle))
        restored = QuestManager.from_save_state(
            manager.to_save_state(),
            [
                {
                    "id": "main-no-snipers",
                    "name": "No Snipers",
                    "description": "Reach level 10 without sniper weapons.",
                    "quest_type": "main",
                    "unlock_level": 5,
                    "reward_pct": 20.0,
                    "condition": "level_reached",
                    "target": 10,
                    "forbidden_item_tags": ["sniper"],
                }
            ],
        )
        self.assertFalse(restored.can_equip(sniper))
        self.assertTrue(manager.set_main_quest_lock("main-no-snipers", False))
        self.assertTrue(manager.can_equip(sniper))

    def test_main_restriction_lock_refuses_conflicting_equipped_items(self) -> None:
        manager = QuestManager([
            {
                "id": "main-no-snipers",
                "name": "No Snipers",
                "description": "Reach level 10 without sniper weapons.",
                "quest_type": "main",
                "unlock_level": 5,
                "reward_pct": 20.0,
                "condition": "level_reached",
                "target": 10,
                "forbidden_item_tags": ["sniper"],
            }
        ])
        manager.register_level(5)

        self.assertFalse(manager.set_main_quest_lock(
            "main-no-snipers", True, [{"id": "sniper", "tags": ["sniper"]}]
        ))
        self.assertFalse(manager.main_quest.lock_on_accept)

    def test_sniper_definition_tag_survives_inventory_creation(self) -> None:
        sniper = next(
            item for item in create_item_catalog()
            if item["id"] == "lantern-sniper"
        )

        self.assertIn("sniper", sniper["tags"])


if __name__ == "__main__":
    unittest.main()
