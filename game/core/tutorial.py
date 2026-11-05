"""Optional, action-driven guidance for the opening of a run."""


STEPS = (
    ("Move", "Use WASD to move. This is safe practice; skip the guide to begin immediately."),
    ("Dash", "Press Space to dash. It has a short cooldown."),
    ("Visit the Bazaar", "Open Inventory, then choose the Bazaar tab."),
    ("Browse crates", "Choose the Crates tab to see possible rewards and prices."),
    ("Inspect a crate", "Select a crate to inspect it. Buying one is optional."),
    ("Open Inventory", "Choose Inventory to inspect and equip your items."),
    ("Build a combination", "Choose Combination, then select a weapon or ability as a base."),
)


class RunTutorial:
    """Track optional practice actions before the live run clock and spawning."""

    def __init__(self, active=False):
        self.active = active
        self.step = 0

    def observe(self, *, actions, panel, tab, bazaar_tab, movement, paused,
                base_id=None):
        if not self.active:
            return
        if "tutorial_skip" in actions:
            self.active = False
            return
        if "tutorial_next" in actions:
            self._advance()
            return
        checks = (
            not panel and not paused and any(movement),
            not panel and not paused and "dash" in actions,
            panel is not None and tab == "bazaar",
            panel is not None and tab == "bazaar" and bazaar_tab == "crates",
            panel is not None and tab == "bazaar" and bazaar_tab == "crates"
            and any(action.startswith("bazaar_crate_select:") for action in actions),
            panel is not None and tab == "inventory",
            panel is not None and tab == "combination"
            and base_id is not None
            and f"select:{base_id}" in actions,
        )
        if checks[self.step]:
            self._advance()

    def _advance(self):
        self.step += 1
        if self.step >= len(STEPS):
            self.active = False

    def view(self):
        if not self.active:
            return None
        title, text = STEPS[self.step]
        return {"title": title, "text": text,
                "step": self.step + 1, "total": len(STEPS)}
