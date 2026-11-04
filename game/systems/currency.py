"""Run currency rewards, kept independent of drawing.

Currency amounts now use LargeNumber to support extreme magnitudes without
precision loss or overflow.
"""
import math
import random

from game.systems.numbers import LargeNumber

from .game_definitions import load_currencies


CURRENCY_DEFINITIONS: dict[str, dict] = {
    currency["id"]: currency for currency in load_currencies()
}
CURRENCY_NAMES: dict[str, str] = {
    alias.casefold(): currency["name"]
    for currency in CURRENCY_DEFINITIONS.values()
    for alias in (currency["id"], currency["name"])
}


class CurrencyWallet:
    """Wallet for tracking multiple currency types with large-number support."""

    def __init__(self) -> None:
        self.amounts: dict[str, LargeNumber] = {
            currency["name"]: LargeNumber(0)
            for currency in CURRENCY_DEFINITIONS.values()
        }

    @staticmethod
    def _currency_name(currency: str) -> str | None:
        return CURRENCY_NAMES.get(currency.casefold())

    def reward_for_kill(self, rng: random.Random | None = None, luck: float = 0.0,
                        multiplier: int | LargeNumber = 1) -> tuple[str, LargeNumber]:
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
        multiplier = LargeNumber(multiplier)
        if multiplier <= 0:
            raise ValueError("Enemy reward multiplier must be positive")
        amount *= multiplier
        self.amounts[currency] = self.amounts.get(
            currency, LargeNumber(0)) + amount
        return currency, amount

    def reward_for_enemy(
        self,
        currency: str,
        base_amount: int | LargeNumber,
        rng: random.Random | None = None,
        luck: float = 0.0,
        multiplier: int | LargeNumber = 1,
    ) -> tuple[str, LargeNumber]:
        """Award an enemy's configured currency, with luck affecting bonus drops."""
        currency_name = self._currency_name(currency)
        if currency_name is None:
            raise ValueError(f"Unknown enemy reward currency: {currency}")

        amount = LargeNumber(base_amount) * LargeNumber(multiplier)
        if amount <= 0:
            raise ValueError(
                "Enemy currency reward and multiplier must be positive")

        luck = float(luck)
        if not math.isfinite(luck):
            raise ValueError("Luck must be finite")
        if luck < 0:
            luck = 0.0
        currency_id = next(
            currency_id
            for currency_id, definition in CURRENCY_DEFINITIONS.items()
            if definition["name"] == currency_name
        )
        drop_modifier = float(
            CURRENCY_DEFINITIONS[currency_id].get("drop_rate_modifier", 1.0))
        luck_factor = luck / (10.0 + luck) if luck < 10.0 else 1.0
        bonus_chance = min(0.75, max(0.0, drop_modifier)
                           * (0.05 + 0.85 * luck_factor))
        rng = rng or random
        if rng.random() < bonus_chance:
            amount = amount + amount

        self.amounts[currency_name] = self.amounts.get(
            currency_name, LargeNumber(0)) + amount
        return currency_name, amount

    def gold_bonus_for_kill(self, rng: random.Random | None = None, luck: float = 0.0) -> LargeNumber:
        """Occasionally award gold alongside an enemy's ordinary currency."""
        rng = rng or random
        chance = min(0.35, 0.15 + max(0.0, float(luck)) * 0.005)
        if rng.random() >= chance:
            return LargeNumber(0)
        amount = LargeNumber(rng.randint(2, 4))
        self.add("Gold", amount)
        return amount

    def spend(self, currency: str, amount: LargeNumber) -> bool:
        """Spend currency if sufficient balance exists.

        Args:
            currency: Currency type to spend.
            amount: Amount to spend (must be LargeNumber).

        Returns:
            True if spent successfully, False if insufficient balance.
        """
        currency_name = self._currency_name(currency)
        if currency_name is None or currency_name not in self.amounts:
            return False
        balance = self.amounts[currency_name]
        if balance < amount:
            return False
        self.amounts[currency_name] = balance - amount
        return True

    def get(self, currency: str) -> LargeNumber:
        """Get current balance for a currency type."""
        currency_name = self._currency_name(currency)
        return self.amounts.get(currency_name, LargeNumber(0)) if currency_name else LargeNumber(0)

    def add(self, currency: str, amount: LargeNumber) -> None:
        """Add currency to wallet.

        Args:
            currency: Currency type to add.
            amount: Amount to add (must be LargeNumber).
        """
        currency_name = self._currency_name(currency)
        if currency_name is None:
            raise ValueError(f"Unknown currency: {currency}")
        self.amounts[currency_name] = self.amounts.get(
            currency_name, LargeNumber(0)) + amount


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
