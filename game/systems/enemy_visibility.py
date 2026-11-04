"""Enemy visibility rules driven by enemy-definition metadata."""

from __future__ import annotations

import math
from typing import Any


def enemy_visibility_alpha(
    distance: float,
    definition: dict[str, Any],
) -> int:
    """Return sprite opacity, revealing stealth enemies as they approach."""
    if not isinstance(distance, (int, float)) or not math.isfinite(distance) or distance < 0:
        raise ValueError("distance must be a finite non-negative number")

    if "reveal_distance" not in definition:
        return 255

    reveal_distance = definition["reveal_distance"]
    hidden_alpha = definition.get("stealth_alpha", 35)
    if (
        isinstance(reveal_distance, bool)
        or not isinstance(reveal_distance, (int, float))
        or not math.isfinite(reveal_distance)
        or reveal_distance <= 0
    ):
        raise ValueError("reveal_distance must be positive and finite")
    if type(hidden_alpha) is not int or not 0 <= hidden_alpha <= 255:
        raise ValueError("stealth_alpha must be an integer from 0 to 255")

    visibility = max(0.0, min(1.0, 1.0 - distance / reveal_distance))
    return round(hidden_alpha + (255 - hidden_alpha) * visibility)
