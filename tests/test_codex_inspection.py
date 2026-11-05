"""Exercise codex navigation through real SDL events at the minimum size."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from client.render import Renderer, pygame


class CodexInspectionTests(unittest.TestCase):
    def setUp(self):
        self.renderer = Renderer(800, 450, 200)
        self.renderer.set_view("CODEX")
        self.renderer.codex_selected = 0
        pygame.event.clear()

    def tearDown(self):
        pygame.event.clear()
        pygame.quit()

    def click(self, name):
        renderer = self.renderer
        position = renderer._buttons[name].center
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=position))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONUP, button=1, pos=position))
        _, _, actions = renderer.process_events()
        self.assertIn(name, actions)

    def test_every_reward_and_odds_reachable_with_clicks(self):
        renderer = self.renderer
        renderer.codex_tab = "crates"
        rewards = [{"name": f"Reward {index:02}", "type": "ability",
                    "rarity": "common", "description": "A fire projectile",
                    "stats": {"element": "fire"}, "chance": 1 / 37}
                   for index in range(37)]
        crates = [{"name": "Large reward pool", "description": "Inspect all",
                   "costs": {"Copper": 10}, "preview_luck": 1,
                   "rewards": rewards}]
        seen = set()
        for _ in range(20):
            with patch.object(renderer, "_text", wraps=renderer._text) as text:
                renderer.draw_codex([], [], crates)
            labels = [str(call.args[0]) for call in text.call_args_list]
            self.assertTrue(any("Title preview" in label for label in labels))
            for rect, item in renderer._hover_slots:
                self.assertEqual(item["description"], "A fire projectile")
                self.assertTrue(renderer.screen.get_rect().contains(rect))
                self.assertIn("2.7%", labels)
                seen.add(item["name"])
            for rect in renderer._buttons.values():
                self.assertTrue(renderer.screen.get_rect().contains(rect))
            previous = renderer.codex_detail_page
            self.click("codex_detail_next")
            renderer.draw_codex([], [], crates)
            if renderer.codex_detail_page == previous:
                break
        self.assertEqual(seen, {reward["name"] for reward in rewards})
        self.click("codex_detail_prev")
        self.assertLess(renderer.codex_detail_page, previous)

    def test_long_item_description_is_paginated_and_fully_readable(self):
        renderer = self.renderer
        renderer.codex_tab = "items"
        description = " ".join(f"word{index:03}" for index in range(200))
        items = [{"name": "Long description", "type": "ability",
                  "rarity": "common", "description": description}]
        seen = set()
        for _ in range(30):
            with patch.object(renderer, "_text", wraps=renderer._text) as text:
                renderer.draw_codex(items, [], [])
            for call in text.call_args_list:
                label, position = str(call.args[0]), call.args[1]
                if position[0] == 350 and position[1] < 390:
                    self.assertLessEqual(position[0] + renderer.font.size(label)[0], 780)
                    self.assertLess(position[1] + renderer.font.get_height(), 410)
                    seen.update(word for word in label.split() if word.startswith("word"))
            previous = renderer.codex_detail_page
            self.click("codex_detail_next")
            renderer.draw_codex(items, [], [])
            if renderer.codex_detail_page == previous:
                break
        self.assertEqual(seen, set(description.split()))

    def test_wheel_and_new_selection_reset_detail_page(self):
        renderer = self.renderer
        renderer.codex_tab = "items"
        items = [{"name": f"Item {index}", "description": "details " * 300}
                 for index in range(2)]
        renderer.draw_codex(items, [], [])
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, x=0))
        with patch.object(pygame.mouse, "get_pos", return_value=(600, 200)):
            renderer.process_events()
        self.assertEqual(renderer.codex_detail_page, 1)
        self.click("codex_select:1")
        self.assertEqual(renderer.codex_detail_page, 0)


if __name__ == "__main__":
    unittest.main()
