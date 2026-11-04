"""Regression tests for spawner edge cases."""

import math
import unittest
from unittest.mock import patch

from game.config.settings import enemy_types
from game.systems.spawner import EncounterDirector, SpawnerSystem


class SpawnerSpawnGuardTests(unittest.TestCase):
    def test_director_eases_pressure_and_limits_group_spawns(self):
        director = EncounterDirector()
        self.assertGreater(director.delay_ms(1000, 50, .1), director.delay_ms(1000, 0, 1))
        self.assertFalse(director.can_spawn(director.MAX_ENEMIES))
        from game.entities.enemy import Enemy
        enemies = [Enemy('swarm') for _ in range(59)]
        stats = {'swarm': {**enemy_types['basic'], 'spawn_group_count': 3}}
        spawner = SpawnerSystem(stats)
        spawner.spawn(0, 0, enemies, max_enemies=director.MAX_ENEMIES)
        self.assertEqual(len(enemies), director.MAX_ENEMIES)

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
