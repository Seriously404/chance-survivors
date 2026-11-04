"""Projectile fired by a ranged enemy."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class EnemyProjectile:
    """A small world-space projectile targeting the player."""

    x: float
    y: float
    dx: float
    dy: float
    speed: float
    damage: int
    radius: float = 6.0
    previous_x: float | None = None
    previous_y: float | None = None

    def move(self, dt: float) -> None:
        self.previous_x = self.x
        self.previous_y = self.y
        self.x += self.dx * self.speed * dt
        self.y += self.dy * self.speed * dt

    def should_despawn(
        self,
        player_x: float,
        player_y: float,
        max_distance: float,
    ) -> bool:
        return math.hypot(self.x - player_x, self.y - player_y) > max_distance
