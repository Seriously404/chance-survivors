"""Contextual menu teaching and mandatory main-quest choice presentation."""

import math

import pygame

from game.systems.main_quest_choices import quest_challenge_modifiers


MENU_HELP = {
    "engineering": ("Defend the core", (
        "Engineer is a defense run. Keep the core alive while completing waves. The core and your deployed structures have their own health bars.",
        "Your repair gun heals friendly structures instead of acting as a normal damage weapon. Aim repair shots at damaged defenses or the core.",
        "Hold a construction ability key to position its outline; release to place it. Walls block and absorb enemies while different turret elements cover different threats.",
        "Repair Pulse restores nearby defenses. Overclock temporarily improves nearby structures. Architect Protocol is a short ultimate boost, not permanent invulnerability.",
    )),
    "inventory": ("Equip your build", (
        "Hover an item to inspect its role, stats and effects. Drag it from the inventory into a matching equipment slot.",
        "Weapons use mouse buttons; abilities use 1–0. Armor has its own shaped slots. Only one dash ability can be equipped.",
        "Drag equipment back into the inventory to remove it. Open Combination to modify an equipped base without consuming its supplements.",
    )),
    "quests": ("Choose your commitments", (
        "Main quests define your run. Their forced choice pauses combat until you choose or skip. Read restrictions before committing.",
        "Side quests are optional. Accept a card to start tracking its objective; progress before acceptance does not count.",
        "Active cards show progress bars. Scroll each quest column independently to read more cards.",
    )),
    "overview": ("Understand your build", (
        "Overview summarizes your equipped items and current bonuses. Your final score and your combat damage are different systems.",
        "Compare equipment and ability roles here, then use Inventory to equip items or Combination to change their behavior.",
    )),
    "combination": ("Build an interaction", (
        "Unlock combinations by discovering three distinct abilities. The selected base must be at least item level 2. These are progress requirements, not timers.",
        "Select a weapon, ability or armor item as the base. Drag compatible inventory items into its combination slots.",
        "Combination changes apply immediately. Read the preview to see the effects the runtime will actually execute; no Apply button is needed.",
        "Numeric supplement stats transfer at 35%, rising by 5% per supplement level to 100%. Executable special tags retain their behavior.",
        "Supplements remain owned. Drag a supplement out to detach it. Rarity determines how many slots the base provides.",
    )),
    "market": ("Buy a relic", (
        "The market sells relics. Inspect the description: owned passive effects and local combination effects can have different rules.",
        "Prices show both the required currencies and your balance. A failed purchase changes neither wallet nor inventory.",
    )),
    "crates": ("Inspect before gambling", (
        "Select a box in the room to inspect all its possible rewards and their probabilities. Scroll the reward panel to see more.",
        "Luck changes eligibility and odds. A listed high-rarity reward may show zero chance until your luck is sufficient; there is no waiting gate.",
        "Buy chooses the reward immediately and spends the displayed currencies once. Skip only shortens the animation; it never rerolls the reward.",
    )),
    "fusion": ("Craft a new item", (
        "Open the fusion codex and select a recipe. Ingredient icons show what you own; matching inventory items are highlighted.",
        "Drag the required ingredients into the crafting table, then press Fuse. Ingredients are consumed only when crafting succeeds.",
        "The result appears on the left and is added to your inventory. Fusion-only items cannot be purchased as market shortcuts.",
    )),
    "rarity_upgrader": ("Invest in a rarity gamble", (
        "Select an owned item. Choose a currency from the dropdown and use its slider to add an amount to the pool. Repeat for other currencies.",
        "Favorable currencies contribute more; unfavorable ones contribute less. The preview shows the actual success chance at your current luck.",
        "The target slider is continuous. Between rarity dots, its position divides successful outcomes between the two adjacent rarities.",
        "An attempt spends its pool even if it fails. Higher rarity is a multiplier and unlocks more combination slots.",
    )),
    "level_upgrader": ("Strengthen an item", (
        "Select an owned item to inspect its next level and exact price. Every required currency shows what you have and what you need.",
        "Level upgrades are guaranteed when affordable. Compare the resulting stats before spending; naturally common items can have strong investment potential.",
    )),
    "sell": ("Sell carefully", (
        "Select an item from the inventory on the right. Read its details and sale value on the left, then press Sell.",
        "Selling removes that item. Equipped or combination-linked items may need to be removed from their current role first.",
    )),
    "exchange": ("Trade currencies", (
        "Drag the currency you have onto the source side of the scale and the currency you want onto its destination side.",
        "Move the amount slider and inspect the quote before converting. Currency worth and the exchange fee determine what you receive.",
        "Converting back loses value. Exchange is a way to reach a needed currency, not a way to create money.",
    )),
}


class GuidanceUI:
    def _menu_help_key(self):
        return self._bazaar_tab if self.menu_tab == "bazaar" else self.menu_tab

    def _guidance_input(self, running, shots, actions):
        """Capture every input while a teaching or quest modal is present."""
        if not (getattr(self, "_quest_choice_active", False)
                or getattr(self, "_context_help_key", None)):
            return None
        handler = self.input_handler
        positions = list(shots)
        if handler.drag_active:
            positions.append(handler.mouse_position)
        if handler.drag_release:
            positions.append(handler.drag_release[1])
        if getattr(self, "_quest_choice_active", False):
            for action in actions:
                if action in ("inventory_up", "inventory_down"):
                    direction = -1 if action == "inventory_up" else 1
                    for key, (rect, maximum) in self._quest_description_regions.items():
                        if rect.collidepoint(handler.mouse_position):
                            offset = self._quest_description_offsets.get(key, 0)
                            self._quest_description_offsets[key] = max(0, min(maximum, offset + direction))
            for pos in positions:
                for key, rect in getattr(self, "_quest_power_sliders", {}).items():
                    start = handler.drag_start or pos
                    if rect.inflate(0, 20).collidepoint(start) or rect.inflate(0, 20).collidepoint(pos):
                        ratio = max(0, min(1, (pos[0] - rect.left) / max(1, rect.width)))
                        self._quest_powers[key] = 1.05 + .95 * ratio
        selected = [key for pos in shots for key, rect in self._buttons.items()
                    if rect.collidepoint(pos)]
        output = []
        for key in selected:
            if key.startswith("quest_confirm:"):
                quest_id = key.split(":", 1)[1]
                output.append(f"quest_choose:{quest_id}:{self._quest_powers[quest_id]:.4f}")
            elif key in ("quest_reroll_main", "quest_decline_main"):
                output.append(key)
            elif key == "context_help_close":
                self._context_help_key = None
                self._tutorial_capture = handler.click_release is None
            elif key == "context_help_next":
                self._context_help_page += 1
            elif key == "context_help_prev":
                self._context_help_page = max(0, self._context_help_page - 1)
        if (not getattr(self, "_quest_choice_active", False)
                and "back" in actions):
            self._context_help_key = None
        handler.player_dx = handler.player_dy = 0
        handler.held_movement.clear()
        handler.held_abilities.clear()
        handler.mouse_buttons_held.clear()
        handler.held_fire = False
        handler.fire_events = []
        if any(action.startswith("quest_choose:") or action == "quest_decline_main"
               for action in output):
            self._tutorial_capture = handler.click_release is None
        return running, [], output

    def _draw_context_help(self):
        key = getattr(self, "_context_help_key", None)
        if not key:
            return
        title, pages = MENU_HELP.get(key, MENU_HELP["inventory"])
        if key == "inventory" and getattr(self, "_last_state", {}).get("engineering"):
            pages = MENU_HELP["engineering"][1] + pages
        page = min(getattr(self, "_context_help_page", 0), len(pages) - 1)
        self._context_help_page = page
        self._buttons = {}
        self._hover_slots = []
        self._drop_targets = {}
        self._item_rects = {}
        shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 210))
        self.screen.blit(shade, (0, 0))
        card = pygame.Rect(0, 0, min(650, self.screen_width - 40), 270)
        card.center = (self.screen_width // 2, self.screen_height // 2)
        pygame.draw.rect(self.screen, (25, 38, 45), card, border_radius=10)
        pygame.draw.rect(self.screen, (100, 205, 190), card, 2, border_radius=10)
        self._text(f"{title} · {page + 1}/{len(pages)}", (card.x + 18, card.y + 16))
        for index, line in enumerate(self._codex_wrap(pages[page], card.width - 40)):
            self._text(line, (card.x + 18, card.y + 55 + index * 23))
        self._text("Menus pause combat. Read, experiment, then return to the run.",
                   (card.x + 18, card.bottom - 78))
        self._button("context_help_prev", "Back", (card.x + 75, card.bottom - 30), 110, 32)
        self._button("context_help_next", "Next", (card.centerx, card.bottom - 30), 110, 32)
        self._button("context_help_close", "Got it", (card.right - 75, card.bottom - 30), 110, 32)

    def _draw_main_quest_choice(self, choice):
        self._quest_choice_active = bool(choice and choice.get("pending"))
        if not self._quest_choice_active:
            return False
        self._buttons = {}
        self._hover_slots = []
        self._item_rects = {}
        self._drop_targets = {}
        self._quest_power_sliders = {}
        self._quest_description_regions = {}
        if not hasattr(self, "_quest_description_offsets"):
            self._quest_description_offsets = {}
        if not hasattr(self, "_quest_powers"):
            self._quest_powers = {}
        self.screen.fill((14, 23, 30))
        self._text("CHOOSE YOUR MAIN QUEST · COMBAT PAUSED", (20, 12))
        self._text("Commit to one path, or skip. Your choice shapes this run.", (20, 35))
        gap, margin = 14, 20
        bottom = self.screen_height - 52
        engineer_height = max(105, int(self.screen_height * .25))
        engineer = pygame.Rect(margin, 65, self.screen_width - margin * 2, engineer_height)
        lower_y = engineer.bottom + gap
        lower_width = (engineer.width - gap) // 2
        cards = [engineer, pygame.Rect(margin, lower_y, lower_width, bottom - lower_y),
                 pygame.Rect(margin + lower_width + gap, lower_y, lower_width, bottom - lower_y)]
        for index, (offer, card) in enumerate(zip(choice.get("offers", []), cards)):
            key = offer["id"]
            power = self._quest_powers.setdefault(key, float(offer.get("default_power", offer.get("reward_power", 1.2))))
            selectable = bool(offer.get("power_selectable", index > 0))
            pygame.draw.rect(self.screen, (27, 43, 49), card, border_radius=8)
            pygame.draw.rect(self.screen, (90, 205, 175) if index == 0 else (130, 145, 185), card, 2, border_radius=8)
            self._text(offer.get("name", "Main quest"), (card.x + 12, card.y + 10))
            text_width = card.width - (165 if index == 0 else 26)
            description = offer.get("description", "")
            lines = self._codex_wrap(description, text_width)
            text_clip = pygame.Rect(card.x + 12, card.y + 34, text_width,
                                    card.height - (148 if selectable else 44))
            visible = max(1, text_clip.height // 18)
            maximum = max(0, len(lines) - visible)
            self._quest_description_regions[key] = (text_clip, maximum)
            offset = min(maximum, self._quest_description_offsets.get(key, 0))
            old_clip = self.screen.get_clip()
            self.screen.set_clip(text_clip)
            for row, line in enumerate(lines[offset:offset + visible]):
                self._text(line, (text_clip.x, text_clip.y + row * 18))
            self.screen.set_clip(old_clip)
            if maximum:
                self._text("Scroll description", (card.x + 12, text_clip.bottom + 1))
            if selectable:
                slider = pygame.Rect(card.x + 18, card.bottom - 65, card.width - 36, 8)
                self._quest_power_sliders[key] = slider
                ratio = max(0, min(1, (power - 1.05) / .95))
                pygame.draw.line(self.screen, (95, 110, 130), slider.midleft, slider.midright, 5)
                pygame.draw.circle(self.screen, (230, 205, 115),
                                   (slider.x + round(slider.width * ratio), slider.centery), 8)
                self._text(f"Score ^{power:.4f} · higher means harder",
                           (card.x + 12, card.bottom - 96))
                challenge = quest_challenge_modifiers(power)
                self._text(f"HP ×{challenge['health']:.2f} · damage ×{challenge['damage']:.2f} · spawn ×{challenge['spawn']:.2f}",
                           (card.x + 12, card.bottom - 78))
                center = (card.centerx, card.bottom - 25)
            else:
                self._text(f"Score ^{power:.2f}", (card.right - 145, card.y + 20))
                center = (card.right - 85, card.bottom - 27)
            self._button(f"quest_confirm:{key}", "Choose", center, 130, 32)
        self._button("quest_decline_main", "Skip main quest", (115, self.screen_height - 24), 190, 34)
        if choice.get("rerolls_remaining", 0):
            self._button("quest_reroll_main", "Reroll bottom choices · 1 left",
                         (self.screen_width - 170, self.screen_height - 24), 300, 34)
        else:
            self._text("Reroll used", (self.screen_width - 120, self.screen_height - 32))
        return True

    def _draw_engineering(self, engineering, camera_x, camera_y):
        if not engineering:
            from types import SimpleNamespace
            structures = [ally for ally in getattr(self, '_last_state', {}).get('summons', [])
                          if getattr(ally, 'structure_kind', 'summon') != 'summon']
            if not structures:
                return
            engineering = SimpleNamespace(objective=None, structures=structures)
        objective = getattr(engineering, "objective", None)
        if objective:
            x, y = self.world_to_screen(objective.x, objective.y, camera_x, camera_y)
            polygon = [(x, y - 20), (x + 18, y), (x, y + 20), (x - 18, y)]
            pygame.draw.polygon(self.screen, (65, 180, 170), polygon)
            pygame.draw.polygon(self.screen, (170, 255, 210), polygon, 2)
            self.draw_health_bar(x, y - 32, objective.health, objective.max_health, 72)
            self._text(f"CORE · wave {getattr(engineering, 'wave', 1)}", (int(x - 38), int(y + 24)))
        for structure in getattr(engineering, "structures", []):
            x, y = self.world_to_screen(structure.x, structure.y, camera_x, camera_y)
            kind = getattr(structure, "structure_kind", "turret")
            color = {"wall": (170, 180, 200), "arc_turret": (145, 135, 255),
                     "flame_turret": (255, 140, 65), "frost_turret": (100, 210, 255)}.get(kind, (120, 220, 170))
            rect = pygame.Rect(int(x - 12), int(y - 10), 24, 20)
            pygame.draw.rect(self.screen, color, rect, border_radius=3)
            if getattr(structure, "protocol_remaining", 0) > 0 or getattr(structure, "overclock_remaining", 0) > 0:
                pulse = 18 + round(3 * (1 + math.sin(pygame.time.get_ticks() / 150)))
                pygame.draw.circle(self.screen, (245, 220, 110), rect.center, pulse, 2)
            if kind != "wall":
                pygame.draw.line(self.screen, (235, 245, 250), rect.center,
                                 (rect.right + 8, rect.centery), 4)
            self.draw_health_bar(x, y - 20, structure.health, structure.max_health, 34)
