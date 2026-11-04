import unittest
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.abilities import cast_ability
from game.systems.inventory import Inventory, _item
from game.systems.items import effective_ability
from game.systems.trails import TrailSystem


class TrailTests(unittest.TestCase):
    def test_fire_combination_leaves_damaging_bounded_blink_path(self):
        blink = _item('b', 'Blink', 'ability', 'common', 1, {
            'script': 'teleport', 'teleport_range': 3})
        fire = _item('f', 'Fire', 'ability', 'common', 1, {
            'script': 'ember', 'cast_damage': 20, 'element': 'fire'})
        fire['tags'] = ['trail:fire']
        inventory = Inventory([blink, fire])
        inventory.assign_combination('b', 0, 'f')
        player = Player()
        outcome = cast_ability(effective_ability(inventory, inventory.get('b')),
                               player, [], angle=0, base_speed=1, enemy_types={})
        self.assertEqual(player.x, 3)
        self.assertIsNotNone(outcome.trail_segment)
        system = TrailSystem()
        system.emit_segment(*outcome.trail_segment)
        enemy = Enemy('basic', x=1.5, y=0, health=100, max_health=100)
        system.update([enemy], {'basic': {'resistances': {'fire': .5}}}, .5)
        self.assertLess(enemy.health, 100)
        system.update([], {}, 3)
        self.assertEqual(system.trails, [])
        system.emit_segment((0, 0), (10000, 0), 'fire', 5)
        self.assertLessEqual(len(system.trails), system.MAX_SEGMENT_TRAILS)

    def test_unmodified_blink_does_not_leave_a_trail(self):
        item = _item('b', 'Blink', 'ability', 'common', 1,
                     {'script': 'teleport', 'teleport_range': 3})
        result = cast_ability(item, Player(), [], angle=0, base_speed=1,
                              enemy_types={})
        self.assertIsNone(result.trail_segment)

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
