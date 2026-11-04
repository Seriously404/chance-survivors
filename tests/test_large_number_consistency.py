"""Tests for the large-number consistent currency and progression systems."""

import unittest
from game.systems.currency import CurrencyWallet
from game.systems.progression import PlayerProgress, award_enemy_kill
from game.systems.numbers import LargeNumber


class TestCurrencyWallet(unittest.TestCase):
    """Test cases for CurrencyWallet with LargeNumber support."""

    def test_normal_kills_can_also_award_gold(self):
        class FixedRandom:
            def random(self): return 0.1
            def randint(self, low, high): return low
        wallet = CurrencyWallet()
        self.assertEqual(wallet.gold_bonus_for_kill(FixedRandom()), 2)
        self.assertEqual(wallet.get("Gold"), 2)

    def test_initial_balance(self):
        """Wallet starts with zero balance for all currencies."""
        wallet = CurrencyWallet()
        self.assertEqual(wallet.get("Copper"), LargeNumber(0))
        self.assertEqual(wallet.get("Gold"), LargeNumber(0))

    def test_reward_for_kill_copper(self):
        """Reward can award copper currency."""
        wallet = CurrencyWallet()
        currency, amount = wallet.reward_for_kill(luck=0.0)
        self.assertIn(currency, ("Copper", "Gold"))
        self.assertIsInstance(amount, LargeNumber)
        self.assertGreater(amount, 0)

    def test_spend_currency(self):
        """Can spend currency if balance exists."""
        wallet = CurrencyWallet()
        wallet.add("Copper", LargeNumber(10))
        self.assertTrue(wallet.spend("Copper", LargeNumber(5)))
        self.assertEqual(wallet.get("Copper"), LargeNumber(5))

    def test_spend_insufficient_balance(self):
        """Cannot spend more than available balance."""
        wallet = CurrencyWallet()
        wallet.add("Copper", LargeNumber(5))
        self.assertFalse(wallet.spend("Copper", LargeNumber(10)))
        self.assertEqual(wallet.get("Copper"), LargeNumber(5))

    def test_small_spend_remains_visible_at_infinity_milestone(self):
        wallet = CurrencyWallet()
        wallet.add("Copper", LargeNumber("1e308"))
        self.assertTrue(wallet.spend("Copper", LargeNumber(1)))
        self.assertEqual(wallet.get("Copper") + LargeNumber(1),
                         LargeNumber("1e308"))
        self.assertLess(wallet.get("Copper"), LargeNumber("1e308"))

    def test_add_currency(self):
        """Can add currency to wallet."""
        wallet = CurrencyWallet()
        wallet.add("Copper", LargeNumber(10))
        wallet.add("Copper", LargeNumber(5))
        self.assertEqual(wallet.get("Copper"), LargeNumber(15))

    def test_notification_format(self):
        """Notifications use formatted LargeNumber display."""
        from game.systems.currency import CurrencyNotifications
        notifications = CurrencyNotifications(lifetime=1.0)
        notifications.add("Gold", LargeNumber(1234567))
        self.assertEqual(len(notifications.items), 1)
        # LargeNumber formats large numbers in scientific notation
        self.assertIn("Gold", notifications.items[0]["text"])
        self.assertIn("+", notifications.items[0]["text"])


class TestPlayerProgress(unittest.TestCase):
    """Test cases for PlayerProgress with LargeNumber support."""

    def test_initial_state(self):
        """Progression starts at level 1 with zero XP."""
        progress = PlayerProgress()
        self.assertEqual(progress.level, 1)
        self.assertEqual(progress.current_exp, LargeNumber(0))
        self.assertEqual(progress.total_exp, LargeNumber(0))

    def test_add_exp(self):
        """Can award XP and track levels."""
        progress = PlayerProgress()
        levels_gained = progress.add_exp(100)
        self.assertGreaterEqual(levels_gained, 0)
        self.assertGreater(progress.total_exp, LargeNumber(0))

    def test_award_enemy_kill(self):
        """award_enemy_kill awards XP correctly."""
        progress = PlayerProgress()
        levels_gained = award_enemy_kill(progress)
        self.assertEqual(levels_gained, 0)  # 1 XP typically doesn't level up
        self.assertEqual(progress.current_exp, LargeNumber(1))

    def test_reset(self):
        """Can reset progression to initial state."""
        progress = PlayerProgress()
        progress.add_exp(1000)
        progress.reset()
        self.assertEqual(progress.level, 1)
        self.assertEqual(progress.current_exp, LargeNumber(0))
        self.assertEqual(progress.total_exp, LargeNumber(0))

    def test_large_xp_values(self):
        """LargeNumber supports extreme XP values without precision loss."""
        progress = PlayerProgress()
        huge_xp = LargeNumber("1.797e308")
        progress.add_exp(huge_xp)
        self.assertEqual(progress.total_exp, huge_xp)
        self.assertTrue(progress.total_exp > LargeNumber(1000000))


class TestLargeNumberIntegration(unittest.TestCase):
    """Test integration of LargeNumber across systems."""

    def test_currency_and_progression_together(self):
        """Currency and progression systems work together with LargeNumber."""
        wallet = CurrencyWallet()
        progress = PlayerProgress()

        # Simulate multiple kills
        for _ in range(10):
            wallet.reward_for_kill(luck=5.0)
            award_enemy_kill(progress)

        # Both systems should have LargeNumber values
        copper = wallet.get("Copper")
        gold = wallet.get("Gold")
        self.assertIsInstance(copper, LargeNumber)
        self.assertIsInstance(gold, LargeNumber)
        self.assertIsInstance(progress.current_exp, LargeNumber)


if __name__ == "__main__":
    unittest.main()
