"""Exercise the new-run introduction through real menu buttons."""
from game.main import main
from client.render import Renderer
import pygame
from unittest.mock import patch
from pathlib import Path
import unittest
import tempfile
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')


class IntroductionIntegrationTests(unittest.TestCase):
    def test_tutorial_pages_can_be_reviewed_without_starting(self):
        renderer = Renderer(800, 450, 200)
        renderer.draw_introduction()
        self.assertIn('intro_next', renderer._buttons)
        renderer.intro_page = 1
        renderer.draw_introduction()
        self.assertIn('intro_prev', renderer._buttons)
        self.assertIn('intro_next', renderer._buttons)
        self.assertIn('start_run', renderer._buttons)
        renderer.codex_tab = 'guide'
        renderer.codex_page = 1
        renderer.draw_codex([], [], [])
        self.assertIn('codex_next', renderer._buttons)

    def run_sequence(self, start):
        with tempfile.TemporaryDirectory() as directory:
            save = Path(directory) / 'run.json'
            save.write_text('existing save')
            seen = []

            class ScriptedRenderer(Renderer):
                def __init__(self, *args):
                    super().__init__(*args)
                    self.set_player_name('Tester')
                    self.steps = 0

                def tick(self, rate):
                    return 0.016

                def process_events(self):
                    self.steps += 1
                    if self.steps == 1:
                        return True, [], ['play']
                    if self.steps == 2:
                        self_test.assertEqual(self.mode, 'INTRODUCTION')
                        self_test.assertEqual(
                            save.read_text(), 'existing save')
                        key = 'start_run' if start else 'back'
                        self_test.assertIn(key, self._buttons)
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, button=1, pos=self._buttons[key].center))
                        return super().process_events()
                    seen.append(self.mode)
                    return False, [], []
            self_test = self
            with patch('game.main.Renderer', ScriptedRenderer), patch('game.main.configured_save_path', return_value=save):
                main()
            if start:
                self.assertEqual(seen, ['PLAYING'])
                self.assertNotEqual(save.read_text(), 'existing save')
            else:
                self.assertEqual(seen, ['MENU'])
                self.assertEqual(save.read_text(), 'existing save')

    def test_back_preserves_save(self):
        self.run_sequence(False)

    def test_start_enters_game_after_introduction(self):
        self.run_sequence(True)
