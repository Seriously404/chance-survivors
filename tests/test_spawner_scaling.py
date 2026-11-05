"""Headless integration tests for spawner scaling and scaled rewards."""

import unittest
from unittest.mock import patch

from game.config.settings import enemy_types
from game.systems.currency import CurrencyWallet
from game.systems.enemy_scaling import EnemyScaling
from game.systems.spawner import SpawnerSystem
from game.systems.numbers import LargeNumber


class SpawnerScalingTests(unittest.TestCase):
    def test_spawner_applies_active_time_scaling_without_changing_roster(self) -> None:
        scaling = EnemyScaling()
        stats = {"max_health": 100, "damage": 100,
                 "speed": 1, "score_multiplier": 1}
        spawner = SpawnerSystem({"basic": stats}, 2000)
        spawner.spawn_delay_ms = scaling.spawn_delay_ms(2000, 600)
        self.assertLess(spawner.spawn_delay_ms, 2000)
        spawner.update(spawner.spawn_delay_ms / 1000)
        self.assertTrue(spawner.should_spawn())
        enemies = []
        with patch("game.systems.spawner.random.random", return_value=0), patch("game.systems.spawner.random.uniform", return_value=1):
            spawner.spawn(0, 0, enemies, elapsed_seconds=600, scaling=scaling)
        enemy = enemies[0]
        self.assertEqual(enemy.max_health, 370)
        self.assertGreater(enemy.damage, stats["damage"])
        self.assertEqual(enemy.score_multiplier, 4)
        self.assertEqual(enemy.currency_multiplier, 2)
        self.assertEqual(stats["max_health"], 100)
        spawner.reset()
        self.assertFalse(spawner.should_spawn())

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
            rng=FixedRandom(), multiplier=LargeNumber("1e1000")
        )

        self.assertEqual(currency, "Copper")
        self.assertEqual(amount, LargeNumber("3e1000"))
        self.assertEqual(wallet.amounts["Copper"], LargeNumber("3e1000"))

        currency, amount = wallet.reward_for_enemy(
            "Copper", 3, rng=FixedRandom(), multiplier=2)
        self.assertEqual((currency, amount), ("Copper", LargeNumber(6)))

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
