import random
import math

from client.render import Renderer
from client.input import Input
from game.core.game import Game
from game.core.states import GameState

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

player_max_health = 100

# -------------------------
# Enemy settings
# -------------------------

# enemy spawn delay is in miliseconds.
enemy_spawn_delay = 2000

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
        "turning_speed": 1.0,
        "size": 30,
        "max_health": 10
    }
}

enemy_list = []

bullet_list = []


# -------------------------
# Initialization
# -------------------------

renderer = Renderer(
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PIXELS_PER_UNIT
)

game = Game()

input = Input()

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

    return math.atan2(direction_y, direction_x)


def shoot_bullet(mouse_position):
    angle = get_player_rotation(mouse_position)

    direction_x = math.cos(angle)
    direction_y = math.sin(angle)

    bullet = {
        "x": player_x,
        "y": player_y,
        "dx": direction_x,
        "dy": direction_y,
        "angle": angle,
        "speed": bullet_base_speed * basic_bullet_speed_modifier,
        "damage": 2,
        "piercing": 0,
        "hit_enemies": [],
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


def spawn_enemy():
    x = random.uniform(-1, 1)
    y = random.uniform(-1, 1)

    magnitude = get_distance(0, 0, x, y)
    x /= magnitude
    y /= magnitude

    x = (x * (SCREEN_WIDTH / 2 / PIXELS_PER_UNIT) * 1.5) + player_x
    y = (y * (SCREEN_HEIGHT / 2 / PIXELS_PER_UNIT) * 1.5) + player_y

    dx = player_x - x
    dy = y - player_y

    angle = math.atan2(dy, dx)

    magnitude = get_distance(0, 0, dx, dy)
    dx /= magnitude
    dy /= magnitude

    enemy_list.append({
        "type": "basic",
        "x": x,
        "y": y,
        "dx": dx,
        "dy": dy,
        "angle": angle,
        "health": enemy_types["basic"]["max_health"],
        "max_health": enemy_types["basic"]["max_health"],
    })


def update_enemies(dt):
    for enemy in enemy_list[:]:
        # sub block moves the enemy
        speed = enemy_types[enemy["type"]]["speed"] * 0.5 * dt

        enemy["x"] += enemy["dx"] * speed
        enemy["y"] -= enemy["dy"] * speed

        # sub block turns the enemy towards the player
        turning_speed = enemy_types[enemy["type"]]["turning_speed"]

        # Direction from enemy to player
        dx = player_x - enemy["x"]
        dy = enemy["y"] - player_y

        if dx == 0 and dy == 0:
            continue

        target_angle = math.atan2(dy, dx)
        current_angle = math.atan2(enemy["dy"], enemy["dx"])

        # Find the shortest rotation direction
        angle_difference = (
            target_angle - current_angle + math.pi
        ) % (2 * math.pi) - math.pi

        max_rotation = math.radians(90) * turning_speed * dt

        rotation = max(
            -max_rotation,
            min(max_rotation, angle_difference)
        )

        # Update the normalized direction vector
        new_angle = current_angle + rotation

        enemy["dx"] = math.cos(new_angle)
        enemy["dy"] = math.sin(new_angle)
        enemy["angle"] = math.atan2(enemy["dy"], enemy["dx"])


def check_bullet_enemy_collision(bullet, enemy, enemy_types):
    """Check if a bullet collides with an enemy"""
    enemy_stats = enemy_types[enemy["type"]]
    bullet_size = 5  # bullet radius

    collision_distance = (
        enemy_stats["size"] / 2 + bullet_size
    ) / PIXELS_PER_UNIT

    distance = get_distance(
        bullet["x"], bullet["y"],
        enemy["x"], enemy["y"]
    )

    return distance <= collision_distance


def check_enemy_player_collision(enemy, enemy_types, player_pos):
    """Check if an enemy collides with the player"""
    enemy_stats = enemy_types[enemy["type"]]
    player_size = 30

    collision_distance = (
        enemy_stats["size"] / 2 + player_size / 2
    ) / PIXELS_PER_UNIT

    distance = get_distance(
        enemy["x"], enemy["y"],
        player_pos["x"], player_pos["y"]
    )

    return distance <= collision_distance


def check_bullet_enemy_collisions():
    for bullet in bullet_list[:]:
        for enemy in enemy_list[:]:

            if enemy in bullet["hit_enemies"]:
                continue

            if not check_bullet_enemy_collision(bullet, enemy, enemy_types):
                continue

            bullet["hit_enemies"].append(enemy)

            damage = min(bullet["damage"], enemy["health"])

            enemy["health"] -= damage
            bullet["damage"] -= damage

            if enemy["health"] <= 0:
                enemy_list.remove(enemy)

            if bullet["piercing"] == 0 or bullet["damage"] <= 0:
                bullet_list.remove(bullet)
                break


def check_enemy_player_collisions():
    global player_health

    player_size = 30

    for enemy in enemy_list[:]:
        if not check_enemy_player_collision(enemy, enemy_types, {"x": player_x, "y": player_y}):
            continue

        enemy_stats = enemy_types[enemy["type"]]

        collision_distance = (
            enemy_stats["size"] / 2 + player_size / 2
        ) / PIXELS_PER_UNIT

        distance = get_distance(
            enemy["x"], enemy["y"],
            player_x, player_y
        )

        if distance <= collision_distance:
            player_health -= enemy_stats["damage"]
            player_health = max(0, player_health)

            enemy_list.remove(enemy)


# --------------------------
# Game reset function
# --------------------------


def reset_game():
    global player_x, player_y
    global player_health
    global total_score, absolute_score

    player_x = 0.0
    player_y = 0.0

    player_health = player_max_health

    total_score = 0
    absolute_score = 0

    enemy_list.clear()
    bullet_list.clear()

# -------------------------
# Main loop
# -------------------------


def main():
    running = True
    enemy_spawn_timer = 0

    try:
        while running:

            # -------------------------
            # Input
            # -------------------------

            running, shots, actions = renderer.process_events()

            if not running:
                break

            # -------------------------
            # State transitions
            # -------------------------

            if game.state == GameState.MENU:

                if "confirm" in actions:
                    reset_game()
                    renderer.reset_timer()
                    enemy_spawn_timer = 0
                    game.start_game("Player")

                elif "open_settings" in actions:
                    game.change_state(GameState.SETTINGS)

            elif game.state == GameState.SETTINGS:

                if "back" in actions:
                    game.change_state(GameState.MENU)

            elif game.state == GameState.PLAYING:

                if "back" in actions:
                    game.change_state(GameState.MENU)

            elif game.state == GameState.GAME_OVER:

                if "confirm" in actions:
                    game.change_state(GameState.MENU)

            # -------------------------
            # Time
            # -------------------------

            dt = renderer.tick(FRAMERATE)

            # -------------------------
            # Gameplay update
            # -------------------------

            if game.state == GameState.PLAYING:

                for mouse_position in shots:
                    shoot_bullet(mouse_position)

                elapsed_ms = renderer.get_elapsed_ms()

                enemy_spawn_timer += dt * 1000

                if enemy_spawn_timer >= enemy_spawn_delay:
                    enemy_spawn_timer -= enemy_spawn_delay
                    spawn_enemy()

                player_dx, player_dy = renderer.get_movement()

                update_player(dt, player_dx, player_dy)
                update_bullets(dt)
                update_enemies(dt)

                check_bullet_enemy_collisions()
                check_enemy_player_collisions()

                if player_health <= 0:
                    game.change_state(GameState.GAME_OVER)

                player_angle = get_player_rotation(
                    renderer.get_mouse_position()
                )

                game_state = {
                    "player_x": player_x,
                    "player_y": player_y,
                    "player_health": player_health,
                    "player_max_health": player_max_health,
                    "player_angle": player_angle,
                    "bullet_list": bullet_list,
                    "enemy_list": enemy_list,
                    "enemy_types": enemy_types,
                    "total_score": total_score,
                    "elapsed_ms": elapsed_ms,
                    "fps": renderer.get_fps(),
                    "delta_time": dt,
                }

                renderer.draw(game_state)

            else:
                renderer.draw_placeholder(
                    game.state.name.replace("_", " ").title()
                )

    finally:
        renderer.close()


if __name__ == "__main__":
    main()
