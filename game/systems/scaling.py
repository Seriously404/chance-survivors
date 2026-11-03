"""Headless time-based and player-controlled enemy scaling."""

from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Mapping
from typing import Any

from game.utils.large_number import LargeNumber


SCALING_STATE_VERSION = 1
_STATS = ("health", "damage", "spawn_rate", "reward")


def _finite_float(value: Any, label: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(result) or result < 0 or (result == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{label} must be finite and {qualifier}")
    return result


@dataclass(frozen=True, slots=True)
class ScalingConfig:
    """Multipliers applied once per active-time step and difficulty level.

    Each multiplier must be at least one. For a stat ``s``, the total
    multiplier is ``time_s ** elapsed_steps * difficulty_s ** difficulty``.
    """

    time_step_seconds: float = 60.0
    time_health_multiplier: LargeNumber | int | float | str = 1.1
    time_damage_multiplier: LargeNumber | int | float | str = 1.05
    time_spawn_rate_multiplier: LargeNumber | int | float | str = 1.05
    time_reward_multiplier: LargeNumber | int | float | str = 1.05
    difficulty_health_multiplier: LargeNumber | int | float | str = 1.5
    difficulty_damage_multiplier: LargeNumber | int | float | str = 1.25
    difficulty_spawn_rate_multiplier: LargeNumber | int | float | str = 1.2
    difficulty_reward_multiplier: LargeNumber | int | float | str = 1.25
    minimum_spawn_delay_seconds: float = 0.001

    def __post_init__(self) -> None:
        for name in ("time_step_seconds", "minimum_spawn_delay_seconds"):
            object.__setattr__(self, name, _finite_float(getattr(self, name), name))
        for stat in _STATS:
            for kind in ("time", "difficulty"):
                name = f"{kind}_{stat}_multiplier"
                raw_multiplier = getattr(self, name)
                if isinstance(raw_multiplier, bool):
                    raise ValueError(f"{name} must be at least one")
                multiplier = LargeNumber(raw_multiplier)
                if multiplier < 1:
                    raise ValueError(f"{name} must be at least one")
                object.__setattr__(self, name, multiplier)

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_step_seconds": self.time_step_seconds,
            "minimum_spawn_delay_seconds": self.minimum_spawn_delay_seconds,
            "time_multipliers": {
                stat: getattr(self, f"time_{stat}_multiplier").to_dict()
                for stat in _STATS
            },
            "difficulty_multipliers": {
                stat: getattr(self, f"difficulty_{stat}_multiplier").to_dict()
                for stat in _STATS
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ScalingConfig:
        if not isinstance(data, Mapping):
            raise ValueError("Scaling configuration must be an object")
        time_multipliers = data.get("time_multipliers")
        difficulty_multipliers = data.get("difficulty_multipliers")
        if not isinstance(time_multipliers, Mapping) or not isinstance(difficulty_multipliers, Mapping):
            raise ValueError("Scaling configuration is missing multiplier maps")
        try:
            values: dict[str, Any] = {
                "time_step_seconds": data["time_step_seconds"],
                "minimum_spawn_delay_seconds": data["minimum_spawn_delay_seconds"],
            }
            for stat in _STATS:
                values[f"time_{stat}_multiplier"] = LargeNumber.from_dict(time_multipliers[stat])
                values[f"difficulty_{stat}_multiplier"] = LargeNumber.from_dict(difficulty_multipliers[stat])
            return cls(**values)
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Malformed scaling configuration: {exc}") from exc


class ScalingSystem:
    """Tracks active time and explicit difficulty independently.

    Time does not advance by reading a wall clock: integrations must call
    ``update_active_time`` with active simulation time. Difficulty changes only
    through ``increase_difficulty``.
    """

    def __init__(self, config: ScalingConfig | None = None) -> None:
        self.config = config or ScalingConfig()
        self._active_time_seconds = 0.0
        self._difficulty_level = 0

    @property
    def active_time_seconds(self) -> float:
        return self._active_time_seconds

    @property
    def difficulty_level(self) -> int:
        return self._difficulty_level

    @property
    def active_time_steps(self) -> int:
        """Whole configured steps elapsed, calculated without float division overflow."""
        elapsed_num, elapsed_den = self._active_time_seconds.as_integer_ratio()
        step_num, step_den = self.config.time_step_seconds.as_integer_ratio()
        return (elapsed_num * step_den) // (elapsed_den * step_num)

    def update_active_time(self, dt: float) -> None:
        delta = _finite_float(dt, "Active-time delta", allow_zero=True)
        updated = self._active_time_seconds + delta
        if not math.isfinite(updated):
            raise ValueError("Active gameplay time exceeded the finite timer range")
        self._active_time_seconds = updated

    def increase_difficulty(self, steps: int = 1) -> None:
        if type(steps) is not int or steps <= 0:
            raise ValueError("Difficulty steps must be a positive integer")
        self._difficulty_level += steps

    def multipliers(self) -> dict[str, LargeNumber]:
        """Return current health, damage, reward, and spawn-rate multipliers."""
        time_steps = self.active_time_steps
        result: dict[str, LargeNumber] = {}
        for stat in _STATS:
            time_multiplier = getattr(self.config, f"time_{stat}_multiplier")
            difficulty_multiplier = getattr(self.config, f"difficulty_{stat}_multiplier")
            result[stat] = (
                time_multiplier ** time_steps
                * difficulty_multiplier ** self._difficulty_level
            )
        return result

    def scaled_enemy_stats(
        self,
        base_health: LargeNumber | int | float | str,
        base_damage: LargeNumber | int | float | str,
        base_reward: LargeNumber | int | float | str = 1,
    ) -> dict[str, LargeNumber]:
        """Scale combat/reward values and include the spawn-rate multiplier."""
        if any(isinstance(value, bool) for value in (base_health, base_damage, base_reward)):
            raise ValueError("Enemy health, damage, and reward must be numeric values")
        health = LargeNumber(base_health)
        damage = LargeNumber(base_damage)
        reward = LargeNumber(base_reward)
        if health <= 0 or damage < 0 or reward < 0:
            raise ValueError("Enemy base health must be positive; damage/reward non-negative")
        multipliers = self.multipliers()
        return {
            "health": health * multipliers["health"],
            "damage": damage * multipliers["damage"],
            "reward": reward * multipliers["reward"],
            "spawn_rate_multiplier": multipliers["spawn_rate"],
        }

    def spawn_delay_seconds(self, base_delay_seconds: float) -> float:
        """Return a timer-safe spawn delay, respecting the configured minimum."""
        base_delay = _finite_float(base_delay_seconds, "Base spawn delay")
        delay = LargeNumber(base_delay) / self.multipliers()["spawn_rate"]
        minimum = self.config.minimum_spawn_delay_seconds
        if delay < minimum:
            return minimum
        return delay.to_float()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SCALING_STATE_VERSION,
            "config": self.config.to_dict(),
            "state": {
                "active_time_seconds": self._active_time_seconds,
                "difficulty_level": self._difficulty_level,
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ScalingSystem:
        if not isinstance(data, Mapping) or type(data.get("version")) is not int or data["version"] != SCALING_STATE_VERSION:
            raise ValueError("Unsupported scaling save version")
        try:
            config = ScalingConfig.from_dict(data["config"])
            state = data["state"]
            if not isinstance(state, Mapping):
                raise ValueError("Scaling save state must be an object")
            active_time = state["active_time_seconds"]
            difficulty = state["difficulty_level"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Malformed scaling save: {exc}") from exc
        active_time = _finite_float(active_time, "Saved active time", allow_zero=True)
        if type(difficulty) is not int or difficulty < 0:
            raise ValueError("Saved difficulty level must be a non-negative integer")
        result = cls(config)
        result._active_time_seconds = active_time
        result._difficulty_level = difficulty
        return result
