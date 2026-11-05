"""Main-loop Engineer choice, modal pause, active defense and persistence."""
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
from game.systems.progression import PlayerProgress
from game.systems.run_save import RunSave


class EngineerRunTests(unittest.TestCase):
    def test_forced_choice_pauses_and_engineer_actions_save(self):
        from game.main import main
        test = self
        captured = {}

        class UnlockProgress(PlayerProgress):
            def reset(self):
                super().reset()
                self.level = 8

        class ScriptedRenderer(Renderer):
            def __init__(self, *args):
                super().__init__(*args)
                self.set_player_name('Engineer Test')
                self.frame = 0
                self.snapshots = []
                pygame.event.clear()

            def tick(self, rate):
                return .016

            def draw(self, state):
                captured['state'] = state
                super().draw(state)

            def process_events(self):
                self.frame += 1
                if self.frame == 1:
                    return True, [], ['play']
                if self.frame == 2:
                    return True, [], ['start_run']
                if self.frame == 3:
                    return True, [], ['tutorial_skip']
                if self.frame in (4, 5, 6):
                    state = captured['state']
                    test.assertTrue(state['main_quest_choice']['pending'])
                    self.snapshots.append((state['run_elapsed_ms'], state['player'].x,
                                           len(state['enemies']), state['player'].health))
                    return True, [], ['back', 'pause', 'inventory']
                if self.frame == 7:
                    test.assertEqual(self.snapshots, [self.snapshots[0]] * 3)
                    key = 'quest_confirm:main-engineer'
                    test.assertIn(key, self._buttons)
                    pos = self._buttons[key].center
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
                    return super().process_events()
                if self.frame == 8:
                    state = captured['state']
                    test.assertIsNotNone(state['engineering'])
                    test.assertFalse(state['main_quest_choice']['pending'])
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
                    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_1))
                    with patch('pygame.mouse.get_pos', return_value=(600, 225)):
                        return super().process_events()
                if self.frame == 9:
                    state = captured['state']
                    defense = state['engineering']
                    test.assertEqual(len(defense.structures), 1)
                    captured['player_hp'] = state['player'].health
                    captured['core_hp'] = defense.objective.health
                    state['enemies'].append(Enemy('basic', x=defense.objective.x + .25,
                                                  y=defense.objective.y, damage=15))
                    return True, [], []
                if self.frame == 10:
                    state = captured['state']
                    test.assertEqual(state['player'].health, captured['player_hp'])
                    test.assertLess(state['engineering'].objective.health, captured['core_hp'])
                    captured['damaged_hp'] = state['engineering'].objective.health
                    pos = (400, 225)
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
                    with patch('pygame.mouse.get_pos', return_value=pos):
                        return super().process_events()
                if self.frame == 11:
                    state = captured['state']
                    test.assertGreater(state['engineering'].objective.health, captured['damaged_hp'])
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3))
                    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_3))
                    return super().process_events()
                if self.frame == 12:
                    state = captured['state']
                    test.assertGreater(state['engineering'].structures[0].overclock_remaining, 0)
                    state['engineering'].objective.take_damage(7)
                    captured['saved_hp'] = state['engineering'].objective.health
                    return False, [], []
                test.fail(f'Unexpected frame {self.frame}')

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run.json'
            with patch('game.main.Renderer', ScriptedRenderer), patch('game.main.PlayerProgress', UnlockProgress), patch(
                'game.main.configured_save_path', return_value=path
            ):
                main()
            saved = RunSave.read(path)
            from game.systems.engineering import EngineeringDefense
            defense = EngineeringDefense.from_dict(saved.state['engineering'])
            self.assertEqual(defense.objective.health, captured['saved_hp'])
            self.assertEqual(len(defense.structures), 1)
            self.assertGreater(defense.structures[0].overclock_remaining, 0)
