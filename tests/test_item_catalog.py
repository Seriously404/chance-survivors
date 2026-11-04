"""Headless tests for versioned item-definition catalog loading."""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from game.systems.item_catalog import (
    ITEM_DEFINITIONS_VERSION,
    RARITY_COMBINATION_SLOTS,
    load_item_definitions,
)


def valid_definition(**changes):
    definition = {
        "id": "ember_rifle",
        "name": "Ember Rifle",
        "type": "weapon",
        "rarity": "rare",
        "level": 1,
        "stats": {"damage": 12, "speed_modifier": 2.0, "automatic": True},
        "tags": ["firearm", "elemental"],
        "behaviors": ["burning_round"],
        "combination_slots": 3,
        "currency_preferences": {"copper": "favored", "gold": "neutral"},
        "acquisition": {"methods": ["starter", "crate"], "min_level": 1},
        "base": True,
        "fusion_only": False,
    }
    definition.update(changes)
    return definition


def write_catalog(path: Path, definitions, *, version: int = ITEM_DEFINITIONS_VERSION):
    path.write_text(json.dumps({"version": version, "items": definitions}), encoding="utf-8")


class ItemCatalogTests(unittest.TestCase):
    def test_load_normalizes_and_returns_deterministic_json_data(self) -> None:
        definition = valid_definition(
            id="Ember-Rifle",
            type="WEAPON",
            rarity="RARE",
            name="  Ember Rifle  ",
            tags=["zeta", "alpha"],
            behaviors=["z_behavior", "a_behavior"],
            currency_preferences={"gold": "Preferred", "copper": 1.5},
            is_base=True,
        )
        definition.pop("base")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.json"
            write_catalog(path, [definition])
            first = load_item_definitions(path)
            second = load_item_definitions(path)

        self.assertEqual(first, second)
        self.assertEqual(first[0]["id"], "Ember-Rifle")
        self.assertEqual(first[0]["name"], "Ember Rifle")
        self.assertEqual(first[0]["type"], "weapon")
        self.assertEqual(first[0]["rarity"], "rare")
        self.assertEqual(first[0]["tags"], ["alpha", "zeta"])
        self.assertEqual(first[0]["behaviors"], ["a_behavior", "z_behavior"])
        self.assertEqual(first[0]["currency_preferences"], {"copper": 1.5, "gold": "favored"})
        self.assertTrue(first[0]["base"])
        self.assertFalse(first[0]["fusion_only"])
        self.assertEqual(first[0]["combination_slots"], 3)

    def test_slot_count_must_match_each_supported_rarity(self) -> None:
        definitions = [
            valid_definition(id=f"item_{rarity}", rarity=rarity, combination_slots=slots)
            for rarity, slots in RARITY_COMBINATION_SLOTS.items()
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.json"
            write_catalog(path, definitions)
            loaded = load_item_definitions(path)
        self.assertEqual([item["combination_slots"] for item in loaded], list(RARITY_COMBINATION_SLOTS.values()))

    def test_catalog_envelope_and_file_errors_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.json"
            for version in (0, 2, True):
                with self.subTest(version=version):
                    write_catalog(path, [valid_definition()], version=version)
                    with self.assertRaises(ValueError):
                        load_item_definitions(path)
            path.write_text(json.dumps({"version": 1, "items": {}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_item_definitions(path)
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_item_definitions(path)
            with self.assertRaises(ValueError):
                load_item_definitions(Path(directory) / "missing.json")

    def test_duplicate_ids_and_unstable_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.json"
            write_catalog(path, [valid_definition(), valid_definition()])
            with self.assertRaisesRegex(ValueError, "unique"):
                load_item_definitions(path)
            for item_id in ("", "bad id", " leading", "trailing ", "slash/id"):
                with self.subTest(item_id=item_id):
                    write_catalog(path, [valid_definition(id=item_id)])
                    with self.assertRaises(ValueError):
                        load_item_definitions(path)

    def test_item_fields_and_types_are_validated(self) -> None:
        invalid_definitions = [
            {"name": "No id"},
            valid_definition(name=" "),
            valid_definition(type="vehicle"),
            valid_definition(rarity="divine"),
            valid_definition(level=0),
            valid_definition(level=True),
            valid_definition(stats=[]),
            valid_definition(stats={"bad": {"nested": 1}}),
            valid_definition(stats={"bad": None}),
            valid_definition(stats={"damage": math.inf}),
            valid_definition(tags="elemental"),
            valid_definition(tags=["tag", "tag"]),
            valid_definition(tags=[""]),
            valid_definition(behaviors=["same", "same"]),
            valid_definition(combination_slots=2),
            valid_definition(combination_slots=True),
            valid_definition(currency_preferences=[]),
            valid_definition(currency_preferences={"gold": "unknown"}),
            valid_definition(currency_preferences={"gold": 0}),
            valid_definition(acquisition=[]),
            valid_definition(acquisition={"metadata": math.nan}),
            valid_definition(base="yes"),
            valid_definition(fusion_only=1),
            valid_definition(base=True, is_base=False),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.json"
            for definition in invalid_definitions:
                with self.subTest(definition=definition):
                    write_catalog(path, [definition])
                    with self.assertRaises(ValueError):
                        load_item_definitions(path)

    def test_acquisition_and_unknown_json_metadata_are_detached(self) -> None:
        definition = valid_definition(extra_metadata={"drop": {"weight": 3, "enabled": True}})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.json"
            write_catalog(path, [definition])
            loaded = load_item_definitions(path)[0]

        definition["acquisition"]["methods"].append("fusion")
        definition["extra_metadata"]["drop"]["weight"] = 99
        self.assertEqual(loaded["acquisition"]["methods"], ["starter", "crate"])
        self.assertEqual(loaded["extra_metadata"]["drop"]["weight"], 3)
        json.dumps(loaded, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
