"""Headless regression tests for collision-driven kill rewards."""

import unittest

from game.config.settings import enemy_types
from game.entities.enemy import Enemy
from game.entities.projectile import Projectile
from game.systems.enemy_scaling import EnemyScaling
from game.systems.numbers import LargeNumber
from game.systems.runtime_probe import RuntimeProbe
from game.systems.score_milestone import (
    has_reached_infinity_milestone, kill_score_multiplier, score_for_kill,
)
from game.systems.quests import QuestManager


class CollisionRewardTests(unittest.TestCase):
    def test_kill_multiplier_is_progress_based_and_persists(self) -> None:
        quests = QuestManager()
        self.assertEqual(score_for_kill(quests.kills_total, 1), 10)
        quests.register_kill('basic')
        restored = QuestManager.from_save_state(quests.to_save_state())
        self.assertEqual(kill_score_multiplier(restored.kills_total), LargeNumber('1.05'))
        self.assertEqual(score_for_kill(restored.kills_total, 2), 21)
        with self.assertRaises(ValueError):
            kill_score_multiplier(-1)

    def test_score_can_reach_milestone_from_kills_alone(self) -> None:
        # Geometric series for 14,500 baseline enemies, no enemy or quest bonus.
        score = LargeNumber(10) * (kill_score_multiplier(14500) - 1) / LargeNumber('0.05')
        self.assertTrue(has_reached_infinity_milestone(score))

    def test_runtime_probe_counts_only_eligible_kills(self) -> None:
        probe = RuntimeProbe()
        for eligible in (True, False, True):
            enemy = Enemy.create_from_type('basic', enemy_types['basic'], 0, 0)
            enemy.health = enemy.max_health = 1
            enemy.reward_eligible = eligible
            probe.enemies.append(enemy)
            probe.bullets.append(Projectile(x=0, y=0, damage=10))
            probe.execute({'action': 'step', 'dt': 0.01})
        self.assertEqual(probe.eligible_kills, 2)
        self.assertEqual(probe.score, LargeNumber('20.5'))

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
        reward_for_enemy = probe.wallet.reward_for_enemy

        def count_reward(
            currency: str,
            amount: int,
            *,
            luck: float = 0.0,
            multiplier: int = 1,
        ):
            nonlocal reward_calls
            reward_calls += 1
            return reward_for_enemy(
                currency,
                amount,
                luck=luck,
                multiplier=multiplier,
            )

        probe.wallet.reward_for_enemy = count_reward

        result = probe.execute({"action": "step", "dt": 0.01})

        self.assertEqual(result["killed"], 1)
        self.assertEqual(probe.score, 10)
        self.assertEqual(probe.progress.total_exp, 10)
        self.assertGreaterEqual(probe.wallet.get("Copper"), 5)
        self.assertEqual(reward_calls, 1)
        self.assertEqual(probe.enemies, [])

    def test_scaled_kill_increases_score_currency_and_xp(self) -> None:
        probe = RuntimeProbe()
        scaled_stats = EnemyScaling(threat_level=1).scale_stats(
            enemy_types["basic"], 0
        )
        enemy = Enemy.create_from_type("basic", scaled_stats, 0.0, 0.0)
        enemy.health = 1
        enemy.max_health = 1
        probe.enemies.append(enemy)
        probe.bullets.append(Projectile(x=0.0, y=0.0, damage=10))

        result = probe.execute({"action": "step", "dt": 0.01})

        self.assertEqual(result["killed"], 1)
        self.assertEqual(enemy.score_multiplier, 2)
        self.assertEqual(probe.score, LargeNumber(20))
        self.assertGreaterEqual(probe.wallet.get("Copper"), LargeNumber(10))
        self.assertEqual(probe.progress.total_exp, LargeNumber(20))


if __name__ == "__main__":
    unittest.main()
