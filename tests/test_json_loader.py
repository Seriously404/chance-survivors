"""Tests for the JSON asset loader."""

import unittest
from game.systems.json_loader import (
    load_json_asset,
    load_weapons,
    load_armor,
    load_abilities,
    load_relics,
    load_all_items,
    create_item_catalog_from_json,
)


class JSONLoaderTests(unittest.TestCase):
    """Test the JSON asset loader."""

    def test_load_weapons(self):
        """Test loading weapons from JSON."""
        weapons = load_weapons()

        self.assertIsInstance(weapons, list)
        self.assertGreater(len(weapons), 0)

        # Check first weapon has required fields
        first_weapon = weapons[0]
        self.assertIn("id", first_weapon)
        self.assertIn("name", first_weapon)
        self.assertIn("type", first_weapon)
        self.assertIn("stats", first_weapon)

    def test_load_armor(self):
        """Test loading armor from JSON."""
        armor = load_armor()

        self.assertIsInstance(armor, list)
        self.assertGreater(len(armor), 0)

        # Check first armor has required fields
        first_armor = armor[0]
        self.assertIn("id", first_armor)
        self.assertIn("name", first_armor)
        self.assertEqual(first_armor["type"], "armor")

    def test_load_abilities(self):
        """Test loading abilities from JSON."""
        abilities = load_abilities()

        self.assertIsInstance(abilities, list)
        self.assertGreater(len(abilities), 0)

        # Check first ability has required fields
        first_ability = abilities[0]
        self.assertIn("id", first_ability)
        self.assertIn("name", first_ability)
        self.assertEqual(first_ability["type"], "ability")

    def test_load_relics(self):
        """Test loading relics from JSON."""
        relics = load_relics()

        self.assertIsInstance(relics, list)
        self.assertGreater(len(relics), 0)

        # Check first relic has required fields
        first_relic = relics[0]
        self.assertIn("id", first_relic)
        self.assertIn("name", first_relic)
        self.assertIn("rarity", first_relic)

    def test_load_all_items(self):
        """Test loading all items from JSON."""
        items = load_all_items()

        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)

        # Check that we have items of different types
        types = {item["type"] for item in items}
        self.assertIn("weapon", types)
        self.assertIn("armor", types)
        self.assertIn("ability", types)
        self.assertIn("relic", types)

    def test_create_item_catalog_from_json(self):
        """Test creating item catalog from JSON."""
        catalog = create_item_catalog_from_json()

        self.assertIsInstance(catalog, list)
        self.assertGreater(len(catalog), 0)

        # Check that all items have required fields
        for item in catalog:
            self.assertIn("id", item)
            self.assertIn("name", item)
            self.assertIn("type", item)
            self.assertIn("stats", item)

    def test_item_stats_are_dicts(self):
        """Test that all items have dict stats."""
        items = load_all_items()

        for item in items:
            self.assertIsInstance(item["stats"], dict)

    def test_item_rarities(self):
        """Test that items have valid rarities."""
        items = load_all_items()

        valid_rarities = {"common", "uncommon", "rare", "epic", "legendary", "mythical", "ultimate"}

        for item in items:
            rarity = item.get("rarity", "common")
            self.assertIn(rarity, valid_rarities)

    def test_item_levels(self):
        """Test that items have valid levels."""
        items = load_all_items()

        for item in items:
            level = item.get("level", 1)
            self.assertIsInstance(level, int)
            self.assertGreaterEqual(level, 1)


if __name__ == "__main__":
    unittest.main()
