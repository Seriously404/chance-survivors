"""Behavior checks for the deterministic, real-system balance probe."""

import random
import unittest
from unittest.mock import patch

from scripts.balance_simulation import simulate


class BalanceSimulationTests(unittest.TestCase):
    def test_seed_replays_without_changing_global_random_state(self):
        before = random.getstate()
        first = simulate('kite', seconds=20, seed=7)
        self.assertEqual(random.getstate(), before)
        second = simulate('kite', seconds=20, seed=7)
        first.pop('wall_seconds')
        second.pop('wall_seconds')
        self.assertEqual(first, second)
        self.assertGreater(first['kills'], 0)
        self.assertGreater(first['spawns'], 0)
        self.assertGreater(float(first['damage_dealt']), 0)
        self.assertTrue(first['wallet'])

    def test_idle_player_takes_real_damage_and_stops_at_death(self):
        result = simulate('idle', seconds=60, seed=7)
        self.assertFalse(result['survived'])
        self.assertLess(result['elapsed'], 60)
        self.assertEqual(result['health'], '0')
        self.assertEqual(result['kills'], 0)
        self.assertEqual(float(result['damage_taken']), 100)
        self.assertIn(result['cause_of_death'],
                      {'enemy contact', 'enemy projectile'})

    def test_shopper_uses_earned_money_and_equips_rewards(self):
        result = simulate('shopper', seconds=60, seed=7)
        self.assertGreater(result['purchases'], 0)
        self.assertEqual(result['purchases'], len(result['drops']))
        self.assertGreater(result['milestones']['first_purchase'], 0)
        self.assertTrue(any(result['loadout']['armor']))
        self.assertTrue(all(float(amount) >= 0
                            for amount in result['wallet'].values()))
        self.assertEqual(result['checkpoints'][-1]['time'], 60)
        self.assertLessEqual(result['peak_enemies'], 60)

    def test_rng_restores_after_failed_simulation(self):
        before = random.getstate()
        with patch('scripts.balance_simulation._simulate',
                   side_effect=RuntimeError('probe failed')):
            with self.assertRaises(RuntimeError):
                simulate('kite', seconds=1)
        self.assertEqual(random.getstate(), before)

    def test_injected_loadouts_are_explicit_and_executable(self):
        for loadout in ('summoner', 'upgraded'):
            with self.subTest(loadout=loadout):
                result = simulate('kite', seconds=10, loadout=loadout)
                self.assertTrue(result['injected_fixture'])
                self.assertEqual(result['fixture_loadout'], loadout)
                self.assertGreater(result['kills'], 0)

    def test_managed_shopper_sells_spares_and_funds_real_upgrades(self):
        result = simulate('managed-shopper', seconds=60, seed=7)
        actions = {entry['action'] for entry in result['transactions']}
        self.assertEqual(actions, {'sell', 'level'})
        self.assertLess(result['inventory_count'], result['purchases'] + 2)
        self.assertGreater(result['milestones']['first_level_upgrade'], 0)
        self.assertTrue(any(item['level'] > 1
                            for item in result['equipped_items']))
        self.assertTrue(all(float(amount) >= 0
                            for amount in result['wallet'].values()))
        self.assertLessEqual(sum(item is not None
                                 for item in result['loadout']['abilities']), 4)

    def test_rejects_invalid_inputs(self):
        for kwargs in ({'seconds': 0}, {'seconds': float('inf')},
                       {'dt': 0}, {'dt': float('nan')}, {'dt': .2}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                simulate('kite', **kwargs)
        with self.assertRaises(ValueError):
            simulate('nonexistent')


if __name__ == '__main__':
    unittest.main()
