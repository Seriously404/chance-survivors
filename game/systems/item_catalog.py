"""Validated, versioned item definition loading for data-driven catalogs."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
from collections.abc import Mapping
from typing import Any


ITEM_DEFINITIONS_PATH = Path(__file__).resolve(
).parents[2] / "assets" / "items.json"
ITEM_DEFINITIONS_VERSION = 1
SUPPORTED_ITEM_TYPES = frozenset({"weapon", "ability", "armor", "relic"})
SUPPORTED_RARITIES = frozenset(
    {"common", "uncommon", "rare", "epic", "legendary", "mythical", "ultimate"})
RARITY_COMBINATION_SLOTS = {
    "common": 1,
    "uncommon": 2,
    "rare": 3,
    "epic": 3,
    "legendary": 4,
    "mythical": 4,
    "ultimate": 5,
}
_STABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_PREFERENCE_LABELS = {
    "favored": "favored",
    "favorable": "favored",
    "preferred": "favored",
    "neutral": "neutral",
    "default": "neutral",
    "unfavored": "unfavored",
    "unfavorable": "unfavored",
    "disfavored": "unfavored",
}
_KNOWN_FIELDS = frozenset({
    "id", "name", "type", "rarity", "level", "stats", "tags", "behaviors",
    "combination_slots", "currency_preferences", "acquisition", "base", "is_base",
    "fusion_only",
})


def _stable_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _STABLE_ID.fullmatch(value):
        raise ValueError(
            f"{label} must be a non-empty stable identifier without whitespace")
    return value


def _unique_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(entry, str) or not entry.strip() for entry in value):
        raise ValueError(f"{label} must be a list of non-empty strings")
    normalized = [entry.strip() for entry in value]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} must not contain duplicates")
    return sorted(normalized)


def _json_value(value: Any, label: str) -> Any:
    """Validate and detach a JSON-compatible value, including finite floats."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} cannot contain NaN or infinity")
        return value
    if isinstance(value, list):
        return [_json_value(entry, f"{label}[]") for entry in value]
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) or not key for key in value):
            raise ValueError(f"{label} object keys must be non-empty strings")
        return {key: _json_value(value[key], f"{label}.{key}") for key in sorted(value)}
    raise ValueError(
        f"{label} contains unsupported value type {type(value).__name__}")


def _normalize_stats(value: Any, item_id: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Item {item_id!r} stats must be an object")
    stats: dict[str, Any] = {}
    for name in sorted(value):
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Item {item_id!r} stat names must be non-empty strings")
        stat_value = value[name]
        if isinstance(stat_value, (dict, list)) or stat_value is None:
            raise ValueError(
                f"Item {item_id!r} stat {name!r} must be a scalar value")
        stats[name.strip()] = _json_value(stat_value, f"Item {item_id}.{name}")
    if len(stats) != len(value):
        raise ValueError(
            f"Item {item_id!r} stat names must be unique after trimming")
    return stats


def _normalize_currency_preferences(value: Any, item_id: str) -> dict[str, str | int | float]:
    if not isinstance(value, Mapping):
        raise ValueError(
            f"Item {item_id!r} currency_preferences must be an object")
    result: dict[str, str | int | float] = {}
    for currency_id in sorted(value):
        _stable_id(currency_id, f"Item {item_id!r} currency id")
        preference = value[currency_id]
        if isinstance(preference, bool):
            raise ValueError(
                f"Item {item_id!r} currency preference must be a label or positive number")
        if isinstance(preference, str):
            normalized = _PREFERENCE_LABELS.get(preference.strip().lower())
            if normalized is None:
                raise ValueError(
                    f"Item {item_id!r} has unsupported preference for {currency_id!r}")
            result[currency_id] = normalized
        elif isinstance(preference, (int, float)):
            if not math.isfinite(preference) or preference <= 0:
                raise ValueError(
                    f"Item {item_id!r} currency preference multipliers must be positive and finite")
            result[currency_id] = preference
        else:
            raise ValueError(
                f"Item {item_id!r} currency preference must be a label or positive number")
    return result


def _normalize_definition(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"Item definition at index {index} must be an object")

    item_id = _stable_id(raw.get("id"), f"Item definition at index {index} id")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Item {item_id!r} needs a non-empty display name")

    item_type = raw.get("type")
    if not isinstance(item_type, str):
        raise ValueError(f"Item {item_id!r} has an unsupported item type")
    item_type = item_type.strip().lower()
    if item_type not in SUPPORTED_ITEM_TYPES:
        raise ValueError(
            f"Item {item_id!r} has unsupported type {item_type!r}")

    rarity = raw.get("rarity")
    if not isinstance(rarity, str):
        raise ValueError(f"Item {item_id!r} has an unsupported rarity")
    rarity = rarity.strip().lower()
    if rarity not in SUPPORTED_RARITIES:
        raise ValueError(f"Item {item_id!r} has unsupported rarity {rarity!r}")

    level = raw.get("level")
    if type(level) is not int or level < 1:
        raise ValueError(f"Item {item_id!r} level must be a positive integer")

    slots = raw.get("combination_slots")
    expected_slots = RARITY_COMBINATION_SLOTS[rarity]
    if type(slots) is not int or slots != expected_slots:
        raise ValueError(
            f"Item {item_id!r} must define {expected_slots} combination slots for {rarity} rarity"
        )

    base = raw.get("base", raw.get("is_base", False))
    if "base" in raw and "is_base" in raw and raw["base"] is not raw["is_base"]:
        raise ValueError(
            f"Item {item_id!r} has conflicting base and is_base flags")
    fusion_only = raw.get("fusion_only", False)
    if type(base) is not bool or type(fusion_only) is not bool:
        raise ValueError(
            f"Item {item_id!r} base and fusion_only flags must be booleans")

    tags = _unique_string_list(raw.get("tags", []), f"Item {item_id!r} tags")
    behaviors = _unique_string_list(
        raw.get("behaviors", []), f"Item {item_id!r} behaviors")
    stats = _normalize_stats(raw.get("stats"), item_id)

    currency_preferences = _normalize_currency_preferences(
        raw.get("currency_preferences", {}), item_id
    )
    acquisition = raw.get("acquisition", {})
    if not isinstance(acquisition, Mapping):
        raise ValueError(
            f"Item {item_id!r} acquisition metadata must be an object")
    normalized_acquisition = _json_value(
        acquisition, f"Item {item_id}.acquisition")

    definition: dict[str, Any] = {
        "id": item_id,
        "name": name.strip(),
        "type": item_type,
        "rarity": rarity,
        "level": level,
        "stats": stats,
        "tags": tags,
        "behaviors": behaviors,
        "combination_slots": slots,
        "currency_preferences": currency_preferences,
        "acquisition": normalized_acquisition,
        "base": base,
        "fusion_only": fusion_only,
    }
    # Preserve future item metadata while requiring it to remain JSON-safe.
    for key in sorted(set(raw) - _KNOWN_FIELDS):
        if not isinstance(key, str) or not key:
            raise ValueError(f"Item {item_id!r} has an invalid field name")
        definition[key] = _json_value(raw[key], f"Item {item_id}.{key}")
    return definition


def load_item_definitions(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load and normalize stable item definitions from a versioned JSON file.

    The loader does not create item instances or mutate definitions after
    loading. Definition order follows the asset file; mapping keys, tags, and
    behaviors are normalized deterministically.
    """
    catalog_path = Path(path) if path is not None else ITEM_DEFINITIONS_PATH
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(
            f"Could not load item definitions from {catalog_path}: {exc}") from exc
    if (
        not isinstance(raw, Mapping)
        or type(raw.get("version")) is not int
        or raw.get("version") != ITEM_DEFINITIONS_VERSION
    ):
        raise ValueError("Unsupported item definition catalog version")
    definitions = raw.get("items")
    if not isinstance(definitions, list):
        raise ValueError("Item definition catalog must contain an items list")

    normalized = [_normalize_definition(item, index)
                  for index, item in enumerate(definitions)]
    ids = [item["id"] for item in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("Item definition ids must be unique")
    return normalized
