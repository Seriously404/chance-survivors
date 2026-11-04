"""Player experience progression backed by a data file.

All experience values now use LargeNumber to support extreme magnitudes without
precision loss or overflow at late-game levels.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from game.systems.numbers import LargeNumber

LEVEL_REQUIREMENTS_PATH = Path(__file__).resolve(
).parents[2] / "assets" / "level_upgrade_req.json"
# Fifty configured upgrades carry the player from level 1 through level 51.
# The final configured threshold is the large level-50-to-51 requirement.
MAX_LEVEL = 51


def load_level_requirements(path: Path = LEVEL_REQUIREMENTS_PATH) -> list[LargeNumber]:
    """Load exactly 50 positive XP requirements, one per level-up.

    Returns:
        List of LargeNumber values for XP requirements.
    """
    try:
        with path.open("r", encoding="utf-8") as file:
            raw: Any = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Could not load level XP requirements from {path}: {exc}") from exc

    requirements = raw.get("requirements") if isinstance(raw, dict) else raw
    if not isinstance(requirements, list) or len(requirements) != MAX_LEVEL - 1:
        raise ValueError(
            f"{path} must contain exactly {MAX_LEVEL - 1} XP requirements")
    if any(type(value) is not int or value <= 0 for value in requirements):
        raise ValueError(
            f"Every XP requirement in {path} must be a positive integer")
    return [LargeNumber(req) for req in requirements]


class PlayerProgress:
    """Level/XP state with LargeNumber support for extreme magnitudes."""

    def __init__(self, requirements: list[LargeNumber] | None = None) -> None:
        self.requirements = requirements if requirements is not None else load_level_requirements()
        if len(self.requirements) != MAX_LEVEL - 1:
            raise ValueError(
                f"Progression needs {MAX_LEVEL - 1} XP requirements")
        self.level = 1
        self.current_exp: LargeNumber = LargeNumber(0)
        self.total_exp: LargeNumber = LargeNumber(0)

    @property
    def exp_to_next_level(self) -> LargeNumber:
        """Get XP required to reach the next level."""
        if self.level >= MAX_LEVEL:
            return LargeNumber(0)
        return self.requirements[self.level - 1]

    def add_exp(self, amount: int | float | LargeNumber = 1) -> int:
        """Award XP and return how many levels were gained.

        Args:
            amount: XP amount to award. Can be int, float, or LargeNumber.

        Returns:
            Number of levels gained (0 if no levels gained or at max level).
        """
        amount = LargeNumber(amount)
        if amount.is_zero or self.level >= MAX_LEVEL:
            return 0
        self.total_exp = self.total_exp + amount
        self.current_exp = self.current_exp + amount
        levels_gained = 0
        while self.level < MAX_LEVEL and self.current_exp >= self.exp_to_next_level:
            self.current_exp = self.current_exp - self.exp_to_next_level
            self.level += 1
            levels_gained += 1
        if self.level >= MAX_LEVEL:
            # Keep overflow as current XP for total accounting, but there is no
            # active progress bar requirement at the cap.
            self.current_exp = LargeNumber(0)
        return levels_gained

    def reset(self) -> None:
        """Reset progression to initial state."""
        self.level = 1
        self.current_exp = LargeNumber(0)
        self.total_exp = LargeNumber(0)


def award_enemy_kill(
    progress: PlayerProgress,
    amount: int | float | LargeNumber = 1,
    multiplier: int | float | LargeNumber = 1,
) -> int:
    """Award an enemy's configured XP exactly once per kill.

    The caller should invoke this once for each enemy returned in the
    collision system's ``killed_enemies`` list, which contains each kill once.

    Returns:
        Number of levels gained.
    """
    scaled_amount = LargeNumber(amount) * LargeNumber(multiplier)
    if scaled_amount <= 0:
        raise ValueError("Enemy XP reward and multiplier must be positive")
    return progress.add_exp(scaled_amount)
