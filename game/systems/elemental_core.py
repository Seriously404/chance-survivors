"""Elemental Core combination effects and damage over time."""
from __future__ import annotations

import random
from game.utils.large_number import LargeNumber

ELEMENTS = ("fire", "frost", "light", "shadow", "arcane", "nature")
RARITIES = ("common", "uncommon", "rare", "epic",
            "legendary", "mythical", "ultimate")


def core_for_item(inventory, item):
    """Find the core actually assigned to this item, if any."""
    if not item:
        return None
    by_id = {entry["id"]: entry for entry in inventory.items}
    return next((by_id[slot] for slot in item.get("combinations", [])
                 if slot in by_id and by_id[slot].get("fusion_recipe") == "elemental-core"), None)


def core_power(core):
    if not core:
        return (0.0, 0.0, 0)
    rarity = str(core.get("rarity", "common")).lower()
    rank = RARITIES.index(rarity) if rarity in RARITIES else 0
    level = max(1, int(core.get("level", 1)))
    return (min(.75, .08 + .04 * rank + .01 * (level - 1)),
            min(.9, .10 + .06 * rank + .01 * (level - 1)),
            min(len(ELEMENTS), 1 + rank // 2 + (level - 1) // 10))


def armor_core_resistance(inventory):
    by_id = {item["id"]: item for item in inventory.items}
    powers = [core_power(core_for_item(inventory, by_id.get(item_id)))[0]
              for item_id in inventory.active_slots["armor"] if item_id in by_id]
    return min(.8, sum(powers))


def weakened_resistances(resistances, core):
    reduction = core_power(core)[0]
    return {element: max(-1.0, float((resistances or {}).get(element, 0)) - reduction)
            for element in ELEMENTS}


def apply_lingering(enemy, damage, core, rng=random):
    """Roll independent elemental effects, each lasting three seconds."""
    _, chance, limit = core_power(core)
    if not limit:
        return
    effects = getattr(enemy, "elemental_lingering", {})
    for element in rng.sample(ELEMENTS, len(ELEMENTS)):
        if len(effects) >= limit and element not in effects:
            continue
        if rng.random() < chance:
            effects[element] = (3.0, LargeNumber(damage) * .10)
    enemy.elemental_lingering = effects


def tick_lingering(enemies, dt, enemy_types):
    """Advance damage over time and return killed enemies for normal rewards."""
    killed = []
    for enemy in enemies[:]:
        effects = getattr(enemy, "elemental_lingering", {})
        remaining = {}
        for element, (seconds, damage_per_second) in effects.items():
            active = min(max(0.0, dt), seconds)
            if active:
                resistance = enemy_types[enemy.type].get(
                    "resistances", {}).get(element, 0)
                damage = damage_per_second * active * \
                    max(0.0, 1.0 - float(resistance))
                enemy.take_damage(damage)
            if seconds > dt:
                remaining[element] = (seconds - dt, damage_per_second)
        enemy.elemental_lingering = remaining
        if enemy.is_dead():
            enemies.remove(enemy)
            killed.append(enemy)
    return killed
