"""Controlled direct-hit criticals shared by weapons, abilities and summons.

The stat is a percentage, not a multiplier: 25 means one chance in four per
target hit. Criticals double the resolved direct hit once. Lingering damage and
trails never roll again, so repeated effects cannot compound critical damage.
"""

import math
import random

from game.utils.large_number import LargeNumber


CRITICAL_DAMAGE_MULTIPLIER = 2


def critical_probability(chance):
    """Clamp percentage bonuses safely even at extreme progression values."""
    if chance >= 100:
        return 1.0
    if chance <= 0:
        return 0.0
    value = chance.to_float() if isinstance(chance, LargeNumber) else float(chance)
    if math.isnan(value):
        return 0.0
    return max(0.0, min(100.0, value)) / 100.0


def resolve_critical_hit(components, chance, *, rng=random):
    """Return fresh damage components and whether this target suffered a crit."""
    probability = critical_probability(chance)
    critical = probability >= 1 or (probability > 0 and rng.random() < probability)
    multiplier = CRITICAL_DAMAGE_MULTIPLIER if critical else 1
    return ({element: LargeNumber(damage) * multiplier
             for element, damage in components.items()}, critical)
