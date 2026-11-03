"""Headless projectile steering and effect-state tests."""

import math
import unittest

from game.entities.enemy import Enemy
from game.entities.projectile import Projectile
from game.utils.large_number import LargeNumber


class ProjectileEffectTests(unittest.TestCase):
    def test_homing_steers_toward_nearest_living_unhit_enemy(self) -> None:
        projectile = Projectile(x=0, y=0, dx=1, dy=0, damage=1, homing_strength=6)
        near = Enemy("near", x=0, y=5, health=10, max_health=10)
        far = Enemy("far", x=10, y=0, health=10, max_health=10)

        projectile.steer_towards([far, near], 0.1)

        self.assertAlmostEqual(projectile.angle, 0.6)
        self.assertAlmostEqual(math.hypot(projectile.dx, projectile.dy), 1.0)

    def test_homing_ignores_dead_and_already_hit_targets(self) -> None:
        projectile = Projectile(x=0, y=0, dx=1, dy=0, damage=1, homing_strength=6)
        dead = Enemy("dead", x=0, y=10, health=0, max_health=10)
        hit = Enemy("hit", x=0, y=-10, health=10, max_health=10)
        projectile.hit_enemies.append(hit)

        projectile.steer_towards([dead, hit], 0.1)

        self.assertEqual(projectile.angle, 0)

    def test_effect_fields_validate_and_large_damage_stays_large(self) -> None:
        projectile = Projectile(
            damage="1e1000", explosion_radius=2.5, bounces_remaining=2,
            homing_strength=1.5,
        )
        self.assertEqual(projectile.damage, LargeNumber("1e1000"))
        self.assertEqual(projectile.explosion_radius, 2.5)
        self.assertEqual(projectile.bounces_remaining, 2)
        self.assertFalse(projectile.exploded)
        with self.assertRaises(ValueError):
            Projectile(explosion_radius=-1)
        with self.assertRaises(ValueError):
            Projectile(bounces_remaining=1.5)
        with self.assertRaises(ValueError):
            Projectile(homing_strength=float("inf"))


if __name__ == "__main__":
    unittest.main()
