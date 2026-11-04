"""Centralized probability and luck system for Chance Survivors.

This module provides configurable probability calculations with luck integration.
Different systems can use luck differently, ensuring numerical stability at
extremely high luck values and avoiding probability overflow.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProbabilityConfig:
    """Configuration for a probability system."""

    base_probability: float = 0.5
    luck_factor: float = 0.1
    max_probability: float = 0.98
    min_probability: float = 0.0
    luck_cap: float = 100.0
    description: str = ""


class ProbabilitySystem:
    """Centralized probability calculations with luck integration."""

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self._configs: dict[str, ProbabilityConfig] = {}

    def register_config(self, system_name: str, config: ProbabilityConfig) -> None:
        """Register a probability configuration for a specific system."""
        self._configs[system_name] = config

    def get_config(self, system_name: str) -> ProbabilityConfig:
        """Get the configuration for a specific system."""
        if system_name not in self._configs:
            # Default configuration if not registered
            return ProbabilityConfig(description=f"Default config for {system_name}")
        return self._configs[system_name]

    def calculate_probability(
        self,
        system_name: str,
        luck: float = 0.0,
        custom_modifier: float = 0.0,
    ) -> float:
        """
        Calculate probability for a system with luck integration.

        Args:
            system_name: Name of the probability system
            luck: Player luck stat affecting the probability
            custom_modifier: Additional custom probability modifier

        Returns:
            A probability value between 0.0 and 1.0
        """
        config = self.get_config(system_name)

        # Apply luck factor with cap
        adjusted_luck = min(luck, config.luck_cap)
        luck_contribution = adjusted_luck * config.luck_factor

        # Calculate base probability with modifiers
        base = config.base_probability + luck_contribution + custom_modifier

        # Clamp to valid range
        return max(config.min_probability, min(config.max_probability, base))

    def roll(self, system_name: str, luck: float = 0.0, custom_modifier: float = 0.0) -> bool:
        """
        Roll against a probability system.

        Args:
            system_name: Name of the probability system
            luck: Player luck stat
            custom_modifier: Additional modifier

        Returns:
            True if the roll succeeds, False otherwise
        """
        probability = self.calculate_probability(system_name, luck, custom_modifier)
        return self.rng.random() < probability

    def roll_with_description(
        self,
        system_name: str,
        luck: float = 0.0,
        custom_modifier: float = 0.0,
    ) -> tuple[bool, str]:
        """
        Roll against a probability system with detailed feedback.

        Returns:
            Tuple of (success, description)
        """
        config = self.get_config(system_name)
        probability = self.calculate_probability(system_name, luck, custom_modifier)
        success = self.rng.random() < probability

        description = (
            f"{system_name}: {probability:.2%} probability "
            f"(base: {config.base_probability:.2%}, "
            f"luck: {luck:.1f}, "
            f"modifier: {custom_modifier:+.2%})"
        )

        return success, description

    def register_system(
        self,
        system_name: str,
        base_probability: float = 0.5,
        luck_factor: float = 0.1,
        max_probability: float = 0.98,
        min_probability: float = 0.0,
        luck_cap: float = 100.0,
        description: str = "",
    ) -> None:
        """Convenience method to register a probability system."""
        config = ProbabilityConfig(
            base_probability=base_probability,
            luck_factor=luck_factor,
            max_probability=max_probability,
            min_probability=min_probability,
            luck_cap=luck_cap,
            description=description,
        )
        self.register_config(system_name, config)


# Pre-registered probability systems
PROBABILITY_SYSTEMS = ProbabilitySystem()

# Initialize default systems
PROBABILITY_SYSTEMS.register_system(
    "crate_reward",
    base_probability=0.3,
    luck_factor=0.05,
    max_probability=0.95,
    description="Crate reward probability",
)

PROBABILITY_SYSTEMS.register_system(
    "rarity_upgrade",
    base_probability=0.35,
    luck_factor=0.1,
    max_probability=0.98,
    description="Rarity upgrade success probability",
)

PROBABILITY_SYSTEMS.register_system(
    "item_drop",
    base_probability=0.1,
    luck_factor=0.02,
    max_probability=0.5,
    description="Special item drop probability",
)

PROBABILITY_SYSTEMS.register_system(
    "critical_proc",
    base_probability=0.05,
    luck_factor=0.03,
    max_probability=0.25,
    description="Critical proc probability",
)

PROBABILITY_SYSTEMS.register_system(
    "random_event",
    base_probability=0.01,
    luck_factor=0.005,
    max_probability=0.1,
    description="Random event trigger probability",
)


def get_probability_system() -> ProbabilitySystem:
    """Get the global probability system instance."""
    return PROBABILITY_SYSTEMS
