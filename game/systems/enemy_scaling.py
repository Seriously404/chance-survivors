"""Time-based and player-controlled enemy scaling."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import math
from typing import Any


@dataclass
class EnemyScaling:
    """Controls the run's challenge tier and scales newly spawned enemies."""

    threat_level: int = 0
    max_threat_level: int = 20

    def __post_init__(self) -> None:
        if not isinstance(self.threat_level, int) or isinstance(self.threat_level, bool):
            raise TypeError("threat_level must be an integer")
        if not isinstance(self.max_threat_level, int) or self.max_threat_level < 0:
            raise ValueError("max_threat_level must be a non-negative integer")
        self.threat_level = min(self.max_threat_level,
                                max(0, self.threat_level))

    def adjust_threat(self, amount: int) -> int:
        """Adjust threat by whole tiers, clamping it to the supported range."""
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise TypeError("threat adjustment must be an integer")
        self.threat_level = min(
            self.max_threat_level,
            max(0, self.threat_level + amount),
        )
        return self.threat_level

    def multiplier(self, elapsed_seconds: float) -> Decimal:
        """Return the health/reward multiplier for active time and threat."""
        if not isinstance(elapsed_seconds, (int, float)) or not math.isfinite(elapsed_seconds):
            raise ValueError("elapsed_seconds must be finite")
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds cannot be negative")
        elapsed_minutes = int(elapsed_seconds // 60)
        # Smooth exponential growth avoids a sudden tenfold health spike every
        # five minutes while still letting long runs reach large numbers.
        return Decimal("1.09") ** elapsed_minutes * Decimal("1.25") ** self.threat_level

    def scale_stats(self, stats: dict[str, Any], elapsed_seconds: float) -> dict[str, Any]:
        """Return a scaled copy; never mutate the shared enemy configuration."""
        result = deepcopy(stats)
        multiplier = self.multiplier(elapsed_seconds)
        result["max_health"] = max(
            1, int(Decimal(str(stats["max_health"])) * multiplier))
        damage_growth = Decimal(1) + multiplier.log10() * Decimal("0.12")
        result["damage"] = max(
            1, int(Decimal(str(stats["damage"])) * damage_growth))
        speed_growth = min(Decimal("1.5"), Decimal(
            1) + multiplier.log10() * Decimal("0.02"))
        result["speed"] = float(Decimal(str(stats["speed"])) * speed_growth)
        base_score_multiplier = Decimal(str(stats.get("score_multiplier", 1)))
        result["score_multiplier"] = max(
            1,
            int(
                (base_score_multiplier * multiplier).to_integral_value(
                    rounding=ROUND_CEILING
                )
            ),
        )
        return result

    def spawn_delay_ms(self, base_delay_ms: int, elapsed_seconds: float) -> int:
        """Increase spawn pressure gradually without allowing zero-delay spawns."""
        if not isinstance(base_delay_ms, int) or base_delay_ms <= 0:
            raise ValueError("base_delay_ms must be a positive integer")
        if not isinstance(elapsed_seconds, (int, float)) or not math.isfinite(elapsed_seconds):
            raise ValueError("elapsed_seconds must be finite")
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds cannot be negative")
        minutes = elapsed_seconds / 60.0
        multiplier = 1.0 + self.threat_level * \
            0.08 + max(0.0, minutes - 3.0) * 0.12
        return max(100, int(base_delay_ms / multiplier))
