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
    bullet_type: str = "rapid_fire"
    element: str = "physical"
    # Projectile effect fields
    explosion_radius: float = 0.0
    bounces_remaining: int = 0
    homing_strength: float = 0.0
    exploded: bool = False

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
        bullet_type: str = "rapid_fire",
        element: str = "physical",
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
            bullet_type=bullet_type,
            element=element,
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

    def steer_towards(self, enemies: List[Any], dt: float) -> None:
        """Steer the projectile towards the nearest living unhit enemy.
        
        Args:
            enemies: List of enemy objects to check.
            dt: Delta time for steering strength.
        """
        import math
        nearest = None
        nearest_dist = float("inf")
        for enemy in enemies:
            if enemy.is_dead() or enemy in self.hit_enemies:
                continue
            dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = enemy
        
        if nearest is None:
            return
        
        angle = math.atan2(nearest.y - self.y, nearest.x - self.x)
        blend = min(1.0, self.homing_strength * dt)
        self.dx = self.dx * (1 - blend) + math.cos(angle) * blend
        self.dy = self.dy * (1 - blend) + math.sin(angle) * blend
        mag = math.hypot(self.dx, self.dy)
        if mag > 0:
            self.dx /= mag
            self.dy /= mag

    def detonate(self, enemies: List[Any], collision_system) -> List[Any]:
        """Detonate explosive projectile, damaging all enemies in radius.
        
        Args:
            enemies: List of enemy objects.
            collision_system: CollisionSystem instance for distance checks.
            
        Returns:
            List of enemies damaged by explosion.
        """
        if self.explosion_radius <= 0 or self.exploded:
            return []
        
        self.exploded = True
        damaged = []
        for enemy in enemies:
            if enemy in self.hit_enemies:
                continue
            dist = collision_system._get_distance(self.x, self.y, enemy.x, enemy.y)
            hit_dist = (10.0 + 5.0) / collision_system.pixels_per_unit  # enemy size + bullet radius
            if dist <= min(self.explosion_radius, hit_dist):
                self.hit_enemies.append(enemy)
                damaged.append(enemy)
        return damaged
