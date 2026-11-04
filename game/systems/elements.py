"""Element definitions and resistance-aware damage resolution."""

from __future__ import annotations

from typing import Any

ELEMENTS: dict[str, dict[str, Any]] = {
    "physical": {"label": "Physical", "color": (220, 220, 220)},
    "fire": {"label": "Fire", "color": (255, 130, 70)},
    "frost": {"label": "Frost", "color": (120, 210, 255)},
    "arcane": {"label": "Arcane", "color": (180, 120, 255)},
    "shadow": {"label": "Shadow", "color": (130, 95, 180)},
    "nature": {"label": "Nature", "color": (90, 210, 120)},
    "light": {"label": "Light", "color": (245, 230, 120)},
}


def normalize_element(name: str | None) -> str:
    key = (name or "physical").strip().lower()
    return key if key in ELEMENTS else "physical"


def element_label(name: str | None) -> str:
    return ELEMENTS.get(normalize_element(name), ELEMENTS["physical"])["label"]


def apply_elemental_damage(
    base_damage: int | float,
    element: str | None,
    resistances: dict[str, float] | None,
    *,
    bonus_pct: float = 0.0,
) -> int:
    """Apply element bonuses and target resistances to a source attack."""
    from game.utils.large_number import LargeNumber
    ordinary_damage = isinstance(base_damage, (int, float))
    damage = LargeNumber(base_damage)
    if bonus_pct:
        damage *= 1.0 + (float(bonus_pct) / 100.0)
    norm = normalize_element(element)
    resistance = 0.0
    if resistances:
        resistance = float(resistances.get(norm, 0.0))
    if norm == "physical":
        resistance = 0.0
    effective = damage * max(0.0, 1.0 - resistance)
    if ordinary_damage:
        return max(1, int(effective.to_float()))
    return max(LargeNumber(1), effective)


def resolve_damage_components(base_damage, element, resistances, components=()):
    """Resolve the separately resisted portions of a hybrid attack."""
    from game.utils.large_number import LargeNumber

    primary_element = normalize_element(element)
    resolved = {primary_element: LargeNumber(
        apply_elemental_damage(base_damage, element, resistances))}
    for component in components:
        damage = LargeNumber(component["damage"])
        if damage <= 0:
            continue
        component_element = normalize_element(component.get("element"))
        resistance = (0.0 if component_element == "physical" else
                      float((resistances or {}).get(component_element, 0.0)))
        resolved[component_element] = resolved.get(component_element, LargeNumber(0)) + (
            damage * max(0.0, 1.0 - resistance))
    return resolved
