import pygame

# Initialize Pygame
pygame.init()


# Set up the display
screen_width: int = 800
screen_height: int = 600
pixels_per_unit: int = 200
screen = pygame.display.set_mode((screen_width, screen_height))

# Set the title of the window
pygame.display.set_caption("Chance Survivors")

# set up text
font = pygame.font.Font(None, 20)
time_text_surface = font.render("Elapsed: 00:00:000", True, (255, 255, 255))
time_text_rect = time_text_surface.get_rect(topleft=(20, 20))


# set up variables for the game
# player has 2 values here, 1 for their current value, and one for the direction they are going in,
player_x: float = 0
player_y: float = 0
player_dx: float = 0
player_dy: float = 0
player_health = 100
magnitude: float = 1

# Bullet settings (hardcoded for testing rn)
bullet_base_speed = 1.0
basic_bullet_speed_modifier = 3.0

bullet_size = (16, 6)
bullet_color = (255, 220, 50)

# set up score (unused right now tho)
total_score: int = 0
absolute_score: int = 0


# basically storage for every bullet and enemy

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


debug_list = {}

# initialize main loop variables
clock = pygame.time.Clock()
running: bool = True
elapsed_ms: int = 0
framerate: int = 60


# here lies dragons (functions)
# draws debug information to the top right of the screen.
def update_debug():
    debug_list = {"player x": player_x,
                  "player y": player_y,
                  "score": total_score,
                  "FPS": clock.get_fps(),
                  "player health": player_health}
    for i, (key, value) in enumerate(debug_list.items()):
        debug_text_surface = font.render(
            f"{key}: {value:.2f}", True, (255, 255, 255)
        )
        debug_text_rect = debug_text_surface.get_rect(
            topright=(screen_width - 20, 20 + (20 * i))
        )
        screen.blit(debug_text_surface, debug_text_rect)


# helper functions
def get_distance(x1, y1, x2, y2):
    return ((x2 - x1)**2 + (y2 - y1)**2)**0.5


def get_direction(x1, y1, x2, y2):
    direction = pygame.math.Vector2(x2 - x1, y2 - y1)

    if direction.length_squared() > 0:
        direction = direction.normalize()

    return direction


# this one is the goat cause it turns the tiny coordinates into proper pixels
def world_to_screen(x, y):
    screen_x = (x - player_x) * pixels_per_unit + screen_width / 2
    screen_y = (player_y - y) * pixels_per_unit + screen_height / 2

    return (screen_x, screen_y)


# i need this otside of the draw player cause
def get_player_rotation():
    mouse_x, mouse_y = pygame.mouse.get_pos()

    direction = pygame.Vector2(
        mouse_x - screen_width / 2,
        screen_height / 2 - mouse_y
    )

    if direction.length_squared() == 0:
        return 0.0

    return direction.as_polar()[1] * 0.01745329252

# gameplay relevant functions


# shoots bullet. self explanatory
def shoot_bullet():
    angle = get_player_rotation()

    direction = pygame.Vector2(1, 0).rotate_rad(angle)

    bullet = {
        "x": player_x,
        "y": player_y,
        "dx": direction.x,
        "dy": direction.y,
        "angle": angle,
        "speed": bullet_base_speed * basic_bullet_speed_modifier,
    }

    bullet_list.append(bullet)


# moves each bullet
def update_bullets(dt):
    # How far from the player a bullet can travel before despawning.
    despawn_x = (screen_width / 2 / pixels_per_unit) * 1.5
    despawn_y = (screen_height / 2 / pixels_per_unit) * 1.5

    for bullet in bullet_list[:]:

        # Move the bullet in world coordinates
        bullet["x"] += bullet["dx"] * bullet["speed"] * dt
        bullet["y"] += bullet["dy"] * bullet["speed"] * dt

        # Check whether the bullet is too far from the player
        if (
            abs(bullet["x"] - player_x) > despawn_x
            or abs(bullet["y"] - player_y) > despawn_y
        ):
            bullet_list.remove(bullet)

# drawing functions


# draws the player
def draw_player():
    player_size = 30

    # Create a fixed-size player surface
    player_surface = pygame.Surface(
        (player_size, player_size),
        pygame.SRCALPHA
    )

    pygame.draw.rect(
        player_surface,
        (50, 200, 255),
        (0, 0, player_size, player_size)
    )

    # Add an indicator so rotation is visible
    pygame.draw.polygon(player_surface, (255, 255, 255), [
        (player_size, player_size // 2),
        (player_size - 10, player_size // 2 - 6),
        (player_size - 10, player_size // 2 + 6)
    ])

    mouse_x, mouse_y = pygame.mouse.get_pos()

    direction = pygame.Vector2(
        mouse_x - screen_width / 2,
        mouse_y - screen_height / 2
    )

    angle = get_player_rotation()
    angle_degrees = angle * 57.295779513

    rotated = pygame.transform.rotate(player_surface, angle_degrees)

    rect = rotated.get_rect(
        center=(screen_width // 2, screen_height // 2)
    )

    screen.blit(rotated, rect)


# draw enemies
def draw_enemies():
    for enemy in enemy_list:

        stats = enemy_types[enemy["type"]]
        size = stats["size"]

        enemy_surface = pygame.Surface(
            (size, size),
        )

        pygame.draw.rect(
            enemy_surface,
            (220, 60, 60),
            (0, 0, size, size)
        )

        rotated = pygame.transform.rotate(
            enemy_surface,
            -enemy["angle"] * 57.295779513
        )

        screen_position = world_to_screen(
            enemy["x"], enemy["y"]
        )

        rect = rotated.get_rect(
            center=screen_position
        )

        screen.blit(rotated, rect)


# draw bullets
def draw_bullets():
    for bullet in bullet_list:

        bullet_surface = pygame.Surface(bullet_size, pygame.SRCALPHA)

        pygame.draw.rect(
            bullet_surface,
            bullet_color,
            (0, 0, bullet_size[0], bullet_size[1])
        )

        # Convert radians to degrees for Pygame
        angle_degrees = bullet["angle"] * 57.295779513

        rotated = pygame.transform.rotate(
            bullet_surface,
            angle_degrees
        )

        screen_position = world_to_screen(
            bullet["x"], bullet["y"]
        )

        rect = rotated.get_rect(center=screen_position)

        screen.blit(rotated, rect)


# draw world grid
def draw_grid():
    grid_size = 1
    spacing = grid_size * pixels_per_unit

    offset_x = (-player_x * pixels_per_unit) % spacing
    offset_y = (player_y * pixels_per_unit) % spacing

    for x in range(int(offset_x), screen_width, spacing):
        pygame.draw.line(
            screen, (55, 55, 65),
            (x, 0), (x, screen_height), 2
        )

    for y in range(int(offset_y), screen_height, spacing):
        pygame.draw.line(
            screen, (55, 55, 65),
            (0, y), (screen_width, y), 2
        )


# main loop
while running:

    # get player input
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
        # there are likely better ways to get player input than this garbage, but i do not care, this is the prototype
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
            if event.button == 1 or event.button == 3:
                shoot_bullet()

    # Calculate delta time in seconds
    dt = clock.tick(framerate) / 1000.0

    # normalize the movement, so diagonals are fair too.
    # no i will not import numpy just to use the normalize function it has.
    magnitude = get_distance(0, 0, player_dx, player_dy)

    if magnitude > 0:
        player_x += (player_dx / magnitude) * dt
        player_y += (player_dy / magnitude) * dt

    update_bullets(dt)

    # Dark background, also works as a reset for the screen
    screen.fill((30, 30, 30))

    # actual rendering code goes here
    draw_grid()
    draw_player()
    draw_bullets()
    draw_enemies()

    # timer
    elapsed_ms = pygame.time.get_ticks()
    minutes = elapsed_ms // 60_000
    seconds = (elapsed_ms // 1_000) % 60
    milliseconds = elapsed_ms % 1_000
    time_text_surface = font.render(
        f"Elapsed: {minutes:02d}:{seconds:02d}:{milliseconds:03d}",
        True,
        (255, 255, 255),
    )
    update_debug()
    screen.blit(time_text_surface, time_text_rect)

    # refresh display
    pygame.display.flip()

# Quit Pygame
pygame.quit()
