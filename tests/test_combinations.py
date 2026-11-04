"""Headless tests for generic and rule-driven item combinations."""

import unittest

from game.systems.combinations import CombinationEngine
from game.systems.inventory import Inventory
from game.systems.items import create_item_catalog, player_bonuses, player_speed_multiplier, effective_ability, item_stat
from game.utils.large_number import LargeNumber


def item(item_id, kind, rarity="common", level=1, stats=None, **extra):
    return {
        "id": item_id,
        "name": item_id.title(),
        "type": kind,
        "rarity": rarity,
        "level": level,
        "stats": dict(stats or {}),
        "combinations": [None] * 3,
        **extra,
    }


class CombinationEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = CombinationEngine()

    def test_live_ability_supplement_and_ultimate_cooldown(self):
        inventory = Inventory([
            item("base", "ability", "ultimate", stats={
                 "cast_damage": 5, "cooldown": 8, "script": "projectile"}),
            item("chip", "ability", stats={"cast_damage": 2, "cooldown": 5}),
        ])
        base = inventory.get("base")
        inventory.assign_combination("base", 0, "chip")
        effective = effective_ability(inventory, base)
        self.assertEqual(item_stat(effective, "cast_damage"), 140)
        self.assertAlmostEqual(item_stat(effective, "cooldown"), 0.4)
        self.assertEqual(effective["stats"]["script"], "projectile")
        inventory.assign_combination("base", 0, None)
        self.assertEqual(item_stat(effective_ability(
            inventory, base), "cast_damage"), 100)

    def test_healing_supplement_heals_on_resisted_projectile_damage_and_removal_stops_it(self):
        from game.entities.enemy import Enemy
        from game.entities.player import Player
        from game.systems.abilities import cast_ability
        from game.systems.collision import CollisionSystem
        inventory = Inventory([
            item("fire", "ability", stats={
                 "cast_damage": 20, "element": "fire", "script": "projectile"}),
            item("heal", "ability", stats={
                 "heal_amount": 5, "script": "heal"}),
        ])
        inventory.assign_combination("fire", 0, "heal")
        player = Player(health=50, max_health=100)
        enemy = Enemy("test", health=100, max_health=100)
        types = {"test": {"size": 30, "resistances": {"fire": 0.5}}}
        cast = cast_ability(effective_ability(inventory, inventory.get("fire")), player, [enemy],
                            angle=0, base_speed=1, enemy_types=types)
        CollisionSystem(50).check_bullet_enemy_collisions(
            [cast.projectile], [enemy], types, player)
        self.assertEqual(player.health, LargeNumber(60))
        inventory.assign_combination("fire", 0, None)
        cast = cast_ability(effective_ability(inventory, inventory.get("fire")), player, [enemy],
                            angle=0, base_speed=1, enemy_types=types)
        CollisionSystem(50).check_bullet_enemy_collisions(
            [cast.projectile], [enemy], types, player)
        self.assertEqual(player.health, LargeNumber(60))

    def test_healing_supplement_heals_on_area_damage_without_overkill(self):
        from game.entities.enemy import Enemy
        from game.entities.player import Player
        from game.systems.abilities import cast_ability
        inventory = Inventory([
            item("nova", "ability", stats={
                 "cast_damage": 20, "cast_radius": 2, "script": "nova"}),
            item("heal", "ability", stats={"script": "heal"}),
        ])
        inventory.assign_combination("nova", 0, "heal")
        player = Player(health=50, max_health=100)
        enemy = Enemy("test", health=4, max_health=4)
        cast_ability(effective_ability(inventory, inventory.get("nova")), player, [enemy],
                     angle=0, base_speed=1, enemy_types={"test": {"resistances": {}}})
        self.assertEqual(player.health, LargeNumber(54))

    def test_healing_supplement_follows_sentry_shot_to_enemy(self):
        from game.ability_scripts.effects import update_summons
        from game.entities.enemy import Enemy
        from game.entities.player import Player
        from game.systems.abilities import cast_ability
        from game.systems.collision import CollisionSystem

        inventory = Inventory([
            item("sentry", "ability", stats={"script": "sentinel",
                 "summon_damage": 10, "summon_duration": 5}),
            item("heal", "ability", stats={"script": "heal"}),
        ])
        inventory.assign_combination("sentry", 0, "heal")
        player = Player(health=50, max_health=100)
        enemy = Enemy("test", x=.2, health=100, max_health=100)
        types = {"test": {"size": 30, "resistances": {}}}
        outcome = cast_ability(
            effective_ability(inventory, inventory.get("sentry")), player,
            [enemy], angle=0, base_speed=1, enemy_types=types)
        shots = update_summons([outcome.summon], [enemy], player, .1, 1)
        shots[0].move(.1)
        CollisionSystem(50).check_bullet_enemy_collisions(
            shots, [enemy], types, player)
        self.assertEqual(player.health, LargeNumber(60))

    def test_generic_stats_use_additive_levels_and_both_rarities(self):
        base = item(
            "bow", "weapon", "rare", level=2,
            stats={"damage": 10, "speed": 2, "projectile": "arrow"},
        )
        supplement = item(
            "homing_lens", "relic", "epic", level=3,
            stats={"damage": 4, "homing_strength": 0},
            tags=["homing"],
        )

        combined = self.engine.evaluate(base, [supplement])

        self.assertEqual(combined.stats["damage"], LargeNumber("62.55"))
        self.assertEqual(combined.stats["speed"], LargeNumber("4.95"))
        self.assertEqual(
            combined.stats["homing_strength"], LargeNumber("2.25"))
        self.assertEqual(combined.metadata["projectile"], "arrow")
        self.assertEqual(combined.tags, ("guided", "homing"))
        self.assertIn("homing_guidance", combined.behaviors)
        self.assertEqual(combined.component_ids, ("bow", "homing_lens"))
        self.assertEqual(combined.stats["damage"], sum(
            (entry["amount"]
             for entry in combined.contributions["damage"]), LargeNumber(0)
        ))

    def test_explosive_and_elemental_rules_add_behavior_and_stat_effects(self):
        explosive = self.engine.evaluate(
            item("fireball", "ability", "uncommon",
                 stats={"damage": 3}, tags=["elemental"]),
            [item("grenade", "relic", stats={
                  "area_radius": 1}, tags=["explosive"])],
        )
        firearm = self.engine.evaluate(
            item("fire", "ability", tags=["elemental"], stats={"damage": 4}),
            [item("rifle", "weapon", stats={"damage": 8})],
        )

        self.assertEqual(explosive.stats["area_radius"], LargeNumber("4.5"))
        self.assertIn("area_damage", explosive.tags)
        self.assertIn("area_explosion", explosive.behaviors)
        self.assertIn("elemental-firearm", firearm.rules_applied)
        self.assertIn("weapon_damage_component", firearm.behaviors)
        self.assertIn("hybrid_damage", firearm.tags)

    def test_fire_and_teleport_create_a_burning_trail(self):
        combined = self.engine.evaluate(
            item("fire", "ability", stats={
                 "damage": 3}, tags=["elemental", "fire"]),
            [item("blink", "ability", stats={
                  "range": 3}, tags=["teleportation"])],
        )

        self.assertIn("fire-teleport-trail", combined.rules_applied)
        self.assertIn("burning_teleport_trail", combined.behaviors)
        self.assertIn("burning_trail", combined.tags)
        self.assertEqual(combined.stats["trail_damage"], LargeNumber(2))

    def test_catalog_components_activate_combination_rules(self):
        catalog = {entry["id"]: entry for entry in create_item_catalog()}

        explosive = self.engine.evaluate(
            catalog["starter-fire-rune"], [catalog["starter-grenade"]]
        )
        teleport = self.engine.evaluate(
            catalog["starter-fire-rune"], [catalog["starter-teleport-sigil"]]
        )

        self.assertEqual(explosive.stats["area_radius"], LargeNumber("6.5"))
        self.assertIn("area_explosion", explosive.behaviors)
        self.assertIn("burning_teleport_trail", teleport.behaviors)
        self.assertIn("homing_guidance", self.engine.evaluate(
            catalog["starter-rapid"], [catalog["starter-homing-lens"]]
        ).behaviors)

    def test_rarity_and_ultimate_subtier_scale_all_stat_contributions(self):
        combined = self.engine.evaluate(
            item("ultimate", "weapon", "ultimate",
                 stats={"damage": 2}, ultimate_tier=10),
            [item("chip", "relic", "rare", stats={"damage": 3})],
        )
        expected = (LargeNumber(2) + LargeNumber(3) * LargeNumber("2.25")) \
            * LargeNumber("20") * (LargeNumber("1.1") ** 9)

        self.assertEqual(combined.stats["damage"], expected)

    def test_inventory_evaluation_reads_assignments_without_mutating_items(self):
        inventory = Inventory([
            item("base", "weapon", "uncommon", stats={"damage": 10}),
            item("supplement", "relic", "rare", stats={"damage": 2}),
        ])
        inventory.assign_combination("base", 0, "supplement")
        original = [dict(record) for record in inventory.items]

        combined = self.engine.evaluate_inventory(inventory, "base")

        self.assertEqual(combined.component_ids, ("base", "supplement"))
        self.assertEqual(combined.stats["damage"], LargeNumber("21.75"))
        self.assertEqual(inventory.items, original)
        serialized = combined.to_dict()
        self.assertEqual(LargeNumber.from_dict(
            serialized["stats"]["damage"]), combined.stats["damage"])

    def test_equipped_armor_combinations_change_player_bonuses_once(self):
        inventory = Inventory([
            item("plate", "armor", "rare", stats={"defense": 10}),
            item("guard", "armor", "common", stats={
                 "defense": 2, "health": 3}),
        ])
        inventory.equip("plate", "armor", 0)
        inventory.assign_combination("plate", 0, "guard")

        bonuses = player_bonuses(inventory)

        self.assertEqual(bonuses["defense"], LargeNumber("27"))
        self.assertEqual(bonuses["health"], LargeNumber("6.75"))
        self.assertEqual(player_speed_multiplier(LargeNumber("1e1000")), 100.0)
        self.assertEqual(player_speed_multiplier(-100), 0.1)

    def test_invalid_levels_slots_types_rules_and_ultimate_tiers_are_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate(item("base", "weapon", level=0))
        with self.assertRaises(ValueError):
            self.engine.evaluate(item("base", "weapon", combinations=[None]), [
                                 item("a", "relic"), item("b", "relic")])
        with self.assertRaises(ValueError):
            self.engine.evaluate(item("armor", "armor"), [
                                 item("relic", "relic")])
        with self.assertRaises(ValueError):
            self.engine.evaluate(
                item("ultimate", "weapon", "ultimate", ultimate_tier=101))
        with self.assertRaises(ValueError):
            CombinationEngine(rules=[{"id": "bad", "stat_modifiers": [
                              {"stat": "damage", "operation": "power", "value": 2}]}])


if __name__ == "__main__":
    unittest.main()
