"""Ability behavior implementations, independent of input and rendering."""
from __future__ import annotations

import math
from dataclasses import dataclass

from game.entities.projectile import Projectile
from game.systems.items import item_stat


@dataclass
class Summon:
    x: float
    y: float
    remaining: float
    damage: int
    element: str
    mobile: bool = False
    attack_timer: float = 0.0
    elemental_core: dict | None = None


def teleport(item, player, angle):
    distance = max(0.0, item_stat(item, "teleport_range", 5))
    player.x += math.cos(angle) * distance
    player.y += math.sin(angle) * distance


def ward(item, player):
    player.shield = max(player.shield, item_stat(item, "shield", 8))
    player.shield_remaining = max(
        player.shield_remaining, item_stat(item, "shield_duration", 6))


def summon(item, player, element, mobile):
    return Summon(player.x, player.y, max(0.0, item_stat(item, "summon_duration", 10)),
                  max(1, int(item_stat(item, "summon_damage", 15))), element, mobile)


def update_summons(summons, enemies, player, dt, base_speed):
    """Advance allied summons and return the projectiles they fire this frame."""
    shots = []
    for ally in summons:
        active_dt = min(max(dt, 0.0), max(ally.remaining, 0.0))
        ally.remaining -= active_dt
        if active_dt <= 0:
            continue
        if ally.mobile:
            distance = math.hypot(player.x - ally.x, player.y - ally.y)
            if distance > 0.6:
                step = min(distance - 0.6, active_dt * 1.5)
                ally.x += (player.x - ally.x) / distance * step
                ally.y += (player.y - ally.y) / distance * step
        ally.attack_timer -= active_dt
        target = min((e for e in enemies if not e.is_dead()),
                     key=lambda e: math.hypot(e.x - ally.x, e.y - ally.y), default=None)
        if target is not None and ally.attack_timer <= 0:
            angle = math.atan2(target.y - ally.y, target.x - ally.x)
            projectile = Projectile.create_from_player(ally.x, ally.y, angle, 2.5, base_speed,
                                                       damage=ally.damage, bullet_type="ability:summon", element=ally.element)
            projectile.elemental_core = ally.elemental_core
            shots.append(projectile)
            ally.attack_timer = 1.0
    summons[:] = [ally for ally in summons if ally.remaining > 0]
    return shots
