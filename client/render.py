import math

import pygame

from client.input import InputHandler
from game.systems.elements import ELEMENTS, element_label, normalize_element
from game.systems.enemy_visibility import enemy_visibility_alpha


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

        self.screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
        pygame.display.set_caption("Chance Survivors")

        self.font = pygame.font.Font(None, 20)
        self.clock = pygame.time.Clock()

        self.bullet_size = (16, 6)
        self.bullet_color = (255, 220, 50)

        self.start_time = pygame.time.get_ticks()

        # Input handler
        self.input_handler = InputHandler()
        self.mode = "MENU"
        self.panel = None
        self.resolutions = [(800, 450), (1280, 720), (1600, 900), (1920, 1080)]
        self.resolution_index = 0
        self.fullscreen = False
        self.bonus_pct = 0
        self._buttons = {}
        self._item_rects = {}
        self._drop_targets = {}
        self._inventory_rect = None
        self._name_entry = None
        self.currency_offset = 0
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
        self._bazaar_tab = "market"
        self._frame_dt = 1 / 60
        self._drag_item_id = None
        self._drop_targets = {}
        self._rarity_icon_cache = {}
        self._drag_origin = None

    def process_events(self) -> tuple[bool, list[tuple[float, float]], list[str]]:
        """Process all pygame events.

        Returns:
            Tuple of (running, shots, actions).
        """
        running, shots, actions = self.input_handler.process_events()
        dragged_this_frame = self.input_handler.drag_release is not None
        current_size = self.screen.get_size()
        if current_size != (self.screen_width, self.screen_height):
            self.screen_width, self.screen_height = current_size
        for pos in shots:
            if self._name_entry and self._name_entry.collidepoint(pos):
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
            for name, rect in self._buttons.items():
                if rect.collidepoint(pos):
                    actions.append(name)
            if self.mode == "PLAYING" and self.panel:
                for slot_key, rect in self._drop_targets.items():
                    if rect.collidepoint(pos):
                        if slot_key.startswith("item:"):
                            actions.append(f"select:{slot_key.split(':',1)[1]}")
                        break
        if self.mode == "PLAYING" and self.panel in ("inventory", "upgrades") and self.input_handler.click_release:
            released_at=self.input_handler.click_release
            for name,rect in self._item_rects.items():
                if rect.collidepoint(released_at):
                    actions.append(f"select:{name}")
                    break
            self.input_handler.click_release=None
        if self.mode == "PLAYING" and self.panel and self.input_handler.drag_active:
            source_pos=self.input_handler.drag_start
            self._drag_item_id=next((item_id for item_id,rect in self._item_rects.items() if rect.collidepoint(source_pos)),None)
        if self.mode == "PLAYING" and self.panel and self.input_handler.drag_release:
            source_pos,target_pos=self.input_handler.drag_release
            actions=[action for action in actions if not action.startswith(("combine:","equip:"))]
            source_item=next((item_id for item_id,rect in self._item_rects.items() if rect.collidepoint(source_pos)),None)
            target=next((key for key,rect in self._drop_targets.items() if rect.collidepoint(target_pos)),None)
            source_slot=next((key for key,rect in self._drop_targets.items() if rect.collidepoint(source_pos)),None)
            # Visual feedback for valid/invalid drops
            if self.upgrade_tab == "combination" and source_item and target and target.startswith("combo:"):
                _,base_id,combo_index=target.split(":",2)
                base_item=next((item for item in self._last_state.get("items",[]) if str(item.get("id"))==base_id),None)
                if base_item:
                    # Check if item can be used as supplement
                    valid_drop=self._is_valid_combination_supplement(base_item, source_item)
                    if valid_drop:
                        # Draw green highlight on valid drop target
                        target_rect=self._drop_targets.get(target)
                        if target_rect:
                            pygame.draw.rect(self.screen,(100,255,100),target_rect,2,border_radius=3)
                    else:
                        # Draw red highlight on invalid drop target
                        target_rect=self._drop_targets.get(target)
                        if target_rect:
                            pygame.draw.rect(self.screen,(255,100,100),target_rect,2,border_radius=3)
            if source_item and target:
                if target.startswith("combo:"):
                    _,base_id,combo_index=target.split(":",2)
                    actions.append(f"combine:{base_id}:{combo_index}:{source_item}")
                else:
                    slot_kind,slot_index=target.split(":",1)
                    actions.append(f"equip:{slot_kind}:{slot_index}:{source_item}")
            elif source_slot and target and not source_slot.startswith("combo:") and not target.startswith("combo:"):
                source_kind,source_index=source_slot.split(":",1)
                target_kind,target_index=target.split(":",1)
                source_ids=self._last_state.get("active_slots",{}).get(source_kind,[])
                source_item=source_ids[int(source_index)] if int(source_index)<len(source_ids) else None
                if source_item:
                    actions.append(f"equip:{target_kind}:{target_index}:{source_item}")
            elif source_slot and source_slot.startswith("combo:") and not (target and target.startswith("combo:")):
                _,base_id,combo_index=source_slot.split(":",2)
                actions.append(f"uncombine:{base_id}:{combo_index}")
            elif source_slot and source_slot.startswith("combo:") and target and target.startswith("combo:"):
                _,source_base,source_index=source_slot.split(":",2)
                source_item_id=None
                for item in self._last_state.get("items",[]):
                    if item.get("id")==source_base:
                        source_item_id=item.get("combinations",[])[int(source_index)]
                        break
                if source_item_id:
                    _,base_id,combo_index=target.split(":",2)
                    actions.append(f"combine:{base_id}:{combo_index}:{source_item_id}")
            elif source_slot and self._inventory_rect and self._inventory_rect.collidepoint(target_pos):
                slot_kind,slot_index=source_slot.split(":",1)
                actions.append(f"unequip:{slot_kind}:{slot_index}")
            self.input_handler.drag_release=None
            self._drag_item_id=None
        for action in actions:
            if action.startswith("tab_"):
                self.menu_tab = action[4:]
            elif action.startswith("upgrade_"):
                self.upgrade_tab = action[8:]
            elif action.startswith("bazaar_tab_"):
                self._bazaar_tab = action[11:]
            elif action.startswith("select:"):
                self.selected_item_id = action.split(":",1)[1]
                if (self.panel == "upgrades" and self.menu_tab == "upgrades"
                        and self.upgrade_tab == "combination" and not dragged_this_frame):
                    item = next((entry for entry in getattr(self,"_last_state",{}).get("items",[])
                                 if str(entry.get("id")) == self.selected_item_id),None)
                    if item and item.get("type") in ("armor","weapon","ability"):
                        self.selected_base_id=self.selected_item_id
            elif action == "apply_combination" and self.panel and self.upgrade_tab == "combination" and self.selected_base_id:
                # Apply the combination by updating the base item with all filled slots
                items=self._last_state.get("items",[])
                base_item=next((item for item in items if str(item.get("id"))==self.selected_base_id),None)
                if base_item:
                    # Collect all filled combination slots
                    filled_slots=[sid for sid in base_item.get("combinations",[]) if sid is not None]
                    # Create a new combined item with aggregated stats
                    from game.systems.combination import CombinationEvaluator
                    evaluator=CombinationEvaluator()
                    supplements=[next((item for item in items if str(item.get("id"))==sid),None) for sid in filled_slots]
                    supplements=[s for s in supplements if s]
                    evaluation=evaluator.evaluate_combination(base_item,supplements)
                    # Create combined item
                    combined_item=dict(base_item)
                    combined_item["id"]=f"combined_{base_item['id']}_{pygame.time.get_ticks()}"
                    combined_item["name"]=f"{base_item.get('name','')} (Combined)"
                    combined_item["stats"]=evaluation.get("final_stats",dict(base_item.get("stats",{})))
                    combined_item["combinations"]=[]
                    combined_item["status"]="normal"
                    # Add to inventory
                    actions.append(f"spawn_item:{combined_item['id']}")
                    # Remove supplements from inventory
                    for sup in supplements:
                        actions.append(f"remove_item:{sup['id']}")
                    # Update base item to show it's been combined
                    base_item["status"]="combination_base"
                    base_item["combined"]=True
            elif action == "inventory_up" and self.panel:
                self.inventory_scroll_target = max(0,self.inventory_scroll_target-3)
                if self.menu_tab == "bazaar":
                    self.bazaar_market_scroll_target = max(
                        0.0, self.bazaar_market_scroll_target - 1
                    )
                    self.bazaar_owned_scroll_target = max(
                        0.0, self.bazaar_owned_scroll_target - 1
                    )
                    self.bazaar_crates_scroll_target = max(
                        0.0, self.bazaar_crates_scroll_target - 1
                    )
            elif action == "inventory_down" and self.panel:
                self.inventory_scroll_target += 3
                if self.menu_tab == "bazaar":
                    self.bazaar_market_scroll_target += 1
                    self.bazaar_owned_scroll_target += 1
                    self.bazaar_crates_scroll_target += 1
            elif action == "bazaar_market_up" and self.panel:
                self.bazaar_market_scroll_target = max(0.0, self.bazaar_market_scroll_target - 1)
            elif action == "bazaar_market_down" and self.panel:
                self.bazaar_market_scroll_target += 1
            elif action == "bazaar_crates_up" and self.panel:
                self.bazaar_crates_scroll_target = max(0.0, self.bazaar_crates_scroll_target - 1)
            elif action == "bazaar_crates_down" and self.panel:
                self.bazaar_crates_scroll_target += 1
            elif action == "currency_up" and self.panel:
                self.inventory_scroll_target=max(0,self.inventory_scroll_target-3)
            elif action == "currency_down" and self.panel:
                self.inventory_scroll_target+=3
        if self.mode != "PLAYING" or self.panel:
            self.input_handler.fire_events=[]
            self.input_handler.mouse_buttons_held.clear()
            self.input_handler.held_fire=False
        else:
            ui_buttons=[button for button,pos in self.input_handler.fire_events
                        if any(rect.collidepoint(pos) for rect in self._buttons.values())]
            for button in ui_buttons:
                self.input_handler.mouse_buttons_held.discard(button)
            self.input_handler.held_fire=bool(self.input_handler.mouse_buttons_held)
            self.input_handler.fire_events=[
                (button,pos) for button,pos in self.input_handler.fire_events
                if button not in ui_buttons
            ]
        shots = [] if self.mode != "PLAYING" or self.panel else shots
        return running, shots, actions

    def set_view(self, mode: str, panel=None):
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
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), flags)

    def get_movement(self) -> tuple[float, float]:
        """Get player movement."""
        return self.input_handler.get_movement()

    def get_mouse_position(self) -> tuple[float, float]:
        """Get mouse position."""
        return self.input_handler.get_mouse_position()

    def tick(self, framerate):
        self._frame_dt = min(0.1,self.clock.tick(framerate) / 1000.0)
        return self._frame_dt

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

    def _draw_ability_vfx(self, effects):
        center = (self.screen_width // 2, self.screen_height // 2)
        for effect in effects:
            remaining = max(0.0, min(0.2, float(effect.get("remaining", 0.0))))
            radius = max(1, int(float(effect.get("radius", 0.0)) * self.pixels_per_unit))
            color = ELEMENTS[normalize_element(str(effect.get("element", "arcane")))]["color"]
            overlay = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(
                overlay,
                (*color, int(180 * remaining / 0.2)),
                (radius + 2, radius + 2),
                radius,
                width=3,
            )
            self.screen.blit(overlay, (center[0] - radius - 2, center[1] - radius - 2))

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

    def draw_game_over(self, state: dict) -> None:
        """Show run results and make leaderboard upload an explicit choice."""
        self._buttons = {}
        self.screen.fill((24, 34, 28))
        center_x = self.screen_width // 2
        self.screen.blit(
            pygame.font.Font(None, 48).render("Run Complete", True, (105, 235, 135)),
            (center_x - 118, 52),
        )
        lines = (
            f"Final score: {state.get('score', '0')}",
            f"Active time: {state.get('runtime', 0.0):.2f}s",
            f"Level: {state.get('level', 1)}    Luck: {state.get('luck', 0.0):.1f}",
        )
        for index, text in enumerate(lines):
            surface = self.font.render(text, True, (235, 240, 236))
            self.screen.blit(surface, surface.get_rect(center=(center_x, 138 + index * 28)))
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
        status_color = (130, 235, 150) if status.startswith("Submitted") else (240, 205, 120)
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
            self.screen.blit(status_surface, status_surface.get_rect(center=(center_x, 230 + index * 20)))
        upload_enabled = not state.get("upload_complete", False)
        if upload_enabled:
            self._button("upload_run", "Upload Score", (center_x, 310), 190, 42)
        else:
            self._button("upload_done", "Uploaded", (center_x, 310), 190, 42)
        self._button("return_menu", "Return to Menu", (center_x, 366), 190, 42)
        pygame.display.flip()

    def _button(self, key, label, center, width=210, height=42):
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center
        self._buttons[key] = rect
        pygame.draw.rect(self.screen, (68, 68, 68), rect, border_radius=6)
        pygame.draw.rect(self.screen, (145, 145, 145), rect, 2, border_radius=6)
        surf = self.font.render(label, True, (245, 245, 250))
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def draw_menu(self, error="", resume_available=False):
        self._buttons = {}
        self._item_rects = {}
        self.screen.fill((32, 32, 32))
        cx, cy = self.screen_width // 2, self.screen_height // 2
        self.screen.blit(pygame.font.Font(None, 48).render("CHANCE SURVIVORS", True, (240, 220, 120)), (cx-185, max(24, cy-155)))
        label = self.font.render("Player name", True, (235, 235, 240)); self.screen.blit(label, label.get_rect(center=(cx,cy-85)))
        self._name_entry = pygame.Rect(cx-140,cy-64,280,38)
        pygame.draw.rect(self.screen,(48,48,48),self._name_entry,border_radius=4); pygame.draw.rect(self.screen,(140,140,140),self._name_entry,2,border_radius=4)
        name = self.input_handler.player_name or "Type your name..."
        self.screen.blit(self.font.render(name,True,(240,240,245) if self.input_handler.player_name else (130,135,145)),(cx-128,cy-54))
        self._button("play", "Play", (cx,cy+8))
        if resume_available:
            self._button("resume_run", "Resume Run", (cx,cy+60))
        self._button("exit", "Exit", (cx,cy+(112 if resume_available else 60)))
        self._button("settings", "Settings", (cx, self.screen_height-36))
        if error:
            message = self.font.render(error,True,(255,110,100))
            self.screen.blit(message,message.get_rect(center=(cx,cy+(160 if resume_available else 112))))
        pygame.display.flip()

    def draw_settings(self):
        self._buttons = {}; self.screen.fill((32,32,32)); cx,cy=self.screen_width//2,self.screen_height//2
        self.screen.blit(pygame.font.Font(None,42).render("Settings",True,(240,220,120)),(cx-70,cy-130))
        w,h=self.resolutions[self.resolution_index]
        self._button("resolution",f"Resolution: {w} × {h}",(cx,cy-45),300)
        self._button("fullscreen",f"Display: {'Fullscreen' if self.fullscreen else 'Windowed'}",(cx,cy+5),300)
        self._button("apply_settings","Apply",(cx,cy+65))
        self._button("back","Back",(cx,cy+117))
        pygame.display.flip()

    def draw(self, state: dict) -> None:
        """Draw the current game state.

        Args:
            state: Dictionary containing player, bullets, enemies, and enemy_types.
        """
        self._last_state=state
        self.screen.fill((30, 30, 30))

        if self.panel:
            self._draw_game_menu(state)
            self._draw_drag_ghost(state)
            pygame.display.flip()
            return

        player = state["player"]
        bullets = state["bullets"]
        enemies = state["enemies"]
        enemy_types = state["enemy_types"]

        self.draw_grid(player.x, player.y)
        self.draw_player(player.angle, player.health, player.max_health)
        self.draw_bullets(bullets, player.x, player.y)
        self.draw_enemy_projectiles(
            state.get("enemy_projectiles", []),
            player.x,
            player.y,
        )
        self._draw_ability_vfx(state.get("ability_vfx", []))
        self.draw_enemies(enemies, enemy_types, player.x, player.y)
        self.draw_debug(state)
        self._draw_game_ui(state)

        pygame.display.flip()

    def draw_enemy_projectiles(self, projectiles, player_x, player_y):
        for projectile in projectiles:
            x, y = self.world_to_screen(
                projectile.x,
                projectile.y,
                player_x,
                player_y,
            )
            radius = max(3, int(projectile.radius))
            pygame.draw.circle(self.screen, (255, 95, 55), (int(x), int(y)), radius)
            pygame.draw.circle(self.screen, (255, 220, 150), (int(x), int(y)), max(1, radius // 2))

    def _draw_game_menu(self, state):
        self._buttons = {}
        self._item_rects = {}
        self._drop_targets = {}
        self.screen.fill((24,24,24))
        pygame.draw.rect(self.screen,(42,42,42),(0,0,self.screen_width,50))
        tabs = [("inventory", "Inventory"), ("quests", "Quests"), ("upgrades", "Upgrades"), ("bazaar", "Bazaar")]
        tab_width = min(160, (self.screen_width-112)//len(tabs))
        for i, (key, label) in enumerate(tabs):
            active = self.menu_tab == key
            self._button(f"tab_{key}", label, (12+i*tab_width+tab_width//2,25), tab_width-8, 38)
            if active:
                pygame.draw.line(self.screen,(225,225,225),(12+i*tab_width+8,47),(12+(i+1)*tab_width-16,47),3)
        self._button("close_menu", "Close", (self.screen_width-48,25), 82, 36)
        pygame.draw.line(self.screen,(125,125,125),(0,50),(self.screen_width,50),1)
        if self.menu_tab=="upgrades":
            for index,(key,label) in enumerate((("overview","Overview"),("combination","Combination"),("fusion","Fusion"))):
                self._button(f"upgrade_{key}",label,(18+index*132+62,69),124,32)
            pygame.draw.line(self.screen,(125,125,125),(0,88),(self.screen_width,88),1)
        top=96 if self.menu_tab=="upgrades" else 58
        outer=pygame.Rect(10,top,self.screen_width-20,self.screen_height-top-10)
        pygame.draw.rect(self.screen,(34,34,34),outer,border_radius=8)
        pygame.draw.rect(self.screen,(95,95,95),outer,1,border_radius=8)
        if self.menu_tab == "inventory":
            self._draw_inventory_menu(state, outer)
        elif self.menu_tab == "quests":
            self._draw_quests_menu(outer, state)
        elif self.menu_tab == "upgrades":
            self._draw_upgrades_menu(state, outer)
        else:
            self._draw_bazaar_menu(outer,state)

    def _draw_inventory_menu(self, state, outer):
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        active = state.get("active_slots", {})
        content_top, content_bottom = outer.top+8, outer.bottom-10
        panel_height = content_bottom-content_top
        stats_width = max(155, int(outer.width*.23))
        inventory_left = outer.right-int(outer.width*.43)
        stats_rect = pygame.Rect(outer.left+10, content_top, stats_width, panel_height)
        gear_width = max(170, inventory_left-stats_rect.right-16)
        gear_rect = pygame.Rect(stats_rect.right+8, content_top, gear_width, panel_height)
        grid_rect = pygame.Rect(inventory_left, content_top, outer.right-inventory_left-10, panel_height)
        self._inventory_rect=grid_rect.copy()
        for rect in (stats_rect, gear_rect, grid_rect):
            pygame.draw.rect(self.screen, (48,48,48), rect, border_radius=5)
            pygame.draw.rect(self.screen, (100,100,100), rect, 1, border_radius=5)
        self._text("Item details", (stats_rect.left+8, stats_rect.top+8))
        selected = by_id.get(str(self.selected_item_id))
        if selected:
            self._draw_item_details(selected, stats_rect.left+8, stats_rect.top+35, stats_rect.width-16)
        else:
            self._text("Select an item",(stats_rect.left+8,stats_rect.top+38))
        self._text("Equipment",(gear_rect.left+8,gear_rect.top+8))
        relic_summary = state.get("relic_summary", {})
        relic_items = [item for item in items if str(item.get("type", "")).lower() == "relic"]
        if relic_items:
            self._text("Relics", (gear_rect.left+8, gear_rect.top+28))
            y = gear_rect.top + 46
            for item in relic_items[:3]:
                stats = item.get("stats", {})
                label = f"{item.get('name', 'Relic')}: +{stats.get('luck', 0)} luck"
                self._text(label, (gear_rect.left+8, y))
                y += 16
            if relic_summary:
                self._text("Passive totals", (gear_rect.left+8, y + 6))
                y += 24
                for stat_name, total in sorted(relic_summary.items(), key=lambda pair: pair[0]):
                    if total:
                        self._text(f"{stat_name}: +{total:.1f}", (gear_rect.left+8, y))
                        y += 15
        y=gear_rect.top+27
        armor_size=min(52,(gear_rect.width-16-16)//5)
        self._text("Armor",(gear_rect.left+8,y)); y+=19
        values=active.get("armor",[])
        armor_labels = ("Boots", "Pants", "Chest", "Head", "Acc.")
        armor_label_font = pygame.font.Font(None, 14)
        for i in range(5):
            slot_x = gear_rect.left+8+i*(armor_size+4)
            label = armor_label_font.render(armor_labels[i], True, (205, 205, 210))
            self.screen.blit(label, label.get_rect(midtop=(slot_x+armor_size//2, y)))
            self._draw_active_slot(f"armor:{i}",values[i] if i<len(values) else None,by_id,
                                   (slot_x,y+12),armor_size,armor_size)
        y+=armor_size+21
        set_stats = {}
        for armor_set in state.get("armor_set_status", []):
            set_bonuses = armor_set.get("active_bonuses", {})
            for threshold, bonuses in set_bonuses.items():
                if int(threshold) <= armor_set.get("pieces", 0):
                    for stat_name, value in bonuses.items():
                        set_stats[stat_name] = set_stats.get(stat_name, 0) + value
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
        weapon_size=min(56,(gear_rect.width-24)//2)
        self._text("Weapons",(gear_rect.left+8,y)); y+=19
        values=active.get("weapons",[])
        for i in range(2):
            cooldown=state.get("weapon_cooldowns",[0,0])[i]
            self._draw_active_slot(f"weapons:{i}",values[i] if i<len(values) else None,by_id,
                                   (gear_rect.left+8+i*(weapon_size+8),y),weapon_size,weapon_size,cooldown)
        y+=weapon_size+9
        self._text("Abilities",(gear_rect.left+8,y)); y+=19
        values=active.get("abilities",[])
        slot_size=min(46,(gear_rect.width-32)//5)
        for i in range(10):
            col=i%5; row=i//5
            cooldown=state.get("ability_cooldowns",[0]*10)[i]
            self._draw_active_slot(f"abilities:{i}",values[i] if i<len(values) else None,by_id,(gear_rect.left+8+col*(slot_size+3),y+row*(slot_size+3)),slot_size,slot_size,cooldown)
        self._text(f"Inventory · {len(items)} / 200",(grid_rect.left+8,grid_rect.top+7))
        slot_size, columns, rows, visible_rows = self._inventory_grid_metrics(grid_rect)
        gap=5
        scroll_row=self._sync_inventory_scroll(rows,visible_rows)
        prior_clip=self.screen.get_clip(); self.screen.set_clip(grid_rect)
        slots_w=columns*(slot_size+gap)-gap
        slots_left=grid_rect.left+max(7,(grid_rect.width-slots_w)//2)
        for row in range(scroll_row,min(rows,scroll_row+visible_rows)):
            for col in range(columns):
                index=row*columns+col
                rect=pygame.Rect(slots_left+col*(slot_size+gap),grid_rect.top+33+(row-scroll_row)*(slot_size+gap),slot_size,slot_size)
                item=items[index] if index<len(items) else None
                color=(105,105,105)
                if item:
                    status=item.get("status", "normal")
                    color={"supplement":(245,205,55),"active":(70,220,115),"combination_base":(240,145,55)}.get(status,(105,105,105))
                    self._item_rects[str(item.get("id"))]=rect.copy()
                pygame.draw.rect(self.screen,(45,45,45),rect,border_radius=3)
                pygame.draw.rect(self.screen,color,rect,2 if item else 1,border_radius=3)
                if item:
                    icon_size=slot_size-20
                    icon=pygame.Rect(rect.centerx-icon_size//2-4,rect.centery-icon_size//2,icon_size,icon_size)
                    self._draw_rarity_icon(item,icon)
                    mini_size=6
                    for combo_index,combo_id in enumerate(item.get("combinations",[])[:5]):
                        mini=pygame.Rect(icon.right+3,rect.y+6+combo_index*(mini_size+2),mini_size,mini_size)
                        self._draw_combo_icon(mini,by_id.get(str(combo_id)) if combo_id is not None else None)
        self.screen.set_clip(prior_clip)
        self._draw_inventory_links(items, active)
        self._draw_inventory_scrollbar(grid_rect, rows, visible_rows)

    def _draw_item_details(self, item, x, y, width):
        rarity=self._item_rarity_label(item)
        icon=pygame.Rect(x,y,48,48)
        self._draw_rarity_icon(item,icon)
        self._text(item.get("name","Item"),(x+51,y)); self._text(f"{rarity} · Lv {item.get('level',1)}",(x+51,y+20))
        by_id={str(candidate.get("id")):candidate for candidate in getattr(self,"_last_state",{}).get("items",[])}
        for index,combo_id in enumerate(item.get("combinations",[])[:5]):
            mini=pygame.Rect(x+51+index*13,y+38,10,10)
            self._draw_combo_icon(mini,by_id.get(str(combo_id)) if combo_id is not None else None)
        y+=52
        self._text(f"Type: {item.get('type','misc').title()}",(x,y)); y+=22
        if item.get("armor_slot"):
            self._text(f"Armor slot: {item['armor_slot'].title()}", (x, y)); y += 20
        if item.get("armor_set"):
            self._text(f"Set: {item['armor_set'].title()}", (x, y)); y += 20
        element = item.get("stats", {}).get("element")
        if element:
            self._text(f"Element: {element_label(str(element))}", (x, y)); y += 20
        for name,value in item.get("stats",{}).items():
            if name == "element":
                continue
            self._text(f"{name}: {value}",(x,y)); y+=20

    def _draw_active_slot(self, key, item_id, by_id, pos, width, height, cooldown=None):
        rect=pygame.Rect(pos,(width,height)); self._drop_targets[key]=rect.copy()
        item=by_id.get(str(item_id)) if item_id is not None else None
        pygame.draw.rect(self.screen,(48,48,48),rect,border_radius=3)
        pygame.draw.rect(self.screen,(70,220,115) if item else (100,100,100),rect,2,border_radius=3)
        if item:
            icon_size=min(width,height)-10
            icon=pygame.Rect(rect.centerx-icon_size//2,rect.centery-icon_size//2,icon_size,icon_size)
            self._draw_rarity_icon(item,icon)
            mini_size=6; combo_slots=item.get("combinations",[])
            start=rect.centerx-(len(combo_slots)*(mini_size+2)-2)//2
            for index,combo_id in enumerate(combo_slots):
                mini=pygame.Rect(start+index*(mini_size+2),rect.bottom-mini_size-2,mini_size,mini_size)
                self._draw_combo_icon(mini,by_id.get(str(combo_id)) if combo_id is not None else None)
            if cooldown is not None:
                self._draw_cooldown_overlay(rect,cooldown)

    def _rarity_color(self, rarity):
        return {
            "common":(145,145,145), "uncommon":(58,181,83), "rare":(48,133,224),
            "epic":(158,75,204), "legendary":(246,207,58), "mythic":(220,65,65),
            "mythical":(220,65,65), "ultimate":(255,255,255),
        }.get(str(rarity).lower(),(145,145,145))

    def _item_rarity_label(self, item):
        rarity = str(item.get("rarity", "common")).title()
        if str(item.get("rarity", "")).lower() == "ultimate":
            tier = item.get("ultimate_tier", 1)
            if type(tier) is int and 1 <= tier <= 100:
                return f"Ultimate {tier}"
        return rarity

    def _draw_rarity_icon(self, rarity, rect):
        ultimate_tier = 1
        if isinstance(rarity, dict):
            ultimate_tier = rarity.get("ultimate_tier", 1)
            rarity = rarity.get("rarity", "common")
        rarity=str(rarity).lower()
        if rarity=="ultimate":
            if type(ultimate_tier) is not int or not 1 <= ultimate_tier <= 100:
                ultimate_tier = 1
            cache_key=(rect.width,rect.height,ultimate_tier)
            surface=self._rarity_icon_cache.get(cache_key)
            if surface is None:
                surface=pygame.Surface(rect.size)
                width,height=rect.size
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
                        surface.set_at((px,py),color)
                self._rarity_icon_cache[cache_key]=surface
            self.screen.blit(surface,rect)
        else:
            pygame.draw.rect(self.screen,self._rarity_color(rarity),rect)
        pygame.draw.rect(self.screen,(220,220,220),rect,1)

    def _draw_combo_icon(self, rect, item):
        if item:
            self._draw_rarity_icon(item,rect)
        else:
            pygame.draw.rect(self.screen,(90,90,90),rect)
            pygame.draw.rect(self.screen,(160,160,160),rect,1)

    def _is_valid_combination_supplement(self, base_item: dict, supplement_item: dict) -> bool:
        """Check if an item can be used as a combination supplement for a base item."""
        # Cannot combine an item with itself
        if base_item.get("id") == supplement_item.get("id"):
            return False
        # Cannot combine items of different types
        if base_item.get("type") != supplement_item.get("type"):
            return False
        # Cannot combine if base item is full
        base_combos = base_item.get("combinations", [])
        if None not in base_combos:
            return False
        # Cannot combine if supplement is already used in another combination
        for item in self._last_state.get("items", []):
            if item.get("id") == supplement_item.get("id"):
                if any(sid == supplement_item.get("id") for sid in item.get("combinations", []) if sid is not None):
                    return False
        # Cannot combine if supplement is actively equipped
        active_slots = self._last_state.get("active_slots", {})
        for kind in ("armor", "weapons", "abilities"):
            if supplement_item.get("id") in active_slots.get(kind, []):
                return False
        return True

    def _inventory_grid_metrics(self, grid_rect):
        gap=5
        columns=max(1,(grid_rect.width-18)//88)
        slot_size=max(28,min(92,(grid_rect.width-18-(columns+1)*gap)//columns))
        rows=(200+columns-1)//columns
        visible_rows=max(1,(grid_rect.height-40)//(slot_size+gap))
        return slot_size,columns,rows,visible_rows

    def _draw_inventory_scrollbar(self, grid_rect, rows, visible_rows):
        rail=pygame.Rect(grid_rect.right-8,grid_rect.top+32,4,max(1,grid_rect.height-42))
        pygame.draw.rect(self.screen,(80,80,80),rail,border_radius=2)
        thumb_h=max(18,int(rail.height*min(1,visible_rows/max(1,rows))))
        max_scroll=max(0,rows-visible_rows)
        thumb_y=rail.top+int((rail.height-thumb_h)*(self.inventory_scroll/max_scroll)) if max_scroll else rail.top
        pygame.draw.rect(self.screen,(185,185,185),(rail.x-2,thumb_y,8,thumb_h),border_radius=3)

    def _sync_inventory_scroll(self, rows, visible_rows):
        maximum=max(0,rows-visible_rows)
        self.inventory_scroll_target=max(0.0,min(float(maximum),self.inventory_scroll_target))
        self.inventory_scroll += (self.inventory_scroll_target-self.inventory_scroll)*min(1.0,self._frame_dt*12)
        if abs(self.inventory_scroll_target-self.inventory_scroll)<0.01:
            self.inventory_scroll=float(self.inventory_scroll_target)
        return int(round(self.inventory_scroll))

    def _draw_inventory_links(self, items, active_slots):
        if not self._item_rects:
            return
        centers={item_id:rect.center for item_id,rect in self._item_rects.items()}
        for kind,slot_ids in active_slots.items():
            for index,item_id in enumerate(slot_ids):
                start=centers.get(str(item_id)); target=self._drop_targets.get(f"{kind}:{index}")
                if start and target:
                    pygame.draw.line(self.screen,(175,175,175),start,target.center,1)
        for item in items:
            base=centers.get(str(item.get("id")))
            if base:
                for supplement_id in item.get("combinations",[]):
                    supplement=centers.get(str(supplement_id)) if supplement_id is not None else None
                    if supplement:
                        pygame.draw.line(self.screen,(175,175,175),base,supplement,1)

    def _draw_drag_ghost(self, state):
        if not self.input_handler.drag_active or not self.input_handler.drag_start or not self._drag_item_id:
            return
        item=next((entry for entry in state.get("items",[]) if str(entry.get("id"))==str(self._drag_item_id)),None)
        if not item:
            return
        x,y=self.input_handler.get_mouse_position()
        size=44
        surface=pygame.Surface((size,size),pygame.SRCALPHA)
        prior=self.screen
        self.screen=surface
        self._draw_rarity_icon(item,pygame.Rect(0,0,size,size))
        self.screen=prior
        surface.set_alpha(210)
        self.screen.blit(surface,(x-size//2,y-size//2))

    def _draw_quests_menu(self, outer, state=None):
        state = state or {}
        left_rect = pygame.Rect(outer.left+12, outer.top+12, outer.width//2-20, outer.height-24)
        right_rect = pygame.Rect(outer.centerx+10, outer.top+12, outer.width//2-24, outer.height-24)
        for rect, label in ((left_rect, "Main quest"), (right_rect, "Active side quests")):
            pygame.draw.rect(self.screen, (46,46,46), rect, border_radius=5)
            pygame.draw.rect(self.screen, (105,105,105), rect, 1, border_radius=5)
            self._text(label, (rect.left+14, rect.top+14))
        bonus_pct = float(state.get("quest_bonus_pct", 0.0))
        self._text(f"Current run bonus: +{bonus_pct:.1f}%", (left_rect.left+14, left_rect.top+48))
        main_quests = [
            quest for quest in state.get("quests", [])
            if quest.get("type") == "main" and quest.get("status") == "active"
        ]
        completed_main = [
            quest for quest in state.get("quests", [])
            if quest.get("type") == "main" and quest.get("status") == "completed"
        ]
        if main_quests:
            main_quest = main_quests[0]
            self._text(f"{main_quest.get('name', 'Main quest')}", (left_rect.left+14, left_rect.top+82))
            self._text(main_quest.get("description", ""), (left_rect.left+14, left_rect.top+106))
            progress = float(main_quest.get("progress", 0.0))
            target = float(main_quest.get("target", 1.0))
            fill = max(0.0, min(1.0, progress / target if target else 1.0))
            progress_bar = pygame.Rect(left_rect.left+14, left_rect.top+142, left_rect.width-28, 10)
            pygame.draw.rect(self.screen, (72,72,72), progress_bar, border_radius=4)
            progress_fill = progress_bar.copy()
            progress_fill.width = int(progress_bar.width * fill)
            pygame.draw.rect(self.screen, (60,180,110), progress_fill, border_radius=4)
            self._text(
                f"Progress: {progress:.0f}/{target:.0f}  (+{main_quest.get('reward_pct', 0)}%)",
                (left_rect.left+14, left_rect.top+158),
            )
            restrictions = main_quest.get("restrictions") or []
            if restrictions:
                self._text("Restrictions:", (left_rect.left+14, left_rect.top+194))
                for idx, restriction in enumerate(restrictions[:3]):
                    self._text(f"- {restriction}", (left_rect.left+18, left_rect.top+214 + idx*18))
            locked = bool(main_quest.get("lock_on_accept", False))
            self._button(
                f"quest_lock:{main_quest['id']}",
                f"Restrictions: {'Locked' if locked else 'Unlocked'}",
                (left_rect.centerx, left_rect.bottom-24),
                min(220, left_rect.width-28),
                34,
            )
        elif completed_main:
            self._text(f"Completed: {completed_main[-1].get('name', 'Main quest')}", (left_rect.left+14, left_rect.top+82))
            self._text("Your main quest score bonus is included above.", (left_rect.left+14, left_rect.top+108))
        else:
            self._text("Main quests unlock at level 5.", (left_rect.left+14, left_rect.top+82))
        quests = [
            quest for quest in state.get("quests", [])
            if quest.get("type") == "side" and quest.get("status") == "active"
        ]
        if not quests:
            self._text("No active quests yet.", (right_rect.left+14, right_rect.top+48))
            return
        y = right_rect.top + 48
        for quest in quests[:6]:
            bar_width = right_rect.width - 28
            self._text(quest.get("name", "Quest"), (right_rect.left+14, y))
            y += 20
            description = quest.get("description", "")
            self._text(description, (right_rect.left+14, y))
            y += 28
            progress = float(quest.get("progress", 0.0))
            target = float(quest.get("target", 1.0))
            fill = max(0.0, min(1.0, progress / target if target else 1.0))
            bar = pygame.Rect(right_rect.left+14, y, bar_width, 10)
            pygame.draw.rect(self.screen, (72,72,72), bar, border_radius=4)
            fill_rect = bar.copy(); fill_rect.width = int(bar.width * fill)
            pygame.draw.rect(self.screen, (60, 180, 110), fill_rect, border_radius=4)
            self._text(f"{progress:.0f}/{target:.0f}  (+{quest.get('reward_pct',0)}%)", (right_rect.left+14, y+16))
            y += 38
            if y > outer.bottom - 30:
                break

    def _draw_upgrades_menu(self, state, outer):
        area=outer.inflate(-16,-16)
        pygame.draw.rect(self.screen,(46,46,46),area,border_radius=5)
        if self.upgrade_tab=="combination":
            self._draw_combination_menu(state,area)
            return
        if self.upgrade_tab=="fusion":
            self._draw_fusion_menu(state,area)
            return
        level=state.get("level",1); xp=state.get("experience",0); required=state.get("next_level_exp",1)
        self._text("Player level",(area.centerx-54,area.top+12))
        self._text(f"{xp} / {required} EXP",(area.centerx-55,area.top+36))
        bar=pygame.Rect(area.centerx-160,area.top+58,280,16); pygame.draw.rect(self.screen,(76,76,76),bar,border_radius=6)
        fill=bar.copy(); fill.width=int(bar.width*min(1,xp/max(1,required))); pygame.draw.rect(self.screen,(100,195,120),fill,border_radius=6)
        self._text(f"Level {level}",(bar.right+10,bar.top-2))
        left=area.left+18; y=bar.bottom+22
        self._text("Player stats",(left,y)); y+=26
        self._text(f"Luck: {state.get('luck',0)}",(left,y)); y+=22
        self._text(f"Speed: {state.get('speed',1.0)}",(left,y)); y+=24
        self._text("Currencies",(left,y)); y+=22
        for name,amount in state.get("currency",{}).items(): self._text(f"{name}: {amount}",(left,y)); y+=20
        self._text("Armor & weapons",(area.centerx-40,bar.bottom+22))
        self._text("Active abilities",(area.right-150,bar.bottom+22))
        by_id={str(item.get("id")):item for item in state.get("items",[])}
        active=state.get("active_slots",{})
        y=bar.bottom+48
        for kind in ("armor","weapons"):
            for item_id in active.get(kind,[]):
                item=by_id.get(str(item_id))
                if item:
                    self._draw_upgrade_item(item,area.centerx-40,y,180); y+=39
        y=bar.bottom+48
        for item_id in active.get("abilities",[]):
            item=by_id.get(str(item_id))
            if item:
                self._draw_upgrade_item(item,area.right-200,y,185); y+=39

    def _draw_upgrade_item(self,item,x,y,width):
        self._text(f"{item['name']} · {self._item_rarity_label(item)} · Lv {item['level']}",(x,y))
        stats=list(item.get("stats",{}).items())[:2]
        if stats:
            self._text(" · ".join(f"{key} {value}" for key,value in stats),(x,y+17))
        for i,combo_id in enumerate(item.get("combinations",[])[:5]):
            rect=pygame.Rect(x+i*11,y+31,8,8)
            pygame.draw.rect(self.screen,(230,175,65) if combo_id is not None else (105,110,125),rect,1)

    def _draw_fusion_menu(self, state, area):
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        selected = by_id.get(str(self.selected_item_id))
        left = pygame.Rect(area.left + 10, area.top + 10, int(area.width * 0.42) - 12, area.height - 20)
        right = pygame.Rect(left.right + 10, area.top + 10, area.right - left.right - 20, area.height - 20)
        for rect in (left, right):
            pygame.draw.rect(self.screen, (46, 46, 46), rect, border_radius=5)
            pygame.draw.rect(self.screen, (105, 105, 105), rect, 1, border_radius=5)
        self._text("Fusion chamber", (left.left + 10, left.top + 8))
        if selected:
            icon = pygame.Rect(left.left + 12, left.top + 38, 52, 52)
            self._draw_rarity_icon(selected, icon)
            self._text(selected.get("name", "Item"), (icon.right + 10, left.top + 42))
            self._text(f"{self._item_rarity_label(selected)} · Level {selected.get('level', 1)}", (icon.right + 10, left.top + 64))
            self._text(f"Type: {selected.get('type', 'item').title()}", (icon.right + 10, left.top + 86))
        else:
            self._text("Select an item in the inventory to use as the fusion core.", (left.left + 10, left.top + 43))
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
                recipe_rect = pygame.Rect(left.left + 12, y, left.width - 24, 62)
                pygame.draw.rect(self.screen, (62, 62, 62), recipe_rect, border_radius=5)
                pygame.draw.rect(self.screen, (120, 120, 120), recipe_rect, 1, border_radius=5)
                self._text(recipe.get("name", "Fusion"), (recipe_rect.left + 10, recipe_rect.top + 8))
                self._text(
                    f"{recipe.get('description', '')[:38]} · "
                    f"{recipe.get('min_rarity', 'common').title()} Lv {recipe.get('min_level', 1)}",
                    (recipe_rect.left + 10, recipe_rect.top + 25),
                )
                self._text(
                    " + ".join(recipe.get("required_types", [])),
                    (recipe_rect.left + 10, recipe_rect.top + 43),
                )
                self._buttons[f"fusion_recipe:{recipe['id']}:{self.selected_item_id or ''}"] = recipe_rect.copy()
                y += 68
        self._text("Inventoried items", (right.left + 8, right.top + 8))
        slot_size, columns, rows, visible_rows = self._inventory_grid_metrics(right)
        gap = 5
        scroll_row = self._sync_inventory_scroll(rows, visible_rows)
        prior_clip = self.screen.get_clip(); self.screen.set_clip(right)
        slots_w = columns * (slot_size + gap) - gap
        slots_left = right.left + max(7, (right.width - slots_w) // 2)
        for row in range(scroll_row, min(rows, scroll_row + visible_rows)):
            for col in range(columns):
                index = row * columns + col
                item = items[index] if index < len(items) else None
                rect = pygame.Rect(slots_left + col * (slot_size + gap), right.top + 30 + (row - scroll_row) * (slot_size + gap), slot_size, slot_size)
                if item:
                    self._item_rects[str(item.get("id"))] = rect.copy()
                    self._draw_rarity_icon(item, rect.inflate(-10, -10))
                pygame.draw.rect(self.screen, (48, 48, 48), rect, border_radius=3)
                pygame.draw.rect(self.screen, (100, 100, 100), rect, 1, border_radius=3)
        self.screen.set_clip(prior_clip)
        self._draw_inventory_scrollbar(right, rows, visible_rows)

    def _draw_combination_menu(self,state,area):
        from game.systems.combination import CombinationEvaluator
        items=state.get("items",[]); by_id={str(item.get("id")):item for item in items}
        left=pygame.Rect(area.left+10,area.top+10,int(area.width*.46)-12,area.height-20)
        right=pygame.Rect(left.right+10,area.top+10,area.right-left.right-20,area.height-20)
        self._inventory_rect=right.copy()
        for rect in (left,right):
            pygame.draw.rect(self.screen,(46,46,46),rect,border_radius=5)
            pygame.draw.rect(self.screen,(105,105,105),rect,1,border_radius=5)
        self._text("Combination setup",(left.left+10,left.top+8))
        base=by_id.get(str(self.selected_base_id))
        if base:
            icon=pygame.Rect(left.left+12,left.top+38,52,52)
            self._draw_rarity_icon(base,icon)
            detail_x=icon.right+10; detail_y=left.top+39
            self._text(base.get("name","Item"),(detail_x,detail_y)); detail_y+=22
            self._text(f"{self._item_rarity_label(base)} · Level {base.get('level',1)}",(detail_x,detail_y)); detail_y+=21
            self._text(f"Type: {base.get('type','item').title()}",(detail_x,detail_y)); detail_y+=23
            # Base stats display
            pygame.draw.rect(self.screen,(36,36,36),pygame.Rect(left.left+12,detail_y-4,left.width-24,96),border_radius=4)
            pygame.draw.rect(self.screen,(105,105,105),pygame.Rect(left.left+12,detail_y-4,left.width-24,96),1,border_radius=4)
            for stat_name,stat_value in base.get("stats",{}).items():
                self._text(f"{stat_name}: {stat_value}",(left.left+14,detail_y)); detail_y+=20
            # Combination slots
            slots=base.get("combinations",[])
            slot_x=left.right-50; slot_y=left.top+40
            self._text("Combinations",(slot_x-76,left.top+14))
            evaluator=CombinationEvaluator()
            # Preview combined stats
            preview_y=left.top+130
            preview_rect=pygame.Rect(left.left+12,preview_y,left.width-24,140)
            pygame.draw.rect(self.screen,(28,46,28),preview_rect,border_radius=4)
            pygame.draw.rect(self.screen,(100,180,100),preview_rect,1,border_radius=4)
            self._text("Preview combined stats",(preview_rect.left+10,preview_rect.top+6))
            # Get current supplements
            current_supplements=[by_id.get(str(sid)) for sid in slots if sid is not None]
            current_supplements=[s for s in current_supplements if s]
            if current_supplements:
                evaluation=evaluator.evaluate_combination(base,current_supplements)
                final_stats=evaluation.get("final_stats",{})
                y=preview_rect.top+26
                for stat_name,stat_value in final_stats.items():
                    color=(150,250,150) if stat_value>0 else (200,150,150) if stat_value<0 else (180,180,180)
                    self._text(f"{stat_name}: {stat_value:.1f}",(preview_rect.left+10,y),color)
                    y+=18
                # Show interactions
                if evaluation.get("interactions"):
                    y+=8
                    self._text("Interactions:",(preview_rect.left+10,y),(255,255,150))
                    y+=18
                    for interaction in evaluation["interactions"]:
                        self._text(f"· {interaction['type']}: {interaction['description']}",(preview_rect.left+10,y),(220,220,200))
                        y+=16
            else:
                self._text("Drag supplements to slots to see preview",(preview_rect.left+10,preview_rect.top+26),(180,180,180))
            # Draw combination slots
            for i in range(len(slots)):
                rect=pygame.Rect(slot_x,slot_y+i*50,42,42)
                self._drop_targets[f"combo:{base['id']}:{i}"]=rect.copy()
                slot_color=(48,48,48)
                if slots[i] is None:
                    pygame.draw.rect(self.screen,(40,40,40),rect,border_radius=3)
                    pygame.draw.rect(self.screen,(80,80,80),rect,1,border_radius=3)
                    # Draw plus icon for empty slots
                    center=rect.center
                    pygame.draw.line(self.screen,(120,120,120),(center[0]-8,center[1]),(center[0]+8,center[1]),2)
                    pygame.draw.line(self.screen,(120,120,120),(center[0],center[1]-8),(center[0],center[1]+8),2)
                else:
                    pygame.draw.rect(self.screen,(50,50,50),rect,border_radius=3)
                    pygame.draw.rect(self.screen,(205,205,205),rect,2,border_radius=3)
                    combo=by_id.get(str(slots[i]))
                    if combo: self._draw_rarity_icon(combo,rect.inflate(-4,-4))
        else:
            self._text("Click an armor, weapon, or ability in the inventory to inspect it here.",(left.left+10,left.top+43))
        self._text("Inventory · drag a supplement to a combination slot",(right.left+8,right.top+7))
        self._draw_inventory_grid(items,right)
        if base:
            for slot_index,combo_id in enumerate(base.get("combinations",[])):
                if combo_id is None: continue
                item_rect=self._item_rects.get(str(combo_id)); slot_rect=self._drop_targets.get(f"combo:{base['id']}:{slot_index}")
                if item_rect and slot_rect:
                    pygame.draw.line(self.screen,(180,180,180),item_rect.center,slot_rect.center,1)
            # Apply combination button
            apply_rect=pygame.Rect(left.left+10,left.bottom-40,left.width-20,32)
            pygame.draw.rect(self.screen,(70,180,70),apply_rect,border_radius=6)
            pygame.draw.rect(self.screen,(100,220,100),apply_rect,2,border_radius=6)
            self._text("Apply Combination",(apply_rect.centerx-50,apply_rect.centery-8),(255,255,255))
            self._buttons["apply_combination"]=apply_rect.copy()

    def _draw_inventory_grid(self,items,grid_rect):
        self._inventory_rect=grid_rect.copy()
        slot_size,columns,rows,visible_rows=self._inventory_grid_metrics(grid_rect); gap=5
        scroll_row=self._sync_inventory_scroll(rows,visible_rows)
        slots_w=columns*(slot_size+gap)-gap
        slots_left=grid_rect.left+max(7,(grid_rect.width-slots_w-14)//2)
        prior_clip=self.screen.get_clip(); self.screen.set_clip(grid_rect)
        for row in range(scroll_row,min(rows,scroll_row+visible_rows)):
            for col in range(columns):
                index=row*columns+col; rect=pygame.Rect(slots_left+col*(slot_size+gap),grid_rect.top+32+(row-scroll_row)*(slot_size+gap),slot_size,slot_size)
                item=items[index] if index<len(items) else None
                color=(105,105,105)
                if item:
                    color={"supplement":(245,205,55),"active":(70,220,115),"combination_base":(240,145,55)}.get(item.get("status","normal"),color)
                    self._item_rects[str(item.get("id"))]=rect.copy()
                pygame.draw.rect(self.screen,(46,46,46),rect,border_radius=3); pygame.draw.rect(self.screen,color,rect,2 if item else 1,border_radius=3)
                if item:
                    icon_size=slot_size-20; icon=pygame.Rect(rect.centerx-icon_size//2-4,rect.centery-icon_size//2,icon_size,icon_size)
                    self._draw_rarity_icon(item,icon)
                    for combo_index,combo_id in enumerate(item.get("combinations",[])[:5]):
                        mini=pygame.Rect(icon.right+3,rect.y+6+combo_index*8,6,6)
                        self._draw_combo_icon(mini,next((entry for entry in items if str(entry.get("id"))==str(combo_id)),None) if combo_id is not None else None)
        self.screen.set_clip(prior_clip)
        self._draw_inventory_scrollbar(grid_rect,rows,visible_rows)
        if self.menu_tab=="inventory":
            self._draw_inventory_links(items,self._last_state.get("active_slots",{}))

    def _draw_bazaar_menu(self, outer, state):
        """Complete bazaar menu with Market, Crates, Fusion, Rarity Upgrader, Level Upgrader, and Sell tabs."""
        self._buttons = {}
        self._item_rects = {}
        self._drop_targets = {}
        
        # Header
        self._text("Bazaar", (outer.left + 20, outer.top + 12))
        wallet = state.get("currency", {})
        gold = wallet.get("gold", 0)
        self._text(f"Gold: {gold}", (outer.left + 20, outer.top + 38))
        self._text(f"Inventory: {len(state.get('items', []))} / 200", (outer.right - 160, outer.top + 12))
        
        # Bazaar tabs
        bazaar_tabs = [
            ("market", "Market"),
            ("crates", "Crates"),
            ("fusion", "Fusion"),
            ("rarity_upgrader", "Rarity"),
            ("level_upgrader", "Level"),
            ("sell", "Sell")
        ]
        tab_width = min(140, (outer.width - 48) // len(bazaar_tabs))
        tab_y = outer.top + 48
        for i, (key, label) in enumerate(bazaar_tabs):
            active = getattr(self, '_bazaar_tab', 'market') == key
            tab_rect = pygame.Rect(outer.left + 12 + i * (tab_width + 4), tab_y, tab_width, 32)
            self._buttons[f"bazaar_tab_{key}"] = tab_rect
            color = (70, 150, 255) if active else (50, 50, 50)
            pygame.draw.rect(self.screen, color, tab_rect, border_radius=4)
            pygame.draw.rect(self.screen, (120, 120, 120), tab_rect, 1, border_radius=4)
            surf = self.font.render(label, True, (245, 245, 250))
            self.screen.blit(surf, surf.get_rect(center=tab_rect.center))
        
        # Content area
        content_rect = pygame.Rect(outer.left + 10, outer.top + 90, outer.width - 20, outer.height - 100)
        pygame.draw.rect(self.screen, (40, 40, 40), content_rect, border_radius=6)
        pygame.draw.rect(self.screen, (100, 100, 100), content_rect, 1, border_radius=6)
        
        # Draw appropriate tab content
        bazaar_tab = getattr(self, '_bazaar_tab', 'market')
        if bazaar_tab == "market":
            self._draw_bazaar_market(content_rect, state)
        elif bazaar_tab == "crates":
            self._draw_bazaar_crates(content_rect, state)
        elif bazaar_tab == "fusion":
            self._draw_bazaar_fusion(content_rect, state)
        elif bazaar_tab == "rarity_upgrader":
            self._draw_bazaar_rarity_upgrader(content_rect, state)
        elif bazaar_tab == "level_upgrader":
            self._draw_bazaar_level_upgrader(content_rect, state)
        elif bazaar_tab == "sell":
            self._draw_bazaar_sell(content_rect, state)
        
        # Close button
        self._button("bazaar_close", "Close", (outer.right - 120, outer.bottom - 40))

    def _draw_bazaar_market(self, rect, state):
        """Market tab - browse and purchase items from catalog."""
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        catalog = state.get("bazaar_catalog", [])
        wallet = state.get("currency", {})
        gold = wallet.get("gold", 0)
        
        # Header
        self._text("Market", (rect.left + 12, rect.top + 8))
        self._text(f"Scroll: {int(self.bazaar_market_scroll_target)}/{len(catalog)}", (rect.right - 120, rect.top + 8))
        
        # Scrollable item list
        item_height = 48
        visible_items = (rect.height - 40) // item_height
        start_idx = int(self.bazaar_market_scroll_target)
        end_idx = min(start_idx + visible_items + 2, len(catalog))
        
        for i, item_def in enumerate(catalog[start_idx:end_idx]):
            y = rect.top + 12 + (i - start_idx) * item_height
            if y > rect.bottom - item_height:
                break
            item_rect = pygame.Rect(rect.left + 8, y, rect.width - 16, item_height)
            
            # Item row
            pygame.draw.rect(self.screen, (55, 55, 55), item_rect, border_radius=4)
            pygame.draw.rect(self.screen, (110, 110, 110), item_rect, 1, border_radius=4)
            
            # Item info
            name = item_def.get("name", "Unknown")
            rarity = item_def.get("rarity", "common")
            item_type = item_def.get("type", "item")
            level = item_def.get("level", 1)
            price = state.get("bazaar_catalog_prices", {}).get(item_def.get("id", ""), 50)
            
            # Rarity color
            rarity_color = self._rarity_color(rarity)
            pygame.draw.rect(self.screen, rarity_color, (rect.left + 10, y + 14, 8, 8), border_radius=2)
            
            # Text
            name_surf = self.font.render(f"{name} (Lvl {level})", True, (245, 245, 250))
            self.screen.blit(name_surf, (rect.left + 24, y + 10))
            
            type_surf = self.font.render(f"{item_type.title()}", True, (180, 180, 180))
            self.screen.blit(type_surf, (rect.left + 120, y + 10))
            
            # Price and buy button
            price_surf = self.font.render(f"{price}G", True, (255, 215, 0) if price <= gold else (255, 100, 100))
            self.screen.blit(price_surf, (rect.right - 80, y + 10))
            
            buy_btn = pygame.Rect(rect.right - 70, y + 6, 60, 32)
            self._buttons[f"bazaar_buy_{item_def.get('id', '')}_{start_idx + i}"] = buy_btn
            buy_label = "BUY" if price <= gold else "NO GOLD"
            buy_color = (70, 150, 255) if price <= gold else (100, 100, 100)
            pygame.draw.rect(self.screen, buy_color, buy_btn, border_radius=4)
            pygame.draw.rect(self.screen, (140, 140, 140), buy_btn, 1, border_radius=4)
            buy_text = self.font.render(buy_label, True, (255, 255, 255))
            self.screen.blit(buy_text, buy_text.get_rect(center=buy_btn.center))
        
        # Navigation buttons
        nav_y = rect.bottom - 30
        self._button("bazaar_market_up", "▲", (rect.left + 40, nav_y), 30, 26)
        self._button("bazaar_market_down", "▼", (rect.left + 80, nav_y), 30, 26)

    def _draw_bazaar_crates(self, rect, state):
        """Crates tab - purchase randomized item crates."""
        crates = state.get("bazaar_crates", [])
        wallet = state.get("currency", {})
        gold = wallet.get("gold", 0)
        
        # Header
        self._text("Crates", (rect.left + 12, rect.top + 8))
        self._text(f"Scroll: {int(self.bazaar_crates_scroll_target)}/{len(crates)}", (rect.right - 120, rect.top + 8))
        
        # Crate list
        crate_height = 72
        visible_crates = (rect.height - 40) // crate_height
        start_idx = int(self.bazaar_crates_scroll_target)
        
        for i, crate in enumerate(crates[start_idx:]):
            y = rect.top + 12 + (i - start_idx) * crate_height
            if y > rect.bottom - crate_height:
                break
            
            crate_rect = pygame.Rect(rect.left + 8, y, rect.width - 16, crate_height)
            
            # Crate background
            crate_color = {
                "starter-crate": (180, 180, 180),
                "gilded-crate": (70, 150, 255),
                "mythic-crate": (180, 80, 220),
                "astral-crate": (255, 215, 0),
                "void-crate": (138, 43, 226)
            }.get(crate.get("id", ""), (100, 100, 100))
            
            pygame.draw.rect(self.screen, crate_color, crate_rect, border_radius=6)
            pygame.draw.rect(self.screen, (150, 150, 150), crate_rect, 2, border_radius=6)
            
            # Crate info
            name = crate.get("name", "Crate")
            cost = crate.get("cost", 100)
            bias = crate.get("bias", "common")
            desc = crate.get("description", "")
            
            name_surf = self.font.render(name, True, (255, 255, 255))
            self.screen.blit(name_surf, (rect.left + 20, y + 8))
            
            bias_surf = self.font.render(f"Bias: {bias.title()}", True, (200, 200, 200))
            self.screen.blit(bias_surf, (rect.left + 20, y + 28))
            
            desc_surf = self.font.render(desc, True, (180, 180, 180))
            max_width = rect.right - rect.left - 50
            wrapped_desc = self._wrap_text(desc_surf, max_width - 40)
            self.screen.blit(wrapped_desc, (rect.left + 20, y + 42))
            
            # Cost and buy button
            cost_surf = self.font.render(f"{cost}G", True, (255, 215, 0) if cost <= gold else (255, 100, 100))
            self.screen.blit(cost_surf, (rect.right - 70, y + 20))
            
            buy_btn = pygame.Rect(rect.right - 60, y + 12, 50, 36)
            self._buttons[f"bazaar_buy_crate_{crate.get('id', '')}_{start_idx + i}"] = buy_btn
            buy_label = "BUY" if cost <= gold else "NO GOLD"
            buy_color = (70, 150, 255) if cost <= gold else (100, 100, 100)
            pygame.draw.rect(self.screen, buy_color, buy_btn, border_radius=4)
            pygame.draw.rect(self.screen, (140, 140, 140), buy_btn, 1, border_radius=4)
            buy_text = self.font.render(buy_label, True, (255, 255, 255))
            self.screen.blit(buy_text, buy_text.get_rect(center=buy_btn.center))
        
        # Navigation
        nav_y = rect.bottom - 30
        self._button("bazaar_crates_up", "▲", (rect.left + 40, nav_y), 30, 26)
        self._button("bazaar_crates_down", "▼", (rect.left + 80, nav_y), 30, 26)

    def _draw_bazaar_fusion(self, rect, state):
        """Fusion tab - combine two items to create a new fused item."""
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        
        # Header
        self._text("Fusion", (rect.left + 12, rect.top + 8))
        self._text("Combine 2 items to create a powerful fused item!", (rect.left + 12, rect.top + 28))
        
        # Selected items
        self._text("Selected Items:", (rect.left + 12, rect.top + 55))
        
        # Item 1 slot
        slot1_y = rect.top + 75
        slot1_rect = pygame.Rect(rect.left + 12, slot1_y, 120, 56)
        pygame.draw.rect(self.screen, (60, 60, 60), slot1_rect, border_radius=4)
        pygame.draw.rect(self.screen, (120, 120, 120), slot1_rect, 2, border_radius=4)
        slot1_surf = self.font.render("Click an item", True, (150, 150, 150))
        self.screen.blit(slot1_surf, slot1_surf.get_rect(center=slot1_rect.center))
        
        # Item 2 slot
        slot2_y = rect.top + 75
        slot2_rect = pygame.Rect(rect.left + 140, slot2_y, 120, 56)
        pygame.draw.rect(self.screen, (60, 60, 60), slot2_rect, border_radius=4)
        pygame.draw.rect(self.screen, (120, 120, 120), slot2_rect, 2, border_radius=4)
        slot2_surf = self.font.render("Click an item", True, (150, 150, 150))
        self.screen.blit(slot2_surf, slot2_surf.get_rect(center=slot2_rect.center))
        
        # Fusion preview
        preview_y = rect.top + 150
        preview_rect = pygame.Rect(rect.left + 12, preview_y, rect.width - 24, 80)
        pygame.draw.rect(self.screen, (50, 50, 50), preview_rect, border_radius=4)
        pygame.draw.rect(self.screen, (180, 180, 180), preview_rect, 1, border_radius=4)
        
        fuse_label = self.font.render("Fuse Selected Items", True, (245, 245, 250))
        self.screen.blit(fuse_label, (rect.left + 12, preview_y + 8))
        
        fuse_cost = 500
        wallet = state.get("currency", {})
        gold = wallet.get("gold", 0)
        cost_color = (255, 215, 0) if gold >= fuse_cost else (255, 100, 100)
        cost_surf = self.font.render(f"Cost: {fuse_cost}G", True, cost_color)
        self.screen.blit(cost_surf, (rect.left + 12, preview_y + 28))
        
        # Fuse button
        fuse_btn = pygame.Rect(rect.right - 130, preview_y + 40, 120, 32)
        self._buttons["bazaar_fuse"] = fuse_btn
        fuse_color = (70, 150, 255) if gold >= fuse_cost else (100, 100, 100)
        pygame.draw.rect(self.screen, fuse_color, fuse_btn, border_radius=4)
        pygame.draw.rect(self.screen, (140, 140, 140), fuse_btn, 1, border_radius=4)
        fuse_text = self.font.render("FUSE", True, (255, 255, 255))
        self.screen.blit(fuse_text, fuse_text.get_rect(center=fuse_btn.center))
        
        # Instructions
        instructions_y = rect.bottom - 30
        instr_surf = self.font.render("Click items in inventory to select for fusion", True, (180, 180, 180))
        self.screen.blit(instr_surf, (rect.left + 12, instructions_y))
        
        # Draw inventory grid below
        inv_y = rect.bottom - 120
        inv_rect = pygame.Rect(rect.left + 10, inv_y, rect.width - 20, 100)
        pygame.draw.rect(self.screen, (40, 40, 40), inv_rect, border_radius=6)
        pygame.draw.rect(self.screen, (100, 100, 100), inv_rect, 1, border_radius=6)
        self._text("Inventory:", (inv_rect.left + 10, inv_rect.top + 5))
        self._draw_inventory_grid(items, inv_rect)
        
        # Draw inventory grid below
        inv_y = rect.bottom - 120
        inv_rect = pygame.Rect(rect.left + 10, inv_y, rect.width - 20, 100)
        pygame.draw.rect(self.screen, (40, 40, 40), inv_rect, border_radius=6)
        pygame.draw.rect(self.screen, (100, 100, 100), inv_rect, 1, border_radius=6)
        self._text("Inventory:", (inv_rect.left + 10, inv_rect.top + 5))
        self._draw_inventory_grid(items, inv_rect)

    def _draw_bazaar_rarity_upgrader(self, rect, state):
        """Rarity upgrader tab - upgrade item rarity using currency and luck."""
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        wallet = state.get("currency", {})
        
        # Header
        self._text("Rarity Upgrader", (rect.left + 12, rect.top + 8))
        self._text("Upgrade item rarity using currency and luck!", (rect.left + 12, rect.top + 28))
        
        # Select item
        select_y = rect.top + 55
        select_surf = self.font.render("Select an item to upgrade:", True, (200, 200, 200))
        self.screen.blit(select_surf, (rect.left + 12, select_y))
        
        # Item slot
        item_slot_y = rect.top + 75
        item_slot_rect = pygame.Rect(rect.left + 12, item_slot_y, 140, 56)
        pygame.draw.rect(self.screen, (60, 60, 60), item_slot_rect, border_radius=4)
        pygame.draw.rect(self.screen, (120, 120, 120), item_slot_rect, 2, border_radius=4)
        item_slot_surf = self.font.render("Click an item", True, (150, 150, 150))
        self.screen.blit(item_slot_surf, item_slot_surf.get_rect(center=item_slot_rect.center))
        
        # Upgrade info
        info_y = rect.top + 150
        info_rect = pygame.Rect(rect.left + 12, info_y, rect.width - 24, 180)
        pygame.draw.rect(self.screen, (50, 50, 50), info_rect, border_radius=4)
        pygame.draw.rect(self.screen, (120, 120, 120), info_rect, 1, border_radius=4)
        
        # Currency options with favorability
        currency_options = [
            ("gold", "Gold", "+15% chance", (255, 215, 0), True),
            ("silver", "Silver", "0% chance", (192, 192, 192), False),
            ("copper", "Copper", "-20% chance", (184, 134, 11), False),
        ]
        
        for i, (curr_id, curr_name, effect, color, favored) in enumerate(currency_options):
            curr_y = info_y + 20 + i * 42
            curr_rect = pygame.Rect(rect.left + 14, curr_y, rect.width - 28, 36)
            
            bg_color = (70, 150, 255) if favored else (60, 60, 60)
            pygame.draw.rect(self.screen, bg_color, curr_rect, border_radius=4)
            pygame.draw.rect(self.screen, (140, 140, 140), curr_rect, 1, border_radius=4)
            
            curr_surf = self.font.render(f"{curr_name} ({wallet.get(curr_id, 0)}) - {effect}", True, color)
            self.screen.blit(curr_surf, (rect.left + 16, curr_y + 8))
        
        # Luck and success chance
        luck = state.get("player_stats", {}).get("luck", 0)
        luck_surf = self.font.render(f"Your Luck: +{luck * 10:.0f}%", True, (150, 200, 255))
        self.screen.blit(luck_surf, (rect.left + 14, info_y + 160))
        
        success_surf = self.font.render("Success chance will be calculated on upgrade", True, (200, 200, 200))
        self.screen.blit(success_surf, (rect.left + 14, info_y + 180))
        
        # Upgrade button
        upgrade_btn = pygame.Rect(rect.right - 130, rect.bottom - 40, 120, 32)
        self._buttons["bazaar_rarity_upgrade"] = upgrade_btn
        upgrade_color = (70, 150, 255)
        pygame.draw.rect(self.screen, upgrade_color, upgrade_btn, border_radius=4)
        pygame.draw.rect(self.screen, (140, 140, 140), upgrade_btn, 1, border_radius=4)
        upgrade_text = self.font.render("UPGRADE", True, (255, 255, 255))
        self.screen.blit(upgrade_text, upgrade_text.get_rect(center=upgrade_btn.center))
        
        # Draw inventory grid below
        inv_y = rect.bottom - 120
        inv_rect = pygame.Rect(rect.left + 10, inv_y, rect.width - 20, 100)
        pygame.draw.rect(self.screen, (40, 40, 40), inv_rect, border_radius=6)
        pygame.draw.rect(self.screen, (100, 100, 100), inv_rect, 1, border_radius=6)
        self._text("Inventory:", (inv_rect.left + 10, inv_rect.top + 5))
        self._draw_inventory_grid(items, inv_rect)
        
        # Draw inventory grid below
        inv_y = rect.bottom - 120
        inv_rect = pygame.Rect(rect.left + 10, inv_y, rect.width - 20, 100)
        pygame.draw.rect(self.screen, (40, 40, 40), inv_rect, border_radius=6)
        pygame.draw.rect(self.screen, (100, 100, 100), inv_rect, 1, border_radius=6)
        self._text("Inventory:", (inv_rect.left + 10, inv_rect.top + 5))
        self._draw_inventory_grid(items, inv_rect)

    def _draw_bazaar_level_upgrader(self, rect, state):
        """Level upgrader tab - upgrade item level using currency."""
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        wallet = state.get("currency", {})
        
        # Header
        self._text("Level Upgrader", (rect.left + 12, rect.top + 8))
        self._text("Increase item level for better stats!", (rect.left + 12, rect.top + 28))
        
        # Select item
        select_y = rect.top + 55
        select_surf = self.font.render("Select an item to level up:", True, (200, 200, 200))
        self.screen.blit(select_surf, (rect.left + 12, select_y))
        
        # Item slot
        item_slot_y = rect.top + 75
        item_slot_rect = pygame.Rect(rect.left + 12, item_slot_y, 140, 56)
        pygame.draw.rect(self.screen, (60, 60, 60), item_slot_rect, border_radius=4)
        pygame.draw.rect(self.screen, (120, 120, 120), item_slot_rect, 2, border_radius=4)
        item_slot_surf = self.font.render("Click an item", True, (150, 150, 150))
        self.screen.blit(item_slot_surf, item_slot_surf.get_rect(center=item_slot_rect.center))
        
        # Level info
        info_y = rect.top + 150
        info_rect = pygame.Rect(rect.left + 12, info_y, rect.width - 24, 120)
        pygame.draw.rect(self.screen, (50, 50, 50), info_rect, border_radius=4)
        pygame.draw.rect(self.screen, (120, 120, 120), info_rect, 1, border_radius=4)
        
        level_surf = self.font.render("Current level and next level stats will be shown here", True, (180, 180, 180))
        self.screen.blit(level_surf, (rect.left + 14, info_y + 8))
        
        cost_surf = self.font.render("Upgrade cost will be calculated on selection", True, (200, 200, 200))
        self.screen.blit(cost_surf, (rect.left + 14, info_y + 28))
        
        # Upgrade button
        upgrade_btn = pygame.Rect(rect.right - 130, rect.bottom - 40, 120, 32)
        self._buttons["bazaar_level_upgrade"] = upgrade_btn
        upgrade_color = (70, 150, 255)
        pygame.draw.rect(self.screen, upgrade_color, upgrade_btn, border_radius=4)
        pygame.draw.rect(self.screen, (140, 140, 140), upgrade_btn, 1, border_radius=4)
        upgrade_text = self.font.render("LEVEL UP", True, (255, 255, 255))
        self.screen.blit(upgrade_text, upgrade_text.get_rect(center=upgrade_btn.center))
        
        # Draw inventory grid below
        inv_y = rect.bottom - 120
        inv_rect = pygame.Rect(rect.left + 10, inv_y, rect.width - 20, 100)
        pygame.draw.rect(self.screen, (40, 40, 40), inv_rect, border_radius=6)
        pygame.draw.rect(self.screen, (100, 100, 100), inv_rect, 1, border_radius=6)
        self._text("Inventory:", (inv_rect.left + 10, inv_rect.top + 5))
        self._draw_inventory_grid(items, inv_rect)

    def _draw_bazaar_sell(self, rect, state):
        """Sell tab - sell unwanted items for currency."""
        items = state.get("items", [])
        by_id = {str(item.get("id")): item for item in items}
        wallet = state.get("currency", {})
        
        # Header
        self._text("Sell Market", (rect.left + 12, rect.top + 8))
        self._text("Sell items you don't need for gold!", (rect.left + 12, rect.top + 28))
        
        # Scrollable item list
        item_height = 44
        visible_items = (rect.height - 60) // item_height
        start_idx = int(self.bazaar_owned_scroll_target)
        
        for i, item in enumerate(items[start_idx:start_idx + visible_items + 2]):
            y = rect.top + 50 + (i - start_idx) * item_height
            if y > rect.bottom - item_height:
                break
            
            item_rect = pygame.Rect(rect.left + 8, y, rect.width - 16, item_height)
            
            # Item row
            rarity = item.get("rarity", "common")
            rarity_color = self._rarity_color(rarity)
            pygame.draw.rect(self.screen, (55, 55, 55), item_rect, border_radius=4)
            pygame.draw.rect(self.screen, (110, 110, 110), item_rect, 1, border_radius=4)
            
            # Item info
            name = item.get("name", "Unknown")
            level = item.get("level", 1)
            
            # Rarity indicator
            pygame.draw.rect(self.screen, rarity_color, (rect.left + 10, y + 14, 8, 8), border_radius=2)
            
            # Text
            name_surf = self.font.render(f"{name} (Lvl {level})", True, (245, 245, 250))
            self.screen.blit(name_surf, (rect.left + 24, y + 10))
            
            # Estimated value
            base_value = 5 + self._rarity_rank(rarity) * 10 + level * 4
            value_surf = self.font.render(f"~{base_value}G", True, (255, 215, 0))
            self.screen.blit(value_surf, (rect.right - 60, y + 10))
            
            # Sell button
            sell_btn = pygame.Rect(rect.right - 50, y + 8, 40, 28)
            self._buttons[f"bazaar_sell:{item.get('id', '')}"] = sell_btn
            sell_color = (200, 80, 80)
            pygame.draw.rect(self.screen, sell_color, sell_btn, border_radius=3)
            pygame.draw.rect(self.screen, (140, 140, 140), sell_btn, 1, border_radius=3)
            sell_text = self.font.render("SELL", True, (255, 255, 255))
            self.screen.blit(sell_text, sell_text.get_rect(center=sell_btn.center))
        
        # Total value
        total_y = rect.bottom - 30
        total_surf = self.font.render("Scroll through inventory and click SELL on items you want to discard", True, (180, 180, 180))
        self.screen.blit(total_surf, (rect.left + 12, total_y))

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
        order = ["common", "uncommon", "rare", "epic", "legendary", "mythical", "ultimate"]
        return order.index(str(rarity).lower()) if str(rarity).lower() in order else 0

    def _wrap_text(self, text_surf, max_width):
        """Wrap text to fit within max_width."""
        words = text_surf.get_text().split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            test_surf = self.font.render(test_line, True, text_surf.get_color())
            if test_surf.get_width() <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Render wrapped lines
        result_surf = pygame.Surface((max_width, len(lines) * text_surf.get_height()), pygame.SRCALPHA)
        for i, line in enumerate(lines):
            line_surf = self.font.render(line, True, text_surf.get_color())
            result_surf.blit(line_surf, (0, i * text_surf.get_height()))
        
        return result_surf

    def _draw_game_ui(self, state):
        self._buttons = {}
        if "currency_up" in state.get("actions", []):
            self.currency_offset = max(0, self.currency_offset - 1)
        if "currency_down" in state.get("actions", []):
            self.currency_offset += 1
        left, right, top, bottom = 14, self.screen_width-14, 12, self.screen_height-12
        self._text(f"Absolute Score: {state.get('absolute_score',0)}", (left,top))
        self._text(f"Total Score: {state.get('total_score',0)}", (left,top+22))
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
        self._text(f"Timer {minutes:02d}:{seconds:02d}:{milliseconds:03d}", (left,top+44))
        threat_level = int(state.get("threat_level", 0))
        self._text(
            f"Enemy scale {state.get('enemy_scale', '1')}×",
            (left, top + 66),
        )
        self._button("threat_down", "-", (right-238, top+18), 30, 32)
        self._text(f"Threat {threat_level}", (right-202, top+11))
        self._button("threat_up", "+", (right-146, top+18), 30, 32)
        active=state.get("active_slots",{})
        by_id={str(item.get("id")):item for item in state.get("items",[])}
        for i in range(10):
            rect=pygame.Rect(0,0,34,34); rect.midbottom=(self.screen_width//2+int((i-4.5)*40),bottom)
            self._buttons[f"ability_cast:{i}"] = rect.copy()
            item_id=active.get("abilities",[])[i] if i<len(active.get("abilities",[])) else None
            item=by_id.get(str(item_id)) if item_id else None
            pygame.draw.rect(self.screen,(105,105,105),rect,2)
            if item:
                pygame.draw.rect(self.screen,(70,220,115),rect,2)
                self._draw_rarity_icon(item,rect.inflate(-8,-8))
                self._draw_combo_markers(rect,item)
                self._draw_cooldown_overlay(rect,state.get("ability_cooldowns",[0]*10)[i])
            self._text(str((i + 1) % 10), (rect.left + 2, rect.top + 1))
        for i in range(5):
            rect=pygame.Rect(0,0,34,34); rect.topleft=(left,top+95+i*38); pygame.draw.rect(self.screen,(105,105,105),rect,2)
            item_id=active.get("armor",[])[i] if i<len(active.get("armor",[])) else None
            item=by_id.get(str(item_id)) if item_id else None
            if item:
                pygame.draw.rect(self.screen,(70,220,115),rect,2)
                self._draw_rarity_icon(item,rect.inflate(-8,-8))
                self._draw_combo_markers(rect,item)
        for i in range(2):
            rect=pygame.Rect(0,0,34,34); rect.topleft=(left,self.screen_height//2+20+i*38); pygame.draw.rect(self.screen,(105,105,105),rect,2)
            item_id=active.get("weapons",[])[i] if i<len(active.get("weapons",[])) else None
            item=by_id.get(str(item_id)) if item_id else None
            if item:
                pygame.draw.rect(self.screen,(70,220,115),rect,2)
                self._draw_rarity_icon(item,rect.inflate(-8,-8))
                self._draw_combo_markers(rect,item)
                self._draw_cooldown_overlay(rect,state.get("weapon_cooldowns",[0,0])[i])
        self._button("pause", "Resume" if state.get("paused") else "Pause", (right-60,top+18),100,34)
        quest_checks = [
            quest for quest in state.get("quests", [])
            if quest.get("status") == "active"
        ]
        self._text("Quests", (right-105, self.screen_height//2-75))
        if not quest_checks:
            self._text("- No active quests", (right-105, self.screen_height//2-48))
        else:
            for index, quest in enumerate(quest_checks[:3]):
                progress = float(quest.get("progress", 0.0))
                target = float(quest.get("target", 1.0))
                label = f"{quest.get('name', 'Quest')}: {progress:.0f}/{target:.0f}"
                self._text(f"- {label}", (right-170, self.screen_height//2-48 + index * 28))
        self._button("inventory","Inventory",(right-60,bottom-100),100,34)
        self._button("upgrades","Upgrades",(right-60,bottom-58),100,34)
        wallet=state.get("currency",{})
        currency_left=left
        self._text("Currencies",(currency_left,bottom-62))
        currency_rows=list(wallet.items())
        self.currency_offset=min(self.currency_offset,max(0,len(currency_rows)-2))
        clip=pygame.Rect(currency_left,bottom-42,150,38)
        self.screen.set_clip(clip)
        for i,(name,amount) in enumerate(currency_rows[self.currency_offset:self.currency_offset+2]):
            self._text(f"{name}: {amount}",(currency_left,bottom-40+i*20))
        self.screen.set_clip(None)
        for i,item in enumerate(state.get("notifications",[])):
            alpha=max(0,min(255,int(255*item['remaining']/3)))
            surf=self.font.render(item['text'],True,(255,220,110)); surf.set_alpha(alpha)
            self.screen.blit(surf,surf.get_rect(midtop=(self.screen_width//2,16+i*24)))
        if state.get("paused") or self.panel:
            title = "Paused" if state.get("paused") and not self.panel else (self.panel or "Panel").title()
            overlay=pygame.Surface((self.screen_width,self.screen_height),pygame.SRCALPHA); overlay.fill((0,0,0,165)); self.screen.blit(overlay,(0,0))
            title_s=pygame.font.Font(None,44).render(title,True,(250,250,250)); self.screen.blit(title_s,title_s.get_rect(center=(self.screen_width//2,self.screen_height//2-20)))
            self._button("close_panel","Resume" if title=="Paused" else "Close",(self.screen_width//2,self.screen_height//2+30))
            if state.get("paused") and not self.panel:
                for i,(key,label) in enumerate((("inventory","Inventory"),("quests","Quests"),("upgrades","Upgrades"),("bazaar","Bazaar"))):
                    self._button(f"tab_{key}",label,(self.screen_width//2+(i-1)*112,self.screen_height//2+85),104,30)

    def _text(self, value, pos):
        self.screen.blit(self.font.render(str(value),True,(240,240,245)),pos)

    def _draw_combo_markers(self,rect,item):
        slots=item.get("combinations",[])[:5]
        marker=4; gap=1
        start=rect.centerx-(len(slots)*(marker+gap)-gap)//2
        for index,combo_id in enumerate(slots):
            square=pygame.Rect(start+index*(marker+gap),rect.bottom-marker-2,marker,marker)
            pygame.draw.rect(self.screen,(245,200,70) if combo_id is not None else (135,140,155),square,1)

    def _draw_cooldown_overlay(self,rect,remaining):
        if remaining <= 0:
            ready=self.font.render("RDY",True,(225,225,225))
            self.screen.blit(ready,ready.get_rect(center=(rect.centerx,rect.bottom-8)))
            return
        overlay=pygame.Surface(rect.size,pygame.SRCALPHA)
        overlay.fill((0,0,0,155))
        self.screen.blit(overlay,rect.topleft)
        label=self.font.render(f"{remaining:.1f}",True,(245,245,245))
        self.screen.blit(label,label.get_rect(center=rect.center))

    def close(self):
        pygame.quit()
