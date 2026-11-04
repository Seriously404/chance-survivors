"""Headless tests for castable active abilities."""

import unittest

from client.input import InputHandler
from game.config.settings import enemy_types
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.abilities import ability_cooldown, cast_ability
from game.systems.elements import apply_elemental_damage


class ActiveAbilityTests(unittest.TestCase):
    def test_teleport_keeps_existing_enemies(self):
        player = Player()
        enemy = Enemy("basic", x=1, y=0)
        enemies = [enemy]
        item = {"id": "blink", "type": "ability", "stats": {
            "script": "teleport", "teleport_range": 2}}
        cast_ability(item, player, enemies, angle=0,
                     base_speed=1, enemy_types=enemy_types)
        self.assertEqual(player.x, 2)
        self.assertEqual(enemies, [enemy])
        self.assertEqual(enemy.x, 1)

    def test_hotkeys_map_to_all_ten_ability_slots(self) -> None:
        import pygame

        pygame.init()
        handler = InputHandler()
        for key in (pygame.K_1, pygame.K_2, pygame.K_9, pygame.K_0):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        _, _, actions = handler.process_events()
        self.assertEqual(actions, [])
        for key in (pygame.K_1, pygame.K_2, pygame.K_9, pygame.K_0):
            pygame.event.post(pygame.event.Event(pygame.KEYUP, key=key))
        _, _, actions = handler.process_events()
        self.assertEqual(
            actions,
            ["ability_cast:0", "ability_cast:1",
                "ability_cast:8", "ability_cast:9"],
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


class CatalogAbilityTests(unittest.TestCase):
    def test_every_catalog_ability_casts_its_configured_script(self):
        from game.systems.items import create_item_catalog
        abilities = [item for item in create_item_catalog()
                     if item['type'] == 'ability']
        self.assertTrue(abilities)
        for ability in abilities:
            with self.subTest(ability=ability['id']):
                self.assertIn('script', ability['stats'])
                result = cast_ability(ability, Player(health=50), [], angle=0,
                                      base_speed=1, enemy_types=enemy_types)
                self.assertTrue(result.consumed)

    def test_blink_moves_toward_aim(self):
        from game.systems.items import create_item_catalog
        item = next(i for i in create_item_catalog()
                    if i['id'] == 'blink-step')
        player = Player()
        cast_ability(item, player, [], angle=0,
                     base_speed=1, enemy_types=enemy_types)
        self.assertGreater(player.x, 0)
        self.assertAlmostEqual(player.y, 0)

    def test_ward_absorbs_damage_and_expires(self):
        from game.systems.items import create_item_catalog
        item = next(i for i in create_item_catalog()
                    if i['id'] == 'warding-sigil')
        player = Player()
        cast_ability(item, player, [], angle=0,
                     base_speed=1, enemy_types=enemy_types)
        player.take_damage(3)
        self.assertEqual(player.health, 100)
        self.assertGreater(player.shield, 0)
        player.update_shield(100)
        self.assertEqual(player.shield, 0)
        player.take_damage(3)
        self.assertEqual(player.health, 97)

    def test_summons_attack_and_expire(self):
        from game.systems.items import create_item_catalog
        from game.ability_scripts.effects import update_summons
        for identifier in ('sentinel-summon', 'turret-deploy'):
            with self.subTest(identifier=identifier):
                item = next(i for i in create_item_catalog()
                            if i['id'] == identifier)
                player = Player()
                ally = cast_ability(item, player, [], angle=0, base_speed=1,
                                    enemy_types=enemy_types).summon
                summons = [ally]
                enemy = Enemy('basic', x=1, y=0)
                shots = update_summons(summons, [enemy], player, 0.1, 1)
                self.assertEqual(len(shots), 1)
                self.assertGreater(shots[0].damage, 0)
                update_summons(summons, [], player, 100, 1)
                self.assertFalse(summons)

    def test_crate_acquisition_preserves_and_executes_each_script(self):
        from game.systems.bazaar import BazaarManager, build_extended_catalog
        from game.systems.bazaar_service import BazaarService
        from game.systems.currency import CurrencyWallet
        from game.systems.inventory import Inventory
        from game.systems.json_loader import load_abilities
        from unittest.mock import patch

        definitions = load_abilities()
        manager = BazaarManager(build_extended_catalog())
        service = BazaarService(manager)
        wallet = CurrencyWallet()
        wallet.add('Copper', 1000000)
        inventory = Inventory()
        for definition in definitions:
            with self.subTest(ability=definition['id']):
                acquired_id = 'bought-' + definition['id']
                catalog_item = next(
                    item for item in manager.catalog if item['id'] == definition['id'])
                with patch.object(manager, 'roll_crate', return_value=catalog_item):
                    service.buy_crate('starter-crate', wallet=wallet,
                                      inventory=inventory, item_id=acquired_id, luck=1)
                inventory.equip(acquired_id, 'abilities', 0)
                equipped = inventory.get(
                    inventory.active_slots['abilities'][0])
                self.assertEqual(
                    equipped['stats']['script'], definition['stats']['script'])
                result = cast_ability(equipped, Player(health=50), [], angle=0,
                                      base_speed=1, enemy_types=enemy_types)
                self.assertTrue(result.consumed)
