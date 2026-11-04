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
    shield: LargeNumber | int | float = 0
    shield_remaining: float = 0.0
    dash_cooldown: float = 0.0
    dash_remaining: float = 0.0
    dash_speed: float = 0.0
    dash_dx: float = 0.0
    dash_dy: float = 0.0
    time_shift_remaining: float = 0.0

    def start_dash(self, dx: float, dy: float, *, distance: float = 2.0,
                   duration: float = 0.18, cooldown: float = 3.0,
                   time_shift: float = 0.0) -> bool:
        """Start a movement dash; aim direction is used when stationary."""
        if self.dash_cooldown > 0 or self.dash_remaining > 0:
            return False
        magnitude = math.hypot(dx, dy)
        if magnitude == 0:
            dx, dy, magnitude = math.cos(self.angle), math.sin(self.angle), 1.0
        duration = max(0.01, duration)
        self.dash_dx, self.dash_dy = dx / magnitude, dy / magnitude
        self.dash_speed = max(0.0, distance) / duration
        self.dash_remaining = duration
        self.dash_cooldown = max(0.0, cooldown)
        self.time_shift_remaining = max(0.0, time_shift)
        return True

    def update_dash(self, dt: float) -> None:
        """Advance the dash in real time, including its independent cooldown."""
        dt = max(0.0, dt)
        active = min(dt, self.dash_remaining)
        self.x += self.dash_dx * self.dash_speed * active
        self.y += self.dash_dy * self.dash_speed * active
        self.dash_remaining = max(0.0, self.dash_remaining - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.time_shift_remaining = max(0.0, self.time_shift_remaining - dt)

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
        absorbed = min(amount, LargeNumber(self.shield))
        self.shield = LargeNumber(self.shield) - absorbed
        amount -= absorbed
        self.health = max(LargeNumber(0), self.health - amount)

    def update_shield(self, dt: float) -> None:
        self.shield_remaining = max(0.0, self.shield_remaining - max(0.0, dt))
        if self.shield_remaining == 0:
            self.shield = 0.0

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
        self.shield = 0.0
        self.shield_remaining = 0.0
        self.dash_cooldown = self.dash_remaining = self.time_shift_remaining = 0.0
