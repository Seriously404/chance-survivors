"""Combination evaluation engine for calculating combined item statistics.

This module provides a reusable system for evaluating how supplemental items
affect base items through generic stat interactions, type-based interactions,
and custom interactions.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from game.systems.inventory import RARITY_COMBINATION_SLOTS


class CombinationEvaluator:
    """Evaluate how supplemental items modify base item statistics."""

    def __init__(self) -> None:
        self._rarity_order = [
            "common", "uncommon", "rare", "epic", "legendary", "mythical", "ultimate"
        ]

    def _rarity_rank(self, rarity: str) -> int:
        rarity = str(rarity).lower()
        if rarity not in self._rarity_order:
            raise ValueError(f"Unsupported rarity: {rarity}")
        return self._rarity_order.index(rarity)

    def evaluate_combination(
        self,
        base_item: dict[str, Any],
        supplements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Evaluate a base item with its supplemental items.

        Returns a dict with:
        - base_item: The original base item
        - supplements: List of supplemental items
        - combined_stats: Aggregated statistics
        - interactions: List of detected interactions
        - final_stats: Final calculated statistics after all modifiers
        """
        if not supplements:
            return {
                "base_item": deepcopy(base_item),
                "supplements": [],
                "combined_stats": {},
                "interactions": [],
                "final_stats": {},
            }

        combined_stats = self._aggregate_stats(base_item, supplements)
        interactions = self._detect_interactions(base_item, supplements)
        final_stats = self._apply_interactions(combined_stats, interactions)

        return {
            "base_item": deepcopy(base_item),
            "supplements": [deepcopy(s) for s in supplements],
            "combined_stats": combined_stats,
            "interactions": interactions,
            "final_stats": final_stats,
        }

    def _aggregate_stats(
        self,
        base_item: dict[str, Any],
        supplements: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Aggregate statistics from base and supplemental items."""
        stats = dict(base_item.get("stats", {}))

        for supplement in supplements:
            supplement_stats = supplement.get("stats", {})
            for key, value in supplement_stats.items():
                if isinstance(value, (int, float)):
                    stats[key] = stats.get(key, 0.0) + float(value)

        return stats

    def _detect_interactions(
        self,
        base_item: dict[str, Any],
        supplements: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Detect special interactions between base and supplemental items."""
        interactions = []

        base_type = base_item.get("type", "")
        base_stats = base_item.get("stats", {})
        base_element = base_stats.get("element", "physical")

        for supplement in supplements:
            supplement_type = supplement.get("type", "")
            supplement_stats = supplement.get("stats", {})

            # Type-based interactions
            if self._is_ability(supplement):
                interaction = self._detect_ability_interaction(
                    base_item, supplement, base_element
                )
                if interaction:
                    interactions.append(interaction)

            # Custom interactions for specific stat combinations
            custom_interaction = self._detect_custom_interaction(
                base_item, supplement, base_stats, supplement_stats
            )
            if custom_interaction:
                interactions.append(custom_interaction)

        return interactions

    def _is_ability(self, item: dict[str, Any]) -> bool:
        """Check if an item is an ability."""
        return str(item.get("type", "")).lower() == "ability"

    def _detect_ability_interaction(
        self,
        base_item: dict[str, Any],
        supplement: dict[str, Any],
        base_element: str,
    ) -> dict[str, Any] | None:
        """Detect interactions when an ability is combined with another item."""
        supplement_stats = supplement.get("stats", {})

        # Fire + projectile = AoE explosion
        if base_element == "fire" and supplement_stats.get("cast_type") == "projectile":
            return {
                "type": "aoe_explosion",
                "description": "Fire projectile creates an area explosion",
                "effects": {"damage_pct": 20.0, "aoe_radius": 1.0},
            }

        # Teleport + fire = burning trail
        if supplement_stats.get("cast_type") == "teleport" and base_element == "fire":
            return {
                "type": "burning_trail",
                "description": "Teleport leaves a burning path",
                "effects": {"damage_pct": 10.0, "burn_duration": 3.0},
            }

        # Healing + damage ability = life steal
        if supplement_stats.get("cast_type") == "heal" and base_stats.get("cast_damage"):
            return {
                "type": "life_steal",
                "description": "Healing ability steals health from enemies",
                "effects": {"heal_pct": 5.0, "damage_conversion": 0.3},
            }

        # Generic ability stacking
        if supplement_stats.get("cast_damage"):
            return {
                "type": "damage_boost",
                "description": "Ability damage increased",
                "effects": {"damage_pct": float(supplement_stats.get("cast_damage", 0))},
            }

        return None

    def _detect_custom_interaction(
        self,
        base_item: dict[str, Any],
        supplement: dict[str, Any],
        base_stats: dict[str, Any],
        supplement_stats: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Detect custom interactions based on specific stat combinations."""
        # Luck + damage = crit chance
        if supplement_stats.get("luck") and base_stats.get("damage"):
            return {
                "type": "luck_damage_synergy",
                "description": "Luck enhances damage output",
                "effects": {"crit_chance": float(supplement_stats.get("luck", 0)) * 0.5},
            }

        # Speed + defense = mobility
        if supplement_stats.get("speed_pct") and base_stats.get("defense"):
            return {
                "type": "mobility_synergy",
                "description": "Speed enhances defensive capabilities",
                "effects": {"speed_defense_bonus": float(supplement_stats.get("speed_pct", 0)) * 0.1},
            }

        return None

    def _apply_interactions(
        self,
        combined_stats: dict[str, float],
        interactions: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Apply interaction effects to combined statistics."""
        final_stats = dict(combined_stats)

        for interaction in interactions:
            effects = interaction.get("effects", {})
            for effect_name, effect_value in effects.items():
                if isinstance(effect_value, (int, float)):
                    final_stats[effect_name] = final_stats.get(effect_name, 0.0) + float(effect_value)

        return final_stats

    def get_combination_summary(
        self,
        base_item: dict[str, Any],
        supplements: list[dict[str, Any]],
    ) -> str:
        """Get a human-readable summary of a combination."""
        evaluation = self.evaluate_combination(base_item, supplements)

        lines = [f"Base: {base_item.get('name', base_item.get('id', 'Unknown'))}"]
        if supplements:
            lines.append(f"Supplements: {', '.join(s.get('name', s.get('id', 'Unknown')) for s in supplements)}")

        if evaluation["interactions"]:
            lines.append("Interactions:")
            for interaction in evaluation["interactions"]:
                lines.append(f"  - {interaction['type']}: {interaction['description']}")

        return "\n".join(lines)
