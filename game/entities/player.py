"""Player entity module."""

import math
from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class Player:
    """Represents the player entity."""

    x: float = 0.0
    y: float = 0.0
    health: int = 100
    max_health: int = 100
    angle: float = 0.0

    def move(self, dx: float, dy: float, dt: float) -> None:
        """Move the player by the given delta, normalized by magnitude."""
        magnitude = math.sqrt(dx**2 + dy**2)
        if magnitude > 0:
            self.x += (dx / magnitude) * dt
            self.y += (dy / magnitude) * dt

    def set_rotation(self, mouse_position: Tuple[float, float], screen_width: int, screen_height: int) -> None:
        """Calculate and set the player's rotation based on mouse position."""
        direction_x = mouse_position[0] - screen_width / 2
        direction_y = screen_height / 2 - mouse_position[1]

        if direction_x == 0 and direction_y == 0:
            self.angle = 0.0
        else:
            self.angle = math.atan2(direction_y, direction_x)

    def take_damage(self, damage: int) -> None:
        """Apply damage to the player, clamping health to minimum 0."""
        self.health = max(0, self.health - damage)

    def is_alive(self) -> bool:
        """Check if the player is still alive."""
        return self.health > 0

    def reset(self, max_health: int) -> None:
        """Reset the player to initial state."""
        self.x = 0.0
        self.y = 0.0
        self.health = max_health
        self.max_health = max_health
        self.angle = 0.0
