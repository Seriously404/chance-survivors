"""Weapon item to projectile adapter, independent of client rendering."""

import math
import copy

from game.entities.projectile import Projectile
from game.systems.combinations import CombinedItem
from game.systems.items import item_stat
from game.utils.large_number import LargeNumber

DEFAULT_WEAPON_TYPES = ("rapid_fire", "heavy_shot")


def projectile_for_weapon(player, angle, weapon, slot_index, bullet_types,
                          base_speed, damage_bonus_pct=0.0):
    if weapon is None:
        raise ValueError("Cannot fire an empty weapon slot")
    combined = isinstance(weapon, CombinedItem)
    metadata = weapon.metadata if combined else weapon.get("stats", {})
    bullet_name = str(metadata.get(
        "bullet_type", DEFAULT_WEAPON_TYPES[slot_index % 2]))
    definition = bullet_types.get(bullet_name)
    if definition is None:
        raise ValueError(
            f"Weapon references unknown bullet type: {bullet_name}")

    def stat(name, default):
        if combined:
            return weapon.stats.get(name, LargeNumber(default))
        return LargeNumber(item_stat(weapon, name, default))

    def bounded(name, default, *, positive=False):
        value = stat(name, default)
        if value < 0 or (positive and value <= 0) or value > 1000000:
            raise ValueError(f"Invalid weapon {name}")
        value = value.to_float()
        if not math.isfinite(value):
            raise ValueError(f"Invalid weapon {name}")
        return value

    damage = stat("damage", definition.damage)
    if damage < 0:
        raise ValueError("Invalid weapon damage")
    damage = max(LargeNumber(1), damage * (1 + damage_bonus_pct / 100))
    if not combined:
        damage = int(damage.to_float())
    raw_speed = stat("speed_modifier", definition.speed_modifier)
    if raw_speed <= 0:
        raise ValueError("Invalid weapon speed_modifier")
    # Speed grows gently at high rarity; collision still sweeps the full path.
    raw_speed = min(raw_speed, LargeNumber(1_000_000)).to_float()
    speed = raw_speed if raw_speed <= 6 else min(
        30.0, 6 + math.sqrt(raw_speed - 6))
    piercing = int(bounded("piercing", definition.piercing))
    cooldown = bounded("cooldown", definition.cooldown, positive=True)
    automatic = metadata.get("automatic", definition.automatic)
    if not isinstance(automatic, bool):
        raise ValueError("Invalid weapon automatic flag")
    projectile = Projectile.create_from_player(
        player.x, player.y, angle, speed, base_speed, damage, piercing,
        bullet_name, str(metadata.get("element", "physical")).lower())
    projectile.damage_components = [
        {"element": part["element"], "damage": part["damage"] * (1 + damage_bonus_pct / 100)}
        for part in metadata.get("hybrid_damage_components", [])
    ]
    projectile.heal_on_damage = any(
        part.get("script", part.get("cast_type")) in {"heal", "mend_ward"}
        for part in metadata.get("supplements", {}).values()
    )
    tags = weapon.tags if combined else weapon.get('tags', [])
    projectile.trail_element = next(
        (tag.split(':', 1)[1] for tag in tags if tag.startswith('trail:')), None)
    if combined:
        projectile.explosion_radius = bounded("area_radius", 0)
        projectile.homing_strength = bounded("homing_strength", 0)
        projectile.bounces_remaining = int(bounded("bounce_count", 0))
    if bullet_name == "homing":
        projectile.homing_strength = max(
            projectile.homing_strength, bounded("homing_speed", 5))
    return projectile, cooldown, automatic


def projectiles_for_weapon(player, angle, weapon, slot_index, bullet_types,
                           base_speed, damage_bonus_pct=0.0):
    """Create the complete volley, including the shotgun's spread."""
    projectile, cooldown, automatic = projectile_for_weapon(
        player, angle, weapon, slot_index, bullet_types, base_speed, damage_bonus_pct)
    if projectile.bullet_type != "shotgun":
        return [projectile], cooldown, automatic
    stats = weapon.stats if isinstance(
        weapon, CombinedItem) else weapon.get("stats", {})
    count = max(1, min(32, int(LargeNumber(stats.get("pellets", 6)).to_float())))
    spread = math.radians(24)
    shots = []
    for index in range(count):
        shot = copy.copy(projectile)
        shot.hit_enemies = []
        shot.angle = angle + (index / (count - 1) - 0.5) * \
            spread if count > 1 else angle
        shot.dx, shot.dy = math.cos(shot.angle), math.sin(shot.angle)
        shots.append(shot)
    return shots, cooldown, automatic
