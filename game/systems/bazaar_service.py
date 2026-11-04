"""Validated, headlessly testable transactions for live Bazaar actions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from game.systems.bazaar import BazaarManager, RARITY_ORDER
from game.systems.currency import CurrencyWallet
from game.systems.inventory import Inventory, RARITY_COMBINATION_SLOTS
from game.systems.numbers import LargeNumber


class BazaarService:
    """Apply purchases, upgrades, and sales without partial transactions."""

    CURRENCY = "Gold"

    def __init__(self, manager: BazaarManager) -> None:
        self.manager = manager

    def buy_crate(
        self,
        crate_id: str,
        *,
        wallet: CurrencyWallet,
        inventory: Inventory,
        item_id: str,
        luck: float,
    ) -> dict[str, Any]:
        crate = next((entry for entry in self.manager.crates if entry.id == crate_id), None)
        if crate is None:
            raise ValueError("That crate is no longer available.")
        self._validate_purchase(wallet, inventory, item_id, crate.cost)
        reward = self.manager.roll_crate(crate, luck=luck)
        return self._add_purchase(reward, wallet, inventory, item_id, crate.cost)

    def buy_catalog_item(
        self,
        definition_id: str,
        *,
        wallet: CurrencyWallet,
        inventory: Inventory,
        item_id: str,
    ) -> dict[str, Any]:
        definition = next(
            (item for item in self.manager.catalog if str(item.get("id")) == definition_id),
            None,
        )
        if definition is None:
            raise ValueError("That market item is no longer available.")
        cost = self.manager.catalog_price(definition)
        self._validate_purchase(wallet, inventory, item_id, cost)
        return self._add_purchase(definition, wallet, inventory, item_id, cost)

    def upgrade_rarity(
        self,
        item_id: str,
        *,
        wallet: CurrencyWallet,
        inventory: Inventory,
        luck: float,
    ) -> bool:
        item = self._owned_item(inventory, item_id)
        if self.manager.rarity_rank(item.get("rarity", "common")) >= len(RARITY_ORDER) - 1:
            tier = item.get("ultimate_tier", 1)
            if type(tier) is not int or not 1 <= tier <= 100:
                raise ValueError("Ultimate rarity tier must be an integer from 1 to 100")
            if tier == 100:
                raise ValueError("Ultimate 100 items cannot be rarity-upgraded further.")
        cost = self.manager.rarity_upgrade_cost(item)
        self._require_funds(wallet, cost)
        staged = deepcopy(item)
        self.manager.upgrade_rarity(staged, luck=luck, currency_cost=cost)
        self._spend(wallet, cost)
        original_rarity = item.get("rarity")
        original_tier = item.get("ultimate_tier", 1) if original_rarity == "ultimate" else 0
        item.clear()
        item.update(staged)
        current_tier = item.get("ultimate_tier", 1) if item.get("rarity") == "ultimate" else 0
        return (
            item.get("rarity") != original_rarity
            or current_tier != original_tier
        )

    def upgrade_level(
        self,
        item_id: str,
        *,
        wallet: CurrencyWallet,
        inventory: Inventory,
    ) -> None:
        item = self._owned_item(inventory, item_id)
        cost = self.manager.level_upgrade_cost(item)
        self._require_funds(wallet, cost)
        staged = deepcopy(item)
        self.manager.upgrade_level(staged, currency_cost=cost)
        self._spend(wallet, cost)
        item.clear()
        item.update(staged)

    def sell_item(
        self,
        item_id: str,
        *,
        wallet: CurrencyWallet,
        inventory: Inventory,
        trader_bonus: float = 0.0,
    ) -> int:
        item = self._owned_item(inventory, item_id)
        if any(item_id in slots for slots in inventory.active_slots.values()):
            raise ValueError("Unequip this item before selling it.")
        if inventory.is_combination_supplement(item_id) or any(
            value is not None for value in item.get("combinations", [])
        ):
            raise ValueError("Remove this item from its combination before selling it.")
        value = self.manager.sell_value(item, trader_bonus=trader_bonus)
        inventory.items.remove(item)
        inventory._refresh_statuses()
        wallet.add(self.CURRENCY, LargeNumber(value))
        return value

    def _validate_purchase(
        self,
        wallet: CurrencyWallet,
        inventory: Inventory,
        item_id: str,
        cost: int,
    ) -> None:
        if len(inventory.items) >= inventory.CAPACITY:
            raise ValueError("Inventory is full; sell an item before buying.")
        if not item_id or any(str(item.get("id")) == item_id for item in inventory.items):
            raise ValueError("Could not create a unique ID for the purchased item.")
        self._require_funds(wallet, cost)

    def _add_purchase(
        self,
        definition: dict[str, Any],
        wallet: CurrencyWallet,
        inventory: Inventory,
        item_id: str,
        cost: int,
    ) -> dict[str, Any]:
        item = deepcopy(definition)
        item["id"] = item_id
        rarity = str(item.get("rarity", "common")).lower()
        if rarity not in RARITY_COMBINATION_SLOTS:
            raise ValueError(f"Unsupported purchased item rarity: {rarity}")
        item.setdefault("combinations", [None] * RARITY_COMBINATION_SLOTS[rarity])
        item.setdefault("status", "normal")
        self._spend(wallet, cost)
        original_items = deepcopy(inventory.items)
        original_slots = deepcopy(inventory.active_slots)
        try:
            inventory.add(item)
        except (OverflowError, TypeError, ValueError):
            inventory.items = original_items
            inventory.active_slots = original_slots
            wallet.add(self.CURRENCY, LargeNumber(cost))
            raise
        return item

    def _owned_item(self, inventory: Inventory, item_id: str) -> dict[str, Any]:
        try:
            return inventory.get(item_id)
        except KeyError as exc:
            raise ValueError("That item is no longer in your inventory.") from exc

    def _require_funds(self, wallet: CurrencyWallet, cost: int) -> None:
        if wallet.get(self.CURRENCY) < LargeNumber(cost):
            raise ValueError(f"Not enough Gold; this action costs {cost}.")

    def _spend(self, wallet: CurrencyWallet, cost: int) -> None:
        if not wallet.spend(self.CURRENCY, LargeNumber(cost)):
            raise ValueError(f"Not enough Gold; this action costs {cost}.")
