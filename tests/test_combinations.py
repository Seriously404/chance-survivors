"""Headless tests for generic and rule-driven item combinations."""

import unittest

from game.systems.combinations import CombinationEngine
from game.systems.inventory import Inventory
from game.systems.items import player_bonuses, player_speed_multiplier
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
        self.assertEqual(combined.stats["homing_strength"], LargeNumber("2.25"))
        self.assertEqual(combined.metadata["projectile"], "arrow")
        self.assertEqual(combined.tags, ("guided", "homing"))
        self.assertIn("homing_guidance", combined.behaviors)
        self.assertEqual(combined.component_ids, ("bow", "homing_lens"))
        self.assertEqual(combined.stats["damage"], sum(
            (entry["amount"] for entry in combined.contributions["damage"]), LargeNumber(0)
        ))

    def test_explosive_and_elemental_rules_add_behavior_and_stat_effects(self):
        explosive = self.engine.evaluate(
            item("fireball", "ability", "uncommon", stats={"damage": 3}, tags=["elemental"]),
            [item("grenade", "relic", stats={"area_radius": 1}, tags=["explosive"])],
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

    def test_rarity_and_ultimate_subtier_scale_all_stat_contributions(self):
        combined = self.engine.evaluate(
            item("ultimate", "weapon", "ultimate", stats={"damage": 2}, ultimate_tier=10),
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
        self.assertEqual(LargeNumber.from_dict(serialized["stats"]["damage"]), combined.stats["damage"])

    def test_equipped_armor_combinations_change_player_bonuses_once(self):
        inventory = Inventory([
            item("plate", "armor", "rare", stats={"defense": 10}),
            item("guard", "armor", "common", stats={"defense": 2, "health": 3}),
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
            self.engine.evaluate(item("base", "weapon", combinations=[None]), [item("a", "relic"), item("b", "relic")])
        with self.assertRaises(ValueError):
            self.engine.evaluate(item("armor", "armor"), [item("relic", "relic")])
        with self.assertRaises(ValueError):
            self.engine.evaluate(item("ultimate", "weapon", "ultimate", ultimate_tier=101))
        with self.assertRaises(ValueError):
            CombinationEngine(rules=[{"id": "bad", "stat_modifiers": [{"stat": "damage", "operation": "power", "value": 2}]}])


if __name__ == "__main__":
    unittest.main()
