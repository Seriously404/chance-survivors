"""Headless coverage for independent active-time and difficulty scaling."""

from __future__ import annotations

import math
import unittest

from game.systems.scaling import ScalingConfig, ScalingSystem
from game.utils.large_number import LargeNumber


class ScalingSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ScalingConfig(
            time_step_seconds=10,
            time_health_multiplier=2,
            time_damage_multiplier="1.5",
            time_spawn_rate_multiplier=3,
            time_reward_multiplier=2,
            difficulty_health_multiplier=4,
            difficulty_damage_multiplier=2,
            difficulty_spawn_rate_multiplier=5,
            difficulty_reward_multiplier=3,
        )

    def test_active_time_and_explicit_difficulty_scale_independently(self) -> None:
        scaling = ScalingSystem(self.config)
        scaling.update_active_time(19)
        self.assertEqual(scaling.active_time_seconds, 19.0)
        self.assertEqual(scaling.active_time_steps, 1)
        scaling.increase_difficulty()

        # Difficulty adds its own multiplier without advancing gameplay time.
        self.assertEqual(scaling.active_time_seconds, 19.0)
        self.assertEqual(scaling.difficulty_level, 1)
        self.assertEqual(scaling.multipliers(), {
            "health": LargeNumber(8),
            "damage": LargeNumber(3),
            "spawn_rate": LargeNumber(15),
            "reward": LargeNumber(6),
        })

        stats = scaling.scaled_enemy_stats(100, 10)
        self.assertEqual(stats["health"], 800)
        self.assertEqual(stats["damage"], 30)
        self.assertEqual(stats["reward"], 6)
        self.assertEqual(stats["spawn_rate_multiplier"], 15)
        self.assertAlmostEqual(scaling.spawn_delay_seconds(3), 0.2)

    def test_time_only_changes_when_active_delta_is_supplied(self) -> None:
        scaling = ScalingSystem(self.config)
        self.assertEqual(scaling.active_time_seconds, 0.0)
        self.assertEqual(scaling.active_time_steps, 0)
        with self.assertRaises(AttributeError):
            scaling.active_time_seconds = 10
        with self.assertRaises(AttributeError):
            scaling.difficulty_level = 1
        scaling.increase_difficulty(2)
        self.assertEqual(scaling.active_time_seconds, 0.0)
        self.assertEqual(scaling.active_time_steps, 0)
        scaling.update_active_time(10)
        self.assertEqual(scaling.active_time_steps, 1)
        self.assertEqual(scaling.difficulty_level, 2)

    def test_very_large_combat_scaling_uses_large_number(self) -> None:
        scaling = ScalingSystem(ScalingConfig(
            time_step_seconds=1,
            time_health_multiplier="1e10000",
            time_damage_multiplier="1e10000",
            time_spawn_rate_multiplier="1e10000",
        ))
        scaling.update_active_time(2)
        stats = scaling.scaled_enemy_stats(7, 11)
        self.assertEqual(stats["health"], LargeNumber("7e20000"))
        self.assertEqual(stats["damage"], LargeNumber("1.1e20001"))
        self.assertEqual(stats["spawn_rate_multiplier"],
                         LargeNumber("1e20000"))
        self.assertEqual(stats["reward"], LargeNumber("1.1025"))
        self.assertEqual(scaling.spawn_delay_seconds(
            1), scaling.config.minimum_spawn_delay_seconds)

    def test_versioned_serialization_round_trip_preserves_config_and_state(self) -> None:
        scaling = ScalingSystem(self.config)
        scaling.update_active_time(25.5)
        scaling.increase_difficulty(3)
        restored = ScalingSystem.from_dict(scaling.to_dict())
        self.assertEqual(restored.to_dict(), scaling.to_dict())
        self.assertEqual(restored.active_time_steps, 2)
        self.assertEqual(restored.scaled_enemy_stats(100, 10),
                         scaling.scaled_enemy_stats(100, 10))

    def test_invalid_inputs_and_corrupt_saves_are_rejected(self) -> None:
        for value in (0, -1, math.inf, math.nan, True):
            with self.subTest(time_step=value), self.assertRaises(ValueError):
                ScalingConfig(time_step_seconds=value)
        with self.assertRaises(ValueError):
            ScalingConfig(time_step_seconds=10 ** 10000)
        with self.assertRaises(ValueError):
            ScalingConfig(time_health_multiplier="0.5")

        scaling = ScalingSystem(self.config)
        for delta in (-1, math.inf, math.nan, True, 10 ** 10000):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                scaling.update_active_time(delta)
        for steps in (0, -1, True, 1.5):
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                scaling.increase_difficulty(steps)
        with self.assertRaises(ValueError):
            scaling.scaled_enemy_stats(0, 1)
        with self.assertRaises(ValueError):
            scaling.spawn_delay_seconds(0)
        with self.assertRaises(ValueError):
            scaling.spawn_delay_seconds(10 ** 10000)
        with self.assertRaises(ValueError):
            ScalingSystem.from_dict({"version": 2})


if __name__ == "__main__":
    unittest.main()
