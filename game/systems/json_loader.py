"""JSON asset loader for item definitions.

This module provides functions to load item definitions from JSON files
in the assets directory.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

# Assets directory is at game/assets/
ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"


def load_json_asset(filename: str) -> Any:
    """Load a JSON asset from the assets directory."""
    filepath = ASSETS_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Asset file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_weapons() -> list[dict[str, Any]]:
    """Load all weapon definitions from weapons.json."""
    data = load_json_asset("weapons.json")
    return data.get("weapons", [])


def load_armor() -> list[dict[str, Any]]:
    """Load all armor definitions from armor.json."""
    data = load_json_asset("armor.json")
    return data.get("armor", [])


def load_abilities() -> list[dict[str, Any]]:
    """Load all ability definitions from abilities.json."""
    data = load_json_asset("abilities.json")
    return data.get("abilities", [])


def load_relics() -> list[dict[str, Any]]:
    """Load all relic definitions from relics.json."""
    data = load_json_asset("relics.json")
    return data.get("relics", [])


def load_all_items() -> list[dict[str, Any]]:
    """Load all item definitions from all JSON files."""
    items = []
    items.extend(load_weapons())
    items.extend(load_armor())
    items.extend(load_abilities())
    items.extend(load_relics())
    return items


def create_item_catalog_from_json() -> list[dict[str, Any]]:
    """Create a complete item catalog from JSON definitions."""
    items = load_all_items()
    existing = {item.get("id") for item in items}
    items.extend(item for item in load_json_asset("items.json").get("items", [])
                 if item.get("id") not in existing)
    return items


def load_rarity_scaling() -> dict[str, Any]:
    """Load and validate data-driven item rarity stat multipliers."""
    data = load_json_asset("rarity_scaling.json")
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Unsupported rarity scaling asset version")
    multipliers = data.get("multipliers")
    expected_rarities = {
        "common", "uncommon", "rare", "epic", "legendary", "mythical", "ultimate"
    }
    if not isinstance(multipliers, dict) or set(multipliers) != expected_rarities:
        raise ValueError(
            "Rarity scaling must define exactly the supported rarities")
    normalized: dict[str, float] = {}
    for rarity, multiplier in multipliers.items():
        numeric_multiplier = _finite_number(multiplier)
        if numeric_multiplier is None or numeric_multiplier <= 0:
            raise ValueError(f"Invalid rarity multiplier for {rarity}")
        normalized[rarity] = numeric_multiplier
    if normalized["common"] != 1.0:
        raise ValueError("Common rarity multiplier must be 1")
    rarity_order = (
        "common", "uncommon", "rare", "epic", "legendary", "mythical", "ultimate"
    )
    if any(
        normalized[current] > normalized[next_rarity]
        for current, next_rarity in zip(rarity_order, rarity_order[1:])
    ):
        raise ValueError(
            "Rarity multipliers must not decrease at higher rarities")
    tier_growth = data.get("ultimate_tier_growth")
    numeric_tier_growth = _finite_number(tier_growth)
    if numeric_tier_growth is None or numeric_tier_growth < 1:
        raise ValueError("Ultimate tier growth must be finite and at least 1")
    return {
        "multipliers": normalized,
        "ultimate_tier_growth": numeric_tier_growth,
    }


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        numeric_value = float(value)
    except OverflowError:
        return None
    return numeric_value if math.isfinite(numeric_value) else None


def load_item_level_scaling() -> dict[str, Any]:
    """Load and validate additive per-level stat growth configuration."""
    data = load_json_asset("item_level_scaling.json")
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Unsupported item level scaling asset version")

    def numeric_mapping(field: str, *, nonnegative: bool) -> dict[str, float]:
        values = data.get(field, {})
        if not isinstance(values, dict):
            raise ValueError(f"Item level scaling {field} must be an object")
        normalized: dict[str, float] = {}
        for stat, value in values.items():
            numeric_value = _finite_number(value)
            if (
                not isinstance(stat, str)
                or not stat
                or numeric_value is None
                or (nonnegative and numeric_value < 0)
            ):
                raise ValueError(
                    f"Invalid item level scaling value for {stat!r}")
            normalized[stat] = numeric_value
        return normalized

    default_rate = data.get("default_addition_rate")
    numeric_default_rate = _finite_number(default_rate)
    if numeric_default_rate is None or numeric_default_rate < 0:
        raise ValueError(
            "Default item level addition rate must be finite and non-negative")
    return {
        "default_addition_rate": numeric_default_rate,
        "stat_addition_rates": numeric_mapping("stat_addition_rates", nonnegative=False),
        "minimum_values": numeric_mapping("minimum_values", nonnegative=True),
    }
