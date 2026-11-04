"""Tests for the finite infinity-score completion milestone."""

import unittest

from game.systems.numbers import LargeNumber
from game.systems.score_milestone import (
    INFINITY_MILESTONE_SCORE,
    has_reached_infinity_milestone,
)


class ScoreMilestoneTests(unittest.TestCase):
    def test_threshold_is_not_reported_as_reached_before_boundary(self) -> None:
        self.assertFalse(
            has_reached_infinity_milestone(
                INFINITY_MILESTONE_SCORE - LargeNumber("1e290")
            )
        )

    def test_threshold_and_larger_finite_scores_reach_milestone(self) -> None:
        self.assertTrue(has_reached_infinity_milestone(
            INFINITY_MILESTONE_SCORE))
        self.assertTrue(
            has_reached_infinity_milestone(
                INFINITY_MILESTONE_SCORE + LargeNumber("1e290")
            )
        )
        self.assertTrue(has_reached_infinity_milestone(LargeNumber("1e1000")))

    def test_milestone_requires_large_number(self) -> None:
        with self.assertRaisesRegex(TypeError, "LargeNumber"):
            has_reached_infinity_milestone(10)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
