"""Healing supplements have one finite pool shared across an entire cast."""

import unittest

from game.ability_scripts.effects import update_summons
from game.entities.enemy import Enemy
from game.entities.player import Player
from game.systems.abilities import cast_ability
from game.systems.bullets import load_bullet_types
from game.systems.collision import CollisionSystem
from game.systems.combat_bonuses import HealingBudget, heal_from_damage
from game.systems.inventory import Inventory
from game.systems.items import create_item_catalog, effective_ability
from game.systems.weapons import projectiles_for_weapon
from game.utils.large_number import LargeNumber


class HealingBudgetTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {i['id']: i for i in create_item_catalog()}
        self.player = Player(health=1, max_health=10000)
        self.types = {'test': {'size': 30, 'resistances': {}}}

    def test_budget_spends_actual_restoration_and_does_not_bank_overhealing(self):
        budget = HealingBudget(10)
        self.player.health = self.player.max_health
        self.assertEqual(heal_from_damage(self.player, 100, 100, budget), 0)
        self.assertEqual(budget.remaining, 10)
        self.player.health = 1
        self.assertEqual(heal_from_damage(self.player, 100, 100, budget), 20)
        self.assertEqual(budget.remaining, 0)
        self.assertEqual(heal_from_damage(self.player, 100, 100, budget), 0)

    def test_shotgun_explosions_and_piercing_share_single_catalog_budget(self):
        inventory = Inventory([self.catalog['flame-blaster'], self.catalog['healing-spark']])
        inventory.assign_combination('flame-blaster', 0, 'healing-spark')
        from game.systems.combinations import CombinationEngine
        combined = CombinationEngine().evaluate_inventory(inventory, 'flame-blaster')
        shots, _, _ = projectiles_for_weapon(
            self.player, 0, combined, 0, load_bullet_types(), 1)
        self.assertTrue(all(s.healing_budget is shots[0].healing_budget for s in shots))
        budget_amount = shots[0].healing_budget.remaining
        for shot in shots:
            shot.explosion_radius = .5
            shot.piercing = 2
        enemies = [Enemy('test', x=x, health=10000) for x in (0, .2, .4)]
        CollisionSystem(200).check_bullet_enemy_collisions(
            shots, enemies, self.types, self.player)
        self.assertEqual(self.player.health, 1 + budget_amount)
        self.assertEqual(shots[0].healing_budget.remaining, 0)

    def test_sentry_volley_does_not_refresh_cast_budget(self):
        inventory = Inventory([self.catalog['sentinel-summon'], self.catalog['healing-spark']])
        inventory.assign_combination('sentinel-summon', 0, 'healing-spark')
        effective = effective_ability(inventory, inventory.get('sentinel-summon'))
        ally = cast_ability(
            effective, self.player, [], angle=0, base_speed=1, enemy_types=self.types).summon
        initial = ally.healing_budget.remaining
        enemy = Enemy('test', health=10000)
        for _ in range(4):
            ally.attack_timer = 0
            shots = update_summons([ally], [enemy], self.player, .1, 1)
            self.assertIs(shots[0].healing_budget, ally.healing_budget)
            CollisionSystem(200).check_bullet_enemy_collisions(
                shots, [enemy], self.types, self.player)
        self.assertEqual(self.player.health, 1 + initial)

    def test_area_spell_shares_budget_across_all_targets(self):
        inventory = Inventory([self.catalog['nova-blast'], self.catalog['healing-spark']])
        inventory.assign_combination('nova-blast', 0, 'healing-spark')
        effective = effective_ability(inventory, inventory.get('nova-blast'))
        enemies = [Enemy('test', health=100) for _ in range(20)]
        cast_ability(effective, self.player, enemies, angle=0, base_speed=1,
                     enemy_types=self.types, healing_bonus_pct=100)
        self.assertEqual(self.player.health,
                         1 + LargeNumber(effective['healing_budget_amount']) * 2)

    def test_standalone_heal_keeps_its_full_restoration(self):
        healing = self.catalog['healing-spark']
        result = cast_ability(healing, self.player, [], angle=0, base_speed=1,
                              enemy_types=self.types)
        self.assertEqual(result.healed, 14)
        self.assertEqual(self.player.health, 15)
