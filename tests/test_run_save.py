"""Headless tests for validated run-save serialization and persistence."""

import tempfile
import unittest
from pathlib import Path

from game.systems.items import create_initial_inventory
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


if __name__ == "__main__":
    unittest.main()
