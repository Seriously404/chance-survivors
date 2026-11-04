"""Enemy spawner system."""

import random
import math
import copy
from typing import List

from game.entities.enemy import Enemy
from game.config.settings import PIXELS_PER_UNIT, SCREEN_WIDTH, SCREEN_HEIGHT
<<<<<<< HEAD
from game.systems.enemy_scaling import EnemyScaling
=======
from game.systems.scaling import ScalingSystem
>>>>>>> birch/projectile-collision-effects


class SpawnerSystem:
    """Handles enemy spawning logic."""

    def __init__(
        self,
        enemy_types: dict,
        spawn_delay_ms: int = 2000,
        scaling: ScalingSystem | None = None,
        rng: random.Random | None = None,
    ):
        """Initialize the spawner system.

        Args:
            enemy_types: Dictionary of enemy type configurations.
            spawn_delay_ms: Delay between enemy spawns in milliseconds.
        """
        self.enemy_types = enemy_types
        if type(spawn_delay_ms) is not int or spawn_delay_ms <= 0:
            raise ValueError("Spawn delay must be a positive integer number of milliseconds")
        self.spawn_delay_ms = spawn_delay_ms
        self.spawn_timer_ms = 0
        self.scaling = scaling or ScalingSystem()
        self.rng = rng or random.Random()
        self._initial_rng_state = self.rng.getstate()

    @property
    def difficulty_level(self) -> int:
        return self.scaling.difficulty_level

    @property
    def current_spawn_delay_ms(self) -> float:
        return self.scaling.spawn_delay_seconds(self.spawn_delay_ms / 1000) * 1000

    def increase_difficulty(self, steps: int = 1) -> None:
        """Raise player-controlled difficulty without changing elapsed time."""
        self.scaling.increase_difficulty(steps)

    def update(self, dt: float) -> None:
        """Update the spawn timer.

        Args:
            dt: Delta time in seconds.
        """
        if isinstance(dt, bool) or not isinstance(dt, (int, float)) or not math.isfinite(dt) or dt < 0:
            raise ValueError("Spawner delta time must be finite and non-negative")
        self.spawn_timer_ms += dt * 1000
        self.scaling.update_active_time(dt)

    def should_spawn(self) -> bool:
        """Check if it's time to spawn a new enemy.

        Returns:
            True if enough time has passed since the last spawn.
        """
        return self.spawn_timer_ms >= self.current_spawn_delay_ms

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
<<<<<<< HEAD
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
=======
        # Sample an angle directly for uniform coverage and no zero-vector case.
        angle = self.rng.uniform(0, math.tau)
        x = math.cos(angle)
        y = math.sin(angle)
>>>>>>> birch/projectile-collision-effects

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
<<<<<<< HEAD
        enemy = Enemy.create_from_type(enemy_name, stats, x, y)
=======
        base_stats = self.enemy_types["basic"]
        scaled = self.scaling.scaled_enemy_stats(
            base_stats["max_health"], base_stats.get("damage", 0),
            base_stats.get("reward_multiplier", 1),
        )
        scaled_stats = dict(base_stats)
        scaled_stats["max_health"] = scaled["health"]
        scaled_stats["damage"] = scaled["damage"]
        scaled_stats["reward_multiplier"] = scaled["reward"]
        enemy = Enemy.create_from_type("basic", scaled_stats, x, y)
>>>>>>> birch/projectile-collision-effects
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
        self.scaling = ScalingSystem(self.scaling.config)
        self.rng.setstate(self._initial_rng_state)
