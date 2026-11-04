"""Finite score milestones for the game's practical infinity objective."""

from game.systems.numbers import LargeNumber


INFINITY_MILESTONE_SCORE = LargeNumber("1.7976931348623157e308")


def has_reached_infinity_milestone(score: LargeNumber) -> bool:
    """Return whether a finite score reaches the practical infinity threshold."""
    if not isinstance(score, LargeNumber):
        raise TypeError("score must be a LargeNumber")
    return score >= INFINITY_MILESTONE_SCORE
