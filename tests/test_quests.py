"""Regression tests for the data-driven quest system."""

import unittest

from game.systems.items import create_item_catalog
from game.systems.quests import QuestManager
from game.entities.enemy import Enemy
from game.entities.projectile import Projectile
from game.systems.collision import CollisionSystem


class QuestManagerTests(unittest.TestCase):
    def test_transactions_count_only_after_acceptance_and_survive_save(self) -> None:
        manager = QuestManager()
        manager.register_level(12)
        ids = ('side-combo-10', 'side-fusion-5', 'side-bazaar-10')
        events = ('combinations_made', 'fusions_made', 'bazaar_purchases')
        for event in events:
            manager.register_event(event)
        for quest_id in ids:
            self.assertTrue(manager.accept(quest_id))
        for event in events:
            manager.register_event(event)
        restored = QuestManager.from_save_state(manager.to_save_state())
        self.assertEqual([q.progress for q in restored.active_quests], [1, 1, 1])
        for _ in range(4):
            restored.register_event('fusions_made')
        self.assertTrue(any(q.id == 'side-fusion-5' for q in restored.completed_quests))

    def test_elemental_quest_uses_actual_damage_and_caps_overkill(self) -> None:
        manager = QuestManager()
        manager.register_level(6)
        self.assertTrue(manager.accept('side-elemental-fire'))
        self.assertTrue(manager.accept('side-elemental-frost'))
        enemy = Enemy(type='basic', health=100, max_health=100)
        enemy.take_damage(200, elemental_damage={'fire': 150, 'frost': 50})
        for element, damage in enemy.damage_events.items():
            manager.register_elemental_damage(element, damage)
        self.assertEqual(manager.active_quests[0].progress, 75)
        self.assertEqual(manager.active_quests[1].progress, 25)
        restored = QuestManager.from_save_state(manager.to_save_state())
        restored.register_elemental_damage('fire', '1e1000')
        self.assertTrue(any(q.id == 'side-elemental-fire' for q in restored.completed_quests))

    def test_projectile_damage_is_recorded_after_resistance(self) -> None:
        enemy = Enemy(type='basic', health=100, max_health=100)
        bullet = Projectile(x=0, y=0, damage=40, element='fire')
        system = CollisionSystem(200)
        system.check_bullet_enemy_collisions(
            [bullet], [enemy], {'basic': {'size': 30, 'resistances': {'fire': .5}}})
        self.assertEqual(enemy.damage_events['fire'], 20)

    def test_necromancer_quest_requires_kill_before_summon(self) -> None:
        manager = QuestManager()
        manager.register_level(9)
        self.assertTrue(manager.accept('side-kill-necro'))
        manager.register_kill('necromancer', has_summoned=True)
        self.assertEqual(manager.active_quests[0].progress, 0)
        manager.register_kill('necromancer', has_summoned=False)
        self.assertEqual(manager.active_quests[0].progress, 1)

    def test_survival_quest_starts_at_acceptance_and_resumes(self) -> None:
        manager = QuestManager()
        manager.register_level(4)
        manager.register_time(120)
        self.assertTrue(manager.accept('side-survive-60'))
        manager.register_time(130)
        restored = QuestManager.from_save_state(manager.to_save_state())
        restored.register_time(130)
        self.assertEqual(restored.active_quests[0].progress, 10)
        restored.register_time(180)
        self.assertTrue(any(q.id == 'side-survive-60' for q in restored.completed_quests))

    def test_multiple_level_quests_complete_on_same_update(self) -> None:
        manager = QuestManager()
        manager.register_level(6)
        self.assertTrue(manager.accept('side-level-run'))
        self.assertTrue(manager.accept('side-level-10'))
        manager.register_level(25)
        self.assertEqual({q.id for q in manager.completed_quests},
                         {'side-level-run', 'side-level-10'})

    def test_quests_progress_only_after_acceptance(self) -> None:
        manager = QuestManager([{"id": "sweep", "name": "Sweep", "description": "Defeat two", "quest_type": "side",
                               "unlock_level": 1, "reward_pct": 5, "condition": "kills_total", "target": 2}])
        manager.register_kill("basic")
        self.assertEqual(manager.total_bonus_pct(), 0)
        self.assertTrue(manager.accept("sweep"))
        manager.register_kill("basic")
        self.assertEqual(manager.active_quests[0].progress, 1)
        manager.register_kill("basic")
        self.assertEqual(manager.total_bonus_pct(), 5)

    def test_unlocks_side_and_main_quests_and_rewards(self) -> None:
        manager = QuestManager([
            {
                "id": "side-kill-10",
                "name": "Warmup Sweep",
                "description": "Defeat 10 enemies.",
                "quest_type": "side",
                "unlock_level": 1,
                "reward_pct": 5.0,
                "condition": "kills_total",
                "target": 10,
            },
            {
                "id": "main-level-5",
                "name": "The Bastion Run",
                "description": "Reach level 5.",
                "quest_type": "main",
                "unlock_level": 5,
                "reward_pct": 25.0,
                "condition": "level_reached",
                "target": 5,
                "restrictions": ["No sniper weapons"],
            },
        ])

        self.assertEqual(len(manager.active_quests), 0)
        self.assertTrue(manager.accept("side-kill-10"))
        self.assertEqual(manager.active_quests[0].id, "side-kill-10")

        for _ in range(10):
            manager.register_kill("basic")

        self.assertEqual(manager.total_bonus_pct(), 5.0)
        self.assertTrue(
            any(quest.id == "side-kill-10" for quest in manager.completed_quests))

        manager.register_level(5)
        self.assertTrue(manager.accept("main-level-5"))
        self.assertIsNotNone(manager.main_quest)
        self.assertTrue(
            any(quest.id == "main-level-5" for quest in manager.completed_quests))
        self.assertEqual(manager.total_bonus_pct(), 5.0)

    def test_locking_main_quest_enables_restriction_tracking(self) -> None:
        manager = QuestManager([
            {
                "id": "main-no-snipers",
                "name": "No Snipers",
                "description": "Reach level 10 without sniper weapons.",
                "quest_type": "main",
                "unlock_level": 5,
                "reward_pct": 20.0,
                "condition": "level_reached",
                "target": 10,
                "restrictions": ["No sniper weapons"],
            }
        ])

        manager.register_level(5)
        self.assertTrue(manager.accept("main-no-snipers"))
        self.assertTrue(manager.main_quest is not None)
        self.assertTrue(manager.lock_main_quest("main-no-snipers"))
        self.assertTrue(manager.main_quest.lock_on_accept)

    def test_locked_main_quest_rejects_tagged_equipment_permanently(self) -> None:
        manager = QuestManager([
            {
                "id": "main-no-snipers",
                "name": "No Snipers",
                "description": "Reach level 10 without sniper weapons.",
                "quest_type": "main",
                "unlock_level": 5,
                "reward_pct": 20.0,
                "condition": "level_reached",
                "target": 10,
                "restrictions": ["Do not equip sniper weapons"],
                "forbidden_item_tags": ["sniper"],
            }
        ])
        manager.register_level(5)
        self.assertTrue(manager.accept("main-no-snipers"))
        sniper = {"id": "sniper-instance", "tags": ["SnIpEr"]}
        rifle = {"id": "rifle-instance", "tags": ["rifle"]}

        self.assertTrue(manager.set_main_quest_lock("main-no-snipers", True))
        self.assertFalse(manager.can_equip(sniper))
        self.assertTrue(manager.can_equip(rifle))
        restored = QuestManager.from_save_state(
            manager.to_save_state(),
            [
                {
                    "id": "main-no-snipers",
                    "name": "No Snipers",
                    "description": "Reach level 10 without sniper weapons.",
                    "quest_type": "main",
                    "unlock_level": 5,
                    "reward_pct": 20.0,
                    "condition": "level_reached",
                    "target": 10,
                    "forbidden_item_tags": ["sniper"],
                }
            ],
        )
        self.assertFalse(restored.can_equip(sniper))
        self.assertFalse(manager.set_main_quest_lock("main-no-snipers", False))
        self.assertFalse(manager.can_equip(sniper))

    def test_main_restriction_lock_refuses_conflicting_equipped_items(self) -> None:
        manager = QuestManager([
            {
                "id": "main-no-snipers",
                "name": "No Snipers",
                "description": "Reach level 10 without sniper weapons.",
                "quest_type": "main",
                "unlock_level": 5,
                "reward_pct": 20.0,
                "condition": "level_reached",
                "target": 10,
                "forbidden_item_tags": ["sniper"],
            }
        ])
        manager.register_level(5)
        self.assertFalse(manager.accept("main-no-snipers",
                         [{"id": "sniper", "tags": ["sniper"]}]))
        self.assertIsNone(manager.main_quest)
        self.assertTrue(manager.accept("main-no-snipers", []))
        self.assertTrue(manager.main_quest.lock_on_accept)

    def test_sniper_definition_tag_survives_inventory_creation(self) -> None:
        sniper = next(
            item for item in create_item_catalog()
            if item["id"] == "lantern-sniper"
        )

        self.assertIn("sniper", sniper["tags"])


if __name__ == "__main__":
    unittest.main()
