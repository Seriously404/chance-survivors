"""Tests for rarity scaling throughout the shared item stat pipeline."""

import unittest
from unittest.mock import patch

from game.entities.player import Player
from game.systems.abilities import ability_cooldown, cast_ability
from game.systems.bazaar import BazaarManager
from game.systems.bazaar_service import BazaarService
from game.systems.bullets import load_bullet_types
from game.systems.currency import CurrencyWallet
from game.systems.inventory import Inventory
from game.systems.items import item_stat, player_bonuses
from game.systems.json_loader import load_item_level_scaling, load_rarity_scaling
from game.systems.numbers import LargeNumber
from game.systems.weapons import projectile_for_weapon


class RarityScalingTests(unittest.TestCase):
    def test_asset_contains_valid_monotonic_rarity_and_tier_multipliers(self) -> None:
        scaling = load_rarity_scaling()

        self.assertEqual(scaling["multipliers"]["common"], 1.0)
        self.assertEqual(scaling["multipliers"]["ultimate"], 20.0)
        self.assertEqual(scaling["ultimate_tier_growth"], 1.1)

    def test_rarity_scales_weapon_stats_and_reduces_cooldown(self) -> None:
        weapon = {
            "id": "rare-rifle",
            "type": "weapon",
            "rarity": "rare",
            "level": 1,
            "stats": {"damage": 10, "cooldown": 1.8, "speed_modifier": 2.0},
        }

        projectile, cooldown, _ = projectile_for_weapon(
            Player(),
            0.0,
            weapon,
            0,
            load_bullet_types(),
            1.0,
        )

        self.assertEqual(projectile.damage, 22)
        self.assertAlmostEqual(cooldown, 0.8)
        self.assertAlmostEqual(item_stat(weapon, "speed_modifier"), 4.5)

    def test_ability_damage_and_cooldown_use_rarity_scaled_stats(self) -> None:
        ability = {
            "id": "epic-bolt",
            "type": "ability",
            "rarity": "epic",
            "level": 1,
            "stats": {
                "cooldown": 10,
                "cast_type": "projectile",
                "cast_damage": 20,
                "cast_speed_modifier": 2.0,
            },
        }

        outcome = cast_ability(
            ability,
            Player(),
            [],
            angle=0,
            base_speed=1,
            enemy_types={},
        )

        self.assertEqual(outcome.projectile.damage, 70)
        self.assertAlmostEqual(outcome.projectile.speed, 7.0)
        self.assertAlmostEqual(ability_cooldown(ability), 10 / 3.5)

    def test_rarity_affects_passive_armor_and_relic_bonuses(self) -> None:
        inventory = Inventory([
            {
                "id": "rare-coat",
                "name": "Rare Coat",
                "type": "armor",
                "rarity": "rare",
                "level": 1,
                "stats": {"defense": 5},
                "combinations": [None] * 3,
            },
            {
                "id": "epic-relic",
                "name": "Epic Relic",
                "type": "relic",
                "rarity": "epic",
                "level": 1,
                "stats": {"luck": 2},
                "combinations": [None] * 3,
            },
        ])
        inventory.equip("rare-coat", "armor", 0)

        bonuses = player_bonuses(inventory)

        self.assertEqual(bonuses["defense"], 11.25)
        self.assertEqual(bonuses["luck"], 8.0)

    def test_ultimate_tier_growth_and_level_growth_compose(self) -> None:
        item = {
            "rarity": "ultimate",
            "ultimate_tier": 100,
            "level": 3,
            "stats": {"damage": 10},
        }

        self.assertAlmostEqual(
            item_stat(item, "damage"),
            10 * 1.2 * 20.0 * 1.1**99,
        )
        with self.assertRaisesRegex(ValueError, "Ultimate rarity tier"):
            item_stat({**item, "ultimate_tier": 101}, "damage")

    def test_level_growth_adds_configured_stat_amounts_before_rarity(self) -> None:
        item = {
            "rarity": "rare",
            "level": 4,
            "stats": {"damage": 10, "cooldown": 10},
        }

        self.assertAlmostEqual(item_stat(item, "damage"), 10 * 1.3 * 2.25)
        self.assertAlmostEqual(item_stat(item, "cooldown"), 10 * 0.94 / 2.25)
        self.assertAlmostEqual(
            item_stat({**item, "level": 1000}, "cooldown"),
            0.05,
        )

    def test_level_growth_reaches_weapon_ability_and_passive_outputs(self) -> None:
        weapon = {
            "id": "levelled-rifle",
            "type": "weapon",
            "rarity": "rare",
            "level": 4,
            "stats": {"damage": 10, "cooldown": 1.8},
        }
        projectile, cooldown, _ = projectile_for_weapon(
            Player(),
            0.0,
            weapon,
            0,
            load_bullet_types(),
            1.0,
        )
        self.assertEqual(projectile.damage, 29)
        self.assertAlmostEqual(cooldown, 1.8 * 0.94 / 2.25)

        ability = {
            "id": "levelled-bolt",
            "type": "ability",
            "rarity": "common",
            "level": 4,
            "stats": {"cooldown": 10, "cast_type": "projectile", "cast_damage": 20},
        }
        outcome = cast_ability(
            ability,
            Player(),
            [],
            angle=0,
            base_speed=1,
            enemy_types={},
        )
        self.assertEqual(outcome.projectile.damage, 26)
        self.assertAlmostEqual(ability_cooldown(ability), 9.4)

        inventory = Inventory([{
            "id": "levelled-coat",
            "name": "Levelled Coat",
            "type": "armor",
            "rarity": "rare",
            "level": 4,
            "stats": {"defense": 5},
            "combinations": [None] * 3,
        }])
        inventory.equip("levelled-coat", "armor", 0)
        self.assertAlmostEqual(player_bonuses(inventory)[
                               "defense"], 5 * 1.3 * 2.25)

    def test_paid_level_upgrade_changes_stats_through_shared_pipeline(self) -> None:
        item = {
            "id": "upgradeable-rifle",
            "name": "Upgradeable Rifle",
            "type": "weapon",
            "rarity": "rare",
            "level": 1,
            "stats": {"damage": 10, "cooldown": 1.8},
            "combinations": [None] * 3,
        }
        inventory = Inventory([item])
        wallet = CurrencyWallet()
        wallet.add("Gold", LargeNumber(100))
        service = BazaarService(BazaarManager([]))

        service.upgrade_level(
            item["id"],
            wallet=wallet,
            inventory=inventory,
        )

        self.assertEqual(item["level"], 2)
        self.assertEqual(wallet.get("Gold"), LargeNumber(94))
        self.assertAlmostEqual(item_stat(item, "damage"), 24.75)
        self.assertAlmostEqual(item_stat(item, "cooldown"), 1.8 * 0.98 / 2.25)

    def test_level_scaling_asset_is_validated(self) -> None:
        self.assertEqual(
            load_item_level_scaling(),
            {
                "default_addition_rate": 0.1,
                "stat_addition_rates": {"cooldown": -0.02},
                "minimum_values": {"cooldown": 0.05},
            },
        )
        malformed = {
            "version": 1,
            "default_addition_rate": float("nan"),
            "stat_addition_rates": {},
            "minimum_values": {},
        }
        with patch("game.systems.json_loader.load_json_asset", return_value=malformed):
            with self.assertRaisesRegex(ValueError, "Default item level addition rate"):
                load_item_level_scaling()
        malformed["default_addition_rate"] = 0.1
        malformed["stat_addition_rates"] = {"cooldown": 10**400}
        with patch("game.systems.json_loader.load_json_asset", return_value=malformed):
            with self.assertRaisesRegex(ValueError, "cooldown"):
                load_item_level_scaling()

    def test_item_stats_reject_non_finite_level_results(self) -> None:
        item = {
            "rarity": "common",
            "level": 10**400,
            "stats": {"damage": 10},
        }
        with self.assertRaisesRegex(ValueError, "level scaling exceeded"):
            item_stat(item, "damage")

    def test_ability_cooldown_rejects_non_numeric_raw_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive number"):
            ability_cooldown({
                "type": "ability",
                "rarity": "rare",
                "stats": {"cooldown": "fast"},
            })

    def test_rarity_asset_validation_rejects_bad_values(self) -> None:
        malformed = {
            "version": 1,
            "multipliers": {
                "common": 1,
                "uncommon": 1.4,
                "rare": float("nan"),
                "epic": 2.5,
                "legendary": 3.5,
                "mythical": 5,
                "ultimate": 8,
            },
            "ultimate_tier_growth": 1.02,
        }
        with patch("game.systems.json_loader.load_json_asset", return_value=malformed):
            with self.assertRaisesRegex(ValueError, "rare"):
                load_rarity_scaling()

    def test_rarity_asset_validation_rejects_decreasing_multipliers(self) -> None:
        malformed = {
            "version": 1,
            "multipliers": {
                "common": 1,
                "uncommon": 1.4,
                "rare": 1.3,
                "epic": 2.5,
                "legendary": 3.5,
                "mythical": 5,
                "ultimate": 8,
            },
            "ultimate_tier_growth": 1.02,
        }
        with patch("game.systems.json_loader.load_json_asset", return_value=malformed):
            with self.assertRaisesRegex(ValueError, "must not decrease"):
                load_rarity_scaling()


if __name__ == "__main__":
    unittest.main()
