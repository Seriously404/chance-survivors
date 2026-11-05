"""Critical bonuses execute once per hit across each direct attack source."""

import random
import unittest
from unittest.mock import Mock

from game.ability_scripts.effects import update_summons
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.systems.abilities import cast_ability
from game.systems.bullets import load_bullet_types
from game.systems.collision import CollisionSystem
from game.systems.criticals import critical_probability, resolve_critical_hit
from game.systems.inventory import _item
from game.systems.weapons import projectile_for_weapon
from game.utils.large_number import LargeNumber


class CriticalHitTests(unittest.TestCase):
    types = {"test": {"size": 30, "resistances": {"fire": .5}}}

    def test_chance_bounds_and_large_damage_remain_safe(self):
        self.assertEqual(critical_probability(-100), 0)
        self.assertEqual(critical_probability(1000), 1)
        self.assertEqual(critical_probability(10 ** 1000), 1)
        self.assertEqual(critical_probability(LargeNumber("1e300")), 1)
        self.assertEqual(critical_probability(float("nan")), 0)
        self.assertEqual(critical_probability(float("inf")), 1)
        components = {"fire": LargeNumber("1e300")}
        damage, critical = resolve_critical_hit(components, 100)
        self.assertTrue(critical)
        self.assertEqual(damage["fire"], LargeNumber("2e300"))
        self.assertEqual(components["fire"], LargeNumber("1e300"))

    def test_piercing_and_explosion_roll_independently_per_target(self):
        rng = Mock()
        rng.random.side_effect = [.1, .9, .1]
        collision = CollisionSystem(200, rng=rng)
        projectile = Projectile(damage=10, critical_chance=50,
                                explosion_radius=1, piercing=1)
        enemies = [Enemy("test", x=x, health=100) for x in (0, .3, .5)]
        collision.check_bullet_enemy_collisions([projectile], enemies, self.types)
        self.assertEqual([enemy.health for enemy in enemies], [80, 90, 80])
        self.assertEqual(rng.random.call_count, 3)
        self.assertEqual([enemy.critical_hit_count for enemy in enemies], [1, 0, 1])

    def test_hybrid_crit_doubles_post_resistance_components_and_actual_heal(self):
        player = Player(health=50, max_health=100)
        projectile = Projectile(damage=10, element="physical",
                                critical_chance=100, heal_on_damage=True,
                                damage_components=[{"element": "fire", "damage": 20}])
        enemy = Enemy("test", health=30)
        collision = CollisionSystem(200)
        _, enemies = collision.check_bullet_enemy_collisions(
            [projectile], [enemy], self.types, player)
        self.assertEqual(enemies, [])
        self.assertEqual(player.health, 80)
        self.assertEqual(enemy.damage_events["physical"], LargeNumber(15))
        self.assertEqual(enemy.damage_events["fire"], LargeNumber(15))

    def test_weapon_combines_own_chance_with_equipment_bonus(self):
        weapon = _item("gun", "Gun", "weapon", "common", 1,
                       {"damage": 10, "crit_chance": 30})
        projectile, _, _ = projectile_for_weapon(
            Player(), 0, weapon, 0, load_bullet_types(), 1,
            critical_chance_bonus=40)
        self.assertEqual(projectile.critical_chance, 70)

    def test_area_rolls_each_target_and_override_does_not_double_count(self):
        ability = _item("area", "Area", "ability", "common", 1,
                        {"script": "nova", "cast_damage": 10,
                         "cast_radius": 2, "element": "physical", "crit_chance": 50})
        enemies = [Enemy("test", health=100) for _ in range(3)]
        rng = Mock()
        rng.random.side_effect = [.1, .9, .1]
        cast_ability(ability, Player(), enemies, angle=0, base_speed=1,
                     enemy_types=self.types, critical_chance=50, rng=rng)
        self.assertEqual([enemy.health for enemy in enemies], [80, 90, 80])
        self.assertEqual(rng.random.call_count, 3)

    def test_summon_shots_inherit_chance_and_roll_when_they_hit(self):
        ability = _item("sentry", "Sentry", "ability", "common", 1,
                        {"script": "sentinel", "summon_damage": 10,
                         "summon_duration": 5, "crit_chance": 25})
        player = Player()
        enemy = Enemy("test", health=100)
        ally = cast_ability(ability, player, [enemy], angle=0, base_speed=1,
                            enemy_types=self.types, critical_chance=100).summon
        shots = update_summons([ally], [enemy], player, .1, 1)
        self.assertEqual(shots[0].critical_chance, 100)
        self.assertEqual(shots[0].damage, 10)
        CollisionSystem(200).check_bullet_enemy_collisions(shots, [enemy], self.types)
        self.assertEqual(enemy.health, 80)

    def test_seeded_random_stream_is_reproducible(self):
        def outcomes():
            rng = random.Random(435)
            return [resolve_critical_hit({"physical": 5}, 27, rng=rng)[1]
                    for _ in range(100)]
        self.assertEqual(outcomes(), outcomes())
        self.assertTrue(any(outcomes()))
        self.assertFalse(all(outcomes()))


if __name__ == "__main__":
    unittest.main()
