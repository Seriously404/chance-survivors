"""Action-driven onboarding and headless tutorial input coverage."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from client.render import Renderer
from game.core.tutorial import RunTutorial
from game.entities.player import Player


class RunTutorialTests(unittest.TestCase):
    def test_reading_practice_guide_does_not_spawn_or_age_the_run(self):
        from game.main import main

        observations = []

        class PracticeRenderer(Renderer):
            def __init__(self, *args):
                super().__init__(*args)
                self.set_player_name("Practice")
                self.frame = 0
                pygame.event.clear()

            def tick(self, rate):
                return .5

            def draw(self, state):
                observations.append((state.get("tutorial") is not None,
                                     state["run_elapsed_ms"], len(state["enemies"])))
                super().draw(state)

            def process_events(self):
                self.frame += 1
                if self.frame == 1:
                    return True, [], ["play"]
                if self.frame == 2:
                    return True, [], ["start_run"]
                if self.frame == 16:
                    pos = self._buttons["tutorial_skip"].center
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
                    return super().process_events()
                return self.frame < 18, [], []

        with tempfile.TemporaryDirectory() as directory:
            with patch("game.main.Renderer", PracticeRenderer), patch(
                "game.main.configured_save_path", return_value=Path(directory) / "run.json"
            ):
                main()
        practice = [row for row in observations if row[0]]
        self.assertGreater(len(practice), 10)
        self.assertTrue(all(elapsed == 0 and enemies == 0 for _, elapsed, enemies in practice))
        self.assertTrue(any(not active and elapsed > 0 for active, elapsed, _ in observations))

    def test_completes_only_after_real_actions_without_a_purchase(self):
        tutorial = RunTutorial(active=True)
        context = dict(actions=[], panel=None, tab="inventory",
                       bazaar_tab="market", movement=(0, 0), paused=False)

        def observe(**changes):
            context.update(changes)
            tutorial.observe(**context)

        observe()
        self.assertEqual(tutorial.step, 0)
        observe(movement=(1, 0))
        self.assertEqual(tutorial.step, 1)
        observe(movement=(0, 0), actions=["dash"])
        observe(actions=[], panel="bazaar", tab="bazaar")
        observe(bazaar_tab="crates")
        self.assertEqual(tutorial.step, 4)
        observe(actions=["bazaar_crate_select:copper"])
        observe(actions=[], panel="inventory", tab="inventory")
        observe(tab="combination", actions=["select:starter-rifle"],
                base_id="starter-rifle")
        self.assertFalse(tutorial.active)

    def test_paused_controls_do_not_advance_and_skip_is_optional(self):
        tutorial = RunTutorial(active=True)
        tutorial.observe(actions=[], panel=None, tab="inventory", bazaar_tab="market",
                         movement=(1, 0), paused=True)
        self.assertEqual(tutorial.step, 0)
        tutorial.observe(actions=["tutorial_skip"], panel=None, tab="inventory",
                         bazaar_tab="market", movement=(0, 0), paused=True)
        self.assertIsNone(tutorial.view())

    def test_overlay_button_is_clickable_in_game_without_firing(self):
        renderer = Renderer(800, 450, 200)
        renderer.set_view("PLAYING")
        state = {"player": Player(), "bullets": [], "enemies": [],
                 "enemy_types": {}, "currency": {},
                 "tutorial": RunTutorial(active=True).view()}
        renderer.draw(state)
        pos = renderer._buttons["tutorial_skip"].center
        pygame.event.clear()
        with patch("pygame.mouse.get_pos", return_value=pos):
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
            _, _, actions = renderer.process_events()
        self.assertIn("tutorial_skip", actions)
        self.assertEqual(renderer.input_handler.fire_events, [])
        with patch("pygame.mouse.get_pos", return_value=pos):
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
            renderer.process_events()
        self.assertIsNone(renderer.input_handler.click_release)

    def test_combination_tab_selects_base_from_inventory_panel(self):
        renderer = Renderer(800, 450, 200)
        renderer.set_view("PLAYING", "inventory")
        renderer.menu_tab = renderer.upgrade_tab = "combination"
        item = {"id": "rifle", "type": "weapon", "stats": {}, "combinations": []}
        renderer._last_state = {"items": [item]}
        renderer._item_rects = {"rifle": pygame.Rect(10, 10, 40, 40)}
        pygame.event.clear()
        pos = (20, 20)
        with patch("pygame.mouse.get_pos", return_value=pos):
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
            renderer.process_events()
        self.assertEqual(renderer.selected_base_id, "rifle")

    def test_new_run_guide_tracks_real_menu_and_key_events(self):
        from game.main import main

        views = []
        class ScriptedRenderer(Renderer):
            def __init__(self, *args):
                super().__init__(*args)
                self.set_player_name("Tester")
                self.frame = 0

            def tick(self, rate):
                return 0.016

            def draw(self, state):
                views.append(state.get("tutorial"))
                super().draw(state)

            def process_events(self):
                self.frame += 1
                if self.frame == 1:
                    return True, [], ["play"]
                if self.frame == 2:
                    return True, [], ["start_run"]
                if self.frame == 3:
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
                elif self.frame == 4:
                    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_w))
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
                elif self.frame == 6:
                    return super().process_events()
                elif self.frame >= 5 and self.frame <= 12:
                    keys = {5: "inventory", 7: "tab_bazaar", 8: "bazaar_tab_crates",
                            10: "tab_inventory", 11: "tab_combination"}
                    if self.frame == 9:
                        key = next(k for k in self._buttons if k.startswith("bazaar_crate_select:"))
                        pos = self._buttons[key].center
                    elif self.frame == 12:
                        pos = next(iter(self._item_rects.values())).center
                    else:
                        if keys[self.frame] not in self._buttons:
                            raise AssertionError((self.frame, self.mode, self.panel, list(self._buttons)))
                        pos = self._buttons[keys[self.frame]].center
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
                else:
                    return False, [], []
                return super().process_events()

        with tempfile.TemporaryDirectory() as directory:
            with patch("game.main.Renderer", ScriptedRenderer), patch(
                "game.main.configured_save_path", return_value=Path(directory) / "run.json"
            ):
                main()
        observed = [view["step"] if view else None for view in views]
        self.assertEqual(observed[:10], [1, 2, 3, 3, 3, 4, 5, 6, 7, 7])
        self.assertIn(None, observed[10:])
