"""Enemy spawner system."""

import random
import math
from typing import List

from game.entities.enemy import Enemy
from game.config.settings import PIXELS_PER_UNIT, SCREEN_WIDTH, SCREEN_HEIGHT


class SpawnerSystem:
    """Handles enemy spawning logic."""

    def __init__(
        self,
        enemy_types: dict,
        spawn_delay_ms: int = 2000,
    ):
        """Initialize the spawner system.

        Args:
            enemy_types: Dictionary of enemy type configurations.
            spawn_delay_ms: Delay between enemy spawns in milliseconds.
        """
        self.enemy_types = enemy_types
        self.spawn_delay_ms = spawn_delay_ms
        self.spawn_timer_ms = 0

    def update(self, dt: float) -> None:
        """Update the spawn timer.

        Args:
            dt: Delta time in seconds.
        """
        self.spawn_timer_ms += dt * 1000

    def should_spawn(self) -> bool:
        """Check if it's time to spawn a new enemy.

        Returns:
            True if enough time has passed since the last spawn.
        """
        return self.spawn_timer_ms >= self.spawn_delay_ms

    def spawn(
        self,
        player_x: float,
        player_y: float,
        enemies: List[Enemy],
    ) -> None:
        """Spawn a new enemy at a random position.

        Args:
            player_x: Player's x position.
            player_y: Player's y position.
            enemies: List to append the new enemy to.
        """
        # Generate random position around the player
        x = random.uniform(-1, 1)
        y = random.uniform(-1, 1)

        # Normalize
        magnitude = math.sqrt(x**2 + y**2)
        x /= magnitude
        y /= magnitude

        # Convert to world coordinates
        spawn_distance = (SCREEN_WIDTH / 2 / PIXELS_PER_UNIT) * 1.5
        x = x * spawn_distance + player_x
        y = y * spawn_distance + player_y

        # Calculate direction towards player
        dx = player_x - x
        dy = y - player_y

        magnitude = math.sqrt(dx**2 + dy**2)
        dx /= magnitude
        dy /= magnitude

        angle = math.atan2(dy, dx)

        # Create and add enemy
        enemy = Enemy.create_from_type("basic", self.enemy_types["basic"], x, y)
        enemy.dx = dx
        enemy.dy = dy
        enemy.angle = angle
        enemies.append(enemy)

    def reset(self) -> None:
        """Reset the spawn timer."""
        self.spawn_timer_ms = 0
