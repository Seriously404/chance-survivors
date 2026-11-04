"""Versioned, headless persistence for resumable gameplay runs."""

from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

from game.systems.inventory import Inventory
from game.systems.numbers import LargeNumber

SAVE_VERSION = 1
MAX_SAVE_BYTES = 5 * 1024 * 1024
DEFAULT_SAVE_PATH = Path(__file__).resolve().parents[2] / "data" / "run_save.json"


def configured_save_path() -> Path:
    """Return the override path when set, otherwise the project-local default."""
    override = os.environ.get("CHANCE_SURVIVORS_RUN_SAVE")
    return Path(override).expanduser() if override else DEFAULT_SAVE_PATH


def _json_value(value: Any) -> Any:
    if isinstance(value, LargeNumber):
        return {"__large_number__": str(value.to_decimal())}
    if isinstance(value, dict):
        if set(value) == {"__large_number__"}:
            raise ValueError("Reserved run-save key: __large_number__")
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError(f"Unsupported run-save value: {type(value).__name__}")


def _decode_value(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"__large_number__"}:
            return LargeNumber(value["__large_number__"])
        return {key: _decode_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode_value(item) for item in value]
    return value


class RunSave:
    """Detached snapshot of state needed to resume a run."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = deepcopy(state)
        self._validate()

    @classmethod
    def capture(
        cls,
        *,
        player_name: str,
        elapsed_seconds: float,
        score: LargeNumber,
        player_health: int,
        player_max_health: int,
        progression_level: int,
        current_exp: LargeNumber,
        total_exp: LargeNumber,
        inventory: Inventory,
        currencies: dict[str, LargeNumber],
        quest_state: dict[str, Any],
        threat_level: int,
        spawn_counter: int,
        bazaar_seed: int = 0,
        bazaar_refresh_count: int = 0,
        bazaar_last_manual_refresh_cycle: int = -1,
    ) -> RunSave:
        return cls({
            "version": SAVE_VERSION,
            "player_name": player_name.strip(),
            "elapsed_seconds": elapsed_seconds,
            "score": str(score.to_decimal()),
            "player": {
                "health": player_health,
                "max_health": player_max_health,
            },
            "progression": {
                "level": progression_level,
                "current_exp": str(current_exp.to_decimal()),
                "total_exp": str(total_exp.to_decimal()),
            },
            "inventory": {
                "items": deepcopy(inventory.items),
                "active_slots": deepcopy(inventory.active_slots),
            },
            "currencies": {
                key: str(value.to_decimal()) for key, value in currencies.items()
            },
            "quests": deepcopy(quest_state),
            "threat_level": threat_level,
            "spawn_counter": spawn_counter,
            "bazaar_seed": bazaar_seed,
            "bazaar_refresh_count": bazaar_refresh_count,
            "bazaar_last_manual_refresh_cycle": bazaar_last_manual_refresh_cycle,
        })

    def _validate(self) -> None:
        state = self.state
        if (not isinstance(state, dict) or type(state.get("version")) is not int
                or state.get("version") != SAVE_VERSION):
            raise ValueError("Unsupported run-save version")
        name = state.get("player_name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 32:
            raise ValueError("Run save needs a player name of 1 to 32 characters")
        elapsed = state.get("elapsed_seconds")
        if (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
                or not math.isfinite(elapsed) or elapsed < 0):
            raise ValueError("Elapsed gameplay time must be finite and non-negative")
        state["elapsed_seconds"] = float(elapsed)
        _nonnegative_number(state.get("score"), "score")
        player = state.get("player")
        progression = state.get("progression")
        if not isinstance(player, dict) or not isinstance(progression, dict):
            raise ValueError("Run save has invalid player or progression state")
        max_health = player.get("max_health")
        health = player.get("health")
        if (type(max_health) is not int or type(health) is not int
                or max_health < 1 or health < 0 or health > max_health):
            raise ValueError("Run save has invalid player health")
        if type(progression.get("level")) is not int or progression["level"] < 1:
            raise ValueError("Run save needs a positive progression level")
        _nonnegative_number(progression.get("current_exp"), "current_exp")
        _nonnegative_number(progression.get("total_exp"), "total_exp")
        inventory_state = state.get("inventory")
        if not isinstance(inventory_state, dict) or not isinstance(
            inventory_state.get("items"), list
        ):
            raise ValueError("Run save has invalid inventory")
        try:
            inventory = Inventory(deepcopy(inventory_state["items"]))
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Run save has invalid inventory items: {exc}") from exc
        active_slots = inventory_state.get("active_slots")
        if not isinstance(active_slots, dict) or set(active_slots) != set(inventory.active_slots):
            raise ValueError("Run save has invalid equipment slots")
        equipped_ids: set[str] = set()
        for kind, slot_ids in active_slots.items():
            if not isinstance(slot_ids, list) or len(slot_ids) != len(inventory.active_slots[kind]):
                raise ValueError(f"Run save has invalid {kind} equipment slots")
            for index, item_id in enumerate(slot_ids):
                if item_id is not None:
                    if not isinstance(item_id, str) or item_id in equipped_ids:
                        raise ValueError("An item cannot occupy multiple equipment slots")
                    try:
                        inventory.equip(item_id, kind, index)
                    except (IndexError, KeyError, TypeError, ValueError) as exc:
                        raise ValueError(f"Run save has invalid {kind} equipment") from exc
                    equipped_ids.add(item_id)
        currencies = state.get("currencies")
        if not isinstance(currencies, dict):
            raise ValueError("Run save has invalid currencies")
        for name, amount in currencies.items():
            if not isinstance(name, str) or not name:
                raise ValueError("Run save currency names must be non-empty strings")
            _nonnegative_number(amount, f"currency {name}")
        if not isinstance(state.get("quests"), dict):
            raise ValueError("Run save has invalid quest state")
        threat_level = state.get("threat_level")
        if type(threat_level) is not int or not 0 <= threat_level <= 20:
            raise ValueError("Run save has invalid threat level")
        if type(state.get("spawn_counter")) is not int or state["spawn_counter"] < 0:
            raise ValueError("Run save has invalid item counter")
        for field in ("bazaar_seed", "bazaar_refresh_count"):
            value = state.setdefault(field, 0)
            if type(value) is not int or value < 0:
                raise ValueError(f"Run save has invalid {field}")
        if state["bazaar_seed"] > 2**64 - 1:
            raise ValueError("Run save has invalid bazaar_seed")
        refresh_cycle = state.get("bazaar_last_manual_refresh_cycle", -1)
        current_cycle = int(elapsed // 300)
        if (
            type(refresh_cycle) is not int
            or refresh_cycle < -1
            or refresh_cycle > current_cycle
        ):
            raise ValueError("Run save has invalid bazaar_last_manual_refresh_cycle")
        state["bazaar_seed"] = state.get("bazaar_seed", 0)
        state["bazaar_refresh_count"] = state.get("bazaar_refresh_count", 0)
        state["bazaar_last_manual_refresh_cycle"] = refresh_cycle
        _json_value(state)

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self.state)

    def restore_inventory(self) -> Inventory:
        """Rebuild the pure inventory model, including active equipment slots."""
        inventory_state = self.state["inventory"]
        inventory = Inventory(deepcopy(inventory_state["items"]))
        for kind, slot_ids in inventory_state["active_slots"].items():
            for index, item_id in enumerate(slot_ids):
                if item_id is not None:
                    inventory.equip(item_id, kind, index)
        return inventory

    @classmethod
    def from_dict(cls, state: dict[str, Any]) -> RunSave:
        if not isinstance(state, dict):
            raise ValueError("Run-save payload must be an object")
        decoded = _decode_value(state)
        return cls(decoded)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), allow_nan=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> RunSave:
        try:
            state = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid run-save JSON") from exc
        return cls.from_dict(state)

    def write(self, path: Path = DEFAULT_SAVE_PATH) -> None:
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
    def read(cls, path: Path = DEFAULT_SAVE_PATH) -> RunSave:
        path = Path(path)
        try:
            if path.stat().st_size > MAX_SAVE_BYTES:
                raise ValueError("Run save exceeds the configured size limit")
            contents = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"Could not read run save at {path}: {exc}") from exc
        return cls.from_json(contents)


def _nonnegative_number(value: Any, label: str) -> LargeNumber:
    if isinstance(value, bool):
        raise ValueError(f"Run save has invalid {label}")
    try:
        number = LargeNumber(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Run save has invalid {label}") from exc
    if number < 0:
        raise ValueError(f"Run save {label} must be non-negative")
    return number
