"""Headless projectile steering and effect-state tests."""

import math
import unittest
from unittest.mock import patch

from game.entities.enemy import Enemy
from game.entities.projectile import Projectile
from game.utils.large_number import LargeNumber


class ProjectileEffectTests(unittest.TestCase):
    def test_ricochet_redirects_at_impact_and_hits_a_second_target(self):
        from game.systems.collision import CollisionSystem

        collision = CollisionSystem(200)
        bullet = Projectile(x=0, y=0, speed=10, damage=5,
                            bounces_remaining=1)
        first = Enemy('basic', x=1, y=0, health=20, max_health=20)
        second = Enemy('basic', x=1, y=1, health=20, max_health=20)
        definitions = {'basic': {'size': 30, 'resistances': {}}}
        bullet.move(.2)
        shots, enemies = collision.check_bullet_enemy_collisions(
            [bullet], [first, second], definitions)
        self.assertEqual(shots, [bullet])
        self.assertEqual(first.health, 15)
        self.assertAlmostEqual(bullet.x, 1)
        self.assertAlmostEqual(bullet.dy, 1)
        bullet.move(.1)
        shots, enemies = collision.check_bullet_enemy_collisions(
            shots, enemies, definitions)
        self.assertEqual(second.health, 15)
        self.assertEqual(shots, [])

    def test_explosion_applies_core_to_secondary_targets(self):
        from game.systems.collision import CollisionSystem

        first = Enemy('basic', x=0, y=0, health=100, max_health=100)
        second = Enemy('basic', x=.2, y=0, health=100, max_health=100)
        bullet = Projectile(x=0, y=0, damage=20, element='fire',
                            explosion_radius=.5, elemental_core={'level': 1})
        definitions = {'basic': {'size': 30, 'resistances': {'fire': .5}}}
        with patch('game.systems.collision.apply_lingering') as lingering:
            CollisionSystem(200).check_bullet_enemy_collisions(
                [bullet], [first, second], definitions)
        self.assertEqual(first.health, second.health)
        self.assertEqual(lingering.call_count, 2)

    def test_fast_projectile_hits_first_enemy_along_its_path(self):
        from game.entities.enemy import Enemy
        from game.systems.collision import CollisionSystem
        from game.entities.projectile import Projectile
        collision = CollisionSystem(200)
        bullet = Projectile(x=0, y=0, speed=100, damage=20)
        bullet.move(.1)
        near = Enemy('basic', x=2, y=0, health=10, max_health=10)
        far = Enemy('basic', x=8, y=0, health=10, max_health=10)
        _, survivors = collision.check_bullet_enemy_collisions(
            [bullet], [far, near], {'basic': {'size': 30, 'resistances': {}}})
        self.assertEqual(survivors, [far])
        self.assertEqual(collision.killed_enemies, [near])

    def test_homing_steers_toward_nearest_living_unhit_enemy(self) -> None:
        projectile = Projectile(x=0, y=0, dx=1, dy=0,
                                damage=1, homing_strength=6)
        near = Enemy("near", x=0, y=5, health=10, max_health=10)
        far = Enemy("far", x=10, y=0, health=10, max_health=10)

        projectile.steer_towards([far, near], 0.1)

        self.assertAlmostEqual(projectile.angle, 0.6)
        self.assertAlmostEqual(math.hypot(projectile.dx, projectile.dy), 1.0)

    def test_homing_ignores_dead_and_already_hit_targets(self) -> None:
        projectile = Projectile(x=0, y=0, dx=1, dy=0,
                                damage=1, homing_strength=6)
        dead = Enemy("dead", x=0, y=10, health=0, max_health=10)
        hit = Enemy("hit", x=0, y=-10, health=10, max_health=10)
        projectile.hit_enemies.append(hit)

        projectile.steer_towards([dead, hit], 0.1)

        self.assertEqual(projectile.angle, 0)

    def test_homing_takes_shortest_turn_and_stops_at_target(self) -> None:
        projectile = Projectile(dx=-1, dy=0.01, homing_strength=10)
        enemy = Enemy("target", x=-5, y=-0.05)
        projectile.steer_towards([enemy], 1)
        self.assertAlmostEqual(projectile.angle % (2 * math.pi),
                               math.atan2(enemy.y, enemy.x) % (2 * math.pi))
        self.assertAlmostEqual(projectile.dx, math.cos(projectile.angle))
        self.assertAlmostEqual(projectile.dy, math.sin(projectile.angle))

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
