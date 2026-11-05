"""Run a real event-driven purchase, combination, damage and saved-run cycle."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
from client.render import Renderer
from game.entities.enemy import Enemy
from game.systems.collision import CollisionSystem
from game.systems.currency import CurrencyWallet
from game.systems.inventory import _item
from game.systems.run_save import RunSave


class RunTransactionTests(unittest.TestCase):
    def test_buy_skip_combine_damage_and_save(self):
        from game.main import main
        test = self
        observations = {}

        class FundedWallet(CurrencyWallet):
            def __init__(self):
                super().__init__()
                self.add('Copper', 100)
                self.add('Gold', 10)

        class ScriptedRenderer(Renderer):
            def __init__(self, *args):
                super().__init__(*args)
                self.set_player_name('Transactions')
                self.stage = 0
                self.frames = 0

            def tick(self, rate):
                return .016

            def click(self, key):
                if key not in self._buttons:
                    return True, [], []
                pos = self._buttons[key].center
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
                self.stage += 1
                return super().process_events()

            def process_events(self):
                self.frames += 1
                test.assertLess(self.frames, 100, (self.stage, self.mode, self.panel, self._buttons))
                if self.stage == 0:
                    self.stage += 1
                    return True, [], ['play']
                if self.stage == 1:
                    self.stage += 1
                    return True, [], ['start_run']
                if self.stage == 2:
                    return self.click('tutorial_skip')
                clicks = {3: 'inventory', 4: 'tab_bazaar', 5: 'bazaar_tab_crates',
                          6: 'bazaar_buy:starter-crate', 7: 'crate_roll_skip',
                          8: 'crate_roll_skip', 9: 'bazaar_buy:starter-crate',
                          10: 'crate_roll_skip', 11: 'crate_roll_skip',
                          12: 'bazaar_tab_level_upgrader',
                          14: 'bazaar_level:starter-fire-rune', 15: 'tab_combination'}
                if self.stage in clicks:
                    return self.click(clicks[self.stage])
                if self.stage in (13, 16):
                    if 'starter-fire-rune' not in self._item_rects:
                        return True, [], []
                    pos = self._item_rects['starter-fire-rune'].center
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
                    self.stage += 1
                    return super().process_events()
                if self.stage == 17:
                    target = 'combo:starter-fire-rune:0'
                    if target not in self._drop_targets:
                        return True, [], []
                    start = self._item_rects['shop-1'].center
                    end = self._drop_targets[target].center
                    for event in (
                        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start),
                        pygame.event.Event(pygame.MOUSEMOTION, pos=end, rel=(20, 0), buttons=(1, 0, 0)),
                        pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=end),
                    ):
                        pygame.event.post(event)
                    self.stage += 1
                    return super().process_events()
                if self.stage == 18:
                    state = self._last_state
                    fireball = next(item for item in state['items'] if item['id'] == 'starter-fire-rune')
                    test.assertEqual(fireball['combinations'], ['shop-1'])
                    test.assertEqual(fireball['level'], 2)
                    observations['copper'] = state['currency']['Copper']
                    player = state['player']
                    enemy = Enemy('basic', x=player.x, y=player.y, damage=7)
                    CollisionSystem(200).check_enemy_player_collisions([enemy], player, {'basic': {'size': 30, 'damage': 7}})
                    observations['health'] = player.health
                    self.stage += 1
                    return False, [], []
                return False, [], []

        reward = _item('healing-definition', 'Healing', 'ability', 'common', 1,
                       {'script': 'heal', 'heal_amount': 10, 'cooldown': 6})
        second_reward = _item('frost-definition', 'Frost', 'ability', 'common', 1,
                              {'script': 'frost', 'cast_damage': 8, 'cooldown': 6})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run.json'
            with patch('game.main.Renderer', ScriptedRenderer), patch('game.main.CurrencyWallet', FundedWallet), patch(
                'game.main.configured_save_path', return_value=path
            ), patch('game.systems.bazaar.BazaarManager.roll_crate', side_effect=[reward, second_reward]):
                main()
            saved = RunSave.read(path)
            inventory = saved.restore_inventory()
            self.assertEqual(inventory.get('starter-fire-rune')['combinations'], ['shop-1'])
            self.assertEqual(observations['copper'], 30)
            self.assertEqual(saved.state['currencies']['Copper'], '30')
            self.assertEqual(saved.state['currencies']['Gold'], '4')
            self.assertEqual(len(inventory.seen_ability_definitions), 3)
            self.assertEqual(saved.state['player']['health'], observations['health'])
            self.assertLess(observations['health'], 100)
