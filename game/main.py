
from client.render import Renderer


# -------------------------
# Display and world settings
# -------------------------

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PIXELS_PER_UNIT = 200

FRAMERATE = 60


# -------------------------
# Player settings
# -------------------------

player_x = 0.0
player_y = 0.0

player_health = 100


# Bullet settings
bullet_base_speed = 1.0
basic_bullet_speed_modifier = 3.0


# -------------------------
# Score
# -------------------------

total_score = 0
absolute_score = 0


# -------------------------
# Entity storage
# -------------------------

enemy_types = {
    "basic": {
        "speed": 1.0,
        "damage": 10,
        "resistances": {},
        "turning_speed": 2.0,
        "size": 30,
    }
}

enemy_list = [
    {
        "type": "basic",
        "x": 1.0,
        "y": 0.0,
        "angle": 0.0,
    }
]

bullet_list = []


# -------------------------
# Initialization
# -------------------------

renderer = Renderer(
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PIXELS_PER_UNIT
)


# -------------------------
# Helper functions
# -------------------------

def get_distance(x1, y1, x2, y2):
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def get_player_rotation(mouse_position):
    mouse_x, mouse_y = mouse_position

    direction_x = mouse_x - SCREEN_WIDTH / 2
    direction_y = SCREEN_HEIGHT / 2 - mouse_y

    if direction_x == 0 and direction_y == 0:
        return 0.0

    import math

    return math.atan2(direction_y, direction_x)


# -------------------------
# Gameplay functions
# -------------------------

def shoot_bullet(mouse_position):
    angle = get_player_rotation(mouse_position)

    import math

    direction_x = math.cos(angle)
    direction_y = math.sin(angle)

    bullet = {
        "x": player_x,
        "y": player_y,
        "dx": direction_x,
        "dy": direction_y,
        "angle": angle,
        "speed": bullet_base_speed * basic_bullet_speed_modifier,
    }

    bullet_list.append(bullet)


def update_bullets(dt):
    despawn_x = (
        SCREEN_WIDTH / 2 / PIXELS_PER_UNIT
    ) * 1.5

    despawn_y = (
        SCREEN_HEIGHT / 2 / PIXELS_PER_UNIT
    ) * 1.5

    for bullet in bullet_list[:]:
        bullet["x"] += bullet["dx"] * bullet["speed"] * dt
        bullet["y"] += bullet["dy"] * bullet["speed"] * dt

        if (
            abs(bullet["x"] - player_x) > despawn_x
            or abs(bullet["y"] - player_y) > despawn_y
        ):
            bullet_list.remove(bullet)


def update_player(dt, player_dx, player_dy):
    global player_x, player_y

    magnitude = get_distance(
        0, 0,
        player_dx, player_dy
    )

    if magnitude > 0:
        player_x += (player_dx / magnitude) * dt
        player_y += (player_dy / magnitude) * dt


# -------------------------
# Main loop
# -------------------------

def main():
    running = True

    try:
        while running:

            # Input handling
            running, shots = renderer.process_events()

            for mouse_position in shots:
                shoot_bullet(mouse_position)

            # Time
            dt = renderer.tick(FRAMERATE)
            elapsed_ms = renderer.get_elapsed_ms()

            # Movement input
            player_dx, player_dy = renderer.get_movement()

            # Update game logic
            update_player(dt, player_dx, player_dy)
            update_bullets(dt)

            # Player rotation
            player_angle = get_player_rotation(
                renderer.get_mouse_position()
            )

            # Prepare state for rendering
            game_state = {
                "player_x": player_x,
                "player_y": player_y,
                "player_health": player_health,
                "player_angle": player_angle,

                "bullet_list": bullet_list,
                "enemy_list": enemy_list,
                "enemy_types": enemy_types,

                "total_score": total_score,
                "elapsed_ms": elapsed_ms,
                "fps": renderer.get_fps(),
            }

            renderer.draw(game_state)

    finally:
        renderer.close()


if __name__ == "__main__":
    main()
