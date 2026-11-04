<<<<<<< HEAD
"""Versioned, headless persistence for resumable gameplay runs."""
=======
"""Versioned, headless serialization for a single player's run state."""
>>>>>>> birch/projectile-collision-effects

from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile
<<<<<<< HEAD
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
=======
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
>>>>>>> birch/projectile-collision-effects
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
<<<<<<< HEAD
    raise ValueError(f"Unsupported run-save value: {type(value).__name__}")


def _decode_value(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"__large_number__"}:
            return LargeNumber(value["__large_number__"])
        return {key: _decode_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode_value(item) for item in value]
=======
    raise ValueError(f"Unsupported save-data value: {type(value).__name__}")


def _decode(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {_LARGE_NUMBER_MARKER}:
            return LargeNumber.from_dict(value[_LARGE_NUMBER_MARKER])
        return {key: _decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode(item) for item in value]
>>>>>>> birch/projectile-collision-effects
    return value


class RunSave:
<<<<<<< HEAD
    """Detached snapshot of state needed to resume a run."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = deepcopy(state)
        self._validate()
=======
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
>>>>>>> birch/projectile-collision-effects

    @classmethod
    def capture(
        cls,
        *,
        player_name: str,
        elapsed_seconds: float,
<<<<<<< HEAD
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
=======
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
>>>>>>> birch/projectile-collision-effects

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), allow_nan=False, sort_keys=True, separators=(",", ":"))

    @classmethod
<<<<<<< HEAD
    def from_json(cls, value: str) -> RunSave:
        try:
            state = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid run-save JSON") from exc
        return cls.from_dict(state)

    def write(self, path: Path = DEFAULT_SAVE_PATH) -> None:
=======
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
>>>>>>> birch/projectile-collision-effects
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
<<<<<<< HEAD
    def read(cls, path: Path = DEFAULT_SAVE_PATH) -> RunSave:
=======
    def load(cls, path: Path) -> RunSave:
>>>>>>> birch/projectile-collision-effects
        path = Path(path)
        try:
            if path.stat().st_size > MAX_SAVE_BYTES:
                raise ValueError("Run save exceeds the configured size limit")
<<<<<<< HEAD
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
=======
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
>>>>>>> birch/projectile-collision-effects
