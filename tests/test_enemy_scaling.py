"""Tests for time-based and player-controlled enemy scaling."""

import unittest

from game.config.settings import enemy_types
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.collision import CollisionSystem
from game.systems.enemy_scaling import EnemyScaling
from game.systems.spawner import SpawnerSystem


class EnemyScalingTests(unittest.TestCase):
    def test_threat_adjustment_clamps_to_supported_range(self) -> None:
        scaling = EnemyScaling()
        self.assertEqual(scaling.adjust_threat(-1), 0)
        self.assertEqual(scaling.adjust_threat(3), 3)
        self.assertEqual(scaling.adjust_threat(100), scaling.max_threat_level)

    def test_time_and_threat_scale_health_and_rewards_without_mutating_config(self) -> None:
        scaling = EnemyScaling(threat_level=4)
        base_stats = enemy_types["basic"]
        scaled = scaling.scale_stats(base_stats, 3600)

        self.assertGreater(scaled["max_health"], base_stats["max_health"])
        self.assertGreater(scaled["damage"], base_stats["damage"])
        self.assertGreater(scaled["score_multiplier"], 1)
        self.assertEqual(base_stats["max_health"], 10)

    def test_scaling_preserves_base_score_multiplier_and_scales_it(self) -> None:
        base_stats = {**enemy_types["basic"], "score_multiplier": 2}
        unscaled = EnemyScaling().scale_stats(base_stats, 0)
        scaled = EnemyScaling(threat_level=1).scale_stats(base_stats, 0)

        self.assertEqual(unscaled["score_multiplier"], base_stats["score_multiplier"])
        self.assertEqual(scaled["score_multiplier"], 3)

    def test_spawn_delay_has_a_positive_floor(self) -> None:
        scaling = EnemyScaling(threat_level=20)
        self.assertLess(scaling.spawn_delay_ms(2000, 3600), 2000)
        self.assertEqual(scaling.spawn_delay_ms(2000, 10_000_000), 250)

    def test_spawner_creates_scaled_enemy_instances(self) -> None:
        scaling = EnemyScaling(threat_level=2)
        spawner = SpawnerSystem({"basic": enemy_types["basic"]})
        enemies = []
        spawner.spawn(0.0, 0.0, enemies, elapsed_seconds=600, scaling=scaling)

        self.assertEqual(len(enemies), 1)
        self.assertGreater(enemies[0].max_health, enemy_types["basic"]["max_health"])
        self.assertGreater(enemies[0].score_multiplier, 1)
        self.assertGreater(enemies[0].damage, 0)

    def test_scaled_enemy_damage_reaches_player_collision(self) -> None:
        scaling = EnemyScaling(threat_level=10)
        scaled_stats = scaling.scale_stats(enemy_types["basic"], 3600)
        enemy = Enemy.create_from_type("basic", scaled_stats, 0.0, 0.0)
        player = Player(health=100, max_health=100)

        CollisionSystem(200).check_enemy_player_collisions(
            [enemy],
            player,
            enemy_types,
        )

        self.assertEqual(player.health, 100 - scaled_stats["damage"])


if __name__ == "__main__":
    unittest.main()
