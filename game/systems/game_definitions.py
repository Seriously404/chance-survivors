"""JSON asset loader for quests, enemies, and currencies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"


def load_json_asset(filename: str) -> Any:
    """Load a JSON asset from the assets directory."""
    filepath = ASSETS_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Asset file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_quests() -> list[dict[str, Any]]:
    """Load all quest definitions from quests.json."""
    data = load_json_asset("quests.json")
    return data.get("quests", [])


def load_enemies() -> list[dict[str, Any]]:
    """Load all enemy definitions from enemies.json."""
    data = load_json_asset("enemies.json")
    return data.get("enemies", [])


def load_currencies() -> list[dict[str, Any]]:
    """Load all currency definitions from currencies.json."""
    data = load_json_asset("currencies.json")
    return data.get("currencies", [])


def load_all_game_definitions() -> dict[str, list[dict[str, Any]]]:
    """Load all game definitions from JSON files."""
    return {
        "quests": load_quests(),
        "enemies": load_enemies(),
        "currencies": load_currencies(),
    }
