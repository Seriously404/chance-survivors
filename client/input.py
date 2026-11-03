"""Input processing module."""

import pygame
from typing import List, Tuple


class InputHandler:
    """Handles all input processing for the game."""

    def __init__(self):
        """Initialize the input handler."""
        self.player_dx = 0
        self.player_dy = 0
        self.mouse_position: Tuple[float, float] = (0, 0)
        self.shots: List[Tuple[float, float]] = []
        self.actions: List[str] = []
        self.player_name = ""
        self.name_error = ""
        self.held_fire = False
        self.drag_start = None
        self.drag_release = None
        self.drag_active = False
        self.click_release = None
        self.fire_events = []
        self.mouse_buttons_held = set()

    def process_events(self) -> Tuple[bool, List[Tuple[float, float]], List[str]]:
        """Process all pygame events.

        Returns:
            Tuple of (running, shots, actions).
        """
        running = True
        shots = []
        actions = []
        self.fire_events = []
        self.click_release = None
        self.drag_release = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key, actions)

            elif event.type == pygame.KEYUP:
                self._handle_keyup(event.key)

            elif event.type == pygame.TEXTINPUT:
                self.player_name = (self.player_name + event.text)[:20]

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 3):
                    shots.append(event.pos)
                    self.fire_events.append((event.button,event.pos))
                    self.mouse_buttons_held.add(event.button)
                    self.held_fire = True
                    self.drag_start = event.pos
                    self.drag_active = False
            elif event.type == pygame.MOUSEMOTION:
                if self.drag_start is not None and not self.drag_active:
                    dx=event.pos[0]-self.drag_start[0]; dy=event.pos[1]-self.drag_start[1]
                    self.drag_active=dx*dx+dy*dy >= 64
            elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 3):
                self.mouse_buttons_held.discard(event.button)
                self.held_fire = bool(self.mouse_buttons_held)
                if self.drag_start is not None and self.drag_active:
                    self.drag_release=(self.drag_start,event.pos)
                elif self.drag_start is not None:
                    self.click_release=event.pos
                self.drag_start=None
                self.drag_active=False
            elif event.type == pygame.MOUSEWHEEL:
                actions.extend(["inventory_up" if event.y > 0 else "inventory_down"] * abs(event.y))

        self.mouse_position = pygame.mouse.get_pos()
        return running, shots, actions

    def _handle_keydown(self, key: int, actions: List[str]) -> None:
        """Handle key down events.

        Args:
            key: The key that was pressed.
            actions: List to append action strings to.
        """
        if key == pygame.K_w:
            self.player_dy += 1
        elif key == pygame.K_s:
            self.player_dy -= 1
        elif key == pygame.K_a:
            self.player_dx -= 1
        elif key == pygame.K_d:
            self.player_dx += 1
        elif key == pygame.K_RETURN:
            actions.append("confirm")
        elif key == pygame.K_ESCAPE:
            actions.append("back")
        elif key == pygame.K_q:
            actions.append("open_settings")
        elif key == pygame.K_BACKSPACE:
            self.player_name = self.player_name[:-1]

    def _handle_keyup(self, key: int) -> None:
        """Handle key up events.

        Args:
            key: The key that was released.
        """
        if key == pygame.K_w:
            self.player_dy -= 1
        elif key == pygame.K_s:
            self.player_dy += 1
        elif key == pygame.K_a:
            self.player_dx += 1
        elif key == pygame.K_d:
            self.player_dx -= 1

    def get_movement(self) -> Tuple[float, float]:
        """Get the current player movement vector.

        Returns:
            Tuple of (player_dx, player_dy).
        """
        return self.player_dx, self.player_dy

    def get_mouse_position(self) -> Tuple[float, float]:
        """Get the current mouse position.

        Returns:
            Tuple of (mouse_x, mouse_y).
        """
        return self.mouse_position

    def get_shots(self) -> List[Tuple[float, float]]:
        """Get all recorded shots.

        Returns:
            List of shot positions.
        """
        return self.shots

    def get_actions(self) -> List[str]:
        """Get all recorded actions.

        Returns:
            List of action strings.
        """
        return self.actions

    def reset(self) -> None:
        """Reset the input state."""
        self.player_dx = 0
        self.player_dy = 0
        self.shots = []
        self.actions = []
        self.drag_start = None
        self.drag_release = None
        self.drag_active = False
        self.click_release = None
        self.fire_events = []
        self.mouse_buttons_held.clear()
        self.held_fire = False
