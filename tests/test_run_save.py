<<<<<<< HEAD
"""Headless tests for validated, versioned run persistence."""
=======
"""Headless tests for validated run-save serialization and persistence."""
>>>>>>> birch/projectile-collision-effects

import tempfile
import unittest
from pathlib import Path

from game.systems.items import create_initial_inventory
<<<<<<< HEAD
from game.systems.numbers import LargeNumber
from game.systems.quests import QuestManager
from game.systems.run_save import RunSave


class RunSaveTests(unittest.TestCase):
    def create_save(self) -> RunSave:
        inventory = create_initial_inventory()
        inventory.items[0]["stats"]["extreme_test"] = LargeNumber("1e400")
        weapon = next(item for item in inventory.items if item["type"] == "weapon")
        inventory.equip(weapon["id"], "weapons", 0)
        quests = QuestManager()
        quests.register_level(5)
        quests.register_kill("basic")
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
            currencies={"Copper": LargeNumber("1e100"), "Gold": LargeNumber(9)},
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
        self.assertIsInstance(state["inventory"]["active_slots"]["weapons"][0], str)
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
        self.assertEqual(restored.state["bazaar_last_manual_refresh_cycle"], -1)

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
=======
from game.systems.run_save import RunSave
from game.systems.scoring import RunScore
from game.utils.large_number import LargeNumber


def create_save() -> RunSave:
    score = RunScore(25)
    score.award("1e1200")
    inventory = create_initial_inventory()
    return RunSave.capture(
        player_name="  Moss  ",
        elapsed_seconds=123.5,
        score=score,
        player={
            "level": 7,
            "health": 125,
            "max_health": 140,
            "stats": {"luck": LargeNumber("1e1000")},
        },
        inventory=inventory,
        currencies={"Copper": LargeNumber("2e1500"), "Gold": 12},
        quests={"version": 1, "progress": {"side_first_blood": 3}},
    )


class RunSaveTests(unittest.TestCase):
    def test_json_round_trip_preserves_run_and_reconstructs_inventory(self) -> None:
        original = create_save()
        restored = RunSave.from_json(original.to_json())

        self.assertEqual(restored.player_name, "Moss")
        self.assertEqual(restored.elapsed_seconds, 123.5)
        self.assertEqual(restored.restore_score().total_score, LargeNumber("1.25e1200"))
        self.assertEqual(restored.player["stats"]["luck"], LargeNumber("1e1000"))
        self.assertEqual(restored.currencies["Copper"], LargeNumber("2e1500"))
        self.assertEqual(restored.quests, {"version": 1, "progress": {"side_first_blood": 3}})
        inventory = restored.restore_inventory()
        self.assertEqual(inventory.active_slots, original.inventory["active_slots"])
        self.assertEqual(len(inventory.items), len(original.inventory["items"]))

    def test_atomic_file_save_load(self) -> None:
        original = create_save()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "run.json"
            original.save(path)
            restored = RunSave.load(path)
            self.assertEqual(restored.to_dict(), original.to_dict())
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_capture_detaches_from_live_inventory(self) -> None:
        original = create_save()
        before = original.inventory["items"][0]["name"]
        inventory = create_initial_inventory()
        inventory.items[0]["name"] = "Changed after capture"
        self.assertEqual(original.inventory["items"][0]["name"], before)

    def test_rejects_bad_identity_time_currency_inventory_and_version(self) -> None:
        base = create_save().to_dict()
        for name in ("", "x" * 41):
            raw = {**base, "player_name": name}
            with self.subTest(name=name), self.assertRaises(ValueError):
                RunSave.from_dict(raw)
        for elapsed in (-1, float("nan"), float("inf")):
            raw = {**base, "elapsed_seconds": elapsed}
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                RunSave.from_dict(raw)
        raw = {**base, "version": 99}
        with self.assertRaises(ValueError):
            RunSave.from_dict(raw)
        raw = {**base, "currencies": {"Copper": -1}}
        with self.assertRaises(ValueError):
            RunSave.from_dict(raw)
        raw = {**base, "player": {**base["player"], "health": 999}}
        with self.assertRaises(ValueError):
            RunSave.from_dict(raw)
        raw = {
            **base,
            "inventory": {
                "items": [
                    {"id": "a", "type": "misc", "combinations": ["b"]},
                    {"id": "b", "type": "misc", "combinations": ["a"]},
                ],
                "active_slots": {
                    "armor": [None] * 5,
                    "weapons": [None] * 2,
                    "abilities": [None] * 10,
                },
            },
        }
        with self.assertRaises(ValueError):
            RunSave.from_dict(raw)

    def test_rejects_malformed_json_and_oversized_save(self) -> None:
        with self.assertRaises(ValueError):
            RunSave.from_json("{")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "too-large.json"
            path.write_bytes(b" " * (5 * 1024 * 1024 + 1))
            with self.assertRaises(ValueError):
                RunSave.load(path)
>>>>>>> birch/projectile-collision-effects


if __name__ == "__main__":
    unittest.main()
