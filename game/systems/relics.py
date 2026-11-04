"""Relic catalog and passive effect summaries for the live run."""

from __future__ import annotations

from typing import Any


def build_relic_catalog() -> list[dict[str, Any]]:
    """Return the data-driven relic set used by the inventory and Bazaar."""
    definitions = [
        (
            "lucky-box",
            "Lucky Box",
            "uncommon",
            {
                "luck": 2.0,
                "crit_chance": 1.0,
                "score_bonus_pct": 1.5,
            },
            "A small charm that quietly heightens fortune every time you cast.",
        ),
        (
            "monkeys-paw",
            "Monkey's Paw",
            "rare",
            {
                "luck": 3.0,
                "damage_pct": 7.0,
                "speed_pct": 4.0,
                "crit_chance": 2.0,
            },
            "Randomized blessings and penalties, all wrapped in a tremble of luck.",
        ),
        (
            "echo-prism",
            "Echo Prism",
            "rare",
            {
                "damage_pct": 9.0,
                "crit_chance": 3.0,
                "score_bonus_pct": 2.0,
            },
            "Shards that repeat the last hit with a little more force.",
        ),
        (
            "iron-nest",
            "Iron Nest",
            "epic",
            {
                "health": 18.0,
                "defense": 3.0,
                "speed_pct": -2.0,
            },
            "A stubborn ward that makes you harder to kill but slower to move.",
        ),
        (
            "glass-heart",
            "Glass Heart",
            "epic",
            {
                "health": 12.0,
                "luck": 4.0,
                "healing_pct": 5.0,
            },
            "A fragile but radiant relic that rewards good fortune with resilience.",
        ),
        (
            "void-bell",
            "Void Bell",
            "legendary",
            {
                "damage_pct": 15.0,
                "luck": 5.0,
                "crit_chance": 4.0,
                "score_bonus_pct": 4.0,
            },
            "A resonant relic that magnifies destructive momentum and luck alike.",
        ),
    ]

    items: list[dict[str, Any]] = []
    for relic_id, name, rarity, stats, description in definitions:
        items.append(
            {
                "id": relic_id,
                "name": name,
                "type": "relic",
                "rarity": rarity,
                "level": 1,
                "stats": stats,
                "status": "normal",
                "description": description,
                "combinations": [None] * 2,
            }
        )
    return items


def relic_effect_summary(inventory: Any) -> dict[str, Any]:
    """Aggregate the passive benefit curve of all relics in the inventory."""
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
            value = item.get("stats", {}).get(key, 0)
            if isinstance(value, (int, float)):
                summary[key] += float(value)
    return {"items": relic_items, "summary": summary}
