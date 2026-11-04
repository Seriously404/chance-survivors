"""Regression tests for spawner edge cases."""

import math
import unittest
from unittest.mock import patch

from game.config.settings import enemy_types
from game.systems.spawner import SpawnerSystem


class SpawnerSpawnGuardTests(unittest.TestCase):
    def test_spawn_retries_when_random_direction_is_zero_vector(self) -> None:
        spawner = SpawnerSystem(enemy_types, spawn_delay_ms=0)
        enemies: list = []
        values = iter([0.0, 0.0, 1.0, 0.0])

        with patch("game.systems.spawner.random.uniform", side_effect=lambda a, b: next(values)):
            spawner.spawn(0.0, 0.0, enemies)

        self.assertEqual(len(enemies), 1)
        enemy = enemies[0]
        self.assertGreater(abs(enemy.x), 0.0)
        self.assertAlmostEqual(math.hypot(enemy.dx, enemy.dy), 1.0)
        self.assertFalse(math.isnan(enemy.angle))


if __name__ == "__main__":
    unittest.main()
