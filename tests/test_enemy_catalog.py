"""Tests for wiring data-defined enemy types into runtime combat."""

import math
import unittest

from game.config.settings import enemy_types as legacy_enemy_types
from game.entities.enemy import Enemy
from game.entities.enemy_projectile import EnemyProjectile
from game.entities.projectile import Projectile
from game.systems.enemy_catalog import build_enemy_roster
from game.systems.enemy_abilities import update_enemy_abilities
from game.systems.enemy_ranged import update_ranged_attacks
from game.systems.runtime_probe import RuntimeProbe
from game.systems.spawner import SpawnerSystem
from game.systems.enemy_visibility import enemy_visibility_alpha
from game.systems.enemy_scaling import EnemyScaling


class EnemyCatalogTests(unittest.TestCase):
    def test_roster_keeps_legacy_types_and_adds_asset_only_ids(self) -> None:
        roster = build_enemy_roster(legacy_enemy_types)
        expected_additions = {
            "fast",
            "tank",
            "shooter",
            "swarm",
            "boss",
            "stealth",
            "elemental-fire",
            "elemental-frost",
            "elemental-shadow",
            "elemental-light",
            "elemental-nature",
            "elemental-arcane",
        }

        self.assertTrue(set(legacy_enemy_types).issubset(roster))
        self.assertTrue(expected_additions.issubset(roster))
        self.assertEqual(roster["basic"], legacy_enemy_types["basic"])
        self.assertEqual(legacy_enemy_types["basic"]["max_health"], 10)
        self.assertLess(roster["boss"]["weight"],
                        roster["elemental-fire"]["weight"])
        self.assertNotEqual(
            roster["elemental-fire"]["color"],
            roster["elemental-frost"]["color"],
        )

    def test_asset_enemy_can_be_spawned_with_its_reward_definition(self) -> None:
        roster = build_enemy_roster(legacy_enemy_types)
        spawner = SpawnerSystem({"elemental-fire": roster["elemental-fire"]})
        enemies: list[Enemy] = []

        spawner.spawn(0.0, 0.0, enemies)

        self.assertEqual(len(enemies), 1)
        self.assertEqual(enemies[0].type, "elemental-fire")
        self.assertEqual(enemies[0].currency_drop, "ember")
        self.assertEqual(enemies[0].currency_amount, 18)
        self.assertEqual(enemies[0].xp_reward, 22)

    def test_live_probe_uses_asset_enemy_resistances(self) -> None:
        probe = RuntimeProbe()
        probe.execute(
            {"action": "spawn_enemy", "type": "elemental-fire", "x": 0, "y": 0}
        )
        enemy = probe.enemies[0]
        probe.bullets.append(
            Projectile(x=0.0, y=0.0, damage=10, element="fire")
        )

        probe.execute({"action": "step", "dt": 0.01})

        self.assertEqual(enemy.health, enemy.max_health - 3)
        self.assertEqual(probe.wallet.get("Silver"), 0)
        self.assertEqual(probe.progress.total_exp, 0)

    def test_necromancer_summons_capped_non_rewarding_minions(self) -> None:
        roster = build_enemy_roster(legacy_enemy_types)
        necromancer = Enemy.create_from_type(
            "necromancer", roster["necromancer"], 0.0, 0.0
        )
        enemies = [necromancer]

        self.assertEqual(
            update_enemy_abilities(enemies, roster, 5.9, 0.0, 0.0),
            [],
        )
        spawned = update_enemy_abilities(enemies, roster, 0.1, 0.0, 0.0)

        self.assertEqual(len(spawned), 1)
        self.assertEqual(spawned[0].type, "necromancer_minion")
        self.assertFalse(spawned[0].reward_eligible)
        self.assertEqual(spawned[0].summoner_id, id(necromancer))

        for _ in range(3):
            update_enemy_abilities(enemies, roster, 6.0, 0.0, 0.0)
        self.assertEqual(
            sum(enemy.summoner_id == id(necromancer) for enemy in enemies),
            roster["necromancer"]["max_minions"],
        )

    def test_summoned_minions_cannot_be_chosen_by_regular_spawner(self) -> None:
        minion_stats = build_enemy_roster(legacy_enemy_types)[
            "necromancer_minion"]

        with self.assertRaisesRegex(ValueError, "no spawnable enemy types"):
            SpawnerSystem({"necromancer_minion": minion_stats}).spawn(
                0.0, 0.0, []
            )

    def test_killing_summoned_minion_awards_no_score_currency_or_xp(self) -> None:
        probe = RuntimeProbe()
        probe.execute(
            {"action": "spawn_enemy", "type": "necromancer", "x": 0.0, "y": 0.0}
        )
        probe.execute({"action": "step", "dt": 6.0})
        minion = next(
            enemy for enemy in probe.enemies if enemy.type == "necromancer_minion"
        )
        minion.health = 1
        minion.max_health = 1
        probe.bullets.append(
            Projectile(
                x=minion.x - 0.03,
                y=minion.y,
                speed=3.0,
                damage=10,
            )
        )

        result = probe.execute({"action": "step", "dt": 0.01})

        self.assertEqual(result["killed"], 1)
        self.assertEqual(probe.score, 0)
        self.assertTrue(
            all(amount == 0 for amount in probe.wallet.amounts.values()))
        self.assertEqual(probe.progress.total_exp, 0)

    def test_shooter_fires_only_after_cooldown_and_inside_range(self) -> None:
        roster = build_enemy_roster(legacy_enemy_types)
        shooter = Enemy.create_from_type(
            "shooter", roster["shooter"], 2.0, 0.0)
        enemies = [shooter]

        self.assertEqual(
            update_ranged_attacks(enemies, roster, 2.4, 0.0, 0.0),
            [],
        )
        shots = update_ranged_attacks(enemies, roster, 0.1, 0.0, 0.0)

        self.assertEqual(len(shots), 1)
        self.assertAlmostEqual(shots[0].dx, -1.0)
        self.assertEqual(shots[0].damage, shooter.damage)

        far_shooter = Enemy.create_from_type(
            "shooter", roster["shooter"], 5.0, 0.0)
        self.assertEqual(
            update_ranged_attacks([far_shooter], roster, 10.0, 0.0, 0.0),
            [],
        )

    def test_enemy_projectile_hit_applies_defense_and_is_consumed(self) -> None:
        probe = RuntimeProbe()
        initial_health = probe.player.health
        probe.enemy_projectiles.append(
            EnemyProjectile(0.0, 0.0, 1.0, 0.0, 2.5, 12)
        )

        remaining, damage = probe.collision.check_enemy_projectile_player_collisions(
            probe.enemy_projectiles,
            probe.player,
            defense=5,
        )

        self.assertEqual(remaining, [])
        self.assertEqual(damage, [7])
        self.assertEqual(probe.player.health, initial_health - 7)

    def test_enemy_projectile_swept_collision_prevents_tunneling(self) -> None:
        probe = RuntimeProbe()
        initial_health = probe.player.health
        projectile = EnemyProjectile(0.2, 0.0, -1.0, 0.0, 5.0, 12)
        projectile.move(0.1)

        remaining, damage = probe.collision.check_enemy_projectile_player_collisions(
            [projectile],
            probe.player,
        )

        self.assertEqual(remaining, [])
        self.assertEqual(damage, [12])
        self.assertEqual(probe.player.health, initial_health - 12)

    def test_live_probe_shooter_projectile_reaches_player(self) -> None:
        probe = RuntimeProbe()
        initial_health = probe.player.health
        probe.execute(
            {"action": "spawn_enemy", "type": "shooter", "x": 2.0, "y": 0.0}
        )

        for _ in range(35):
            probe.execute({"action": "step", "dt": 0.1})

        self.assertLess(probe.player.health, initial_health)
        self.assertEqual(probe.enemy_projectiles, [])

    def test_stealth_visibility_fades_in_with_distance(self) -> None:
        stealth_stats = build_enemy_roster(legacy_enemy_types)["stealth"]
        ordinary_stats = build_enemy_roster(legacy_enemy_types)["basic"]

        self.assertEqual(enemy_visibility_alpha(2.0, stealth_stats), 35)
        self.assertEqual(enemy_visibility_alpha(0.8, stealth_stats), 35)
        self.assertEqual(enemy_visibility_alpha(0.4, stealth_stats), 145)
        self.assertEqual(enemy_visibility_alpha(0.0, stealth_stats), 255)
        self.assertEqual(enemy_visibility_alpha(2.0, ordinary_stats), 255)

    def test_stealth_visibility_rejects_invalid_distance(self) -> None:
        with self.assertRaisesRegex(ValueError, "distance"):
            enemy_visibility_alpha(float("nan"), {"reveal_distance": 0.8})

    def test_swarm_spawn_creates_a_scaled_group_with_per_enemy_rewards(self) -> None:
        roster = build_enemy_roster(legacy_enemy_types)
        spawner = SpawnerSystem({"swarm": roster["swarm"]})
        enemies: list[Enemy] = []

        spawner.spawn(
            0.0,
            0.0,
            enemies,
            elapsed_seconds=600,
            scaling=EnemyScaling(threat_level=1),
        )

        self.assertEqual(len(enemies), 3)
        self.assertEqual({enemy.type for enemy in enemies}, {"swarm"})
        self.assertEqual(
            {enemy.currency_drop for enemy in enemies}, {"copper"})
        self.assertEqual({enemy.currency_amount for enemy in enemies}, {3})
        self.assertEqual({enemy.xp_reward for enemy in enemies}, {5})
        self.assertTrue(
            all(enemy.max_health > roster["swarm"]["max_health"] for enemy in enemies))
        self.assertEqual(len({(enemy.x, enemy.y) for enemy in enemies}), 3)
        for enemy in enemies:
            self.assertGreater(enemy.dx * -enemy.x + enemy.dy * -enemy.y, 0)
            self.assertLessEqual(math.hypot(
                enemy.x - enemies[0].x, enemy.y - enemies[0].y), 0.2)

    def test_invalid_swarm_configuration_does_not_partially_spawn(self) -> None:
        stats = {
            **build_enemy_roster(legacy_enemy_types)["swarm"],
            "spawn_group_count": 9,
        }
        enemies: list[Enemy] = []

        with self.assertRaisesRegex(ValueError, "spawn_group_count"):
            SpawnerSystem({"swarm": stats}).spawn(0.0, 0.0, enemies)

        self.assertEqual(enemies, [])


if __name__ == "__main__":
    unittest.main()
