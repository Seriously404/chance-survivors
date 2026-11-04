"""Headless coverage for item inspection without changing selection."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from client.render import Renderer


class ItemTooltipTests(unittest.TestCase):
    def setUp(self):
        self.renderer = Renderer(800, 450, 200)
        self.item = {
            "id": "test", "name": "Test item", "type": "ability",
            "description": "A useful item with a clear description.",
            "rarity": "rare", "level": 2, "stats": {"element": "fire"},
        }

    def test_inventory_hover_stays_on_screen_and_preserves_selection(self):
        renderer = self.renderer
        renderer.selected_item_id = "another"
        renderer._item_rects = {"test": pygame.Rect(770, 420, 25, 25)}
        renderer.input_handler.mouse_position = (780, 430)
        box = renderer._draw_item_tooltip({"items": [self.item]})
        self.assertIsNotNone(box)
        self.assertTrue(renderer.screen.get_rect().contains(box))
        self.assertEqual(renderer.selected_item_id, "another")

    def test_equipped_item_hover_and_drag_suppression(self):
        renderer = self.renderer
        renderer._hover_slots = [(pygame.Rect(10, 10, 30, 30), self.item)]
        renderer.input_handler.mouse_position = (15, 15)
        self.assertIsNotNone(renderer._draw_item_tooltip({"items": [self.item]}))
        renderer.input_handler.drag_active = True
        self.assertIsNone(renderer._draw_item_tooltip({"items": [self.item]}))

    def test_unoccupied_location_has_no_tooltip(self):
        renderer = self.renderer
        renderer._item_rects = {"test": pygame.Rect(10, 10, 30, 30)}
        renderer.input_handler.mouse_position = (50, 50)
        self.assertIsNone(renderer._draw_item_tooltip({"items": [self.item]}))

    def test_bazaar_market_and_rewards_use_catalog_metadata(self):
        from game.main import _bazaar_view_state
        from game.systems.bazaar import BazaarManager, build_extended_catalog
        from game.systems.currency import CurrencyWallet
        from game.systems.items import create_initial_inventory

        manager = BazaarManager(build_extended_catalog())
        bazaar = _bazaar_view_state(
            manager, create_initial_inventory(), CurrencyWallet(), 1, 0)
        renderer = self.renderer
        renderer.panel = renderer.menu_tab = "bazaar"
        state = {"items": [], "bazaar": bazaar}
        renderer._bazaar_tab = "market"
        renderer.draw(state)
        market_item = bazaar["catalog"][0]
        market_rect, metadata = next(
            (rect, item) for rect, item in renderer._hover_slots
            if item is market_item)
        renderer.input_handler.mouse_position = market_rect.center
        self.assertIsNotNone(renderer._draw_item_tooltip(state))
        self.assertEqual(metadata["description"], market_item["description"])

        renderer._bazaar_tab = "crates"
        renderer.draw(state)
        rewards = bazaar["crates"][0]["rewards"]
        reward_rect, reward = next(
            (rect, item) for rect, item in renderer._hover_slots
            if any(item is candidate for candidate in rewards))
        renderer.input_handler.mouse_position = reward_rect.center
        self.assertIsNotNone(renderer._draw_item_tooltip(state))
        self.assertIn("description", reward)
        self.assertTrue(renderer._scroll_regions["bazaar_rewards_scroll"].contains(reward_rect))

        renderer.start_crate_roll(reward, rewards)
        renderer.draw(state)
        self.assertEqual(renderer._hover_slots, [])
        renderer._crate_roll["elapsed"] = 3
        renderer.draw(state)
        self.assertEqual(len(renderer._hover_slots), 1)
        self.assertIs(renderer._hover_slots[0][1], reward)

    def test_fusion_catalog_hover_describes_real_requirements(self):
        from game.systems.fusion import FusionManager

        renderer = self.renderer
        renderer.panel = renderer.menu_tab = "bazaar"
        renderer._bazaar_tab = "fusion"
        renderer.fusion_codex = True
        recipes = FusionManager().all_recipes()
        state = {"items": [], "bazaar": {}, "fusion_recipes": recipes}
        renderer.draw(state)
        recipe_rect, recipe = next(
            (rect, item) for rect, item in renderer._hover_slots
            if item is recipes[0])
        renderer.input_handler.mouse_position = recipe_rect.center
        self.assertIsNotNone(renderer._draw_item_tooltip(state))
        self.assertEqual(recipe["description"], recipes[0]["description"])
        badge_rect, badge = next(
            (rect, item) for rect, item in renderer._hover_slots
            if item.get("tooltip_subtitle") == "Fusion ingredient requirement")
        self.assertIn("No valid ingredient owned", badge["description"])
        self.assertIn(str(recipes[0]["min_level"]), badge["description"])
        renderer.input_handler.mouse_position = badge_rect.center
        self.assertIsNotNone(renderer._draw_item_tooltip(state))

    def test_economy_sliders_accept_extreme_wallets(self):
        from game.systems.numbers import LargeNumber

        renderer = self.renderer
        total = 10 ** 309
        renderer._last_state = {"bazaar": {"wallet": {"Copper": LargeNumber(total)}}}
        renderer._bazaar_tab = "exchange"
        renderer._sliders = {"exchange": pygame.Rect(100, 100, 100, 20)}
        renderer._update_economy_slider((100, 110), (150, 110))
        self.assertEqual(renderer._exchange_amount, total // 2)
        renderer._bazaar_tab = "rarity_upgrader"
        renderer._sliders = {"pool": pygame.Rect(100, 100, 100, 20)}
        renderer._update_economy_slider((100, 110), (175, 110))
        self.assertEqual(renderer._rarity_pool["Copper"], total * 3 // 4)
