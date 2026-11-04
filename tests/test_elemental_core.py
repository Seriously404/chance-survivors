import unittest

from game.entities.enemy import Enemy
from game.entities.projectile import Projectile
from game.systems.collision import CollisionSystem
from game.systems.abilities import cast_ability
from game.entities.player import Player
from game.systems.elemental_core import apply_lingering, core_power, tick_lingering, weakened_resistances


class AlwaysRoll:
    def sample(self, elements, count):
        return list(elements)

    def random(self):
        return 0


class ElementalCoreTests(unittest.TestCase):
    def test_power_scales_and_resistance_is_reduced(self):
        low = {"rarity": "common", "level": 1}
        high = {"rarity": "legendary", "level": 11}
        self.assertGreater(core_power(high)[0], core_power(low)[0])
        self.assertGreater(core_power(high)[1], core_power(low)[1])
        self.assertGreater(core_power(high)[2], core_power(low)[2])
        self.assertLess(weakened_resistances({"fire": .5}, high)["fire"], .5)

    def test_lingering_stacks_respects_limit_and_kills_once(self):
        core = {"rarity": "legendary", "level": 1}
        enemy = Enemy("test", health=10, max_health=10)
        apply_lingering(enemy, 100, core, AlwaysRoll())
        self.assertEqual(len(enemy.elemental_lingering), core_power(core)[2])
        enemies = [enemy]
        killed = tick_lingering(enemies, 1, {"test": {"resistances": {}}})
        self.assertEqual(killed, [enemy])
        self.assertEqual(enemies, [])
        self.assertEqual(tick_lingering(enemies, 1, {"test": {}}), [])

    def test_projectiles_and_novas_apply_resistance_reduction(self):
        core = {"rarity": "legendary", "level": 1}
        enemy_types = {"test": {"size": 20, "resistances": {"fire": .8}}}
        bullet = Projectile(x=0, y=0, damage=100,
                            element="fire", elemental_core=core)
        enemy = Enemy("test", health=100, max_health=100)
        CollisionSystem(100).check_bullet_enemy_collisions(
            [bullet], [enemy], enemy_types)
        self.assertLess(enemy.health, 80)
        target = Enemy("test", health=100, max_health=100)
        ability = {"id": "nova", "type": "ability", "rarity": "common", "level": 1,
                   "stats": {"script": "nova", "cast_damage": 100, "cast_radius": 2, "element": "fire"}}
        cast_ability(ability, Player(), [target], angle=0, base_speed=1,
                     enemy_types=enemy_types, core=core)
        self.assertLess(target.health, 80)

    def test_armor_resistance_only_reduces_elemental_contact(self):
        stats = {"elemental-fire": {"size": 20, "damage": 20},
                 "normal": {"size": 20, "damage": 20}}
        collision = CollisionSystem(100)
        player = Player()
        original = player.health
        collision.check_enemy_player_collisions([Enemy("elemental-fire", damage=20)], player, stats,
                                                elemental_resistance=.5)
        self.assertEqual(original - player.health, 10)
        player = Player()
        original = player.health
        collision.check_enemy_player_collisions([Enemy("normal", damage=20)], player, stats,
                                                elemental_resistance=.5)
        self.assertEqual(original - player.health, 20)
