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
    }
}
