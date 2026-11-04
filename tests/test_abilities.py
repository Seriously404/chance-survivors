"""Headless tests for castable active abilities."""

import unittest

from client.input import InputHandler
from game.config.settings import enemy_types
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.abilities import ability_cooldown, cast_ability
from game.systems.elements import apply_elemental_damage


class ActiveAbilityTests(unittest.TestCase):
    def test_hotkeys_map_to_all_ten_ability_slots(self) -> None:
        import pygame

        handler = InputHandler()
        actions = []
        for key in (pygame.K_1, pygame.K_2, pygame.K_9, pygame.K_0):
            handler._handle_keydown(key, actions)
        self.assertEqual(
            actions,
            ["ability_cast:0", "ability_cast:1", "ability_cast:8", "ability_cast:9"],
        )

    def test_projectile_cast_uses_elemental_damage_stats(self) -> None:
        item = {
            "id": "test-firebolt",
            "type": "ability",
            "level": 1,
            "stats": {
                "cooldown": 4,
                "cast_type": "projectile",
                "cast_damage": 20,
                "element": "fire",
                "cast_speed_modifier": 3,
            },
        }
        result = cast_ability(
            item,
            Player(),
            [],
            angle=0.5,
            base_speed=1.0,
            enemy_types=enemy_types,
            damage_bonus_pct=25,
        )

        self.assertIsNotNone(result.projectile)
        self.assertEqual(result.projectile.element, "fire")
        self.assertEqual(result.projectile.damage, 25)
        self.assertEqual(ability_cooldown(item), 4.0)

    def test_nova_damages_and_removes_killed_enemies(self) -> None:
        item = {
            "id": "test-nova",
            "type": "ability",
            "level": 1,
            "stats": {
                "cooldown": 5,
                "cast_type": "nova",
                "cast_damage": 20,
                "cast_radius": 0.5,
                "element": "fire",
            },
        }
        enemy = Enemy.create_from_type("basic", enemy_types["basic"], 0.1, 0)
        enemies = [enemy]
        result = cast_ability(
            item,
            Player(),
            enemies,
            angle=0,
            base_speed=1,
            enemy_types=enemy_types,
        )

        self.assertEqual(result.killed_enemies, [enemy])
        self.assertEqual(enemies, [])
        self.assertEqual(
            apply_elemental_damage(20, "fire", {"fire": 0.5}),
            10,
        )

    def test_heal_is_capped_and_does_not_consume_when_full(self) -> None:
        item = {
            "id": "test-heal",
            "type": "ability",
            "level": 1,
            "stats": {"cooldown": 6, "cast_type": "heal", "heal_amount": 30},
        }
        player = Player(health=90, max_health=100)
        outcome = cast_ability(
            item,
            player,
            [],
            angle=0,
            base_speed=1,
            enemy_types=enemy_types,
        )
        self.assertEqual(outcome.healed, 10)
        self.assertEqual(player.health, 100)

        full_health_outcome = cast_ability(
            item,
            player,
            [],
            angle=0,
            base_speed=1,
            enemy_types=enemy_types,
        )
        self.assertFalse(full_health_outcome.consumed)

    def test_rejects_non_ability_and_invalid_cooldown(self) -> None:
        with self.assertRaises(ValueError):
            ability_cooldown({"type": "weapon", "stats": {"cooldown": 2}})
        with self.assertRaises(ValueError):
            ability_cooldown({"type": "ability", "stats": {"cooldown": 0}})


if __name__ == "__main__":
    unittest.main()
