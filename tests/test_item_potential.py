import unittest

from game.systems.combinations import CombinationEngine
from game.systems.inventory import Inventory, _item
from game.systems.items import effective_ability, item_stat, player_bonuses
from game.systems.bazaar import BazaarManager
from game.systems.run_save import RunSave
from tests.test_run_save import RunSaveTests


class ItemPotentialTests(unittest.TestCase):
    def test_origin_changes_level_growth_at_equal_rarity(self):
        common = _item("common", "Common", "ability", "common",
                       11, {"cast_damage": 10, "cooldown": 10})
        common["rarity"] = "legendary"
        legendary = {**common, "id": "legendary", "base_rarity": "legendary"}
        self.assertGreater(item_stat(common, "cast_damage"),
                           item_stat(legendary, "cast_damage"))
        self.assertLess(item_stat(common, "cooldown"),
                        item_stat(legendary, "cooldown"))
        engine = CombinationEngine()
        for candidate in (common, legendary):
            computed = engine.evaluate(candidate)
            self.assertAlmostEqual(
                computed.stats["cast_damage"].to_float(), item_stat(candidate, "cast_damage"))
            self.assertAlmostEqual(
                computed.stats["cooldown"].to_float(), item_stat(candidate, "cooldown"))

    def test_combined_and_equipped_armor_uses_same_growth(self):
        armor = _item("armor", "Armor", "armor", "common", 5, {"health": 10})
        armor.update(rarity="legendary", combinations=[None] * 4)
        inv = Inventory([armor])
        inv.equip("armor", "armor", 0)
        self.assertAlmostEqual(player_bonuses(
            inv)["health"], item_stat(armor, "health"))
        self.assertAlmostEqual(CombinationEngine().evaluate(
            armor).stats["health"].to_float(), item_stat(armor, "health"))

    def test_combined_ability_is_not_scaled_twice(self):
        ability = _item("a", "A", "ability", "common", 5, {
                        "cast_damage": 10, "script": "projectile"})
        supplement = _item("s", "S", "ability", "common",
                           1, {"cast_damage": 2})
        ability["combinations"] = ["s"]
        inv = Inventory([ability, supplement])
        cast = effective_ability(inv, ability)
        expected = CombinationEngine().evaluate_inventory(
            inv, "a").stats["cast_damage"].to_float()
        self.assertAlmostEqual(item_stat(cast, "cast_damage"), expected)

    def test_upgrade_records_origin_and_save_preserves_it(self):
        legacy = _item("a", "A", "ability", "common", 1, {"cast_damage": 10})
        del legacy["base_rarity"]
        BazaarManager().upgrade_rarity(legacy, luck=5)
        self.assertEqual(legacy["base_rarity"], "common")
        self.assertEqual(legacy["rarity"], "uncommon")
        save = RunSaveTests().create_save()
        save.state["inventory"]["items"][0]["base_rarity"] = "common"
        loaded = RunSave.from_json(RunSave(save.state).to_json())
        self.assertEqual(loaded.restore_inventory(
        ).items[0]["base_rarity"], "common")
