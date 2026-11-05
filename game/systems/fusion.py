"""Reusable fusion recipes and item creation for late-game build crafting."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from copy import deepcopy
import hashlib
import json
from typing import Any

from game.systems.inventory import RARITY_COMBINATION_SLOTS
from game.systems.json_loader import load_rarity_scaling
from game.systems.liquidation import BASIS_KEY, liquidation_basis
from game.systems.numbers import LargeNumber

RARITY_ORDER = [
    "common",
    "uncommon",
    "rare",
    "epic",
    "legendary",
    "mythical",
    "ultimate",
]

RARITY_MULTIPLIERS = load_rarity_scaling()["multipliers"]


class FusionRecipe:
    """Blueprint for a fused item that combines multiple source items."""

    def __init__(
        self,
        recipe_id: str,
        name: str,
        item_type: str,
        output_rarity: str,
        description: str,
        required_types: tuple[str, ...],
        min_rarity: str = "rare",
        min_level: int = 2,
        stats: dict[str, float] | None = None,
        unlock_level: int = 1,
        required_elements: tuple[str, ...] = (),
        required_fusion: str | None = None,
    ) -> None:
        self.id = recipe_id
        self.name = name
        self.item_type = item_type
        self.output_rarity = output_rarity.lower()
        self.description = description
        self.required_types = tuple(required_types)
        self.min_rarity = min_rarity.lower()
        self.min_level = max(1, int(min_level))
        self.stats = dict(stats or {})
        self.unlock_level = unlock_level
        self.required_elements = tuple(required_elements)
        self.required_fusion = required_fusion

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.item_type,
            "rarity": self.output_rarity,
            "description": self.description,
            "required_types": list(self.required_types),
            "min_rarity": self.min_rarity,
            "min_level": self.min_level,
            "stats": deepcopy(self.stats),
            "unlock_level": self.unlock_level,
            "required_elements": list(self.required_elements),
            "required_fusion": self.required_fusion,
        }


DEFAULT_FUSION_RECIPES = [
    FusionRecipe("architect-protocol", "Architect Protocol", "ability", "ultimate",
                 "For eight seconds, overclock nearby defenses and double their shot damage. Requires active nearby structures; does not repair or create them. A progress-earned engineering ultimate with a long recovery.",
                 ("ability", "ability", "relic"), min_rarity="mythical", min_level=12,
                 unlock_level=30, required_fusion="elemental-core"),
    FusionRecipe("sandevistan", "Sandevistan", "ability", "ultimate",
                 "An ultimate dash that slows the world and accelerates movement and ability recovery.",
                 ("ability", "ability", "relic"), min_rarity="ultimate", min_level=20,
                 unlock_level=51, required_fusion="elemental-core"),
    FusionRecipe("field-rifle", "Field Rifle", "weapon", "uncommon",
                 "A practical weapon reinforced with spare armor.", (
                     "weapon", "armor"),
                 min_rarity="common", min_level=1, stats={"damage_pct": 8, "health": 10}),
    FusionRecipe("battle-charm", "Battle Charm", "relic", "uncommon",
                 "A charm that combines an ability with a relic.", (
                     "ability", "relic"),
                 min_rarity="common", min_level=1, stats={"damage_pct": 6, "luck": 0.1}),
    FusionRecipe("elemental-core", "Elemental Core", "relic", "legendary",
                 "A core made from one ability of each elemental type.",
                 ("ability",) * 6, min_rarity="common", min_level=1, unlock_level=8,
                 required_elements=("fire", "frost", "light", "shadow", "arcane", "nature")),
    FusionRecipe("prismatic-rifle", "Prismatic Rifle", "weapon", "legendary",
                 "A weapon forged around an Elemental Core.", (
                     "weapon", "relic"),
                 min_rarity="common", min_level=1, unlock_level=15,
                 required_fusion="elemental-core", stats={"damage_pct": 20}),
    FusionRecipe(
        "ember-ward-sentinel",
        "Ember Ward Sentinel",
        "ability",
        "epic",
        "A fire-laced guardian that burns a lane and boosts survivability.",
        ("ability", "armor"),
        min_rarity="rare",
        min_level=2,
        unlock_level=4,
        stats={"damage_pct": 18.0, "health": 28.0, "luck": 3.0},
    ),
    FusionRecipe(
        "solar-hammer",
        "Solar Hammer",
        "weapon",
        "legendary",
        "A fused weapon that strikes with radiant force and a volatile punch.",
        ("weapon", "ability"),
        min_rarity="epic",
        min_level=2,
        unlock_level=10,
        stats={"damage_pct": 26.0, "speed_pct": 10.0, "luck": 4.0},
    ),
    FusionRecipe(
        "ghost-titan",
        "Ghost Titan",
        "armor",
        "epic",
        "A heavy fused armor set core that shifts survivability and speed.",
        ("armor", "relic"),
        min_rarity="rare",
        min_level=2,
        unlock_level=6,
        stats={"defense": 12.0, "health": 44.0, "speed_pct": 8.0},
    ),
    FusionRecipe(
        "starfire-echo",
        "Starfire Echo",
        "relic",
        "mythical",
        "A relic-like fusion object that amplifies luck and explosive output.",
        ("relic", "ability"),
        min_rarity="epic",
        min_level=2,
        unlock_level=12,
        stats={"luck": 9.0, "damage_pct": 15.0, "speed_pct": 6.0},
    ),
]


class FusionManager:
    """Create permanent fusion items from valid source inventory entries."""

    UNLOCK_LEVEL = 1

    def __init__(self, recipes: list[FusionRecipe] | None = None) -> None:
        self.recipes = list(recipes or DEFAULT_FUSION_RECIPES)

    def is_unlocked(self, player_level: int) -> bool:
        """Return whether the player has reached the Fusion progression milestone."""
        return type(player_level) is int and player_level >= self.UNLOCK_LEVEL

    def recipe_by_id(self, recipe_id: str) -> FusionRecipe:
        for recipe in self.recipes:
            if recipe.id == recipe_id:
                return recipe
        raise KeyError(f"Unknown fusion recipe: {recipe_id}")

    def all_recipes(self) -> list[dict[str, Any]]:
        return [recipe.to_dict() for recipe in self.recipes]

    def _rarity_rank(self, rarity: str) -> int:
        rarity = str(rarity).lower()
        if rarity not in RARITY_ORDER:
            raise ValueError(f"Unsupported rarity: {rarity}")
        return RARITY_ORDER.index(rarity)

    def is_valid_candidate(
        self,
        item: dict[str, Any],
        required_type: str,
        recipe: FusionRecipe,
    ) -> bool:
        if not isinstance(item, dict):
            return False
        if str(item.get("type", "")).lower() != required_type.lower():
            return False
        if self._rarity_rank(item.get("rarity", "common")) < self._rarity_rank(recipe.min_rarity):
            return False
        level = item.get("level", 1)
        if type(level) is not int or level < recipe.min_level:
            return False
        return True

    def validate_sources(
        self,
        source_items: list[dict[str, Any]],
        recipe: FusionRecipe,
    ) -> None:
        if len(source_items) != len(recipe.required_types):
            raise ValueError(
                f"{recipe.name} requires exactly {len(recipe.required_types)} source items."
            )
        source_ids = [str(item.get("id", "")) for item in source_items]
        if any(not item_id for item_id in source_ids) or len(set(source_ids)) != len(source_ids):
            raise ValueError(
                "Fusion sources must have distinct, stable item IDs.")
        expected_types = Counter(required.lower()
                                 for required in recipe.required_types)
        actual_types = Counter(str(item.get("type", "")).lower()
                               for item in source_items)
        if actual_types != expected_types:
            required = " + ".join(recipe.required_types)
            raise ValueError(
                f"{recipe.name} requires {required} source items.")
        if recipe.required_elements:
            elements = Counter(str(item.get("stats", {}).get(
                "element", "")).lower() for item in source_items)
            if elements != Counter(recipe.required_elements):
                raise ValueError(
                    f"{recipe.name} requires abilities with: {', '.join(recipe.required_elements)}.")
        if recipe.required_fusion and not any(item.get("fusion_recipe") == recipe.required_fusion for item in source_items):
            raise ValueError(
                f"{recipe.name} requires {recipe.required_fusion}.")
        for item, required_type in zip(
            sorted(source_items, key=lambda source: str(
                source.get("type", "")).lower()),
            sorted(recipe.required_types, key=str.lower),
        ):
            if not self.is_valid_candidate(item, required_type, recipe):
                raise ValueError(
                    f"Each fusion source must be {recipe.min_rarity.title()} or higher "
                    f"and level {recipe.min_level} or higher."
                )

    def find_companion(
        self,
        source_item: dict[str, Any],
        candidates: list[dict[str, Any]],
        recipe_id: str,
    ) -> dict[str, Any] | None:
        recipe = self.recipe_by_id(recipe_id)
        for candidate in candidates:
            if str(candidate.get("id")) == str(source_item.get("id")):
                continue
            try:
                self.validate_sources([source_item, candidate], recipe)
            except ValueError:
                continue
            return candidate
        return None

    def find_sources(self, candidates: list[dict[str, Any]], recipe_id: str,
                     player_level: int, preferred_id: str | None = None) -> list[dict[str, Any]]:
        """Find a complete set without consuming anything, preferring the selected item."""
        recipe = self.recipe_by_id(recipe_id)
        if player_level < recipe.unlock_level:
            raise ValueError(
                f"{recipe.name} unlocks at player level {recipe.unlock_level}.")
        eligible = [item for item in candidates if item.get("status") not in
                    {"active", "supplement", "combination_base"}]
        eligible = [item for item in eligible if any(self.is_valid_candidate(item, kind, recipe)
                                                     for kind in recipe.required_types)]
        if recipe.required_elements:
            available = Counter(str(item.get("stats", {}).get(
                "element", "")).lower() for item in eligible)
            if any(available[element] < count for element, count in Counter(recipe.required_elements).items()):
                raise ValueError(
                    "Missing compatible unequipped ingredients for this recipe.")
            eligible = [item for item in eligible if item.get(
                "stats", {}).get("element") in recipe.required_elements]
        for preferred_only in ((True, False) if preferred_id else (False,)):
            for group in combinations(eligible, len(recipe.required_types)):
                if preferred_only and not any(str(item.get("id")) == preferred_id for item in group):
                    continue
                try:
                    self.validate_sources(list(group), recipe)
                except ValueError:
                    continue
                return list(group)
        raise ValueError(
            "Missing compatible unequipped ingredients for this recipe.")

    def match_recipe(self, main_item: dict[str, Any], source_items: list[dict[str, Any]]) -> FusionRecipe:
        if not main_item:
            raise ValueError("A fusion requires a main item")
        for recipe in self.recipes:
            try:
                self.validate_sources([main_item, *source_items], recipe)
            except ValueError:
                continue
            else:
                return recipe
        raise ValueError("No valid fusion recipe matches these items")

    def build_fusion(self, source_items: list[dict[str, Any]], recipe_id: str | None = None) -> dict[str, Any]:
        if len(source_items) < 2:
            raise ValueError("Fusion requires at least two source items")
        if recipe_id:
            recipe = self.recipe_by_id(recipe_id)
        else:
            recipe = self.match_recipe(source_items[0], source_items[1:])
        self.validate_sources(source_items, recipe)
        selected = [deepcopy(item) for item in source_items]

        rarity = recipe.output_rarity
        total_level = max(int(item.get("level", 1)) for item in selected) + 1
        stats: dict[str, float] = {}
        output_metadata: dict[str, Any] = {}
        output_tags: list[str] = []
        for item in selected:
            item_stats = item.get("stats", {})
            if not isinstance(item_stats, dict):
                raise ValueError("Fusion source statistics must be an object.")
            if str(item.get("type", "")).lower() == recipe.item_type:
                tags = item.get("tags", [])
                if isinstance(tags, list):
                    output_tags = [tag for tag in tags if isinstance(tag, str)]
                output_metadata = {
                    key: deepcopy(value)
                    for key, value in item_stats.items()
                    if not isinstance(value, (int, float)) or isinstance(value, bool)
                }
            for stat_name, stat_value in item_stats.items():
                if not isinstance(stat_value, (int, float)):
                    continue
                stats[stat_name] = stats.get(
                    stat_name, 0.0) + float(stat_value)
        for stat_name, bonus in recipe.stats.items():
            stats[stat_name] = stats.get(stat_name, 0.0) + float(bonus)

        stats.update(output_metadata)
        if recipe.id == "sandevistan":
            stats = {"script": "sandevistan", "cooldown": 90.0,
                     "dash_distance": 4.0, "dash_duration": 0.2,
                     "time_shift_duration": 6.0}
        if recipe.id == "architect-protocol":
            stats = {"script": "architect_protocol", "cooldown": 120.0}
            output_tags = ["engineering", "engineering_support"]
        source_ids = sorted(str(item.get("id")) for item in selected)
        identity = json.dumps([recipe.id, source_ids],
                              separators=(",", ":"), ensure_ascii=True)
        identity_suffix = hashlib.sha256(
            identity.encode("utf-8")).hexdigest()[:16]

        result = {
            "id": f"fusion-{recipe.id}-{identity_suffix}",
            "name": recipe.name,
            "type": recipe.item_type,
            "rarity": rarity,
            "base_rarity": rarity,
            "level": total_level,
            "stats": stats,
            "combinations": [None] * RARITY_COMBINATION_SLOTS[rarity],
            "status": "normal",
            "fusion_recipe": recipe.id,
            "fusion_origin": source_ids,
            "fusion_only": True,
            "description": recipe.description,
            BASIS_KEY: str(sum((liquidation_basis(item) for item in selected), LargeNumber(0))),
        }
        if output_tags:
            result["tags"] = output_tags
        if recipe.id == "elemental-core":
            result["tags"] = ["elemental-core"]
        if recipe.item_type == "armor":
            armor_source = next(
                item for item in selected if item.get("type") == "armor")
            if "armor_slot" in armor_source:
                result["armor_slot"] = armor_source["armor_slot"]
        return result
