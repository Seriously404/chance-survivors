"""Projectile/bullet entity module."""

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, List

from game.utils.large_number import LargeNumber

@dataclass
class Projectile:
    """Represents a bullet/projectile entity."""

    x: float = 0.0
    y: float = 0.0
    dx: float = 1.0
    dy: float = 0.0
    angle: float = 0.0
    speed: float = 3.0
    damage: LargeNumber | int | float | str = 2
    piercing: int = 0
    hit_enemies: List[Any] = field(default_factory=list)
    bullet_type: str = "rapid_fire"
    explosion_radius: float = 0.0
    bounces_remaining: int = 0
    homing_strength: float = 0.0
    exploded: bool = False

    def __post_init__(self) -> None:
        self.damage = LargeNumber(self.damage)
        if (isinstance(self.explosion_radius, bool)
                or not isinstance(self.explosion_radius, (int, float))
                or not math.isfinite(self.explosion_radius) or self.explosion_radius < 0):
            raise ValueError("Projectile explosion radius must be finite and non-negative")
        if type(self.bounces_remaining) is not int or self.bounces_remaining < 0:
            raise ValueError("Projectile bounces_remaining must be a non-negative integer")
        if (isinstance(self.homing_strength, bool)
                or not isinstance(self.homing_strength, (int, float))
                or not math.isfinite(self.homing_strength) or self.homing_strength < 0):
            raise ValueError("Projectile homing_strength must be finite and non-negative")

    @classmethod
    def create_from_player(
        cls,
        player_x: float,
        player_y: float,
        angle: float,
        speed_modifier: float,
        base_speed: float,
        damage: LargeNumber | int | float | str = 2,
        piercing: int = 0,
        bullet_type: str = "rapid_fire",
        explosion_radius: float = 0.0,
        bounces_remaining: int = 0,
        homing_strength: float = 0.0,
    ) -> "Projectile":
        """Create a projectile from player position and angle."""
        direction_x = math.cos(angle)
        direction_y = math.sin(angle)

        return cls(
            x=player_x,
            y=player_y,
            dx=direction_x,
            dy=direction_y,
            angle=angle,
            speed=base_speed * speed_modifier,
            damage=damage,
            piercing=piercing,
            bullet_type=bullet_type,
            explosion_radius=explosion_radius,
            bounces_remaining=bounces_remaining,
            homing_strength=homing_strength,
        )

    def move(self, dt: float) -> None:
        """Move the projectile by its speed and direction."""
        self.x += self.dx * self.speed * dt
        self.y += self.dy * self.speed * dt

    def steer_towards(self, enemies: Iterable[Any], dt: float) -> None:
        """Turn toward the closest living, not-yet-hit enemy."""
        if self.homing_strength <= 0 or dt <= 0:
            return
        candidates = [
            enemy for enemy in enemies
            if enemy not in self.hit_enemies and not enemy.is_dead()
        ]
        if not candidates:
            return
        target = min(
            candidates,
            key=lambda enemy: (enemy.x-self.x)**2 + (enemy.y-self.y)**2,
        )
        dx = target.x-self.x
        dy = target.y-self.y
        if dx == 0 and dy == 0:
            return
        target_angle = math.atan2(dy, dx)
        current_angle = math.atan2(self.dy, self.dx)
        difference = (target_angle-current_angle+math.pi) % (2*math.pi)-math.pi
        turn_rate = min(6.0, self.homing_strength)
        rotation = max(-turn_rate*dt, min(turn_rate*dt, difference))
        new_angle = current_angle+rotation
        self.dx = math.cos(new_angle)
        self.dy = math.sin(new_angle)
        self.angle = new_angle

    def should_despawn(
        self,
        player_x: float,
        player_y: float,
        despawn_distance: float,
    ) -> bool:
        """Check if the projectile should be despawned based on distance from player."""
        distance_x = abs(self.x - player_x)
        distance_y = abs(self.y - player_y)
        return distance_x > despawn_distance or distance_y > despawn_distance

    def take_damage(self, enemy_health: LargeNumber | int | float | str) -> tuple[LargeNumber, bool]:
        """
        Apply damage to an enemy.
        Returns (damage_dealt, remaining_piercing).
        """
        damage_dealt = min(self.damage, LargeNumber(enemy_health))
        self.damage -= damage_dealt
        self.piercing -= 1
        return damage_dealt, self.piercing <= 0
