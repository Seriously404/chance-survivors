from enum import Enum, auto


class GameState(Enum):
    MENU = auto()
    SETTINGS = auto()
    PLAYING = auto()
    GAME_OVER = auto()
