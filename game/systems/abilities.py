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
from game.ability_scripts.effects import Summon, teleport, ward, summon
from game.systems.elemental_core import weakened_resistances, apply_lingering


@dataclass
class AbilityOutcome:
    """Effects produced by a successful active ability cast."""

    projectile: Projectile | None = None
    killed_enemies: list[Enemy] = field(default_factory=list)
    healed: int = 0
    consumed: bool = True
    summon: Summon | None = None


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
    if item.get("stats", {}).get("script") == "sandevistan":
        return max(60.0, float(cooldown))
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
    core: dict[str, Any] | None = None,
) -> AbilityOutcome:
    """Execute one configured projectile, area-damage, or healing ability."""
    if str(item.get("type", "")).lower() != "ability":
        raise ValueError("Only ability items can be cast")
    stats = item.get("stats", {})
    script = stats.get("script", stats.get("cast_type", "projectile"))
    if script not in {"projectile", "nova", "heal", "teleport", "ward", "sentinel", "turret", "ember", "void", "frost", "mend_ward", "siphon", "dash", "sandevistan"}:
        raise ValueError(f"Unsupported ability script: {script!r}")

    if script in {"dash", "sandevistan"}:
        started = player.start_dash(math.cos(angle), math.sin(angle),
                                    distance=min(6.0, max(0.1, item_stat(
                                        item, "dash_distance", 2.0))),
                                    duration=float(
                                        stats.get("dash_duration", 0.18)),
                                    cooldown=ability_cooldown(item),
                                    time_shift=float(stats.get("time_shift_duration", 6.0)) if script == "sandevistan" else 0.0)
        return AbilityOutcome(consumed=started)
    if script == "teleport":
        teleport(item, player, angle)
        return AbilityOutcome()
    if script == "ward":
        ward(item, player)
        return AbilityOutcome()
    if script in {"sentinel", "turret"}:
        element = normalize_element(str(stats.get("element", "arcane")))
        ally = summon(item, player, element, script == "sentinel")
        ally.elemental_core = core
        ally.trail_element = next((tag.split(':', 1)[1] for tag in item.get(
            'tags', []) if tag.startswith('trail:')), None)
        return AbilityOutcome(summon=ally)

    if script in {"heal", "mend_ward"}:
        heal_amount = max(0, int(item_stat(item, "heal_amount", 0)))
        healed = min(heal_amount, max(0, player.max_health - player.health))
        shield_increase = script == "mend_ward" and player.shield < item_stat(
            item, "shield", 8)
        if healed <= 0 and not shield_increase:
            return AbilityOutcome(consumed=False)
        player.health += healed
        if script == "mend_ward":
            ward(item, player)
        return AbilityOutcome(healed=healed)

    damage = max(1, int(item_stat(item, "cast_damage", 8)))
    damage = max(1, int(damage * (1.0 + max(-99.0, damage_bonus_pct) / 100.0)))
    element = normalize_element(str(stats.get("element", "arcane")))

    if script in {"projectile", "ember", "frost"}:
        raw_speed_modifier = stats.get("cast_speed_modifier", 2.5)
        if (
            isinstance(raw_speed_modifier, bool)
            or not isinstance(raw_speed_modifier, (int, float))
            or not math.isfinite(float(raw_speed_modifier))
            or raw_speed_modifier <= 0
        ):
            raise ValueError(
                "Ability cast_speed_modifier must be positive and finite")
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
        if script == "ember":
            projectile.homing_strength = 1.0
        elif script == "frost":
            projectile.piercing = max(1, projectile.piercing)
        projectile.elemental_core = core
        projectile.trail_element = next((tag.split(':', 1)[1] for tag in item.get(
            'tags', []) if tag.startswith('trail:')), None)
        projectile.heal_on_damage = bool(item.get("heal_on_damage"))
        projectile.explosion_radius = max(
            0.0, float(stats.get("area_radius", 0)))
        projectile.homing_strength = max(
            projectile.homing_strength, float(stats.get("homing_strength", 0)))
        projectile.bounces_remaining = max(
            0, int(stats.get("bounce_count", 0)))
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
            raise ValueError(
                f"Unknown enemy type for ability target: {enemy.type}")
        effective_damage = apply_elemental_damage(
            damage,
            element,
            weakened_resistances(enemy_stats.get("resistances", {}), core)
            if core else enemy_stats.get("resistances", {}),
        )
        health_before = enemy.health
        enemy.take_damage(effective_damage)
        if item.get("heal_on_damage") or script == "siphon":
            dealt = min(health_before, effective_damage)
            player.health = min(player.max_health, player.health + dealt)
        if core:
            apply_lingering(enemy, damage, core)
        if enemy.is_dead():
            killed.append(enemy)
        else:
            survivors.append(enemy)
    enemies[:] = survivors
    return AbilityOutcome(killed_enemies=killed)
