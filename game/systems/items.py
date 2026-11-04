"""Starter item catalog and stat aggregation helpers."""

from __future__ import annotations

<<<<<<< HEAD
from copy import deepcopy
import math
from typing import Any

from game.systems.inventory import ARMOR_EQUIPMENT_SLOTS, Inventory, _item
from game.systems.json_loader import create_item_catalog_from_json
from game.systems.json_loader import load_item_level_scaling, load_rarity_scaling
from game.systems.armor_sets import (
    armor_set_bonuses as calculate_armor_set_bonuses,
    armor_set_status as calculate_armor_set_status,
    load_armor_sets,
)


_RARITY_SCALING = load_rarity_scaling()
_ARMOR_SETS = load_armor_sets()
_ITEM_LEVEL_SCALING = load_item_level_scaling()


def create_item_catalog() -> list[dict[str, Any]]:
    """Return fresh starter/test items suitable for inventory or Bazaar spawns."""
    # Load items from JSON definitions
    json_items = create_item_catalog_from_json()

    # Convert JSON items to inventory format
    items = []
    for item in json_items:
        if item.get("type") == "armor":
            armor_slot = item.get("armor_slot")
            if armor_slot is not None and (
                not isinstance(armor_slot, str)
                or armor_slot not in ARMOR_EQUIPMENT_SLOTS
            ):
                raise ValueError(f"Unsupported armor slot on item {item.get('id')!r}")
            armor_set = item.get("armor_set")
            if armor_set is not None:
                if (
                    not isinstance(armor_set, str)
                    or not armor_set.strip()
                    or armor_set not in _ARMOR_SETS
                ):
                    raise ValueError(f"Unsupported armor set on item {item.get('id')!r}")
                if armor_slot is None:
                    raise ValueError(
                        f"Armor set item {item.get('id')!r} must define an armor slot"
                    )
        inventory_item = _item(
            item.get("id", "unknown"),
            item.get("name", "Unknown Item"),
            item.get("type", "misc"),
            item.get("rarity", "common"),
            item.get("level", 1),
            deepcopy(item.get("stats", {}))
        )
        if "tags" in item:
            inventory_item["tags"] = deepcopy(item["tags"])
        for metadata_key in ("armor_set", "armor_slot"):
            if metadata_key in item:
                inventory_item[metadata_key] = item[metadata_key]
        items.append(inventory_item)

    return items
=======
from typing import Any

from game.systems.combinations import CombinationEngine
from game.systems.inventory import Inventory, _item
from game.systems.item_catalog import load_item_definitions
from game.utils.large_number import LargeNumber


_COMBINATION_ENGINE = CombinationEngine()
MAX_PLAYER_SPEED_MULTIPLIER = 100.0
MIN_PLAYER_SPEED_MULTIPLIER = 0.1


def create_item_catalog() -> list[dict[str, Any]]:
    """Return fresh item instances built from the validated asset catalog."""
    catalog = []
    for definition in load_item_definitions():
        item = _item(
            definition["id"], definition["name"], definition["type"],
            definition["rarity"], definition["level"], dict(definition["stats"]),
        )
        item.update({
            "definition_version": 1,
            "combination_slots": definition["combination_slots"],
            "tags": list(definition["tags"]),
            "behaviors": list(definition["behaviors"]),
            "currency_preferences": dict(definition["currency_preferences"]),
            "acquisition": dict(definition["acquisition"]),
            "base": definition["base"],
            "fusion_only": definition["fusion_only"],
        })
        catalog.append(item)
    return catalog
>>>>>>> birch/projectile-collision-effects


def create_initial_inventory() -> Inventory:
    """Create a minimal starting inventory with only a basic common rifle."""
    inventory = Inventory(create_item_catalog())
    # Player starts with only a basic common rifle
    inventory.equip("starter-rapid", "weapons", 0)
    return inventory


def item_stat(item: dict[str, Any], name: str, default: float = 0.0) -> float:
    value = item.get("stats", {}).get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    try:
        base_value = float(value)
    except OverflowError as exc:
        raise ValueError(f"Item stat {name!r} exceeds the supported numeric range") from exc
    if not math.isfinite(base_value):
        raise ValueError(f"Item stat {name!r} must be finite")
    level = item.get("level", 1)
    if type(level) is not int or level < 1:
        raise ValueError("Item level must be a positive integer")
    addition_rate = _ITEM_LEVEL_SCALING["stat_addition_rates"].get(
        name, _ITEM_LEVEL_SCALING["default_addition_rate"]
    )
    try:
        leveled_value = base_value + base_value * addition_rate * (level - 1)
    except OverflowError as exc:
        raise ValueError("Item level scaling exceeded the supported numeric range") from exc
    if not math.isfinite(leveled_value):
        raise ValueError("Item level scaling exceeded the supported numeric range")
    rarity = str(item.get("rarity", "common")).lower()
    multipliers = _RARITY_SCALING["multipliers"]
    if rarity not in multipliers:
        raise ValueError(f"Unsupported item rarity: {rarity}")
    rarity_multiplier = multipliers[rarity]
    if rarity == "ultimate":
        tier = item.get("ultimate_tier", 1)
        if type(tier) is not int or not 1 <= tier <= 100:
            raise ValueError("Ultimate rarity tier must be an integer from 1 to 100")
        rarity_multiplier *= _RARITY_SCALING["ultimate_tier_growth"] ** (tier - 1)
    if name == "cooldown":
        rarity_multiplier = 1 / rarity_multiplier
    result = leveled_value * rarity_multiplier
    minimum_value = _ITEM_LEVEL_SCALING["minimum_values"].get(name)
    if minimum_value is not None:
        result = max(minimum_value, result)
    if not math.isfinite(result):
        raise ValueError(f"Scaled item stat {name!r} exceeds the supported numeric range")
    return result


<<<<<<< HEAD
def player_bonuses(inventory: Inventory) -> dict[str, float]:
    """Aggregate equipped armor plus passive owned relic/misc bonuses."""
    by_id = {str(item["id"]): item for item in inventory.items}
    equipped_armor = [
        by_id[str(item_id)] for item_id in inventory.active_slots["armor"]
        if item_id is not None
    ]
    contributors = list(equipped_armor)
    contributors.extend(item for item in inventory.items if item.get("type") in {"misc", "relic"})
    result = {"defense": 0.0, "health": 0.0, "speed_pct": 0.0,
              "luck": 0.0, "damage_pct": 0.0, "crit_chance": 0.0,
              "score_bonus_pct": 0.0, "elemental_dmg": 0.0}
    for item in contributors:
        for stat_name in result:
            result[stat_name] += item_stat(item, stat_name)
    for stat_name, value in calculate_armor_set_bonuses(
        equipped_armor, _ARMOR_SETS
    ).items():
        result[stat_name] += value
    return result


def armor_set_status(inventory: Inventory) -> list[dict[str, Any]]:
    """Return display-ready set progress and active bonuses for equipped armor."""
    by_id = {str(item["id"]): item for item in inventory.items}
    equipped_armor = [
        by_id[str(item_id)] for item_id in inventory.active_slots["armor"]
        if item_id is not None
    ]
    return calculate_armor_set_status(equipped_armor, _ARMOR_SETS)
=======
def player_bonuses(inventory: Inventory) -> dict[str, LargeNumber]:
    """Aggregate evaluated equipped armor plus passive owned misc items.

    Supplemental misc items contribute through their base item and are not
    counted a second time as independent passive items.
    """
    by_id = {str(item["id"]): item for item in inventory.items}
    contributors = [by_id[str(item_id)] for item_id in inventory.active_slots["armor"]
                    if item_id is not None]
    contributors.extend(
        item for item in inventory.items
        if item.get("type") == "misc" and not inventory.is_combination_supplement(str(item["id"]))
    )
    result = {"defense": LargeNumber(0), "health": LargeNumber(0),
              "speed_pct": LargeNumber(0), "luck": LargeNumber(0),
              "damage_pct": LargeNumber(0)}
    for item in contributors:
        combined = _COMBINATION_ENGINE.evaluate_inventory(inventory, str(item["id"]))
        for stat_name, value in combined.stats.items():
            if stat_name in result:
                result[stat_name] += value
    return result


def player_speed_multiplier(speed_bonus_pct: LargeNumber | int | float | str) -> float:
    """Convert a large speed bonus to a bounded physics multiplier."""
    bonus = LargeNumber(speed_bonus_pct)
    if bonus >= (MAX_PLAYER_SPEED_MULTIPLIER - 1) * 100:
        return MAX_PLAYER_SPEED_MULTIPLIER
    if bonus <= (MIN_PLAYER_SPEED_MULTIPLIER - 1) * 100:
        return MIN_PLAYER_SPEED_MULTIPLIER
    return max(MIN_PLAYER_SPEED_MULTIPLIER, 1 + bonus.to_float() / 100)
>>>>>>> birch/projectile-collision-effects


def spawnable_items() -> list[dict[str, Any]]:
    """Fresh copies of catalog records used by the test-spawn Bazaar UI."""
    return create_item_catalog()
