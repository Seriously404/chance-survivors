"""Headless tests for armor-set configuration and passive bonuses."""

import json
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from game.systems.armor_sets import (
    __all__,
    armor_set_bonuses,
    armor_set_status,
    load_armor_sets,
)
from game.systems import armor_sets


def make_data(sets=None):
    return {
        "version": 1,
        "sets": sets
        if sets is not None
        else [
            {
                "id": "vanguard",
                "name": "Vanguard",
                "bonuses": {
                    "2": {"defense": 3, "health": 10},
                    "4": {"defense": 5, "speed_pct": 8},
                },
            }
        ],
    }


def load_data(data):
    with patch.object(Path, "read_text", return_value=json.dumps(data)):
        return load_armor_sets(Path("custom-armor-sets.json"))


class ArmorSetTests(unittest.TestCase):
    def setUp(self):
        self.definitions = load_data(make_data())

    def test_two_and_four_piece_thresholds_apply_once(self):
        two_piece = armor_set_bonuses(
            [{"armor_set": "vanguard"} for _ in range(2)],
            self.definitions,
        )
        self.assertEqual(two_piece["defense"], 3)
        self.assertEqual(two_piece["health"], 10)
        self.assertEqual(two_piece["speed_pct"], 0)

        four_piece = armor_set_bonuses(
            [{"armor_set": "vanguard"} for _ in range(4)],
            self.definitions,
        )
        self.assertEqual(four_piece["defense"], 8)
        self.assertEqual(four_piece["health"], 10)
        self.assertEqual(four_piece["speed_pct"], 8)

    def test_only_equipped_tagged_pieces_count(self):
        equipped_armor = [
            {"armor_set": "vanguard"},
            {"armor_set": "vanguard"},
            {"armor_set": None},
            {"id": "untagged"},
        ]
        bonuses = armor_set_bonuses(equipped_armor, self.definitions)
        self.assertEqual(bonuses["defense"], 3)

    def test_multiple_sets_stack(self):
        definitions = load_data(
            make_data(
                [
                    {
                        "id": "vanguard",
                        "name": "Vanguard",
                        "bonuses": {"2": {"defense": 3, "health": 10}},
                    },
                    {
                        "id": "oracle",
                        "name": "Oracle",
                        "bonuses": {"2": {"defense": 2, "luck": 4}},
                    },
                ]
            )
        )
        bonuses = armor_set_bonuses(
            [
                {"armor_set": "vanguard"},
                {"armor_set": "vanguard"},
                {"armor_set": "oracle"},
                {"armor_set": "oracle"},
            ],
            definitions,
        )
        self.assertEqual(bonuses["defense"], 5)
        self.assertEqual(bonuses["health"], 10)
        self.assertEqual(bonuses["luck"], 4)

    def test_returns_zero_for_every_supported_passive_stat(self):
        bonuses = armor_set_bonuses([], self.definitions)
        self.assertEqual(
            set(bonuses),
            {
                "defense",
                "health",
                "speed_pct",
                "luck",
                "damage_pct",
                "crit_chance",
                "score_bonus_pct",
                "elemental_dmg",
            },
        )
        self.assertTrue(all(value == 0 for value in bonuses.values()))

    def test_default_definitions_are_loaded_when_omitted(self):
        with patch.object(armor_sets, "load_armor_sets", return_value=self.definitions) as load:
            bonuses = armor_set_bonuses([{"armor_set": "vanguard"}] * 2)
            status = armor_set_status([{"armor_set": "vanguard"}] * 2)
        self.assertEqual(bonuses["defense"], 3)
        self.assertEqual(status[0]["id"], "vanguard")
        self.assertEqual(load.call_count, 2)

    def test_loads_from_an_optional_path(self):
        path = Path("custom-armor-sets.json")
        with patch.object(
            Path,
            "read_text",
            autospec=True,
            return_value=json.dumps(make_data()),
        ) as read_text:
            loaded = load_armor_sets(path)
        read_text.assert_called_once_with(path, encoding="utf-8")
        self.assertEqual(loaded, self.definitions)

    def test_rejects_malformed_definitions(self):
        invalid_configs = [
            {"version": True, "sets": []},
            {"version": 2, "sets": []},
            {"version": 1, "sets": {}},
            make_data([{"id": "", "name": "Name", "bonuses": {}}]),
            make_data([{"id": " padded ", "name": "Name", "bonuses": {}}]),
            make_data([{"id": "one", "name": " ", "bonuses": {}}]),
            make_data(
                [
                    {"id": "same", "name": "One", "bonuses": {}},
                    {"id": "same", "name": "Two", "bonuses": {}},
                ]
            ),
            make_data([{"id": "one", "name": "One", "bonuses": {"2.0": {}}}]),
            make_data([{"id": "one", "name": "One", "bonuses": {"6": {}}}]),
            make_data([{"id": "one", "name": "One", "bonuses": {"2": {"unknown": 1}}}]),
            make_data([{"id": "one", "name": "One", "bonuses": {"2": {"defense": True}}}]),
            make_data([{"id": "one", "name": "One", "bonuses": {"2": {"defense": math.inf}}}]),
        ]
        for config in invalid_configs:
            with self.subTest(config=config), self.assertRaises(ValueError):
                load_data(config)

    def test_rejects_unsupported_equipped_set_id(self):
        with self.assertRaises(ValueError):
            armor_set_bonuses([{"armor_set": "unknown"}], self.definitions)
        with self.assertRaisesRegex(ValueError, "non-empty strings"):
            armor_set_bonuses([{"armor_set": 3}], self.definitions)

    def test_status_reports_pieces_and_only_active_thresholds(self):
        status = armor_set_status([{"armor_set": "vanguard"}] * 2, self.definitions)
        self.assertEqual(
            status,
            [
                {
                    "id": "vanguard",
                    "name": "Vanguard",
                    "pieces": 2,
                    "active_bonuses": {"2": {"defense": 3.0, "health": 10.0}},
                }
            ],
        )

    def test_exports_only_the_integration_api(self):
        self.assertEqual(
            __all__,
            ["load_armor_sets", "armor_set_bonuses", "armor_set_status"],
        )


if __name__ == "__main__":
    unittest.main()
