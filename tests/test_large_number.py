"""Regression tests for the large-number score primitive."""

import unittest

from game.systems.numbers import LargeNumber


class LargeNumberTests(unittest.TestCase):
    def test_addition_and_multiplication_preserve_extreme_scale(self) -> None:
        score = LargeNumber("1e50")
        score += LargeNumber("2.5e50")
        score = score * 1.2
        self.assertEqual(str(score), "4.2E+50")
        self.assertGreater(score, LargeNumber("1e50"))

    def test_higher_orders_compare_without_float_overflow(self) -> None:
        self.assertGreater(LargeNumber("1e309"), LargeNumber("1e308"))
        self.assertLess(LargeNumber("9.9e307"), LargeNumber("1e308"))

    def test_percent_scaling_uses_decimal_math(self) -> None:
        score = LargeNumber("1e24")
        scaled = score.scale_by_percent(25)
        self.assertEqual(str(scaled), "1.25E+24")


if __name__ == "__main__":
    unittest.main()
