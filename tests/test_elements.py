"""Tests for element tags and resistance-aware combat."""

import unittest

from game.systems.elements import apply_elemental_damage, normalize_element
from game.systems.items import create_initial_inventory
from game.systems.weapons import projectile_for_weapon


class ElementSystemTests(unittest.TestCase):
    def test_elemental_damage_reduces_against_resistance(self) -> None:
        damaged = apply_elemental_damage(20, "fire", {"fire": 0.5})
        self.assertEqual(damaged, 10)

    def test_missing_element_defaults_to_physical(self) -> None:
        self.assertEqual(normalize_element(""), "physical")
        self.assertEqual(normalize_element("Fire"), "fire")

    def test_weapon_projectile_inherits_item_element(self) -> None:
        inventory = create_initial_inventory()
        weapon = next(item for item in inventory.items if item["id"] == "starter-heavy")
        projectile, _, _ = projectile_for_weapon(
            type("Player", (), {"x": 0.0, "y": 0.0})(),
            0.0,
            weapon,
            0,
            {"heavy_shot": type("Def", (), {"damage": 20, "cooldown": 1.0, "speed_modifier": 1.0, "piercing": 0, "automatic": False})()},
            1.0,
        )
        self.assertEqual(projectile.element, "fire")


if __name__ == "__main__":
    unittest.main()
