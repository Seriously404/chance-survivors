"""Headless regression tests for collision-driven kill rewards."""

import unittest

from game.config.settings import enemy_types
from game.entities.enemy import Enemy
from game.entities.projectile import Projectile
from game.systems.runtime_probe import RuntimeProbe


class CollisionRewardTests(unittest.TestCase):
    def test_overlapping_projectiles_award_one_kill_once(self) -> None:
        probe = RuntimeProbe()
        enemy = Enemy.create_from_type("basic", enemy_types["basic"], 0.0, 0.0)
        enemy.health = 1
        enemy.max_health = 1
        probe.enemies.append(enemy)
        probe.bullets.extend(
            [
                Projectile(x=0.0, y=0.0, damage=10),
                Projectile(x=0.0, y=0.0, damage=10),
            ]
        )
        reward_calls = 0
        reward_for_kill = probe.wallet.reward_for_kill

        def count_reward(*, luck: float = 0.0, reward_multiplier: int = 1):
            nonlocal reward_calls
            reward_calls += 1
            return reward_for_kill(luck=luck, reward_multiplier=reward_multiplier)

        probe.wallet.reward_for_kill = count_reward

        result = probe.execute({"action": "step", "dt": 0.01})

        self.assertEqual(result["killed"], 1)
        self.assertEqual(probe.score.total_score, 10)
        self.assertEqual(probe.progress.total_exp, 1)
        self.assertEqual(reward_calls, 1)
        self.assertEqual(probe.enemies, [])


if __name__ == "__main__":
    unittest.main()
