"""Collision detection system."""

import math
from typing import List, Tuple, Any

from game.entities.projectile import Projectile
from game.entities.enemy_projectile import EnemyProjectile
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.elements import resolve_damage_components
from game.systems.elemental_core import weakened_resistances, apply_lingering
from game.utils.large_number import LargeNumber


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
        self.killed_enemies: list[Enemy] = []

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

        start_x = bullet.previous_x if bullet.previous_x is not None else bullet.x
        start_y = bullet.previous_y if bullet.previous_y is not None else bullet.y
        distance = self._distance_to_segment(
            enemy.x, enemy.y, start_x, start_y, bullet.x, bullet.y)
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
        player: Player | None = None,
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
        self.killed_enemies = []

        for i, bullet in enumerate(bullets):
            start_x = bullet.previous_x if bullet.previous_x is not None else bullet.x
            start_y = bullet.previous_y if bullet.previous_y is not None else bullet.y
            dx, dy = bullet.x - start_x, bullet.y - start_y
            length_sq = dx * dx + dy * dy

            def along_path(entry):
                enemy = entry[1]
                if not length_sq:
                    return 0.0
                return max(0.0, min(1.0, ((enemy.x-start_x)*dx + (enemy.y-start_y)*dy) / length_sq))
            for j, enemy in sorted(enumerate(enemies), key=along_path):
                # Later projectiles in this same pass may overlap an enemy
                # that an earlier projectile already killed. Treat it as
                # removed immediately so the kill/reward is only reported once.
                if j in enemies_to_remove:
                    continue
                if enemy in bullet.hit_enemies:
                    continue

                if not self.check_bullet_enemy_collision(bullet, enemy, enemy_types[enemy.type]):
                    continue

                bullet.hit_enemies.append(enemy)

                # Apply damage with elemental resistances.
                resolved = resolve_damage_components(
                    bullet.damage,
                    bullet.element,
                    weakened_resistances(enemy_types[enemy.type].get(
                        "resistances", {}), bullet.elemental_core)
                    if bullet.elemental_core else enemy_types[enemy.type].get("resistances", {}),
                    bullet.damage_components,
                )
                effective_damage = sum(resolved.values(), LargeNumber(0))
                health_before = enemy.health
                enemy.take_damage(effective_damage, elemental_damage=resolved)
                if player is not None and bullet.heal_on_damage:
                    dealt = min(LargeNumber(health_before),
                                LargeNumber(effective_damage))
                    player.health = min(player.max_health,
                                        player.health + dealt)
                if bullet.elemental_core:
                    apply_lingering(enemy, bullet.damage,
                                    bullet.elemental_core)

                # Check if enemy dies
                if enemy.is_dead():
                    enemies_to_remove.add(j)
                    self.killed_enemies.append(enemy)

                # Handle explosive effect
                if bullet.explosion_radius > 0 and not bullet.exploded:
                    bullet.exploded = True
                    progress = along_path((j, enemy))
                    impact_x, impact_y = start_x + dx * progress, start_y + dy * progress
                    # Damage all enemies within explosion radius
                    for k, other_enemy in enumerate(enemies):
                        if k in enemies_to_remove:
                            continue
                        if other_enemy in bullet.hit_enemies:
                            continue
                        distance = self._get_distance(
                            impact_x, impact_y, other_enemy.x, other_enemy.y)
                        if distance <= bullet.explosion_radius:
                            bullet.hit_enemies.append(other_enemy)
                            resolved = resolve_damage_components(
                                bullet.damage,
                                bullet.element,
                                weakened_resistances(
                                    enemy_types[other_enemy.type].get("resistances", {}),
                                    bullet.elemental_core,
                                ) if bullet.elemental_core else
                                enemy_types[other_enemy.type].get("resistances", {}),
                                bullet.damage_components,
                            )
                            effective_damage = sum(resolved.values(), LargeNumber(0))
                            health_before = other_enemy.health
                            other_enemy.take_damage(effective_damage, elemental_damage=resolved)
                            if bullet.elemental_core:
                                apply_lingering(other_enemy, bullet.damage,
                                                bullet.elemental_core)
                            if player is not None and bullet.heal_on_damage:
                                dealt = min(LargeNumber(health_before),
                                            LargeNumber(effective_damage))
                                player.health = min(
                                    player.max_health, player.health + dealt)
                            if other_enemy.is_dead():
                                enemies_to_remove.add(k)
                                self.killed_enemies.append(other_enemy)

                # A bounce changes direction at the impact point and continues
                # on the next frame; the old swept path must not hit again.
                if bullet.bounces_remaining > 0:
                    progress = along_path((j, enemy))
                    impact_x, impact_y = start_x + dx * progress, start_y + dy * progress
                    target = min(
                        (other for k, other in enumerate(enemies)
                         if k not in enemies_to_remove
                         and other not in bullet.hit_enemies
                         and not other.is_dead()),
                        key=lambda other: self._get_distance(
                            impact_x, impact_y, other.x, other.y),
                        default=None,
                    )
                    if target is not None:
                        bullet.bounces_remaining -= 1
                        bullet.x, bullet.y = impact_x, impact_y
                        bullet.previous_x, bullet.previous_y = impact_x, impact_y
                        bullet.angle = math.atan2(target.y - impact_y,
                                                  target.x - impact_x)
                        bullet.dx = math.cos(bullet.angle)
                        bullet.dy = math.sin(bullet.angle)
                        break

                if bullet.piercing <= 0:
                    bullets_to_remove.add(i)
                    break
                bullet.piercing -= 1

                # Handle homing effect
                if bullet.homing_strength > 0:
                    # Find nearest unhit alive enemy
                    nearest_enemy = None
                    nearest_distance = float("inf")
                    for k, other_enemy in enumerate(enemies):
                        if k in enemies_to_remove:
                            continue
                        if other_enemy in bullet.hit_enemies:
                            continue
                        distance = self._get_distance(
                            bullet.x, bullet.y, other_enemy.x, other_enemy.y)
                        if distance < nearest_distance:
                            nearest_distance = distance
                            nearest_enemy = (k, other_enemy)
                    if nearest_enemy is not None:
                        k, target = nearest_enemy
                        # Steer towards target
                        target_x = target.x
                        target_y = target.y
                        angle_to_target = math.atan2(
                            target_y - bullet.y, target_x - bullet.x)
                        # Blend current direction with target direction
                        blend = min(1.0, bullet.homing_strength)
                        bullet.dx = bullet.dx * \
                            (1 - blend) + math.cos(angle_to_target) * blend
                        bullet.dy = bullet.dy * \
                            (1 - blend) + math.sin(angle_to_target) * blend
                        # Normalize
                        mag = math.sqrt(bullet.dx * bullet.dx +
                                        bullet.dy * bullet.dy)
                        if mag > 0:
                            bullet.dx /= mag
                            bullet.dy /= mag

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
        defense: float = 0.0,
        elemental_resistance: float = 0.0,
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
            damage = getattr(
                enemy, "damage", enemy_types[enemy.type]["damage"])
            if str(enemy.type).startswith("elemental-"):
                damage = LargeNumber(
                    damage) * (1.0 - max(0.0, min(.8, elemental_resistance)))
            player.take_damage(max(LargeNumber(1), LargeNumber(
                damage)-max(LargeNumber(0), LargeNumber(defense))))
            enemies.remove(enemy)

        return player

    def check_enemy_projectile_player_collisions(
        self,
        projectiles: List[EnemyProjectile],
        player: Player,
        defense: float = 0.0,
    ) -> Tuple[List[EnemyProjectile], list[int]]:
        """Apply and remove enemy shots that hit the player."""
        remaining: list[EnemyProjectile] = []
        damage_taken: list[int] = []
        for projectile in projectiles:
            hit_distance = (projectile.radius +
                            self.PLAYER_SIZE / 2) / self.pixels_per_unit
            start_x = projectile.previous_x if projectile.previous_x is not None else projectile.x
            start_y = projectile.previous_y if projectile.previous_y is not None else projectile.y
            if self._distance_to_segment(
                player.x,
                player.y,
                start_x,
                start_y,
                projectile.x,
                projectile.y,
            ) > hit_distance:
                remaining.append(projectile)
                continue
            damage = max(1, int(projectile.damage - max(0.0, defense)))
            player.take_damage(damage)
            damage_taken.append(damage)
        return remaining, damage_taken

    @staticmethod
    def _distance_to_segment(
        point_x: float,
        point_y: float,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
    ) -> float:
        segment_x = end_x - start_x
        segment_y = end_y - start_y
        segment_length_squared = segment_x * segment_x + segment_y * segment_y
        if segment_length_squared == 0:
            return math.hypot(point_x - start_x, point_y - start_y)
        projection = (
            (point_x - start_x) * segment_x + (point_y - start_y) * segment_y
        ) / segment_length_squared
        projection = max(0.0, min(1.0, projection))
        closest_x = start_x + projection * segment_x
        closest_y = start_y + projection * segment_y
        return math.hypot(point_x - closest_x, point_y - closest_y)

    def _get_distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate the Euclidean distance between two points."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
