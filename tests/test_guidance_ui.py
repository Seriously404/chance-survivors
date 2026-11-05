"""Mouse and keyboard integration for quest choices, menu help and HUD scaling."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from client.render import Renderer, pygame
from client.ui_guidance import MENU_HELP


class GuidanceUITests(unittest.TestCase):
    def setUp(self):
        self.renderer = Renderer(800, 450, 200)
        self.renderer.set_view("PLAYING")
        pygame.event.clear()

    def tearDown(self):
        pygame.quit()

    def click(self, key):
        position = self.renderer._buttons[key].center
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=position))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=position))
        return self.renderer.process_events()[2]

    def choice(self, rerolls=1):
        offers = [{"id": key, "name": key.title(), "description": "Protect the core." * 20,
                   "default_power": 1.5, "power_selectable": index > 0}
                  for index, key in enumerate(("engineer", "fire", "sniper"))]
        return {"pending": True, "offers": offers, "rerolls_remaining": rerolls}

    def test_forced_choice_captures_gameplay_and_selects_exact_power(self):
        renderer = self.renderer
        renderer.draw({"main_quest_choice": self.choice()})
        self.assertNotIn("engineer", renderer._quest_power_sliders)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        _, shots, actions = renderer.process_events()
        self.assertEqual(actions, [])
        self.assertEqual(shots, [])
        self.assertEqual(renderer.get_movement(), (0, 0))
        slider = renderer._quest_power_sliders["fire"]
        position = (slider.x + round(slider.width * .7), slider.centery)
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=position))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=position))
        renderer.process_events()
        selected = renderer._quest_powers["fire"]
        self.assertAlmostEqual(selected, 1.05 + .95 * .7, delta=.005)
        actions = self.click("quest_confirm:fire")
        self.assertEqual(actions, [f"quest_choose:fire:{selected:.4f}"])
        self.assertEqual(self.click("quest_reroll_main"), ["quest_reroll_main"])
        renderer.draw({"main_quest_choice": self.choice(rerolls=0)})
        self.assertNotIn("quest_reroll_main", renderer._buttons)
        self.assertEqual(self.click("quest_decline_main"), ["quest_decline_main"])

    def test_long_quest_descriptions_scroll_and_controls_fit(self):
        renderer = self.renderer
        renderer.draw({"main_quest_choice": self.choice()})
        for rect in renderer._buttons.values():
            self.assertTrue(renderer.screen.get_rect().contains(rect))
        rect, maximum = renderer._quest_description_regions["fire"]
        self.assertGreater(maximum, 0)
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, x=0))
        with patch.object(pygame.mouse, "get_pos", return_value=rect.center):
            renderer.process_events()
        self.assertEqual(renderer._quest_description_offsets["fire"], 1)

    def test_every_menu_tab_has_paged_help_without_underlying_clicks(self):
        renderer = self.renderer
        for key, (_, pages) in MENU_HELP.items():
            renderer._context_help_key = key
            for page in range(len(pages)):
                renderer._context_help_page = page
                renderer._draw_context_help()
                for rect in renderer._buttons.values():
                    self.assertTrue(renderer.screen.get_rect().contains(rect))
                self.assertEqual(self.click("context_help_next"), [])
            renderer._draw_context_help()
            self.assertEqual(self.click("context_help_close"), [])
            self.assertIsNone(renderer._context_help_key)

    def test_hud_buttons_icons_and_hover_regions_scale_together(self):
        renderer = self.renderer
        item = {"id": "ability", "name": "Fireball", "type": "ability",
                "rarity": "common", "stats": {"element": "fire"}}
        state = {"items": [item], "active_slots": {"abilities": ["ability"]}}
        renderer._draw_game_ui(state)
        baseline = renderer._buttons["ability_cast:0"].width
        renderer.screen = pygame.display.set_mode((1920, 1080))
        renderer.screen_width, renderer.screen_height = 1920, 1080
        renderer._draw_game_ui(state)
        rect = renderer._buttons["ability_cast:0"]
        self.assertGreaterEqual(rect.width, baseline * 2)
        self.assertEqual(renderer._hover_slots[0][0], rect)
        self.assertIn("ability_cast:0", self.click("ability_cast:0"))
        self.assertEqual(renderer.screen.get_size(), (1920, 1080))

    def test_engineering_objective_structures_and_buff_are_drawn(self):
        renderer = self.renderer
        objective = SimpleNamespace(x=0, y=0, health=50, max_health=100)
        wall = SimpleNamespace(x=.3, y=.2, health=20, max_health=30,
                               structure_kind="wall", protocol_remaining=1)
        engineering = SimpleNamespace(objective=objective, structures=[wall], wave=3,
                                      wave_kills=5, wave_target=10)
        with patch.object(renderer, "draw_health_bar", wraps=renderer.draw_health_bar) as bars:
            renderer._draw_engineering(engineering, 0, 0)
        self.assertEqual(bars.call_count, 2)
        with patch.object(renderer, "_text", wraps=renderer._text) as text:
            renderer._draw_game_ui({"engineering": engineering})
        labels = [str(call.args[0]) for call in text.call_args_list]
        self.assertIn("Core: 50 / 100", labels)
        self.assertIn("Wave 3 · 5 / 10", labels)


if __name__ == "__main__":
    unittest.main()
