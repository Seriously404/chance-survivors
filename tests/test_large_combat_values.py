"""Cross-system checks for scaled enemy and player health values."""

import unittest

from game.entities.enemy import Enemy
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.systems.collision import CollisionSystem
from game.utils.large_number import LargeNumber


class LargeCombatValueTests(unittest.TestCase):
    def test_projectile_collision_kills_enemy_beyond_float_range(self) -> None:
        stats = {
            "max_health": LargeNumber("1e1000"),
            "damage": LargeNumber("1e500"),
            "size": 30,
        }
        enemy = Enemy.create_from_type("scaled", stats, 0.0, 0.0)
        bullet = Projectile(x=0.0, y=0.0, damage="1e1001")
        collision = CollisionSystem(200)

        bullets, enemies = collision.check_bullet_enemy_collisions(
            [bullet], [enemy], {"scaled": stats}
        )

        self.assertEqual(bullets, [])
        self.assertEqual(enemies, [])
        self.assertEqual(collision.killed_enemies, [enemy])
        self.assertEqual(enemy.health, 0)

    def test_enemy_damage_and_player_health_remain_large_numbers(self) -> None:
        stats = {"max_health": 100, "damage": "1e500", "size": 30}
        enemy = Enemy.create_from_type("scaled", stats, 0.0, 0.0)
        player = Player(health="1e600", max_health="1e600")
        collision = CollisionSystem(200)

        collision.check_enemy_player_collisions(
            [enemy], player, {"scaled": stats}, defense="1e450")

        expected = LargeNumber("1e600") - \
            (LargeNumber("1e500") - LargeNumber("1e450"))
        self.assertEqual(player.health, expected)
        self.assertEqual(player.max_health, LargeNumber("1e600"))
        self.assertFalse(player.health == 0)


if __name__ == "__main__":
    unittest.main()
