import unittest
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.abilities import cast_ability
from game.systems.inventory import Inventory, _item
from game.systems.items import effective_ability
from game.systems.trails import TrailSystem


class TrailTests(unittest.TestCase):
    def test_fire_supplement_gives_sentry_a_finite_damaging_trail(self):
        sentry = _item('s', 'Sentry', 'ability', 'common', 1, {
                       'script': 'sentinel', 'summon_damage': 10})
        fire = _item('f', 'Fire', 'ability', 'common', 1, {
                     'script': 'ember', 'element': 'fire'})
        fire['tags'] = ['trail:fire']
        sentry['combinations'] = ['f']
        inventory = Inventory([sentry, fire])
        ally = cast_ability(effective_ability(inventory, sentry), Player(), [
        ], angle=0, base_speed=1, enemy_types={}).summon
        self.assertEqual(ally.trail_element, 'fire')
        system = TrailSystem()
        system.emit(ally, .2)
        enemy = Enemy('basic', x=ally.x, y=ally.y, health=10, max_health=10)
        system.update([enemy], {'basic': {'resistances': {}}}, .5)
        self.assertLess(enemy.health, 10)
        system.update([], {}, 3)
        self.assertEqual(system.trails, [])
