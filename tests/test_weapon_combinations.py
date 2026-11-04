"""Headless projectile adapter coverage for ordinary and combined weapons."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from game.systems.bullets import load_bullet_types
from game.systems.combinations import CombinationEngine, CombinedItem
from game.systems.weapons import projectile_for_weapon, projectiles_for_weapon
from game.systems.items import create_item_catalog
from game.utils.large_number import LargeNumber


PLAYER = SimpleNamespace(x=12.0, y=34.0)


def weapon(item_id: str, stats: dict, *, rarity: str = "common") -> dict:
    return {
        "id": item_id,
        "name": item_id,
        "type": "weapon",
        "rarity": rarity,
        "level": 1,
        "stats": stats,
        "combinations": [None] * 2,
        "status": "normal",
    }


class WeaponCombinationAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bullet_types = load_bullet_types()

    def test_catalog_shotgun_and_homing_fire_and_track(self) -> None:
        catalog = {item['id']: item for item in create_item_catalog()}
        shotgun = catalog['flame-blaster']
        shots, cooldown, _ = projectiles_for_weapon(
            PLAYER, 0, shotgun, 0, self.bullet_types, 3)
        self.assertEqual(len(shots), 6)
        self.assertGreater(cooldown, 0)
        self.assertLess(shots[0].dy, 0)
        self.assertGreater(shots[-1].dy, 0)
        self.assertTrue(all(shot.element == 'fire' for shot in shots))
        guided, _, _ = projectiles_for_weapon(
            PLAYER, 0, catalog['homing-devastator'], 0, self.bullet_types, 3)
        enemy = SimpleNamespace(x=12, y=40, is_dead=lambda: False)
        guided[0].steer_towards([enemy], 0.1)
        self.assertGreater(guided[0].dy, 0)

    def test_combined_weapon_numeric_stats_and_metadata_reach_projectile(self) -> None:
        base = weapon("base", {
            "damage": 10,
            "piercing": 1,
            "speed_modifier": 2,
            "cooldown": 0.4,
            "bullet_type": "heavy_shot",
            "automatic": False,
        })
        supplement = weapon("supplement", {
            "damage": 5,
            "piercing": 2,
            "speed_modifier": 2,
            "cooldown": 0.2,
        })
        combined = CombinationEngine().evaluate(base, [supplement])

        projectile, cooldown, automatic = projectile_for_weapon(
            PLAYER, 0.0, combined, 0, self.bullet_types, 3.0
        )
        self.assertEqual(projectile.damage, LargeNumber(15))
        self.assertEqual(projectile.piercing, 3)
        self.assertEqual(projectile.bullet_type, "heavy_shot")
        self.assertEqual(projectile.speed, 12.0)
        self.assertEqual(cooldown, 0.4)
        self.assertFalse(automatic)

    def test_combined_large_damage_remains_large_number(self) -> None:
        combined = CombinationEngine().evaluate(
            weapon("large", {"damage": LargeNumber("1e1000"),
                   "speed_modifier": 1, "cooldown": 0.1}),
        )
        projectile, _, _ = projectile_for_weapon(
            PLAYER, 0.0, combined, 0, self.bullet_types, 1.0
        )
        self.assertIsInstance(projectile.damage, LargeNumber)
        self.assertEqual(projectile.damage, LargeNumber("1e1000"))

    def test_combination_behaviors_populate_projectile_effects(self) -> None:
        base = weapon("base", {
            "damage": 10,
            "speed_modifier": 1,
            "cooldown": 0.2,
            "bullet_type": "rapid_fire",
        })
        base["combinations"] = [None] * 3
        explosive = {"id": "grenade", "type": "relic", "rarity": "common", "level": 1,
                     "stats": {"area_radius": 2}, "tags": ["explosive"], "behaviors": [],
                     "combinations": [None]}
        homing = {"id": "lens", "type": "relic", "rarity": "common", "level": 1,
                  "stats": {"homing_strength": 1}, "tags": ["homing"], "behaviors": [],
                  "combinations": [None]}
        ricochet = {"id": "chip", "type": "relic", "rarity": "common", "level": 1,
                    "stats": {"bounce_count": 1}, "tags": ["ricochet"], "behaviors": [],
                    "combinations": [None]}
        combined = CombinationEngine().evaluate(
            base, [explosive, homing, ricochet])

        projectile, _, _ = projectile_for_weapon(
            PLAYER, 0.0, combined, 0, self.bullet_types, 1.0
        )

        self.assertEqual(projectile.explosion_radius, 4.0)
        self.assertEqual(projectile.homing_strength, 2.0)
        self.assertEqual(projectile.bounces_remaining, 2)

    def test_existing_dictionary_callers_keep_item_level_and_damage_bonus(self) -> None:
        item = weapon("legacy", {
            "damage": 10,
            "piercing": 1,
            "speed_modifier": 2,
            "cooldown": 0.2,
        })
        item["level"] = 3
        projectile, cooldown, automatic = projectile_for_weapon(
            PLAYER, 0.0, item, 0, self.bullet_types, 2.0, 50
        )
        # Inventory items retain the prior additive 10%-per-level damage and
        # piercing rules, and the caller's percentage bonus stays additive.
        self.assertEqual(projectile.damage, LargeNumber(18))
        self.assertEqual(projectile.piercing, 1)
        self.assertEqual(projectile.speed, 4.8)
        self.assertAlmostEqual(cooldown, 0.192)
        self.assertTrue(automatic)

    def test_unknown_bullet_types_and_invalid_or_unbounded_stats_are_rejected(self) -> None:
        invalid_type = weapon("invalid-type", {"bullet_type": "missing"})
        with self.assertRaisesRegex(ValueError, "unknown bullet type"):
            projectile_for_weapon(PLAYER, 0, invalid_type,
                                  0, self.bullet_types, 1)

        for stat, value in (
            ("damage", -1),
            ("speed_modifier", 0),
            ("piercing", -1),
            ("piercing", "1e10000"),
            ("cooldown", 0),
            ("cooldown", "1e10000"),
            ("automatic", "yes"),
        ):
            combined = CombinedItem(
                base_id="invalid",
                name="invalid",
                item_type="weapon",
                rarity="common",
                level=1,
                ultimate_tier=None,
                stats={stat: LargeNumber(
                    value)} if stat != "automatic" else {},
                metadata={stat: value} if stat == "automatic" else {},
                tags=(),
                behaviors=(),
                component_ids=("invalid",),
                rules_applied=(),
                contributions={},
            )
            with self.subTest(stat=stat, value=value), self.assertRaises(ValueError):
                projectile_for_weapon(
                    PLAYER, 0, combined, 0, self.bullet_types, 1)


if __name__ == "__main__":
    unittest.main()
