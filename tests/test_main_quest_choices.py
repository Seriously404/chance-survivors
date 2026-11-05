import unittest

from game.systems.quests import QuestManager
from game.systems.numbers import LargeNumber


class MainQuestChoiceTests(unittest.TestCase):
    def test_three_choices_decline_and_restore(self):
        quests = QuestManager()
        quests.register_level(8)
        self.assertEqual(len(quests.main_choice_state()['offers']), 3)
        self.assertTrue(quests.decline_main_quest())
        restored = QuestManager.from_save_state(quests.to_save_state())
        self.assertFalse(
            any(q.quest_type == "main" for q in restored.available_quests()))

    def test_restrictions_and_exponent_persist_after_completion(self):
        quests = QuestManager()
        quests.register_level(8)
        rifle = {"type": "weapon", "stats": {}, "tags": []}
        sentry = {"type": "ability", "stats": {"script": "turret"}, "tags": []}
        fireball = {"type": "ability", "stats": {
            "script": "projectile"}, "tags": []}
        self.assertFalse(quests.accept("main-luckmaster", [rifle]))
        self.assertTrue(quests.accept("main-luckmaster", [sentry]))
        self.assertFalse(quests.can_equip(fireball))
        quests.register_level(15)
        self.assertEqual(quests.final_score(
            LargeNumber(100)), LargeNumber(10000))
        restored = QuestManager.from_save_state(quests.to_save_state())
        self.assertFalse(restored.can_equip(rifle))
        self.assertEqual(restored.final_score(
            LargeNumber("1e1000")), LargeNumber("1e2000"))

    def test_enemy_specific_quest_counts_only_matching_kills(self):
        quests = QuestManager()
        quests.register_level(2)
        self.assertTrue(quests.accept("side-kill-basic"))
        quests.register_kill("fast")
        self.assertEqual(quests.active_quests[0].progress, 0)
        quests.register_kill("basic")
        self.assertEqual(quests.active_quests[0].progress, 1)


if __name__ == "__main__":
    unittest.main()
