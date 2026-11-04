"""Headless tests for validated, versioned run persistence."""

import tempfile
import unittest
from pathlib import Path

from game.systems.items import create_initial_inventory
from game.systems.numbers import LargeNumber
from game.systems.quests import QuestManager
from game.systems.run_save import RunSave
from game.utils.large_number import LargeNumber as CombatNumber


class RunSaveTests(unittest.TestCase):
    def test_damaged_large_health_round_trips_exactly(self) -> None:
        original = self.create_save()
        original.state["player"] = {
            "health": CombatNumber("7.1234567890123456789e400"),
            "max_health": CombatNumber("1e401"),
        }
        original = RunSave(original.state)
        restored = RunSave.from_json(original.to_json())
        self.assertEqual(
            restored.state["player"]["health"], original.state["player"]["health"])
        self.assertEqual(
            restored.state["player"]["max_health"], original.state["player"]["max_health"])

    def create_save(self) -> RunSave:
        inventory = create_initial_inventory()
        inventory.items[0]["stats"]["extreme_test"] = LargeNumber("1e400")
        weapon = next(
            item for item in inventory.items if item["type"] == "weapon")
        inventory.equip(weapon["id"], "weapons", 0)
        quests = QuestManager()
        quests.register_level(8)
        quests.register_kill("basic")
        quests.accept("main-bastion")
        quests.lock_main_quest(quests.main_quest.id)
        return RunSave.capture(
            player_name="Saved Player",
            elapsed_seconds=123.5,
            score=LargeNumber("1e400"),
            player_health=75,
            player_max_health=100,
            progression_level=4,
            current_exp=LargeNumber("2e80"),
            total_exp=LargeNumber("3e90"),
            inventory=inventory,
            currencies={"Copper": LargeNumber(
                "1e100"), "Gold": LargeNumber(9)},
            quest_state=quests.to_save_state(),
            threat_level=7,
            spawn_counter=11,
            bazaar_seed=23,
            bazaar_refresh_count=2,
            bazaar_last_manual_refresh_cycle=0,
        )

    def test_round_trip_preserves_large_values_equipment_and_quest_progress(self) -> None:
        original = self.create_save()
        loaded = RunSave.from_json(original.to_json())
        state = loaded.state
        self.assertEqual(state["score"], "1E+400")
        self.assertEqual(state["currencies"]["Copper"], "1E+100")
        self.assertIsInstance(
            state["inventory"]["active_slots"]["weapons"][0], str)
        self.assertEqual(state["quests"]["kills_total"], 1)
        self.assertEqual(state["spawn_counter"], 11)
        self.assertEqual(state["bazaar_seed"], 23)
        self.assertEqual(state["bazaar_refresh_count"], 2)
        self.assertEqual(state["bazaar_last_manual_refresh_cycle"], 0)
        self.assertEqual(
            state["inventory"]["items"][0]["stats"]["extreme_test"],
            LargeNumber("1e400"),
        )
        restored_inventory = loaded.restore_inventory()
        self.assertEqual(
            restored_inventory.active_slots["weapons"][0],
            state["inventory"]["active_slots"]["weapons"][0],
        )

        restored_quests = QuestManager.from_save_state(state["quests"])
        self.assertEqual(restored_quests.kills_total, 1)
        self.assertTrue(restored_quests.main_quest.lock_on_accept)
        self.assertEqual(restored_quests.main_quest.id, "main-bastion")

    def test_atomic_file_round_trip_and_missing_file_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "run.json"
            original = self.create_save()
            original.write(path)
            self.assertEqual(RunSave.read(path).to_json(), original.to_json())
            with self.assertRaisesRegex(ValueError, "Could not read run save"):
                RunSave.read(path.with_name("missing.json"))

    def test_older_version_one_save_defaults_bazaar_rotation_state(self) -> None:
        payload = self.create_save().to_dict()
        payload.pop("bazaar_seed")
        payload.pop("bazaar_refresh_count")
        payload.pop("bazaar_last_manual_refresh_cycle")

        restored = RunSave.from_dict(payload)

        self.assertEqual(restored.state["bazaar_seed"], 0)
        self.assertEqual(restored.state["bazaar_refresh_count"], 0)
        self.assertEqual(
            restored.state["bazaar_last_manual_refresh_cycle"], -1)

    def test_round_trip_preserves_ultimate_rarity_subtier(self) -> None:
        payload = self.create_save().to_dict()
        item = payload["inventory"]["items"][0]
        item["rarity"] = "ultimate"
        item["ultimate_tier"] = 73
        item["combinations"] = [None] * 5

        restored = RunSave.from_dict(payload)

        self.assertEqual(
            restored.restore_inventory().items[0]["ultimate_tier"],
            73,
        )

    def test_rejects_bad_version_duplicate_equipment_and_invalid_numbers(self) -> None:
        payload = self.create_save().to_dict()
        payload["version"] = 99
        with self.assertRaisesRegex(ValueError, "version"):
            RunSave.from_dict(payload)

        payload = self.create_save().to_dict()
        payload["inventory"]["active_slots"]["weapons"][1] = payload[
            "inventory"
        ]["active_slots"]["weapons"][0]
        with self.assertRaises(ValueError):
            RunSave.from_dict(payload)

        payload = self.create_save().to_dict()
        payload["score"] = "NaN"
        with self.assertRaises(ValueError):
            RunSave.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
