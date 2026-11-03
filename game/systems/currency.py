"""Run currency rewards, kept independent of drawing."""
import random


class CurrencyWallet:
    def __init__(self):
        self.amounts = {"Copper": 0, "Gold": 0}

    def reward_for_kill(self, rng=random, luck: float = 0.0) -> tuple[str, int]:
        gold_chance=min(0.5,0.08+max(0.0,luck)*0.005)
        currency, amount = ("Gold", 1) if rng.random() < gold_chance else ("Copper", rng.randint(3, 7))
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

