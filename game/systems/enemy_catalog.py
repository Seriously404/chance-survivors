"""Build the runtime enemy roster from legacy stats and JSON definitions."""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from game.systems.game_definitions import load_enemies


_ADDITIONAL_SPAWN_WEIGHTS = {
    "fast": 3.0,
    "tank": 1.0,
    "shooter": 1.0,
    "swarm": 4.0,
    "boss": 0.05,
    "stealth": 0.8,
    "elemental-fire": 0.5,
    "elemental-frost": 0.5,
    "elemental-shadow": 0.5,
    "elemental-light": 0.5,
    "elemental-nature": 0.5,
    "elemental-arcane": 0.5,
}

_ADDITIONAL_COLORS = {
    "fast": (235, 145, 70),
    "tank": (130, 130, 145),
    "shooter": (205, 90, 90),
    "swarm": (210, 160, 50),
    "boss": (165, 40, 55),
    "stealth": (105, 100, 130),
    "elemental-fire": (245, 95, 50),
    "elemental-frost": (100, 195, 245),
    "elemental-shadow": (90, 60, 135),
    "elemental-light": (250, 230, 110),
    "elemental-nature": (80, 180, 90),
    "elemental-arcane": (175, 105, 240),
}


def build_enemy_roster(
    base_types: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return a runtime roster retaining legacy types and adding asset enemies."""
    roster = deepcopy(base_types)
    for definition in load_enemies():
        enemy_id = definition.get("id")
        if not isinstance(enemy_id, str) or not enemy_id:
            continue
        if enemy_id in roster:
            for key in (
                "special_ability",
                "summon_interval_seconds",
                "summon_count",
                "max_minions",
            ):
                if key in definition:
                    roster[enemy_id].setdefault(key, definition[key])
            continue

        try:
            weight = float(
                definition.get(
                    "spawn_weight",
                    _ADDITIONAL_SPAWN_WEIGHTS.get(enemy_id, 1.0),
                )
            )
            stats = {
                **definition,
                "max_health": int(definition["max_health"]),
                "damage": int(definition["damage"]),
                "speed": float(definition["speed"]),
                "turning_speed": float(definition["turning_speed"]),
                "score_multiplier": int(definition.get("score_multiplier", 1)),
                "size": int(definition.get("size", 52 if enemy_id == "boss" else 30)),
                "weight": weight,
                "color": _ADDITIONAL_COLORS.get(enemy_id, (220, 60, 60)),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid enemy definition for {enemy_id!r}") from exc

        numeric_values = (
            stats["speed"],
            stats["turning_speed"],
            stats["weight"],
        )
        if (
            stats["max_health"] <= 0
            or stats["damage"] <= 0
            or stats["score_multiplier"] <= 0
            or stats["size"] <= 0
            or any(not math.isfinite(value) or value <= 0 for value in numeric_values)
        ):
            raise ValueError(f"Enemy definition {enemy_id!r} has invalid runtime stats")
        roster[enemy_id] = stats
    if "swarm" in roster:
        minion_stats = deepcopy(roster["swarm"])
        minion_stats.update(
            id="necromancer_minion",
            name="Necromancer Minion",
            max_health=4,
            damage=2,
            speed=1.5,
            turning_speed=1.2,
            score_multiplier=1,
            size=18,
            weight=0.0,
            reward_eligible=False,
            summoned_only=True,
            color=(125, 75, 135),
        )
        roster["necromancer_minion"] = minion_stats
    return roster
