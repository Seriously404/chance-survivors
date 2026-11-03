"""Game state management system."""

from enum import Enum, auto


class GameState(Enum):
    """Represents all possible game states."""

    MENU = auto()
    SETTINGS = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class GameStateManager:
    """Manages game state transitions and panel management."""

    def __init__(self):
        """Initialize the game state manager."""
        self.state = GameState.MENU
        self.active_panel = None
        self.player_name = ""

    def change_state(self, new_state: GameState) -> None:
        """Change the current game state.

        Args:
            new_state: The new state to transition to.
        """
        self.state = new_state
        self.active_panel = None

    def start_game(self, player_name: str) -> None:
        """Start a new game with the given player name.

        Args:
            player_name: The name of the player.
        """
        self.player_name = player_name
        self.change_state(GameState.PLAYING)

    def open_panel(self, panel_name: str) -> None:
        """Open a panel during gameplay.

        Args:
            panel_name: The name of the panel to open.
        """
        if self.state == GameState.PLAYING:
            self.active_panel = panel_name

    def close_panel(self) -> None:
        """Close the currently active panel."""
        self.active_panel = None

    def is_playing(self) -> bool:
        """Check if the game is currently playing.

        Returns:
            True if the game state is PLAYING.
        """
        return self.state == GameState.PLAYING

    def is_menu(self) -> bool:
        """Check if the game is in the menu state.

        Returns:
            True if the game state is MENU.
        """
        return self.state == GameState.MENU

    def is_settings(self) -> bool:
        """Check if the game is in the settings state.

        Returns:
            True if the game state is SETTINGS.
        """
        return self.state == GameState.SETTINGS

    def is_game_over(self) -> bool:
        """Check if the game is in the game over state.

        Returns:
            True if the game state is GAME_OVER.
        """
        return self.state == GameState.GAME_OVER
