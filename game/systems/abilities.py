"""Reusable active ability effects, independent of input and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from game.entities.enemy import Enemy
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.systems.elements import apply_elemental_damage, normalize_element
from game.systems.items import item_stat


@dataclass
class AbilityOutcome:
    """Effects produced by a successful active ability cast."""

    projectile: Projectile | None = None
    killed_enemies: list[Enemy] = field(default_factory=list)
    healed: int = 0
    consumed: bool = True


def ability_cooldown(item: dict[str, Any]) -> float:
    """Return a validated cooldown in seconds for an ability item."""
    if str(item.get("type", "")).lower() != "ability":
        raise ValueError("Only ability items can be cast")
    raw_cooldown = item.get("stats", {}).get("cooldown", 8.0)
    if isinstance(raw_cooldown, bool) or not isinstance(raw_cooldown, (int, float)):
        raise ValueError("Ability cooldown must be a positive number")
    if not math.isfinite(float(raw_cooldown)) or raw_cooldown <= 0:
        raise ValueError("Ability cooldown must be a positive finite number")
    cooldown = item_stat(item, "cooldown", 8.0)
    return float(cooldown)


def cast_ability(
    item: dict[str, Any],
    player: Player,
    enemies: list[Enemy],
    *,
    angle: float,
    base_speed: float,
    enemy_types: dict[str, dict[str, Any]],
    damage_bonus_pct: float = 0.0,
) -> AbilityOutcome:
    """Execute one configured projectile, area-damage, or healing ability."""
    if str(item.get("type", "")).lower() != "ability":
        raise ValueError("Only ability items can be cast")
    stats = item.get("stats", {})
    cast_type = stats.get("cast_type", "projectile")
    if cast_type not in {"projectile", "nova", "heal"}:
        raise ValueError(f"Unsupported ability cast_type: {cast_type!r}")

    if cast_type == "heal":
        heal_amount = max(0, int(item_stat(item, "heal_amount", 0)))
        healed = min(heal_amount, max(0, player.max_health - player.health))
        if healed <= 0:
            return AbilityOutcome(consumed=False)
        player.health += healed
        return AbilityOutcome(healed=healed)

    damage = max(1, int(item_stat(item, "cast_damage", 8)))
    damage = max(1, int(damage * (1.0 + max(-99.0, damage_bonus_pct) / 100.0)))
    element = normalize_element(str(stats.get("element", "arcane")))

    if cast_type == "projectile":
        raw_speed_modifier = stats.get("cast_speed_modifier", 2.5)
        if (
            isinstance(raw_speed_modifier, bool)
            or not isinstance(raw_speed_modifier, (int, float))
            or not math.isfinite(float(raw_speed_modifier))
            or raw_speed_modifier <= 0
        ):
            raise ValueError("Ability cast_speed_modifier must be positive and finite")
        speed_modifier = item_stat(item, "cast_speed_modifier", 2.5)
        projectile = Projectile.create_from_player(
            player.x,
            player.y,
            angle,
            speed_modifier,
            base_speed,
            damage=damage,
            piercing=max(0, int(item_stat(item, "cast_piercing", 0))),
            bullet_type=f"ability:{item.get('id', 'unknown')}",
            element=element,
        )
        return AbilityOutcome(projectile=projectile)

    radius = item_stat(item, "cast_radius", 0.5)
    if radius <= 0 or not math.isfinite(radius):
        raise ValueError("Ability cast_radius must be positive and finite")

    killed: list[Enemy] = []
    survivors: list[Enemy] = []
    for enemy in enemies:
        if math.hypot(enemy.x - player.x, enemy.y - player.y) > radius:
            survivors.append(enemy)
            continue
        enemy_stats = enemy_types.get(enemy.type)
        if enemy_stats is None:
            raise ValueError(f"Unknown enemy type for ability target: {enemy.type}")
        effective_damage = apply_elemental_damage(
            damage,
            element,
            enemy_stats.get("resistances", {}),
        )
        enemy.take_damage(effective_damage)
        if enemy.is_dead():
            killed.append(enemy)
        else:
            survivors.append(enemy)
    enemies[:] = survivors
    return AbilityOutcome(killed_enemies=killed)
