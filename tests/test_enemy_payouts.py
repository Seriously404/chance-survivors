"""Tests for data-driven enemy currency and experience rewards."""

import unittest

from game.config.settings import enemy_types
from game.entities.enemy import Enemy
from game.systems.currency import CurrencyWallet
from game.systems.numbers import LargeNumber
from game.systems.progression import PlayerProgress, award_enemy_kill


class FixedRandom:
    def __init__(self, value: float) -> None:
        self.value = value

    def random(self) -> float:
        return self.value


class EnemyPayoutTests(unittest.TestCase):
    def test_live_enemy_types_receive_data_defined_rewards(self) -> None:
        expected = {
            "basic": ("copper", 5, 10),
            "swift": ("copper", 8, 12),
            "brute": ("copper", 20, 30),
            "ranged": ("silver", 15, 18),
            "necromancer": ("silver", 25, 35),
            "shadow": ("dark_matter", 20, 28),
        }

        for enemy_type, reward in expected.items():
            with self.subTest(enemy_type=enemy_type):
                enemy = Enemy.create_from_type(
                    enemy_type, enemy_types[enemy_type], 0.0, 0.0
                )
                self.assertEqual(
                    (enemy.currency_drop, enemy.currency_amount, enemy.xp_reward),
                    reward,
                )

    def test_configured_currency_and_xp_are_awarded(self) -> None:
        wallet = CurrencyWallet()
        progress = PlayerProgress()
        currency, amount = wallet.reward_for_enemy(
            "dark_matter",
            20,
            rng=FixedRandom(1.0),
            multiplier=3,
        )
        award_enemy_kill(progress, 28, multiplier=3)

        self.assertEqual(currency, "Dark Matter")
        self.assertEqual(amount, LargeNumber(60))
        self.assertEqual(wallet.get("dark_matter"), LargeNumber(60))
        self.assertEqual(wallet.get("Dark Matter"), LargeNumber(60))
        self.assertEqual(progress.total_exp, LargeNumber(84))

    def test_luck_increases_the_chance_of_a_configured_bonus_drop(self) -> None:
        unlucky_wallet = CurrencyWallet()
        lucky_wallet = CurrencyWallet()

        _, unlucky_amount = unlucky_wallet.reward_for_enemy(
            "copper", 5, rng=FixedRandom(0.5), luck=0
        )
        _, lucky_amount = lucky_wallet.reward_for_enemy(
            "copper", 5, rng=FixedRandom(0.5), luck=100
        )

        self.assertEqual(unlucky_amount, LargeNumber(5))
        self.assertEqual(lucky_amount, LargeNumber(10))

    def test_unknown_reward_currency_is_rejected(self) -> None:
        wallet = CurrencyWallet()
        with self.assertRaisesRegex(ValueError, "Unknown enemy reward currency"):
            wallet.reward_for_enemy("unobtainium", 1, rng=FixedRandom(1.0))

    def test_currency_aliases_remain_compatible_with_bazaar(self) -> None:
        wallet = CurrencyWallet()
        wallet.add("gold", LargeNumber(100))

        self.assertEqual(wallet.get("Gold"), LargeNumber(100))
        self.assertTrue(wallet.spend("Gold", LargeNumber(25)))
        self.assertEqual(wallet.get("gold"), LargeNumber(75))


if __name__ == "__main__":
    unittest.main()
