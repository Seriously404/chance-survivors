import pygame


from client.render import Renderer


# Display and world settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PIXELS_PER_UNIT = 200

FRAMERATE = 60

# Player settings
player_x = 0.0
player_y = 0.0

player_dx = 0.0
player_dy = 0.0

player_health = 100

# Bullet settings (hardcoded prototype)
bullet_base_speed = 1.0
basic_bullet_speed_modifier = 3.0

# Score
total_score = 0
absolute_score = 0


# Entity storage
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


# Initialize client and clock
renderer = Renderer(
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PIXELS_PER_UNIT
)

clock = pygame.time.Clock()

running = True


# Helper functions
def get_distance(x1, y1, x2, y2):
    return ((x2 - x1)**2 + (y2 - y1)**2)**0.5


def get_player_rotation(mouse_position):
    mouse_x, mouse_y = mouse_position

    direction = pygame.Vector2(
        mouse_x - SCREEN_WIDTH / 2,
        SCREEN_HEIGHT / 2 - mouse_y
    )

    if direction.length_squared() == 0:
        return 0.0

    return direction.as_polar()[1] * 0.01745329252


# Gameplay functions
def shoot_bullet(mouse_position):
    angle = get_player_rotation(mouse_position)

    direction = pygame.Vector2(1, 0).rotate_rad(angle)

    # Don't shoot if the mouse is exactly at the player's centre
    if direction.length_squared() == 0:
        return

    bullet = {
        "x": player_x,
        "y": player_y,
        "dx": direction.x,
        "dy": direction.y,
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


def update_player(dt):
    global player_x, player_y

    magnitude = get_distance(
        0, 0,
        player_dx, player_dy
    )

    if magnitude > 0:
        player_x += (player_dx / magnitude) * dt
        player_y += (player_dy / magnitude) * dt


# Main loop
elapsed_ms = 0

while running:

    # Input handling
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                player_dy += 1
            elif event.key == pygame.K_s:
                player_dy -= 1
            elif event.key == pygame.K_a:
                player_dx -= 1
            elif event.key == pygame.K_d:
                player_dx += 1

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_w:
                player_dy -= 1
            elif event.key == pygame.K_s:
                player_dy += 1
            elif event.key == pygame.K_a:
                player_dx += 1
            elif event.key == pygame.K_d:
                player_dx -= 1

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (1, 3):
                shoot_bullet(event.pos)

    # Time
    dt = clock.tick(FRAMERATE) / 1000.0
    elapsed_ms = pygame.time.get_ticks()

    # Update game logic
    update_player(dt)
    update_bullets(dt)

    # Get current player rotation for rendering
    player_angle = get_player_rotation(pygame.mouse.get_pos())

    # Prepare state for the renderer
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
        "fps": clock.get_fps(),
    }

    # One call to the client to render everything
    renderer.draw(game_state)


# Shutdown
renderer.close()
