import unittest

from game.entities.player import Player
from game.systems.abilities import ability_cooldown, cast_ability
from game.systems.fusion import FusionManager
from game.systems.inventory import Inventory


def item(identity, script="dash"):
    return {"id": identity, "name": identity, "type": "ability", "rarity": "common",
            "level": 1, "stats": {"script": script, "cooldown": 5, "dash_distance": 2},
            "combinations": [None], "status": "normal"}


class DashTests(unittest.TestCase):
    def test_space_requests_a_dash(self):
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from client.input import InputHandler
        pygame.init()
        try:
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(
                pygame.KEYDOWN, key=pygame.K_SPACE))
            _, _, actions = InputHandler().process_events("PLAYING")
            self.assertIn("dash", actions)
        finally:
            pygame.quit()

    def test_default_dash_normalizes_and_respects_cooldown(self):
        player = Player()
        self.assertTrue(player.start_dash(3, 4))
        self.assertFalse(player.start_dash(1, 0))
        player.update_dash(0.18)
        self.assertAlmostEqual(player.x, 1.2)
        self.assertAlmostEqual(player.y, 1.6)
        player.update_dash(3)
        self.assertTrue(player.start_dash(0, 0))

    def test_only_one_dash_equipped(self):
        inv = Inventory([item("a"), item("b")])
        inv.equip("a", "abilities", 0)
        with self.assertRaisesRegex(ValueError, "Only one dash"):
            inv.equip("b", "abilities", 1)
        inv.equip("b", "abilities", 0)

    def test_fusion_dash_has_long_cooldown_and_time_shift(self):
        manager = FusionManager()
        recipe = manager.recipe_by_id("sandevistan")
        self.assertEqual(recipe.unlock_level, 51)
        sources = [item("a"), item("b"), {
            **item("c"), "type": "relic", "fusion_recipe": "elemental-core"}]
        for source in sources:
            source.update(rarity="ultimate", level=20, combinations=[None] * 5)
        fused = manager.build_fusion(sources, "sandevistan")
        self.assertGreaterEqual(ability_cooldown(fused), 60)
        player = Player()
        result = cast_ability(fused, player, [], angle=0,
                              base_speed=1, enemy_types={})
        self.assertTrue(result.consumed)
        self.assertGreater(player.time_shift_remaining, 0)
        self.assertFalse(cast_ability(fused, player, [], angle=0,
                         base_speed=1, enemy_types={}).consumed)
