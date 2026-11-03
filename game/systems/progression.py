"""Player experience progression backed by a data file.

All experience values use Python integers so the late-game curve is not limited
by floating-point precision.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEVEL_REQUIREMENTS_PATH = Path(__file__).resolve().parents[2] / "assets" / "level_upgrade_req.json"
# Fifty configured upgrades carry the player from level 1 through level 51.
# The final configured threshold is the large level-50-to-51 requirement.
MAX_LEVEL = 51


def load_level_requirements(path: Path = LEVEL_REQUIREMENTS_PATH) -> list[int]:
    """Load exactly 50 positive integer XP requirements, one per level-up."""
    try:
        with path.open("r", encoding="utf-8") as file:
            raw: Any = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load level XP requirements from {path}: {exc}") from exc

    requirements = raw.get("requirements") if isinstance(raw, dict) else raw
    if not isinstance(requirements, list) or len(requirements) != MAX_LEVEL - 1:
        raise ValueError(f"{path} must contain exactly {MAX_LEVEL - 1} XP requirements")
    if any(type(value) is not int or value <= 0 for value in requirements):
        raise ValueError(f"Every XP requirement in {path} must be a positive integer")
    return requirements


class PlayerProgress:
    """Level/XP state. XP beyond a threshold carries into the next level."""

    def __init__(self, requirements: list[int] | None = None) -> None:
        self.requirements = requirements if requirements is not None else load_level_requirements()
        if len(self.requirements) != MAX_LEVEL - 1 or any(type(v) is not int or v <= 0 for v in self.requirements):
            raise ValueError(f"Progression needs {MAX_LEVEL - 1} positive integer requirements")
        self.level = 1
        self.current_exp = 0
        self.total_exp = 0

    @property
    def exp_to_next_level(self) -> int:
        if self.level >= MAX_LEVEL:
            return 0
        return self.requirements[self.level - 1]

    def add_exp(self, amount: int = 1) -> int:
        """Award XP and return how many levels were gained."""
        if type(amount) is not int or amount < 0:
            raise ValueError("XP award must be a non-negative integer")
        if amount == 0 or self.level >= MAX_LEVEL:
            return 0
        self.total_exp += amount
        self.current_exp += amount
        levels_gained = 0
        while self.level < MAX_LEVEL and self.current_exp >= self.exp_to_next_level:
            self.current_exp -= self.exp_to_next_level
            self.level += 1
            levels_gained += 1
        if self.level >= MAX_LEVEL:
            # Keep overflow as current XP for total accounting, but there is no
            # active progress bar requirement at the cap.
            self.current_exp = 0
        return levels_gained

    def reset(self) -> None:
        self.level = 1
        self.current_exp = 0
        self.total_exp = 0


def award_enemy_kill(progress: PlayerProgress) -> int:
    """Award the current placeholder kill reward (one XP) exactly per call.

    The caller should invoke this once for each enemy returned in the
    collision system's ``killed_enemies`` list, which contains each kill once.
    """
    return progress.add_exp(1)

