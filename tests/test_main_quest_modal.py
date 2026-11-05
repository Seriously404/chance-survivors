"""Main quest offers, atomic starter grants and resumable reserve migration."""

from copy import deepcopy
import random
import unittest

from game.systems.inventory import Inventory, _item
from game.systems.items import create_initial_inventory
from game.systems.quests import QuestManager


def offered_manager(quest_id):
    manager = QuestManager(rng=random.Random(7))
    manager.register_level(8)
    # Deterministic fixture for a specific offered alternative.
    manager.main_offer_ids = ['main-engineer', quest_id, 'main-glass-cannon'
                              if quest_id != 'main-glass-cannon' else 'main-bastion']
    return manager


class MainQuestModalTests(unittest.TestCase):
    def test_unlock_has_fixed_engineer_and_two_distinct_sampled_choices(self):
        manager = QuestManager(rng=random.Random(7))
        self.assertFalse(manager.pending_main_choice)
        manager.register_level(8)
        state = manager.main_choice_state()
        self.assertTrue(state['pending'])
        self.assertEqual(state['offers'][0]['id'], 'main-engineer')
        self.assertFalse(state['offers'][0]['power_selectable'])
        self.assertTrue(all(offer['power_selectable']
                        for offer in state['offers'][1:]))
        self.assertEqual(len(set(manager.main_offer_ids)), 3)
        self.assertGreater(len([bp for bp in manager.blueprints
                                if bp['quest_type'] == 'main']), 3)

    def test_reroll_is_once_disjoint_and_persists_across_resume(self):
        manager = QuestManager(rng=random.Random(7))
        manager.register_level(8)
        original = manager.main_offer_ids[:]
        restored = QuestManager.from_save_state(manager.to_save_state())
        self.assertEqual(restored.main_offer_ids, original)
        self.assertTrue(restored.reroll_main_offers())
        self.assertEqual(restored.main_offer_ids[0], 'main-engineer')
        self.assertFalse(set(original[1:]) & set(restored.main_offer_ids[1:]))
        resumed = QuestManager.from_save_state(restored.to_save_state())
        self.assertFalse(resumed.reroll_main_offers())
        self.assertEqual(resumed.main_offer_ids, restored.main_offer_ids)
        self.assertEqual(resumed.main_choice_state()['rerolls_remaining'], 0)

    def test_skip_resolves_pending_choice_permanently(self):
        manager = QuestManager()
        manager.register_level(8)
        self.assertTrue(manager.decline_main_quest())
        self.assertFalse(manager.pending_main_choice)
        manager.register_level(30)
        restored = QuestManager.from_save_state(manager.to_save_state())
        self.assertFalse(restored.pending_main_choice)
        self.assertFalse(restored.reroll_main_offers())

    def test_custom_power_increases_challenge_and_survives_save(self):
        previous = None
        for power in (1.05, 1.234, 2.):
            manager = offered_manager('main-aggressor')
            inventory = create_initial_inventory()
            report = manager.choose_main_quest('main-aggressor', inventory,
                                               score_power=power)
            self.assertIn('starter-rapid', report['unequipped'])
            self.assertTrue(any(inventory.active_slots['abilities']))
            self.assertFalse(manager.pending_main_choice)
            restored = QuestManager.from_save_state(manager.to_save_state())
            self.assertEqual(restored.main_quest.reward_power, power)
            self.assertFalse(restored.can_equip({'type': 'weapon'}))
            modifiers = restored.challenge_modifiers()
            if previous:
                self.assertTrue(
                    all(modifiers[key] > previous[key] for key in modifiers))
            previous = modifiers

    def test_engineer_fixed_power_grants_usable_support_build(self):
        manager = QuestManager()
        manager.register_level(8)
        inventory = create_initial_inventory()
        before = deepcopy(inventory.items)
        with self.assertRaisesRegex(ValueError, 'fixed'):
            manager.choose_main_quest(
                'main-engineer', inventory, score_power=2)
        self.assertEqual(inventory.items, before)
        self.assertIsNone(manager.main_quest)
        result = manager.choose_main_quest('main-engineer', inventory)
        self.assertEqual(len(result['granted']), 5)
        self.assertIn('starter-fire-rune', inventory.seen_ability_definitions)
        self.assertTrue({'engineer-turret', 'engineer-wall', 'engineer-overclock',
                         'engineer-repair-pulse'} <= inventory.seen_ability_definitions)
        for item_id in result['granted']:
            self.assertTrue(manager.can_equip(inventory.get(item_id)))
        self.assertTrue(
            manager.can_use_supplement(
                inventory.get('starter-fire-rune')))
        self.assertFalse(manager.can_equip(inventory.get('starter-fire-rune')))
        manager.register_defense_wave(9)
        self.assertFalse(manager.main_quest.completed)
        restored = QuestManager.from_save_state(manager.to_save_state())
        restored.register_defense_wave(10)
        self.assertTrue(restored.main_quest.completed)

    def test_full_inventory_reserves_and_restores_whole_combinations(self):
        manager = QuestManager()
        manager.register_level(8)
        inventory = create_initial_inventory()
        for index in range(inventory.CAPACITY - len(inventory.items)):
            inventory.add(_item(f'spare-{index}', 'Spare Rifle', 'weapon',
                                'common', 1, {'damage': 1}))
        inventory.assign_combination('spare-0', 0, 'spare-1')
        original_ids = {item['id'] for item in inventory.items}
        report = manager.choose_main_quest('main-engineer', inventory)
        self.assertEqual(len(inventory.items), inventory.CAPACITY)
        self.assertGreater(report['stored'], 0)
        all_ids = {item['id']
                   for item in inventory.items + manager.quest_storage}
        self.assertEqual(all_ids, original_ids | set(report['granted']))
        Inventory._validate_combination_records(inventory.items)
        Inventory._validate_combination_records(manager.quest_storage)
        restored = QuestManager.from_save_state(manager.to_save_state())
        for item in inventory.items[:]:
            if item['id'].startswith('spare-'):
                inventory.items.remove(item)
                if len(inventory.items) <= inventory.CAPACITY - \
                        report['stored']:
                    break
        restored.recover_stored_items(inventory)
        self.assertFalse(restored.quest_storage)
        self.assertEqual(inventory.get('spare-0')['combinations'], ['spare-1'])
        Inventory._validate_combination_records(inventory.items)

    def test_selection_rejects_unoffered_or_invalid_power_atomically(self):
        manager = offered_manager('main-aggressor')
        inventory = create_initial_inventory()
        for quest_id, power in (('main-luckmaster', 1.5),
                                ('main-aggressor', float('nan')),
                                ('main-aggressor', 2.01)):
            before = manager.to_save_state()
            items = deepcopy(inventory.items)
            with self.assertRaises(ValueError):
                manager.choose_main_quest(
                    quest_id, inventory, score_power=power)
            self.assertEqual(manager.to_save_state(), before)
            self.assertEqual(inventory.items, items)

    def test_empty_restricted_build_receives_a_valid_offensive_starter(self):
        for quest_id in ('main-aggressor', 'main-luckmaster', 'main-ballistics',
                         'main-pyromancer', 'main-glass-cannon'):
            with self.subTest(quest=quest_id):
                manager = offered_manager(quest_id)
                inventory = Inventory()
                manager.choose_main_quest(quest_id, inventory, score_power=1.2)
                active = [inventory.get(item_id) for category in ('weapons', 'abilities')
                          for item_id in inventory.active_slots[category] if item_id]
                self.assertTrue(active)
                self.assertTrue(all(manager.can_activate(
                    item, inventory) for item in active))

    def test_old_save_migrates_to_pending_choice_and_invalid_offers_reject(
            self):
        manager = QuestManager()
        manager.register_level(8)
        state = manager.to_save_state()
        state['version'] = 1
        for key in ('main_offer_ids', 'main_offer_seed',
                    'main_reroll_used', 'quest_storage'):
            state.pop(key)
        restored = QuestManager.from_save_state(state)
        self.assertTrue(restored.pending_main_choice)
        self.assertEqual(len(restored.main_choice_state()['offers']), 3)
        damaged = restored.to_save_state()
        damaged['main_offer_ids'] = ['main-engineer'] * 3
        with self.assertRaises(ValueError):
            QuestManager.from_save_state(damaged)


if __name__ == '__main__':
    unittest.main()
