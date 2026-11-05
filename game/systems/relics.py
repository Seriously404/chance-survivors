"""Relic catalog and passive effect summaries for the live run."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from game.systems.inventory import _item
from game.systems.items import item_stat
from game.systems.json_loader import load_relics


def build_relic_catalog() -> list[dict[str, Any]]:
    """Build fresh relic instances from the same definitions as the Bazaar.

    This compatibility helper must not carry a second catalog with promises
    (such as repeat hits or random penalties) absent from the actual runtime.
    Armor entries stored in the historical relic asset are not relics.
    """
    items = []
    for definition in load_relics():
        if definition.get("type") != "relic":
            continue
        item = deepcopy(definition)
        instance = _item(
            item["id"], item["name"], "relic", item["rarity"],
            item.get("level", 1), item.get("stats", {}),
        )
        item.update(instance)
        items.append(item)
    return items


def relic_effect_summary(inventory: Any) -> dict[str, Any]:
    """Summarize owned relic passives using live level and rarity scaling."""
    relic_items = [
        item for item in getattr(inventory, "items", [])
        if str(item.get("type", "")).lower() == "relic"
    ]
    summary = {
        "luck": 0.0,
        "damage_pct": 0.0,
        "health": 0.0,
        "defense": 0.0,
        "speed_pct": 0.0,
        "crit_chance": 0.0,
        "score_bonus_pct": 0.0,
        "healing_pct": 0.0,
    }
    for item in relic_items:
        for key in summary:
            summary[key] += item_stat(item, key)
    return {"items": relic_items, "summary": summary}
