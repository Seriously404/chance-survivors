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
    mission_score_bonus_pct,
)
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.systems.collision import CollisionSystem
from game.systems.spawner import SpawnerSystem
from game.systems.game_state import GameStateManager, GameState
from game.utils.helpers import get_player_rotation
from game.systems.bullets import load_bullet_types
from game.systems.currency import CurrencyWallet, CurrencyNotifications
from game.systems.inventory import Inventory
from game.systems.progression import PlayerProgress, award_enemy_kill
from game.systems.scoring import RunScore
from game.systems.items import create_initial_inventory, spawnable_items, player_bonuses
from game.systems.weapons import projectile_for_weapon
from game.utils.large_number import LargeNumber
from game.systems.combinations import CombinationEngine
from game.systems.items import player_speed_multiplier
from copy import deepcopy


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


def _combination_preview(engine: CombinationEngine, inventory: Inventory, item_id: str | None) -> dict | None:
    if not item_id:
        return None
    try:
        combined = engine.evaluate_inventory(inventory, item_id)
    except (KeyError, ValueError):
        return None
    return {
        "base_id": combined.base_id,
        "stats": {name: str(value) for name, value in combined.stats.items()},
        "behaviors": list(combined.behaviors),
        "rules_applied": list(combined.rules_applied),
        "contributions": {
            name: [f"{part['source_id']}: {part['amount']}" for part in parts]
            for name, parts in combined.contributions.items()
        },
    }


def main() -> None:
    """Main game loop."""
    # Initialize systems
    renderer = Renderer(SCREEN_WIDTH, SCREEN_HEIGHT, PIXELS_PER_UNIT)
    bullet_types = load_bullet_types()
    weapon_cooldowns = [0.0, 0.0]
    ability_cooldowns = [0.0] * 10
    wallet = CurrencyWallet()
    notifications = CurrencyNotifications()
    inventory = create_initial_inventory()
    spawn_catalog = spawnable_items()
    spawn_counter = 0
    progress = PlayerProgress()
    run_score = RunScore(mission_score_bonus_pct)
    combination_engine = CombinationEngine()
    game_state = GameStateManager()
    collision_system = CollisionSystem(PIXELS_PER_UNIT)
    spawner = SpawnerSystem(enemy_types, enemy_spawn_delay)

    # Initialize game entities
    player = Player(health=player_max_health, max_health=player_max_health)
    applied_health_bonus=0
    bullets: list[Projectile] = []
    enemies: list = []

    # Game state
    running = True
    enemy_spawn_timer = 0
    menu_error = ""
    paused = False

    try:
        while running:
            # -------------------------
            # Input
            # -------------------------
            renderer.set_view(game_state.state.name, game_state.active_panel)
            running, shots, actions = renderer.process_events()

            if not running:
                break

            # -------------------------
            # State transitions
            # -------------------------
            if game_state.is_menu():
                if "play" in actions or "confirm" in actions:
                    if not renderer.get_player_name():
                        menu_error = "Enter a name before playing."
                        renderer.input_handler.name_error = menu_error
                        continue
                    player, bullets, spawner = reset_game(
                        player, bullets, spawner)
                    renderer.reset_timer()
                    enemy_spawn_timer = 0
                    run_score = RunScore(mission_score_bonus_pct)
                    wallet = CurrencyWallet()
                    notifications = CurrencyNotifications()
                    inventory = create_initial_inventory()
                    weapon_cooldowns = [0.0, 0.0]
                    ability_cooldowns = [0.0] * 10
                    bonuses = player_bonuses(inventory)
                    player.max_health = LargeNumber(player_max_health) + bonuses["health"]
                    player.health = player.max_health
                    applied_health_bonus=bonuses["health"]
                    paused = False
                    menu_error = ""
                    game_state.start_game(renderer.get_player_name())

                elif "settings" in actions or "open_settings" in actions:
                    game_state.change_state(GameState.SETTINGS)
                elif "exit" in actions:
                    running = False

            elif game_state.is_settings():
                if "resolution" in actions:
                    renderer.set_resolution(renderer.resolution_index + 1)
                if "fullscreen" in actions:
                    renderer.fullscreen = not renderer.fullscreen
                if "apply_settings" in actions:
                    renderer.apply_display()
                if "back" in actions or "close_panel" in actions:
                    game_state.change_state(GameState.MENU)

            elif game_state.is_playing():
                if "pause" in actions:
                    paused = not paused
                for panel in ("inventory", "quests", "upgrades", "bazaar"):
                    if panel in actions:
                        game_state.open_panel(panel)
                        renderer.menu_tab = panel
                for action in actions:
                    if action.startswith("spawn_item:"):
                        template_id=action.split(":",1)[1]
                        template=next((item for item in spawn_catalog if item["id"]==template_id),None)
                        if template and len(inventory.items)<Inventory.CAPACITY:
                            spawned=deepcopy(template)
                            spawn_counter+=1
                            spawned["id"]=f"bazaar-{spawn_counter}"
                            inventory.add(spawned)
                    elif action.startswith("tab_"):
                        renderer.menu_tab = action[4:]
                        game_state.open_panel(renderer.menu_tab)
                    elif action == "increase_difficulty":
                        spawner.increase_difficulty()
                    elif action.startswith("upgrade_"):
                        renderer.upgrade_tab = action[8:]
                    elif action.startswith("select:"):
                        renderer.selected_item_id = action.split(":",1)[1]
                    elif action.startswith("combine:"):
                        _, base_id, combo_index, item_id = action.split(":",3)
                        try:
                            inventory.assign_combination(base_id,int(combo_index),item_id)
                        except (KeyError, IndexError, ValueError):
                            pass
                    elif action.startswith("equip:"):
                        _, slot_kind, slot_index, item_id = action.split(":",3)
                        try:
                            inventory.equip(item_id,slot_kind,int(slot_index))
                        except (KeyError, IndexError, ValueError):
                            pass
                    elif action.startswith("uncombine:"):
                        _, base_id, combo_index = action.split(":",2)
                        try:
                            inventory.assign_combination(base_id,int(combo_index),None)
                        except (KeyError, IndexError, ValueError):
                            pass
                    elif action.startswith("unequip:"):
                        _, slot_kind, slot_index = action.split(":",2)
                        try:
                            inventory.unequip(slot_kind,int(slot_index))
                        except (KeyError, IndexError, ValueError):
                            pass
                    elif action == "set_base" and renderer.selected_item_id:
                        renderer.selected_base_id = renderer.selected_item_id
                if "close_panel" in actions:
                    if game_state.active_panel:
                        game_state.close_panel()
                    else:
                        paused = False
                if "close_menu" in actions:
                    game_state.close_panel()
                if "back" in actions and not game_state.active_panel:
                    game_state.change_state(GameState.MENU)

            elif game_state.is_game_over():
                if "confirm" in actions:
                    game_state.change_state(GameState.MENU)

            # -------------------------
            # Time
            # -------------------------
            dt = renderer.tick(FRAMERATE)
            notifications.update(dt)

            # -------------------------
            # Gameplay update
            # -------------------------
            if game_state.is_playing() and not paused and not game_state.active_panel:
                bonuses=player_bonuses(inventory)
                current_health_bonus=bonuses["health"]
                if current_health_bonus != applied_health_bonus:
                    player.max_health=LargeNumber(player_max_health)+current_health_bonus
                    player.health=max(LargeNumber(0),min(player.max_health,player.health+current_health_bonus-applied_health_bonus))
                    applied_health_bonus=current_health_bonus
                weapon_cooldowns=[max(0.0,value-dt) for value in weapon_cooldowns]
                ability_cooldowns=[max(0.0,value-dt) for value in ability_cooldowns]
                clicks={0:None,1:None}
                for button,position in renderer.input_handler.fire_events:
                    if button==1: clicks[0]=position
                    elif button==3: clicks[1]=position
                by_id={str(item["id"]):item for item in inventory.items}
                for slot_index,button in enumerate((1,3)):
                    weapon_id=inventory.active_slots["weapons"][slot_index]
                    weapon=by_id.get(str(weapon_id)) if weapon_id else None
                    weapon_stats=weapon.get("stats",{}) if weapon else {}
                    type_name=weapon_stats.get("bullet_type",("rapid_fire","heavy_shot")[slot_index])
                    definition=bullet_types.get(str(type_name))
                    if definition is None:
                        continue
                    automatic=bool(weapon_stats.get("automatic",definition.automatic))
                    fire_position=clicks[slot_index]
                    if fire_position is None and automatic and button in renderer.input_handler.mouse_buttons_held:
                        fire_position=renderer.get_mouse_position()
                    if fire_position is None or weapon_cooldowns[slot_index]>0:
                        continue
                    player_angle=get_player_rotation(fire_position,renderer.screen_width,renderer.screen_height)
                    combined_weapon = (
                        combination_engine.evaluate_inventory(inventory, str(weapon_id))
                        if weapon is not None else None
                    )
                    projectile,cooldown,_=projectile_for_weapon(
                        player,player_angle,combined_weapon,slot_index,bullet_types,
                        bullet_base_speed,bonuses["damage_pct"])
                    bullets.append(projectile)
                    weapon_cooldowns[slot_index]=cooldown

                # Update spawner
                spawner.update(dt)
                if spawner.should_spawn():
                    spawner.spawn(player.x, player.y, enemies)
                    spawner.reset()

                # Get player movement
                player_dx, player_dy = renderer.get_movement()
                speed_multiplier = player_speed_multiplier(bonuses["speed_pct"])
                player.move(player_dx, player_dy, dt, speed_multiplier)

                # Update bullets
                despawn_distance = (SCREEN_WIDTH / 2 / PIXELS_PER_UNIT) * 1.5
                bullets = [
                    bullet for bullet in bullets
                    if not bullet.should_despawn(player.x, player.y, despawn_distance)
                ]
                for bullet in bullets:
                    bullet.steer_towards(enemies, dt)
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
                for _enemy in collision_system.killed_enemies:
                    run_score.award(LargeNumber(10) * _enemy.reward_multiplier)
                    currency, amount = wallet.reward_for_kill(
                        luck=bonuses["luck"], reward_multiplier=_enemy.reward_multiplier
                    )
                    notifications.add(currency, amount)
                    award_enemy_kill(progress)
                player = collision_system.check_enemy_player_collisions(
                    enemies,
                    player,
                    enemy_types,
                    bonuses["defense"],
                )

                # Check game over
                if not player.is_alive():
                    game_state.change_state(GameState.GAME_OVER)

                # Update player rotation
                player.set_rotation(
                    renderer.get_mouse_position(),
                    renderer.screen_width,
                    renderer.screen_height,
                )

                # Prepare game state for rendering
                preview = (
                    _combination_preview(combination_engine, inventory, renderer.selected_base_id)
                    if renderer.menu_tab == "upgrades" and renderer.upgrade_tab == "combination"
                    else None
                )
                game_state_dict = {
                    "player": player,
                    "bullets": bullets,
                    "enemies": enemies,
                    "enemy_types": enemy_types,
                    "absolute_score": str(run_score.base_score),
                    "total_score": str(run_score.total_score),
                    "currency": wallet.amounts,
                    "notifications": notifications.items,
                    "paused": paused,
                    "actions": actions,
                    "items": inventory.items,
                    "active_slots": inventory.active_slots,
                    "level": progress.level,
                    "experience": progress.current_exp,
                    "next_level_exp": progress.exp_to_next_level,
                    "total_experience": progress.total_exp,
                    "luck": bonuses["luck"],
                    "speed": speed_multiplier,
                    "weapon_cooldowns": weapon_cooldowns,
                    "ability_cooldowns": ability_cooldowns,
                    "spawn_catalog": spawn_catalog,
                    "difficulty_level": spawner.difficulty_level,
                    "active_scaling_time": spawner.scaling.active_time_seconds,
                    "combined_item": preview,
                }

                renderer.draw(game_state_dict)

            elif game_state.is_menu():
                renderer.draw_menu(menu_error)
            elif game_state.is_settings():
                renderer.draw_settings()
            elif game_state.is_game_over():
                renderer.draw_placeholder(
                    "Game Over — Enter to return to menu")
            elif game_state.is_playing():
                bonuses=player_bonuses(inventory)
                preview = (
                    _combination_preview(combination_engine, inventory, renderer.selected_base_id)
                    if renderer.menu_tab == "upgrades" and renderer.upgrade_tab == "combination"
                    else None
                )
                renderer.draw({"player": player, "bullets": bullets, "enemies": enemies, "enemy_types": enemy_types,
                               "absolute_score": str(run_score.base_score), "total_score": str(run_score.total_score), "currency": wallet.amounts,
                               "notifications": notifications.items, "paused": paused, "actions": actions,
                               "items":inventory.items,"active_slots":inventory.active_slots,"level":progress.level,
                               "experience":progress.current_exp,"next_level_exp":progress.exp_to_next_level,
                               "total_experience":progress.total_exp,"luck":bonuses["luck"],"speed":player_speed_multiplier(bonuses["speed_pct"]),
                               "weapon_cooldowns":weapon_cooldowns,"ability_cooldowns":ability_cooldowns,"spawn_catalog":spawn_catalog,
                               "difficulty_level":spawner.difficulty_level,"active_scaling_time":spawner.scaling.active_time_seconds,
                               "combined_item":preview})

    finally:
        renderer.close()


if __name__ == "__main__":
    main()
