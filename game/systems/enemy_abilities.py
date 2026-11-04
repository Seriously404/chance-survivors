"""Runtime behavior for data-configured enemy abilities."""

from __future__ import annotations

import math
from typing import Any

from game.entities.enemy import Enemy


def update_enemy_abilities(
    enemies: list[Enemy],
    enemy_types: dict[str, dict[str, Any]],
    dt: float,
    player_x: float,
    player_y: float,
    *,
    pixels_per_unit: int = 200,
) -> list[Enemy]:
    """Advance configured summoners and append capped, non-rewarding minions."""
    if not isinstance(dt, (int, float)) or not math.isfinite(dt) or dt < 0:
        raise ValueError("dt must be a finite non-negative number")
    if pixels_per_unit <= 0:
        raise ValueError("pixels_per_unit must be positive")

    spawned: list[Enemy] = []
    for summoner in enemies[:]:
        definition = enemy_types.get(summoner.type, {})
        if definition.get("special_ability") != "summon_minion":
            continue

        interval = definition.get("summon_interval_seconds", 6.0)
        summon_count = definition.get("summon_count", 1)
        maximum = definition.get("max_minions", 3)
        if (
            isinstance(interval, bool)
            or not isinstance(interval, (int, float))
            or not math.isfinite(interval)
            or interval <= 0
            or type(summon_count) is not int
            or summon_count <= 0
            or type(maximum) is not int
            or maximum <= 0
        ):
            raise ValueError(
                f"Invalid summon configuration for {summoner.type!r}")

        summoner.summon_timer_seconds += dt
        minions = [
            enemy
            for enemy in enemies
            if enemy.summoner_id == id(summoner) and not enemy.is_dead()
        ]
        if len(minions) >= maximum:
            summoner.summon_timer_seconds = min(
                summoner.summon_timer_seconds, float(interval)
            )
            continue

        minion_definition = enemy_types.get("necromancer_minion")
        if minion_definition is None:
            raise ValueError(
                "Enemy roster is missing the necromancer minion definition")

        spawned_this_cycle = 0
        while (
            summoner.summon_timer_seconds >= interval
            and len(minions) < maximum
            and spawned_this_cycle < summon_count
        ):
            summoner.summon_timer_seconds -= interval
            minions.append(
                _create_minion(
                    summoner,
                    minion_definition,
                    len(minions),
                    player_x,
                    player_y,
                    pixels_per_unit,
                )
            )
            spawned_this_cycle += 1

        if summoner.summon_timer_seconds >= interval:
            summoner.summon_timer_seconds = float(interval)

        for minion in minions[-spawned_this_cycle:] if spawned_this_cycle else ():
            enemies.append(minion)
            spawned.append(minion)
    return spawned


def _create_minion(
    summoner: Enemy,
    definition: dict[str, Any],
    index: int,
    player_x: float,
    player_y: float,
    pixels_per_unit: int,
) -> Enemy:
    """Create one minion with bounded stats derived from its summoner."""
    size = int(definition["size"])
    radius = (int(definition["size"]) + 30) / (2 * pixels_per_unit) + 0.02
    angle = index * math.tau / 3
    x = summoner.x + math.cos(angle) * radius
    y = summoner.y + math.sin(angle) * radius
    stats = {
        **definition,
        "max_health": max(1, int(summoner.max_health * 0.25)),
        "damage": max(1, int(summoner.damage * 0.5)),
        "speed": float(definition["speed"]),
        "size": size,
        "score_multiplier": 1,
    }
    dx = player_x - x
    dy = player_y - y
    magnitude = math.hypot(dx, dy)
    if magnitude == 0:
        dx, dy = 1.0, 0.0
    else:
        dx /= magnitude
        dy /= magnitude
    minion = Enemy.create_from_type("necromancer_minion", stats, x, y)
    minion.dx = dx
    minion.dy = dy
    minion.angle = math.atan2(dy, dx)
    minion.reward_eligible = False
    minion.summoner_id = id(summoner)
    return minion
