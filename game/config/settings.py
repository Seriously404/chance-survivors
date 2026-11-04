"""Game configuration and constants."""

from typing import Dict, Any

# -------------------------
# Display and world settings
# -------------------------

SCREEN_WIDTH: int = 800
SCREEN_HEIGHT: int = 450
PIXELS_PER_UNIT: int = 200
FRAMERATE: int = 60
mission_score_bonus_pct: float = 0.0

# -------------------------
# Player settings
# -------------------------

player_max_health: int = 100

# -------------------------
# Enemy settings
# -------------------------

# Enemy spawn delay is in milliseconds.
enemy_spawn_delay: int = 2000

# -------------------------
# Bullet settings
# -------------------------

bullet_base_speed: float = 1.0
basic_bullet_speed_modifier: float = 3.0

# -------------------------
# Enemy types configuration
# -------------------------

enemy_types: Dict[str, Dict[str, Any]] = {
    "basic": {
        "speed": 1.0,
        "damage": 10,
        "resistances": {},
        "turning_speed": 1.0,
        "size": 30,
        "max_health": 10,
        "weight": 6,
    },
    "swift": {
        "speed": 1.6,
        "damage": 14,
        "resistances": {"slow": 0.2},
        "turning_speed": 1.25,
        "size": 24,
        "max_health": 8,
        "weight": 4,
    },
    "brute": {
        "speed": 0.7,
        "damage": 18,
        "resistances": {"fire": 0.4},
        "turning_speed": 0.8,
        "size": 38,
        "max_health": 24,
        "weight": 3,
    },
    "ranged": {
        "speed": 0.9,
        "damage": 16,
        "resistances": {"pierce": 0.15},
        "turning_speed": 1.1,
        "size": 28,
        "max_health": 16,
        "weight": 2,
    },
    "necromancer": {
        "speed": 0.8,
        "damage": 14,
        "resistances": {"shadow": 0.5},
        "turning_speed": 0.9,
        "size": 32,
        "max_health": 18,
        "weight": 1,
    },
    "shadow": {
        "speed": 1.35,
        "damage": 12,
        "resistances": {"light": 0.5},
        "turning_speed": 1.5,
        "size": 24,
        "max_health": 12,
        "weight": 2,
    },
}
