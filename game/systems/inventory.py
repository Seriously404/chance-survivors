"""Pure data model for the 200-slot inventory and item relationships."""

from __future__ import annotations

from typing import Any

RARITY_COMBINATION_SLOTS = {
    "common": 1, "uncommon": 2, "rare": 3, "epic": 3,
    "legendary": 4, "mythical": 4, "ultimate": 5,
}
ARMOR_EQUIPMENT_SLOTS = ("boots", "pants", "chestplate", "headpiece", "accessory")


def _item(item_id: str, name: str, kind: str, rarity: str, level: int,
          stats: dict[str, int | float | str]) -> dict[str, Any]:
    rarity = rarity.lower()
    if rarity not in RARITY_COMBINATION_SLOTS:
        raise ValueError(f"Unsupported rarity: {rarity}")
    return {"id": item_id, "name": name, "type": kind, "rarity": rarity,
            "level": level, "stats": stats,
            "combinations": [None] * RARITY_COMBINATION_SLOTS[rarity],
            "status": "normal"}


def create_test_items() -> list[dict[str, Any]]:
    """Backward-compatible name for the current starter item catalog."""
    from game.systems.items import create_item_catalog
    return create_item_catalog()


class Inventory:
    """Inventory items are dict records suitable for direct UI inspection.

    ``status`` values are ``normal``, ``supplement``, ``combination_base`` or
    ``active``. Active status has display priority over combination status.
    """

    CAPACITY = 200
    SLOT_COUNTS = {"armor": 5, "weapons": 2, "abilities": 10}

    def __init__(self, items: list[dict[str, Any]] | None = None) -> None:
        self.items: list[dict[str, Any]] = list(items or [])
        if len(self.items) > self.CAPACITY:
            raise ValueError("Inventory exceeds 200 slots")
        if any(not isinstance(item, dict) for item in self.items):
            raise ValueError("Inventory entries must be item objects")
        item_ids = [item.get("id") for item in self.items]
        if any(not isinstance(item_id, str) or not item_id for item_id in item_ids):
            raise ValueError("Inventory items need non-empty string ids")
        if len(set(item_ids)) != len(self.items):
            raise ValueError("Inventory item IDs must be unique")
        self._validate_combination_records(self.items)
        self.active_slots: dict[str, list[str | None]] = {
            name: [None] * count for name, count in self.SLOT_COUNTS.items()
        }
        self._refresh_statuses()

    def get(self, item_id: str) -> dict[str, Any]:
        for item in self.items:
            if item["id"] == item_id:
                return item
        raise KeyError(item_id)

    def add(self, item: dict[str, Any]) -> int:
        if len(self.items) >= self.CAPACITY:
            raise OverflowError("Inventory is full")
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError("Inventory items need non-empty string ids")
        if any(existing["id"] == item["id"] for existing in self.items):
            raise ValueError(f"Duplicate inventory item ID: {item['id']}")
        proposed_items = self.items + [item]
        supplement_ids = self._validate_combination_records(proposed_items)
        active_ids = {item_id for slots in self.active_slots.values() for item_id in slots if item_id is not None}
        if active_ids.intersection(supplement_ids):
            raise ValueError("An actively equipped item cannot be a combination supplement")
        self.items.append(item)
        self._refresh_statuses()
        return len(self.items) - 1

    def is_combination_supplement(self, item_id: str) -> bool:
        return any(item_id in item["combinations"] for item in self.items)

    @staticmethod
    def _validate_combination_records(items: list[dict[str, Any]]) -> set[str]:
        """Validate the complete base/supplement graph without changing it."""
        if any(not isinstance(item, dict) for item in items):
            raise ValueError("Inventory entries must be item objects")
        if any(not isinstance(item.get("id"), str) or not item["id"] for item in items):
            raise ValueError("Items need non-empty ids for combinations")
        by_id = {item["id"]: item for item in items}
        owners: dict[str, str] = {}
        base_ids: set[str] = set()
        for base in items:
            base_id = base["id"]
            base_type = base.get("type")
            slots = base.get("combinations")
            if not isinstance(base_type, str) or not base_type:
                raise ValueError(f"Item {base_id!r} needs a non-empty type for combinations")
            if not isinstance(slots, list):
                raise ValueError(f"Item {base_id!r} combination slots must be a list")
            for supplement_id in slots:
                if supplement_id is None:
                    continue
                if not isinstance(supplement_id, str) or supplement_id not in by_id:
                    raise ValueError(f"Item {base_id!r} references an unknown combination supplement")
                if supplement_id == base_id:
                    raise ValueError("An item cannot be combined with itself")
                if supplement_id in owners:
                    raise ValueError("A combination supplement can belong to only one base item")
                supplement_type = by_id[supplement_id].get("type")
                if not isinstance(supplement_type, str):
                    raise ValueError(f"Item {supplement_id!r} has no valid type")
                if (base_type == "armor") != (supplement_type == "armor"):
                    raise ValueError("Armor can only be combined with armor; non-armor with non-armor")
                owners[supplement_id] = base_id
                base_ids.add(base_id)

        if base_ids.intersection(owners):
            raise ValueError("An item cannot be both a combination base and a supplement")
        return set(owners)

    def assign_combination(self, base_id: str, combo_index: int,
                           supplement_id: str | None) -> None:
        base = self.get(base_id)
        combos = base["combinations"]
        if type(combo_index) is not int:
            raise IndexError("Combination slot index must be an integer")
        if not 0 <= combo_index < len(combos):
            raise IndexError("Combination slot is outside this item's rarity capacity")

        # Reject pre-existing corrupt graphs and compute a candidate ownership
        # graph before changing any item slots.
        self._validate_combination_records(self.items)
        proposed_slots = {item["id"]: list(item["combinations"]) for item in self.items}
        if supplement_id is not None:
            if not isinstance(supplement_id, str):
                raise ValueError("Combination supplement id must be a string or None")
            supplement = self.get(supplement_id)
            if supplement_id == base_id:
                raise ValueError("An item cannot be combined with itself")
            if any(supplement_id in slots for slots in self.active_slots.values()):
                raise ValueError("An actively equipped item cannot become a combination supplement")
            if any(value is not None for value in supplement["combinations"]):
                raise ValueError("A combination base cannot also be used as a supplement")
            if (base["type"] == "armor") != (supplement["type"] == "armor"):
                raise ValueError("Armor can only be combined with armor; non-armor with non-armor")

            old_base_id = next(
                (owner_id for owner_id, slots in proposed_slots.items() if supplement_id in slots),
                None,
            )
            if old_base_id is not None:
                if old_base_id != base_id:
                    raise ValueError("An item already used in another combination cannot be moved")
                old_index = proposed_slots[base_id].index(supplement_id)
                if old_index != combo_index:
                    displaced = proposed_slots[base_id][combo_index]
                    proposed_slots[base_id][combo_index] = supplement_id
                    proposed_slots[base_id][old_index] = displaced
            else:
                proposed_slots[base_id][combo_index] = supplement_id
        else:
            proposed_slots[base_id][combo_index] = None

        proposed_items = [
            {**item, "combinations": proposed_slots[item["id"]]}
            for item in self.items
        ]
        supplement_ids = self._validate_combination_records(proposed_items)
        active_ids = {item_id for slots in self.active_slots.values() for item_id in slots if item_id is not None}
        if active_ids.intersection(supplement_ids):
            raise ValueError("An actively equipped item cannot be a combination supplement")

        for item in self.items:
            item["combinations"] = proposed_slots[item["id"]]
        self._refresh_statuses()

    def equip(self, item_id: str, slot_kind: str, slot_index: int) -> None:
        item = self.get(item_id)
        if slot_kind not in self.active_slots:
            raise ValueError(f"Unknown equipment category: {slot_kind}")
        expected_type = {"armor": "armor", "weapons": "weapon", "abilities": "ability"}[slot_kind]
        if item["type"] != expected_type:
            raise ValueError(f"{item['type']} item cannot be placed in {slot_kind} slot")
        slots = self.active_slots[slot_kind]
        if not 0 <= slot_index < len(slots):
            raise IndexError("Equipment slot out of range")
        if slot_kind == "armor":
            if item.get("armor_set") is not None and "armor_slot" not in item:
                raise ValueError("Armor set pieces must define an equipment slot")
            if "armor_slot" in item:
                armor_slot = item["armor_slot"]
                if not isinstance(armor_slot, str) or armor_slot not in ARMOR_EQUIPMENT_SLOTS:
                    raise ValueError(f"Unsupported armor slot: {armor_slot}")
                if armor_slot != ARMOR_EQUIPMENT_SLOTS[slot_index]:
                    raise ValueError(
                        f"{item.get('name', 'Armor')} belongs in the {armor_slot} slot"
                    )
        if self.is_combination_supplement(item_id):
            raise ValueError("Combination supplements cannot be actively equipped")
        # Moving an item between slots of the same category clears its old slot.
        for index, existing_id in enumerate(slots):
            if existing_id == item_id:
                slots[index] = None
        slots[slot_index] = item_id
        self._refresh_statuses()

    def unequip(self, slot_kind: str, slot_index: int) -> None:
        """Return an active item to an ordinary inventory slot."""
        if slot_kind not in self.active_slots:
            raise ValueError(f"Unknown equipment category: {slot_kind}")
        slots = self.active_slots[slot_kind]
        if not 0 <= slot_index < len(slots):
            raise IndexError("Equipment slot out of range")
        slots[slot_index] = None
        self._refresh_statuses()

    def _refresh_statuses(self) -> None:
        active_ids = {item_id for slots in self.active_slots.values()
                      for item_id in slots if item_id is not None}
        supplement_ids = {item_id for item in self.items
                          for item_id in item["combinations"] if item_id is not None}
        base_ids = {item["id"] for item in self.items
                    if any(value is not None for value in item["combinations"])}
        for item in self.items:
            item["status"] = ("active" if item["id"] in active_ids else
                              "supplement" if item["id"] in supplement_ids else
                              "combination_base" if item["id"] in base_ids else "normal")

    def fuse_items(self, source_item_ids: list[str], *, recipe_id: str | None = None,
                   fusion_manager: Any | None = None) -> dict[str, Any]:
        """Create a permanent fused item from two compatible sources."""
        if len(source_item_ids) < 2:
            raise ValueError("Fusion requires at least two items")
        normalized = [str(item_id) for item_id in source_item_ids]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Duplicate item IDs are not valid for a fusion")
        source_items = [self.get(item_id) for item_id in normalized]
        active_ids = {
            active_id
            for slot_ids in self.active_slots.values()
            for active_id in slot_ids
            if active_id is not None
        }
        if any(item.get("id") in active_ids for item in source_items):
            raise ValueError("Equipped items cannot be fused")
        if any(
            self.is_combination_supplement(str(item.get("id")))
            or any(value is not None for value in item.get("combinations", []))
            for item in source_items
        ):
            raise ValueError("Remove fusion sources from combinations before fusing them")
        if fusion_manager is None:
            from game.systems.fusion import FusionManager
            fusion_manager = FusionManager()
        if recipe_id is not None:
            result = fusion_manager.build_fusion(source_items, recipe_id=recipe_id)
        else:
            result = fusion_manager.build_fusion(source_items)
        source_id_set = set(normalized)
        remaining_items = [
            item for item in self.items
            if str(item.get("id")) not in source_id_set
        ]
        if any(str(item.get("id")) == str(result.get("id")) for item in remaining_items):
            raise ValueError("Fusion result ID already exists in this inventory")
        self.items = [*remaining_items, result]
        self._refresh_statuses()
        return result
