import math
import re
from game.systems.json_loader import load_json_asset

import pygame

from client.input import InputHandler
from client.tutorial import INTRO_PAGES
from client.ui_guidance import GuidanceUI
from game.systems.elements import ELEMENTS, element_label, normalize_element
from game.systems.enemy_visibility import enemy_visibility_alpha
from game.utils.large_number import LargeNumber
from game.systems.currency_economy import currency_affinity, currency_definition, exchange_quote, rarity_chance
from game.systems.bazaar import RARITY_ORDER
from game.systems.currency import CURRENCY_DEFINITIONS


class Renderer(GuidanceUI):
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
            (screen_width, screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("Chance Survivors")

        self.font = pygame.font.Font(None, 20)
        self.currency_font = pygame.font.SysFont("symbola,dejavusans", 24)
        names = sorted(
            (entry['name'] for entry in CURRENCY_DEFINITIONS.values()), key=len, reverse=True)
        self._currency_pattern = re.compile(
            r'(?<!\w)(' + '|'.join(map(re.escape, names)) + r')(?!\w)')
        self.clock = pygame.time.Clock()

        self.bullet_size = (16, 6)
        self.bullet_color = (255, 220, 50)

        self.start_time = pygame.time.get_ticks()

        # Input handler
        self.input_handler = InputHandler()
        pygame.key.start_text_input()
        self.mode = "MENU"
        self.panel = None
        self.resolutions = [(800, 450), (1280, 720), (1600, 900), (1920, 1080)]
        self.resolution_index = 0
        self.fullscreen = False
        self.bonus_pct = 0
        self._buttons = {}
        self._item_rects = {}
        self._hover_slots = []
        self._tutorial_capture = False
        self._drop_targets = {}
        self._inventory_rect = None
        self._name_entry = None
        self.currency_offset = 0
        self.quest_offsets = {"main": 0, "side": 0}
        self.quest_scroll_positions = {"main": 0.0, "side": 0.0}
        self._scroll_regions = {}
        self._scroll_positions = {}
        self.menu_tab = "inventory"
        self.upgrade_tab = "overview"
        self.selected_item_id = None
        self.selected_base_id = None
        self.inventory_scroll = 0
        self.inventory_scroll_target = 0.0
        self.bazaar_market_scroll = 0.0
        self.bazaar_market_scroll_target = 0.0
        self.bazaar_owned_scroll = 0.0
        self.bazaar_owned_scroll_target = 0.0
        self.bazaar_crates_scroll = 0.0
        self.bazaar_crates_scroll_target = 0.0
        self._crate_roll = None
        self._bazaar_tab = "market"
        self._rarity_pool = {}
        self._rarity_currency = 0
        self._rarity_target = 0
        self._exchange_source = 0
        self._exchange_destination = 1
        self._exchange_amount = 1
        self._exchange_scroll = 0
        self._currency_drag_rects = {}
        self._exchange_slots = {}
        self._sliders = {}
        self._rarity_dropdown_open = False
        self._rarity_dropdown_scroll = 0
        self._frame_dt = 1 / 60
        self._camera = None
        self._enemy_health_seen = {}
        self._enemy_crits_seen = {}
        self._damage_feedback = []
        self._player_health_seen = None
        self._damage_flash_remaining = 0.0
        self.codex_tab = 'guide'
        self.intro_page = 0
        self.codex_page = 0
        self.codex_selected = None
        self.codex_detail_page = 0
        self._drag_item_id = None
        self._drop_targets = {}
        self._rarity_icon_cache = {}
        self.item_icons = load_json_asset('item_icons.json')
        self._drag_origin = None
        self.fusion_recipe_id = None
        self.fusion_sources = []
        self.fusion_codex = False
        self.fusion_catalog_scroll = 0

    def process_events(self) -> tuple[bool, list[tuple[float, float]], list[str]]:
        """Process all pygame events.

        Returns:
            Tuple of (running, shots, actions).
        """
        running, shots, actions = self.input_handler.process_events(
            self.mode, self._name_entry)
        captured = self._guidance_input(running, shots, actions)
        if captured is not None:
            return captured
        if self._tutorial_capture and (self.input_handler.click_release is not None
                                       or self.input_handler.drag_release is not None):
            self.input_handler.click_release = None
            self.input_handler.drag_release = None
            self._tutorial_capture = False
        if self.mode == "PLAYING" and self.panel == "bazaar":
            for pos in shots:
                self._update_economy_slider(pos, pos)
            if self.input_handler.drag_active and self.input_handler.drag_start:
                self._update_economy_slider(
                    self.input_handler.drag_start, self.input_handler.mouse_position)
            if self.input_handler.drag_release:
                start, end = self.input_handler.drag_release
                self._update_economy_slider(start, end)
                if self._bazaar_tab == "exchange":
                    source = next((name for name, rect in self._currency_drag_rects.items(
                    ) if rect.collidepoint(start)), None)
                    slot = next((name for name, rect in self._exchange_slots.items(
                    ) if rect.collidepoint(end)), None)
                    names = list(self._last_state.get(
                        "bazaar", {}).get("wallet", {}))
                    if source in names and slot:
                        if slot == "source":
                            self._exchange_source = names.index(source)
                            self._exchange_amount = 0
                        else:
                            self._exchange_destination = names.index(source)
                    self.input_handler.drag_release = None
        dragged_this_frame = self.input_handler.drag_release is not None
        current_size = self.screen.get_size()
        if current_size != (self.screen_width, self.screen_height):
            self.screen_width, self.screen_height = current_size
        for pos in shots:
            tutorial_button = next((name for name in ("tutorial_skip", "tutorial_next")
                                    if name in self._buttons and self._buttons[name].collidepoint(pos)), None)
            if tutorial_button:
                actions.append(tutorial_button)
                self._tutorial_capture = self.input_handler.click_release is None
                self.input_handler.click_release = None
                continue
            for name, rect in self._buttons.items():
                if rect.collidepoint(pos):
                    actions.append(name)
            if self.mode == "PLAYING" and self.panel:
                for slot_key, rect in self._drop_targets.items():
                    if rect.collidepoint(pos):
                        if slot_key.startswith("item:"):
                            actions.append(
                                f"select:{slot_key.split(':', 1)[1]}")
                        break
        if self.mode == "PLAYING" and self.panel in ("inventory", "upgrades", "bazaar") and self.input_handler.click_release:
            released_at = self.input_handler.click_release
            for name, rect in self._item_rects.items():
                if rect.collidepoint(released_at):
                    actions.append(f"select:{name}")
                    break
            self.input_handler.click_release = None
        if self.mode == "PLAYING" and self.panel and self.input_handler.drag_active:
            source_pos = self.input_handler.drag_start
            self._drag_item_id = next((item_id for item_id, rect in self._item_rects.items(
            ) if rect.collidepoint(source_pos)), None)
        if self.mode == "PLAYING" and self.panel and self.input_handler.drag_release:
            source_pos, target_pos = self.input_handler.drag_release
            actions = [action for action in actions if not action.startswith(
                ("combine:", "equip:"))]
            source_item = next((item_id for item_id, rect in self._item_rects.items(
            ) if rect.collidepoint(source_pos)), None)
            target = next((key for key, rect in self._drop_targets.items(
            ) if rect.collidepoint(target_pos)), None)
            source_slot = next((key for key, rect in self._drop_targets.items(
            ) if rect.collidepoint(source_pos)), None)
            # Visual feedback for valid/invalid drops
            if self.upgrade_tab == "combination" and source_item and target and target.startswith("combo:"):
                _, base_id, combo_index = target.split(":", 2)
                base_item = next((item for item in self._last_state.get(
                    "items", []) if str(item.get("id")) == base_id), None)
                if base_item:
                    # Check if item can be used as supplement
                    supplement = next((item for item in self._last_state.get(
                        "items", []) if str(item.get("id")) == source_item), None)
                    valid_drop = bool(
                        supplement and self._is_valid_combination_supplement(base_item, supplement))
                    if valid_drop:
                        # Draw green highlight on valid drop target
                        target_rect = self._drop_targets.get(target)
                        if target_rect:
                            pygame.draw.rect(
                                self.screen, (100, 255, 100), target_rect, 2, border_radius=3)
                    else:
                        # Draw red highlight on invalid drop target
                        target_rect = self._drop_targets.get(target)
                        if target_rect:
                            pygame.draw.rect(
                                self.screen, (255, 100, 100), target_rect, 2, border_radius=3)
            if source_item and target:
                if target.startswith("fusion_slot:"):
                    index = int(target.split(":", 1)[1])
                    if source_item not in self.fusion_sources:
                        while len(self.fusion_sources) <= index:
                            self.fusion_sources.append(None)
                        self.fusion_sources[index] = source_item
                elif target.startswith("combo:"):
                    _, base_id, combo_index = target.split(":", 2)
                    actions.append(
                        f"combine:{base_id}:{combo_index}:{source_item}")
                else:
                    slot_kind, slot_index = target.split(":", 1)
                    actions.append(
                        f"equip:{slot_kind}:{slot_index}:{source_item}")
            elif source_slot and source_slot.startswith("fusion_slot:"):
                index = int(source_slot.split(":", 1)[1])
                if index < len(self.fusion_sources):
                    self.fusion_sources[index] = None
            elif source_slot and target and not source_slot.startswith("combo:") and not target.startswith("combo:"):
                source_kind, source_index = source_slot.split(":", 1)
                target_kind, target_index = target.split(":", 1)
                source_ids = self._last_state.get(
                    "active_slots", {}).get(source_kind, [])
                source_item = source_ids[int(source_index)] if int(
                    source_index) < len(source_ids) else None
                if source_item:
                    actions.append(
                        f"equip:{target_kind}:{target_index}:{source_item}")
            elif source_slot and source_slot.startswith("combo:") and not (target and target.startswith("combo:")):
                _, base_id, combo_index = source_slot.split(":", 2)
                actions.append(f"uncombine:{base_id}:{combo_index}")
            elif source_slot and source_slot.startswith("combo:") and target and target.startswith("combo:"):
                _, source_base, source_index = source_slot.split(":", 2)
                source_item_id = None
                for item in self._last_state.get("items", []):
                    if item.get("id") == source_base:
                        source_item_id = item.get("combinations", [])[
                            int(source_index)]
                        break
                if source_item_id:
                    _, base_id, combo_index = target.split(":", 2)
                    actions.append(
                        f"combine:{base_id}:{combo_index}:{source_item_id}")
            elif source_slot and self._inventory_rect and self._inventory_rect.collidepoint(target_pos):
                slot_kind, slot_index = source_slot.split(":", 1)
                actions.append(f"unequip:{slot_kind}:{slot_index}")
            self.input_handler.drag_release = None
            self._drag_item_id = None
        for action in actions:
            if action == "context_help":
                self._context_help_key = self._menu_help_key()
                self._context_help_page = 0
            elif action == "codex_detail_prev":
                self.codex_detail_page = max(0, self.codex_detail_page - 1)
            elif action == "codex_detail_next":
                self.codex_detail_page += 1
            elif self.mode == "CODEX" and action in ("inventory_up", "inventory_down"):
                direction = -1 if action == "inventory_up" else 1
                if self.input_handler.mouse_position[0] >= 350:
                    self.codex_detail_page = max(0, self.codex_detail_page + direction)
                else:
                    actions.append("codex_prev" if direction < 0 else "codex_next")
            elif (action.startswith(("codex_select:", "codex_tab:"))
                  or action in ("codex_prev", "codex_next")):
                self.codex_detail_page = 0
            elif action == "fusion_codex":
                self.fusion_codex = not self.fusion_codex
            elif action.startswith("fusion_select:"):
                self.fusion_recipe_id = action.split(":", 1)[1]
                self.fusion_sources = []
                self.fusion_codex = False
            elif action.startswith("fusion_remove:"):
                index = int(action.split(":", 1)[1])
                if index < len(self.fusion_sources):
                    self.fusion_sources[index] = None
            elif action.startswith("tab_"):
                self.menu_tab = action[4:]
            elif action.startswith("upgrade_"):
                self.upgrade_tab = action[8:]
            elif action.startswith("bazaar_tab_"):
                self._bazaar_tab = action[11:]
            elif action.startswith("bazaar_crate_select:"):
                self.selected_crate_id = action.split(":", 1)[1]
                self.bazaar_rewards_scroll = 0
            elif action == "crate_roll_skip" and self._crate_roll:
                if self._crate_roll["elapsed"] < 3.0:
                    self._crate_roll["elapsed"] = 3.0
                else:
                    self._crate_roll = None
            elif action in ("bazaar_rewards_up", "bazaar_rewards_down"):
                self.bazaar_rewards_scroll = max(0, getattr(
                    self, "bazaar_rewards_scroll", 0) + (1 if action.endswith("down") else -1))
            elif action in ("fusion_catalog_up", "fusion_catalog_down"):
                self.fusion_catalog_scroll = max(0, getattr(
                    self, "fusion_catalog_scroll", 0) + (1 if action.endswith("down") else -1))
            elif action.startswith("quest_scroll:"):
                _, kind, direction = action.split(":")
                self.quest_offsets[kind] = max(
                    0, self.quest_offsets[kind] + int(direction))
            elif action.startswith("rarity_ui_"):
                wallet = list(self._last_state.get(
                    "bazaar", {}).get("wallet", {}))
                if wallet:
                    op = action[10:]
                    if op == "prev":
                        self._rarity_currency = (
                            self._rarity_currency - 1) % len(wallet)
                    elif op == "dropdown":
                        self._rarity_dropdown_open = not self._rarity_dropdown_open
                    elif op.startswith("choose:"):
                        self._rarity_currency = int(
                            op.split(":", 1)[1]) % len(wallet)
                        self._rarity_dropdown_open = False
                    elif op == "next":
                        self._rarity_currency = (
                            self._rarity_currency + 1) % len(wallet)
                    elif op == "target":
                        self._rarity_target += 1
                    elif op in ("add1", "add10", "remove1", "clear"):
                        name = wallet[self._rarity_currency % len(wallet)]
                        value = self._rarity_pool.get(name, 0)
                        if op == "clear":
                            value = 0
                        elif op == "remove1":
                            value = max(0, value - 1)
                        else:
                            value = min(int(
                                self._last_state["bazaar"]["wallet"][name]), value + (10 if op == "add10" else 1))
                        self._rarity_pool[name] = value
            elif action.startswith("exchange_ui_"):
                wallet = list(self._last_state.get(
                    "bazaar", {}).get("wallet", {}))
                if wallet:
                    op = action[12:]
                    if op == "source":
                        self._exchange_source = (
                            self._exchange_source + 1) % len(wallet)
                    elif op == "destination":
                        self._exchange_destination = (
                            self._exchange_destination + 1) % len(wallet)
                    elif op == "add1":
                        self._exchange_amount += 1
                    elif op == "add10":
                        self._exchange_amount += 10
                    elif op == "remove1":
                        self._exchange_amount = max(
                            1, self._exchange_amount - 1)
                    elif op == "all":
                        self._exchange_amount = max(
                            1, int(self._last_state["bazaar"]["wallet"][wallet[self._exchange_source]]))
            elif action.startswith("bazaar_gamble:"):
                self._rarity_pool = {}
            elif action.startswith("select:"):
                self.selected_item_id = action.split(":", 1)[1]
                self.bazaar_detail_scroll = 0
                if (self.panel and self.menu_tab == "combination"
                        and self.upgrade_tab == "combination" and not dragged_this_frame):
                    item = next((entry for entry in getattr(self, "_last_state", {}).get("items", [])
                                 if str(entry.get("id")) == self.selected_item_id), None)
                    if item and item.get("type") in ("armor", "weapon", "ability"):
                        self.selected_base_id = self.selected_item_id
            elif action in ("inventory_up", "inventory_down") and not self.panel:
                direction = -1 if action == "inventory_up" else 1
                rect = self._scroll_regions.get("hud_currency")
                if rect and rect.collidepoint(self.input_handler.mouse_position):
                    self.currency_offset = max(0, self.currency_offset + direction)
            elif action in ("inventory_up", "inventory_down") and self.panel:
                direction = -1 if action == "inventory_up" else 1
                self._scroll_at(self.input_handler.mouse_position, direction)
            elif action == "bazaar_market_up" and self.panel:
                self.bazaar_market_scroll_target = max(
                    0.0, self.bazaar_market_scroll_target - 1)
            elif action == "bazaar_market_down" and self.panel:
                self.bazaar_market_scroll_target += 1
            elif action == "bazaar_crates_up" and self.panel:
                self.bazaar_crates_scroll_target = max(
                    0.0, self.bazaar_crates_scroll_target - 1)
            elif action == "bazaar_crates_down" and self.panel:
                self.bazaar_crates_scroll_target += 1
            elif action == "currency_up" and self.panel:
                self.inventory_scroll_target = max(
                    0, self.inventory_scroll_target-3)
            elif action == "currency_down" and self.panel:
                self.inventory_scroll_target += 3
        if self.mode != "PLAYING" or self.panel:
            self.input_handler.fire_events = []
            self.input_handler.mouse_buttons_held.clear()
            self.input_handler.held_fire = False
        else:
            ui_buttons = [button for button, pos in self.input_handler.fire_events
                          if any(rect.collidepoint(pos) for rect in self._buttons.values())]
            for button in ui_buttons:
                self.input_handler.mouse_buttons_held.discard(button)
            self.input_handler.held_fire = bool(
                self.input_handler.mouse_buttons_held)
            self.input_handler.fire_events = [
                (button, pos) for button, pos in self.input_handler.fire_events
                if button not in ui_buttons
            ]
        shots = [] if self.mode != "PLAYING" or self.panel else shots
        return running, shots, actions

    def set_view(self, mode: str, panel=None):
        if mode != self.mode:
            self.input_handler.reset()
            self.input_handler.name_focused = mode == "MENU"
            if mode == "MENU":
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
        self.mode, self.panel = mode, panel

    def get_player_name(self):
        return self.input_handler.player_name.strip()

    def set_player_name(self, name: str) -> None:
        self.input_handler.player_name = name

    def set_resolution(self, index):
        self.resolution_index = index % len(self.resolutions)

    def apply_display(self):
        self.screen_width, self.screen_height = self.resolutions[self.resolution_index]
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), flags)

    def get_movement(self) -> tuple[float, float]:
        """Get player movement."""
        return self.input_handler.get_movement()

    def get_mouse_position(self) -> tuple[float, float]:
        """Get mouse position."""
        return self.input_handler.get_mouse_position()

    def tick(self, framerate):
        self._frame_dt = min(0.1, self.clock.tick(framerate) / 1000.0)
        return self._frame_dt

    def get_elapsed_ms(self):
        return pygame.time.get_ticks() - self.start_time

    def get_fps(self):
        return self.clock.get_fps()

    def reset_timer(self):
        self.start_time = pygame.time.get_ticks()
        self._camera = None
        self._enemy_health_seen.clear()
        self._enemy_crits_seen.clear()
        self._damage_feedback.clear()
        self._player_health_seen = None
        self._damage_flash_remaining = 0.0

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

    def aim_angle(self, mouse_position, player_x, player_y):
        camera = self._camera or (player_x, player_y)
        x, y = self.world_to_screen(player_x, player_y, *camera)
        return math.atan2(y - mouse_position[1], mouse_position[0] - x)

    def cursor_world(self, player_x, player_y):
        camera_x, camera_y = self._camera or (player_x, player_y)
        x, y = self.get_mouse_position()
        return (camera_x + (x - self.screen_width / 2) / self.pixels_per_unit,
                camera_y - (y - self.screen_height / 2) / self.pixels_per_unit)

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
                (55, 55, 55),
                (x, 0),
                (x, self.screen_height),
                2
            )

        for y in range(int(offset_y), self.screen_height, spacing):
            pygame.draw.line(
                self.screen,
                (55, 55, 55),
                (0, y),
                (self.screen_width, y),
                2
            )

    def draw_player(self, angle, health, max_health, position=None, shield=0):
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

        center_x, center_y = position or (
            self.screen_width // 2, self.screen_height // 2)

        rect = rotated.get_rect(center=(center_x, center_y))
        self.screen.blit(rotated, rect)
        if LargeNumber(shield) > 0:
            pygame.draw.circle(self.screen, (115, 205, 250), (int(center_x), int(center_y)), player_size // 2 + 7, 2)

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
            stats = enemy_types[enemy.type]
            size = stats["size"]
            opacity = enemy_visibility_alpha(
                math.hypot(enemy.x - player_x, enemy.y - player_y),
                stats,
            )

            enemy_surface = pygame.Surface(
                (size, size),
                pygame.SRCALPHA
            )

            pygame.draw.rect(
                enemy_surface,
                stats.get("color", (220, 60, 60)),
                (0, 0, size, size)
            )
            enemy_surface.set_alpha(opacity)

            rotated = pygame.transform.rotate(
                enemy_surface,
                enemy.angle * 57.295779513
            )

            screen_position = self.world_to_screen(
                enemy.x,
                enemy.y,
                player_x,
                player_y
            )

            rect = rotated.get_rect(center=screen_position)
            self.screen.blit(rotated, rect)
            if opacity and enemy.health < enemy.max_health:
                self.draw_health_bar(
                    rect.centerx, rect.top - 9, enemy.health, enemy.max_health)

    def _draw_player_damage_feedback(self, player):
        health = LargeNumber(player.health)
        if self._player_health_seen is not None and health < self._player_health_seen:
            self._damage_flash_remaining = .3
        self._player_health_seen = health
        self._damage_flash_remaining = max(0.0, self._damage_flash_remaining - self._frame_dt)
        if self._damage_flash_remaining:
            strength = self._damage_flash_remaining / .3
            color = (round(110 + 100 * strength), 35, 40)
            pygame.draw.rect(self.screen, color, self.screen.get_rect(), max(2, round(6 * strength)))

    def _draw_defeat_feedback(self, effects, camera_x, camera_y):
        """Render a bounded world-space pulse for confirmed enemy defeats."""
        for effect in effects[-64:]:
            if effect["remaining"] <= 0:
                continue
            x, y = self.world_to_screen(effect["x"], effect["y"], camera_x, camera_y)
            progress = max(0.0, min(1.0, 1 - effect["remaining"] / .35))
            radius = max(2, int(5 + 18 * progress))
            color = tuple(round(value * (1 - progress * .65)) for value in (210, 235, 155))
            pygame.draw.circle(self.screen, color, (int(x), int(y)), radius, 2)

    def _draw_damage_feedback(self, enemies, camera_x, camera_y):
        """Show short, bounded damage popups without affecting simulation."""
        current = {}
        current_crits = {}
        for enemy in enemies:
            key = id(enemy)
            health = LargeNumber(enemy.health)
            critical_count = getattr(enemy, "critical_hit_count", 0)
            previous = self._enemy_health_seen.get(key)
            if previous is not None and health < previous:
                self._damage_feedback.append({
                    "x": enemy.x, "y": enemy.y, "amount": previous - health,
                    "remaining": 0.7,
                    "critical": critical_count > self._enemy_crits_seen.get(key, 0),
                })
            current[key] = health
            current_crits[key] = critical_count
        self._enemy_health_seen = current
        self._enemy_crits_seen = current_crits
        self._damage_feedback = self._damage_feedback[-50:]
        remaining = []
        for effect in self._damage_feedback:
            effect["remaining"] -= self._frame_dt
            if effect["remaining"] <= 0:
                continue
            remaining.append(effect)
            x, y = self.world_to_screen(effect["x"], effect["y"], camera_x, camera_y)
            age = 0.7 - effect["remaining"]
            critical = effect.get("critical", False)
            text = ("CRIT " if critical else "") + str(effect["amount"])
            color = (255, 150, 80) if critical else (255, 225, 145)
            label = self.font.render(text, True, color)
            label.set_alpha(max(0, min(255, int(effect["remaining"] / 0.7 * 255))))
            self.screen.blit(label, label.get_rect(center=(int(x), int(y - 30 - age * 25))))
        self._damage_feedback = remaining

    def _draw_ability_vfx(self, effects, center=None):
        center = center or (self.screen_width // 2, self.screen_height // 2)
        for effect in effects:
            remaining = max(0.0, min(0.2, float(effect.get("remaining", 0.0))))
            radius = max(
                1, int(float(effect.get("radius", 0.0)) * self.pixels_per_unit))
            color = ELEMENTS[normalize_element(
                str(effect.get("element", "arcane")))]["color"]
            overlay = pygame.Surface(
                (radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(
                overlay,
                (*color, int(180 * remaining / 0.2)),
                (radius + 2, radius + 2),
                radius,
                width=3,
            )
            self.screen.blit(
                overlay, (center[0] - radius - 2, center[1] - radius - 2))

    def _draw_ability_aim(self, state, center):
        held = self.input_handler.held_abilities
        if not held:
            return
        key = min(held)
        index = 9 if key == pygame.K_0 else key - pygame.K_1
        slots = state.get("active_slots", {}).get("abilities", [])
        if not 0 <= index < len(slots):
            return
        item = next((i for i in state.get("items", [])
                    if i.get("id") == slots[index]), None)
        if not item:
            return
        from game.systems.items import effective_ability, item_stat
        if any(item.get("combinations", [])):
            # Build a detached inventory so aiming uses the same combined stats
            # as the cast without changing live item status.
            from copy import deepcopy
            from game.systems.inventory import Inventory
            try:
                ids = {item["id"], *(value for value in item["combinations"] if value is not None)}
                detached = Inventory(deepcopy([entry for entry in state.get("items", []) if entry.get("id") in ids]))
                item = effective_ability(detached, detached.get(item["id"]))
            except (KeyError, TypeError, ValueError):
                pass
        stats = item.get("stats", {})
        script = stats.get("script", stats.get("cast_type", "projectile"))
        origin = (int(center[0]), int(center[1]))
        mouse = self.input_handler.mouse_position
        angle = math.atan2(mouse[1]-origin[1], mouse[0]-origin[0])
        if script in {"wall", "arc_turret", "flame_turret", "frost_turret", "turret"}:
            max_distance = self.pixels_per_unit * 3.5
            distance = min(max_distance, math.hypot(mouse[0] - origin[0], mouse[1] - origin[1]))
            target = (round(origin[0] + math.cos(angle) * distance),
                      round(origin[1] + math.sin(angle) * distance))
            color = (120, 235, 185)
            pygame.draw.line(self.screen, color, origin, target, 1)
            preview = pygame.Rect(target[0] - 16, target[1] - 12, 32, 24)
            pygame.draw.rect(self.screen, color, preview, 2, border_radius=3)
            self._text("Release to deploy", (preview.x - 30, preview.bottom + 6))
        elif script in {"repair_pulse", "overclock", "architect_protocol"}:
            pygame.draw.circle(self.screen, (100, 225, 190), origin,
                               round(3.5 * self.pixels_per_unit), 2)
        elif script == "teleport":
            distance = item_stat(item, "teleport_range",
                                 5) * self.pixels_per_unit
            dest = (int(origin[0]+math.cos(angle)*distance),
                    int(origin[1]+math.sin(angle)*distance))
            pygame.draw.line(self.screen, (170, 130, 255), origin, dest, 2)
            for dx, dy in ((-9, -9), (9, 9), (-9, 9), (9, -9)):
                pygame.draw.line(self.screen, (210, 180, 255),
                                 dest, (dest[0]+dx, dest[1]+dy), 2)
        elif script in ("nova", "void", "siphon"):
            pygame.draw.circle(self.screen, (255, 180, 90), origin, max(
                1, int(max(item_stat(item, "cast_radius", .5), item_stat(item, "area_radius", 0))*self.pixels_per_unit)), 2)
        elif script in ("projectile", "ember", "frost"):
            tip = (int(origin[0]+math.cos(angle)*95),
                   int(origin[1]+math.sin(angle)*95))
            pygame.draw.line(self.screen, (255, 220, 120), origin, tip, 3)
            for side in (-1, 1):
                end = (int(tip[0]-15*math.cos(angle+side*.5)),
                       int(tip[1]-15*math.sin(angle+side*.5)))
                pygame.draw.line(self.screen, (255, 220, 120), tip, end, 3)

    def draw_bullets(self, bullet_list, player_x, player_y):
        for bullet in bullet_list:
            element = normalize_element(getattr(bullet, "element", "physical"))
            color = ELEMENTS[element]["color"]
            bullet_surface = pygame.Surface(
                self.bullet_size,
                pygame.SRCALPHA
            )

            pygame.draw.rect(
                bullet_surface,
                color,
                (0, 0, self.bullet_size[0], self.bullet_size[1])
            )

            rotated = pygame.transform.rotate(
                bullet_surface,
                bullet.angle * 57.295779513
            )

            screen_position = self.world_to_screen(
                bullet.x,
                bullet.y,
                player_x,
                player_y
            )

            rect = rotated.get_rect(center=screen_position)
            self.screen.blit(rotated, rect)

    def draw_health_bar(self, center_x, top_y, current_health, max_health, width=40):
        height = 5

        if max_health <= 0:
            return

        ratio = current_health / max_health
        if isinstance(ratio, LargeNumber):
            health_ratio = min(1.0, max(0.0, ratio.to_float()))
        else:
            health_ratio = max(0.0, min(1.0, ratio))

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

    def draw_game_over(self, state: dict) -> None:
        """Show run results and make leaderboard upload an explicit choice."""
        self._buttons = {}
        self.screen.fill((24, 34, 28))
        center_x = self.screen_width // 2
        self.screen.blit(
            pygame.font.Font(None, 48).render(
                "Run Complete", True, (105, 235, 135)),
            (center_x - 118, 52),
        )
        lines = (
            f"Final score: {state.get('score', '0')}",
            f"Active time: {state.get('runtime', 0.0):.2f}s",
            f"Level: {state.get('level', 1)}    Luck: {state.get('luck', 0.0):.1f}",
        )
        for index, text in enumerate(lines):
            surface = self.font.render(text, True, (235, 240, 236))
            self.screen.blit(surface, surface.get_rect(
                center=(center_x, 138 + index * 28)))
        if state.get('end_reason'):
            label = self.font.render(state['end_reason'], True, (240, 185, 125))
            self.screen.blit(label, label.get_rect(center=(center_x, 212)))
        if state.get("infinity_milestone_reached", False):
            milestone = self.font.render(
                "INFINITY MILESTONE REACHED - SCORE IS FINITE",
                True,
                (105, 235, 135),
            )
            self.screen.blit(
                milestone,
                milestone.get_rect(center=(center_x, 106)),
            )
        status = str(state.get("upload_status", "Upload is optional."))
        status_color = (130, 235, 150) if status.startswith(
            "Submitted") else (240, 205, 120)
        max_status_width = self.screen_width - 48
        status_lines = []
        current_line = ""
        for word in status.split():
            candidate = f"{current_line} {word}".strip()
            if current_line and self.font.size(candidate)[0] > max_status_width:
                status_lines.append(current_line)
                current_line = word
            else:
                current_line = candidate
        if current_line:
            status_lines.append(current_line)
        for index, line in enumerate(status_lines[:3]):
            status_surface = self.font.render(line, True, status_color)
            self.screen.blit(status_surface, status_surface.get_rect(
                center=(center_x, 230 + index * 20)))
        upload_enabled = not state.get("upload_complete", False)
        if upload_enabled:
            self._button("upload_run", "Upload Score",
                         (center_x, 310), 190, 42)
        else:
            self._button("upload_done", "Uploaded", (center_x, 310), 190, 42)
        self._button("return_menu", "Return to Menu", (center_x, 366), 190, 42)
        pygame.display.flip()

    def _button(self, key, label, center, width=210, height=42):
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center
        self._buttons[key] = rect
        pygame.draw.rect(self.screen, (68, 68, 68), rect, border_radius=6)
        pygame.draw.rect(self.screen, (145, 145, 145),
                         rect, 2, border_radius=6)
        surf = self._currency_text_surface(label, (245, 245, 250))
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def draw_menu(self, error="", resume_available=False):
        self._buttons = {}
        self._item_rects = {}
        self.screen.fill((32, 32, 32))
        cx, cy = self.screen_width // 2, self.screen_height // 2
        self.screen.blit(pygame.font.Font(None, 48).render(
            "CHANCE SURVIVORS", True, (240, 220, 120)), (cx-185, max(24, cy-155)))
        label = self.font.render("Player name", True, (235, 235, 240))
        self.screen.blit(label, label.get_rect(center=(cx, cy-85)))
        self._name_entry = pygame.Rect(cx-140, cy-64, 280, 38)
        pygame.draw.rect(self.screen, (48, 48, 48),
                         self._name_entry, border_radius=4)
        pygame.draw.rect(self.screen, (140, 140, 140),
                         self._name_entry, 2, border_radius=4)
        name = self.input_handler.player_name or "Type your name..."
        self.screen.blit(self.font.render(name, True, (240, 240, 245)
                         if self.input_handler.player_name else (130, 135, 145)), (cx-128, cy-54))
        self._button("play", "Play", (cx, cy+8))
        if resume_available:
            self._button("resume_run", "Resume Run", (cx, cy+60))
        self._button("exit", "Exit",
                     (cx, cy+(112 if resume_available else 60)))
        self._button("codex", "Codex",
                     (cx, cy+(157 if resume_available else 105)), 210, 38)
        self._button("settings", "Settings",
                     (self.screen_width-75, 25), 130, 34)
        if error:
            message = self.font.render(error, True, (255, 110, 100))
            self.screen.blit(message, message.get_rect(
                center=(cx, cy+(160 if resume_available else 112))))
        pygame.display.flip()

    def draw_codex(self, catalog, recipes, crates):
        self._buttons = {}
        self._hover_slots = []
        self._item_rects = {}
        self.screen.fill((25, 32, 30))
        tabs = [('guide', 'Guide'), ('items', 'Items'),
                ('fusions', 'Fusions'), ('crates', 'Crates')]
        for index, (key, label) in enumerate(tabs):
            self._button('codex_tab:' + key, label,
                         (70 + index * 145, 28), 135, 36)
        self._button('back', 'Back', (self.screen_width-65, 28), 110, 36)
        if self.codex_tab == 'guide':
            self.codex_page = max(0, min(self.codex_page, len(INTRO_PAGES) - 1))
            heading, lines = INTRO_PAGES[self.codex_page]
            self._text(f"{heading}  ·  {self.codex_page + 1}/{len(INTRO_PAGES)}", (25, 65))
            rows = [(line, None) for text in lines
                    for line in self._codex_wrap(text, self.screen_width - 50)]
            self._draw_codex_rows(rows, 25, 95, self.screen_width - 50,
                                  navigation_center=self.screen_width - 200)
            self._button('codex_prev', 'Previous', (95, self.screen_height-25), 130, 30)
            self._button('codex_next', 'Next', (255, self.screen_height-25), 130, 30)
            pygame.display.flip()
            return
        entries = {'items': catalog, 'fusions': recipes,
                   'crates': crates}[self.codex_tab]
        page_size = max(1, (self.screen_height-130)//32)
        pages = max(1, (len(entries)+page_size-1)//page_size)
        self.codex_page = max(0, min(self.codex_page, pages-1))
        start = self.codex_page*page_size
        for index, entry in enumerate(entries[start:start+page_size]):
            name = entry.get('name', 'Item')
            while name and self.font.size(name)[0] > 280:
                name = name[:-2] + '…'
            self._button(f'codex_select:{start+index}',
                         name, (175, 85+index*32), 300, 29)
        self._button('codex_prev', 'Previous',
                     (95, self.screen_height-25), 130, 30)
        self._text(f'{self.codex_page+1} / {pages}',
                   (170, self.screen_height-33))
        self._button('codex_next', 'Next',
                     (255, self.screen_height-25), 130, 30)
        selected = self.codex_selected
        if selected is not None and 0 <= selected < len(entries):
            entry = entries[selected]
            x, y = 350, 78
            if self.codex_tab == 'crates':
                self._draw_codex_crate_details(entry, x, y)
                self._draw_item_tooltip({})
                pygame.display.flip()
                return
            lines = [entry.get('name', 'Item'), entry.get('description', '')]
            if self.codex_tab == 'items':
                lines += [
                    f"Type: {entry.get('type', '')}  |  Base rarity: {entry.get('rarity', '')}"]
            elif self.codex_tab == 'fusions':
                lines += ['Requires: ' + ', '.join(entry.get('required_elements') or entry.get('required_types', [])),
                          f"Unlock level: {entry.get('unlock_level', 1)}"]
            max_width = self.screen_width - x - 20
            rows = [(line, None) for text in lines
                    for line in self._codex_wrap(text, max_width - 8)]
            self._draw_codex_rows(rows, x, y, max_width)
        pygame.display.flip()

    def _codex_wrap(self, text, width):
        """Wrap descriptions, including a single word wider than the panel."""
        def text_width(value):
            return self._currency_text_surface(value, (240, 240, 245)).get_width()

        rows = []
        line = ""
        for word in str(text).split():
            while word and text_width(word) > width:
                if line:
                    rows.append(line)
                    line = ""
                end = len(word)
                while end > 1 and text_width(word[:end]) > width:
                    end -= 1
                rows.append(word[:end])
                word = word[end:]
            candidate = f"{line} {word}".strip()
            if line and text_width(candidate) > width:
                rows.append(line)
                line = word
            else:
                line = candidate
        if line:
            rows.append(line)
        return rows

    def _draw_codex_crate_details(self, entry, x, y):
        """Show complete rewards using the same weighted odds as crate purchase."""
        right = self.screen_width - 18
        width = right - x
        rows = []

        def add_wrapped(text):
            rows.extend((line, None) for line in self._codex_wrap(text, width - 8))

        # Keep the preview context visible on every page, even late reward pages.
        luck = entry.get('preview_luck', 1)
        context = f"Title preview · luck {luck:g} · live build odds may differ"
        for line in self._codex_wrap(context, width - 8):
            self._text(line, (x, y))
            y += 22
        add_wrapped(entry.get('name', 'Crate'))
        add_wrapped(entry.get('description', ''))
        add_wrapped("Cost: " + ", ".join(f"{value} {name}" for name, value
                                         in entry.get('costs', {}).items()))
        add_wrapped(f"Bias: {entry.get('bias', 'common')}. Availability rotates in the Bazaar.")
        add_wrapped("All possible rewards below. Hover an item for its effects.")
        add_wrapped("Rewards showing 0% need more luck, not more time.")
        rewards = entry.get('rewards', [])
        if not rewards:
            add_wrapped("No rewards available.")
        for reward in rewards:
            if isinstance(reward, dict):
                item = reward
                chance = reward.get('chance', 0)
            else:
                name, chance = reward
                item = {'name': name, 'type': 'item', 'rarity': 'common'}
            percentage = f"{chance * 100:.3g}%" if chance else "0%"
            name_lines = self._codex_wrap(item.get('name', 'Item'),
                                          width - 35 - self.font.size(percentage)[0])
            for index, line in enumerate(name_lines):
                rows.append(((line, percentage if index == 0 else ''), item))

        self._draw_codex_rows(rows, x, y, width)

    def _draw_codex_rows(self, rows, x, y, width, navigation_center=None):
        """Paginate complete text and item rows within the available viewport."""
        right = x + width

        row_height = 24
        visible = max(1, (self.screen_height - y - 60) // row_height)
        pages = max(1, (len(rows) + visible - 1) // visible)
        self.codex_detail_page = max(0, min(self.codex_detail_page, pages - 1))
        clip = pygame.Rect(x, y, width, visible * row_height)
        prior_clip = self.screen.get_clip()
        self.screen.set_clip(clip)
        start = self.codex_detail_page * visible
        for index, (label, item) in enumerate(rows[start:start + visible]):
            line_y = y + index * row_height
            if item:
                icon = pygame.Rect(x, line_y, 20, 20)
                self._draw_rarity_icon(item, icon)
                self._register_item_hover(pygame.Rect(x, line_y, width, 22), item)
                name, percentage = label
                self._text(name, (x + 25, line_y + 2))
                self._text(percentage, (right - self.font.size(percentage)[0] - 3, line_y + 2))
            else:
                self._text(label, (x, line_y + 2))
        self.screen.set_clip(prior_clip)
        center = navigation_center if navigation_center is not None else x + width // 2
        self._button('codex_detail_prev', 'Previous', (center - 125, self.screen_height - 25), 105, 30)
        self._text(f'{self.codex_detail_page + 1} / {pages}', (center - 18, self.screen_height - 33))
        self._button('codex_detail_next', 'Next', (center + 125, self.screen_height - 25), 105, 30)

    def draw_introduction(self, error="", replacing_save=False):
        """Explain the controls and the opening choices before a new run."""
        self._buttons = {}
        self.screen.fill((25, 30, 36))
        width, height = self.screen_width, self.screen_height
        title = pygame.font.Font(None, 38).render(
            "READY TO SURVIVE?", True, (245, 220, 130))
        self.screen.blit(title, title.get_rect(center=(width // 2, 30)))
        self.intro_page = max(0, min(self.intro_page, len(INTRO_PAGES) - 1))
        heading, lines = INTRO_PAGES[self.intro_page]
        card = pygame.Rect(32, 58, width - 64, max(190, height - 170))
        pygame.draw.rect(self.screen, (38, 48, 55), card, border_radius=8)
        pygame.draw.rect(self.screen, (100, 145, 151), card, 2, border_radius=8)
        self._text(f"{heading}  ·  {self.intro_page + 1}/{len(INTRO_PAGES)}", (card.x + 14, card.y + 12))
        y = card.y + 42
        for line in lines:
            current = ""
            for word in line.split():
                candidate = f"{current} {word}".strip()
                if current and self.font.size(candidate)[0] > card.width - 34:
                    self._text(current, (card.x + 16, y)); y += 21
                    current = word
                else:
                    current = candidate
            if current:
                self._text(current, (card.x + 16, y)); y += 28
        if self.intro_page:
            self._button("intro_prev", "Previous", (width // 2 - 90, height - 78), 150, 30)
        if self.intro_page < len(INTRO_PAGES) - 1:
            self._button("intro_next", "Next", (width // 2 + 90, height - 78), 150, 30)
        if replacing_save and not error:
            text = "Starting a new run replaces your saved run."
            warning = self.font.render(text, True, (255, 190, 135))
            self.screen.blit(warning, warning.get_rect(
                center=(width // 2, height - 108)))
        if error:
            message = self.font.render(error, True, (255, 120, 110))
            self.screen.blit(message, message.get_rect(
                center=(width // 2, height - 108)))
        self._button("back", "Back", (width // 2 - 120, height - 32), 180, 38)
        self._button("start_run", "Start Run",
                     (width // 2 + 120, height - 32), 180, 38)
        pygame.display.flip()

    def draw_settings(self):
        self._buttons = {}
        self.screen.fill((32, 32, 32))
        cx, cy = self.screen_width//2, self.screen_height//2
        self.screen.blit(pygame.font.Font(None, 42).render(
            "Settings", True, (240, 220, 120)), (cx-70, cy-130))
        w, h = self.resolutions[self.resolution_index]
        self._button("resolution", f"Resolution: {w} × {h}", (cx, cy-45), 300)
        self._button(
            "fullscreen", f"Display: {'Fullscreen' if self.fullscreen else 'Windowed'}", (cx, cy+5), 300)
        self._button("apply_settings", "Apply", (cx, cy+65))
        self._button("back", "Back", (cx, cy+117))
        pygame.display.flip()

    def draw(self, state: dict) -> None:
        """Draw the current game state.

        Args:
            state: Dictionary containing player, bullets, enemies, and enemy_types.
        """
        self._last_state = state
        self.screen.fill((30, 30, 30))
        if self._draw_main_quest_choice(state.get("main_quest_choice")):
            pygame.display.flip()
            return

        if self.panel:
            self._draw_game_menu(state)
            self._draw_item_tooltip(state)
            self._draw_drag_ghost(state)
            self._draw_notifications(state)
            self._draw_run_tutorial(state.get("tutorial"))
            self._draw_context_help()
            pygame.display.flip()
            return

        player = state["player"]
        bullets = state["bullets"]
        enemies = state["enemies"]
        enemy_types = state["enemy_types"]

        if self._camera is None:
            self._camera = (player.x, player.y)
        blend = 1.0 - math.exp(-6.0 * self._frame_dt)
        self._camera = tuple(a + (b-a)*blend for a,
                             b in zip(self._camera, (player.x, player.y)))
        camera_x, camera_y = self._camera
        player_screen = self.world_to_screen(
            player.x, player.y, camera_x, camera_y)
        self.draw_grid(camera_x, camera_y)
        self.draw_player(player.angle, player.health,
                         player.max_health, player_screen, player.shield)
        self.draw_bullets(bullets, camera_x, camera_y)
        self.draw_enemy_projectiles(
            state.get("enemy_projectiles", []),
            camera_x,
            camera_y,
        )
        self._draw_ability_vfx(state.get("ability_vfx", []), player_screen)
        for trail in state.get("trails", []):
            x, y = self.world_to_screen(trail.x, trail.y, camera_x, camera_y)
            color = ELEMENTS[normalize_element(trail.element)]["color"]
            pygame.draw.circle(self.screen, color, (int(x), int(y)), max(
                2, int(self.pixels_per_unit * .12)), 2)
        for ally in state.get("summons", []):
            if getattr(ally, "structure_kind", "summon") != "summon":
                continue
            x, y = self.world_to_screen(ally.x, ally.y, camera_x, camera_y)
            pygame.draw.circle(self.screen, (100, 220, 255) if ally.mobile else (
                230, 190, 100), (int(x), int(y)), 8)
        self.draw_enemies(enemies, enemy_types, camera_x, camera_y)
        self._draw_engineering(state.get("engineering"), camera_x, camera_y)
        self._draw_defeat_feedback(state.get("defeat_vfx", []), camera_x, camera_y)
        self._draw_damage_feedback(enemies, camera_x, camera_y)
        self._draw_player_damage_feedback(player)
        self._draw_ability_aim(state, player_screen)
        self._draw_game_ui(state)
        self._draw_item_tooltip(state)
        self._draw_run_tutorial(state.get("tutorial"))

        pygame.display.flip()

    def _draw_run_tutorial(self, tutorial):
        if not tutorial:
            return
        width = min(490, self.screen_width - 24)
        card = pygame.Rect((self.screen_width - width) // 2,
                           self.screen_height - 125, width, 76)
        pygame.draw.rect(self.screen, (20, 29, 35), card, border_radius=7)
        pygame.draw.rect(self.screen, (105, 195, 185), card, 2, border_radius=7)
        self._text(f"Practice {tutorial['step']}/{tutorial['total']} · {tutorial['title']}",
                   (card.left + 10, card.top + 7))
        words = tutorial["text"].split()
        line = ""
        y = card.top + 27
        for word in words:
            candidate = f"{line} {word}".strip()
            if line and self.font.size(candidate)[0] > width - 110:
                self._text(line, (card.left + 10, y))
                line, y = word, y + 18
            else:
                line = candidate
        if line:
            self._text(line, (card.left + 10, y))
        self._button("tutorial_next", "Next", (card.right - 47, card.top + 23), 75, 24)
        self._button("tutorial_skip", "Skip", (card.right - 47, card.top + 53), 75, 24)

    def draw_enemy_projectiles(self, projectiles, player_x, player_y):
        for projectile in projectiles:
            x, y = self.world_to_screen(
                projectile.x,
                projectile.y,
                player_x,
                player_y,
            )
            radius = max(3, int(projectile.radius))
            pygame.draw.circle(self.screen, (255, 95, 55),
                               (int(x), int(y)), radius)
            pygame.draw.circle(self.screen, (255, 220, 150),
                               (int(x), int(y)), max(1, radius // 2))

    def _draw_game_menu(self, state):
        self._buttons = {}
        self._item_rects = {}
        self._hover_slots = []
        self._drop_targets = {}
        self._scroll_regions = {}
        self.screen.fill((24, 24, 24))
        pygame.draw.rect(self.screen, (42, 42, 42),
                         (0, 0, self.screen_width, 50))
        tabs = [("inventory", "Inventory"), ("quests", "Quests"), ("overview",
                                                                   "Overview"), ("combination", "Combination"), ("bazaar", "Bazaar")]
        tab_width = min(160, (self.screen_width-172)//len(tabs))
        for i, (key, label) in enumerate(tabs):
            active = self.menu_tab == key
            self._button(f"tab_{key}", label, (12+i *
                         tab_width+tab_width//2, 25), tab_width-8, 38)
            if active:
                pygame.draw.line(self.screen, (225, 225, 225),
                                 (12+i*tab_width+8, 47), (12+(i+1)*tab_width-16, 47), 3)
        self._button("close_menu", "Close", (self.screen_width-48, 25), 82, 36)
        self._button("context_help", "Help", (self.screen_width-125, 25), 58, 36)
        pygame.draw.line(self.screen, (125, 125, 125),
                         (0, 50), (self.screen_width, 50), 1)
        top = 58
        outer = pygame.Rect(10, top, self.screen_width -
                            20, self.screen_height-top-10)
        pygame.draw.rect(self.screen, (34, 34, 34), outer, border_radius=8)
        pygame.draw.rect(self.screen, (95, 95, 95), outer, 1, border_radius=8)
        if self.menu_tab == "inventory":
            self._draw_inventory_menu(state, outer)
        elif self.menu_tab == "quests":
            self._draw_quests_menu(outer, state)
        elif self.menu_tab in ("overview", "combination"):
            self.upgrade_tab = self.menu_tab
            self._draw_upgrades_menu(state, outer)
        else:
            self._draw_bazaar_menu(outer, state)

    def _draw_inventory_menu(self, state, outer):
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        active = state.get("active_slots", {})
        content_top, content_bottom = outer.top+8, outer.bottom-10
        panel_height = content_bottom-content_top
        stats_width = max(155, int(outer.width*.23))
        inventory_left = outer.right-int(outer.width*.43)
        stats_rect = pygame.Rect(
            outer.left+10, content_top, stats_width, panel_height)
        gear_width = max(170, inventory_left-stats_rect.right-16)
        gear_rect = pygame.Rect(
            stats_rect.right+8, content_top, gear_width, panel_height)
        grid_rect = pygame.Rect(
            inventory_left, content_top, outer.right-inventory_left-10, panel_height)
        self._inventory_rect = grid_rect.copy()
        self._scroll_regions["inventory"] = grid_rect.copy()
        for rect in (stats_rect, gear_rect, grid_rect):
            pygame.draw.rect(self.screen, (48, 48, 48), rect, border_radius=5)
            pygame.draw.rect(self.screen, (100, 100, 100),
                             rect, 1, border_radius=5)
        self._text("Item details", (stats_rect.left+8, stats_rect.top+8))
        selected = by_id.get(str(self.selected_item_id))
        if selected:
            self._draw_item_details(
                selected, stats_rect.left+8, stats_rect.top+35, stats_rect.width-16)
        else:
            self._text("Select an item",
                       (stats_rect.left+8, stats_rect.top+38))
        self._text("Equipment", (gear_rect.left+8, gear_rect.top+8))
        y = gear_rect.top+27
        armor_size = min(52, (gear_rect.width-16-16)//5)
        self._text("Armor", (gear_rect.left+8, y))
        y += 19
        values = active.get("armor", [])
        armor_labels = ("Boots", "Pants", "Chest", "Head", "Acc.")
        armor_label_font = pygame.font.Font(None, 14)
        for i in range(5):
            slot_x = gear_rect.left+8+i*(armor_size+4)
            label = armor_label_font.render(
                armor_labels[i], True, (205, 205, 210))
            self.screen.blit(label, label.get_rect(
                midtop=(slot_x+armor_size//2, y)))
            self._draw_active_slot(f"armor:{i}", values[i] if i < len(values) else None, by_id,
                                   (slot_x, y+12), armor_size, armor_size)
        y += armor_size+21
        set_stats = {}
        for armor_set in state.get("armor_set_status", []):
            set_bonuses = armor_set.get("active_bonuses", {})
            for threshold, bonuses in set_bonuses.items():
                if int(threshold) <= armor_set.get("pieces", 0):
                    for stat_name, value in bonuses.items():
                        set_stats[stat_name] = set_stats.get(
                            stat_name, 0) + value
        active_set_names = [
            f"{entry.get('name', entry.get('id', 'Set'))} "
            f"{entry.get('pieces', 0)}/4"
            for entry in state.get("armor_set_status", [])
        ]
        if active_set_names:
            compact_stats = {
                "defense": "DEF",
                "health": "HP",
                "speed_pct": "SPD",
                "luck": "LUCK",
                "damage_pct": "DMG",
                "crit_chance": "CRIT",
                "score_bonus_pct": "SCORE",
            }
            bonus_text = " ".join(
                f"{compact_stats.get(name, name)}{value:+g}"
                for name, value in sorted(set_stats.items())
                if value
            )
            status_text = ", ".join(active_set_names[:2])
            if bonus_text:
                status_text = f"{status_text}: {bonus_text}"
            small_font = pygame.font.Font(None, 17)
            max_status_width = gear_rect.width - 16
            was_truncated = small_font.size(status_text)[0] > max_status_width
            while status_text and small_font.size(status_text + "...")[0] > max_status_width:
                status_text = status_text[:-1]
            if was_truncated:
                status_text = status_text.rstrip(" ,:") + "..."
            self.screen.blit(
                small_font.render(status_text, True, (170, 225, 180)),
                (gear_rect.left + 8, y),
            )
            y += 17
        weapon_size = min(56, (gear_rect.width-24)//2)
        self._text("Weapons", (gear_rect.left+8, y))
        y += 19
        values = active.get("weapons", [])
        for i in range(2):
            cooldown = state.get("weapon_cooldowns", [0, 0])[i]
            self._draw_active_slot(f"weapons:{i}", values[i] if i < len(values) else None, by_id,
                                   (gear_rect.left+8+i*(weapon_size+8), y), weapon_size, weapon_size, cooldown)
        y += weapon_size+9
        self._text("Abilities", (gear_rect.left+8, y))
        y += 19
        values = active.get("abilities", [])
        slot_size = min(46, (gear_rect.width-32)//5)
        for i in range(10):
            col = i % 5
            row = i//5
            cooldown = state.get("ability_cooldowns", [0]*10)[i]
            self._draw_active_slot(f"abilities:{i}", values[i] if i < len(values) else None, by_id, (
                gear_rect.left+8+col*(slot_size+3), y+row*(slot_size+3)), slot_size, slot_size, cooldown)
        self._text(f"Inventory · {len(items)} / 200",
                   (grid_rect.left+8, grid_rect.top+7))
        slot_size, columns, rows, visible_rows = self._inventory_grid_metrics(
            grid_rect)
        gap = 5
        scroll_row = self._sync_inventory_scroll(rows, visible_rows)
        content_clip = pygame.Rect(
            grid_rect.left, grid_rect.top+32, grid_rect.width, grid_rect.height-38)
        prior_clip = self.screen.get_clip()
        self.screen.set_clip(content_clip)
        slots_w = columns*(slot_size+gap)-gap
        slots_left = grid_rect.left+max(7, (grid_rect.width-slots_w)//2)
        for row in range(int(scroll_row), min(rows, int(scroll_row)+visible_rows+2)):
            for col in range(columns):
                index = row*columns+col
                rect = pygame.Rect(slots_left+col*(slot_size+gap), grid_rect.top +
                                   33+(row-scroll_row)*(slot_size+gap), slot_size, slot_size)
                item = items[index] if index < len(items) else None
                color = (105, 105, 105)
                if item:
                    status = item.get("status", "normal")
                    color = {"supplement": (245, 205, 55), "active": (
                        70, 220, 115), "combination_base": (240, 145, 55)}.get(status, (105, 105, 105))
                    visible_rect = rect.clip(content_clip)
                    if visible_rect.width and visible_rect.height:
                        self._item_rects[str(item.get("id"))] = visible_rect
                pygame.draw.rect(self.screen, (45, 45, 45),
                                 rect, border_radius=3)
                pygame.draw.rect(self.screen, color, rect,
                                 2 if item else 1, border_radius=3)
                if item:
                    icon_size = slot_size-20
                    icon = pygame.Rect(
                        rect.centerx-icon_size//2-4, rect.centery-icon_size//2, icon_size, icon_size)
                    self._draw_rarity_icon(item, icon)
                    mini_size = 6
                    for combo_index, combo_id in enumerate(item.get("combinations", [])[:5]):
                        mini = pygame.Rect(
                            icon.right+3, rect.y+6+combo_index*(mini_size+2), mini_size, mini_size)
                        self._draw_combo_icon(mini, by_id.get(
                            str(combo_id)) if combo_id is not None else None)
        self.screen.set_clip(prior_clip)
        self._draw_inventory_scrollbar(grid_rect, rows, visible_rows)

    def _draw_item_details(self, item, x, y, width):
        rarity = self._item_rarity_label(item)
        icon = pygame.Rect(x, y, 48, 48)
        self._draw_rarity_icon(item, icon)
        self._text(item.get("name", "Item"), (x+51, y))
        self._text(f"{rarity} · Lv {item.get('level', 1)}", (x+51, y+20))
        by_id = {str(candidate.get("id")): candidate for candidate in getattr(
            self, "_last_state", {}).get("items", [])}
        for index, combo_id in enumerate(item.get("combinations", [])[:5]):
            mini = pygame.Rect(x+51+index*13, y+38, 10, 10)
            self._draw_combo_icon(mini, by_id.get(
                str(combo_id)) if combo_id is not None else None)
        y += 52
        description = item.get('description', '')
        words = description.split()
        line = ''
        for word in words:
            candidate = (line + ' ' + word).strip()
            if line and self.font.size(candidate)[0] > width:
                self._text(line, (x, y))
                y += 18
                line = word
            else:
                line = candidate
        if line:
            self._text(line, (x, y))
            y += 22
        self._text(f"Type: {item.get('type', 'misc').title()}", (x, y))
        y += 22
        from game.systems.item_potential import level_potential
        base_rarity = str(
            item.get("base_rarity", item.get("rarity", "common"))).title()
        self._text(
            f"Origin: {base_rarity} · Level growth: {level_potential(item) * 100:.0f}%", (x, y))
        y += 22
        if item.get("armor_slot"):
            self._text(f"Armor slot: {item['armor_slot'].title()}", (x, y))
            y += 20
        if item.get("armor_set"):
            self._text(f"Set: {item['armor_set'].title()}", (x, y))
            y += 20
        element = item.get("stats", {}).get("element")
        if element:
            self._text(f"Element: {element_label(str(element))}", (x, y))
            y += 20
        for name, value in item.get("stats", {}).items():
            if name in {"element", "script", "cast_type", "bullet_type", "automatic"}:
                continue
            self._text(f"{name.replace('_', ' ').title()}: {value}", (x, y))
            y += 20

    def _draw_active_slot(self, key, item_id, by_id, pos, width, height, cooldown=None):
        rect = pygame.Rect(pos, (width, height))
        self._drop_targets[key] = rect.copy()
        item = by_id.get(str(item_id)) if item_id is not None else None
        pygame.draw.rect(self.screen, (48, 48, 48), rect, border_radius=3)
        pygame.draw.rect(self.screen, (70, 220, 115) if item else (
            100, 100, 100), rect, 2, border_radius=3)
        if item:
            self._hover_slots.append((rect.copy(), item))
            icon_size = min(width, height)-10
            icon = pygame.Rect(rect.centerx-icon_size//2,
                               rect.centery-icon_size//2, icon_size, icon_size)
            self._draw_rarity_icon(item, icon)
            mini_size = 6
            combo_slots = item.get("combinations", [])
            start = rect.centerx-(len(combo_slots)*(mini_size+2)-2)//2
            for index, combo_id in enumerate(combo_slots):
                mini = pygame.Rect(start+index*(mini_size+2),
                                   rect.bottom-mini_size-2, mini_size, mini_size)
                self._draw_combo_icon(mini, by_id.get(
                    str(combo_id)) if combo_id is not None else None)
            if cooldown is not None:
                self._draw_cooldown_overlay(rect, cooldown)

    def _draw_item_tooltip(self, state):
        """Inspect the visible item under the pointer without changing selection."""
        if self.input_handler.drag_active:
            return None
        pos = self.input_handler.mouse_position
        items = {str(item.get("id")): item for item in state.get("items", [])}
        hovered = next((item for rect, item in reversed(self._hover_slots)
                        if rect.collidepoint(pos)), None)
        if hovered is None:
            hovered = next((items[item_id] for item_id, rect in self._item_rects.items()
                            if item_id in items and rect.collidepoint(pos)), None)
        if hovered is None:
            return None

        width = min(300, self.screen_width - 16)
        max_text_width = width - 24
        subtitle_parts = [self._item_rarity_label(hovered)]
        if "level" in hovered:
            subtitle_parts.append(f"Lv {hovered['level']}")
        subtitle_parts.append(str(hovered.get('type', 'item')).title())
        subtitle = hovered.get("tooltip_subtitle") or " · ".join(subtitle_parts)
        lines = [(str(hovered.get("name", "Item")), (255, 244, 205)),
                 (subtitle, self._rarity_color(hovered.get("rarity", "common")))]
        description = str(hovered.get("description") or "No description available.")
        paragraph = ""
        for word in description.split():
            candidate = f"{paragraph} {word}".strip()
            if paragraph and self.font.size(candidate)[0] > max_text_width:
                lines.append((paragraph, (224, 229, 230)))
                paragraph = word
            else:
                paragraph = candidate
        if paragraph:
            lines.append((paragraph, (224, 229, 230)))
        element = hovered.get("stats", {}).get("element")
        if element:
            lines.append((f"Element: {element_label(str(element))}", (177, 213, 226)))
        slot = hovered.get("armor_slot")
        if slot:
            lines.append((f"Armor slot: {str(slot).replace('_', ' ').title()}",
                          (177, 213, 226)))
        max_lines = max(1, (self.screen_height - 28) // 19)
        if len(lines) > max_lines:
            lines = lines[:max_lines - 1] + [("…", (224, 229, 230))]
        height = 18 + len(lines) * 19
        x = min(max(8, int(pos[0]) + 16), self.screen_width - width - 8)
        y = min(max(8, int(pos[1]) + 18), self.screen_height - height - 8)
        box = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (18, 24, 30), box, border_radius=6)
        pygame.draw.rect(self.screen, self._rarity_color(hovered.get("rarity", "common")),
                         box, 2, border_radius=6)
        for index, (text, color) in enumerate(lines):
            self.screen.blit(self.font.render(text, True, color),
                             (box.left + 12, box.top + 9 + index * 19))
        return box

    def _register_item_hover(self, rect, item):
        """Track only the portion of an item visible inside the current clip."""
        visible = rect.clip(self.screen.get_clip())
        if visible.width and visible.height:
            self._hover_slots.append((visible, item))

    def _rarity_color(self, rarity):
        return {
            "common": (145, 145, 145), "uncommon": (58, 181, 83), "rare": (48, 133, 224),
            "epic": (158, 75, 204), "legendary": (246, 207, 58), "mythic": (220, 65, 65),
            "mythical": (220, 65, 65), "ultimate": (255, 255, 255),
        }.get(str(rarity).lower(), (145, 145, 145))

    def _item_rarity_label(self, item):
        rarity = str(item.get("rarity", "common")).title()
        if str(item.get("rarity", "")).lower() == "ultimate":
            tier = item.get("ultimate_tier", 1)
            if type(tier) is int and 1 <= tier <= 100:
                return f"Ultimate {tier}"
        return rarity

    def _draw_rarity_icon(self, rarity, rect):
        ultimate_tier = 1
        item = rarity if isinstance(rarity, dict) else None
        if isinstance(rarity, dict):
            ultimate_tier = rarity.get("ultimate_tier", 1)
            rarity = rarity.get("rarity", "common")
        rarity = str(rarity).lower()
        if rarity == "ultimate":
            if type(ultimate_tier) is not int or not 1 <= ultimate_tier <= 100:
                ultimate_tier = 1
            cache_key = (rect.width, rect.height, ultimate_tier)
            surface = self._rarity_icon_cache.get(cache_key)
            if surface is None:
                surface = pygame.Surface(rect.size)
                width, height = rect.size
                progress = (ultimate_tier - 1) / 99
                base_color = tuple(
                    round(start + (255 - start) * progress)
                    for start in (8, 10, 52)
                )
                for py in range(height):
                    for px in range(width):
                        shade = (
                            (px / max(1, width - 1) + py / max(1, height - 1))
                            / 2
                            * 0.18
                        )
                        color = tuple(
                            round(channel + (255 - channel) * shade)
                            for channel in base_color
                        )
                        surface.set_at((px, py), color)
                self._rarity_icon_cache[cache_key] = surface
            self.screen.blit(surface, rect)
        else:
            pygame.draw.rect(self.screen, self._rarity_color(rarity), rect)
        pygame.draw.rect(self.screen, (220, 220, 220), rect, 1)
        if item and rect.width >= 16 and rect.height >= 16:
            self._draw_item_icon(item, rect)

    def _draw_item_icon(self, item, rect):
        kind = item.get('type', 'relic')
        if kind == 'armor':
            kind = item.get('armor_slot', 'chestplate')
            if kind == 'headpiece':
                kind = 'helmet'
        elif kind == 'ability':
            stats = item.get('stats', {})
            if stats.get('cast_type') == 'heal' or stats.get('script') in ('heal', 'mend_ward'):
                kind = 'heal'
            elif stats.get('element') == 'fire':
                kind = 'fire'
        icon = self.item_icons.get(kind, self.item_icons['ability'])
        color = icon.get('color', [240, 240, 240])

        def point(p):
            return (rect.left + int(p[0] * rect.width), rect.top + int(p[1] * rect.height))
        for polygon in icon.get('polygons', []):
            pygame.draw.polygon(self.screen, color, [
                                point(p) for p in polygon])
        for cx, cy, radius in icon.get('circles', []):
            pygame.draw.circle(self.screen, color, point((cx, cy)), max(
                1, int(radius * min(rect.size))), max(1, rect.width // 14))
        for start, end in icon.get('lines', []):
            pygame.draw.line(self.screen, color, point(start),
                             point(end), max(1, rect.width // 15))

    def _draw_combo_icon(self, rect, item):
        if item:
            self._draw_rarity_icon(item, rect)
        else:
            pygame.draw.rect(self.screen, (90, 90, 90), rect)
            pygame.draw.rect(self.screen, (160, 160, 160), rect, 1)

    def _is_valid_combination_supplement(self, base_item: dict, supplement_item: dict) -> bool:
        """Check if an item can be used as a combination supplement for a base item."""
        # Cannot combine an item with itself
        if base_item.get("id") == supplement_item.get("id"):
            return False
        if ((base_item.get("type") == "armor") != (supplement_item.get("type") == "armor")
                and not (base_item.get("type") == "armor" and supplement_item.get("fusion_recipe") == "elemental-core")):
            return False
        # Cannot combine if base item is full
        base_combos = base_item.get("combinations", [])
        if None not in base_combos:
            return False
        # Cannot combine if supplement is already used in another combination
        for item in self._last_state.get("items", []):
            if supplement_item.get("id") in item.get("combinations", []):
                return False
        # Cannot combine if supplement is actively equipped
        active_slots = self._last_state.get("active_slots", {})
        for kind in ("armor", "weapons", "abilities"):
            if supplement_item.get("id") in active_slots.get(kind, []):
                return False
        return True

    def _inventory_grid_metrics(self, grid_rect):
        gap = 5
        columns = max(1, (grid_rect.width-18)//88)
        slot_size = max(
            28, min(92, (grid_rect.width-18-(columns+1)*gap)//columns))
        rows = (200+columns-1)//columns
        visible_rows = max(1, (grid_rect.height-40)//(slot_size+gap))
        return slot_size, columns, rows, visible_rows

    def _scroll_at(self, pos, direction):
        for key, rect in reversed(list(self._scroll_regions.items())):
            if not rect.collidepoint(pos):
                continue
            if key == "inventory":
                self.inventory_scroll_target = max(
                    0, self.inventory_scroll_target + direction * 2)
            elif key.startswith("quest:"):
                kind = key.split(":", 1)[1]
                self.quest_offsets[kind] = max(
                    0, self.quest_offsets[kind] + direction)
            else:
                setattr(self, key, max(0, getattr(self, key, 0) + direction))
            break

    def _smooth_scroll(self, key, maximum):
        target = max(0.0, min(float(maximum), float(getattr(self, key, 0))))
        setattr(self, key, target)
        current = min(float(maximum), self._scroll_positions.get(key, 0.0))
        current += (target - current) * min(1.0, self._frame_dt * 12)
        if abs(target - current) < .01:
            current = target
        self._scroll_positions[key] = current
        return current

    def _draw_inventory_scrollbar(self, grid_rect, rows, visible_rows):
        rail = pygame.Rect(grid_rect.right-8, grid_rect.top +
                           32, 4, max(1, grid_rect.height-42))
        pygame.draw.rect(self.screen, (80, 80, 80), rail, border_radius=2)
        thumb_h = max(18, int(rail.height*min(1, visible_rows/max(1, rows))))
        max_scroll = max(0, rows-visible_rows)
        thumb_y = rail.top + \
            int((rail.height-thumb_h)*(self.inventory_scroll/max_scroll)
                ) if max_scroll else rail.top
        pygame.draw.rect(self.screen, (185, 185, 185),
                         (rail.x-2, thumb_y, 8, thumb_h), border_radius=3)

    def _sync_inventory_scroll(self, rows, visible_rows):
        maximum = max(0, rows-visible_rows)
        self.inventory_scroll_target = max(
            0.0, min(float(maximum), self.inventory_scroll_target))
        self.inventory_scroll += (self.inventory_scroll_target -
                                  self.inventory_scroll)*min(1.0, self._frame_dt*12)
        if abs(self.inventory_scroll_target-self.inventory_scroll) < 0.01:
            self.inventory_scroll = float(self.inventory_scroll_target)
        return self.inventory_scroll

    def _draw_inventory_links(self, items, active_slots):
        if not self._item_rects:
            return
        centers = {item_id: rect.center for item_id,
                   rect in self._item_rects.items()}
        for kind, slot_ids in active_slots.items():
            for index, item_id in enumerate(slot_ids):
                start = centers.get(str(item_id))
                target = self._drop_targets.get(f"{kind}:{index}")
                if start and target:
                    pygame.draw.line(
                        self.screen, (175, 175, 175), start, target.center, 1)
        for item in items:
            base = centers.get(str(item.get("id")))
            if base:
                for supplement_id in item.get("combinations", []):
                    supplement = centers.get(
                        str(supplement_id)) if supplement_id is not None else None
                    if supplement:
                        pygame.draw.line(
                            self.screen, (175, 175, 175), base, supplement, 1)

    def _draw_drag_ghost(self, state):
        if not self.input_handler.drag_active or not self.input_handler.drag_start or not self._drag_item_id:
            return
        item = next((entry for entry in state.get("items", []) if str(
            entry.get("id")) == str(self._drag_item_id)), None)
        if not item:
            return
        x, y = self.input_handler.get_mouse_position()
        size = 44
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        prior = self.screen
        self.screen = surface
        self._draw_rarity_icon(item, pygame.Rect(0, 0, size, size))
        self.screen = prior
        surface.set_alpha(210)
        self.screen.blit(surface, (x-size//2, y-size//2))

    def _draw_quests_menu(self, outer, state=None):
        state = state or {}
        quests = state.get("quests", [])
        self._text(
            f"Completed quest bonus: +{float(state.get('quest_bonus_pct', 0)):.1f}%", (outer.left + 12, outer.top + 4))
        for index, kind in enumerate(("main", "side")):
            rect = pygame.Rect(outer.left + 8 + index * (outer.width // 2),
                               outer.top + 28, outer.width // 2 - 16, outer.height - 36)
            self._scroll_regions[f"quest:{kind}"] = rect.copy()
            pygame.draw.rect(self.screen, (46, 46, 46), rect, border_radius=5)
            pygame.draw.rect(self.screen, (105, 105, 105),
                             rect, 1, border_radius=5)
            self._text("Main quests" if kind ==
                       "main" else "Side quests (max 3 active)", (rect.left + 10, rect.top + 8))
            entries = [q for q in quests if q.get("type") == kind and q.get(
                "status") in ("active", "available", "completed")
                and not (kind == "main" and q.get("status") == "available"
                         and "main_quest_choice" in state)]
            if kind == "main" and any(q.get("status") == "available" for q in entries):
                self._button("quest_decline_main", "Skip main quest",
                             (rect.right - 77, rect.top + 14), 140, 24)
            card_height = 126
            visible = max(1, (rect.height - 65) // card_height)
            maximum = max(0, len(entries) - visible)
            self.quest_offsets[kind] = min(self.quest_offsets[kind], maximum)
            offset = min(self.quest_scroll_positions[kind], maximum)
            offset += (self.quest_offsets[kind] -
                       offset) * min(1.0, self._frame_dt * 12)
            self.quest_scroll_positions[kind] = offset
            if not entries:
                self._text("No quests available yet.",
                           (rect.left + 10, rect.top + 34))
            old_clip = self.screen.get_clip()
            content_clip = pygame.Rect(
                rect.left + 3, rect.top + 29, rect.width - 6, rect.height - 52)
            self.screen.set_clip(content_clip)
            for row in range(int(offset), min(len(entries), int(offset) + visible + 2)):
                quest = entries[row]
                y = int(rect.top + 32 + (row - offset) * card_height)
                status = quest.get("status")
                box = pygame.Rect(rect.left + 5, y - 3,
                                  rect.width - 10, card_height - 4)
                pygame.draw.rect(self.screen, (39, 54, 43) if status == "active" else (
                    40, 40, 40), box, border_radius=4)
                pygame.draw.rect(self.screen, (100, 175, 110) if status == "active" else (
                    95, 95, 95), box, 1, border_radius=4)
                reward = f"^{quest.get('reward_power', 1):g}" if kind == "main" else f"+{quest.get('reward_pct', 0)}%"
                self._text(
                    f"{quest.get('name', 'Quest')}  ({reward})", (rect.left + 10, y))
                text_y = y + 18
                description = str(quest.get("description", ""))
                restrictions = quest.get("restrictions") or []
                if restrictions:
                    description += "  Restriction: " + ", ".join(restrictions)
                line = ''
                for word in description.split():
                    candidate = (line + ' ' + word).strip()
                    if line and self.font.size(candidate)[0] > rect.width - 24:
                        self._text(line, (rect.left + 10, text_y))
                        text_y += 17
                        line = word
                    else:
                        line = candidate
                if line:
                    self._text(line, (rect.left + 10, text_y))
                if status == "available":
                    self._button(
                        f"quest_accept:{quest['id']}", "Accept", (rect.right - 45, y + card_height - 21), 70, 27)
                    self._buttons[f"quest_accept:{quest['id']}"] = self._buttons[f"quest_accept:{quest['id']}"].clip(
                        content_clip)
                    self._text("Available", (rect.left +
                               10, y + card_height - 29))
                else:
                    self._text("Complete" if status == "completed" else "Active",
                               (rect.left + 10, y + card_height - 33))
                    bar = pygame.Rect(
                        rect.left + 80, y + card_height - 28, max(20, rect.width - 120), 10)
                    pygame.draw.rect(self.screen, (70, 70, 70),
                                     bar, border_radius=3)
                    fill = bar.copy()
                    fill.width = int(
                        bar.width * min(1, max(0, quest.get("progress", 0) / max(1, quest.get("target", 1)))))
                    pygame.draw.rect(
                        self.screen, (80, 195, 110), fill, border_radius=3)
            self.screen.set_clip(old_clip)
            if len(entries) > visible:
                self._text("Scroll to browse",
                           (rect.left + 10, rect.bottom - 18))

    def _draw_upgrades_menu(self, state, outer):
        area = outer.inflate(-16, -16)
        pygame.draw.rect(self.screen, (46, 46, 46), area, border_radius=5)
        if self.upgrade_tab == "combination":
            progress = state.get("combination_progress")
            if progress:
                discovered = progress.get("discovered", 0)
                required = progress.get("required", 3)
                minimum = progress.get("minimum_base_level", 2)
                self._text(f"Ability discoveries: {discovered}/{required} · Base item level {minimum}+ required",
                           (area.x + 10, area.y + 7))
                self._text("Combination unlocked" if progress.get("ready") else "Discover distinct abilities to unlock combinations. No waiting timer.",
                           (area.x + 10, area.y + 26))
                area = pygame.Rect(area.x, area.y + 48, area.width, area.height - 48)
            self._draw_combination_menu(state, area)
            return
        level = state.get("level", 1)
        xp = state.get("experience", 0)
        required = state.get("next_level_exp", 1)
        self._text("Player level", (area.centerx-54, area.top+12))
        self._text(f"{xp} / {required} EXP", (area.centerx-55, area.top+36))
        bar = pygame.Rect(area.centerx-160, area.top+58, 280, 16)
        pygame.draw.rect(self.screen, (76, 76, 76), bar, border_radius=6)
        fill = bar.copy()
        fill.width = int(bar.width*min(1, xp/max(1, required)))
        pygame.draw.rect(self.screen, (100, 195, 120), fill, border_radius=6)
        self._text(f"Level {level}", (bar.right+10, bar.top-2))
        left = area.left+18
        y = bar.bottom+22
        self._text("Player stats", (left, y))
        y += 26
        self._text(f"Luck: {state.get('luck', 0)}", (left, y))
        y += 22
        self._text(f"Speed: {state.get('speed', 1.0)}", (left, y))
        y += 24
        self._text("Currencies", (left, y))
        y += 22
        for name, amount in state.get("currency", {}).items():
            self._text(f"{name}: {amount}", (left, y))
            y += 20
        self._text("Armor & weapons", (area.centerx-40, bar.bottom+22))
        self._text("Active abilities", (area.right-150, bar.bottom+22))
        by_id = {str(item.get("id")): item for item in state.get("items", [])}
        active = state.get("active_slots", {})
        y = bar.bottom+48
        for kind in ("armor", "weapons"):
            for item_id in active.get(kind, []):
                item = by_id.get(str(item_id))
                if item:
                    self._draw_upgrade_item(item, area.centerx-40, y, 180)
                    y += 39
        y = bar.bottom+48
        for item_id in active.get("abilities", []):
            item = by_id.get(str(item_id))
            if item:
                self._draw_upgrade_item(item, area.right-200, y, 185)
                y += 39

    def _draw_upgrade_item(self, item, x, y, width):
        self._text(
            f"{item['name']} · {self._item_rarity_label(item)} · Lv {item['level']}", (x, y))
        stats = list(item.get("stats", {}).items())[:2]
        if stats:
            self._text(" · ".join(
                f"{key} {value}" for key, value in stats), (x, y+17))
        for i, combo_id in enumerate(item.get("combinations", [])[:5]):
            rect = pygame.Rect(x+i*11, y+31, 8, 8)
            pygame.draw.rect(self.screen, (230, 175, 65)
                             if combo_id is not None else (105, 110, 125), rect, 1)

    def _draw_fusion_menu(self, state, area):
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        selected = by_id.get(str(self.selected_item_id))
        left = pygame.Rect(area.left + 10, area.top + 10,
                           int(area.width * 0.42) - 12, area.height - 20)
        right = pygame.Rect(left.right + 10, area.top + 10,
                            area.right - left.right - 20, area.height - 20)
        for rect in (left, right):
            pygame.draw.rect(self.screen, (46, 46, 46), rect, border_radius=5)
            pygame.draw.rect(self.screen, (105, 105, 105),
                             rect, 1, border_radius=5)
        self._text("Fusion chamber", (left.left + 10, left.top + 8))
        if selected:
            icon = pygame.Rect(left.left + 12, left.top + 38, 52, 52)
            self._draw_rarity_icon(selected, icon)
            self._text(selected.get("name", "Item"),
                       (icon.right + 10, left.top + 42))
            self._text(f"{self._item_rarity_label(selected)} · Level {selected.get('level', 1)}",
                       (icon.right + 10, left.top + 64))
            self._text(f"Type: {selected.get('type', 'item').title()}",
                       (icon.right + 10, left.top + 86))
        else:
            self._text("Select an item in the inventory to use as the fusion core.",
                       (left.left + 10, left.top + 43))
        recipes = state.get("fusion_recipes", [])
        fusion_unlocked = bool(state.get("fusion_unlocked", False))
        if not fusion_unlocked:
            self._text(
                f"Fusion unlocks at level {state.get('fusion_unlock_level', 50)}.",
                (left.left + 12, left.top + 132),
            )
            self._text(
                f"Current level: {state.get('level', 1)}",
                (left.left + 12, left.top + 158),
            )
        else:
            y = left.top + 132
            for recipe in recipes:
                recipe_rect = pygame.Rect(
                    left.left + 12, y, left.width - 24, 62)
                pygame.draw.rect(self.screen, (62, 62, 62),
                                 recipe_rect, border_radius=5)
                pygame.draw.rect(self.screen, (120, 120, 120),
                                 recipe_rect, 1, border_radius=5)
                self._text(recipe.get("name", "Fusion"),
                           (recipe_rect.left + 10, recipe_rect.top + 8))
                self._text(
                    f"{recipe.get('description', '')[:38]} · "
                    f"{recipe.get('min_rarity', 'common').title()} Lv {recipe.get('min_level', 1)}",
                    (recipe_rect.left + 10, recipe_rect.top + 25),
                )
                self._text(
                    " + ".join(recipe.get("required_types", [])),
                    (recipe_rect.left + 10, recipe_rect.top + 43),
                )
                self._buttons[f"fusion_recipe:{recipe['id']}:{self.selected_item_id or ''}"] = recipe_rect.copy(
                )
                y += 68
        self._text("Inventoried items", (right.left + 8, right.top + 8))
        slot_size, columns, rows, visible_rows = self._inventory_grid_metrics(
            right)
        gap = 5
        scroll_row = self._sync_inventory_scroll(rows, visible_rows)
        prior_clip = self.screen.get_clip()
        self.screen.set_clip(right)
        slots_w = columns * (slot_size + gap) - gap
        slots_left = right.left + max(7, (right.width - slots_w) // 2)
        for row in range(int(scroll_row), min(rows, int(scroll_row) + visible_rows + 2)):
            for col in range(columns):
                index = row * columns + col
                item = items[index] if index < len(items) else None
                rect = pygame.Rect(slots_left + col * (slot_size + gap), right.top + 30 + (
                    row - scroll_row) * (slot_size + gap), slot_size, slot_size)
                pygame.draw.rect(self.screen, (48, 48, 48),
                                 rect, border_radius=3)
                pygame.draw.rect(self.screen, (100, 100, 100),
                                 rect, 1, border_radius=3)
                if item:
                    visible_rect = rect.clip(right)
                    if visible_rect.width and visible_rect.height:
                        self._item_rects[str(item.get("id"))] = visible_rect
                    self._draw_rarity_icon(item, rect.inflate(-10, -10))
        self.screen.set_clip(prior_clip)
        self._draw_inventory_scrollbar(right, rows, visible_rows)

    def _draw_combination_menu(self, state, area):
        from game.systems.combinations import CombinationEngine
        from game.systems.combat_bonuses import combined_local_stat
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        left = pygame.Rect(area.left+10, area.top+10,
                           int(area.width*.46)-12, area.height-20)
        right = pygame.Rect(left.right+10, area.top+10,
                            area.right-left.right-20, area.height-20)
        self._inventory_rect = right.copy()
        for rect in (left, right):
            pygame.draw.rect(self.screen, (46, 46, 46), rect, border_radius=5)
            pygame.draw.rect(self.screen, (105, 105, 105),
                             rect, 1, border_radius=5)
        self._text("Combination setup", (left.left+10, left.top+8))
        base = by_id.get(str(self.selected_base_id))
        if base:
            icon = pygame.Rect(left.left+12, left.top+38, 52, 52)
            self._draw_rarity_icon(base, icon)
            detail_x = icon.right+10
            detail_y = left.top+39
            self._text(base.get("name", "Item"), (detail_x, detail_y))
            detail_y += 22
            self._text(
                f"{self._item_rarity_label(base)} · Level {base.get('level', 1)}", (detail_x, detail_y))
            detail_y += 21
            self._text(
                f"Type: {base.get('type', 'item').title()}", (detail_x, detail_y))
            detail_y += 23
            # Combination slots
            slots = base.get("combinations", [])
            slot_x = left.right-50
            slot_y = left.top+40
            self._text("Combinations", (slot_x-76, left.top+14))
            # The preview shows the same evaluated values that combat uses.
            preview_y = left.top+130
            preview_rect = pygame.Rect(
                left.left+12, preview_y, max(40, left.width-76), max(40, left.bottom-preview_y-12))
            pygame.draw.rect(self.screen, (28, 46, 28),
                             preview_rect, border_radius=4)
            pygame.draw.rect(self.screen, (100, 180, 100),
                             preview_rect, 1, border_radius=4)
            self._text("Combined effects · live preview",
                       (preview_rect.left+10, preview_rect.top+6))
            # Get current supplements
            current_supplements = [by_id.get(str(sid))
                                   for sid in slots if sid is not None]
            current_supplements = [s for s in current_supplements if s]
            try:
                evaluation = CombinationEngine().evaluate(base, current_supplements)
                lines = []
                if evaluation.metadata.get("owned_relic_ids"):
                    lines.append("Owned relic passives apply once.")
                    lines.append("Special effects transfer here.")
                for stat_name in evaluation.stats:
                    stat_value = combined_local_stat(evaluation, stat_name)
                    lines.append(f"{stat_name.replace('_', ' ')}: {stat_value}")
                if any(s.get("type") == "ability" and s.get("stats", {}).get(
                        "script", s.get("stats", {}).get("cast_type")) in {"heal", "mend_ward"}
                       for s in current_supplements):
                    budget = combined_local_stat(evaluation, "heal_amount")
                    lines.append(f"Heals actual damage dealt, up to {budget} per cast.")
                content = pygame.Rect(preview_rect.left + 4, preview_rect.top + 25,
                                      preview_rect.width - 8, preview_rect.height - 30)
                lines = [row for line in lines
                         for row in self._codex_wrap(line, content.width - 12)]
                self._scroll_regions["combination_stats_scroll"] = content.copy()
                visible = max(1, content.height // 18)
                offset = self._smooth_scroll("combination_stats_scroll", max(0, len(lines) - visible))
                previous_clip = self.screen.get_clip()
                self.screen.set_clip(content)
                for index in range(int(offset), min(len(lines), int(offset) + visible + 2)):
                    self._text(lines[index], (content.left + 6, content.top + (index - offset) * 18))
                self.screen.set_clip(previous_clip)
            except ValueError:
                self._text("This combination is invalid.",
                           (preview_rect.left+10, preview_rect.top+26))
            # Draw combination slots
            for i in range(len(slots)):
                rect = pygame.Rect(slot_x, slot_y+i*50, 42, 42)
                self._drop_targets[f"combo:{base['id']}:{i}"] = rect.copy()
                slot_color = (48, 48, 48)
                if slots[i] is None:
                    pygame.draw.rect(self.screen, (40, 40, 40),
                                     rect, border_radius=3)
                    pygame.draw.rect(self.screen, (80, 80, 80),
                                     rect, 1, border_radius=3)
                    # Draw plus icon for empty slots
                    center = rect.center
                    pygame.draw.line(
                        self.screen, (120, 120, 120), (center[0]-8, center[1]), (center[0]+8, center[1]), 2)
                    pygame.draw.line(
                        self.screen, (120, 120, 120), (center[0], center[1]-8), (center[0], center[1]+8), 2)
                else:
                    pygame.draw.rect(self.screen, (50, 50, 50),
                                     rect, border_radius=3)
                    pygame.draw.rect(self.screen, (205, 205, 205),
                                     rect, 2, border_radius=3)
                    combo = by_id.get(str(slots[i]))
                    if combo:
                        self._draw_rarity_icon(combo, rect.inflate(-4, -4))
        else:
            self._text("Click an armor, weapon, or ability in the inventory to inspect it here.",
                       (left.left+10, left.top+43))
        self._text("Inventory · drag a supplement to a combination slot",
                   (right.left+8, right.top+7))
        self._draw_inventory_grid(items, right)

    def _draw_inventory_grid(self, items, grid_rect):
        self._inventory_rect = grid_rect.copy()
        self._scroll_regions["inventory"] = grid_rect.copy()
        slot_size, columns, rows, visible_rows = self._inventory_grid_metrics(
            grid_rect)
        gap = 5
        scroll_row = self._sync_inventory_scroll(rows, visible_rows)
        slots_w = columns*(slot_size+gap)-gap
        slots_left = grid_rect.left+max(7, (grid_rect.width-slots_w-14)//2)
        content_clip = pygame.Rect(
            grid_rect.left, grid_rect.top+32, grid_rect.width, grid_rect.height-38)
        prior_clip = self.screen.get_clip()
        self.screen.set_clip(content_clip)
        for row in range(int(scroll_row), min(rows, int(scroll_row)+visible_rows+2)):
            for col in range(columns):
                index = row*columns+col
                rect = pygame.Rect(slots_left+col*(slot_size+gap), grid_rect.top +
                                   32+(row-scroll_row)*(slot_size+gap), slot_size, slot_size)
                item = items[index] if index < len(items) else None
                color = (105, 105, 105)
                if item:
                    color = {"supplement": (245, 205, 55), "active": (70, 220, 115), "combination_base": (
                        240, 145, 55)}.get(item.get("status", "normal"), color)
                    visible_rect = rect.clip(content_clip)
                    if visible_rect.width and visible_rect.height:
                        self._item_rects[str(item.get("id"))] = visible_rect
                pygame.draw.rect(self.screen, (46, 46, 46),
                                 rect, border_radius=3)
                pygame.draw.rect(self.screen, color, rect,
                                 2 if item else 1, border_radius=3)
                if item:
                    icon_size = slot_size-20
                    icon = pygame.Rect(
                        rect.centerx-icon_size//2-4, rect.centery-icon_size//2, icon_size, icon_size)
                    self._draw_rarity_icon(item, icon)
                    for combo_index, combo_id in enumerate(item.get("combinations", [])[:5]):
                        mini = pygame.Rect(
                            icon.right+3, rect.y+6+combo_index*8, 6, 6)
                        self._draw_combo_icon(mini, next((entry for entry in items if str(
                            entry.get("id")) == str(combo_id)), None) if combo_id is not None else None)
        self.screen.set_clip(prior_clip)
        self._draw_inventory_scrollbar(grid_rect, rows, visible_rows)

    def _draw_bazaar_menu(self, outer, state):
        bazaar = state.get("bazaar", {})
        wallet = bazaar.get("wallet", {})
        self._text("Bazaar", (outer.left + 16, outer.top + 8))
        tabs = [("market", "Market"), ("crates", "Crates"), ("fusion", "Fusion"),
                ("rarity_upgrader", "Rarity"), ("level_upgrader", "Level"), ("sell", "Sell"), ("exchange", "Exchange")]
        tab_width = min(140, (outer.width - 28) // len(tabs))
        for i, (key, label) in enumerate(tabs):
            self._button(f"bazaar_tab_{key}", label,
                         (outer.left + 12 + i * tab_width +
                          tab_width // 2, outer.top + 45),
                         tab_width - 4, 30)
            if self._bazaar_tab == key:
                pygame.draw.line(self.screen, (225, 225, 225),
                                 (outer.left + 14 + i * tab_width, outer.top + 61),
                                 (outer.left + (i + 1) * tab_width, outer.top + 61), 2)
        content = pygame.Rect(outer.left + 8, outer.top +
                              68, outer.width - 16, outer.height - 76)
        if self._bazaar_tab in ("market", "crates"):
            self._draw_bazaar_offers(content, state, self._bazaar_tab)
        elif self._bazaar_tab == "exchange":
            self._draw_currency_exchange(content, state)
        else:
            self._draw_bazaar_owned(content, state, self._bazaar_tab)

    def _draw_currency_icon(self, name, rect):
        definition = currency_definition(name) or {}
        pygame.draw.rect(self.screen, definition.get(
            "color", (120, 120, 120)), rect, border_radius=4)
        pygame.draw.rect(self.screen, (225, 225, 225),
                         rect, 1, border_radius=4)
        # Symbols remain identifiable on systems without a color emoji font.
        symbol = definition.get("emoji", definition.get("symbol", "◆"))
        glyph = self.currency_font.render(symbol, True, (255, 255, 255))
        if glyph.get_width() > rect.width - 2 or glyph.get_height() > rect.height - 2:
            glyph = pygame.transform.smoothscale(
                glyph, (max(1, rect.width - 2), max(1, rect.height - 2)))
        self.screen.blit(glyph, glyph.get_rect(center=rect.center))

    def _draw_economy_slider(self, key, rect, fraction, dots=0):
        self._sliders[key] = rect
        y = rect.centery
        pygame.draw.line(self.screen, (130, 130, 130),
                         (rect.left, y), (rect.right, y), 4)
        for i in range(dots):
            x = rect.left + int(rect.width * i / max(1, dots - 1))
            pygame.draw.circle(self.screen, (220, 220, 220), (x, y), 4)
        x = rect.left + int(rect.width * max(0, min(1, fraction)))
        pygame.draw.circle(self.screen, (100, 230, 150), (x, y), 7)

    def _update_economy_slider(self, start, pos):
        wallet = self._last_state.get("bazaar", {}).get("wallet", {})
        names = list(wallet)
        if not names:
            return
        if self._bazaar_tab == "rarity_upgrader" and self._rarity_dropdown_open:
            return
        for key, rect in self._sliders.items():
            if not rect.inflate(10, 14).collidepoint(start):
                continue
            width = max(1, rect.width)
            offset = max(0, min(width, pos[0] - rect.left))
            fraction = offset / width
            def scaled_amount(value):
                # Integer arithmetic avoids converting enormous wallets to float.
                quotient, remainder = divmod(int(value) * offset, width)
                if remainder * 2 > width or (remainder * 2 == width and quotient % 2):
                    quotient += 1
                return quotient
            if key == "exchange" and self._bazaar_tab == "exchange":
                self._exchange_amount = scaled_amount(
                    wallet[names[self._exchange_source % len(names)]])
            elif key == "pool" and self._bazaar_tab == "rarity_upgrader":
                name = names[self._rarity_currency % len(names)]
                self._rarity_pool[name] = scaled_amount(wallet[name])
            elif key == "target" and self._bazaar_tab == "rarity_upgrader":
                selected = next((item for item in self._last_state.get("items", []) if str(
                    item.get("id")) == str(self.selected_item_id)), None)
                if selected:
                    rank = RARITY_ORDER.index(
                        str(selected.get("rarity", "common")).lower())
                    self._rarity_target = fraction * \
                        max(0, len(RARITY_ORDER) - rank - 2)
            break

    def _draw_currency_exchange(self, rect, state):
        wallet = state.get("bazaar", {}).get("wallet", {})
        names = list(wallet)
        if len(names) < 2:
            self._text("No currencies available.",
                       (rect.left + 15, rect.top + 15))
            return
        source = names[self._exchange_source % len(names)]
        destination = names[self._exchange_destination % len(names)]
        left = pygame.Rect(rect.left + 5, rect.top + 5,
                           int(rect.width * .48), rect.height - 10)
        right = pygame.Rect(left.right + 8, rect.top + 5,
                            rect.right - left.right - 13, rect.height - 10)
        self._scroll_regions["_exchange_scroll"] = right.copy()
        for panel in (left, right):
            pygame.draw.rect(self.screen, (46, 46, 46), panel, border_radius=5)
            pygame.draw.rect(self.screen, (105, 105, 105),
                             panel, 1, border_radius=5)
        self._text("Drag currencies onto the scale",
                   (left.left + 10, left.top + 8))
        self._text("Currencies (scroll to browse)",
                   (right.left + 10, right.top + 8))
        src_value = currency_definition(source)['value_multiplier']
        dst_value = currency_definition(destination)['value_multiplier']
        tilt = 12 if src_value > dst_value else -12 if src_value < dst_value else 0
        beam_y = left.top + 90
        a, b = (left.left + 55, beam_y +
                tilt), (left.right - 55, beam_y - tilt)
        pygame.draw.line(self.screen, (220, 190, 110), a, b, 5)
        pygame.draw.polygon(self.screen, (150, 130, 85), [(
            left.centerx, beam_y), (left.centerx - 18, beam_y + 64), (left.centerx + 18, beam_y + 64)])
        arrow_y = left.top + 146
        pygame.draw.line(self.screen, (220, 220, 210), (left.centerx -
                         24, arrow_y), (left.centerx + 24, arrow_y), 2)
        pygame.draw.lines(self.screen, (220, 220, 210), False, [
                          (left.centerx + 17, arrow_y - 5), (left.centerx + 24, arrow_y), (left.centerx + 17, arrow_y + 5)], 2)
        self._exchange_slots = {}
        for key, name, pt in (("source", source, a), ("destination", destination, b)):
            slot = pygame.Rect(pt[0] - 25, pt[1] + 7, 50, 50)
            self._exchange_slots[key] = slot
            self._draw_currency_icon(name, slot)
            self._text("From" if key == "source" else "To",
                       (slot.left, slot.bottom + 2))
        self._text(f"{source} -> {destination}",
                   (left.left + 10, left.top + 159))
        amount = min(max(0, self._exchange_amount), int(wallet[source]))
        self._exchange_amount = amount
        self._text(
            f"Amount: {amount} / {wallet[source]}", (left.left + 10, left.top + 180))
        self._draw_economy_slider("exchange", pygame.Rect(
            left.left + 15, left.top + 201, left.width - 30, 22), amount / max(1, int(wallet[source])))
        try:
            received = exchange_quote(source, destination, amount)
            self._text(f"Receive: {received} {destination}",
                       (left.left + 10, left.bottom - 61))
            self._button(f"bazaar_exchange:{source}:{destination}:{amount}", "Exchange", (
                left.centerx, left.bottom - 23), left.width - 20, 30)
        except ValueError as exc:
            self._text(str(exc), (left.left + 10, left.bottom - 55))
        row_height = 49
        visible = max(1, (right.height - 35) // row_height)
        offset = self._smooth_scroll(
            "_exchange_scroll", max(0, len(names) - visible))
        self._currency_drag_rects = {}
        content_clip = pygame.Rect(
            right.left, right.top + 32, right.width, right.height - 35)
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(content_clip)
        for index in range(int(offset), min(len(names), int(offset) + visible + 2)):
            name = names[index]
            row = pygame.Rect(right.left + 8, right.top + 32 + (index - offset)
                              * row_height, right.width - 16, row_height - 3)
            pygame.draw.rect(self.screen, (110, 110, 110),
                             row, 1, border_radius=4)
            icon = pygame.Rect(row.left + 3, row.top + 3, 38, 38)
            self._draw_currency_icon(name, icon)
            self._currency_drag_rects[name] = icon.clip(content_clip)
            self._text(name, (icon.right + 7, row.top + 13))
            amount_text = str(wallet[name])
            amount_surface = self.font.render(
                amount_text, True, (240, 235, 215))
            amount_rect = amount_surface.get_rect(
                midright=(row.right - 7, row.centery)).inflate(8, 6)
            pygame.draw.rect(self.screen, (28, 28, 28),
                             amount_rect, border_radius=3)
            self.screen.blit(amount_surface, amount_surface.get_rect(
                center=amount_rect.center))
        self.screen.set_clip(previous_clip)

    def _draw_bazaar_offers(self, rect, state, tab):
        bazaar = state.get("bazaar", {})
        offers = bazaar.get("catalog" if tab == "market" else "crates", [])
        if tab == "crates":
            self._draw_crate_offers(rect, bazaar, offers)
            return
        self._scroll_regions["bazaar_market_scroll_target"] = rect.copy()
        scroll_attr = "bazaar_market_scroll_target" if tab == "market" else "bazaar_crates_scroll_target"
        row_height = 76 if tab == "market" else 68
        visible = max(1, (rect.height - 44) // row_height)
        start = self._smooth_scroll(scroll_attr, max(0, len(offers) - visible))
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(rect)
        for i in range(int(start), min(len(offers), int(start) + visible + 2)):
            offer = offers[i]
            row = pygame.Rect(rect.left + 8, rect.top + 4 + (i - start)
                              * row_height, rect.width - 16, row_height - 4)
            pygame.draw.rect(self.screen, (55, 55, 55), row, border_radius=4)
            pygame.draw.rect(self.screen, (110, 110, 110),
                             row, 1, border_radius=4)
            icon_rect = pygame.Rect(row.left + 8, row.top + 8, 48, 48)
            self._draw_rarity_icon(offer, icon_rect)
            self._register_item_hover(icon_rect, offer)
            self._text(offer.get("name", "Item"), (row.left + 65, row.top + 5))
            if tab == "market":
                detail = f"{offer.get('type', 'item').title()} · {offer.get('rarity', 'common').title()}"
                price = offer.get("market_price", 0)
                action = f"bazaar_item:{offer.get('id', '')}"
            else:
                detail = offer.get("description", "")
                price = offer.get("cost", 0)
                action = f"bazaar_buy:{offer.get('id', '')}"
            self._text(detail[:70], (row.left + 65, row.top + 25))
            description = offer.get('description', '')
            self._text(
                description[:max(10, (row.width - 240) // 8)], (row.left + 65, row.top + 46))
            self._text(f"{price} Gold", (row.right - 165, row.top + 10))
            self._button(action, "Buy", (row.right - 45, row.centery), 75, 32)
            self._buttons[action] = self._buttons[action].clip(rect)
        self.screen.set_clip(previous_clip)
        if not offers:
            self._text("No offers available right now.",
                       (rect.left + 12, rect.top + 12))
        if tab == "crates":
            self._button("bazaar_refresh", "Refresh",
                         (rect.right - 65, rect.bottom - 17), 110, 28)

    def _draw_crate_offers(self, rect, bazaar, offers):
        left = pygame.Rect(rect.left + 5, rect.top + 5,
                           int(rect.width * .48) - 10, rect.height - 10)
        right = pygame.Rect(left.right + 10, rect.top + 5,
                            rect.right - left.right - 15, rect.height - 10)
        self._scroll_regions["bazaar_crates_scroll_target"] = left.copy()
        self._scroll_regions["bazaar_rewards_scroll"] = right.copy()
        for panel in (left, right):
            pygame.draw.rect(self.screen, (46, 46, 46), panel, border_radius=5)
            pygame.draw.rect(self.screen, (105, 105, 105),
                             panel, 1, border_radius=5)
        self._text(f"Crate room · Daily refresh: {bazaar.get('daily_refresh_seconds', 60)}s", (
            left.left + 10, left.top + 8))
        selected_id = getattr(self, "selected_crate_id", None)
        selected = next(
            (offer for offer in offers if offer.get("id") == selected_id), None)
        if selected is None and offers:
            selected = offers[0]
        visible_rows = max(1, (left.height - 78) // 112)
        rows = (len(offers) + 1) // 2
        start = self._smooth_scroll(
            "bazaar_crates_scroll_target", max(0, rows - visible_rows))
        content_clip = pygame.Rect(
            left.left, left.top + 32, left.width, left.height - 76)
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(content_clip)
        for index in range(len(offers)):
            offer = offers[index]
            row = pygame.Rect(left.left + 8 + (index % 2) * ((left.width - 16) // 2),
                              left.top + 35 + (index // 2 - start) * 112,
                              (left.width - 24) // 2, 104)
            if not row.colliderect(content_clip):
                continue
            color = self._rarity_color(offer.get("bias", "common"))
            self._button(
                f"bazaar_crate_select:{offer['id']}", "", row.center, row.width, row.height)
            self._buttons[f"bazaar_crate_select:{offer['id']}"] = row.clip(
                content_clip)
            icon = pygame.Rect(row.left + 7, row.top + 28, 36, 35)
            pygame.draw.rect(self.screen, color, icon, border_radius=4)
            pygame.draw.line(self.screen, (35, 30, 25), (icon.left,
                             icon.centery), (icon.right, icon.centery), 3)
            pygame.draw.line(self.screen, (35, 30, 25), (icon.centerx,
                             icon.top), (icon.centerx, icon.bottom), 3)
            label = ("Elemental · " if offer.get("element")
                     else "") + offer.get("name", "Crate")
            self._text(label, (row.left + 6, row.top + 5))
            wallet = bazaar.get("wallet", {})
            for cost_index, (currency, amount) in enumerate(offer.get("costs", {}).items()):
                currency_icon = pygame.Rect(
                    icon.right + 5, row.top + 28 + cost_index * 21, 17, 17)
                self._draw_currency_icon(currency, currency_icon)
                self._text(f"{wallet.get(currency, 0)}/{amount}",
                           (currency_icon.right + 3, currency_icon.top))
        self.screen.set_clip(previous_clip)
        self._button("bazaar_refresh", "Refresh",
                     (left.right - 62, left.bottom - 19), 105, 28)
        if not selected:
            self._text("No crates available.",
                       (right.left + 10, right.top + 10))
            return
        self._text(selected.get("name", "Crate"),
                   (right.left + 10, right.top + 10))
        costs = selected.get('costs', {})
        self._text("Cost: " + ", ".join(f"{amount} {currency}" for currency,
                   amount in costs.items()), (right.left + 10, right.top + 34))
        self._text(selected.get("description", ""),
                   (right.left + 10, right.top + 58))
        self._text("Possible items:", (right.left + 10, right.top + 88))
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(
            right.left + 5, right.top + 110, right.width - 10, max(1, right.height - 160)))
        rewards = selected.get("rewards", [])
        reward_visible = max(1, (right.height - 160) // 32)
        reward_start = self._smooth_scroll(
            "bazaar_rewards_scroll", max(0, len(rewards) - reward_visible))
        for index in range(int(reward_start), min(len(rewards), int(reward_start) + reward_visible + 2)):
            item = rewards[index]
            if isinstance(item, str):
                item = {"name": item, "rarity": "common", "chance": 0}
            y = int(right.top + 110 + (index - reward_start) * 32)
            self._draw_rarity_icon(
                item, pygame.Rect(right.left + 10, y, 27, 27))
            self._register_item_hover(
                pygame.Rect(right.left + 10, y, right.width - 20, 27), item)
            chance = item.get("chance", 0)
            label = (f"{chance * 100:.1f}%" if chance
                     else f"Requires {item.get('luck_required', 0)} luck")
            self._text(f"{item.get('name', 'Item')} · {label}",
                       (right.left + 45, y + 5))
        self.screen.set_clip(previous_clip)
        self._button(f"bazaar_buy:{selected['id']}", "Buy crate",
                     (right.centerx, right.bottom - 23), right.width - 20, 32)
        if self._crate_roll:
            self._draw_crate_roll(rect)

    def start_crate_roll(self, reward, candidates):
        """Animate an already committed purchase; animation never rolls rewards."""
        self._crate_roll = {"reward": reward,
                            "candidates": list(candidates), "elapsed": 0.0}

    def _draw_crate_roll(self, rect):
        roll = self._crate_roll
        # The opening panel is modal, so the offers underneath cannot be hovered.
        self._hover_slots = []
        self._item_rects = {}
        roll["elapsed"] = min(3.0, roll["elapsed"] + self._frame_dt)
        elapsed = roll["elapsed"]
        panel = pygame.Rect(rect.centerx - min(300, rect.width // 2 - 8), rect.centery - 100,
                            min(600, rect.width - 16), 200)
        pygame.draw.rect(self.screen, (23, 26, 29), panel, border_radius=8)
        pygame.draw.rect(self.screen, (225, 190, 95),
                         panel, 2, border_radius=8)
        self._text("Opening crate" if elapsed < 3 else "Your reward",
                   (panel.left + 15, panel.top + 12))
        strip = pygame.Rect(panel.left + 8, panel.top +
                            38, panel.width - 16, 75)
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(strip)
        candidates = roll["candidates"] or [roll["reward"]]
        progress = 1 - (1 - elapsed / 3.0) ** 3
        position = progress * 20
        for index in range(int(position) - 4, int(position) + 5):
            item = roll["reward"] if index == 20 else candidates[index %
                                                                 len(candidates)]
            x = int(panel.centerx + (index - position) * 84 - 28)
            self._draw_rarity_icon(item, pygame.Rect(x, strip.top + 5, 56, 56))
        self.screen.set_clip(previous_clip)
        pygame.draw.line(self.screen, (255, 220, 75), (panel.centerx,
                         strip.top), (panel.centerx, strip.bottom), 2)
        if elapsed >= 3:
            self._text(roll["reward"].get("name", "Item"),
                       (panel.left + 15, panel.top + 121))
            self._register_item_hover(
                pygame.Rect(panel.centerx - 28, strip.top + 5, 56, 56),
                roll["reward"],
            )
        self._buttons = {}
        self._button("crate_roll_skip", "Skip" if elapsed <
                     3 else "Continue", (panel.centerx, panel.bottom - 25), 150, 30)

    def _draw_bazaar_owned(self, rect, state, tab):
        items = state.get("items", [])
        selected = next((item for item in items if str(
            item.get("id")) == str(self.selected_item_id)), None)
        left = pygame.Rect(rect.left + 5, rect.top + 5,
                           int(rect.width * .45) - 10, rect.height - 10)
        right = pygame.Rect(left.right + 10, rect.top + 5,
                            rect.right - left.right - 15, rect.height - 10)
        for panel in (left, right):
            pygame.draw.rect(self.screen, (46, 46, 46), panel, border_radius=5)
            pygame.draw.rect(self.screen, (105, 105, 105),
                             panel, 1, border_radius=5)
        self._text("Inventory", (right.left + 10, right.top + 8))
        self._draw_inventory_grid(items, right)
        titles = {"fusion": "Fusion", "rarity_upgrader": "Rarity upgrade",
                  "level_upgrader": "Level upgrade", "sell": "Sell item"}
        self._text(titles.get(tab, "Item"), (left.left + 10, left.top + 8))
        if tab == "fusion":
            self._draw_fusion_table(left, state, items)
            return
        if not selected:
            self._text("Select an item from your inventory.",
                       (left.left + 10, left.top + 36))
            return
        if tab == "rarity_upgrader":
            self._draw_rarity_gamble(left, selected, state)
            return
        previous_clip = self.screen.get_clip()
        details = pygame.Rect(left.left + 8, left.top + 34, left.width - 16,
                              max(20, left.height - 132))
        self._scroll_regions["bazaar_detail_scroll"] = details.copy()
        detail_width = left.width - 20
        description_rows = len(self._codex_wrap(selected.get("description", ""), detail_width))
        visible_stats = [key for key in selected.get("stats", {})
                         if key not in {"element", "script", "cast_type", "bullet_type", "automatic"}]
        height = (96 + (18 * description_rows + 4 if description_rows else 0)
                  + 20 * len(visible_stats)
                  + 20 * bool(selected.get("armor_slot"))
                  + 20 * bool(selected.get("armor_set"))
                  + 20 * bool(selected.get("stats", {}).get("element")))
        offset = self._smooth_scroll("bazaar_detail_scroll", max(0, (height - details.height) / 20))
        self.screen.set_clip(details)
        self._draw_item_details(selected, left.left + 10,
                                details.top - offset * 20, detail_width)
        self.screen.set_clip(previous_clip)
        item_id = str(selected.get("id"))
        prices = state.get("bazaar", {}).get(
            "owned_prices", {}).get(item_id, {})
        if tab == "fusion":
            if not state.get("fusion_unlocked", False):
                self._text(
                    f"Unlocks at level {state.get('fusion_unlock_level', 50)}", (left.left + 10, left.bottom - 55))
            else:
                recipes = state.get("fusion_recipes", [])
                for i, recipe in enumerate(recipes):
                    y = left.bottom - 24 - (len(recipes) - 1 - i) * 34
                    if y > left.top + 100:
                        self._button(f"fusion_recipe:{recipe['id']}:{item_id}", recipe.get("name", "Fuse"),
                                     (left.centerx, y), left.width - 20, 30)
        else:
            price_key, action, label = {
                "rarity_upgrader": ("rarity", "bazaar_upgrade", "Upgrade rarity"),
                "level_upgrader": ("level", "bazaar_level", "Level up"),
                "sell": ("sell", "bazaar_sell", "Sell"),
            }[tab]
            wallet_gold = state.get("bazaar", {}).get(
                "wallet", {}).get("Gold", 0)
            self._text(f"{'Value' if tab == 'sell' else 'Owned / cost'}: {prices.get(price_key, 0) if tab == 'sell' else f'{wallet_gold} / {prices.get(price_key, 0)}'} Gold",
                       (left.left + 10, left.bottom - 64))
            if tab == "sell":
                self._text("Purchased items return a partial refund.", (left.left + 10, left.bottom - 88))
            self._button(f"{action}:{item_id}", label,
                         (left.centerx, left.bottom - 25), left.width - 20, 32)

    def _draw_fusion_table(self, rect, state, items):
        from game.systems.fusion import FusionManager

        manager = FusionManager()
        recipes = state.get("fusion_recipes", [])
        recipe = next((r for r in recipes if r.get(
            "id") == self.fusion_recipe_id), None)
        self._button("fusion_codex", "Close codex" if self.fusion_codex else "Open fusion codex",
                     (rect.centerx, rect.top + 38), rect.width - 20, 28)
        if self.fusion_codex:
            self._scroll_regions["fusion_catalog_scroll"] = rect.copy()
            self._text("Choose a recipe; green ingredients are owned.",
                       (rect.left + 10, rect.top + 58))
            visible = max(1, (rect.height - 90) // 80)
            offset = self._smooth_scroll(
                "fusion_catalog_scroll", max(0, len(recipes) - visible))
            content_clip = pygame.Rect(
                rect.left, rect.top + 80, rect.width, rect.height - 84)
            previous_clip = self.screen.get_clip()
            self.screen.set_clip(content_clip)
            for i in range(int(offset), min(len(recipes), int(offset) + visible + 2)):
                entry = recipes[i]
                y = int(rect.top + 82 + (i - offset) * 80)
                self._button(f"fusion_select:{entry['id']}",
                             f"{entry['name']} (player Lv {entry.get('unlock_level', 1)})",
                             (rect.centerx, y + 10), rect.width - 20, 25)
                self._buttons[f"fusion_select:{entry['id']}"] = self._buttons[f"fusion_select:{entry['id']}"].clip(
                    content_clip)
                self._register_item_hover(
                    self._buttons[f"fusion_select:{entry['id']}"], entry)
                requirements = entry.get(
                    "required_elements") or entry.get("required_types", [])
                for j, requirement in enumerate(requirements):
                    definition = manager.recipe_by_id(entry['id'])
                    owned = any(item.get('status') not in {'active', 'supplement', 'combination_base'}
                                and manager.is_valid_candidate(item, 'ability' if entry.get('required_elements') else requirement, definition)
                                and (not entry.get('required_elements') or item.get('stats', {}).get('element') == requirement)
                                and (not entry.get('required_fusion') or requirement != 'relic' or item.get('fusion_recipe') == entry['required_fusion'])
                                for item in items)
                    badge = pygame.Rect(rect.left + 10 + j * min(60, (rect.width - 20) // max(1, len(
                        requirements))), y + 27, min(56, (rect.width - 24) // max(1, len(requirements))), 25)
                    pygame.draw.rect(self.screen, (70, 190, 95)
                                     if owned else (190, 70, 70), badge, 2)
                    badge_item = {'type': 'ability' if entry.get('required_elements') else requirement,
                                  'stats': {'element': requirement} if entry.get('required_elements') else {}}
                    self._draw_item_icon(badge_item, pygame.Rect(
                        badge.left + 2, badge.top + 3, 17, 17))
                    self._text(str(requirement).title()[
                               :5], (badge.left + 20, badge.top + 5))
                    requirement_name = (f"{str(requirement).title()} ability"
                                        if entry.get('required_elements')
                                        else str(requirement).title())
                    if entry.get('required_fusion') and requirement == 'relic':
                        requirement_name = entry['required_fusion'].replace('-', ' ').title()
                    status = "You have a valid ingredient." if owned else "No valid ingredient owned."
                    requirement_info = {
                        'name': requirement_name,
                        'rarity': entry.get('min_rarity', 'common'),
                        'tooltip_subtitle': 'Fusion ingredient requirement',
                        'description': (f"{status} Requires {entry.get('min_rarity', 'common')} "
                                        f"rarity or higher and item level {entry.get('min_level', 1)} or higher."),
                    }
                    self._register_item_hover(badge, requirement_info)
                description = entry.get('description', '')
                self._text(
                    description[:max(10, (rect.width - 20) // 8)], (rect.left + 10, y + 55))
            self.screen.set_clip(previous_clip)
            return
        if not recipe:
            self._text("Open the codex to choose a recipe.",
                       (rect.left + 10, rect.top + 75))
            return
        definition = manager.recipe_by_id(recipe['id'])
        self._text(recipe['name'], (rect.left + 10, rect.top + 72))
        self._text(recipe.get('description', '')[
                   :max(15, (rect.width - 20) // 8)], (rect.left + 10, rect.top + 94))
        self._text(f"Requires {recipe.get('min_rarity', 'common')}+ items, level {recipe.get('min_level', 1)}+",
                   (rect.left + 10, rect.top + 114))
        requirements = recipe.get(
            'required_elements') or recipe.get('required_types', [])
        size = min(52, max(32, (rect.width - 24) // max(1, len(requirements))))
        for index, requirement in enumerate(requirements):
            slot = pygame.Rect(rect.left + 10 + index * size,
                               rect.top + 155, size - 4, size - 4)
            self._drop_targets[f'fusion_slot:{index}'] = slot
            self._buttons[f'fusion_remove:{index}'] = slot
            pygame.draw.rect(self.screen, (70, 70, 70), slot)
            pygame.draw.rect(self.screen, (160, 160, 160), slot, 2)
            item_id = self.fusion_sources[index] if index < len(
                self.fusion_sources) else None
            ingredient = next((i for i in items if str(
                i.get('id')) == str(item_id)), None)
            if ingredient:
                self._draw_rarity_icon(ingredient, slot.inflate(-6, -6))
                self._register_item_hover(slot, ingredient)
            self._text(str(requirement)[:7], (slot.left, slot.bottom + 3))
        for item in items:
            item_id = str(item.get('id'))
            slot = self._item_rects.get(item_id)
            if not slot or item.get('status') in {'active', 'supplement', 'combination_base'}:
                continue
            valid = any(manager.is_valid_candidate(item, kind, definition)
                        for kind in recipe.get('required_types', []))
            if recipe.get('required_elements'):
                valid = valid and item.get('stats', {}).get(
                    'element') in recipe['required_elements']
            if valid:
                pygame.draw.rect(self.screen, (65, 230, 100), slot, 3)
        self._text("Drag ingredients from inventory. Click a slot to remove it.",
                   (rect.left + 10, rect.top + 225))
        ids = ','.join(str(value) for value in self.fusion_sources if value)
        self._button(f"fusion_craft:{recipe['id']}:{ids}", "Fuse",
                     (rect.centerx, rect.bottom - 24), rect.width - 20, 32)
        result = getattr(self, 'fusion_last_result', None)
        if result:
            self._text(f"Created: {result.get('name', 'Fusion')}",
                       (rect.left + 10, rect.bottom - 65))
            self._draw_rarity_icon(result, pygame.Rect(
                rect.right - 60, rect.bottom - 108, 42, 42))
            self._register_item_hover(
                pygame.Rect(rect.right - 60, rect.bottom - 108, 42, 42), result)

    def _draw_rarity_gamble(self, rect, item, state):
        wallet = state.get("bazaar", {}).get("wallet", {})
        names = list(wallet)
        rank = RARITY_ORDER.index(str(item.get("rarity", "common")).lower())
        targets = RARITY_ORDER[rank + 1:]
        x, y = rect.left + 10, rect.top + 37
        self._text(
            f"{item.get('name', 'Item')} · {self._item_rarity_label(item)}", (x, y))
        y += 28
        if not targets:
            self._text("This item has reached the highest rarity.", (x, y))
            return
        if not names:
            self._text("No currencies available.", (x, y))
            return
        self._rarity_target = max(
            0, min(self._rarity_target, len(targets) - 1))
        target_index = int(self._rarity_target)
        upper_percent = round((self._rarity_target - target_index) * 100)
        if upper_percent == 100:
            target_index += 1
            upper_percent = 0
        target = targets[target_index]
        if upper_percent and target_index + 1 < len(targets):
            target += "~" + targets[target_index + 1] + f"~{upper_percent}"
        currency = names[self._rarity_currency % len(names)]
        target_label = target.title(
        ) if not upper_percent else f"{targets[target_index].title()} {100-upper_percent}% / {targets[target_index+1].title()} {upper_percent}%"
        self._text(f"Target: {target_label}", (x, y))
        y += 18
        self._draw_economy_slider("target", pygame.Rect(
            x + 8, y, rect.width - 36, 20), self._rarity_target / max(1, len(targets) - 1), len(targets))
        y += 28
        dropdown_y = y
        self._button("rarity_ui_dropdown", f"{currency}  |  owned: {wallet[currency]}  v", (
            rect.centerx, y + 13), rect.width - 20, 27)
        y += 34
        affinity = currency_affinity(item, currency)
        label = "Favorable" if affinity > 1 else "Unfavorable" if affinity < 1 else "Regular"
        pool_amount = min(self._rarity_pool.get(
            currency, 0), int(wallet[currency]))
        self._rarity_pool[currency] = pool_amount
        self._text(f"{label} ({affinity:g}x) · Pool: {pool_amount}", (x, y))
        y += 19
        self._draw_economy_slider("pool", pygame.Rect(
            x + 8, y, rect.width - 36, 20), pool_amount / max(1, int(wallet[currency])))
        y += 23
        pool = {name: amount for name,
                amount in self._rarity_pool.items() if amount}
        chance = rarity_chance(item, target, pool, state.get('luck', 0))
        self._text(f"Pool: {', '.join(f'{v} {k}' for k,
                   v in pool.items()) or 'empty'}"[:55], (x, y))
        y += 22
        self._text(
            f"Success: {chance * 100:.1f}% (pool spent on success or failure)", (x, y))
        y += 30
        encoded = ','.join(f'{name}={amount}' for name, amount in pool.items())
        self._button(f"bazaar_gamble:{item['id']}:{target}:{encoded}", "Attempt upgrade", (
            rect.centerx, min(y, rect.bottom - 22)), rect.width - 20, 32)
        if self._rarity_dropdown_open:
            count = max(1, (rect.bottom - dropdown_y - 30) // 25)
            offset = self._smooth_scroll(
                "_rarity_dropdown_scroll", max(0, len(names) - count))
            popup = pygame.Rect(x, dropdown_y + 27,
                                rect.width - 20, count * 25)
            self._scroll_regions["_rarity_dropdown_scroll"] = popup.copy()
            for key, button_rect in list(self._buttons.items()):
                if key != "rarity_ui_dropdown" and button_rect.colliderect(popup):
                    del self._buttons[key]
            pygame.draw.rect(self.screen, (28, 32, 30), popup)
            pygame.draw.rect(self.screen, (175, 175, 175), popup, 1)
            previous_clip = self.screen.get_clip()
            self.screen.set_clip(popup)
            for index in range(int(offset), min(len(names), int(offset) + count + 1)):
                name = names[index]
                key = f"rarity_ui_choose:{index}"
                self._button(key, f"{name}: {wallet[name]}", (
                    popup.centerx, popup.top + 12 + (index - offset) * 25), popup.width - 2, 24)
                self._buttons[key] = self._buttons[key].clip(popup)
            self.screen.set_clip(previous_clip)

    def _rarity_color(self, rarity):
        """Get color for rarity."""
        colors = {
            "common": (180, 180, 180),
            "uncommon": (50, 205, 50),
            "rare": (30, 144, 255),
            "epic": (150, 75, 200),
            "legendary": (255, 215, 0),
            "mythical": (220, 20, 60),
            "ultimate": (255, 105, 180)
        }
        return colors.get(str(rarity).lower(), (180, 180, 180))

    def _rarity_rank(self, rarity):
        """Get rarity rank (0-6)."""
        order = ["common", "uncommon", "rare", "epic",
                 "legendary", "mythical", "ultimate"]
        return order.index(str(rarity).lower()) if str(rarity).lower() in order else 0

    def _wrap_text(self, text_surf, max_width):
        """Wrap text to fit within max_width."""
        words = text_surf.get_text().split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            test_surf = self.font.render(
                test_line, True, text_surf.get_color())
            if test_surf.get_width() <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # Render wrapped lines
        result_surf = pygame.Surface(
            (max_width, len(lines) * text_surf.get_height()), pygame.SRCALPHA)
        for i, line in enumerate(lines):
            line_surf = self.font.render(line, True, text_surf.get_color())
            result_surf.blit(line_surf, (0, i * text_surf.get_height()))

        return result_surf

    def _draw_game_ui(self, state):
        """Scale the entire combat HUD proportionally with monitor resolution."""
        physical_screen = self.screen
        physical_width, physical_height = self.screen_width, self.screen_height
        scale = max(1.0, min(physical_width / 800, physical_height / 450))
        virtual_size = (round(physical_width / scale), round(physical_height / scale))
        self._hover_slots = []
        self._item_rects = {}
        self._scroll_regions = {}
        if scale == 1:
            self._draw_game_ui_unscaled(state)
            return
        canvas = pygame.Surface(virtual_size, pygame.SRCALPHA)
        try:
            self.screen = canvas
            self.screen_width, self.screen_height = virtual_size
            self._draw_game_ui_unscaled(state)
        finally:
            self.screen = physical_screen
            self.screen_width, self.screen_height = physical_width, physical_height
        physical_screen.blit(pygame.transform.smoothscale(canvas, (physical_width, physical_height)), (0, 0))

        def scaled(rect):
            return pygame.Rect(round(rect.x * scale), round(rect.y * scale),
                               round(rect.width * scale), round(rect.height * scale))

        self._buttons = {key: scaled(rect) for key, rect in self._buttons.items()}
        self._hover_slots = [(scaled(rect), item) for rect, item in self._hover_slots]
        self._scroll_regions = {key: scaled(rect) for key, rect in self._scroll_regions.items()}

    def _draw_game_ui_unscaled(self, state):
        self._buttons = {}
        if "currency_up" in state.get("actions", []):
            self.currency_offset = max(0, self.currency_offset - 1)
        if "currency_down" in state.get("actions", []):
            self.currency_offset += 1
        left, right, top, bottom = 14, self.screen_width-14, 12, self.screen_height-12
        self._text(
            f"Absolute Score: {state.get('absolute_score', 0)}", (left, top))
        self._text(
            f"Total Score: {state.get('total_score', 0)}", (left, top+22))
        if state.get("infinity_milestone_reached", False):
            milestone = self.font.render(
                "INFINITY MILESTONE REACHED - SCORE IS FINITE",
                True,
                (105, 235, 135),
            )
            self.screen.blit(
                milestone,
                milestone.get_rect(center=(self.screen_width // 2, top + 44)),
            )
        elapsed_ms = int(state.get("run_elapsed_ms", self.get_elapsed_ms()))
        minutes = elapsed_ms // 60_000
        seconds = (elapsed_ms // 1_000) % 60
        milliseconds = elapsed_ms % 1_000
        self._text(
            f"Timer {minutes:02d}:{seconds:02d}:{milliseconds:03d}", (left, top+44))
        self._text(
            f"Enemy scale {state.get('enemy_scale', '1')}× | Next kill score {state.get('kill_score_multiplier', '1')}×",
            (left, top + 66),
        )
        active = state.get("active_slots", {})
        by_id = {str(item.get("id")): item for item in state.get("items", [])}
        for i in range(10):
            rect = pygame.Rect(0, 0, 34, 34)
            rect.midbottom = (self.screen_width//2+int((i-4.5)*40), bottom)
            self._buttons[f"ability_cast:{i}"] = rect.copy()
            item_id = active.get("abilities", [])[i] if i < len(
                active.get("abilities", [])) else None
            item = by_id.get(str(item_id)) if item_id else None
            pygame.draw.rect(self.screen, (105, 105, 105), rect, 2)
            if item:
                self._register_item_hover(rect, item)
                pygame.draw.rect(self.screen, (70, 220, 115), rect, 2)
                self._draw_rarity_icon(item, rect.inflate(-8, -8))
                self._draw_combo_markers(rect, item)
                self._draw_cooldown_overlay(
                    rect, state.get("ability_cooldowns", [0]*10)[i])
            self._text(str((i + 1) % 10), (rect.left + 2, rect.top + 1))
        for i in range(5):
            rect = pygame.Rect(0, 0, 34, 34)
            rect.topleft = (left, top+95+i*38)
            pygame.draw.rect(self.screen, (105, 105, 105), rect, 2)
            item_id = active.get("armor", [])[i] if i < len(
                active.get("armor", [])) else None
            item = by_id.get(str(item_id)) if item_id else None
            if item:
                self._register_item_hover(rect, item)
                pygame.draw.rect(self.screen, (70, 220, 115), rect, 2)
                self._draw_rarity_icon(item, rect.inflate(-8, -8))
                self._draw_combo_markers(rect, item)
        for i in range(2):
            rect = pygame.Rect(0, 0, 34, 34)
            rect.topleft = (left + 42, top + 95 + i * 38)
            pygame.draw.rect(self.screen, (105, 105, 105), rect, 2)
            item_id = active.get("weapons", [])[i] if i < len(
                active.get("weapons", [])) else None
            item = by_id.get(str(item_id)) if item_id else None
            if item:
                self._register_item_hover(rect, item)
                pygame.draw.rect(self.screen, (70, 220, 115), rect, 2)
                self._draw_rarity_icon(item, rect.inflate(-8, -8))
                self._draw_combo_markers(rect, item)
                self._draw_cooldown_overlay(
                    rect, state.get("weapon_cooldowns", [0, 0])[i])
        self._button("pause", "Resume" if state.get("paused")
                     else "Pause", (right-60, top+18), 100, 34)
        engineering = state.get("engineering")
        if engineering:
            objective = getattr(engineering, "objective", None)
            if objective:
                self._text(f"Core: {objective.health} / {objective.max_health}",
                           (right - 220, top + 87))
            self._text(f"Wave {getattr(engineering, 'wave', 1)} · "
                       f"{getattr(engineering, 'wave_kills', 0)} / {getattr(engineering, 'wave_target', 0)}",
                       (right - 220, top + 108))
        quest_checks = [
            quest for quest in state.get("quests", [])
            if quest.get("status") == "active"
        ]
        self._text("Quests", (right-105, self.screen_height//2-75))
        if not quest_checks:
            self._text("- No active quests",
                       (right-105, self.screen_height//2-48))
        else:
            for index, quest in enumerate(quest_checks[:3]):
                progress = float(quest.get("progress", 0.0))
                target = float(quest.get("target", 1.0))
                label = f"{quest.get('name', 'Quest')}: {progress:.0f}/{target:.0f}"
                self._text(f"- {label}", (right-170,
                           self.screen_height//2-48 + index * 28))
        self._button("inventory", "Inventory", (right-60, bottom-100), 100, 34)
        self._button("upgrades", "Upgrades", (right-60, bottom-58), 100, 34)
        wallet = state.get("currency", {})
        currency_left = left
        currency_rows = list(wallet.items())
        visible_currencies = min(5, len(currency_rows))
        self.currency_offset = min(self.currency_offset, max(
            0, len(currency_rows)-visible_currencies))
        clip = pygame.Rect(currency_left, bottom-42 -
                           (visible_currencies-2)*20, 190, visible_currencies*20)
        self._text("Currencies", (currency_left, clip.top-20))
        self.screen.set_clip(clip)
        for i, (name, amount) in enumerate(currency_rows[self.currency_offset:self.currency_offset+visible_currencies]):
            self._text(f"{name}: {amount}", (currency_left, clip.top+i*20))
        self.screen.set_clip(None)
        self._scroll_regions["hud_currency"] = clip
        self._draw_notifications(state)
        if state.get("paused") or self.panel:
            title = "Paused" if state.get("paused") and not self.panel else (
                self.panel or "Panel").title()
            overlay = pygame.Surface(
                (self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            self.screen.blit(overlay, (0, 0))
            title_s = pygame.font.Font(None, 44).render(
                title, True, (250, 250, 250))
            self.screen.blit(title_s, title_s.get_rect(
                center=(self.screen_width//2, self.screen_height//2-20)))
            self._button("close_panel", "Resume" if title == "Paused" else "Close",
                         (self.screen_width//2, self.screen_height//2+30))
            if state.get("paused") and not self.panel:
                for i, (key, label) in enumerate((("inventory", "Inventory"), ("quests", "Quests"), ("upgrades", "Upgrades"), ("bazaar", "Bazaar"))):
                    self._button(f"tab_{key}", label, (self.screen_width //
                                 2+(i-1)*112, self.screen_height//2+85), 104, 30)

    def _draw_notifications(self, state):
        for i, item in enumerate(state.get("notifications", [])):
            alpha = max(0, min(255, int(255*item['remaining']/3)))
            surf = self._currency_text_surface(item['text'], (255, 220, 110))
            surf.set_alpha(alpha)
            rect = surf.get_rect(midtop=(self.screen_width//2, 54+i*25))
            background = pygame.Surface(
                (rect.width+16, rect.height+8), pygame.SRCALPHA)
            background.fill((10, 15, 12, 225))
            self.screen.blit(background, (rect.x-8, rect.y-4))
            self.screen.blit(surf, rect)

    def _text(self, value, pos):
        self.screen.blit(self._currency_text_surface(
            str(value), (240, 240, 245)), pos)

    def _currency_text_surface(self, text, color):
        """Draw a small currency icon beside every currency name in UI text."""
        pieces = self._currency_pattern.split(str(text))
        rendered = [(piece, self.font.render(piece, True, color))
                    for piece in pieces if piece]
        icon_size = 14
        width = sum(surf.get_width() + (icon_size + 3 if currency_definition(piece) else 0)
                    for piece, surf in rendered)
        surface = pygame.Surface(
            (max(1, width), max(18, self.font.get_height())), pygame.SRCALPHA)
        previous_screen = self.screen
        self.screen = surface
        try:
            x = 0
            for piece, glyph in rendered:
                if currency_definition(piece):
                    self._draw_currency_icon(
                        piece, pygame.Rect(x, 1, icon_size, icon_size))
                    x += icon_size + 3
                surface.blit(glyph, (x, 0))
                x += glyph.get_width()
        finally:
            self.screen = previous_screen
        return surface

    def _draw_combo_markers(self, rect, item):
        slots = item.get("combinations", [])[:5]
        marker = 4
        gap = 1
        start = rect.centerx-(len(slots)*(marker+gap)-gap)//2
        for index, combo_id in enumerate(slots):
            square = pygame.Rect(start+index*(marker+gap),
                                 rect.bottom-marker-2, marker, marker)
            pygame.draw.rect(self.screen, (245, 200, 70) if combo_id is not None else (
                135, 140, 155), square, 1)

    def _draw_cooldown_overlay(self, rect, remaining):
        if remaining <= 0:
            ready = self.font.render("RDY", True, (225, 225, 225))
            self.screen.blit(ready, ready.get_rect(
                center=(rect.centerx, rect.bottom-8)))
            return
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        self.screen.blit(overlay, rect.topleft)
        label = self.font.render(f"{remaining:.1f}", True, (245, 245, 245))
        self.screen.blit(label, label.get_rect(center=rect.center))

    def close(self):
        pygame.quit()
