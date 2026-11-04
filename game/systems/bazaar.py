"""Modular economy features for the Bazaar and content expansion.

This module keeps the design's gambling and progression systems isolated from
rendering and the main game loop so they may be tested headlessly.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import random
import math
from typing import Any

from game.systems.inventory import RARITY_COMBINATION_SLOTS
from game.systems.json_loader import load_abilities, load_armor, load_weapons, load_relics

RARITY_ORDER = [
    "common",
    "uncommon",
    "rare",
    "epic",
    "legendary",
    "mythical",
    "ultimate",
]

RARITY_TIER = {rarity: index for index, rarity in enumerate(RARITY_ORDER)}
CRATE_LUCK_REQUIREMENTS = (0, 0, 1, 4, 10, 25, 60)


@dataclass(frozen=True)
class BazaarCrate:
    """Shop crate definition."""

    id: str
    name: str
    cost: int
    bias: str
    weight: float = 1.0
    description: str = ""
    unlock_seconds: float = 0.0
    currency: str = "Gold"
    element: str = ""
    extra_costs: tuple[tuple[str, int], ...] = ()

    @property
    def costs(self) -> dict[str, int]:
        costs = {self.currency: self.cost}
        for currency, amount in self.extra_costs:
            costs[currency] = costs.get(currency, 0) + amount
        return costs


class BazaarManager:
    """Provide data-driven economy actions with injectable randomness."""

    ROTATION_SECONDS = 300
    MAX_CRATE_OFFERS = 4

    def __init__(
        self,
        catalog: list[dict[str, Any]] | None = None,
        *,
        rng: random.Random | None = None,
        seed: int | None = None,
        refresh_count: int = 0,
        last_manual_refresh_cycle: int = -1,
    ) -> None:
        self.catalog = [deepcopy(item) for item in (catalog or [])]
        if seed is not None and (type(seed) is not int or seed < 0):
            raise ValueError("Bazaar seed must be a non-negative integer")
        if type(refresh_count) is not int or refresh_count < 0:
            raise ValueError(
                "Bazaar refresh count must be a non-negative integer")
        if type(last_manual_refresh_cycle) is not int or last_manual_refresh_cycle < -1:
            raise ValueError("Bazaar manual refresh cycle is invalid")
        self.seed = seed if seed is not None else random.SystemRandom().getrandbits(64)
        self.rng = rng or random.Random()
        self.refresh_count = refresh_count
        self.last_manual_refresh_cycle = last_manual_refresh_cycle
        self.crate_catalog = [
            BazaarCrate(id="daily-crate", name="Daily Crate", cost=60, bias="rare", currency="Copper",
                        description="A random selection refreshed every active minute."),
            BazaarCrate(
                id="starter-crate",
                name="Cheapskate Box",
                cost=35,
                bias="common",
                currency="Copper",
                description="A safe, cheap crate with a high chance of a reliable item.",
            ),
            BazaarCrate(
                id="gilded-crate",
                name="Gilded Crate",
                cost=80,
                bias="rare",
                description="A mid-tier gamble with better odds of a rare drop.",
                currency="Silver",
            ),
            BazaarCrate(
                id="mythic-crate",
                name="Mythic Crate",
                cost=220,
                bias="epic",
                description="A high-cost box with access to rarer base equipment after it unlocks.",
                currency="Gold",
            ),
            BazaarCrate(id="ember-crate", name="Ember Box", cost=12, bias="uncommon",
                        currency="Ember", element="fire",
                        extra_costs=(("Copper", 25),),
                        description="Fire weapons and abilities for a burning build."),
            BazaarCrate(id="arcane-crate", name="Arcane Box", cost=12, bias="rare",
                        currency="Arcane Dust", element="arcane",
                        description="Arcane weapons and abilities for a magical build."),
            BazaarCrate(id="shadow-crate", name="Shadow Box", cost=12, bias="rare",
                        currency="Dark Matter", element="shadow",
                        description="Shadow weapons and abilities for a dark build."),
            BazaarCrate(id="light-crate", name="Radiant Box", cost=12, bias="rare",
                        currency="Holy Water", element="light",
                        description="Light weapons and abilities for a radiant build."),
            BazaarCrate(id="nature-crate", name="Verdant Box", cost=12, bias="rare",
                        currency="Essence", element="nature",
                        description="Nature weapons and abilities for a growing build."),
            BazaarCrate(id="frost-crate", name="Frost Box", cost=25, bias="rare",
                        currency="Silver", element="frost", extra_costs=(("Mana Crystal", 3),),
                        description="Cold gear for freezing the battlefield."),
            BazaarCrate(id="arsenal-crate", name="Adventurer Box", cost=120, bias="uncommon",
                        currency="Copper", extra_costs=(("Silver", 5),),
                        description="A mixed selection of early equipment."),
            BazaarCrate(
                id="astral-crate",
                name="Astral Crate",
                cost=600,
                bias="legendary",
                description="A late-run crate with access to exceptional finds.",
                unlock_seconds=600,
            ),
            BazaarCrate(
                id="void-crate",
                name="Void Crate",
                cost=1800,
                bias="mythical",
                description="A deep-run gamble for rare base equipment; upgrade it to reach mythical rarity.",
                unlock_seconds=1200,
            ),
        ]
        # Additional currency-specific boxes enter the rotating general section.
        for crate_id, name, currency in (
            ("iron-cache", "Iron Arsenal", "Iron Coin"),
            ("mana-cache", "Mana Cache", "Mana Crystal"),
            ("soul-cache", "Soul Reliquary", "Soul Fragment"),
            ("blood-cache", "Blood Cache", "Blood Orb"),
            ("time-cache", "Clockwork Cache", "Time Crystal"),
            ("star-cache", "Starlight Cache", "Star Dust"),
            ("chaos-cache", "Chaos Cache", "Chaos Fragment"),
            ("platinum-cache", "Platinum Cache", "Platinum Nugget"),
            ("quantum-cache", "Quantum Cache", "Quantum Bit"),
            ("infinity-cache", "Infinity Cache", "Infinity Shard"),
            ("soul-gem-cache", "Soul Gem Cache", "Soul Gem"),
        ):
            self.crate_catalog.append(BazaarCrate(
                id=crate_id, name=name, cost=12, bias='rare', currency=currency,
                description=f'A rotating mixed-equipment box purchased with {currency}.',
                unlock_seconds=300,
            ))
        self.crates: list[BazaarCrate] = []
        self.elapsed_seconds = 0.0
        self.daily_cycle = 0
        self.current_crate_cycle = -1
        self.refresh_crates(0)

    def refresh_crates(self, elapsed_seconds: float) -> None:
        """Update shop offers for the active-time cycle without changing run state."""
        if (
            isinstance(elapsed_seconds, bool)
            or not isinstance(elapsed_seconds, (int, float))
            or not math.isfinite(elapsed_seconds)
            or elapsed_seconds < 0
        ):
            raise ValueError("elapsed_seconds must be finite and non-negative")
        self.elapsed_seconds = float(elapsed_seconds)
        self.daily_cycle = int(elapsed_seconds // 60)
        cycle = int(elapsed_seconds // self.ROTATION_SECONDS)
        if cycle == self.current_crate_cycle:
            return
        self.current_crate_cycle = cycle
        self._select_crate_offers(elapsed_seconds)

    def manual_refresh_crates(self, elapsed_seconds: float) -> bool:
        """Reroll offers once per rotation when unlocked alternatives exist."""
        self.refresh_crates(elapsed_seconds)
        available = self.available_crates(elapsed_seconds)
        if (
            len(available) <= self.MAX_CRATE_OFFERS
            or self.last_manual_refresh_cycle == self.current_crate_cycle
        ):
            return False
        self.refresh_count += 1
        self.last_manual_refresh_cycle = self.current_crate_cycle
        self._select_crate_offers(elapsed_seconds)
        return True

    def can_manual_refresh(self, elapsed_seconds: float) -> bool:
        self.refresh_crates(elapsed_seconds)
        return (
            len(self.available_crates(elapsed_seconds)) > self.MAX_CRATE_OFFERS
            and self.last_manual_refresh_cycle != self.current_crate_cycle
        )

    def available_crates(self, elapsed_seconds: float) -> list[BazaarCrate]:
        """Return crate definitions unlocked at the supplied active-run time."""
        return [
            crate for crate in self.crate_catalog
            if crate.unlock_seconds <= elapsed_seconds
        ]

    def _select_crate_offers(self, elapsed_seconds: float) -> None:
        available = self.available_crates(elapsed_seconds)
        starter = next(
            crate for crate in available if crate.id == "starter-crate")
        daily = next(crate for crate in available if crate.id == "daily-crate")
        elemental = [crate for crate in available if crate.element]
        alternatives = [crate for crate in available if crate.id not in (
            starter.id, daily.id) and not crate.element]
        offer_count = min(self.MAX_CRATE_OFFERS - 2, len(alternatives))
        cycle_seed = self.seed + self.current_crate_cycle * 1_000_003 + self.refresh_count
        offers = random.Random(cycle_seed).sample(alternatives, offer_count)
        self.crates = [starter, daily, *sorted(
            elemental, key=lambda crate: crate.id), *sorted(offers, key=lambda crate: crate.id)]

    def add_catalog_items(self, items: list[dict[str, Any]]) -> None:
        self.catalog.extend(deepcopy(item) for item in items)

    def rarity_rank(self, rarity: str) -> int:
        rarity = str(rarity).lower()
        if rarity not in RARITY_TIER:
            raise ValueError(f"Unsupported rarity: {rarity}")
        return RARITY_TIER[rarity]

    def upgrade_rarity(
        self,
        item: dict[str, Any],
        luck: float = 0.0,
        currency_cost: int = 10,
        *,
        rng: random.Random | None = None,
    ) -> dict[str, Any]:
        current_rarity = str(item.get("rarity", "common")).lower()
        if current_rarity == "ultimate":
            current_tier = _validated_ultimate_tier(item)
            if current_tier >= 100:
                return item
            next_rarity = "ultimate"
        else:
            current_tier = 0
            current_rank = self.rarity_rank(current_rarity)
            next_rarity = RARITY_ORDER[min(
                current_rank + 1, len(RARITY_ORDER) - 1)]
        if currency_cost <= 0:
            raise ValueError(
                "upgrade_rarity requires a positive currency cost")
        level = _validated_level(item)
        combinations = item.get("combinations", [])
        if not isinstance(combinations, list):
            raise ValueError("Item combinations must be a list")
        adjusted = max(0.0, float(luck) * 0.1)
        tier_pressure = current_tier * 0.0025
        success_probability = min(
            0.98,
            max(0.05, 0.35 + adjusted +
                (self.rarity_rank(current_rarity) * 0.08) - tier_pressure),
        )
        roll = (rng or self.rng).random()
        if float(luck) >= 5.0 or roll <= success_probability:
            item.setdefault("base_rarity", current_rarity)
            item["rarity"] = next_rarity
            item["level"] = level
            if next_rarity == "ultimate":
                item["ultimate_tier"] = min(100, current_tier + 1)
            slot_count = RARITY_COMBINATION_SLOTS[next_rarity]
            item["combinations"] = combinations[:slot_count] + [None] * max(
                0, slot_count - len(combinations)
            )
        return item

    def upgrade_level(self, item: dict[str, Any], currency_cost: int = 1) -> dict[str, Any]:
        if currency_cost <= 0:
            raise ValueError("upgrade_level requires a positive currency cost")
        item["level"] = _validated_level(item) + 1
        return item

    def rarity_upgrade_cost(self, item: dict[str, Any]) -> int:
        rarity = str(item.get("rarity", "common")).lower()
        rank = self.rarity_rank(rarity)
        tier_cost = _validated_ultimate_tier(
            item) * 12 if rarity == "ultimate" else 0
        return max(8, (rank + 1) * 8 + _validated_level(item) * 4 + tier_cost)

    def level_upgrade_cost(self, item: dict[str, Any]) -> int:
        return max(5, _validated_level(item) * 6)

    def catalog_price(self, item: dict[str, Any]) -> int:
        rank = self.rarity_rank(item.get("rarity", "common"))
        return (rank + 1) * 100 + _validated_level(item) * 25

    def sell_value(self, item: dict[str, Any], *, trader_bonus: float = 0.0) -> int:
        rarity_index = self.rarity_rank(item.get("rarity", "common"))
        base = 5 + rarity_index * 10 + _validated_level(item) * 4
        return int(base * (1.0 + float(trader_bonus)))

    def roll_crate(
        self,
        crate: BazaarCrate,
        *,
        luck: float = 0.0,
        rng: random.Random | None = None,
    ) -> dict[str, Any]:
        item_pool, weights = self.crate_odds(crate, luck)
        if not weights or not any(weights):
            raise ValueError("Your luck is too low for this crate's rewards.")
        chosen = (rng or self.rng).choices(item_pool, weights=weights, k=1)[0]
        return deepcopy(chosen)

    def crate_odds(self, crate: BazaarCrate, luck: float = 0.0) -> tuple[list[dict[str, Any]], list[float]]:
        """Return the exact reward weights; higher base rarities require luck."""
        luck = float(luck)
        if not math.isfinite(luck):
            raise ValueError("Luck must be finite.")
        luck = max(0.0, luck)
        bias = self.rarity_rank(crate.bias)
        items = self.crate_rewards(crate)
        weights = []
        for item in items:
            rank = self.rarity_rank(item.get("rarity", "common"))
            if rank >= self.rarity_rank("epic") and self.elapsed_seconds < 900:
                weights.append(0.0)
                continue
            if luck < CRATE_LUCK_REQUIREMENTS[rank]:
                weights.append(0.0)
                continue
            weight = 1.0 / (1.0 + abs(rank - bias) * 2.0)
            weight *= 1.0 + rank * min(luck, 100.0) * 0.025
            if item.get("stats", {}).get("script") == "teleport":
                weight *= 0.08
            weights.append(weight)
        return items, weights

    def crate_rewards(self, crate: BazaarCrate) -> list[dict[str, Any]]:
        """List exactly the definitions that may be rolled from this box."""
        rarity_cap = self.rarity_rank(crate.bias) + 2
        items = [item for item in self.catalog
                 if item.get("type") in ("weapon", "armor", "ability")
                 and not item.get("fusion_only", False)
                 and self.rarity_rank(item.get("rarity", "common")) <= rarity_cap
                 and (not crate.element or item.get("stats", {}).get("element") == crate.element
                      or item.get("element") == crate.element)]
        if crate.id == "daily-crate":
            return random.Random(self.seed + self.daily_cycle * 7919).sample(items, min(12, len(items)))
        return items


def _validated_level(item: dict[str, Any]) -> int:
    level = item.get("level", 1)
    if type(level) is not int or level < 1:
        raise ValueError("Item level must be a positive integer")
    return level


def _validated_ultimate_tier(item: dict[str, Any]) -> int:
    tier = item.get("ultimate_tier", 1)
    if type(tier) is not int or not 1 <= tier <= 100:
        raise ValueError(
            "Ultimate rarity tier must be an integer from 1 to 100")
    return tier


def build_extended_catalog() -> list[dict[str, Any]]:
    """Return a broader starter catalog aligned with the final design."""
    catalog = [
        # Weapons
        {"id": "rifle-arc", "name": "Arc Rifle", "type": "weapon", "rarity": "common", "level": 1,
            "stats": {"bullet_type": "rapid_fire", "damage": 7, "cooldown": 0.15, "speed_modifier": 3.2, "piercing": 0, "element": "arcane"}},
        {"id": "lantern-sniper", "name": "Lantern Sniper", "type": "weapon", "rarity": "rare", "level": 1, "tags": ["sniper"], "stats": {
            "bullet_type": "heavy_shot", "damage": 22, "cooldown": 0.72, "speed_modifier": 2.6, "piercing": 4, "element": "light"}},
        {"id": "void-piercer", "name": "Void Piercer", "type": "weapon", "rarity": "epic", "level": 1,
            "stats": {"bullet_type": "heavy_shot", "damage": 35, "cooldown": 0.8, "speed_modifier": 2.0, "piercing": 8, "element": "shadow"}},
        {"id": "flame-blaster", "name": "Flame Blaster", "type": "weapon", "rarity": "uncommon", "level": 1, "stats": {"bullet_type": "shotgun",
                                                                                                                       "damage": 12, "cooldown": 0.9, "speed_modifier": 2.0, "pellets": 6, "pellet_range": 8, "element": "fire"}},
        {"id": "storm-spool", "name": "Storm Spool", "type": "weapon", "rarity": "epic", "level": 1,
            "stats": {"bullet_type": "rapid_fire", "damage": 26, "cooldown": 0.11, "speed_modifier": 4.2, "piercing": 2, "element": "frost"}},
        {"id": "homing-devastator", "name": "Homing Devastator", "type": "weapon", "rarity": "legendary", "level": 1, "stats": {"bullet_type": "homing",
                                                                                                                                "damage": 28, "cooldown": 0.25, "speed_modifier": 3.8, "piercing": 1, "homing_speed": 5.0, "element": "arcane"}},
        {"id": "ember-lance", "name": "Ember Lance", "type": "weapon", "rarity": "uncommon", "level": 1,
            "stats": {"bullet_type": "rapid_fire", "damage": 12, "cooldown": 0.18, "speed_modifier": 3.4, "piercing": 1, "element": "fire"}},
        {"id": "azar-saber", "name": "Azar Saber", "type": "weapon", "rarity": "rare", "level": 1,
            "stats": {"bullet_type": "heavy_shot", "damage": 22, "cooldown": 0.9, "speed_modifier": 2.4, "piercing": 3, "element": "shadow"}},

        # Abilities
        {"id": "ember-wand", "name": "Ember Wand", "type": "ability", "rarity": "uncommon", "level": 1, "stats": {"cooldown": 8,
                                                                                                                  "damage_pct": 12, "burn": 2, "cast_type": "projectile", "cast_damage": 22, "cast_speed_modifier": 2.8, "element": "fire"}},
        {"id": "warding-sigil", "name": "Warding Sigil", "type": "ability", "rarity": "rare", "level": 1,
            "stats": {"cooldown": 10, "shield": 8, "luck": 1, "cast_type": "heal", "heal_amount": 18}},
        {"id": "void-bloom", "name": "Void Bloom", "type": "ability", "rarity": "epic", "level": 1, "stats": {"cooldown": 12,
                                                                                                              "damage_pct": 18, "crit_chance": 4, "cast_type": "nova", "cast_damage": 32, "cast_radius": 0.6, "element": "shadow"}},
        {"id": "frost-lantern", "name": "Frost Lantern", "type": "ability", "rarity": "epic", "level": 1, "stats": {"cooldown": 9,
                                                                                                                    "damage_pct": 14, "luck": 3, "cast_type": "nova", "cast_damage": 26, "cast_radius": 0.45, "element": "frost"}},
        {"id": "sentinel-summon", "name": "Sentinel Summon", "type": "ability", "rarity": "legendary", "level": 1,
            "stats": {"cooldown": 30, "cast_type": "summon", "summon_count": 2, "summon_duration": 15, "summon_health": 50, "summon_damage": 15}},
        {"id": "turret-deploy", "name": "Turret Deploy", "type": "ability", "rarity": "epic", "level": 1, "stats": {"cooldown": 25,
                                                                                                                    "cast_type": "summon", "summon_count": 1, "summon_duration": 20, "summon_health": 30, "summon_damage": 12, "summon_fire_rate": 0.3}},
        {"id": "blink-step", "name": "Blink Step", "type": "ability", "rarity": "rare", "level": 1, "stats": {"cooldown": 12, "cast_type": "teleport",
                                                                                                              # "leave_trail" was set to "true" and i changed it to a 1/0 format.
                                                                                                              "teleport_distance": 8, "leave_trail": 1, "trail_element": "arcane"}},
        {"id": "glass-cascade", "name": "Glass Cascade", "type": "ability", "rarity": "rare", "level": 1, "stats": {"cooldown": 9,
                                                                                                                    "damage_pct": 11, "luck": 2, "cast_type": "projectile", "cast_damage": 20, "cast_speed_modifier": 2.5, "element": "light"}},

        # Armor
        {"id": "titan-plate", "name": "Titan Plate", "type": "armor",
            "rarity": "uncommon", "level": 1, "stats": {"defense": 5, "health": 20}},
        {"id": "starlit-hood", "name": "Starlit Hood", "type": "armor",
            "rarity": "rare", "level": 1, "stats": {"luck": 4, "defense": 3}},
        {"id": "ghost-boots", "name": "Ghost Boots", "type": "armor",
            "rarity": "epic", "level": 1, "stats": {"speed_pct": 16, "defense": 2}},
        {"id": "sentinel-heart", "name": "Sentinel Heart", "type": "armor",
            "rarity": "legendary", "level": 1, "stats": {"health": 60, "defense": 7}},
        {"id": "ember-gloves", "name": "Ember Gloves", "type": "armor",
            "rarity": "uncommon", "level": 1, "stats": {"damage_pct": 8, "speed_pct": 5}},
        {"id": "sunforge-plate", "name": "Sunforge Plate", "type": "armor",
            "rarity": "legendary", "level": 1, "stats": {"defense": 9, "health": 48}},

        # Relics/Misc
        {"id": "lucky-box", "name": "Lucky Box", "type": "relic",
            "rarity": "legendary", "level": 1, "stats": {"luck": 8, "damage_pct": 6}},
        {"id": "monkeys-paw", "name": "Monkey's Paw", "type": "relic", "rarity": "legendary",
            "level": 1, "stats": {"luck": 6, "damage_pct": 8, "defense": -2}},
        {"id": "chaos-core", "name": "Chaos Core", "type": "relic", "rarity": "legendary",
            "level": 1, "stats": {"luck": 12, "damage_pct": 12, "speed_pct": 8}},
        {"id": "ricochet-amulet", "name": "Ricochet Amulet", "type": "relic",
            "rarity": "rare", "level": 1, "stats": {"damage_pct": 10, "luck": 2}},
        {"id": "sentry-lattice", "name": "Sentry Lattice", "type": "relic",
            "rarity": "epic", "level": 1, "stats": {"luck": 5, "health": 18, "damage_pct": 7}},
        {"id": "inferno-core", "name": "Inferno Core", "type": "relic",
            "rarity": "legendary", "level": 1, "stats": {"damage_pct": 16, "luck": 4}},
        {"id": "shimmer-petal", "name": "Shimmer Petal", "type": "relic",
            "rarity": "rare", "level": 1, "stats": {"luck": 5, "speed_pct": 8}},
        {"id": "moon-sigil", "name": "Moon Sigil", "type": "relic", "rarity": "legendary",
            "level": 1, "stats": {"luck": 10, "damage_pct": 12, "speed_pct": 6}},
    ]
    # The asset is authoritative for active behavior; old shop copies must
    # never silently replace the scripts attached to those definitions.
    catalog = [item for item in catalog if item.get("type") != "ability"]
    catalog.extend(load_abilities())
    armor_definitions = load_armor()
    armor_by_id = {str(item.get("id")): item for item in armor_definitions}
    for item in catalog:
        definition = armor_by_id.get(str(item.get("id")))
        if definition is not None:
            for metadata_key in ("armor_set", "armor_slot"):
                if metadata_key in definition:
                    item[metadata_key] = definition[metadata_key]
    catalog.extend(item for item in armor_definitions if item.get("armor_set"))
    descriptions = {item['id']: item.get('description', '')
                    for item in (*load_weapons(), *armor_definitions, *load_relics())}
    for item in catalog:
        if not item.get('description'):
            parts = [f"{key.replace('_', ' ')}: {value}" for key, value in item.get('stats', {}).items()
                     if isinstance(value, (int, float)) and not isinstance(value, bool)]
            item['description'] = descriptions.get(
                item['id']) or f"Adds {', '.join(parts)} when equipped or combined."
    return catalog
