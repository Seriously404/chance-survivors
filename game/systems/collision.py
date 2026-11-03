"""Collision detection system."""

import math
from typing import List, Tuple, Any

from game.entities.projectile import Projectile
from game.entities.enemy import Enemy
from game.entities.player import Player


class CollisionSystem:
    """Handles all collision detection in the game."""

    BULLET_RADIUS: float = 5
    PLAYER_SIZE: float = 30

    def __init__(self, pixels_per_unit: int):
        """Initialize the collision system.

        Args:
            pixels_per_unit: Conversion factor from world units to pixels.
        """
        self.pixels_per_unit = pixels_per_unit

    def _calculate_collision_distance(
        self,
        entity_size: float,
        other_size: float,
    ) -> float:
        """Calculate the collision distance between two entities."""
        return (entity_size / 2 + other_size / 2) / self.pixels_per_unit

    def check_bullet_enemy_collision(
        self,
        bullet: Projectile,
        enemy: Enemy,
        enemy_stats: dict,
    ) -> bool:
        """Check if a bullet collides with an enemy.

        Args:
            bullet: The projectile to check.
            enemy: The enemy to check against.
            enemy_stats: The enemy type statistics.

        Returns:
            True if collision detected, False otherwise.
        """
        collision_distance = (
            enemy_stats["size"] / 2 + self.BULLET_RADIUS
        ) / self.pixels_per_unit

        distance = self._get_distance(bullet.x, bullet.y, enemy.x, enemy.y)
        return distance <= collision_distance

    def check_enemy_player_collision(
        self,
        enemy: Enemy,
        player: Player,
        enemy_stats: dict,
    ) -> bool:
        """Check if an enemy collides with the player.

        Args:
            enemy: The enemy to check.
            player: The player to check against.
            enemy_stats: The enemy type statistics.

        Returns:
            True if collision detected, False otherwise.
        """
        collision_distance = self._calculate_collision_distance(
            enemy_stats["size"],
            self.PLAYER_SIZE,
        )

        distance = self._get_distance(enemy.x, enemy.y, player.x, player.y)
        return distance <= collision_distance

    def check_bullet_enemy_collisions(
        self,
        bullets: List[Projectile],
        enemies: List[Enemy],
        enemy_types: dict,
    ) -> Tuple[List[Projectile], List[Enemy]]:
        """Check all bullet-enemy collisions and update entities.

        Args:
            bullets: List of active bullets.
            enemies: List of active enemies.
            enemy_types: Dictionary of enemy type configurations.

        Returns:
            Tuple of (remaining_bullets, remaining_enemies).
        """
        bullets_to_remove = set()
        enemies_to_remove = set()

        for i, bullet in enumerate(bullets):
            for j, enemy in enumerate(enemies):
                if enemy in bullet.hit_enemies:
                    continue

                if not self.check_bullet_enemy_collision(bullet, enemy, enemy_types[enemy.type]):
                    continue

                bullet.hit_enemies.append(enemy)

                # Apply damage
                damage_dealt = enemy.take_damage(bullet.damage)
                bullet.damage -= damage_dealt

                # Check if enemy dies
                if enemy.is_dead():
                    enemies_to_remove.add(j)

                # Check if bullet should be removed
                if bullet.piercing == 0 or bullet.damage <= 0:
                    bullets_to_remove.add(i)
                    break

        # Remove dead enemies and spent bullets
        remaining_enemies = [
            enemy for j, enemy in enumerate(enemies) if j not in enemies_to_remove
        ]
        remaining_bullets = [
            bullet for i, bullet in enumerate(bullets) if i not in bullets_to_remove
        ]

        return remaining_bullets, remaining_enemies

    def check_enemy_player_collisions(
        self,
        enemies: List[Enemy],
        player: Player,
        enemy_types: dict,
    ) -> Player:
        """Check all enemy-player collisions and update player health.

        Args:
            enemies: List of active enemies.
            player: The player to check against.
            enemy_types: Dictionary of enemy type configurations.

        Returns:
            Updated player entity.
        """
        for enemy in enemies[:]:
            if not self.check_enemy_player_collision(enemy, player, enemy_types[enemy.type]):
                continue

            # Apply damage and remove enemy
            player.take_damage(enemy_types[enemy.type]["damage"])
            enemies.remove(enemy)

        return player

    def _get_distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate the Euclidean distance between two points."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
