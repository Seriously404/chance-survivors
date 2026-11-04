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
from game.systems.currency_economy import gamble_rarity, exchange_currency
from game.systems.inventory import Inventory
from game.systems.progression import PlayerProgress, award_enemy_kill
from game.systems.items import (
    armor_set_status,
    create_initial_inventory,
    player_bonuses,
    spawnable_items,
)
from game.systems.numbers import LargeNumber
from game.utils.large_number import LargeNumber as CombatNumber
from game.systems.quests import QuestManager
from game.systems.elemental_core import core_for_item, tick_lingering, armor_core_resistance
from game.systems.trails import TrailSystem
from game.systems.relics import relic_effect_summary
from game.systems.weapons import projectiles_for_weapon
from game.systems.bazaar import BazaarManager, build_extended_catalog, CRATE_LUCK_REQUIREMENTS
from game.systems.bazaar_service import BazaarService
from game.systems.fusion import FusionManager
from game.systems.enemy_scaling import EnemyScaling
from game.systems.enemy_catalog import build_enemy_roster
from game.systems.enemy_abilities import update_enemy_abilities
from game.systems.enemy_ranged import update_ranged_attacks
from game.systems.abilities import ability_cooldown, cast_ability
from game.systems.combinations import CombinationEngine
from game.systems.items import effective_ability
from game.ability_scripts.effects import update_summons
from game.systems.leaderboard_client import build_run_submission, submit_run
from game.systems.run_save import RunSave, configured_save_path
from game.systems.score_milestone import has_reached_infinity_milestone
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

    def crate_view(crate):
        items, weights = manager.crate_odds(crate, luck)
        total = sum(weights)
        return {
            "id": crate.id, "name": crate.name, "cost": crate.cost,
            "currency": crate.currency, "costs": crate.costs,
            "bias": crate.bias, "description": crate.description,
            "element": crate.element,
            "rewards": [{**item, "chance": weight / total if total else 0.0,
                         "time_locked": manager.rarity_rank(item.get("rarity", "common")) >= manager.rarity_rank("epic") and elapsed_seconds < 900,
                         "luck_required": CRATE_LUCK_REQUIREMENTS[manager.rarity_rank(item.get("rarity", "common"))]}
                        for item, weight in zip(items, weights)],
        }

    return {
        "crates": [
            crate_view(crate)
            for crate in manager.crates
        ],
        "can_refresh_crates": can_refresh,
        "crate_refresh_seconds": seconds_to_rotation,
        "daily_refresh_seconds": 60 - int(elapsed_seconds % 60),
        "crate_count": len(manager.available_crates(elapsed_seconds)),
        "crate_catalog_size": len(manager.crate_catalog),
        "next_crate_unlock_seconds": next_unlock_seconds,
        "catalog": [
            {**item, "market_price": manager.catalog_price(item)}
            for item in manager.catalog
            if item.get("type") == "relic" and not item.get("fusion_only")
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


def main() -> None:
    """Main game loop."""
    # Initialize systems
    renderer = Renderer(SCREEN_WIDTH, SCREEN_HEIGHT, PIXELS_PER_UNIT)
    bullet_types = load_bullet_types()
    weapon_cooldowns = [0.0, 0.0]
    ability_cooldowns = [0.0] * 10
    ability_vfx: list[dict[str, object]] = []
    summons = []
    trails = TrailSystem()
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
    absolute_score = LargeNumber(0)
    quest_manager = QuestManager()
    settings.mission_score_bonus_pct = quest_manager.total_bonus_pct()
    game_state = GameStateManager()
    collision_system = CollisionSystem(PIXELS_PER_UNIT)
    spawner = SpawnerSystem(enemy_types, enemy_spawn_delay)
    enemy_scaling = EnemyScaling()

    # Initialize game entities
    player = Player(health=player_max_health, max_health=player_max_health)
    applied_health_bonus = 0
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
        summons.clear()
        trails.reset()
        player.health = CombatNumber(saved["player"]["health"])
        player.max_health = CombatNumber(saved["player"]["max_health"])
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
                    menu_error = ""
                    game_state.change_state(GameState.INTRODUCTION)
                elif "settings" in actions or "open_settings" in actions:
                    game_state.change_state(GameState.SETTINGS)
                elif "codex" in actions:
                    renderer.codex_tab, renderer.codex_page, renderer.codex_selected = 'guide', 0, None
                    game_state.change_state(GameState.CODEX)
                elif "exit" in actions:
                    running = False

            elif game_state.state == GameState.CODEX:
                if 'back' in actions:
                    game_state.change_state(GameState.MENU)
                for action in actions:
                    if action.startswith('codex_tab:'):
                        renderer.codex_tab = action.split(':', 1)[1]
                        renderer.codex_page, renderer.codex_selected = 0, None
                    elif action == 'codex_prev':
                        renderer.codex_page = max(0, renderer.codex_page - 1)
                    elif action == 'codex_next':
                        renderer.codex_page += 1
                    elif action.startswith('codex_select:'):
                        renderer.codex_selected = int(action.split(':', 1)[1])

            elif game_state.is_introduction():
                if "back" in actions:
                    menu_error = ""
                    game_state.change_state(GameState.MENU)
                elif "start_run" in actions or "confirm" in actions:
                    try:
                        save_path.unlink(missing_ok=True)
                    except OSError as exc:
                        menu_error = f"Could not replace the previous run save: {exc}"[
                            :180]
                        continue
                    save_available = False
                    player, bullets, spawner = reset_game(
                        player, bullets, spawner)
                    enemy_projectiles.clear()
                    summons.clear()
                    trails.reset()
                    renderer.reset_timer()
                    enemy_spawn_timer = 0
                    run_elapsed_seconds = 0.0
                    enemy_scaling = EnemyScaling()
                    ability_vfx = []
                    absolute_score = LargeNumber(0)
                    wallet = CurrencyWallet()
                    notifications = CurrencyNotifications()
                    notifications.items.append(
                        {"text": "Earn Copper, then open Bazaar for a crate. Accept quests in the quest menu.", "remaining": 9.0})
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
                    player.max_health = player_max_health + \
                        int(bonuses["health"])
                    player.health = player.max_health
                    applied_health_bonus = int(bonuses["health"])
                    paused = False
                    menu_error = ""
                    upload_status = "Upload is optional; your score is not sent unless you choose Upload."
                    upload_complete = False
                    game_state.start_game(renderer.get_player_name())
                    last_save_seconds = -autosave_interval_seconds

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
                if "pause" in actions:
                    paused = not paused
                for panel in ("inventory", "quests", "upgrades", "bazaar"):
                    if panel in actions:
                        game_state.open_panel(panel)
                        renderer.menu_tab = "overview" if panel == "upgrades" else panel
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
                            notifications.items.append(
                                {"text": str(exc), "remaining": 3.0})
                        else:
                            spawn_counter = next_counter
                            crate = next(
                                entry for entry in bazaar_manager.crates if entry.id == crate_id)
                            renderer.start_crate_roll(
                                reward, bazaar_manager.crate_rewards(crate))
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
                            notifications.items.append(
                                {"text": str(exc), "remaining": 3.0})
                        else:
                            spawn_counter = next_counter
                            notifications.items.append({
                                "text": f"Bought {item.get('name', 'market item')}",
                                "remaining": 3.0,
                            })
                    elif action.startswith("bazaar_gamble:"):
                        _, item_id, target, encoded = action.split(":", 3)
                        try:
                            pool = {name: int(amount) for name, amount in
                                    (part.split("=", 1) for part in encoded.split(",") if part)}
                            upgraded = gamble_rarity(inventory.get(item_id), target, pool, wallet, bazaar_manager.rng,
                                                     elapsed_seconds=run_elapsed_seconds, luck=bonuses["luck"])
                        except (ValueError, KeyError) as exc:
                            notifications.items.append(
                                {"text": str(exc), "remaining": 3.0})
                        else:
                            message = "Rarity increased!" if upgraded else "Upgrade failed; pool spent."
                            notifications.items.append(
                                {"text": message, "remaining": 3.0})
                    elif action.startswith("bazaar_exchange:"):
                        _, source, destination, amount = action.split(":", 3)
                        try:
                            received = exchange_currency(
                                wallet, source, destination, int(amount))
                        except ValueError as exc:
                            notifications.items.append(
                                {"text": str(exc), "remaining": 3.0})
                        else:
                            notifications.items.append(
                                {"text": f"Received {received} {destination}", "remaining": 3.0})
                    elif action.startswith("bazaar_upgrade:"):
                        item_id = action.split(":", 1)[1]
                        try:
                            if bazaar_manager.rarity_rank(inventory.get(item_id).get('rarity', 'common')) >= 2 and run_elapsed_seconds < 900:
                                raise ValueError(
                                    'Epic and higher upgrades unlock after 15 minutes.')
                            if inventory.get(item_id).get('rarity') == 'mythical' and (run_elapsed_seconds < 1800 or bonuses['luck'] < 20):
                                raise ValueError(
                                    'Ultimate upgrades require 30 minutes and 20 luck.')
                            upgraded = bazaar_service.upgrade_rarity(
                                item_id,
                                wallet=wallet,
                                inventory=inventory,
                                luck=bonuses["luck"],
                            )
                        except ValueError as exc:
                            notifications.items.append(
                                {"text": str(exc), "remaining": 3.0})
                        else:
                            message = "Rarity increased!" if upgraded else "Rarity upgrade failed."
                            notifications.items.append(
                                {"text": message, "remaining": 3.0})
                    elif action.startswith("bazaar_level:"):
                        item_id = action.split(":", 1)[1]
                        try:
                            bazaar_service.upgrade_level(
                                item_id,
                                wallet=wallet,
                                inventory=inventory,
                            )
                        except ValueError as exc:
                            notifications.items.append(
                                {"text": str(exc), "remaining": 3.0})
                        else:
                            notifications.items.append(
                                {"text": "Item level increased!", "remaining": 3.0})
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
                            notifications.items.append(
                                {"text": str(exc), "remaining": 3.0})
                        else:
                            notifications.items.append({
                                "text": f"Sold for {value} Gold",
                                "remaining": 3.0,
                            })
                    elif action.startswith("fusion_craft:"):
                        _, recipe_id, source_ids = action.split(":", 2)
                        try:
                            recipe = fusion_manager.recipe_by_id(recipe_id)
                            if progress.level < recipe.unlock_level:
                                raise ValueError(
                                    f"{recipe.name} unlocks at player level {recipe.unlock_level}.")
                            if bazaar_manager.rarity_rank(recipe.output_rarity) >= 3 and run_elapsed_seconds < 900:
                                raise ValueError(
                                    'Epic and higher fusions unlock after 15 minutes.')
                            if recipe.output_rarity == 'ultimate' and run_elapsed_seconds < 1800:
                                raise ValueError(
                                    'Ultimate fusions unlock after 30 minutes.')
                            ids = source_ids.split(",") if source_ids else []
                            sources = [next((item for item in inventory.items if str(
                                item.get("id")) == item_id), None) for item_id in ids]
                            if any(item is None or item.get("status") in {"active", "supplement", "combination_base"} for item in sources):
                                raise ValueError(
                                    "Ingredients must be unequipped inventory items.")
                            fusion_manager.validate_sources(sources, recipe)
                            result = inventory.fuse_items(
                                [item["id"] for item in sources],
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
                            renderer.fusion_last_result = result
                            renderer.fusion_sources = []
                            notifications.items.append({
                                "text": f"Created {result['name']}",
                                "remaining": 3.0,
                            })
                    elif action.startswith("tab_"):
                        renderer.menu_tab = action[4:]
                        game_state.open_panel("upgrades" if renderer.menu_tab in (
                            "overview", "combination") else renderer.menu_tab)
                    elif action.startswith("upgrade_"):
                        renderer.upgrade_tab = action[8:]
                    elif action.startswith("quest_accept:"):
                        equipped_ids = {item_id for slots in inventory.active_slots.values()
                                        for item_id in slots if item_id is not None}
                        equipped_ids.update(sid for item_id in tuple(equipped_ids)
                                            for sid in inventory.get(item_id).get("combinations", []) if sid is not None)
                        if not quest_manager.accept(action.split(":", 1)[1], [inventory.get(i) for i in equipped_ids]):
                            notifications.items.append(
                                {"text": "Cannot accept: check equipped items and quest limits.", "remaining": 3.0})
                    elif action == "quest_decline_main":
                        quest_manager.decline_main_quest()
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
                        equipped_items = [inventory.get(
                            item_id) for item_id in equipped_ids]
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
                        notifications.items.append(
                            {"text": message, "remaining": 3.0})
                    elif action.startswith("select:"):
                        renderer.selected_item_id = action.split(":", 1)[1]
                    elif action.startswith("combine:"):
                        _, base_id, combo_index, item_id = action.split(":", 3)
                        try:
                            if not quest_manager.can_equip(inventory.get(item_id)):
                                raise ValueError(
                                    "Main quest restrictions prevent using this item.")
                            inventory.assign_combination(
                                base_id, int(combo_index), item_id)
                        except (KeyError, IndexError, ValueError) as exc:
                            notifications.items.append(
                                {"text": str(exc), "remaining": 3.0})
                    elif action.startswith("equip:"):
                        _, slot_kind, slot_index, item_id = action.split(
                            ":", 3)
                        try:
                            item = inventory.get(item_id)
                            if not quest_manager.can_equip(item) or any(
                                not quest_manager.can_equip(inventory.get(sid))
                                for sid in item.get("combinations", []) if sid is not None
                            ):
                                raise ValueError(
                                    "Main quest restrictions prevent equipping this item.")
                            inventory.equip(item_id, slot_kind,
                                            int(slot_index))
                        except (KeyError, IndexError, ValueError) as exc:
                            notifications.items.append(
                                {"text": str(exc), "remaining": 3.0})
                    elif action.startswith("uncombine:"):
                        _, base_id, combo_index = action.split(":", 2)
                        try:
                            inventory.assign_combination(
                                base_id, int(combo_index), None)
                        except (KeyError, IndexError, ValueError):
                            pass
                    elif action.startswith("unequip:"):
                        _, slot_kind, slot_index = action.split(":", 2)
                        try:
                            inventory.unequip(slot_kind, int(slot_index))
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
                    final_score = quest_manager.final_score(absolute_score)
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
                player.update_shield(dt)
                ability_vfx = [
                    {**effect, "remaining": float(effect["remaining"]) - dt}
                    for effect in ability_vfx
                    if float(effect["remaining"]) > dt
                ]
                bonuses = player_bonuses(inventory)
                relic_summary = relic_effect_summary(inventory)
                current_health_bonus = int(bonuses["health"])
                if current_health_bonus != applied_health_bonus:
                    player.max_health = player_max_health+current_health_bonus
                    player.health = max(0, min(
                        player.max_health, player.health+current_health_bonus-applied_health_bonus))
                    applied_health_bonus = current_health_bonus
                weapon_cooldowns = [max(0.0, value-dt)
                                    for value in weapon_cooldowns]
                ability_cooldowns = [max(
                    0.0, value-dt * (4.0 if player.time_shift_remaining > 0 else 1.0)) for value in ability_cooldowns]
                clicks = {0: None, 1: None}
                for button, position in renderer.input_handler.fire_events:
                    if button == 1:
                        clicks[0] = position
                    elif button == 3:
                        clicks[1] = position
                by_id = {str(item["id"]): item for item in inventory.items}
                ability_kills = []
                player_dx, player_dy = renderer.get_movement()
                dash_slot = next((i for i, item_id in enumerate(inventory.active_slots["abilities"])
                                  if item_id and by_id.get(str(item_id), {}).get("stats", {}).get("script") in {"dash", "sandevistan"}), None)
                cast_actions = list(actions)
                if "dash" in actions:
                    if dash_slot is None:
                        player.start_dash(player_dx, player_dy)
                    else:
                        cast_actions.append(f"ability_cast:{dash_slot}")
                for action in cast_actions:
                    if not action.startswith("ability_cast:"):
                        continue
                    try:
                        ability_index = int(action.split(":", 1)[1])
                    except ValueError:
                        continue
                    if not 0 <= ability_index < len(ability_cooldowns):
                        continue
                    ability_id = inventory.active_slots["abilities"][ability_index]
                    ability = by_id.get(
                        str(ability_id)) if ability_id else None
                    if ability is None or ability_cooldowns[ability_index] > 0:
                        continue
                    angle = renderer.aim_angle(
                        renderer.get_mouse_position(), player.x, player.y)
                    effective_cast = effective_ability(inventory, ability)
                    cooldown = ability_cooldown(effective_cast)
                    script = ability.get("stats", {}).get("script")
                    if script in {"dash", "sandevistan"}:
                        from game.systems.items import item_stat
                        distance = min(6.0, max(0.1, item_stat(
                            effective_cast, "dash_distance", 2.0)))
                        duration = float(ability.get(
                            "stats", {}).get("dash_duration", 0.18))
                        shift = float(ability.get("stats", {}).get(
                            "time_shift_duration", 6.0)) if script == "sandevistan" else 0.0
                        if player.start_dash(player_dx, player_dy, distance=distance, duration=duration,
                                             cooldown=cooldown, time_shift=shift):
                            ability_cooldowns[ability_index] = cooldown
                        continue
                    outcome = cast_ability(
                        effective_cast,
                        player,
                        enemies,
                        angle=angle,
                        base_speed=bullet_base_speed,
                        enemy_types=enemy_types,
                        damage_bonus_pct=bonuses["damage_pct"],
                        core=core_for_item(inventory, ability),
                    )
                    if not outcome.consumed:
                        continue
                    ability_cooldowns[ability_index] = cooldown
                    if outcome.projectile is not None:
                        bullets.append(outcome.projectile)
                    if outcome.summon is not None:
                        summons.append(outcome.summon)
                    ability_kills.extend(outcome.killed_enemies)
                    if outcome.healed:
                        notifications.items.append({
                            "text": f"Healed {outcome.healed} HP",
                            "remaining": 3.0,
                        })
                    if ability.get("stats", {}).get("script", ability.get("stats", {}).get("cast_type")) in {"nova", "void"}:
                        ability_vfx.append({
                            "radius": float(ability.get("stats", {}).get("cast_radius", 0.5)),
                            "remaining": 0.2,
                            "element": ability.get("stats", {}).get("element", "arcane"),
                        })
                for slot_index, button in enumerate((1, 3)):
                    weapon_id = inventory.active_slots["weapons"][slot_index]
                    weapon = by_id.get(str(weapon_id)) if weapon_id else None
                    if weapon is None:
                        continue
                    weapon_stats = weapon.get("stats", {}) if weapon else {}
                    type_name = weapon_stats.get(
                        "bullet_type", ("rapid_fire", "heavy_shot")[slot_index])
                    definition = bullet_types.get(str(type_name))
                    if definition is None:
                        continue
                    automatic = bool(weapon_stats.get(
                        "automatic", definition.automatic))
                    fire_position = clicks[slot_index]
                    if fire_position is None and automatic and button in renderer.input_handler.mouse_buttons_held:
                        fire_position = renderer.get_mouse_position()
                    if fire_position is None or weapon_cooldowns[slot_index] > 0:
                        continue
                    player_angle = renderer.aim_angle(
                        fire_position, player.x, player.y)
                    effective_weapon = (CombinationEngine().evaluate_inventory(inventory, weapon_id)
                                        if any(weapon.get("combinations", [])) else weapon)
                    volley, cooldown, _ = projectiles_for_weapon(
                        player, player_angle, effective_weapon, slot_index, bullet_types,
                        bullet_base_speed, bonuses["damage_pct"])
                    for projectile in volley:
                        projectile.elemental_core = core_for_item(
                            inventory, weapon)
                    bullets.extend(volley)
                    weapon_cooldowns[slot_index] = cooldown

                # Update quests, spawner, and progression
                quest_manager.register_time(run_elapsed_seconds)
                quest_manager.register_level(progress.level)
                spawner.spawn_delay_ms = enemy_scaling.spawn_delay_ms(
                    enemy_spawn_delay,
                    run_elapsed_seconds,
                )
                world_dt = dt * \
                    (0.2 if player.time_shift_remaining > 0 else 1.0)
                spawner.update(world_dt)
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
                    world_dt,
                    player.x,
                    player.y,
                    pixels_per_unit=PIXELS_PER_UNIT,
                )

                # Get player movement
                player.update_dash(dt)
                if player.dash_remaining <= 0:
                    player.move(player_dx, player_dy, dt, (1+bonuses["speed_pct"]/100) * (
                        2 if player.time_shift_remaining > 0 else 1))

                # Update bullets
                bullets.extend(update_summons(summons, enemies,
                               player, dt, bullet_base_speed))
                for ally in summons:
                    trails.emit(ally, dt)
                despawn_distance = (SCREEN_WIDTH / 2 / PIXELS_PER_UNIT) * 1.5
                bullets = [
                    bullet for bullet in bullets
                    if not bullet.should_despawn(player.x, player.y, despawn_distance)
                ]
                for bullet in bullets:
                    if bullet.homing_strength > 0:
                        bullet.steer_towards(enemies, dt)
                    bullet.move(dt)
                    trails.emit(bullet, dt)

                # Update enemies
                for enemy in enemies:
                    enemy.move_towards_player(
                        player.x,
                        player.y,
                        enemy.speed * 0.5,
                        enemy.turning_speed,
                        world_dt,
                    )
                enemy_projectiles.extend(
                    update_ranged_attacks(
                        enemies,
                        enemy_types,
                        world_dt,
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
                    projectile.move(world_dt)
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
                ability_kills.extend(tick_lingering(
                    enemies, world_dt, enemy_types))
                ability_kills.extend(trails.update(
                    enemies, enemy_types, world_dt))
                bullets, enemies = collision_system.check_bullet_enemy_collisions(
                    bullets,
                    enemies,
                    enemy_types,
                    player,
                )
                for _enemy in [*ability_kills, *collision_system.killed_enemies]:
                    if not _enemy.reward_eligible:
                        continue
                    absolute_score += LargeNumber(10) * \
                        LargeNumber(_enemy.score_multiplier)
                    if _enemy.currency_drop and _enemy.currency_amount > 0:
                        currency, amount = wallet.reward_for_enemy(
                            _enemy.currency_drop,
                            _enemy.currency_amount,
                            luck=bonuses["luck"],
                            multiplier=_enemy.score_multiplier,
                        )
                    else:
                        currency, amount = wallet.reward_for_kill(
                            luck=bonuses["luck"], multiplier=_enemy.score_multiplier)
                    notifications.add(currency, amount)
                    if currency != "Gold":
                        gold = wallet.gold_bonus_for_kill(luck=bonuses["luck"])
                        if gold > 0:
                            notifications.add("Gold", gold)
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
                    armor_core_resistance(inventory),
                )

                # Check game over
                if not player.is_alive():
                    game_state.change_state(GameState.GAME_OVER)
                    try:
                        save_path.unlink(missing_ok=True)
                    except OSError as exc:
                        menu_error = f"Could not remove completed run save: {exc}"[
                            :180]
                    else:
                        save_available = False

                # Update player rotation
                player.angle = renderer.aim_angle(
                    renderer.get_mouse_position(), player.x, player.y)

                # Prepare game state for rendering
                settings.mission_score_bonus_pct = quest_manager.total_bonus_pct()
                relic_summary = relic_effect_summary(inventory)
                game_state_dict = {
                    "player": player,
                    "bullets": bullets,
                    "enemy_projectiles": enemy_projectiles,
                    "enemies": enemies,
                    "enemy_types": enemy_types,
                    "absolute_score": absolute_score,
                    "total_score": quest_manager.final_score(absolute_score),
                    "infinity_milestone_reached": has_reached_infinity_milestone(
                        quest_manager.final_score(absolute_score)
                    ),
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
                    "speed": 1 + bonuses["speed_pct"] / 100,
                    "run_elapsed_ms": int(run_elapsed_seconds * 1000),
                    "threat_level": enemy_scaling.threat_level,
                    "enemy_scale": enemy_scaling.multiplier(run_elapsed_seconds).to_eng_string(),
                    "weapon_cooldowns": weapon_cooldowns,
                    "ability_cooldowns": ability_cooldowns,
                    "ability_vfx": ability_vfx,
                    "summons": summons,
                    "trails": trails.trails,
                    "spawn_catalog": spawn_catalog,
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
                }

                renderer.draw(game_state_dict)

                if run_elapsed_seconds - last_save_seconds >= autosave_interval_seconds:
                    persist_run()

            elif game_state.is_menu():
                renderer.draw_menu(
                    menu_error,
                    resume_available=save_available and save_path.is_file(),
                )
            elif game_state.is_introduction():
                renderer.draw_introduction(
                    menu_error, save_available and save_path.is_file())
            elif game_state.state == GameState.CODEX:
                codex_crates = []
                for crate in bazaar_manager.crate_catalog:
                    items, weights = bazaar_manager.crate_odds(crate, 1.0)
                    total = sum(weights)
                    codex_crates.append({'name': crate.name, 'description': crate.description,
                                         'costs': crate.costs, 'bias': crate.bias,
                                         'unlock_seconds': crate.unlock_seconds,
                                         'rewards': [(item.get('name', 'Item'), weight/total if total else 0)
                                                     for item, weight in zip(items, weights)]})
                renderer.draw_codex(bazaar_manager.catalog,
                                    fusion_manager.all_recipes(), codex_crates)
            elif game_state.is_settings():
                renderer.draw_settings()
            elif game_state.is_game_over():
                final_score = quest_manager.final_score(absolute_score)
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
                bonuses = player_bonuses(inventory)
                settings.mission_score_bonus_pct = quest_manager.total_bonus_pct()
                relic_summary = relic_effect_summary(inventory)
                total_score = quest_manager.final_score(absolute_score)
                renderer.draw({"player": player, "bullets": bullets, "enemy_projectiles": enemy_projectiles, "enemies": enemies, "enemy_types": enemy_types,
                               "absolute_score": absolute_score, "total_score": total_score,
                               "infinity_milestone_reached": has_reached_infinity_milestone(total_score),
                               "currency": wallet.amounts,
                               "notifications": notifications.items, "paused": paused, "actions": actions,
                               "items": inventory.items, "active_slots": inventory.active_slots, "level": progress.level,
                               "experience": progress.current_exp, "next_level_exp": progress.exp_to_next_level,
                               "total_experience": progress.total_exp, "luck": bonuses["luck"], "speed": 1 + bonuses["speed_pct"] / 100,
                               "run_elapsed_ms": int(run_elapsed_seconds * 1000), "threat_level": enemy_scaling.threat_level,
                               "enemy_scale": enemy_scaling.multiplier(run_elapsed_seconds).to_eng_string(),
                               "weapon_cooldowns": weapon_cooldowns, "ability_cooldowns": ability_cooldowns, "spawn_catalog": spawn_catalog,
                               "ability_vfx": ability_vfx,
                               "summons": summons,
                               "trails": trails.trails,
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

    finally:
        if game_state.is_playing():
            persist_run()
        renderer.close()


if __name__ == "__main__":
    main()
