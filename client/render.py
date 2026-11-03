import pygame

from client.input import InputHandler
from game.utils.large_number import LargeNumber


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
            elif action.startswith("select:"):
                self.selected_item_id = action.split(":",1)[1]
                if (self.panel == "upgrades" and self.menu_tab == "upgrades"
                        and self.upgrade_tab == "combination" and not dragged_this_frame):
                    item = next((entry for entry in getattr(self,"_last_state",{}).get("items",[])
                                 if str(entry.get("id")) == self.selected_item_id),None)
                    if item and item.get("type") in ("armor","weapon","ability"):
                        self.selected_base_id=self.selected_item_id
            elif action == "inventory_up" and self.panel:
                self.inventory_scroll_target = max(0,self.inventory_scroll_target-3)
            elif action == "inventory_down" and self.panel:
                self.inventory_scroll_target += 3
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

            # Only show the enemy's healthbar when damaged
            if enemy.health < enemy.max_health:
                self.draw_health_bar(
                    screen_position[0],
                    screen_position[1] - size / 2 - 8,
                    enemy.health,
                    enemy.max_health,
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

    def _button(self, key, label, center, width=210, height=42):
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center
        self._buttons[key] = rect
        pygame.draw.rect(self.screen, (68, 68, 68), rect, border_radius=6)
        pygame.draw.rect(self.screen, (145, 145, 145), rect, 2, border_radius=6)
        surf = self.font.render(label, True, (245, 245, 250))
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def draw_menu(self, error=""):
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
        self._button("exit", "Exit", (cx,cy+60))
        self._button("settings", "Settings", (cx, self.screen_height-36))
        if error:
            self.screen.blit(self.font.render(error,True,(255,110,100)),self.font.render(error,True,(255,110,100)).get_rect(center=(cx,cy+112)))
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
        self.draw_enemies(enemies, enemy_types, player.x, player.y)
        self.draw_debug(state)
        self._draw_game_ui(state)

        pygame.display.flip()

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
            for index,(key,label) in enumerate((("overview","Overview"),("combination","Combination"))):
                self._button(f"upgrade_{key}",label,(18+index*132+62,69),124,32)
            pygame.draw.line(self.screen,(125,125,125),(0,88),(self.screen_width,88),1)
        top=96 if self.menu_tab=="upgrades" else 58
        outer=pygame.Rect(10,top,self.screen_width-20,self.screen_height-top-10)
        pygame.draw.rect(self.screen,(34,34,34),outer,border_radius=8)
        pygame.draw.rect(self.screen,(95,95,95),outer,1,border_radius=8)
        if self.menu_tab == "inventory":
            self._draw_inventory_menu(state, outer)
        elif self.menu_tab == "quests":
            self._draw_quests_menu(outer)
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
        y=gear_rect.top+27
        armor_size=min(52,(gear_rect.width-16-16)//5)
        self._text("Armor",(gear_rect.left+8,y)); y+=19
        values=active.get("armor",[])
        for i in range(5):
            self._draw_active_slot(f"armor:{i}",values[i] if i<len(values) else None,by_id,
                                   (gear_rect.left+8+i*(armor_size+4),y),armor_size,armor_size)
        y+=armor_size+9
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
                    self._draw_rarity_icon(item.get("rarity","common"),icon)
                    mini_size=6
                    for combo_index,combo_id in enumerate(item.get("combinations",[])[:5]):
                        mini=pygame.Rect(icon.right+3,rect.y+6+combo_index*(mini_size+2),mini_size,mini_size)
                        self._draw_combo_icon(mini,by_id.get(str(combo_id)) if combo_id is not None else None)
        self.screen.set_clip(prior_clip)
        self._draw_inventory_links(items, active)
        self._draw_inventory_scrollbar(grid_rect, rows, visible_rows)

    def _draw_item_details(self, item, x, y, width):
        rarity=item.get("rarity","common").title()
        icon=pygame.Rect(x,y,48,48)
        self._draw_rarity_icon(item.get("rarity","common"),icon)
        self._text(item.get("name","Item"),(x+51,y)); self._text(f"{rarity} · Lv {item.get('level',1)}",(x+51,y+20))
        by_id={str(candidate.get("id")):candidate for candidate in getattr(self,"_last_state",{}).get("items",[])}
        for index,combo_id in enumerate(item.get("combinations",[])[:5]):
            mini=pygame.Rect(x+51+index*13,y+38,10,10)
            self._draw_combo_icon(mini,by_id.get(str(combo_id)) if combo_id is not None else None)
        y+=52
        self._text(f"Type: {item.get('type','misc').title()}",(x,y)); y+=22
        for name,value in item.get("stats",{}).items():
            self._text(f"{name}: {value}",(x,y)); y+=20

    def _draw_active_slot(self, key, item_id, by_id, pos, width, height, cooldown=None):
        rect=pygame.Rect(pos,(width,height)); self._drop_targets[key]=rect.copy()
        item=by_id.get(str(item_id)) if item_id is not None else None
        pygame.draw.rect(self.screen,(48,48,48),rect,border_radius=3)
        pygame.draw.rect(self.screen,(70,220,115) if item else (100,100,100),rect,2,border_radius=3)
        if item:
            icon_size=min(width,height)-10
            icon=pygame.Rect(rect.centerx-icon_size//2,rect.centery-icon_size//2,icon_size,icon_size)
            self._draw_rarity_icon(item.get("rarity","common"),icon)
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

    def _draw_rarity_icon(self, rarity, rect):
        rarity=str(rarity).lower()
        if rarity=="ultimate":
            cache_key=(rect.width,rect.height)
            surface=self._rarity_icon_cache.get(cache_key)
            if surface is None:
                surface=pygame.Surface(rect.size)
                width,height=rect.size
                for py in range(height):
                    for px in range(width):
                        hue=((px/max(1,width-1)+py/max(1,height-1))/2*360)%360
                        color=pygame.Color(0); color.hsva=(hue,100,100,100)
                        surface.set_at((px,py),color)
                self._rarity_icon_cache[cache_key]=surface
            self.screen.blit(surface,rect)
        else:
            pygame.draw.rect(self.screen,self._rarity_color(rarity),rect)
        pygame.draw.rect(self.screen,(220,220,220),rect,1)

    def _draw_combo_icon(self, rect, item):
        if item:
            self._draw_rarity_icon(item.get("rarity","common"),rect)
        else:
            pygame.draw.rect(self.screen,(90,90,90),rect)
            pygame.draw.rect(self.screen,(160,160,160),rect,1)

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
        self._draw_rarity_icon(item.get("rarity","common"),pygame.Rect(0,0,size,size))
        self.screen=prior
        surface.set_alpha(210)
        self.screen.blit(surface,(x-size//2,y-size//2))

    def _draw_quests_menu(self, outer):
        self._text("Active quests",(outer.left+18,outer.top+18))
        list_rect=pygame.Rect(outer.centerx+10,outer.top+12,outer.width//2-24,outer.height-24)
        pygame.draw.rect(self.screen,(46,46,46),list_rect,border_radius=5)
        pygame.draw.rect(self.screen,(105,105,105),list_rect,1,border_radius=5)
        self._text("Active quests",(list_rect.left+14,list_rect.top+14))
        self._text("No active quests yet.",(list_rect.left+14,list_rect.top+48))

    def _draw_upgrades_menu(self, state, outer):
        area=outer.inflate(-16,-16)
        pygame.draw.rect(self.screen,(46,46,46),area,border_radius=5)
        if self.upgrade_tab=="combination":
            self._draw_combination_menu(state,area)
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
        self._text(f"{item['name']} · {item['rarity'].title()} · Lv {item['level']}",(x,y))
        stats=list(item.get("stats",{}).items())[:2]
        if stats:
            self._text(" · ".join(f"{key} {value}" for key,value in stats),(x,y+17))
        for i,combo_id in enumerate(item.get("combinations",[])[:5]):
            rect=pygame.Rect(x+i*11,y+31,8,8)
            pygame.draw.rect(self.screen,(230,175,65) if combo_id is not None else (105,110,125),rect,1)

    def _draw_combination_menu(self,state,area):
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
            self._draw_rarity_icon(base.get("rarity","common"),icon)
            detail_x=icon.right+10; detail_y=left.top+39
            self._text(base.get("name","Item"),(detail_x,detail_y)); detail_y+=22
            self._text(f"{base.get('rarity','common').title()} · Level {base.get('level',1)}",(detail_x,detail_y)); detail_y+=21
            self._text(f"Type: {base.get('type','item').title()}",(detail_x,detail_y)); detail_y+=23
            for stat_name,stat_value in base.get("stats",{}).items():
                self._text(f"{stat_name}: {stat_value}",(left.left+12,detail_y)); detail_y+=20
            slots=base.get("combinations",[])
            slot_x=left.right-50; slot_y=left.top+40
            self._text("Combinations",(slot_x-76,left.top+14))
            for i in range(len(slots)):
                rect=pygame.Rect(slot_x,slot_y+i*50,42,42)
                self._drop_targets[f"combo:{base['id']}:{i}"]=rect.copy()
                pygame.draw.rect(self.screen,(48,48,48),rect,border_radius=3)
                pygame.draw.rect(self.screen,(205,205,205),rect,2,border_radius=3)
                if slots[i] is not None:
                    combo=by_id.get(str(slots[i]))
                    if combo: self._draw_rarity_icon(combo.get("rarity","common"),rect.inflate(-4,-4))
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
                    self._draw_rarity_icon(item.get("rarity","common"),icon)
                    for combo_index,combo_id in enumerate(item.get("combinations",[])[:5]):
                        mini=pygame.Rect(icon.right+3,rect.y+6+combo_index*8,6,6)
                        self._draw_combo_icon(mini,next((entry for entry in items if str(entry.get("id"))==str(combo_id)),None) if combo_id is not None else None)
        self.screen.set_clip(prior_clip)
        self._draw_inventory_scrollbar(grid_rect,rows,visible_rows)
        if self.menu_tab=="inventory":
            self._draw_inventory_links(items,self._last_state.get("active_slots",{}))

    def _draw_bazaar_menu(self,outer,state):
        catalog=state.get("spawn_catalog",[])
        self._text("Bazaar · Test item spawner",(outer.left+16,outer.top+10))
        self._text("Click an item's rarity icon to add it to your inventory.",(outer.left+16,outer.top+31))
        self._text(f"Inventory: {len(state.get('items',[]))} / 200",(outer.right-145,outer.top+12))
        columns=2; cell_w=(outer.width-36)//columns; row_h=48
        visible_rows=max(1,(outer.height-62)//row_h)
        row_count=(len(catalog)+columns-1)//columns
        offset=self._sync_inventory_scroll(row_count,visible_rows)
        for index,item in enumerate(catalog):
            row=index//columns; col=index%columns
            if not offset <= row < offset+visible_rows:
                continue
            x=outer.left+16+col*cell_w; y=outer.top+58+(row-offset)*row_h
            icon=pygame.Rect(x,y,38,38)
            self._buttons[f"spawn_item:{item['id']}"]=icon
            self._draw_rarity_icon(item.get("rarity","common"),icon)
            self._text(item.get("name","Item"),(x+48,y+2))
            stats=" · ".join(f"{key} {value}" for key,value in list(item.get("stats",{}).items())[:2])
            self._text(f"{item.get('type','misc').title()} · Lv {item.get('level',1)} · {stats}"[:48],(x+48,y+21))
        if len(state.get("items",[]))>=200:
            self._text("Inventory full",(outer.left+16,outer.bottom-25))

    def _draw_game_ui(self, state):
        self._buttons = {}
        if "currency_up" in state.get("actions", []):
            self.currency_offset = max(0, self.currency_offset - 1)
        if "currency_down" in state.get("actions", []):
            self.currency_offset += 1
        left, right, top, bottom = 14, self.screen_width-14, 12, self.screen_height-12
        self._text(f"Absolute Score: {state.get('absolute_score',0)}", (left,top))
        self._text(f"Total Score: {state.get('total_score',0)}", (left,top+22))
        elapsed_ms = self.get_elapsed_ms()
        minutes = elapsed_ms // 60_000
        seconds = (elapsed_ms // 1_000) % 60
        milliseconds = elapsed_ms % 1_000
        self._text(f"Timer {minutes:02d}:{seconds:02d}:{milliseconds:03d}", (left,top+44))
        active=state.get("active_slots",{})
        by_id={str(item.get("id")):item for item in state.get("items",[])}
        for i in range(10):
            rect=pygame.Rect(0,0,34,34); rect.midbottom=(self.screen_width//2+int((i-4.5)*40),bottom)
            item_id=active.get("abilities",[])[i] if i<len(active.get("abilities",[])) else None
            item=by_id.get(str(item_id)) if item_id else None
            pygame.draw.rect(self.screen,(105,105,105),rect,2)
            if item:
                pygame.draw.rect(self.screen,(70,220,115),rect,2)
                self._draw_rarity_icon(item.get("rarity","common"),rect.inflate(-8,-8))
                self._draw_combo_markers(rect,item)
                self._draw_cooldown_overlay(rect,state.get("ability_cooldowns",[0]*10)[i])
        for i in range(5):
            rect=pygame.Rect(0,0,34,34); rect.topleft=(left,top+95+i*38); pygame.draw.rect(self.screen,(105,105,105),rect,2)
            item_id=active.get("armor",[])[i] if i<len(active.get("armor",[])) else None
            item=by_id.get(str(item_id)) if item_id else None
            if item:
                pygame.draw.rect(self.screen,(70,220,115),rect,2)
                self._draw_rarity_icon(item.get("rarity","common"),rect.inflate(-8,-8))
                self._draw_combo_markers(rect,item)
        for i in range(2):
            rect=pygame.Rect(0,0,34,34); rect.topleft=(left,self.screen_height//2+20+i*38); pygame.draw.rect(self.screen,(105,105,105),rect,2)
            item_id=active.get("weapons",[])[i] if i<len(active.get("weapons",[])) else None
            item=by_id.get(str(item_id)) if item_id else None
            if item:
                pygame.draw.rect(self.screen,(70,220,115),rect,2)
                self._draw_rarity_icon(item.get("rarity","common"),rect.inflate(-8,-8))
                self._draw_combo_markers(rect,item)
                self._draw_cooldown_overlay(rect,state.get("weapon_cooldowns",[0,0])[i])
        self._button("pause", "Resume" if state.get("paused") else "Pause", (right-60,top+18),100,34)
        self._button("increase_difficulty",
                     f"Difficulty {state.get('difficulty_level', 0)} +",
                     (right-75,top+58),130,32)
        self._text("Quests",(right-105,self.screen_height//2-75))
        self._text("- No active quests",(right-105,self.screen_height//2-48))
        self._text("- Quest list placeholder",(right-105,self.screen_height//2-26))
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
