"""Starter item catalog and stat aggregation helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from game.systems.inventory import Inventory, _item


def create_item_catalog() -> list[dict[str, Any]]:
    """Return fresh starter/test items suitable for inventory or Bazaar spawns."""
    definitions = [
        ("starter-vest", "Copper Vest", "armor", "common", {"defense": 2, "health": 12}),
        ("starter-boots", "Scout Boots", "armor", "uncommon", {"defense": 1, "speed_pct": 8}),
        ("starter-plate", "Iron Plate", "armor", "rare", {"defense": 4, "health": 20}),
        ("starter-hood", "Lucky Hood", "armor", "epic", {"defense": 2, "luck": 3}),
        ("starter-gloves", "Swift Gloves", "armor", "legendary", {"defense": 2, "speed_pct": 12}),
        ("starter-rapid", "Rapid Carbine", "weapon", "uncommon", {
            "bullet_type": "rapid_fire", "damage": 7, "cooldown": 0.14,
            "speed_modifier": 3.0, "piercing": 0,
        }),
        ("starter-heavy", "Heavy Pistol", "weapon", "rare", {
            "bullet_type": "heavy_shot", "damage": 18, "cooldown": 0.68,
            "speed_modifier": 2.2, "piercing": 2,
        }),
        ("starter-charm", "Lucky Charm", "ability", "rare", {"luck": 2, "cooldown": 8}),
        ("starter-core", "Vitality Core", "ability", "epic", {"health": 10, "cooldown": 12}),
        ("starter-relic", "Fortune Relic", "misc", "common", {"luck": 2, "damage_pct": 5}),
        ("starter-token", "Copper Token", "misc", "uncommon", {"health": 5, "speed_pct": 2}),
    ]
    return [_item(item_id, name, kind, rarity, 1, deepcopy(stats))
            for item_id, name, kind, rarity, stats in definitions]


def create_initial_inventory() -> Inventory:
    inventory = Inventory(create_item_catalog())
    for index, item_id in enumerate(("starter-vest", "starter-boots", "starter-plate")):
        inventory.equip(item_id, "armor", index)
    inventory.equip("starter-rapid", "weapons", 0)
    inventory.equip("starter-heavy", "weapons", 1)
    inventory.equip("starter-charm", "abilities", 0)
    inventory.equip("starter-core", "abilities", 1)
    return inventory


def item_stat(item: dict[str, Any], name: str, default: float = 0.0) -> float:
    value = item.get("stats", {}).get(name, default)
    if not isinstance(value, (int, float)):
        return default
    return float(value) * (1 + max(0, int(item.get("level", 1)) - 1) * 0.1)


def player_bonuses(inventory: Inventory) -> dict[str, float]:
    """Aggregate equipped armor plus passive owned misc-item bonuses."""
    by_id = {str(item["id"]): item for item in inventory.items}
    contributors = [by_id[str(item_id)] for item_id in inventory.active_slots["armor"]
                    if item_id is not None]
    contributors.extend(item for item in inventory.items if item.get("type") == "misc")
    result = {"defense": 0.0, "health": 0.0, "speed_pct": 0.0,
              "luck": 0.0, "damage_pct": 0.0}
    for item in contributors:
        for stat_name in result:
            result[stat_name] += item_stat(item, stat_name)
    return result


def spawnable_items() -> list[dict[str, Any]]:
    """Fresh copies of catalog records used by the test-spawn Bazaar UI."""
    return create_item_catalog()
