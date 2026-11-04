"""Large-number helpers for score and progression values.

The game is designed to scale toward extreme values, so ordinary float/int math
is not sufficient for a durable score pipeline. This module wraps Decimal to keep
arithmetic exact for large totals while still providing UI-friendly scientific
notation for display.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
import math
from typing import SupportsFloat


# Keep individual currency spends visible through the practical 1e308 goal.
_ARITHMETIC_PRECISION = 512


class LargeNumber:
    """Decimal-backed numeric primitive for high-magnitude gameplay values."""

    def __init__(self, value: object = 0) -> None:
        self.value = self._coerce(value)

    @staticmethod
    def _coerce(value: object) -> Decimal:
        if isinstance(value, LargeNumber):
            return value.value
        if isinstance(value, Decimal):
            decimal_value = value
        elif isinstance(value, int):
            decimal_value = Decimal(value)
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("LargeNumber does not accept NaN or Infinity")
            decimal_value = Decimal(str(value))
        elif isinstance(value, str):
            try:
                decimal_value = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError(
                    f"Unsupported large-number literal: {value!r}") from exc
        else:
            raise TypeError(
                f"Unsupported type for LargeNumber: {type(value).__name__}")

        if not decimal_value.is_finite():
            raise ValueError("LargeNumber does not accept NaN or Infinity")
        return decimal_value

    @classmethod
    def from_score(cls, value: object) -> "LargeNumber":
        return cls(value)

    def __add__(self, other: object) -> "LargeNumber":
        with localcontext() as context:
            context.prec = _ARITHMETIC_PRECISION
            return LargeNumber(self.value + self._coerce(other))

    def __radd__(self, other: object) -> "LargeNumber":
        return self + other

    def __sub__(self, other: object) -> "LargeNumber":
        with localcontext() as context:
            context.prec = _ARITHMETIC_PRECISION
            return LargeNumber(self.value - self._coerce(other))

    def __rsub__(self, other: object) -> "LargeNumber":
        with localcontext() as context:
            context.prec = _ARITHMETIC_PRECISION
            return LargeNumber(self._coerce(other) - self.value)

    def __mul__(self, other: object) -> "LargeNumber":
        with localcontext() as context:
            context.prec = _ARITHMETIC_PRECISION
            return LargeNumber(self.value * self._coerce(other))

    def __rmul__(self, other: object) -> "LargeNumber":
        return self * other

    def __truediv__(self, other: object) -> "LargeNumber":
        with localcontext() as context:
            context.prec = _ARITHMETIC_PRECISION
            return LargeNumber(self.value / self._coerce(other))

    def __rtruediv__(self, other: object) -> "LargeNumber":
        with localcontext() as context:
            context.prec = _ARITHMETIC_PRECISION
            return LargeNumber(self._coerce(other) / self.value)

    def __pow__(self, exponent: int) -> "LargeNumber":
        return LargeNumber(self.value ** exponent)

    def __neg__(self) -> "LargeNumber":
        return LargeNumber(-self.value)

    def __abs__(self) -> "LargeNumber":
        return LargeNumber(abs(self.value))

    def __lt__(self, other: object) -> bool:
        return self.value < self._coerce(other)

    def __le__(self, other: object) -> bool:
        return self.value <= self._coerce(other)

    def __gt__(self, other: object) -> bool:
        return self.value > self._coerce(other)

    def __ge__(self, other: object) -> bool:
        return self.value >= self._coerce(other)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LargeNumber):
            return self.value == other.value
        return self.value == self._coerce(other)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __int__(self) -> int:
        return int(self.value)

    def __float__(self) -> float:
        return float(self.value)

    def __str__(self) -> str:
        return self.format()

    def __repr__(self) -> str:
        return f"LargeNumber({self.format()!r})"

    def format(self, *, places: int = 2) -> str:
        """Render the value in a compact but readable form."""
        if self.value == 0:
            return "0"
        normalized = self.value.normalize()
        exponent = normalized.adjusted()
        if exponent >= 12 or exponent <= -4:
            return format(normalized, "E")
        quantized = normalized.quantize(
            Decimal(1).scaleb(-places), rounding="ROUND_HALF_UP")
        return format(quantized, "f")

    def scale_by_percent(self, percentage: SupportsFloat) -> "LargeNumber":
        percent = Decimal(str(float(percentage)))
        factor = Decimal(1) + percent / Decimal(100)
        return LargeNumber(self.value * factor)

    def to_decimal(self) -> Decimal:
        return self.value

    @property
    def is_zero(self) -> bool:
        return self.value == 0
