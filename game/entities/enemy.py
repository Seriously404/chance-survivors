"""Enemy entity module."""

import math
from dataclasses import dataclass, field
from typing import Dict, Any

from functools import lru_cache
from game.utils.large_number import LargeNumber


@lru_cache(maxsize=1)
def _load_enemy_definitions() -> Dict[str, Dict[str, Any]]:
    """Lazy load enemy definitions to avoid circular imports."""
    from ..systems.game_definitions import load_enemies
    return {enemy["id"]: enemy for enemy in load_enemies()}


def get_enemy_definitions() -> Dict[str, Dict[str, Any]]:
    """Get all enemy definitions."""
    return _load_enemy_definitions()


REWARD_DEFINITION_ALIASES = {
    "swift": "fast",
    "brute": "tank",
    "ranged": "shooter",
    "shadow": "elemental-shadow",
}


@dataclass
class Enemy:
    """Represents an enemy entity."""

    type: str
    x: float = 0.0
    y: float = 0.0
    dx: float = 1.0
    dy: float = 0.0
    angle: float = 0.0
    health: int = 10
    max_health: int = 10
    damage: int = 10
    speed: float = 1.0
    turning_speed: float = 1.0
    score_multiplier: int = 1
    currency_drop: str | None = None
    currency_amount: int = 0
    xp_reward: int = 1
    reward_eligible: bool = True
    summon_timer_seconds: float = 0.0
    ranged_attack_timer_seconds: float = 0.0
    summoner_id: int | None = None
    has_summoned: bool = False
    damage_events: dict[str, LargeNumber] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Normalize direction vector after initialization."""
        self._normalize_direction()

    def _normalize_direction(self) -> None:
        """Normalize the direction vector."""
        magnitude = math.sqrt(self.dx**2 + self.dy**2)
        if magnitude > 0:
            self.dx /= magnitude
            self.dy /= magnitude
            self.angle = math.atan2(self.dy, self.dx)

    def move_towards_player(
        self,
        player_x: float,
        player_y: float,
        speed: float,
        turning_speed: float,
        dt: float,
    ) -> None:
        """Move the enemy towards the player with rotation."""
        # Move the enemy (positive y = up)
        self.x += self.dx * speed * dt
        self.y += self.dy * speed * dt

        # Turn towards player
        dx = player_x - self.x
        dy = player_y - self.y

        if dx == 0 and dy == 0:
            return

        target_angle = math.atan2(dy, dx)
        current_angle = math.atan2(self.dy, self.dx)

        # Find the shortest rotation direction
        angle_difference = (target_angle - current_angle +
                            math.pi) % (2 * math.pi) - math.pi

        max_rotation = math.radians(90) * turning_speed * dt
        rotation = max(-max_rotation, min(max_rotation, angle_difference))

        # Update the normalized direction vector
        new_angle = current_angle + rotation
        self.dx = math.cos(new_angle)
        self.dy = math.sin(new_angle)
        self.angle = math.atan2(self.dy, self.dx)

    def take_damage(self, damage: int, *, elemental_damage=None) -> int:
        """Apply damage to the enemy. Returns the actual damage dealt."""
        actual_damage = min(damage, self.health)
        self.health -= actual_damage
        if elemental_damage and actual_damage > 0:
            components = {str(element).lower(): LargeNumber(amount)
                          for element, amount in elemental_damage.items()
                          if LargeNumber(amount) > 0}
            total = sum(components.values(), LargeNumber(0))
            if total > 0:
                for element, amount in components.items():
                    dealt = LargeNumber(actual_damage) * amount / total
                    self.damage_events[element] = self.damage_events.get(
                        element, LargeNumber(0)) + dealt
        return actual_damage

    def is_dead(self) -> bool:
        """Check if the enemy is dead."""
        return self.health <= 0

    @classmethod
    def create_from_type(
        cls,
        enemy_type: str,
        stats: Dict[str, Any],
        x: float,
        y: float,
    ) -> "Enemy":
        """Create an enemy from a type configuration."""
        reward_definition = get_enemy_definitions().get(
            REWARD_DEFINITION_ALIASES.get(enemy_type, enemy_type)
        )
        return cls(
            type=enemy_type,
            x=x,
            y=y,
            dx=1.0,
            dy=0.0,
            angle=0.0,
            health=stats["max_health"],
            max_health=stats["max_health"],
            damage=(stats.get("damage", 10) if isinstance(stats.get("damage", 10), int)
                    else LargeNumber(stats.get("damage", 10))),
            speed=float(stats.get("speed", 1.0)),
            turning_speed=float(stats.get("turning_speed", 1.0)),
            score_multiplier=max(1, int(stats.get("score_multiplier", 1))),
            currency_drop=(
                reward_definition.get("currency_drop")
                if reward_definition is not None
                else None
            ),
            currency_amount=(
                int(reward_definition.get("currency_amount", 0))
                if reward_definition is not None
                else 0
            ),
            xp_reward=(
                int(reward_definition.get("xp_reward", 1))
                if reward_definition is not None
                else 1
            ),
        )

    @classmethod
    def get_definition(cls, enemy_type: str) -> Dict[str, Any] | None:
        """Get the definition for an enemy type."""
        return get_enemy_definitions().get(enemy_type)

    @classmethod
    def get_all_definitions(cls) -> Dict[str, Dict[str, Any]]:
        """Get all enemy definitions."""
        return get_enemy_definitions().copy()
