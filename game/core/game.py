from game.core.states import GameState


class Game:
    def __init__(self):
        self.state = GameState.MENU
        self.active_panel = None

        self.player_name = ""

    def change_state(self, new_state):
        self.state = new_state
        self.active_panel = None

    def start_game(self, player_name):
        self.player_name = player_name
        self.change_state(GameState.PLAYING)

    def open_panel(self, panel_name):
        if self.state == GameState.PLAYING:
            self.active_panel = panel_name

    def close_panel(self):
        self.active_panel = None
