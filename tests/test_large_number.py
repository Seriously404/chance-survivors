<<<<<<< HEAD
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
=======
"""Headless tests for arbitrary-magnitude numeric operations."""

import unittest

from game.utils.large_number import LargeNumber
from game.systems.scoring import RunScore


class LargeNumberTests(unittest.TestCase):
    def test_parses_and_orders_values_beyond_float_range(self) -> None:
        huge = LargeNumber("9.5e100000000000000000000")
        larger = LargeNumber("1e100000000000000000001")
        tiny = LargeNumber("1e-100000000000000000000")

        self.assertGreater(larger, huge)
        self.assertGreater(huge, 0)
        self.assertGreater(0, -huge)
        self.assertLess(tiny, LargeNumber("1e-99999999999999999999"))
        self.assertEqual(huge.exponent, 100000000000000000000)

    def test_arithmetic_normalizes_and_handles_signs(self) -> None:
        self.assertEqual(LargeNumber("1e5000") + LargeNumber("2e5000"), "3e+5000")
        self.assertEqual(LargeNumber("1e5000") - LargeNumber("1e5000"), 0)
        self.assertEqual(LargeNumber("-2.5e900") * LargeNumber("4e100"), "-1e+1001")
        self.assertEqual(LargeNumber("-1e900") / LargeNumber("2e100"), "-5e+799")
        self.assertEqual(LargeNumber("-2") ** 3, -8)
        self.assertEqual(LargeNumber("2") ** -3, "1.25e-1")

    def test_addition_retains_small_terms_when_precision_allows(self) -> None:
        value = LargeNumber("1e20") + LargeNumber("1")

        self.assertEqual(value.exponent, 20)
        self.assertEqual(value.significand, LargeNumber("1.00000000000000000001").significand)

    def test_versioned_json_round_trip(self) -> None:
        original = LargeNumber("-1.234567890123456789e12345678901234567890")

        self.assertEqual(LargeNumber.from_json(original.to_json()), original)
        self.assertEqual(LargeNumber.from_dict(LargeNumber(0).to_dict()), 0)

    def test_display_format_handles_plain_values_and_rounding_rollover(self) -> None:
        self.assertEqual(str(LargeNumber("1.25")), "1.25")
        self.assertEqual(str(LargeNumber(10)), "10")
        self.assertEqual(LargeNumber("9.99e100").format_scientific(1), "1e+101")

    def test_run_score_applies_bonus_once_and_restores(self) -> None:
        score = RunScore("25")
        score.award("1e1000")
        score.award(100)

        self.assertEqual(score.base_score, LargeNumber("1e1000"))
        self.assertEqual(score.total_score, LargeNumber("1.25e1000"))
        restored = RunScore.from_dict(score.to_dict())
        self.assertEqual(restored.total_score, score.total_score)
        self.assertEqual(restored.snapshot()["final_score"], "1.25e+1000")

    def test_rejects_invalid_values_and_unsafe_float_conversion(self) -> None:
        for literal in ("NaN", "Infinity", "1e", "not a number"):
            with self.subTest(literal=literal), self.assertRaises(ValueError):
                LargeNumber(literal)
        with self.assertRaises(OverflowError):
            LargeNumber("1e1000").to_float()
        with self.assertRaises(OverflowError):
            LargeNumber("1e-1000").to_float()
        with self.assertRaises(ZeroDivisionError):
            LargeNumber(1) / 0
>>>>>>> birch/projectile-collision-effects


if __name__ == "__main__":
    unittest.main()
