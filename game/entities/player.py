"""Player entity module."""

import math
from dataclasses import dataclass, field
from typing import Tuple

from game.utils.large_number import LargeNumber

@dataclass
class Player:
    """Represents the player entity."""

    x: float = 0.0
    y: float = 0.0
    health: LargeNumber | int | str = 100
    max_health: LargeNumber | int | str = 100
    angle: float = 0.0

    def __post_init__(self) -> None:
        self.health = LargeNumber(self.health)
        self.max_health = LargeNumber(self.max_health)

    def move(self, dx: float, dy: float, dt: float, speed_multiplier: float = 1.0) -> None:
        """Move the player by the given delta, normalized by magnitude."""
        magnitude = math.sqrt(dx**2 + dy**2)
        if magnitude > 0:
            self.x += (dx / magnitude) * dt * speed_multiplier
            self.y += (dy / magnitude) * dt * speed_multiplier

    def set_rotation(self, mouse_position: Tuple[float, float], screen_width: int, screen_height: int) -> None:
        """Calculate and set the player's rotation based on mouse position."""
        direction_x = mouse_position[0] - screen_width / 2
        direction_y = screen_height / 2 - mouse_position[1]

        if direction_x == 0 and direction_y == 0:
            self.angle = 0.0
        else:
            self.angle = math.atan2(direction_y, direction_x)

    def take_damage(self, damage: LargeNumber | int | float | str) -> None:
        """Apply damage to the player, clamping health to minimum 0."""
        amount = LargeNumber(damage)
        if amount < 0:
            raise ValueError("Damage must be non-negative")
        self.health = max(LargeNumber(0), self.health - amount)

    def is_alive(self) -> bool:
        """Check if the player is still alive."""
        return self.health > 0

    def reset(self, max_health: int) -> None:
        """Reset the player to initial state."""
        self.x = 0.0
        self.y = 0.0
        self.health = LargeNumber(max_health)
        self.max_health = LargeNumber(max_health)
        self.angle = 0.0
