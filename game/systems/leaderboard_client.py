"""HTTP client for explicit completed-run leaderboard submissions."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from game.systems.numbers import LargeNumber
from game.utils.large_number import LargeNumber as CombatNumber

DEFAULT_LEADERBOARD_URL = "http://127.0.0.1:8000"
MAX_RESPONSE_BYTES = 64 * 1024


def _json_value(value: Any) -> Any:
    if isinstance(value, CombatNumber):
        # Preserve all digits and the exponent, including values outside float range.
        return f"{'-' if value.sign < 0 else ''}{value.significand}e{value.exponent}"
    if isinstance(value, LargeNumber):
        return str(value.to_decimal())
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported run data value: {type(value).__name__}")


def build_run_submission(
    *,
    name: str,
    score: LargeNumber,
    runtime_seconds: float,
    level: int,
    luck: float,
    inventory: list[dict[str, Any]],
    active_slots: dict[str, list[str | None]],
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Build the leaderboard API's JSON-compatible completed-run document."""
    active_items = [
        item_id
        for slots in active_slots.values()
        for item_id in slots
        if item_id is not None
    ]
    return {
        "name": name,
        "score": str(score.to_decimal()),
        "runtime_seconds": float(runtime_seconds),
        "level": int(level),
        "luck": float(luck),
        "inventory": _json_value(inventory),
        "active_items": [str(item_id) for item_id in active_items],
        "stats": _json_value(stats),
    }


def submit_run(
    payload: dict[str, Any],
    *,
    base_url: str | None = None,
    timeout_seconds: float = 4.0,
) -> dict[str, Any]:
    """Explicitly submit a run; raises clear transport or API errors."""
    if not 0 < timeout_seconds <= 30:
        raise ValueError(
            "timeout_seconds must be greater than 0 and at most 30")
    endpoint = (base_url or os.environ.get(
        "CHANCE_SURVIVORS_LEADERBOARD_URL",
        DEFAULT_LEADERBOARD_URL,
    )).rstrip("/")
    if not endpoint.startswith(("http://", "https://")):
        raise ValueError("Leaderboard URL must use http:// or https://")
    body = json.dumps(payload, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")
    request = Request(
        f"{endpoint}/api/submit-run",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(response_body) > MAX_RESPONSE_BYTES:
                raise ValueError(
                    "Leaderboard API response exceeded the size limit")
            result = json.loads(response_body)
    except HTTPError as exc:
        response_body = exc.read(MAX_RESPONSE_BYTES).decode(
            "utf-8", errors="replace")
        raise RuntimeError(
            f"Leaderboard API returned HTTP {exc.code}: {response_body}") from exc
    except URLError as exc:
        raise ConnectionError(
            f"Leaderboard server is offline or unreachable: {exc.reason}") from exc
    except TimeoutError as exc:
        raise TimeoutError("Leaderboard API request timed out") from exc

    if not isinstance(result, dict) or result.get("status") != "accepted" or "id" not in result:
        raise ValueError(
            "Leaderboard API returned an invalid submission response")
    return result
