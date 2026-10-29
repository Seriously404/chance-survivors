import pygame

# Initialize Pygame
pygame.init()


# Set up the display
screen_width: int = 800
screen_height: int = 600
screen = pygame.display.set_mode((screen_width, screen_height))

# Set the title of the window
pygame.display.set_caption("Chance Survivors")

# set up text
font = pygame.font.Font(None, 20)
time_text_surface = font.render("Elapsed: 00:00:000", True, (255, 255, 255))
time_text_rect = time_text_surface.get_rect(topleft=(20, 20))
debug_text_surface = font.render("Hello World from the debug menu!", True, (255, 255, 255))
debug_text_rect = debug_text_surface.get_rect(topright=(screen_width - 20, 20))


# set up variables for the game
# player has 2 values here, 1 for their current value, and one for the direction they are going in, 
player_x: float = 0
player_y: float = 0
player_dx: float = 0
player_dy: float = 0
magnitude: float = 1

total_score: int = 0
absolute_score: int = 0


# initialize main loop variables
clock  = pygame.time.Clock()
running: bool = True
elapsed_ms: int = 0
framerate: int = 60

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

    # normalize movement vector and apply speed
    # dt = delta time
    dt = clock.tick(framerate) / 1000.0
    if player_dx != 0 or player_dy != 0:
        # holy pythagorean theoryem. this is propably not a good implementation.
        # i will change it to use constant values
        magnitude = (player_dx**2 + player_dy**2) ** 0.5

    if magnitude != 0:
        player_x += (player_dx / magnitude) * dt
        player_y += (player_dy / magnitude) * dt

    screen.fill((30, 30, 30))  # Dark background

    # update the debug menu
    debug_text_surface = font.render(f"player x: {player_x:.2f} \n player y: {player_y:.2f}", True, (255, 255, 255))

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
    screen.blit(time_text_surface, time_text_rect)
    screen.blit(debug_text_surface, debug_text_rect)


    # refresh display
    pygame.display.flip()

# Quit Pygame
pygame.quit()