"""Versioned, headless serialization for a single player's run state."""

from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from game.systems.inventory import Inventory
from game.systems.scoring import RunScore
from game.utils.large_number import LargeNumber


SAVE_VERSION = 1
MAX_SAVE_BYTES = 5 * 1024 * 1024
_LARGE_NUMBER_MARKER = "__large_number__"


def _encode(value: Any) -> Any:
    if isinstance(value, LargeNumber):
        return {_LARGE_NUMBER_MARKER: value.to_dict()}
    if isinstance(value, dict):
        if _LARGE_NUMBER_MARKER in value:
            raise ValueError(f"Reserved save-data key: {_LARGE_NUMBER_MARKER}")
        return {str(key): _encode(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError(f"Unsupported save-data value: {type(value).__name__}")


def _decode(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {_LARGE_NUMBER_MARKER}:
            return LargeNumber.from_dict(value[_LARGE_NUMBER_MARKER])
        return {key: _decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode(item) for item in value]
    return value


class RunSave:
    """A validated snapshot independent of live entities or Pygame objects."""

    def __init__(
        self,
        *,
        player_name: str,
        elapsed_seconds: float,
        score: Mapping[str, Any],
        player: Mapping[str, Any],
        inventory: Mapping[str, Any],
        currencies: Mapping[str, Any],
        quests: Mapping[str, Any] | None = None,
    ) -> None:
        self.player_name = _validate_player_name(player_name)
        if (isinstance(elapsed_seconds, bool)
                or not isinstance(elapsed_seconds, (int, float))
                or not math.isfinite(elapsed_seconds) or elapsed_seconds < 0):
            raise ValueError("Elapsed gameplay time must be finite and non-negative")
        self.elapsed_seconds = float(elapsed_seconds)
        self.score = RunScore.from_dict(dict(score))
        self.player = deepcopy(dict(player))
        self.inventory = deepcopy(dict(inventory))
        self.currencies = deepcopy(dict(currencies))
        self.quests = deepcopy(dict(quests)) if quests is not None else None
        self._validate_player()
        self._validate_inventory()
        self._validate_currencies()
        _encode(self.player)
        _encode(self.inventory)
        _encode(self.currencies)
        if self.quests is not None:
            _encode(self.quests)

    @classmethod
    def capture(
        cls,
        *,
        player_name: str,
        elapsed_seconds: float,
        score: RunScore,
        player: Mapping[str, Any],
        inventory: Inventory,
        currencies: Mapping[str, Any],
        quests: Mapping[str, Any] | None = None,
    ) -> RunSave:
        """Copy current pure-data state into a detached snapshot."""
        inventory_state = {
            "items": deepcopy(inventory.items),
            "active_slots": deepcopy(inventory.active_slots),
        }
        return cls(
            player_name=player_name,
            elapsed_seconds=elapsed_seconds,
            score=score.to_dict(),
            player=player,
            inventory=inventory_state,
            currencies=currencies,
            quests=quests,
        )

    def _validate_player(self) -> None:
        if type(self.player.get("level")) is not int or self.player["level"] < 1:
            raise ValueError("Player save needs a positive integer level")
        health = self.player.get("health")
        max_health = self.player.get("max_health")
        if not (type(health) is int or isinstance(health, LargeNumber)) or not (
            type(max_health) is int or isinstance(max_health, LargeNumber)
        ):
            raise ValueError("Player save needs numeric health and max_health")
        if health < 0 or max_health < 0 or health > max_health:
            raise ValueError("Player health must be between zero and max_health")

    def _validate_inventory(self) -> None:
        items = self.inventory.get("items")
        active = self.inventory.get("active_slots")
        if not isinstance(items, list) or not isinstance(active, dict):
            raise ValueError("Inventory save needs items and active_slots")
        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not item["id"]
            or not isinstance(item.get("type"), str)
            for item in items
        ):
            raise ValueError("Every inventory item needs a stable string id and type")
        try:
            restored = Inventory(deepcopy(items))
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Malformed inventory items: {exc}") from exc
        required = Inventory.SLOT_COUNTS
        if set(active) != set(required):
            raise ValueError("Inventory save has invalid equipment categories")
        assigned: set[str] = set()
        for category, count in required.items():
            slot_ids = active[category]
            if not isinstance(slot_ids, list) or len(slot_ids) != count:
                raise ValueError(f"Inventory save needs {count} {category} slots")
            for index, item_id in enumerate(slot_ids):
                if item_id is None:
                    continue
                if not isinstance(item_id, str) or item_id in assigned:
                    raise ValueError("An item cannot occupy multiple equipment slots")
                try:
                    restored.equip(item_id, category, index)
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid equipped item in {category} slot {index}") from exc
                assigned.add(item_id)

        known_ids = {str(item["id"]) for item in restored.items}
        by_id = {str(item["id"]): item for item in restored.items}
        supplements: set[str] = set()
        for item in restored.items:
            combinations = item.get("combinations", [])
            if not isinstance(combinations, list):
                raise ValueError("Item combinations must be a list")
            for supplement_id in combinations:
                if supplement_id is None:
                    continue
                if not isinstance(supplement_id, str) or supplement_id not in known_ids:
                    raise ValueError("Combination references an unknown inventory item")
                if supplement_id == str(item["id"]) or supplement_id in supplements:
                    raise ValueError("Invalid repeated or self-referential combination")
                if any(value is not None for value in by_id[supplement_id].get("combinations", [])):
                    raise ValueError("A combination supplement cannot also be a base item")
                supplements.add(supplement_id)
        if assigned.intersection(supplements):
            raise ValueError("An equipped item cannot also be a combination supplement")

    def _validate_currencies(self) -> None:
        if not all(isinstance(name, str) and name for name in self.currencies):
            raise ValueError("Currency identifiers must be non-empty strings")
        for amount in self.currencies.values():
            if not (type(amount) is int or isinstance(amount, LargeNumber)) or amount < 0:
                raise ValueError("Currency amounts must be non-negative integers or LargeNumbers")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SAVE_VERSION,
            "player_name": self.player_name,
            "elapsed_seconds": self.elapsed_seconds,
            "score": deepcopy(dict(self.score.to_dict())),
            "player": _encode(self.player),
            "inventory": _encode(self.inventory),
            "currencies": _encode(self.currencies),
            "quests": _encode(self.quests),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), allow_nan=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> RunSave:
        if not isinstance(raw, Mapping) or type(raw.get("version")) is not int or raw.get("version") != SAVE_VERSION:
            raise ValueError("Unsupported run-save version")
        player = _decode(raw.get("player"))
        inventory = _decode(raw.get("inventory"))
        currencies = _decode(raw.get("currencies"))
        quests = _decode(raw.get("quests"))
        if not all(isinstance(value, dict) for value in (player, inventory, currencies)):
            raise ValueError("Malformed run-save payload")
        if quests is not None and not isinstance(quests, dict):
            raise ValueError("Quest save must be an object or null")
        score = raw.get("score")
        if not isinstance(score, Mapping):
            raise ValueError("Malformed score save")
        return cls(
            player_name=raw.get("player_name"),
            elapsed_seconds=raw.get("elapsed_seconds"),
            score=score,
            player=player,
            inventory=inventory,
            currencies=currencies,
            quests=quests,
        )

    @classmethod
    def from_json(cls, value: str) -> RunSave:
        try:
            raw = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid run-save JSON") from exc
        return cls.from_dict(raw)

    def save(self, path: Path) -> None:
        """Atomically replace a save file after writing the complete JSON data."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = self.to_json()
        if len(encoded.encode("utf-8")) > MAX_SAVE_BYTES:
            raise ValueError("Run save exceeds the configured size limit")
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=path.parent,
                prefix=f".{path.name}.", suffix=".tmp", delete=False,
            ) as file:
                temporary_path = Path(file.name)
                file.write(encoded)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @classmethod
    def load(cls, path: Path) -> RunSave:
        path = Path(path)
        try:
            if path.stat().st_size > MAX_SAVE_BYTES:
                raise ValueError("Run save exceeds the configured size limit")
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"Could not read run save at {path}: {exc}") from exc
        return cls.from_json(raw)

    def restore_score(self) -> RunScore:
        return RunScore.from_dict(dict(self.score.to_dict()))

    def restore_inventory(self) -> Inventory:
        inventory = Inventory(deepcopy(self.inventory["items"]))
        for category, slot_ids in self.inventory["active_slots"].items():
            for index, item_id in enumerate(slot_ids):
                if item_id is not None:
                    inventory.equip(item_id, category, index)
        return inventory


def _validate_player_name(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Player name must be a string")
    name = value.strip()
    if not name or len(name) > 40:
        raise ValueError("Player name must contain 1 to 40 characters")
    return name
