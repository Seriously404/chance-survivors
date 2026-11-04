"""One score pipeline for base points, percentage bonuses, and final score."""

from __future__ import annotations

from game.utils.large_number import LargeNumber


class RunScore:
    """Tracks base score and applies additive percentage bonuses once.

    Calculation order is ``base * (100 + bonus_percent) / 100``. The final
    score is therefore the value used for ranking, while base and bonus score
    remain available for UI breakdowns and saved run records.
    """

    def __init__(self, bonus_percent: LargeNumber | int | float | str = 0) -> None:
        self.base_score = LargeNumber(0)
        self.set_bonus_percent(bonus_percent)

    @property
    def bonus_score(self) -> LargeNumber:
        return self.base_score * self.bonus_percent / 100

    @property
    def total_score(self) -> LargeNumber:
        return self.base_score + self.bonus_score

    def award(self, points: LargeNumber | int | float | str) -> None:
        amount = LargeNumber(points)
        if amount < 0:
            raise ValueError("Score awards must be non-negative")
        self.base_score += amount

    def set_bonus_percent(self, bonus_percent: LargeNumber | int | float | str) -> None:
        """Replace the current sum of percentage bonuses."""
        value = LargeNumber(bonus_percent)
        if value < 0:
            raise ValueError("Score percentage bonus must be non-negative")
        self.bonus_percent = value

    def snapshot(self) -> dict[str, str]:
        """Return display/API-friendly decimal strings for all score components."""
        return {
            "base_score": str(self.base_score),
            "bonus_score": str(self.bonus_score),
            "final_score": str(self.total_score),
        }

    def to_dict(self) -> dict[str, object]:
        """Return exact, versioned LargeNumber records for persistence."""
        return {
            "version": 1,
            "base_score": self.base_score.to_dict(),
            "bonus_percent": self.bonus_percent.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RunScore:
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("Unsupported run score serialization version")
        base = LargeNumber.from_dict(data.get("base_score"))
        bonus = LargeNumber.from_dict(data.get("bonus_percent"))
        if base < 0 or bonus < 0:
            raise ValueError("Serialized score and bonus must be non-negative")
        result = cls(bonus)
        result.base_score = base
        return result
