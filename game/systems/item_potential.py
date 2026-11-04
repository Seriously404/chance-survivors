"""Level-growth potential based on an item's original rarity."""

from collections.abc import Mapping
from typing import Any

POTENTIAL = {"common": 1.0, "uncommon": 0.9, "rare": 0.8,
             "epic": 0.7, "legendary": 0.6, "mythical": 0.5, "ultimate": 0.4}


def level_potential(item: Mapping[str, Any]) -> float:
    """Return the fraction of the normal per-level growth this item receives.

    Old saves without origin metadata retain their original level growth,
    since their starting rarity cannot be recovered reliably.
    """
    if "base_rarity" not in item:
        return 1.0
    rarity = str(item["base_rarity"]).lower()
    try:
        return POTENTIAL[rarity]
    except KeyError as exc:
        raise ValueError(f"Unsupported base rarity: {rarity}") from exc
