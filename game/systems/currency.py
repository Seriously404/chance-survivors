"""Run currency rewards, kept independent of drawing."""
import random

from game.utils.large_number import LargeNumber


class CurrencyWallet:
    def __init__(self):
        self.amounts = {"Copper": LargeNumber(0), "Gold": LargeNumber(0)}

    def reward_for_kill(self, rng=random, luck: float = 0.0,
                        reward_multiplier: LargeNumber | int | float | str = 1) -> tuple[str, LargeNumber]:
        gold_chance=min(0.5,0.08+max(0.0,luck)*0.005)
        currency, base_amount = ("Gold", 1) if rng.random() < gold_chance else ("Copper", rng.randint(3, 7))
        amount = LargeNumber(base_amount) * LargeNumber(reward_multiplier)
        self.amounts[currency] = self.amounts.get(currency, 0) + amount
        return currency, amount


class CurrencyNotifications:
    def __init__(self, lifetime: float = 3.0):
        self.lifetime = lifetime
        self.items: list[dict] = []

    def add(self, currency: str, amount: int) -> None:
        self.items.append({"text": f"+{amount} {currency}", "remaining": self.lifetime})

    def update(self, dt: float) -> None:
        for item in self.items:
            item["remaining"] -= dt
        self.items = [item for item in self.items if item["remaining"] > 0]

