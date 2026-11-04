"""Configured ranged enemy attack scheduling."""

from __future__ import annotations

import math
from typing import Any

from game.entities.enemy import Enemy
from game.entities.enemy_projectile import EnemyProjectile


def update_ranged_attacks(
    enemies: list[Enemy],
    enemy_types: dict[str, dict[str, Any]],
    dt: float,
    player_x: float,
    player_y: float,
) -> list[EnemyProjectile]:
    """Advance shooter cooldowns and launch aimed shots within configured range."""
    if not isinstance(dt, (int, float)) or not math.isfinite(dt) or dt < 0:
        raise ValueError("dt must be a finite non-negative number")

    projectiles: list[EnemyProjectile] = []
    for enemy in enemies:
        definition = enemy_types.get(enemy.type, {})
        if definition.get("special_ability") != "ranged_attack":
            continue

        interval = definition.get("attack_interval_seconds")
        attack_range = definition.get("attack_range")
        projectile_speed = definition.get("projectile_speed")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
            for value in (interval, attack_range, projectile_speed)
        ):
            raise ValueError(f"Invalid ranged attack configuration for {enemy.type!r}")

        distance = math.hypot(player_x - enemy.x, player_y - enemy.y)
        if distance > attack_range:
            enemy.ranged_attack_timer_seconds = 0.0
            continue

        enemy.ranged_attack_timer_seconds += dt
        if enemy.ranged_attack_timer_seconds < interval:
            continue

        enemy.ranged_attack_timer_seconds %= interval
        direction_x = player_x - enemy.x
        direction_y = player_y - enemy.y
        if distance == 0:
            direction_x, direction_y = 1.0, 0.0
        else:
            direction_x /= distance
            direction_y /= distance
        projectiles.append(
            EnemyProjectile(
                x=enemy.x,
                y=enemy.y,
                dx=direction_x,
                dy=direction_y,
                speed=float(projectile_speed),
                damage=max(1, int(enemy.damage)),
            )
        )
    return projectiles
