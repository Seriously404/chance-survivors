import pygame

from client.input import InputHandler

from game.core.game import Game
from game.core.states import GameState


class Renderer:
    """Handles all rendering and display operations."""

    def __init__(self, screen_width: int, screen_height: int, pixels_per_unit: int):
        """Initialize the renderer.

        Args:
            screen_width: Width of the screen in pixels.
            screen_height: Height of the screen in pixels.
            pixels_per_unit: Conversion factor from world units to pixels.
        """
        pygame.init()

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.pixels_per_unit = pixels_per_unit

        self.screen = pygame.display.set_mode(
            (screen_width, screen_height)
        )
        pygame.display.set_caption("Chance Survivors")

        self.font = pygame.font.Font(None, 20)
        self.clock = pygame.time.Clock()

        self.bullet_size = (16, 6)
        self.bullet_color = (255, 220, 50)

        self.start_time = pygame.time.get_ticks()

        # Input handler
        self.input_handler = InputHandler()

    def process_events(self) -> tuple[bool, list[tuple[float, float]], list[str]]:
        """Process all pygame events.

        Returns:
            Tuple of (running, shots, actions).
        """
        return self.input_handler.process_events()

    def get_movement(self) -> tuple[float, float]:
        """Get player movement."""
        return self.input_handler.get_movement()

    def get_mouse_position(self) -> tuple[float, float]:
        """Get mouse position."""
        return self.input_handler.get_mouse_position()

    def tick(self, framerate):
        return self.clock.tick(framerate) / 1000.0

    def get_elapsed_ms(self):
        return pygame.time.get_ticks() - self.start_time

    def get_fps(self):
        return self.clock.get_fps()

    def reset_timer(self):
        self.start_time = pygame.time.get_ticks()

    # -------------------------
    # Coordinate conversion
    # -------------------------

    def world_to_screen(self, x, y, player_x, player_y):
        screen_x = (
            (x - player_x) * self.pixels_per_unit
            + self.screen_width / 2
        )
        screen_y = (
            (player_y - y) * self.pixels_per_unit
            + self.screen_height / 2
        )

        return screen_x, screen_y

    # -------------------------
    # Rendering
    # -------------------------

    def draw_grid(self, player_x, player_y):
        spacing = self.pixels_per_unit

        offset_x = (-player_x * self.pixels_per_unit) % spacing
        offset_y = (player_y * self.pixels_per_unit) % spacing

        for x in range(int(offset_x), self.screen_width, spacing):
            pygame.draw.line(
                self.screen,
                (55, 55, 65),
                (x, 0),
                (x, self.screen_height),
                2
            )

        for y in range(int(offset_y), self.screen_height, spacing):
            pygame.draw.line(
                self.screen,
                (55, 55, 65),
                (0, y),
                (self.screen_width, y),
                2
            )

    def draw_player(self, angle, health, max_health):
        player_size = 30

        player_surface = pygame.Surface(
            (player_size, player_size),
            pygame.SRCALPHA
        )

        pygame.draw.rect(
            player_surface,
            (50, 200, 255),
            (0, 0, player_size, player_size)
        )

        pygame.draw.polygon(
            player_surface,
            (255, 255, 255),
            [
                (player_size, player_size // 2),
                (player_size - 10, player_size // 2 - 6),
                (player_size - 10, player_size // 2 + 6)
            ]
        )

        rotated = pygame.transform.rotate(
            player_surface,
            angle * 57.295779513
        )

        center_x = self.screen_width // 2
        center_y = self.screen_height // 2

        rect = rotated.get_rect(center=(center_x, center_y))
        self.screen.blit(rotated, rect)

        # Only show the player's healthbar when damaged
        if health < max_health:
            self.draw_health_bar(
                center_x,
                center_y - player_size // 2 - 10,
                health,
                max_health
            )

    def draw_enemies(self, enemy_list, enemy_types, player_x, player_y):
        for enemy in enemy_list:
            stats = enemy_types[enemy["type"]]
            size = stats["size"]

            enemy_surface = pygame.Surface(
                (size, size),
                pygame.SRCALPHA
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

            screen_position = self.world_to_screen(
                enemy["x"],
                enemy["y"],
                player_x,
                player_y
            )

            rect = rotated.get_rect(center=screen_position)
            self.screen.blit(rotated, rect)

            # Only show the enemy's healthbar when damaged
            if enemy["health"] < enemy["max_health"]:
                self.draw_health_bar(
                    screen_position[0],
                    screen_position[1] - size / 2 - 8,
                    enemy["health"],
                    enemy["max_health"],
                )

    def draw_bullets(self, bullet_list, player_x, player_y):
        for bullet in bullet_list:
            bullet_surface = pygame.Surface(
                self.bullet_size,
                pygame.SRCALPHA
            )

            pygame.draw.rect(
                bullet_surface,
                self.bullet_color,
                (0, 0, self.bullet_size[0], self.bullet_size[1])
            )

            rotated = pygame.transform.rotate(
                bullet_surface,
                bullet["angle"] * 57.295779513
            )

            screen_position = self.world_to_screen(
                bullet["x"],
                bullet["y"],
                player_x,
                player_y
            )

            rect = rotated.get_rect(center=screen_position)
            self.screen.blit(rotated, rect)

    def draw_health_bar(self, center_x, top_y, current_health, max_health, width=40):
        height = 5

        if max_health <= 0:
            return

        health_ratio = max(0, min(1, current_health / max_health))

        background_rect = pygame.Rect(
            center_x - width / 2,
            top_y,
            width,
            height
        )

        health_rect = pygame.Rect(
            center_x - width / 2,
            top_y,
            width * health_ratio,
            height
        )

        pygame.draw.rect(self.screen, (100, 30, 30), background_rect)
        pygame.draw.rect(self.screen, (50, 220, 70), health_rect)

    def draw_debug(self, state: dict) -> None:
        """Draw debug information on screen.

        Args:
            state: Dictionary containing game state information.
        """
        player = state["player"]
        debug_values = {
            "player x": player.x,
            "player y": player.y,
            "FPS": self.get_fps(),
            "player health": player.health,
            "bullets": len(state["bullets"]),
        }

        for i, (key, value) in enumerate(debug_values.items()):
            text = self.font.render(
                f"{key}: {value:.2f}",
                True,
                (255, 255, 255)
            )

            rect = text.get_rect(
                topright=(
                    self.screen_width - 20,
                    20 + (20 * i)
                )
            )

            self.screen.blit(text, rect)

    def draw_timer(self, elapsed_ms):
        minutes = elapsed_ms // 60_000
        seconds = (elapsed_ms // 1_000) % 60
        milliseconds = elapsed_ms % 1_000

        text = self.font.render(
            f"Elapsed: {minutes:02d}:{seconds:02d}:{milliseconds:03d}",
            True,
            (255, 255, 255)
        )

        rect = text.get_rect(topleft=(20, 20))
        self.screen.blit(text, rect)

    # --------------------
    # Draw placeholders, remove these later
    # --------------------

    def draw_placeholder(self, message):
        self.screen.fill((30, 30, 30))

        text = self.font.render(
            message,
            True,
            (255, 255, 255)
        )

        rect = text.get_rect(
            center=(
                self.screen_width // 2,
                self.screen_height // 2
            )
        )

        self.screen.blit(text, rect)

        pygame.display.flip()

    def draw(self, state: dict) -> None:
        """Draw the current game state.

        Args:
            state: Dictionary containing player, bullets, enemies, and enemy_types.
        """
        self.screen.fill((30, 30, 30))

        player = state["player"]
        bullets = state["bullets"]
        enemies = state["enemies"]
        enemy_types = state["enemy_types"]

        self.draw_grid(player.x, player.y)
        self.draw_player(player.angle, player.health, player.max_health)
        self.draw_bullets(bullets, player.x, player.y)
        self.draw_enemies(enemies, enemy_types, player.x, player.y)
        self.draw_timer(self.get_elapsed_ms())
        self.draw_debug(state)

        pygame.display.flip()

    def close(self):
        pygame.quit()
