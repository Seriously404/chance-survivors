"""Shared, once-only effectiveness modifiers for damage and healing."""

import math

from game.utils.large_number import LargeNumber


def effect_multiplier(bonus_pct):
    """Convert a finite percent modifier to a nonnegative multiplier."""
    if (isinstance(bonus_pct, bool)
            or not isinstance(bonus_pct, (int, float))
            or not math.isfinite(bonus_pct)):
        raise ValueError("Effectiveness bonus must be a finite number")
    return max(0.0, 1.0 + bonus_pct / 100.0)


def restore_health(player, amount, bonus_pct=0.0):
    """Restore actual health, with effectiveness once and no over-healing.

    This affects health restoration, including damage-to-health conversion.
    Shields and defensive absorption are intentionally separate mechanics.
    """
    amount = max(LargeNumber(0), LargeNumber(amount))
    missing = max(LargeNumber(0), player.max_health - player.health)
    restored = min(missing, amount * effect_multiplier(bonus_pct))
    player.health += restored
    return restored


# Relics grant these passives once while owned, including while assigned as a
# supplement. Damage/delivery fields such as area_radius are intentionally not
# on this list and retain their complete combination contribution.
OWNED_PASSIVE_STATS = frozenset({
    "defense", "health", "speed_pct", "luck", "damage_pct", "crit_chance",
    "score_bonus_pct", "elemental_dmg", "healing_pct",
})


def combined_local_stat(combined, name, default=0):
    """Read a combined stat without re-granting globally owned relic passives.

    Trace amounts already include both source and base rarity scaling. Removing
    those amounts preserves all non-relic sources and rule contributions.
    """
    value = combined.stats.get(name, LargeNumber(default))
    if name not in OWNED_PASSIVE_STATS:
        return value
    owned_ids = set(combined.metadata.get("owned_relic_ids", ()))
    for entry in combined.contributions.get(name, ()):
        if (entry.get("kind") == "supplement"
                and entry.get("source_id") in owned_ids):
            value -= entry["amount"]
    return value


class HealingBudget:
    """One finite pre-effect restoration budget shared by a cast or volley."""

    def __init__(self, amount):
        self.remaining = max(LargeNumber(0), LargeNumber(amount))

    def restore(self, player, damage_dealt, bonus_pct=0.0):
        factor = effect_multiplier(bonus_pct)
        if factor <= 0:
            return LargeNumber(0)
        eligible = min(self.remaining, max(LargeNumber(0), LargeNumber(damage_dealt)))
        restored = restore_health(player, eligible, bonus_pct)
        self.remaining = max(LargeNumber(0), self.remaining - restored / factor)
        return restored


def heal_from_damage(player, damage_dealt, bonus_pct=0.0, budget=None):
    """Restore from actual damage, respecting an optional cast-wide budget."""
    if budget is not None:
        return budget.restore(player, damage_dealt, bonus_pct)
    return restore_health(player, damage_dealt, bonus_pct)
