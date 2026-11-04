"""Weapon item to projectile adapter, independent of client rendering."""

from __future__ import annotations

from game.entities.projectile import Projectile
from game.systems.items import item_stat


DEFAULT_WEAPON_TYPES = ("rapid_fire", "heavy_shot")


def projectile_for_weapon(player, angle, weapon, slot_index, bullet_types,
                          base_speed, damage_bonus_pct=0.0):
    item_stats=weapon.get("stats",{}) if weapon else {}
    bullet_name=str(item_stats.get("bullet_type",DEFAULT_WEAPON_TYPES[slot_index % 2]))
    definition=bullet_types.get(bullet_name)
    if definition is None:
        raise ValueError(f"Weapon references unknown bullet type: {bullet_name}")
    damage=max(1,int(item_stat(weapon,"damage",definition.damage) if weapon else definition.damage))
    damage=max(1,int(damage*(1+damage_bonus_pct/100)))
    speed=item_stat(weapon,"speed_modifier",definition.speed_modifier) if weapon else definition.speed_modifier
    piercing=max(0,int(item_stat(weapon,"piercing",definition.piercing) if weapon else definition.piercing))
    raw_cooldown=item_stat(weapon,"cooldown",definition.cooldown) if weapon else definition.cooldown
    cooldown=float(raw_cooldown) if isinstance(raw_cooldown,(int,float)) and raw_cooldown>0 else definition.cooldown
    automatic=bool(item_stats.get("automatic",definition.automatic))
    element = str(item_stats.get("element", "physical")).lower()
    projectile=Projectile.create_from_player(
        player.x,player.y,angle,speed,base_speed,damage,piercing,bullet_name,element)
    return projectile,cooldown,automatic
