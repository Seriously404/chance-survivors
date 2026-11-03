"""Enemy entity module."""

import math
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Enemy:
    """Represents an enemy entity."""

    type: str
    x: float = 0.0
    y: float = 0.0
    dx: float = 1.0
    dy: float = 0.0
    angle: float = 0.0
    health: int = 10
    max_health: int = 10

    def __post_init__(self) -> None:
        """Normalize direction vector after initialization."""
        self._normalize_direction()

    def _normalize_direction(self) -> None:
        """Normalize the direction vector."""
        magnitude = math.sqrt(self.dx**2 + self.dy**2)
        if magnitude > 0:
            self.dx /= magnitude
            self.dy /= magnitude
            self.angle = math.atan2(self.dy, self.dx)

    def move_towards_player(
        self,
        player_x: float,
        player_y: float,
        speed: float,
        turning_speed: float,
        dt: float,
    ) -> None:
        """Move the enemy towards the player with rotation."""
        # Move the enemy
        self.x += self.dx * speed * dt
        self.y -= self.dy * speed * dt

        # Turn towards player
        dx = player_x - self.x
        dy = player_y - self.y

        if dx == 0 and dy == 0:
            return

        target_angle = math.atan2(dy, dx)
        current_angle = math.atan2(self.dy, self.dx)

        # Find the shortest rotation direction
        angle_difference = (target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi

        max_rotation = math.radians(90) * turning_speed * dt
        rotation = max(-max_rotation, min(max_rotation, angle_difference))

        # Update the normalized direction vector
        new_angle = current_angle + rotation
        self.dx = math.cos(new_angle)
        self.dy = math.sin(new_angle)
        self.angle = math.atan2(self.dy, self.dx)

    def take_damage(self, damage: int) -> int:
        """Apply damage to the enemy. Returns the actual damage dealt."""
        actual_damage = min(damage, self.health)
        self.health -= actual_damage
        return actual_damage

    def is_dead(self) -> bool:
        """Check if the enemy is dead."""
        return self.health <= 0

    @classmethod
    def create_from_type(
        cls,
        enemy_type: str,
        stats: Dict[str, Any],
        x: float,
        y: float,
    ) -> "Enemy":
        """Create an enemy from a type configuration."""
        return cls(
            type=enemy_type,
            x=x,
            y=y,
            dx=1.0,
            dy=0.0,
            angle=0.0,
            health=stats["max_health"],
            max_health=stats["max_health"],
        )
