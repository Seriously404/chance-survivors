import pygame

# Initialize Pygame
pygame.init()

# Set up the display
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))

# Set the title of the window
pygame.display.set_caption("Chance Survivors")

# set up text
font = pygame.font.Font(None, 20)
text_surface = font.render("EYour FPS: 0", True, (255, 255, 255))
text_rect = text_surface.get_rect(topleft=(20, 20))


# set up variables for the game
player_x = 0
player_y = 0
total_score = 0
absolute_score = 0



# Main loop
running = True
clock = pygame.time.Clock()
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((30, 30, 40))  # Dark background

    text_surface = font.render(f"Your FPS: {clock.get_fps():.1f}", True, (255, 255, 255))
    screen.blit(text_surface, text_rect)

    pygame.display.flip()
    clock.tick(60)

# Quit Pygame
pygame.quit()