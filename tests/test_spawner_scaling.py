"""Headless integration tests for spawner scaling and scaled rewards."""

import random
import unittest

from game.config.settings import enemy_types
from game.systems.currency import CurrencyWallet
from game.systems.scaling import ScalingConfig, ScalingSystem
from game.systems.spawner import SpawnerSystem
from game.utils.large_number import LargeNumber


class SpawnerScalingTests(unittest.TestCase):
    def test_spawner_applies_active_time_and_difficulty_separately(self) -> None:
        scaling = ScalingSystem(ScalingConfig(
            time_step_seconds=10,
            time_health_multiplier=2,
            time_damage_multiplier=2,
            time_spawn_rate_multiplier=2,
            time_reward_multiplier=2,
            difficulty_health_multiplier=3,
            difficulty_damage_multiplier=3,
            difficulty_spawn_rate_multiplier=3,
            difficulty_reward_multiplier=3,
        ))
        spawner = SpawnerSystem(enemy_types, 2000, scaling=scaling, rng=random.Random(9))
        spawner.update(10)
        self.assertEqual(scaling.active_time_seconds, 10)
        spawner.increase_difficulty()
        self.assertEqual(scaling.active_time_seconds, 10)
        self.assertEqual(spawner.difficulty_level, 1)
        self.assertAlmostEqual(spawner.current_spawn_delay_ms, 2000 / 6)

        enemies = []
        spawner.spawn(0, 0, enemies)
        enemy = enemies[0]
        self.assertEqual(enemy.max_health, LargeNumber(60))
        self.assertEqual(enemy.damage, LargeNumber(60))
        self.assertEqual(enemy.reward_multiplier, LargeNumber(6))
        self.assertAlmostEqual((enemy.x**2 + enemy.y**2) ** 0.5, 3.0)

        spawner.reset()
        self.assertEqual(spawner.difficulty_level, 0)
        self.assertEqual(spawner.scaling.active_time_seconds, 0)
        enemies = []
        spawner.spawn(0, 0, enemies)
        self.assertEqual((enemies[0].x, enemies[0].y), (enemy.x, enemy.y))

    def test_kill_reward_uses_large_scaled_currency(self) -> None:
        class FixedRandom:
            def __init__(self, roll=0.99):
                self.roll = roll

            def random(self) -> float:
                return self.roll

            @staticmethod
            def randint(_low: int, _high: int) -> int:
                return 3

        wallet = CurrencyWallet()
        currency, amount = wallet.reward_for_kill(
            rng=FixedRandom(), reward_multiplier=LargeNumber("1e1000")
        )

        self.assertEqual(currency, "Copper")
        self.assertEqual(amount, LargeNumber("3e1000"))
        self.assertEqual(wallet.amounts["Copper"], LargeNumber("3e1000"))

    def test_extreme_luck_saturates_at_a_valid_probability(self) -> None:
        wallet = CurrencyWallet()

        class FixedRandom:
            def __init__(self, roll):
                self.roll = roll

            def random(self) -> float:
                return self.roll

            @staticmethod
            def randint(_low: int, _high: int) -> int:
                return 3

        currency, _ = wallet.reward_for_kill(
            rng=FixedRandom(0.49), luck=LargeNumber("1e10000")
        )
        self.assertEqual(currency, "Gold")
        currency, _ = wallet.reward_for_kill(
            rng=FixedRandom(0.51), luck=LargeNumber("1e10000")
        )
        self.assertEqual(currency, "Copper")


if __name__ == "__main__":
    unittest.main()
