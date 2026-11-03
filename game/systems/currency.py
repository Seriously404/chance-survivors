"""Run currency rewards, kept independent of drawing.

Currency amounts now use LargeNumber to support extreme magnitudes without
precision loss or overflow.
"""
import random

from game.systems.numbers import LargeNumber


class CurrencyWallet:
    """Wallet for tracking multiple currency types with large-number support."""

    def __init__(self) -> None:
        self.amounts: dict[str, LargeNumber] = {
            "Copper": LargeNumber(0),
            "Gold": LargeNumber(0),
        }

    def reward_for_kill(self, rng: random.Random | None = None, luck: float = 0.0) -> tuple[str, LargeNumber]:
        """Award currency for killing an enemy.

        Args:
            rng: Random number generator. Defaults to module-level random.
            luck: Player luck stat affecting reward chances.

        Returns:
            Tuple of (currency_type, amount) where amount is a LargeNumber.
        """
        rng = rng or random
        gold_chance = min(0.5, 0.08 + max(0.0, luck) * 0.005)
        if rng.random() < gold_chance:
            currency, amount = "Gold", LargeNumber(1)
        else:
            amount = LargeNumber(rng.randint(3, 7))
            currency = "Copper"
        self.amounts[currency] = self.amounts.get(currency, LargeNumber(0)) + amount
        return currency, amount

    def spend(self, currency: str, amount: LargeNumber) -> bool:
        """Spend currency if sufficient balance exists.

        Args:
            currency: Currency type to spend.
            amount: Amount to spend (must be LargeNumber).

        Returns:
            True if spent successfully, False if insufficient balance.
        """
        if currency not in self.amounts:
            return False
        balance = self.amounts[currency]
        if balance < amount:
            return False
        self.amounts[currency] = balance - amount
        return True

    def get(self, currency: str) -> LargeNumber:
        """Get current balance for a currency type."""
        return self.amounts.get(currency, LargeNumber(0))

    def add(self, currency: str, amount: LargeNumber) -> None:
        """Add currency to wallet.

        Args:
            currency: Currency type to add.
            amount: Amount to add (must be LargeNumber).
        """
        self.amounts[currency] = self.amounts.get(currency, LargeNumber(0)) + amount


class CurrencyNotifications:
    """Display notifications for currency changes."""

    def __init__(self, lifetime: float = 3.0) -> None:
        self.lifetime = lifetime
        self.items: list[dict] = []

    def add(self, currency: str, amount: LargeNumber) -> None:
        """Add a notification for currency gain.

        Args:
            currency: Currency type.
            amount: Amount gained (will be formatted for display).
        """
        self.items.append({
            "text": f"+{amount.format()} {currency}",
            "remaining": self.lifetime,
        })

    def update(self, dt: float) -> None:
        """Update notifications and remove expired ones."""
        for item in self.items:
            item["remaining"] -= dt
        self.items = [item for item in self.items if item["remaining"] > 0]

