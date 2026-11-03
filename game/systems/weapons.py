"""Weapon item and combination adapter for projectile generation."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from game.entities.projectile import Projectile
from game.systems.combinations import CombinedItem
from game.utils.large_number import LargeNumber


DEFAULT_WEAPON_TYPES = ("rapid_fire", "heavy_shot")
MIN_PROJECTILE_SPEED_MODIFIER = 0.001
MAX_PROJECTILE_SPEED_MODIFIER = 1_000.0
MAX_BASE_SPEED = 1_000.0
MAX_PROJECTILE_SPEED = 100_000.0
MIN_WEAPON_COOLDOWN = 0.001
MAX_WEAPON_COOLDOWN = 3_600.0
MAX_PIERCING = 1_000


def _number(value: Any, label: str) -> LargeNumber:
    if isinstance(value, bool):
        raise ValueError(f"Weapon {label} must be numeric")
    try:
        return LargeNumber(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Weapon {label} must be a finite numeric value") from exc


def _weapon_sources(
    weapon: Mapping[str, Any] | CombinedItem | None,
) -> tuple[Mapping[str, Any], Mapping[str, Any], int, frozenset[str]]:
    if weapon is None:
        return {}, {}, 1, frozenset()
    if isinstance(weapon, CombinedItem):
        if weapon.item_type != "weapon":
            raise ValueError("Combined item is not a weapon")
        if not isinstance(weapon.stats, Mapping) or not isinstance(weapon.metadata, Mapping):
            raise ValueError("Combined weapon stats and metadata must be objects")
        return weapon.stats, weapon.metadata, 1, frozenset(weapon.behaviors)
    if not isinstance(weapon, Mapping):
        raise ValueError("Weapon must be an item object or CombinedItem")
    if weapon.get("type") not in (None, "weapon"):
        raise ValueError("Inventory item is not a weapon")
    stats = weapon.get("stats", {})
    if not isinstance(stats, Mapping):
        raise ValueError("Weapon stats must be an object")
    level = weapon.get("level", 1)
    if type(level) is not int or level < 1:
        raise ValueError("Weapon level must be a positive integer")
    behaviors = weapon.get("behaviors", ())
    if not isinstance(behaviors, (list, tuple)) or any(not isinstance(value, str) for value in behaviors):
        raise ValueError("Weapon behaviors must be a sequence of strings")
    return stats, stats, level, frozenset(behaviors)


def _stat_value(
    stats: Mapping[str, Any],
    name: str,
    default: Any,
    level: int,
    *,
    scale_by_level: bool = True,
) -> LargeNumber:
    value = _number(stats.get(name, default), name)
    if scale_by_level and level > 1:
        # Keep the existing additive 10%-per-item-level behavior without
        # converting combat values through float or int.
        level_factor = LargeNumber(1) + LargeNumber("0.1") * (level - 1)
        value *= level_factor
    return value


def _definition_value(definition: Any, name: str) -> Any:
    return definition.get(name) if isinstance(definition, Mapping) else getattr(definition, name, None)


def _bounded_float(value: LargeNumber, label: str, minimum: float, maximum: float) -> float:
    if value < minimum or value > maximum:
        raise ValueError(f"Weapon {label} must be between {minimum} and {maximum}")
    try:
        result = value.to_float()
    except OverflowError as exc:
        raise ValueError(f"Weapon {label} is outside the supported range") from exc
    if not math.isfinite(result):
        raise ValueError(f"Weapon {label} must be finite")
    return result


def _bounded_piercing(value: LargeNumber) -> int:
    if value < 0 or value > MAX_PIERCING:
        raise ValueError(f"Weapon piercing must be between 0 and {MAX_PIERCING}")
    # The configured bound makes this conversion safe and deliberately keeps
    # piercing as a small integer counter in the collision loop.
    try:
        return int(value.to_float())
    except OverflowError as exc:
        raise ValueError("Weapon piercing is outside the supported range") from exc


def projectile_for_weapon(
    player: Any,
    angle: float,
    weapon: Mapping[str, Any] | CombinedItem | None,
    slot_index: int,
    bullet_types: Mapping[str, Any],
    base_speed: float,
    damage_bonus_pct: LargeNumber | int | float | str = 0,
) -> tuple[Projectile, float, bool]:
    """Build a projectile from an inventory item or evaluated combination.

    Combination stats have already passed the shared rarity/level pipeline, so
    they are used as-is. Ordinary inventory dictionaries retain their existing
    additive item-level behavior. Combat damage stays a ``LargeNumber``; only
    bounded movement, cooldown, and piercing fields are converted.
    """
    if type(slot_index) is not int or slot_index < 0:
        raise ValueError("Weapon slot index must be a non-negative integer")
    if not isinstance(bullet_types, Mapping):
        raise ValueError("Bullet type definitions must be a mapping")
    try:
        base_speed_value = float(base_speed)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Base projectile speed must be finite and positive") from exc
    if isinstance(base_speed, bool) or not math.isfinite(base_speed_value) or not 0 < base_speed_value <= MAX_BASE_SPEED:
        raise ValueError(f"Base projectile speed must be between 0 and {MAX_BASE_SPEED}")
    try:
        angle_value = float(angle)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Projectile angle must be finite") from exc
    if isinstance(angle, bool) or not math.isfinite(angle_value):
        raise ValueError("Projectile angle must be finite")

    stats, metadata, item_level, behaviors = _weapon_sources(weapon)
    if "bullet_type" in metadata:
        bullet_name = metadata["bullet_type"]
        if not isinstance(bullet_name, str) or not bullet_name:
            raise ValueError("Weapon bullet_type metadata must be a non-empty string")
    else:
        bullet_name = DEFAULT_WEAPON_TYPES[slot_index % len(DEFAULT_WEAPON_TYPES)]
    definition = bullet_types.get(bullet_name)
    if definition is None:
        raise ValueError(f"Weapon references unknown bullet type: {bullet_name}")

    default_damage = _definition_value(definition, "damage")
    default_speed = _definition_value(definition, "speed_modifier")
    default_piercing = _definition_value(definition, "piercing")
    default_cooldown = _definition_value(definition, "cooldown")
    default_automatic = _definition_value(definition, "automatic")
    if not isinstance(default_automatic, bool):
        raise ValueError(f"Bullet type {bullet_name!r} has invalid automatic metadata")

    damage = _stat_value(stats, "damage", default_damage, item_level)
    if damage < 0:
        raise ValueError("Weapon damage cannot be negative")
    damage_bonus = _number(damage_bonus_pct, "damage bonus")
    if damage_bonus < -100:
        raise ValueError("Weapon damage bonus cannot be below -100 percent")
    damage *= (LargeNumber(100) + damage_bonus) / 100
    damage = max(damage, LargeNumber(1))

    speed_modifier = _stat_value(stats, "speed_modifier", default_speed, item_level)
    speed_modifier_float = _bounded_float(
        speed_modifier,
        "speed modifier",
        MIN_PROJECTILE_SPEED_MODIFIER,
        MAX_PROJECTILE_SPEED_MODIFIER,
    )
    projectile_speed = base_speed_value * speed_modifier_float
    if not math.isfinite(projectile_speed) or projectile_speed > MAX_PROJECTILE_SPEED:
        raise ValueError(f"Projectile speed cannot exceed {MAX_PROJECTILE_SPEED}")

    piercing = _bounded_piercing(_stat_value(stats, "piercing", default_piercing, item_level))
    cooldown = _bounded_float(
        _stat_value(stats, "cooldown", default_cooldown, item_level, scale_by_level=False),
        "cooldown",
        MIN_WEAPON_COOLDOWN,
        MAX_WEAPON_COOLDOWN,
    )
    if "automatic" in metadata:
        automatic = metadata["automatic"]
        if not isinstance(automatic, bool):
            raise ValueError("Weapon automatic metadata must be a boolean")
    else:
        automatic = default_automatic

    explosion_radius = LargeNumber(0)
    if "area_explosion" in behaviors:
        explosion_radius = _stat_value(stats, "area_radius", 0, item_level)
    explosion_radius_float = _bounded_float(
        explosion_radius, "explosion radius", 0.0, 1_000.0
    )

    homing_strength = LargeNumber(0)
    if "homing_guidance" in behaviors:
        homing_strength = _stat_value(stats, "homing_strength", 1, item_level)
    homing_strength_float = _bounded_float(
        homing_strength, "homing strength", 0.0, 100.0
    )

    bounces_remaining = 0
    if "ricochet" in behaviors:
        bounces_remaining = _bounded_piercing(
            _stat_value(stats, "bounce_count", 1, item_level)
        )

    projectile = Projectile.create_from_player(
        player.x,
        player.y,
        angle_value,
        speed_modifier_float,
        base_speed_value,
        damage,
        piercing,
        bullet_name,
        explosion_radius_float,
        bounces_remaining,
        homing_strength_float,
    )
    return projectile, cooldown, automatic
