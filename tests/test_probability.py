"""Tests for the probability and luck system."""

import unittest
from game.systems.probability import (
    ProbabilitySystem,
    ProbabilityConfig,
    PROBABILITY_SYSTEMS,
)


class ProbabilitySystemTests(unittest.TestCase):
    """Test the probability system."""

    def setUp(self):
        self.system = ProbabilitySystem()

    def test_register_config(self):
        """Test registering a probability configuration."""
        config = ProbabilityConfig(
            base_probability=0.5,
            luck_factor=0.1,
            max_probability=0.9,
            description="Test config"
        )
        self.system.register_config("test_system", config)

        retrieved = self.system.get_config("test_system")
        self.assertEqual(retrieved.base_probability, 0.5)
        self.assertEqual(retrieved.description, "Test config")

    def test_default_config(self):
        """Test that unregistered systems get default config."""
        config = self.system.get_config("unregistered_system")
        self.assertIsInstance(config, ProbabilityConfig)
        self.assertIn("unregistered_system", config.description)

    def test_calculate_probability_with_luck(self):
        """Test probability calculation with luck modifier."""
        self.system.register_system(
            "test_system",
            base_probability=0.5,
            luck_factor=0.1,
        )

        prob_no_luck = self.system.calculate_probability(
            "test_system", luck=0.0)
        prob_with_luck = self.system.calculate_probability(
            "test_system", luck=10.0)

        self.assertLess(prob_no_luck, prob_with_luck)
        self.assertGreaterEqual(prob_with_luck, prob_no_luck)

    def test_probability_clamping(self):
        """Test that probability is clamped to valid range."""
        self.system.register_system(
            "test_system",
            base_probability=0.5,
            luck_factor=0.1,
            max_probability=0.98,
            min_probability=0.0,
        )

        # High luck should not exceed max_probability
        prob = self.system.calculate_probability("test_system", luck=1000.0)
        self.assertLessEqual(prob, 0.98)

        # Negative luck should not go below min_probability
        prob = self.system.calculate_probability("test_system", luck=-100.0)
        self.assertGreaterEqual(prob, 0.0)

    def test_roll(self):
        """Test probability roll."""
        self.system.register_system(
            "test_system",
            base_probability=0.5,
            luck_factor=0.0,
        )

        # With 50% base probability, should have roughly 50% success rate
        successes = sum(
            self.system.roll("test_system")
            for _ in range(1000)
        )

        # Allow some variance (should be between 40% and 60%)
        self.assertGreater(successes, 400)
        self.assertLess(successes, 600)

    def test_roll_with_description(self):
        """Test roll with detailed feedback."""
        self.system.register_system(
            "test_system",
            base_probability=0.5,
            luck_factor=0.1,
        )

        success, description = self.system.roll_with_description(
            "test_system", luck=5.0)

        self.assertIsInstance(success, bool)
        self.assertIsInstance(description, str)
        self.assertGreater(len(description), 0)
        self.assertIn("test_system", description)

    def test_register_system_convenience(self):
        """Test the convenience register_system method."""
        self.system.register_system(
            "custom_system",
            base_probability=0.3,
            luck_factor=0.05,
            max_probability=0.8,
            description="Custom system",
        )

        config = self.system.get_config("custom_system")
        self.assertEqual(config.base_probability, 0.3)
        self.assertEqual(config.max_probability, 0.8)
        self.assertEqual(config.description, "Custom system")

    def test_custom_modifier(self):
        """Test custom probability modifier."""
        self.system.register_system(
            "test_system",
            base_probability=0.5,
            luck_factor=0.0,
        )

        prob_no_modifier = self.system.calculate_probability(
            "test_system", custom_modifier=0.0)
        prob_with_modifier = self.system.calculate_probability(
            "test_system", custom_modifier=0.2)

        self.assertLess(prob_no_modifier, prob_with_modifier)


class GlobalProbabilitySystemTests(unittest.TestCase):
    """Test the global probability system instance."""

    def test_global_system_exists(self):
        """Test that the global system is initialized."""
        self.assertIsInstance(PROBABILITY_SYSTEMS, ProbabilitySystem)

    def test_global_system_has_preregistered_systems(self):
        """Test that global system has pre-registered systems."""
        # Check that at least one system is registered
        config = PROBABILITY_SYSTEMS.get_config("crate_reward")
        self.assertIsInstance(config, ProbabilityConfig)

    def test_global_system_roll(self):
        """Test rolling on a pre-registered system."""
        success = PROBABILITY_SYSTEMS.roll("crate_reward")
        self.assertIsInstance(success, bool)


if __name__ == "__main__":
    unittest.main()
