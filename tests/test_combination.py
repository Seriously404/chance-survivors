"""Tests for the combination evaluation engine."""

import unittest
from game.systems.combination import CombinationEvaluator
from game.systems.items import create_item_catalog


class CombinationEvaluatorTests(unittest.TestCase):
    """Test the combination evaluation system."""

    def setUp(self):
        self.evaluator = CombinationEvaluator()
        self.items = create_item_catalog()

    def test_evaluate_no_supplements(self):
        """Test evaluation with no supplements."""
        base_item = self.items[0]
        result = self.evaluator.evaluate_combination(base_item, [])

        self.assertEqual(result["supplements"], [])
        self.assertEqual(result["interactions"], [])
        self.assertIn("base_item", result)

    def test_evaluate_with_supplements(self):
        """Test evaluation with supplemental items."""
        base_item = self.items[0]
        supplement = self.items[1]
        result = self.evaluator.evaluate_combination(base_item, [supplement])

        self.assertEqual(len(result["supplements"]), 1)
        self.assertIn("combined_stats", result)
        self.assertIn("final_stats", result)

    def test_aggregate_stats(self):
        """Test stat aggregation from base and supplements."""
        base_item = {"id": "test-base", "stats": {"damage": 10, "health": 20}}
        supplement = {"id": "test-supplement",
                      "stats": {"damage": 5, "luck": 3}}

        combined = self.evaluator._aggregate_stats(base_item, [supplement])

        self.assertEqual(combined["damage"], 15.0)
        self.assertEqual(combined["health"], 20.0)
        self.assertEqual(combined["luck"], 3.0)

    def test_detect_ability_interaction(self):
        """Test detection of ability interactions."""
        base_item = {
            "id": "fire-weapon",
            "stats": {"element": "fire", "cast_damage": 10},
            "type": "weapon"
        }
        supplement = {
            "id": "teleport-ability",
            "stats": {"cast_type": "teleport"},
            "type": "ability"
        }

        interactions = self.evaluator._detect_interactions(base_item, [
                                                           supplement])

        # Should detect burning trail interaction
        self.assertGreater(len(interactions), 0)
        self.assertIn("type", interactions[0])

    def test_apply_interactions(self):
        """Test applying interaction effects."""
        combined_stats = {"damage": 10.0, "health": 20.0}
        interactions = [
            {
                "type": "damage_boost",
                "effects": {"damage_pct": 20.0, "crit_chance": 5.0}
            }
        ]

        final = self.evaluator._apply_interactions(
            combined_stats, interactions)

        self.assertEqual(final["damage"], 10.0)
        self.assertEqual(final["damage_pct"], 20.0)
        self.assertEqual(final["crit_chance"], 5.0)

    def test_healing_supplement_on_damaging_ability(self):
        base = {"type": "ability", "stats": {"cast_damage": 10}}
        heal = {"type": "ability", "stats": {"cast_type": "heal"}}
        result = self.evaluator.evaluate_combination(base, [heal])
        self.assertTrue(
            any(i["type"] == "life_steal" for i in result["interactions"]))

    def test_get_combination_summary(self):
        """Test human-readable combination summary."""
        base_item = self.items[0]
        supplement = self.items[1]

        summary = self.evaluator.get_combination_summary(base_item, [
                                                         supplement])

        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)

    def test_rarity_rank(self):
        """Test rarity ranking."""
        self.assertEqual(self.evaluator._rarity_rank("common"), 0)
        self.assertEqual(self.evaluator._rarity_rank("uncommon"), 1)
        self.assertEqual(self.evaluator._rarity_rank("rare"), 2)
        self.assertEqual(self.evaluator._rarity_rank("epic"), 3)
        self.assertEqual(self.evaluator._rarity_rank("legendary"), 4)
        self.assertEqual(self.evaluator._rarity_rank("mythical"), 5)
        self.assertEqual(self.evaluator._rarity_rank("ultimate"), 6)

    def test_invalid_rarity(self):
        """Test that invalid rarity raises error."""
        with self.assertRaises(ValueError):
            self.evaluator._rarity_rank("invalid")


if __name__ == "__main__":
    unittest.main()
