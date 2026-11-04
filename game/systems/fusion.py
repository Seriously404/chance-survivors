"""Reusable fusion recipes and item creation for late-game build crafting."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from typing import Any

from game.systems.inventory import RARITY_COMBINATION_SLOTS
from game.systems.json_loader import load_rarity_scaling

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
        }


DEFAULT_FUSION_RECIPES = [
    FusionRecipe(
        "ember-ward-sentinel",
        "Ember Ward Sentinel",
        "ability",
        "epic",
        "A fire-laced guardian that burns a lane and boosts survivability.",
        ("ability", "armor"),
        min_rarity="rare",
        min_level=2,
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
        stats={"damage_pct": 26.0, "speed_pct": 10.0, "luck": 4.0},
    ),
    FusionRecipe(
        "ghost-titan",
        "Ghost Titan",
        "armor",
        "epic",
        "A heavy fused armor set core that shifts survivability and speed.",
        ("armor", "misc"),
        min_rarity="rare",
        min_level=2,
        stats={"defense": 12.0, "health": 44.0, "speed_pct": 8.0},
    ),
    FusionRecipe(
        "starfire-echo",
        "Starfire Echo",
        "misc",
        "mythical",
        "A relic-like fusion object that amplifies luck and explosive output.",
        ("misc", "ability"),
        min_rarity="epic",
        min_level=2,
        stats={"luck": 9.0, "damage_pct": 15.0, "speed_pct": 6.0},
    ),
]


class FusionManager:
    """Create permanent fusion items from valid source inventory entries."""

    UNLOCK_LEVEL = 50

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
            raise ValueError("Fusion sources must have distinct, stable item IDs.")
        expected_types = Counter(required.lower() for required in recipe.required_types)
        actual_types = Counter(str(item.get("type", "")).lower() for item in source_items)
        if actual_types != expected_types:
            required = " + ".join(recipe.required_types)
            raise ValueError(f"{recipe.name} requires {required} source items.")
        for item, required_type in zip(
            sorted(source_items, key=lambda source: str(source.get("type", "")).lower()),
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
                stats[stat_name] = stats.get(stat_name, 0.0) + float(stat_value)
        for stat_name, bonus in recipe.stats.items():
            stats[stat_name] = stats.get(stat_name, 0.0) + float(bonus)

        rarity_multiplier = RARITY_MULTIPLIERS.get(rarity, 1.0)
        stats = {key: value * rarity_multiplier for key, value in stats.items()}
        stats.update(output_metadata)
        source_ids = sorted(str(item.get("id")) for item in selected)
        identity = json.dumps([recipe.id, source_ids], separators=(",", ":"), ensure_ascii=True)
        identity_suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]

        result = {
            "id": f"fusion-{recipe.id}-{identity_suffix}",
            "name": recipe.name,
            "type": recipe.item_type,
            "rarity": rarity,
            "level": total_level,
            "stats": stats,
            "combinations": [None] * RARITY_COMBINATION_SLOTS[rarity],
            "status": "normal",
            "fusion_recipe": recipe.id,
            "fusion_origin": source_ids,
            "fusion_only": True,
            "description": recipe.description,
        }
        if output_tags:
            result["tags"] = output_tags
        return result
