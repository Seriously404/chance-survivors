"""Main entry point for Chance Survivors.

This module contains the main game loop and coordinates all game systems.
"""

import game.config.settings as settings
import secrets
from client.render import Renderer
from game.config.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PIXELS_PER_UNIT,
    FRAMERATE,
    player_max_health,
    enemy_types as base_enemy_types,
    enemy_spawn_delay,
    bullet_base_speed,
    basic_bullet_speed_modifier,
)
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.entities.enemy_projectile import EnemyProjectile
from game.systems.collision import CollisionSystem
from game.systems.spawner import SpawnerSystem
from game.systems.game_state import GameStateManager, GameState
from game.utils.helpers import get_player_rotation
from game.systems.bullets import load_bullet_types
from game.systems.currency import CurrencyWallet, CurrencyNotifications
from game.systems.inventory import Inventory
from game.systems.progression import PlayerProgress, award_enemy_kill
<<<<<<< HEAD
from game.systems.items import (
    armor_set_status,
    create_initial_inventory,
    player_bonuses,
    spawnable_items,
)
from game.systems.numbers import LargeNumber
from game.systems.quests import QuestManager
from game.systems.relics import relic_effect_summary
from game.systems.weapons import projectile_for_weapon
from game.systems.bazaar import BazaarManager, build_extended_catalog
from game.systems.bazaar_service import BazaarService
from game.systems.fusion import FusionManager
from game.systems.enemy_scaling import EnemyScaling
from game.systems.enemy_catalog import build_enemy_roster
from game.systems.enemy_abilities import update_enemy_abilities
from game.systems.enemy_ranged import update_ranged_attacks
from game.systems.abilities import ability_cooldown, cast_ability
from game.systems.leaderboard_client import build_run_submission, submit_run
from game.systems.run_save import RunSave, configured_save_path
from game.systems.score_milestone import has_reached_infinity_milestone
=======
from game.systems.scoring import RunScore
from game.systems.items import create_initial_inventory, spawnable_items, player_bonuses
from game.systems.weapons import projectile_for_weapon
from game.utils.large_number import LargeNumber
from game.systems.combinations import CombinationEngine
from game.systems.items import player_speed_multiplier
>>>>>>> birch/projectile-collision-effects
from copy import deepcopy


enemy_types = build_enemy_roster(base_enemy_types)


def _find_item(items: list[dict], item_id: str | None) -> dict | None:
    if item_id is None:
        return None
    for item in items:
        if str(item.get("id")) == str(item_id):
            return item
    return None


def _bazaar_view_state(
    manager: BazaarManager,
    inventory: Inventory,
    wallet: CurrencyWallet,
    luck: float,
    elapsed_seconds: float,
) -> dict:
    manager.refresh_crates(elapsed_seconds)
    can_refresh = manager.can_manual_refresh(elapsed_seconds)
    seconds_to_rotation = (
        manager.ROTATION_SECONDS
        - int(elapsed_seconds % manager.ROTATION_SECONDS)
    )
    next_unlocks = [
        crate.unlock_seconds
        for crate in manager.crate_catalog
        if crate.unlock_seconds > elapsed_seconds
    ]
    next_unlock_seconds = (
        min(next_unlocks) - elapsed_seconds if next_unlocks else None
    )
    return {
        "crates": [
            {
                "id": crate.id,
                "name": crate.name,
                "cost": crate.cost,
                "bias": crate.bias,
                "description": crate.description,
            }
            for crate in manager.crates
        ],
        "can_refresh_crates": can_refresh,
        "crate_refresh_seconds": seconds_to_rotation,
        "crate_count": len(manager.available_crates(elapsed_seconds)),
        "crate_catalog_size": len(manager.crate_catalog),
        "next_crate_unlock_seconds": next_unlock_seconds,
        "catalog": [
            {**item, "market_price": manager.catalog_price(item)}
            for item in manager.catalog
        ],
        "owned_prices": {
            str(item["id"]): {
                "rarity": manager.rarity_upgrade_cost(item),
                "level": manager.level_upgrade_cost(item),
                "sell": manager.sell_value(item, trader_bonus=luck * 0.03),
            }
            for item in inventory.items
        },
        "wallet": wallet.amounts,
    }


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
    ability_vfx: list[dict[str, object]] = []
    wallet = CurrencyWallet()
    notifications = CurrencyNotifications()
    inventory = create_initial_inventory()
    bazaar_manager = BazaarManager(build_extended_catalog())
    bazaar_seed = bazaar_manager.seed
    bazaar_refresh_count = 0
    bazaar_last_manual_refresh_cycle = -1
    bazaar_service = BazaarService(bazaar_manager)
    fusion_manager = FusionManager()
    spawn_catalog = bazaar_manager.catalog
    spawn_counter = 0
    progress = PlayerProgress()
<<<<<<< HEAD
    absolute_score = LargeNumber(0)
    quest_manager = QuestManager()
    settings.mission_score_bonus_pct = quest_manager.total_bonus_pct()
=======
    run_score = RunScore(mission_score_bonus_pct)
    combination_engine = CombinationEngine()
>>>>>>> birch/projectile-collision-effects
    game_state = GameStateManager()
    collision_system = CollisionSystem(PIXELS_PER_UNIT)
    spawner = SpawnerSystem(enemy_types, enemy_spawn_delay)
    enemy_scaling = EnemyScaling()

    # Initialize game entities
    player = Player(health=player_max_health, max_health=player_max_health)
    applied_health_bonus=0
    bullets: list[Projectile] = []
    enemy_projectiles: list[EnemyProjectile] = []
    enemies: list = []

    # Game state
    running = True
    enemy_spawn_timer = 0
    run_elapsed_seconds = 0.0
    ability_vfx: list[dict[str, object]] = []
    menu_error = ""
    paused = False
    upload_status = "Upload is optional; your score is not sent unless you choose Upload."
    upload_complete = False
    save_path = configured_save_path()
    save_available = save_path.is_file()
    last_save_seconds = 0.0
    autosave_interval_seconds = 15.0

    def persist_run() -> bool:
        nonlocal save_available, last_save_seconds, menu_error
        try:
            snapshot = RunSave.capture(
                player_name=game_state.player_name,
                elapsed_seconds=run_elapsed_seconds,
                score=absolute_score,
                player_health=player.health,
                player_max_health=player.max_health,
                progression_level=progress.level,
                current_exp=progress.current_exp,
                total_exp=progress.total_exp,
                inventory=inventory,
                currencies=wallet.amounts,
                quest_state=quest_manager.to_save_state(),
                threat_level=enemy_scaling.threat_level,
                spawn_counter=spawn_counter,
                bazaar_seed=bazaar_seed,
                bazaar_refresh_count=bazaar_refresh_count,
                bazaar_last_manual_refresh_cycle=bazaar_last_manual_refresh_cycle,
            )
            snapshot.write(save_path)
        except (OSError, TypeError, ValueError) as exc:
            menu_error = f"Run save failed: {exc}"[:180]
            notifications.items.append({"text": menu_error, "remaining": 4.0})
            last_save_seconds = run_elapsed_seconds
            return False
        save_available = True
        last_save_seconds = run_elapsed_seconds
        menu_error = ""
        notifications.items.append({"text": "Run autosaved", "remaining": 2.0})
        return True

    def resume_saved_run() -> None:
        nonlocal player, bullets, spawner, run_elapsed_seconds, absolute_score
        nonlocal wallet, inventory, progress, quest_manager, enemy_scaling
        nonlocal spawn_counter, enemy_spawn_timer, weapon_cooldowns
        nonlocal bazaar_manager, bazaar_service, spawn_catalog, bazaar_seed
        nonlocal bazaar_refresh_count, bazaar_last_manual_refresh_cycle
        nonlocal ability_cooldowns, ability_vfx, save_available, last_save_seconds
        nonlocal applied_health_bonus, upload_status, upload_complete, menu_error, paused
        run_save = RunSave.read(save_path)
        saved = run_save.state
        player, bullets, spawner = reset_game(player, bullets, spawner)
        enemy_projectiles.clear()
        player.health = saved["player"]["health"]
        player.max_health = saved["player"]["max_health"]
        run_elapsed_seconds = saved["elapsed_seconds"]
        absolute_score = LargeNumber(saved["score"])
        progress.level = saved["progression"]["level"]
        progress.current_exp = LargeNumber(saved["progression"]["current_exp"])
        progress.total_exp = LargeNumber(saved["progression"]["total_exp"])
        inventory = run_save.restore_inventory()
        wallet = CurrencyWallet()
        for currency, amount in saved["currencies"].items():
            wallet.add(currency, LargeNumber(amount))
        quest_manager = QuestManager.from_save_state(saved["quests"])
        enemy_scaling = EnemyScaling(saved["threat_level"])
        spawn_counter = saved["spawn_counter"]
        bazaar_seed = saved["bazaar_seed"]
        bazaar_refresh_count = saved["bazaar_refresh_count"]
        bazaar_last_manual_refresh_cycle = saved["bazaar_last_manual_refresh_cycle"]
        bazaar_manager = BazaarManager(
            build_extended_catalog(),
            seed=bazaar_seed,
            refresh_count=bazaar_refresh_count,
            last_manual_refresh_cycle=bazaar_last_manual_refresh_cycle,
        )
        bazaar_manager.refresh_crates(run_elapsed_seconds)
        bazaar_service = BazaarService(bazaar_manager)
        spawn_catalog = bazaar_manager.catalog
        enemy_spawn_timer = 0
        weapon_cooldowns = [0.0, 0.0]
        ability_cooldowns = [0.0] * 10
        ability_vfx = []
        notifications.items = []
        paused = False
        applied_health_bonus = int(player_bonuses(inventory)["health"])
        renderer.set_player_name(saved["player_name"])
        settings.mission_score_bonus_pct = quest_manager.total_bonus_pct()
        last_save_seconds = run_elapsed_seconds
        save_available = True
        menu_error = ""
        upload_status = "Upload is optional; your score is not sent unless you choose Upload."
        upload_complete = False
        game_state.start_game(saved["player_name"])

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
                if "resume_run" in actions:
                    try:
                        resume_saved_run()
                    except (OSError, KeyError, TypeError, ValueError, OverflowError) as exc:
                        menu_error = f"Could not resume run: {exc}"[:180]
                elif "play" in actions or "confirm" in actions:
                    if not renderer.get_player_name():
                        menu_error = "Enter a name before playing."
                        renderer.input_handler.name_error = menu_error
                        continue
                    try:
                        save_path.unlink(missing_ok=True)
                    except OSError as exc:
                        menu_error = f"Could not replace the previous run save: {exc}"[:180]
                        continue
                    save_available = False
                    player, bullets, spawner = reset_game(
                        player, bullets, spawner)
                    enemy_projectiles.clear()
                    renderer.reset_timer()
                    enemy_spawn_timer = 0
<<<<<<< HEAD
                    run_elapsed_seconds = 0.0
                    enemy_scaling = EnemyScaling()
                    ability_vfx = []
                    absolute_score = LargeNumber(0)
=======
                    run_score = RunScore(mission_score_bonus_pct)
>>>>>>> birch/projectile-collision-effects
                    wallet = CurrencyWallet()
                    notifications = CurrencyNotifications()
                    inventory = create_initial_inventory()
                    bazaar_seed = secrets.randbits(64)
                    bazaar_manager = BazaarManager(
                        build_extended_catalog(),
                        seed=bazaar_seed,
                    )
                    bazaar_refresh_count = 0
                    bazaar_last_manual_refresh_cycle = -1
                    bazaar_service = BazaarService(bazaar_manager)
                    fusion_manager = FusionManager()
                    spawn_catalog = bazaar_manager.catalog
                    quest_manager = QuestManager()
                    settings.mission_score_bonus_pct = quest_manager.total_bonus_pct()
                    weapon_cooldowns = [0.0, 0.0]
                    ability_cooldowns = [0.0] * 10
                    bonuses = player_bonuses(inventory)
                    player.max_health = LargeNumber(player_max_health) + bonuses["health"]
                    player.health = player.max_health
                    applied_health_bonus=bonuses["health"]
                    paused = False
                    menu_error = ""
                    upload_status = "Upload is optional; your score is not sent unless you choose Upload."
                    upload_complete = False
                    game_state.start_game(renderer.get_player_name())
                    last_save_seconds = -autosave_interval_seconds

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
                bonuses = player_bonuses(inventory)
                for action in actions:
                    if action == "threat_up":
                        enemy_scaling.adjust_threat(1)
                    elif action == "threat_down":
                        enemy_scaling.adjust_threat(-1)
                if "pause" in actions:
                    paused = not paused
                for panel in ("inventory", "quests", "upgrades", "bazaar"):
                    if panel in actions:
                        game_state.open_panel(panel)
                        renderer.menu_tab = panel
                for action in actions:
                    if action == "bazaar_refresh":
                        if game_state.active_panel != "bazaar":
                            continue
                        try:
                            refreshed = bazaar_manager.manual_refresh_crates(
                                run_elapsed_seconds
                            )
                        except ValueError as exc:
                            notifications.items.append({
                                "text": str(exc),
                                "remaining": 3.0,
                            })
                        else:
                            if refreshed:
                                bazaar_refresh_count = bazaar_manager.refresh_count
                                bazaar_last_manual_refresh_cycle = (
                                    bazaar_manager.last_manual_refresh_cycle
                                )
                                persist_run()
                                notifications.items.append({
                                    "text": "Crate offers refreshed",
                                    "remaining": 3.0,
                                })
                            else:
                                notifications.items.append({
                                    "text": "No new crate offers are available to refresh yet.",
                                    "remaining": 3.0,
                                })
                    elif action.startswith("bazaar_buy:"):
                        crate_id = action.split(":", 1)[1]
                        next_counter = spawn_counter + 1
                        try:
                            reward = bazaar_service.buy_crate(
                                crate_id,
                                wallet=wallet,
                                inventory=inventory,
                                item_id=f"shop-{next_counter}",
                                luck=bonuses["luck"],
                            )
                        except ValueError as exc:
                            notifications.items.append({"text": str(exc), "remaining": 3.0})
                        else:
                            spawn_counter = next_counter
                            notifications.items.append({
                                "text": f"Bought {reward.get('name', 'crate item')}",
                                "remaining": 3.0,
                            })
                    elif action.startswith("bazaar_item:"):
                        definition_id = action.split(":", 1)[1]
                        next_counter = spawn_counter + 1
                        try:
                            item = bazaar_service.buy_catalog_item(
                                definition_id,
                                wallet=wallet,
                                inventory=inventory,
                                item_id=f"market-{next_counter}",
                            )
                        except ValueError as exc:
                            notifications.items.append({"text": str(exc), "remaining": 3.0})
                        else:
                            spawn_counter = next_counter
                            notifications.items.append({
                                "text": f"Bought {item.get('name', 'market item')}",
                                "remaining": 3.0,
                            })
                    elif action.startswith("bazaar_upgrade:"):
                        item_id = action.split(":", 1)[1]
                        try:
                            upgraded = bazaar_service.upgrade_rarity(
                                item_id,
                                wallet=wallet,
                                inventory=inventory,
                                luck=bonuses["luck"],
                            )
                        except ValueError as exc:
                            notifications.items.append({"text": str(exc), "remaining": 3.0})
                        else:
                            message = "Rarity increased!" if upgraded else "Rarity upgrade failed."
                            notifications.items.append({"text": message, "remaining": 3.0})
                    elif action.startswith("bazaar_level:"):
                        item_id = action.split(":", 1)[1]
                        try:
                            bazaar_service.upgrade_level(
                                item_id,
                                wallet=wallet,
                                inventory=inventory,
                            )
                        except ValueError as exc:
                            notifications.items.append({"text": str(exc), "remaining": 3.0})
                        else:
                            notifications.items.append({"text": "Item level increased!", "remaining": 3.0})
                    elif action.startswith("bazaar_sell:"):
                        item_id = action.split(":", 1)[1]
                        try:
                            value = bazaar_service.sell_item(
                                item_id,
                                wallet=wallet,
                                inventory=inventory,
                                trader_bonus=bonuses["luck"] * 0.03,
                            )
                        except ValueError as exc:
                            notifications.items.append({"text": str(exc), "remaining": 3.0})
                        else:
                            notifications.items.append({
                                "text": f"Sold for {value} Gold",
                                "remaining": 3.0,
                            })
                    elif action == "bazaar_fuse":
                        # Fusion is handled through the combination system
                        notifications.items.append({
                            "text": "Fusion requires selecting items from inventory first",
                            "remaining": 3.0,
                        })
                    elif action.startswith("bazaar_rarity_upgrade"):
                        # Rarity upgrade is handled through bazaar_upgrade action
                        pass
                    elif action.startswith("bazaar_level_upgrade"):
                        # Level upgrade is handled through bazaar_level action
                        pass
                    elif action.startswith("fusion_recipe:"):
                        _, recipe_id, source_id = action.split(":", 2)
                        if not fusion_manager.is_unlocked(progress.level):
                            notifications.items.append({
                                "text": f"Fusion unlocks at level {fusion_manager.UNLOCK_LEVEL}.",
                                "remaining": 3.0,
                            })
                            continue
                        source_item = _find_item(inventory.items, source_id or renderer.selected_item_id)
                        if source_item is None:
                            notifications.items.append({
                                "text": "Select an item to use as the fusion source.",
                                "remaining": 3.0,
                            })
                            continue
                        try:
                            companion = fusion_manager.find_companion(
                                source_item,
                                [
                                    candidate
                                    for candidate in inventory.items
                                    if candidate.get("status") not in {"active", "supplement", "combination_base"}
                                ],
                                recipe_id,
                            )
                            if companion is None:
                                raise ValueError(
                                    "No compatible unequipped fusion partner meets the recipe requirements."
                                )
                            result = inventory.fuse_items(
                                [source_item["id"], companion["id"]],
                                recipe_id=recipe_id,
                                fusion_manager=fusion_manager,
                            )
                        except (KeyError, ValueError) as exc:
                            notifications.items.append({
                                "text": f"Fusion failed: {exc}"[:180],
                                "remaining": 3.0,
                            })
                        else:
                            renderer.selected_item_id = result["id"]
                            notifications.items.append({
                                "text": f"Created {result['name']}",
                                "remaining": 3.0,
                            })
                    elif action.startswith("tab_"):
                        renderer.menu_tab = action[4:]
                        game_state.open_panel(renderer.menu_tab)
                    elif action == "increase_difficulty":
                        spawner.increase_difficulty()
                    elif action.startswith("upgrade_"):
                        renderer.upgrade_tab = action[8:]
                    elif action.startswith("quest_lock:"):
                        quest_id = action.split(":", 1)[1]
                        main_quest = quest_manager.main_quest
                        if main_quest is None or main_quest.id != quest_id:
                            continue
                        lock_restrictions = not main_quest.lock_on_accept
                        equipped_ids = {
                            item_id
                            for slots in inventory.active_slots.values()
                            for item_id in slots
                            if item_id is not None
                        }
                        equipped_ids.update(
                            supplement_id
                            for item_id in tuple(equipped_ids)
                            for supplement_id in inventory.get(item_id).get("combinations", [])
                            if supplement_id is not None
                        )
                        equipped_items = [inventory.get(item_id) for item_id in equipped_ids]
                        if not quest_manager.set_main_quest_lock(
                            quest_id,
                            lock_restrictions,
                            equipped_items,
                        ):
                            message = "Unequip restricted items before locking this quest."
                        else:
                            message = (
                                "Main quest restrictions locked."
                                if lock_restrictions
                                else "Main quest restrictions unlocked."
                            )
                        notifications.items.append({"text": message, "remaining": 3.0})
                    elif action.startswith("select:"):
                        renderer.selected_item_id = action.split(":",1)[1]
                    elif action.startswith("combine:"):
                        _, base_id, combo_index, item_id = action.split(":",3)
                        try:
                            if not quest_manager.can_equip(inventory.get(item_id)):
                                raise ValueError("Main quest restrictions prevent using this item.")
                            inventory.assign_combination(base_id,int(combo_index),item_id)
                        except (KeyError, IndexError, ValueError) as exc:
                            notifications.items.append({"text": str(exc), "remaining": 3.0})
                    elif action.startswith("equip:"):
                        _, slot_kind, slot_index, item_id = action.split(":",3)
                        try:
                            if not quest_manager.can_equip(inventory.get(item_id)):
                                raise ValueError("Main quest restrictions prevent equipping this item.")
                            inventory.equip(item_id,slot_kind,int(slot_index))
                        except (KeyError, IndexError, ValueError) as exc:
                            notifications.items.append({"text": str(exc), "remaining": 3.0})
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
                if "close_panel" in actions or "bazaar_close" in actions:
                    if game_state.active_panel:
                        game_state.close_panel()
                    else:
                        paused = False
                if "close_menu" in actions:
                    game_state.close_panel()
                if "back" in actions and not game_state.active_panel:
                    persist_run()
                    game_state.change_state(GameState.MENU)

            elif game_state.is_game_over():
                if "upload_run" in actions and not upload_complete:
                    bonuses = player_bonuses(inventory)
                    final_score = absolute_score.scale_by_percent(
                        quest_manager.total_bonus_pct()
                    )
                    try:
                        payload = build_run_submission(
                            name=renderer.get_player_name(),
                            score=final_score,
                            runtime_seconds=run_elapsed_seconds,
                            level=progress.level,
                            luck=bonuses["luck"],
                            inventory=inventory.items,
                            active_slots=inventory.active_slots,
                            stats={
                                "health": player.health,
                                "max_health": player.max_health,
                                "defense": bonuses["defense"],
                                "damage_pct": bonuses["damage_pct"],
                                "speed_pct": bonuses["speed_pct"],
                                "luck": bonuses["luck"],
                                "threat_level": enemy_scaling.threat_level,
                                "quest_bonus_pct": quest_manager.total_bonus_pct(),
                                "currency": wallet.amounts,
                                "quests": quest_manager.to_state(),
                            },
                        )
                        response = submit_run(payload)
                    except (ConnectionError, OSError, RuntimeError, TimeoutError, TypeError, ValueError) as exc:
                        upload_status = f"Upload failed: {exc}"[:180]
                    else:
                        upload_complete = True
                        upload_status = f"Submitted successfully (run #{response['id']})."
                if "confirm" in actions or "back" in actions or "return_menu" in actions:
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
                run_elapsed_seconds += dt
                ability_vfx = [
                    {**effect, "remaining": float(effect["remaining"]) - dt}
                    for effect in ability_vfx
                    if float(effect["remaining"]) > dt
                ]
                bonuses=player_bonuses(inventory)
<<<<<<< HEAD
                relic_summary = relic_effect_summary(inventory)
                current_health_bonus=int(bonuses["health"])
=======
                current_health_bonus=bonuses["health"]
>>>>>>> birch/projectile-collision-effects
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
                ability_kills = []
                for action in actions:
                    if not action.startswith("ability_cast:"):
                        continue
                    try:
                        ability_index = int(action.split(":", 1)[1])
                    except ValueError:
                        continue
                    if not 0 <= ability_index < len(ability_cooldowns):
                        continue
                    ability_id = inventory.active_slots["abilities"][ability_index]
                    ability = by_id.get(str(ability_id)) if ability_id else None
                    if ability is None or ability_cooldowns[ability_index] > 0:
                        continue
                    angle = get_player_rotation(
                        renderer.get_mouse_position(),
                        renderer.screen_width,
                        renderer.screen_height,
                    )
                    cooldown = ability_cooldown(ability)
                    outcome = cast_ability(
                        ability,
                        player,
                        enemies,
                        angle=angle,
                        base_speed=bullet_base_speed,
                        enemy_types=enemy_types,
                        damage_bonus_pct=bonuses["damage_pct"],
                    )
                    if not outcome.consumed:
                        continue
                    ability_cooldowns[ability_index] = cooldown
                    if outcome.projectile is not None:
                        bullets.append(outcome.projectile)
                    ability_kills.extend(outcome.killed_enemies)
                    if outcome.healed:
                        notifications.items.append({
                            "text": f"Healed {outcome.healed} HP",
                            "remaining": 3.0,
                        })
                    if ability.get("stats", {}).get("cast_type") == "nova":
                        ability_vfx.append({
                            "radius": float(ability.get("stats", {}).get("cast_radius", 0.5)),
                            "remaining": 0.2,
                            "element": ability.get("stats", {}).get("element", "arcane"),
                        })
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

                # Update quests, spawner, and progression
                quest_manager.register_time(run_elapsed_seconds)
                quest_manager.register_level(progress.level)
                spawner.spawn_delay_ms = enemy_scaling.spawn_delay_ms(
                    enemy_spawn_delay,
                    run_elapsed_seconds,
                )
                spawner.update(dt)
                if spawner.should_spawn():
                    spawner.spawn(
                        player.x,
                        player.y,
                        enemies,
                        elapsed_seconds=run_elapsed_seconds,
                        scaling=enemy_scaling,
                    )
                    spawner.reset()
                update_enemy_abilities(
                    enemies,
                    enemy_types,
                    dt,
                    player.x,
                    player.y,
                    pixels_per_unit=PIXELS_PER_UNIT,
                )

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
                        enemy.speed * 0.5,
                        enemy.turning_speed,
                        dt,
                    )
                enemy_projectiles.extend(
                    update_ranged_attacks(
                        enemies,
                        enemy_types,
                        dt,
                        player.x,
                        player.y,
                    )
                )
                enemy_projectiles = [
                    projectile
                    for projectile in enemy_projectiles
                    if not projectile.should_despawn(
                        player.x,
                        player.y,
                        (SCREEN_WIDTH / 2 / PIXELS_PER_UNIT) * 1.5,
                    )
                ]
                for projectile in enemy_projectiles:
                    projectile.move(dt)
                enemy_projectiles, projectile_damage = (
                    collision_system.check_enemy_projectile_player_collisions(
                        enemy_projectiles,
                        player,
                        bonuses["defense"],
                    )
                )
                for damage in projectile_damage:
                    notifications.items.append({
                        "text": f"Enemy shot: -{damage} HP",
                        "remaining": 1.5,
                    })

                # Check collisions
                bullets, enemies = collision_system.check_bullet_enemy_collisions(
                    bullets,
                    enemies,
                    enemy_types,
                )
<<<<<<< HEAD
                for _enemy in [*ability_kills, *collision_system.killed_enemies]:
                    if not _enemy.reward_eligible:
                        continue
                    absolute_score += LargeNumber(10) * LargeNumber(_enemy.score_multiplier)
                    if _enemy.currency_drop and _enemy.currency_amount > 0:
                        currency, amount = wallet.reward_for_enemy(
                            _enemy.currency_drop,
                            _enemy.currency_amount,
                            luck=bonuses["luck"],
                            multiplier=_enemy.score_multiplier,
                        )
                    else:
                        currency, amount = wallet.reward_for_kill(luck=bonuses["luck"])
=======
                for _enemy in collision_system.killed_enemies:
                    run_score.award(LargeNumber(10) * _enemy.reward_multiplier)
                    currency, amount = wallet.reward_for_kill(
                        luck=bonuses["luck"], reward_multiplier=_enemy.reward_multiplier
                    )
>>>>>>> birch/projectile-collision-effects
                    notifications.add(currency, amount)
                    quest_manager.register_kill(getattr(_enemy, "type", None))
                    award_enemy_kill(
                        progress,
                        _enemy.xp_reward,
                        multiplier=_enemy.score_multiplier,
                    )
                    quest_manager.register_level(progress.level)
                settings.mission_score_bonus_pct = quest_manager.total_bonus_pct()
                player = collision_system.check_enemy_player_collisions(
                    enemies,
                    player,
                    enemy_types,
                    bonuses["defense"],
                )

                # Check game over
                if not player.is_alive():
                    game_state.change_state(GameState.GAME_OVER)
                    try:
                        save_path.unlink(missing_ok=True)
                    except OSError as exc:
                        menu_error = f"Could not remove completed run save: {exc}"[:180]
                    else:
                        save_available = False

                # Update player rotation
                player.set_rotation(
                    renderer.get_mouse_position(),
                    renderer.screen_width,
                    renderer.screen_height,
                )

                # Prepare game state for rendering
<<<<<<< HEAD
                settings.mission_score_bonus_pct = quest_manager.total_bonus_pct()
                relic_summary = relic_effect_summary(inventory)
=======
                preview = (
                    _combination_preview(combination_engine, inventory, renderer.selected_base_id)
                    if renderer.menu_tab == "upgrades" and renderer.upgrade_tab == "combination"
                    else None
                )
>>>>>>> birch/projectile-collision-effects
                game_state_dict = {
                    "player": player,
                    "bullets": bullets,
                    "enemy_projectiles": enemy_projectiles,
                    "enemies": enemies,
                    "enemy_types": enemy_types,
<<<<<<< HEAD
                    "absolute_score": absolute_score,
                    "total_score": absolute_score.scale_by_percent(settings.mission_score_bonus_pct),
                    "infinity_milestone_reached": has_reached_infinity_milestone(
                        absolute_score.scale_by_percent(settings.mission_score_bonus_pct)
                    ),
=======
                    "absolute_score": str(run_score.base_score),
                    "total_score": str(run_score.total_score),
>>>>>>> birch/projectile-collision-effects
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
<<<<<<< HEAD
                    "speed": 1 + bonuses["speed_pct"] / 100,
                    "run_elapsed_ms": int(run_elapsed_seconds * 1000),
                    "threat_level": enemy_scaling.threat_level,
                    "enemy_scale": enemy_scaling.multiplier(run_elapsed_seconds).to_eng_string(),
=======
                    "speed": speed_multiplier,
>>>>>>> birch/projectile-collision-effects
                    "weapon_cooldowns": weapon_cooldowns,
                    "ability_cooldowns": ability_cooldowns,
                    "ability_vfx": ability_vfx,
                    "spawn_catalog": spawn_catalog,
<<<<<<< HEAD
                    "bazaar": _bazaar_view_state(
                        bazaar_manager,
                        inventory,
                        wallet,
                        bonuses["luck"],
                        run_elapsed_seconds,
                    ),
                    "fusion_recipes": fusion_manager.all_recipes(),
                    "fusion_unlocked": fusion_manager.is_unlocked(progress.level),
                    "fusion_unlock_level": fusion_manager.UNLOCK_LEVEL,
                    "quests": quest_manager.to_state(),
                    "quest_bonus_pct": settings.mission_score_bonus_pct,
                    "relics": relic_summary["items"],
                    "relic_summary": relic_summary["summary"],
                    "armor_set_status": armor_set_status(inventory),
=======
                    "difficulty_level": spawner.difficulty_level,
                    "active_scaling_time": spawner.scaling.active_time_seconds,
                    "combined_item": preview,
>>>>>>> birch/projectile-collision-effects
                }

                renderer.draw(game_state_dict)

                if run_elapsed_seconds - last_save_seconds >= autosave_interval_seconds:
                    persist_run()

            elif game_state.is_menu():
                renderer.draw_menu(
                    menu_error,
                    resume_available=save_available and save_path.is_file(),
                )
            elif game_state.is_settings():
                renderer.draw_settings()
            elif game_state.is_game_over():
                final_score = absolute_score.scale_by_percent(
                    quest_manager.total_bonus_pct()
                )
                renderer.draw_game_over({
                    "score": final_score,
                    "infinity_milestone_reached": has_reached_infinity_milestone(
                        final_score
                    ),
                    "runtime": run_elapsed_seconds,
                    "level": progress.level,
                    "luck": player_bonuses(inventory)["luck"],
                    "upload_status": upload_status,
                    "upload_complete": upload_complete,
                })
            elif game_state.is_playing():
                bonuses=player_bonuses(inventory)
<<<<<<< HEAD
                settings.mission_score_bonus_pct = quest_manager.total_bonus_pct()
                relic_summary = relic_effect_summary(inventory)
                total_score = absolute_score.scale_by_percent(settings.mission_score_bonus_pct)
                renderer.draw({"player": player, "bullets": bullets, "enemy_projectiles": enemy_projectiles, "enemies": enemies, "enemy_types": enemy_types,
                               "absolute_score": absolute_score, "total_score": total_score,
                               "infinity_milestone_reached": has_reached_infinity_milestone(total_score),
                               "currency": wallet.amounts,
                               "notifications": notifications.items, "paused": paused, "actions": actions,
                               "items":inventory.items,"active_slots":inventory.active_slots,"level":progress.level,
                               "experience":progress.current_exp,"next_level_exp":progress.exp_to_next_level,
                               "total_experience":progress.total_exp,"luck":bonuses["luck"],"speed":1 + bonuses["speed_pct"] / 100,
                               "run_elapsed_ms":int(run_elapsed_seconds * 1000),"threat_level":enemy_scaling.threat_level,
                               "enemy_scale":enemy_scaling.multiplier(run_elapsed_seconds).to_eng_string(),
                               "weapon_cooldowns":weapon_cooldowns,"ability_cooldowns":ability_cooldowns,"spawn_catalog":spawn_catalog,
                               "ability_vfx":ability_vfx,
                               "bazaar": _bazaar_view_state(
                                   bazaar_manager,
                                   inventory,
                                   wallet,
                                   bonuses["luck"],
                                   run_elapsed_seconds,
                               ),
                               "fusion_recipes": fusion_manager.all_recipes(),
                               "fusion_unlocked": fusion_manager.is_unlocked(progress.level),
                               "fusion_unlock_level": fusion_manager.UNLOCK_LEVEL,
                               "quests": quest_manager.to_state(), "quest_bonus_pct": settings.mission_score_bonus_pct,
                               "relics": relic_summary["items"], "relic_summary": relic_summary["summary"],
                               "armor_set_status": armor_set_status(inventory)})
=======
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
>>>>>>> birch/projectile-collision-effects

    finally:
        if game_state.is_playing():
            persist_run()
        renderer.close()


if __name__ == "__main__":
    main()
