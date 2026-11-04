"""Regression tests for the relic system and live inventory passives."""

import unittest

from game.systems.items import create_initial_inventory
from game.systems.relics import build_relic_catalog, relic_effect_summary


class RelicSystemTests(unittest.TestCase):
    def test_relic_catalog_contains_functional_items(self) -> None:
        catalog = build_relic_catalog()
        self.assertGreater(len(catalog), 0)
        self.assertTrue(all(item["type"] == "relic" for item in catalog))
        self.assertTrue(any(item["stats"].get("luck", 0) > 0 for item in catalog))

    def test_inventory_relic_summary_aggregates_passive_bonuses(self) -> None:
        inventory = create_initial_inventory()
        summary = relic_effect_summary(inventory)
        self.assertGreater(len(summary["items"]), 0)
        self.assertGreater(summary["summary"]["luck"], 0.0)
        self.assertGreater(summary["summary"]["crit_chance"], 0.0)


if __name__ == "__main__":
    unittest.main()
