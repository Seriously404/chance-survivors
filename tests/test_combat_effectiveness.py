"""Real equipment bonuses reach damage and health restoration exactly once."""

import unittest

from game.ability_scripts.effects import update_summons
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.systems.abilities import cast_ability
from game.systems.bullets import load_bullet_types
from game.systems.collision import CollisionSystem
from game.systems.combat_bonuses import effect_multiplier, restore_health
from game.systems.elements import resolve_damage_components
from game.systems.inventory import Inventory
from game.systems.items import (
    create_item_catalog, effective_ability, item_stat, player_bonuses,
)
from game.systems.weapons import projectile_for_weapon
from game.utils.large_number import LargeNumber


class CombatEffectivenessTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {item['id']: item for item in create_item_catalog()}
        self.player = Player(health=1, max_health=10000)
        self.types = {'test': {'size': 30, 'resistances': {'fire': .5}}}

    def bonuses(self):
        inventory = Inventory([
            self.catalog['elemental-helm'], self.catalog['glass-heart'],
        ])
        inventory.equip('elemental-helm', 'armor', 3)
        return player_bonuses(inventory)

    def test_equipped_elemental_armor_boosts_gun_damage_once_before_resistance(self):
        bonuses = self.bonuses()
        gun = self.catalog['starter-heavy']
        boosted, _, _ = projectile_for_weapon(
            self.player, 0, gun, 0, load_bullet_types(), 1,
            elemental_bonus_pct=bonuses['elemental_dmg'],
        )
        enemy = Enemy('test', health=10000, max_health=10000)
        CollisionSystem(200).check_bullet_enemy_collisions(
            [boosted], [enemy], self.types, self.player)
        expected = int(boosted.damage * effect_multiplier(
            bonuses['elemental_dmg']) * .5)
        self.assertEqual(enemy.damage_events['fire'], LargeNumber(expected))
        self.assertEqual(boosted.damage, int(item_stat(gun, 'damage')))

    def test_elemental_percent_changes_only_nonphysical_components(self):
        result = resolve_damage_components(
            LargeNumber(10), 'physical', {'fire': .5},
            [{'element': 'fire', 'damage': LargeNumber(20)},
             {'element': 'physical', 'damage': LargeNumber(5)}],
            elemental_bonus_pct=50,
        )
        self.assertEqual(result['physical'], 15)
        self.assertEqual(result['fire'], 15)

    def test_owned_glass_heart_improves_real_healing_cast(self):
        bonuses = self.bonuses()
        spell = self.catalog['healing-spark']
        outcome = cast_ability(
            spell, self.player, [], angle=0, base_speed=1,
            enemy_types=self.types,
            healing_bonus_pct=bonuses['healing_pct'],
        )
        expected = LargeNumber(item_stat(spell, 'heal_amount')) * (
            effect_multiplier(bonuses['healing_pct']))
        self.assertGreater(bonuses['healing_pct'], 0)
        self.assertEqual(outcome.healed, expected)
        self.assertEqual(self.player.health, 1 + expected)

    def test_healing_effectiveness_does_not_increase_ward_shields(self):
        spell = self.catalog['menders-ward']
        outcome = cast_ability(
            spell, self.player, [], angle=0, base_speed=1,
            enemy_types=self.types, healing_bonus_pct=100,
        )
        self.assertEqual(outcome.healed, item_stat(spell, 'heal_amount') * 2)
        self.assertEqual(self.player.shield, item_stat(spell, 'shield'))

    def test_explosion_healing_uses_actual_damage_and_modifier_once(self):
        bullet = Projectile(damage=10, element='fire', explosion_radius=1,
                            heal_on_damage=True, elemental_bonus_pct=100,
                            healing_bonus_pct=50)
        first = Enemy('test', health=3, max_health=3)
        second = Enemy('test', x=.3, health=100, max_health=100)
        CollisionSystem(200).check_bullet_enemy_collisions(
            [bullet], [first, second], self.types, self.player)
        # Each hit is 10 actual post-resistance damage, but the first
        # enemy only has 3 HP. (3 + 10) * 1.5 = 19.5 restored HP.
        self.assertEqual(self.player.health, LargeNumber('20.5'))
        self.assertEqual(second.health, 90)

    def test_area_siphon_bonuses_scale_damage_and_actual_healing_once(self):
        spell = self.catalog['shadow-siphon']
        enemy = Enemy('test', health=1000, max_health=1000)
        cast_ability(
            spell, self.player, [enemy], angle=0, base_speed=1,
            enemy_types=self.types, elemental_bonus_pct=50,
            healing_bonus_pct=100,
        )
        dealt = LargeNumber(int(item_stat(spell, 'cast_damage') * 1.5))
        self.assertEqual(1000 - enemy.health, dealt)
        self.assertEqual(self.player.health, 1 + dealt * 2)

    def test_combined_summon_snapshots_damage_and_healing_effectiveness(self):
        inventory = Inventory([
            self.catalog['sentinel-summon'], self.catalog['healing-spark'],
        ])
        inventory.assign_combination('sentinel-summon', 0, 'healing-spark')
        ally = cast_ability(
            effective_ability(inventory, inventory.get('sentinel-summon')),
            self.player, [], angle=0, base_speed=1, enemy_types=self.types,
            elemental_bonus_pct=50, healing_bonus_pct=100,
        ).summon
        enemy = Enemy('test', health=10000, max_health=10000)
        shots = update_summons([ally], [enemy], self.player, .1, 1)
        self.assertEqual(shots[0].elemental_bonus_pct, 50)
        self.assertEqual(shots[0].healing_bonus_pct, 100)
        CollisionSystem(200).check_bullet_enemy_collisions(
            shots, [enemy], self.types, self.player)
        dealt = LargeNumber(int(ally.damage * 1.5))
        self.assertEqual(10000 - enemy.health, dealt)
        self.assertEqual(self.player.health, 1 + min(
            dealt, LargeNumber(effective_ability(
                inventory, inventory.get('sentinel-summon'))['healing_budget_amount'])) * 2)

    def test_healing_clamps_to_max_and_large_values_stay_large(self):
        self.player.health = LargeNumber('1e1000')
        self.player.max_health = LargeNumber('2e1000')
        restored = restore_health(self.player, '1e1000', 50)
        self.assertEqual(restored, LargeNumber('1e1000'))
        self.assertEqual(self.player.health, self.player.max_health)
        self.assertEqual(restore_health(self.player, 10, 50), 0)

    def test_trail_damage_snapshots_elemental_effectiveness_once(self):
        from game.systems.trails import TrailSystem

        shot = Projectile(damage=100, elemental_bonus_pct=50)
        shot.trail_element = 'fire'
        trails = TrailSystem()
        trails.emit(shot, .2)
        enemy = Enemy('test', health=1000, max_health=1000)
        trails.update([enemy], self.types, .5)
        # 100 * .2 trail rate * 1.5 elemental * .5 seconds * .5 resistance.
        self.assertEqual(enemy.damage_events['fire'], LargeNumber('7.5'))

    def test_core_lingering_snapshots_elemental_effectiveness_once(self):
        from game.systems.elemental_core import apply_lingering, tick_lingering
        from unittest.mock import Mock

        enemy = Enemy('test', health=1000, max_health=1000)
        rng = Mock()
        rng.sample.return_value = ['fire']
        rng.random.return_value = 0
        apply_lingering(enemy, 100, {'level': 1}, rng,
                        elemental_bonus_pct=50)
        tick_lingering([enemy], .5, self.types)
        # 100 * .1 lingering rate * 1.5 elemental * .5 seconds * .5 resistance.
        self.assertEqual(enemy.damage_events['fire'], LargeNumber('3.75'))

    def test_invalid_effectiveness_is_rejected(self):
        for value in (True, float('nan'), float('inf'), '50'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    effect_multiplier(value)


if __name__ == '__main__':
    unittest.main()
