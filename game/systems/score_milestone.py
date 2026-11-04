"""Finite score milestones for the game's practical infinity objective."""

from functools import lru_cache

from game.systems.numbers import LargeNumber


INFINITY_MILESTONE_SCORE = LargeNumber("1.7976931348623157e308")
KILL_SCORE_GROWTH = LargeNumber("1.05")


@lru_cache(maxsize=256, typed=True)
def kill_score_multiplier(eligible_kills: int) -> LargeNumber:
    """Return the multiplier for the next eligible kill, starting at one."""
    if type(eligible_kills) is not int or eligible_kills < 0:
        raise ValueError("Eligible kill count must be a non-negative integer")
    return KILL_SCORE_GROWTH ** eligible_kills


def score_for_kill(eligible_kills: int, enemy_multiplier: int) -> LargeNumber:
    """Score one eligible kill; enemy XP and currency are unaffected."""
    if type(enemy_multiplier) is not int or enemy_multiplier < 1:
        raise ValueError("Enemy score multiplier must be a positive integer")
    return LargeNumber(10) * enemy_multiplier * kill_score_multiplier(eligible_kills)


def has_reached_infinity_milestone(score: LargeNumber) -> bool:
    """Return whether a finite score reaches the practical infinity threshold."""
    if not isinstance(score, LargeNumber):
        raise TypeError("score must be a LargeNumber")
    return score >= INFINITY_MILESTONE_SCORE
