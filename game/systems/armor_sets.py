"""Pure logic for loading armor-set definitions and calculating their bonuses."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping


__all__ = ["load_armor_sets", "armor_set_bonuses", "armor_set_status"]


_PASSIVE_BONUS_STATS = (
    "defense",
    "health",
    "speed_pct",
    "luck",
    "damage_pct",
    "crit_chance",
    "score_bonus_pct",
    "elemental_dmg",
)
_SUPPORTED_STATS = frozenset(_PASSIVE_BONUS_STATS)
_SUPPORTED_THRESHOLDS = frozenset(range(2, 6))
_DEFAULT_ASSET_PATH = Path(__file__).resolve().parents[2] / "assets" / "armor_sets.json"


def _validate_armor_sets(data: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Armor sets must use version 1")
    sets = data.get("sets")
    if not isinstance(sets, list):
        raise ValueError("Armor sets must be a list")

    definitions: dict[str, dict[str, Any]] = {}
    for armor_set in sets:
        if not isinstance(armor_set, dict):
            raise ValueError("Each armor set must be an object")
        set_id = armor_set.get("id")
        name = armor_set.get("name")
        if not isinstance(set_id, str) or not set_id.strip():
            raise ValueError("Armor set IDs must be non-empty strings")
        if set_id != set_id.strip():
            raise ValueError("Armor set IDs cannot contain surrounding whitespace")
        if set_id in definitions:
            raise ValueError(f"Duplicate armor set ID: {set_id}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Armor set {set_id!r} must have a non-empty name")

        raw_bonuses = armor_set.get("bonuses")
        if not isinstance(raw_bonuses, dict):
            raise ValueError(f"Armor set {set_id!r} bonuses must be an object")
        bonuses: dict[int, dict[str, float]] = {}
        for raw_threshold, raw_stats in raw_bonuses.items():
            if (
                not isinstance(raw_threshold, str)
                or not raw_threshold.isdecimal()
                or str(int(raw_threshold)) != raw_threshold
            ):
                raise ValueError(f"Invalid threshold in armor set {set_id!r}")
            threshold = int(raw_threshold)
            if threshold not in _SUPPORTED_THRESHOLDS:
                raise ValueError(f"Unsupported threshold {raw_threshold!r} in armor set {set_id!r}")
            if not isinstance(raw_stats, dict):
                raise ValueError(f"Threshold {threshold} bonuses must be an object")

            stats: dict[str, float] = {}
            for stat, value in raw_stats.items():
                if stat not in _SUPPORTED_STATS:
                    raise ValueError(f"Unsupported armor-set bonus stat: {stat!r}")
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"Armor-set bonus {stat!r} must be a finite number")
                try:
                    numeric_value = float(value)
                except OverflowError as error:
                    raise ValueError(f"Armor-set bonus {stat!r} must be a finite number") from error
                if not math.isfinite(numeric_value):
                    raise ValueError(f"Armor-set bonus {stat!r} must be a finite number")
                stats[stat] = numeric_value
            bonuses[threshold] = stats

        definitions[set_id] = {"name": name, "bonuses": bonuses}
    return definitions


def load_armor_sets(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Load and validate armor-set definitions from the default asset or a given path."""
    asset_path = Path(path) if path is not None else _DEFAULT_ASSET_PATH
    try:
        data = json.loads(asset_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid armor-set JSON in {asset_path}") from error
    return _validate_armor_sets(data)


def _count_equipped_sets(
    equipped_armor: Iterable[Mapping[str, Any]],
    definitions: Mapping[str, Mapping[str, Any]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in equipped_armor:
        if not isinstance(item, Mapping):
            raise ValueError("Equipped armor items must be mappings")
        set_id = item.get("armor_set")
        if set_id is None:
            continue
        if not isinstance(set_id, str) or not set_id.strip():
            raise ValueError("Equipped armor set IDs must be non-empty strings")
        if set_id not in definitions:
            raise ValueError(f"Unsupported equipped armor set ID: {set_id!r}")
        counts[set_id] = counts.get(set_id, 0) + 1
    return counts


def armor_set_bonuses(
    equipped_armor: Iterable[Mapping[str, Any]],
    definitions: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, float]:
    """Sum armor-set bonuses for equipped pieces, loading default definitions if omitted."""
    validated_definitions = definitions if definitions is not None else load_armor_sets()
    counts = _count_equipped_sets(equipped_armor, validated_definitions)
    totals = {stat: 0.0 for stat in _PASSIVE_BONUS_STATS}
    for set_id, count in counts.items():
        bonuses = validated_definitions[set_id]["bonuses"]
        for threshold, stats in bonuses.items():
            if count >= threshold:
                for stat, value in stats.items():
                    totals[stat] += value
    return totals


def armor_set_status(
    equipped_armor: Iterable[Mapping[str, Any]],
    definitions: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return JSON-friendly status for each armor set with equipped pieces."""
    validated_definitions = definitions if definitions is not None else load_armor_sets()
    counts = _count_equipped_sets(equipped_armor, validated_definitions)
    status: list[dict[str, Any]] = []
    for set_id, definition in validated_definitions.items():
        pieces = counts.get(set_id, 0)
        if pieces == 0:
            continue
        active_bonuses = {
            str(threshold): dict(stats)
            for threshold, stats in definition["bonuses"].items()
            if pieces >= threshold
        }
        status.append(
            {
                "id": set_id,
                "name": definition["name"],
                "pieces": pieces,
                "active_bonuses": active_bonuses,
            }
        )
    return status
