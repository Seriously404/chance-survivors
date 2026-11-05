"""Combination rules carry separately resisted damage into live combat."""

import unittest
import json

from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.abilities import cast_ability
from game.systems.bullets import load_bullet_types
from game.systems.collision import CollisionSystem
from game.systems.combinations import CombinationEngine
from game.systems.inventory import Inventory, _item
from game.systems.items import effective_ability
from game.systems.weapons import projectile_for_weapon
from game.utils.large_number import LargeNumber


class HybridAttackTests(unittest.TestCase):
    def setUp(self):
        self.types = {"test": {"size": 30, "resistances": {"fire": .5}}}

    def test_weapon_ability_component_applies_to_hit_and_explosion(self):
        gun = _item("gun", "Gun", "weapon", "ultimate", 1, {
            "damage": 10, "cooldown": 1, "speed_modifier": 1,
            "area_radius": .5, "bullet_type": "rapid_fire"})
        fire = _item("fire", "Fire", "ability", "common", 1, {
            "script": "projectile", "cast_damage": 20, "element": "fire"})
        fire["tags"] = ["elemental"]
        heal = _item("heal", "Heal", "ability", "common", 1,
                     {"script": "heal", "heal_amount": 5})
        inventory = Inventory([gun, fire, heal])
        inventory.assign_combination("gun", 0, "fire")
        inventory.assign_combination("gun", 1, "heal")
        combined = CombinationEngine().evaluate_inventory(inventory, "gun")
        json.dumps(combined.to_dict())
        player = Player(health=100, max_health=1000)
        projectile, _, _ = projectile_for_weapon(
            player, 0, combined, 0, load_bullet_types(), 1)
        self.assertTrue(projectile.heal_on_damage)
        # Keep this test's radius small even though Ultimate scales area stats.
        projectile.explosion_radius = .5
        first = Enemy("test", health=1000, max_health=1000)
        second = Enemy("test", x=.3, health=1000, max_health=1000)
        CollisionSystem(200).check_bullet_enemy_collisions(
            [projectile], [first, second], self.types, player)
        for enemy in (first, second):
            # 200 physical + (20 fire * .35 transfer * 20 rarity * .5 resistance).
            self.assertEqual(enemy.health, LargeNumber(730))
            self.assertEqual(enemy.damage_events["physical"], LargeNumber(200))
            self.assertEqual(enemy.damage_events["fire"], LargeNumber(70))
        self.assertEqual(player.health, LargeNumber(100) + combined.stats["heal_amount"])

    def test_elemental_ability_adds_physical_weapon_damage(self):
        fire = _item("fire", "Fire", "ability", "ultimate", 1, {
            "script": "projectile", "cast_damage": 10, "element": "fire"})
        fire["tags"] = ["elemental"]
        gun = _item("gun", "Gun", "weapon", "common", 1,
                    {"damage": 20})
        inventory = Inventory([fire, gun])
        inventory.assign_combination("fire", 0, "gun")
        player = Player()
        enemy = Enemy("test", health=1000, max_health=1000)
        outcome = cast_ability(effective_ability(inventory, inventory.get("fire")),
                               player, [enemy], angle=0, base_speed=1,
                               enemy_types=self.types)
        CollisionSystem(200).check_bullet_enemy_collisions(
            [outcome.projectile], [enemy], self.types, player)
        # (200 fire * .5 resistance) + (20 physical * .35 * 20 rarity).
        self.assertEqual(enemy.health, LargeNumber(760))
        self.assertEqual(enemy.damage_events["fire"], LargeNumber(100))
        self.assertEqual(enemy.damage_events["physical"], LargeNumber(140))


if __name__ == "__main__":
    unittest.main()
