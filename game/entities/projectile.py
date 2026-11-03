"""Projectile/bullet entity module."""

import math
from dataclasses import dataclass, field
from typing import List, Any


@dataclass
class Projectile:
    """Represents a bullet/projectile entity."""

    x: float = 0.0
    y: float = 0.0
    dx: float = 1.0
    dy: float = 0.0
    angle: float = 0.0
    speed: float = 3.0
    damage: int = 2
    piercing: int = 0
    hit_enemies: List[Any] = field(default_factory=list)

    @classmethod
    def create_from_player(
        cls,
        player_x: float,
        player_y: float,
        angle: float,
        speed_modifier: float,
        base_speed: float,
        damage: int = 2,
        piercing: int = 0,
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
        )

    def move(self, dt: float) -> None:
        """Move the projectile by its speed and direction."""
        self.x += self.dx * self.speed * dt
        self.y += self.dy * self.speed * dt

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

    def take_damage(self, enemy_health: int) -> tuple[int, int]:
        """
        Apply damage to an enemy.
        Returns (damage_dealt, remaining_piercing).
        """
        damage_dealt = min(self.damage, enemy_health)
        self.damage -= damage_dealt
        self.piercing -= 1
        return damage_dealt, self.piercing <= 0
