"""Headless evaluation of item combinations and their stat contributions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from game.systems.inventory import Inventory
from game.systems.item_potential import level_potential
from game.utils.large_number import LargeNumber


COMBINATION_RULES_PATH = Path(__file__).resolve(
).parents[2] / "assets" / "combination_rules.json"
RARITY_DATA_PATH = Path(__file__).resolve(
).parents[2] / "assets" / "rarity_multipliers.json"
RULES_VERSION = 1
RARITY_DATA_VERSION = 1
_NUMERIC_TYPES = (LargeNumber, int, float)


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load {label} at {path}: {exc}") from exc


def _string_set(raw: Any, label: str) -> frozenset[str]:
    if raw is None:
        return frozenset()
    if not isinstance(raw, list) or any(not isinstance(item, str) or not item for item in raw):
        raise ValueError(f"{label} must be a list of non-empty strings")
    if len(raw) != len(set(raw)):
        raise ValueError(f"{label} must not contain duplicates")
    return frozenset(raw)


@dataclass(frozen=True, slots=True)
class StatModifier:
    stat: str
    operation: str
    value: LargeNumber

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> StatModifier:
        if not isinstance(raw, Mapping):
            raise ValueError("Combination stat modifier must be an object")
        stat, operation = raw.get("stat"), raw.get("operation")
        if not isinstance(stat, str) or not stat:
            raise ValueError("Combination stat modifier needs a stat name")
        if operation not in ("add", "multiply"):
            raise ValueError(
                "Combination stat modifier operation must be add or multiply")
        value = raw.get("value")
        if isinstance(value, bool):
            raise ValueError("Combination stat modifier value must be numeric")
        return cls(stat, operation, LargeNumber(value))

    def to_dict(self) -> dict[str, Any]:
        return {"stat": self.stat, "operation": self.operation, "value": self.value.to_dict()}


@dataclass(frozen=True, slots=True)
class CombinationRule:
    rule_id: str
    base_types: frozenset[str]
    supplement_types: frozenset[str]
    base_tags: frozenset[str]
    supplement_tags: frozenset[str]
    add_tags: frozenset[str]
    behaviors: frozenset[str]
    stat_modifiers: tuple[StatModifier, ...]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CombinationRule:
        if not isinstance(raw, Mapping):
            raise ValueError("Combination rule must be an object")
        rule_id = raw.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError("Combination rule needs a stable id")
        modifiers = raw.get("stat_modifiers", [])
        if not isinstance(modifiers, list):
            raise ValueError(f"{rule_id}.stat_modifiers must be a list")
        return cls(
            rule_id=rule_id,
            base_types=_string_set(raw.get("base_types"),
                                   f"{rule_id}.base_types"),
            supplement_types=_string_set(
                raw.get("supplement_types"), f"{rule_id}.supplement_types"),
            base_tags=_string_set(raw.get("base_tags"),
                                  f"{rule_id}.base_tags"),
            supplement_tags=_string_set(
                raw.get("supplement_tags"), f"{rule_id}.supplement_tags"),
            add_tags=_string_set(raw.get("add_tags"), f"{rule_id}.add_tags"),
            behaviors=_string_set(raw.get("behaviors"),
                                  f"{rule_id}.behaviors"),
            stat_modifiers=tuple(StatModifier.from_dict(modifier)
                                 for modifier in modifiers),
        )

    def matches(self, base: Mapping[str, Any], supplement: Mapping[str, Any]) -> bool:
        base_tags = set(base.get("tags", ()))
        supplement_tags = set(supplement.get("tags", ()))
        return (
            (not self.base_types or base.get("type") in self.base_types)
            and (not self.supplement_types or supplement.get("type") in self.supplement_types)
            and self.base_tags.issubset(base_tags)
            and self.supplement_tags.issubset(supplement_tags)
        )


@dataclass(frozen=True, slots=True)
class CombinedItem:
    """Evaluated item data plus a trace of its contributing components."""

    base_id: str
    name: str
    item_type: str
    rarity: str
    level: int
    ultimate_tier: int | None
    stats: Mapping[str, LargeNumber]
    metadata: Mapping[str, Any]
    tags: tuple[str, ...]
    behaviors: tuple[str, ...]
    component_ids: tuple[str, ...]
    rules_applied: tuple[str, ...]
    contributions: Mapping[str, tuple[Mapping[str, Any], ...]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_id": self.base_id,
            "name": self.name,
            "type": self.item_type,
            "rarity": self.rarity,
            "level": self.level,
            "ultimate_tier": self.ultimate_tier,
            "stats": {key: value.to_dict() for key, value in self.stats.items()},
            "metadata": dict(self.metadata),
            "tags": list(self.tags),
            "behaviors": list(self.behaviors),
            "component_ids": list(self.component_ids),
            "rules_applied": list(self.rules_applied),
            "contributions": {
                stat: [
                    {key: value.to_dict() if isinstance(value, LargeNumber) else value
                     for key, value in entry.items()}
                    for entry in entries
                ]
                for stat, entries in self.contributions.items()
            },
        }


class CombinationEngine:
    """Apply generic component stats, rarity/level scaling, and custom rules.

    Evaluation order is:
    1. Add each component's linear, additive per-level amount (10% of its
       base stat per level by default).
    2. Multiply each supplement's contribution by its own rarity.
    3. Sum component values and apply matching custom rule modifiers.
    4. Multiply the full combined result by the base item's rarity.

    This ensures the base rarity multiplies stats introduced by supplements
    while each supplement's own rarity still changes its contribution.
    """

    def __init__(
        self,
        rules: Iterable[CombinationRule | Mapping[str, Any]] | None = None,
        *,
        rarity_data: Mapping[str, Any] | None = None,
    ) -> None:
        raw_rules = rules if rules is not None else self._load_rules()
        self.rules = tuple(
            rule if isinstance(
                rule, CombinationRule) else CombinationRule.from_dict(rule)
            for rule in raw_rules
        )
        rule_ids = [rule.rule_id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Combination rule ids must be unique")
        self.rarity_data = dict(
            rarity_data) if rarity_data is not None else self._load_rarity_data()
        if type(self.rarity_data.get("version")) is not int or self.rarity_data["version"] != RARITY_DATA_VERSION:
            raise ValueError("Unsupported rarity multiplier data version")
        multipliers = self.rarity_data.get("multipliers")
        if not isinstance(multipliers, Mapping):
            raise ValueError("Rarity data needs a multiplier map")
        self.rarity_multipliers = {str(key): LargeNumber(
            value) for key, value in multipliers.items()}
        required_rarities = {"common", "uncommon", "rare",
                             "epic", "legendary", "mythical", "ultimate"}
        if set(self.rarity_multipliers) != required_rarities:
            raise ValueError(
                "Rarity data must define every supported rarity exactly once")
        if any(isinstance(value, bool) for value in multipliers.values()):
            raise ValueError("Rarity multipliers must be numeric")
        if any(value <= 0 for value in self.rarity_multipliers.values()):
            raise ValueError("Rarity multipliers must be positive")
        raw_level_fraction = self.rarity_data.get("level_add_fraction", "0.1")
        raw_ultimate_step = self.rarity_data.get(
            "ultimate_tier_step_multiplier", "1.1")
        if isinstance(raw_level_fraction, bool) or isinstance(raw_ultimate_step, bool):
            raise ValueError("Rarity growth values must be numeric")
        self.level_add_fraction = LargeNumber(raw_level_fraction)
        self.ultimate_tier_step = LargeNumber(raw_ultimate_step)
        if self.level_add_fraction < 0 or self.ultimate_tier_step < 1:
            raise ValueError(
                "Level growth must be non-negative and ultimate tier growth at least one")

    @staticmethod
    def _load_rules() -> list[dict[str, Any]]:
        raw = _load_json(COMBINATION_RULES_PATH, "combination rules")
        if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] != RULES_VERSION:
            raise ValueError("Unsupported combination rules data version")
        rules = raw.get("rules")
        if not isinstance(rules, list):
            raise ValueError("Combination rules file needs a rules list")
        return rules

    @staticmethod
    def _load_rarity_data() -> dict[str, Any]:
        raw = _load_json(RARITY_DATA_PATH, "rarity multipliers")
        if not isinstance(raw, dict):
            raise ValueError("Rarity multiplier data must be an object")
        return raw

    def rarity_multiplier(self, item: Mapping[str, Any]) -> LargeNumber:
        rarity = str(item.get("rarity", "common")).lower()
        try:
            multiplier = self.rarity_multipliers[rarity]
        except KeyError as exc:
            raise ValueError(f"Unsupported item rarity: {rarity}") from exc
        if rarity != "ultimate":
            if "ultimate_tier" in item:
                raise ValueError(
                    "Only ultimate items may have an ultimate_tier")
            return multiplier
        tier = item.get("ultimate_tier", 1)
        if type(tier) is not int or not 1 <= tier <= 100:
            raise ValueError(
                "Ultimate tier must be an integer between 1 and 100")
        return multiplier * (self.ultimate_tier_step ** (tier - 1))

    def _component_stats(self, item: Mapping[str, Any], *, supplement: bool) -> tuple[dict[str, LargeNumber], dict[str, Any]]:
        stats = item.get("stats", {})
        if not isinstance(stats, Mapping):
            raise ValueError("Item stats must be an object")
        level = item.get("level", 1)
        if type(level) is not int or level < 1:
            raise ValueError("Item level must be a positive integer")
        output: dict[str, LargeNumber] = {}
        metadata: dict[str, Any] = {}
        supplement_rarity = self.rarity_multiplier(
            item) if supplement else LargeNumber(1)
        for name, value in stats.items():
            if not isinstance(name, str) or not name:
                raise ValueError("Item stat names must be non-empty strings")
            if isinstance(value, bool):
                metadata[name] = value
                continue
            if isinstance(value, _NUMERIC_TYPES):
                # Cooldowns describe how often the base is used, not a bonus
                # contributed by a different item.
                if name == "cooldown" and supplement:
                    continue
                base_value = LargeNumber(value)
                rate = (LargeNumber("-0.02") if name == "cooldown" else self.level_add_fraction) * \
                    LargeNumber(str(level_potential(item)))
                level_value = base_value + base_value * rate * (level - 1)
                output[name] = level_value * supplement_rarity
            else:
                metadata[name] = value
        return output, metadata

    @staticmethod
    def _item_identity(item: Mapping[str, Any], label: str) -> tuple[str, str]:
        item_id, item_type = item.get("id"), item.get("type")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError(f"{label} item needs a stable string id")
        if not isinstance(item_type, str) or not item_type:
            raise ValueError(f"{label} item needs a type")
        return item_id, item_type

    def evaluate(
        self,
        base: Mapping[str, Any],
        supplements: Sequence[Mapping[str, Any]] = (),
    ) -> CombinedItem:
        if not isinstance(base, Mapping):
            raise ValueError("Combination base must be an item object")
        if not isinstance(supplements, Sequence) or isinstance(supplements, (str, bytes)):
            raise ValueError(
                "Combination supplements must be an ordered sequence")
        base_id, base_type = self._item_identity(base, "Base")
        base_slots = base.get("combinations", [])
        if not isinstance(base_slots, list):
            raise ValueError("Base combination slots must be a list")
        if len(supplements) > len(base_slots):
            raise ValueError(
                "Combination exceeds the base item's available slots")
        if base.get("status") == "supplement":
            raise ValueError(
                "A combination supplement cannot also be a base item")

        component_ids = [base_id]
        totals, base_metadata = self._component_stats(base, supplement=False)
        trace: dict[str, list[dict[str, Any]]] = {
            stat: [{"source_id": base_id, "kind": "base", "amount": value}]
            for stat, value in totals.items()
        }
        tags = set(_string_set(base.get("tags", []), "base.tags"))
        behaviors = set(_string_set(
            base.get("behaviors", []), "base.behaviors"))
        rule_ids: list[str] = []
        seen_ids = {base_id}
        metadata: dict[str, Any] = dict(base_metadata)
        base_rarity = self.rarity_multiplier(base)

        for supplement in supplements:
            if not isinstance(supplement, Mapping):
                raise ValueError(
                    "Combination supplements must be item objects")
            supplement_id, supplement_type = self._item_identity(
                supplement, "Supplement")
            if supplement_id in seen_ids:
                raise ValueError(
                    "An item cannot be repeated or combined with itself")
            seen_ids.add(supplement_id)
            if ((base_type == "armor") != (supplement_type == "armor")
                    and not (base_type == "armor" and supplement.get("fusion_recipe") == "elemental-core")):
                raise ValueError("Armor can only combine with armor")
            if supplement.get("status") == "active":
                raise ValueError(
                    "An actively equipped item cannot be a supplement")
            supplement_slots = supplement.get("combinations", [])
            if not isinstance(supplement_slots, list):
                raise ValueError("Supplement combination slots must be a list")
            if any(value is not None for value in supplement_slots):
                raise ValueError(
                    "A supplement cannot also contain its own supplements")

            component_ids.append(supplement_id)
            supplement_stats, supplement_metadata = self._component_stats(
                supplement, supplement=True)
            for stat, amount in supplement_stats.items():
                totals[stat] = totals.get(stat, LargeNumber(0)) + amount
                trace.setdefault(stat, []).append(
                    {"source_id": supplement_id,
                        "kind": "supplement", "amount": amount}
                )
            if supplement_metadata:
                metadata.setdefault("supplements", {})[
                    supplement_id] = supplement_metadata
            tags.update(_string_set(supplement.get(
                "tags", []), f"{supplement_id}.tags"))
            behaviors.update(_string_set(supplement.get(
                "behaviors", []), f"{supplement_id}.behaviors"))

            for rule in self.rules:
                if not rule.matches(base, supplement):
                    continue
                rule_ids.append(rule.rule_id)
                tags.update(rule.add_tags)
                behaviors.update(rule.behaviors)
                for modifier in rule.stat_modifiers:
                    current = totals.get(modifier.stat, LargeNumber(0))
                    updated = current + \
                        modifier.value if modifier.operation == "add" else current * modifier.value
                    totals[modifier.stat] = updated
                    trace.setdefault(modifier.stat, []).append({
                        "source_id": rule.rule_id,
                        "kind": f"rule_{modifier.operation}",
                        "before": current,
                        "amount": modifier.value,
                        "after": updated,
                    })

        # Base rarity applies to every component and custom stat effect.
        final_stats = {stat: (max(LargeNumber("0.05"), value / base_rarity)
                              if stat == "cooldown" else value * base_rarity)
                       for stat, value in totals.items()}
        for stat, entries in trace.items():
            for entry in entries:
                scale = LargeNumber(
                    1) / base_rarity if stat == "cooldown" else base_rarity
                if entry["kind"].startswith("rule_"):
                    for key in ("before", "amount", "after"):
                        entry[key] = entry[key] * scale
                else:
                    entry["amount"] = entry["amount"] * scale

        name = base.get("name", base_id)
        if not isinstance(name, str):
            raise ValueError("Item name must be a string")
        level = base.get("level", 1)
        return CombinedItem(
            base_id=base_id,
            name=name,
            item_type=base_type,
            rarity=str(base.get("rarity", "common")).lower(),
            level=level,
            ultimate_tier=base.get("ultimate_tier") if str(
                base.get("rarity", "common")).lower() == "ultimate" else None,
            stats=final_stats,
            metadata=metadata,
            tags=tuple(sorted(tags)),
            behaviors=tuple(sorted(behaviors)),
            component_ids=tuple(component_ids),
            rules_applied=tuple(rule_ids),
            contributions={stat: tuple(entries)
                           for stat, entries in trace.items()},
        )

    def evaluate_inventory(self, inventory: Inventory, base_id: str) -> CombinedItem:
        """Evaluate a base and its assigned supplements without mutating inventory."""
        if inventory.is_combination_supplement(base_id):
            raise ValueError(
                "A combination supplement cannot be used as a base")
        base = inventory.get(base_id)
        slots = base.get("combinations", [])
        supplements = [inventory.get(item_id)
                       for item_id in slots if item_id is not None]
        return self.evaluate(base, supplements)
