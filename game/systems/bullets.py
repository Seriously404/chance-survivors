"""Validated data-driven projectile definitions."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BulletType:
    name: str
    cooldown: float
    damage: int
    speed_modifier: float
    piercing: int
    automatic: bool


def load_bullet_types(path: Path | None = None) -> dict[str, BulletType]:
    config_path = path or Path(__file__).resolve(
    ).parents[2] / "assets" / "bullet_types.json"
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not raw:
            raise ValueError(
                "expected a non-empty object keyed by bullet type")
        result = {}
        for key, data in raw.items():
            if not isinstance(data, dict):
                raise ValueError(f"{key}: expected an object")
            cooldown, damage = data.get("cooldown"), data.get("damage")
            speed, piercing = data.get("speed_modifier"), data.get("piercing")
            automatic = data.get("automatic")
            if not isinstance(cooldown, (int, float)) or cooldown <= 0:
                raise ValueError(f"{key}.cooldown must be positive")
            if not isinstance(damage, int) or damage <= 0:
                raise ValueError(f"{key}.damage must be a positive integer")
            if not isinstance(speed, (int, float)) or speed <= 0:
                raise ValueError(f"{key}.speed_modifier must be positive")
            if not isinstance(piercing, int) or piercing < 0 or not isinstance(automatic, bool):
                raise ValueError(
                    f"{key} needs non-negative integer piercing and boolean automatic")
            result[key] = BulletType(key, float(
                cooldown), damage, float(speed), piercing, automatic)
        return result
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"Could not load bullet configuration at {config_path}: {exc}") from exc
