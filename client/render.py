
import pygame


class Renderer:
    def __init__(self, screen_width, screen_height, pixels_per_unit):
        pygame.init()

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.pixels_per_unit = pixels_per_unit

        self.screen = pygame.display.set_mode(
            (screen_width, screen_height)
        )
        pygame.display.set_caption("Chance Survivors")

        self.font = pygame.font.Font(None, 20)

        self.bullet_size = (16, 6)
        self.bullet_color = (255, 220, 50)

    def world_to_screen(self, x, y, player_x, player_y):
        screen_x = (
            (x - player_x) * self.pixels_per_unit
            + self.screen_width / 2
        )
        screen_y = (
            (player_y - y) * self.pixels_per_unit
            + self.screen_height / 2
        )

        return (screen_x, screen_y)

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

    def draw_player(self, angle):
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

        rect = rotated.get_rect(
            center=(
                self.screen_width // 2,
                self.screen_height // 2
            )
        )

        self.screen.blit(rotated, rect)

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

    def draw_debug(self, state):
        debug_values = {
            "player x": state["player_x"],
            "player y": state["player_y"],
            "score": state["total_score"],
            "FPS": state["fps"],
            "player health": state["player_health"],
            "bullets": len(state["bullet_list"])
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

    # The one main rendering call used by the game
    def draw(self, state):
        self.screen.fill((30, 30, 30))

        self.draw_grid(
            state["player_x"],
            state["player_y"]
        )

        self.draw_player(state["player_angle"])

        self.draw_bullets(
            state["bullet_list"],
            state["player_x"],
            state["player_y"]
        )

        self.draw_enemies(
            state["enemy_list"],
            state["enemy_types"],
            state["player_x"],
            state["player_y"]
        )

        self.draw_timer(state["elapsed_ms"])
        self.draw_debug(state)

        pygame.display.flip()

    def close(self):
        pygame.quit()
