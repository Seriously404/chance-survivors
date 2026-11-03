"""Main entry point for Chance Survivors.

This module contains the main game loop and coordinates all game systems.
"""

from client.render import Renderer
from game.config.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PIXELS_PER_UNIT,
    FRAMERATE,
    player_max_health,
    enemy_types,
    enemy_spawn_delay,
    bullet_base_speed,
    basic_bullet_speed_modifier,
)
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.systems.collision import CollisionSystem
from game.systems.spawner import SpawnerSystem
from game.systems.game_state import GameStateManager, GameState
from game.utils.helpers import get_player_rotation


def reset_game(
    player: Player,
    bullets: list[Projectile],
    spawner: SpawnerSystem,
) -> tuple[Player, list[Projectile], SpawnerSystem]:
    """Reset the game state.

    Args:
        player: The player entity to reset.
        bullets: List of bullets to clear.
        spawner: The spawner system to reset.

    Returns:
        Tuple of (reset_player, cleared_bullets, reset_spawner).
    """
    player.reset(player_max_health)
    bullets.clear()
    spawner.reset()
    return player, bullets, spawner


def create_bullet(
    player_x: float,
    player_y: float,
    angle: float,
) -> Projectile:
    """Create a new bullet from player position.

    Args:
        player_x: Player's x position.
        player_y: Player's y position.
        angle: Player's rotation angle.

    Returns:
        A new Projectile instance.
    """
    return Projectile.create_from_player(
        player_x=player_x,
        player_y=player_y,
        angle=angle,
        speed_modifier=basic_bullet_speed_modifier,
        base_speed=bullet_base_speed,
    )


def main() -> None:
    """Main game loop."""
    # Initialize systems
    renderer = Renderer(SCREEN_WIDTH, SCREEN_HEIGHT, PIXELS_PER_UNIT)
    game_state = GameStateManager()
    collision_system = CollisionSystem(PIXELS_PER_UNIT)
    spawner = SpawnerSystem(enemy_types, enemy_spawn_delay)

    # Initialize game entities
    player = Player(health=player_max_health, max_health=player_max_health)
    bullets: list[Projectile] = []
    enemies: list = []

    # Game state
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
            if game_state.is_menu():
                if "confirm" in actions:
                    player, bullets, spawner = reset_game(player, bullets, spawner)
                    renderer.reset_timer()
                    enemy_spawn_timer = 0
                    game_state.start_game("Player")

                elif "open_settings" in actions:
                    game_state.change_state(GameState.SETTINGS)

            elif game_state.is_settings():
                if "back" in actions:
                    game_state.change_state(GameState.MENU)

            elif game_state.is_playing():
                if "back" in actions:
                    game_state.change_state(GameState.MENU)

            elif game_state.is_game_over():
                if "confirm" in actions:
                    game_state.change_state(GameState.MENU)

            # -------------------------
            # Time
            # -------------------------
            dt = renderer.tick(FRAMERATE)

            # -------------------------
            # Gameplay update
            # -------------------------
            if game_state.is_playing():
                # Spawn bullets
                for mouse_position in shots:
                    player_angle = get_player_rotation(
                        mouse_position,
                        SCREEN_WIDTH,
                        SCREEN_HEIGHT,
                    )
                    bullet = create_bullet(player.x, player.y, player_angle)
                    bullets.append(bullet)

                # Update spawner
                spawner.update(dt)
                if spawner.should_spawn():
                    spawner.spawn(player.x, player.y, enemies)
                    spawner.reset()

                # Get player movement
                player_dx, player_dy = renderer.get_movement()
                player.move(player_dx, player_dy, dt)

                # Update bullets
                despawn_distance = (SCREEN_WIDTH / 2 / PIXELS_PER_UNIT) * 1.5
                bullets = [
                    bullet for bullet in bullets
                    if not bullet.should_despawn(player.x, player.y, despawn_distance)
                ]
                for bullet in bullets:
                    bullet.move(dt)

                # Update enemies
                for enemy in enemies:
                    enemy.move_towards_player(
                        player.x,
                        player.y,
                        enemy_types["basic"]["speed"] * 0.5,
                        enemy_types["basic"]["turning_speed"],
                        dt,
                    )

                # Check collisions
                bullets, enemies = collision_system.check_bullet_enemy_collisions(
                    bullets,
                    enemies,
                    enemy_types,
                )
                player = collision_system.check_enemy_player_collisions(
                    enemies,
                    player,
                    enemy_types,
                )

                # Check game over
                if not player.is_alive():
                    game_state.change_state(GameState.GAME_OVER)

                # Update player rotation
                player.set_rotation(
                    renderer.get_mouse_position(),
                    SCREEN_WIDTH,
                    SCREEN_HEIGHT,
                )

                # Prepare game state for rendering
                game_state_dict = {
                    "player": player,
                    "bullets": bullets,
                    "enemies": enemies,
                    "enemy_types": enemy_types,
                }

                renderer.draw(game_state_dict)

            else:
                renderer.draw_placeholder(game_state.state.name.replace("_", " ").title())

    finally:
        renderer.close()


if __name__ == "__main__":
    main()
