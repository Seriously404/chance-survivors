"""Enemy spawner system."""

import random
import math
import copy
from typing import List

from game.entities.enemy import Enemy
from game.config.settings import PIXELS_PER_UNIT, SCREEN_WIDTH, SCREEN_HEIGHT
from game.systems.enemy_scaling import EnemyScaling


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
        *,
        elapsed_seconds: float = 0.0,
        scaling: EnemyScaling | None = None,
    ) -> None:
        """Spawn a new enemy at a random position.

        Args:
            player_x: Player's x position.
            player_y: Player's y position.
            enemies: List to append the new enemy to.
            elapsed_seconds: Active run time used for time-based scaling.
            scaling: Optional player-controlled enemy scaling state.
        """
        spawn_candidates = [
            (name, data, float(data.get("weight", 1)))
            for name, data in self.enemy_types.items()
            if not data.get("summoned_only")
            and float(data.get("weight", 1)) > 0
        ]
        if not spawn_candidates:
            raise ValueError("Enemy roster has no spawnable enemy types")
        total_weight = sum(weight for _, _, weight in spawn_candidates)
        choice = random.random() * total_weight
        running = 0.0
        enemy_name = spawn_candidates[-1][0]
        for name, _, weight in spawn_candidates:
            running += weight
            if choice <= running:
                enemy_name = name
                break

        stats = self.enemy_types[enemy_name]
        if scaling is not None:
            stats = scaling.scale_stats(stats, elapsed_seconds)
        group_count = stats.get("spawn_group_count", 1)
        if type(group_count) is not int or not 1 <= group_count <= 8:
            raise ValueError(f"Invalid spawn_group_count for enemy {enemy_name!r}")
        group_radius = stats.get("spawn_group_radius", 0.0)
        if (
            isinstance(group_radius, bool)
            or not isinstance(group_radius, (int, float))
            or not math.isfinite(group_radius)
            or group_radius < 0
        ):
            raise ValueError(f"Invalid spawn_group_radius for enemy {enemy_name!r}")

        # Generate a random offset around the player and avoid the zero-vector
        # edge case where both random values land on 0.
        for _ in range(16):
            x = random.uniform(-1, 1)
            y = random.uniform(-1, 1)
            magnitude = math.hypot(x, y)
            if magnitude > 0:
                break
        else:
            x, y = 1.0, 0.0
            magnitude = 1.0

        x /= magnitude
        y /= magnitude

        # Convert to world coordinates
        spawn_distance = (SCREEN_WIDTH / 2 / PIXELS_PER_UNIT) * 1.5
        x = x * spawn_distance + player_x
        y = y * spawn_distance + player_y

        # Calculate direction towards player (positive y = up)
        dx = player_x - x
        dy = player_y - y

        magnitude = math.hypot(dx, dy)
        if magnitude == 0:
            dx, dy = 1.0, 0.0
        else:
            dx /= magnitude
            dy /= magnitude

        angle = math.atan2(dy, dx)

        # Create and add enemy
        enemy = Enemy.create_from_type(enemy_name, stats, x, y)
        enemy.dx = dx
        enemy.dy = dy
        enemy.angle = angle
        enemies.append(enemy)
        for index in range(1, group_count):
            group_angle = math.tau * index / group_count
            member_x = x + math.cos(group_angle) * group_radius
            member_y = y + math.sin(group_angle) * group_radius
            member_dx = player_x - member_x
            member_dy = player_y - member_y
            member_magnitude = math.hypot(member_dx, member_dy)
            if member_magnitude == 0:
                member_dx, member_dy = 1.0, 0.0
            else:
                member_dx /= member_magnitude
                member_dy /= member_magnitude
            member = Enemy.create_from_type(
                enemy_name,
                copy.deepcopy(stats),
                member_x,
                member_y,
            )
            member.dx = member_dx
            member.dy = member_dy
            member.angle = math.atan2(member_dy, member_dx)
            enemies.append(member)

    def reset(self) -> None:
        """Reset the spawn timer."""
        self.spawn_timer_ms = 0
