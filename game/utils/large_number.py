"""Decimal-significand numbers with an unbounded base-10 magnitude.

``LargeNumber`` stores a sign, a finite Decimal significand in ``[1, 10)``,
and an arbitrary-size Python integer exponent. It keeps roughly 64 significant
decimal digits for arithmetic while allowing exponents much larger than those
supported by floats or Decimal contexts. Parsing and serialization preserve
the supplied significand exactly; arithmetic rounds to the documented
significant-digit precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
import json
import math
import re
from typing import Any


ARITHMETIC_PRECISION = 64
_NUMBER_RE = re.compile(
    r"^(?P<sign>[+-]?)(?P<coefficient>(?:\d+(?:\.\d*)?|\.\d+))"
    r"(?:[eE](?P<exponent>[+-]?\d+))?$"
)


def _coefficient_parts(value: Decimal) -> tuple[int, Decimal, int]:
    """Return sign, normalized significand, and exponent without context math."""
    if not value.is_finite():
        raise ValueError("LargeNumber only supports finite values")
    sign, digits, decimal_exponent = value.as_tuple()
    if not any(digits):
        return 0, Decimal(0), 0
    first_nonzero = next(index for index, digit in enumerate(digits) if digit)
    significant_digits = digits[first_nonzero:]
    magnitude = len(digits) + decimal_exponent - first_nonzero - 1
    significand = Decimal(
        (0, significant_digits, -(len(significant_digits) - 1)))
    return (-1 if sign else 1), significand, magnitude


@dataclass(frozen=True, slots=True, init=False)
class LargeNumber:
    """A finite signed decimal value whose exponent is an arbitrary-size int."""

    sign: int
    significand: Decimal
    exponent: int

    def __init__(self, value: LargeNumber | Decimal | int | float | str = 0) -> None:
        if isinstance(value, LargeNumber):
            sign, significand, exponent = value.sign, value.significand, value.exponent
        elif isinstance(value, bool):
            sign, significand, exponent = _coefficient_parts(
                Decimal(int(value)))
        elif isinstance(value, int):
            sign, significand, exponent = _coefficient_parts(Decimal(value))
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("LargeNumber only supports finite values")
            sign, significand, exponent = _coefficient_parts(
                Decimal(str(value)))
        elif isinstance(value, Decimal):
            sign, significand, exponent = _coefficient_parts(value)
        elif isinstance(value, str):
            sign, significand, exponent = self._parse_string(value)
        else:
            raise TypeError(
                f"Unsupported LargeNumber input: {type(value).__name__}")

        object.__setattr__(self, "sign", sign)
        object.__setattr__(self, "significand", significand)
        object.__setattr__(self, "exponent", exponent)

    @staticmethod
    def _parse_string(value: str) -> tuple[int, Decimal, int]:
        match = _NUMBER_RE.fullmatch(value.strip())
        if match is None:
            raise ValueError(f"Invalid LargeNumber literal: {value!r}")
        try:
            coefficient = Decimal(match.group("coefficient"))
        except InvalidOperation as exc:
            raise ValueError(
                f"Invalid LargeNumber literal: {value!r}") from exc
        sign, significand, exponent = _coefficient_parts(coefficient)
        if match.group("sign") == "-":
            sign = -sign
        literal_exponent = int(match.group("exponent") or 0)
        return sign, significand, exponent + literal_exponent

    @classmethod
    def _from_parts(cls, sign: int, significand: Decimal, exponent: int) -> LargeNumber:
        if sign == 0 or not significand:
            return cls(0)
        if not significand.is_finite() or significand < 0:
            raise ValueError("Significand must be finite and non-negative")
        normalized_sign, normalized_significand, shift = _coefficient_parts(
            significand)
        instance = object.__new__(cls)
        object.__setattr__(instance, "sign", (1 if sign >
                           0 else -1) * normalized_sign)
        object.__setattr__(instance, "significand", normalized_significand)
        object.__setattr__(instance, "exponent", int(exponent) + shift)
        return instance

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LargeNumber:
        """Restore a versioned representation, rejecting malformed values."""
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("Unsupported LargeNumber serialization version")
        sign = data.get("sign")
        significand_text = data.get("significand")
        exponent = data.get("exponent")
        if type(sign) is not int or sign not in (-1, 0, 1):
            raise ValueError("Serialized sign must be -1, 0, or 1")
        if not isinstance(significand_text, str) or type(exponent) is not int:
            raise ValueError(
                "Serialized significand and exponent have invalid types")
        try:
            significand = Decimal(significand_text)
        except InvalidOperation as exc:
            raise ValueError("Serialized significand is invalid") from exc
        if sign == 0:
            if significand != 0 or exponent != 0:
                raise ValueError(
                    "Serialized zero must use sign=0, significand=0, exponent=0")
            return cls(0)
        if not significand.is_finite() or not Decimal(1) <= significand < Decimal(10):
            raise ValueError(
                "Serialized significand must be finite and in [1, 10)")
        return cls._from_parts(sign, significand, exponent)

    @classmethod
    def from_json(cls, value: str) -> LargeNumber:
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid LargeNumber JSON") from exc
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible, versioned representation."""
        return {
            "version": 1,
            "sign": self.sign,
            "significand": str(self.significand) if self.sign else "0",
            "exponent": self.exponent,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def __bool__(self) -> bool:
        return self.sign != 0

    def __neg__(self) -> LargeNumber:
        return self._from_parts(-self.sign, self.significand, self.exponent)

    def __abs__(self) -> LargeNumber:
        return self._from_parts(abs(self.sign), self.significand, self.exponent)

    def __add__(self, other: LargeNumber | Decimal | int | float | str) -> LargeNumber:
        right = LargeNumber(other)
        if not self:
            return right
        if not right:
            return self
        if self.exponent < right.exponent:
            left, right = right, self
        else:
            left = self
        difference = left.exponent - right.exponent
        if left.sign == right.sign and difference > ARITHMETIC_PRECISION + 2:
            return left
        if left.sign != right.sign and difference > ARITHMETIC_PRECISION + 2:
            return left
        with localcontext() as context:
            context.prec = ARITHMETIC_PRECISION + 4
            aligned_right = right.significand.scaleb(-difference)
            signed_total = left.sign * left.significand + right.sign * aligned_right
        if not signed_total:
            return LargeNumber(0)
        return self._from_parts(
            1 if signed_total > 0 else -1,
            abs(signed_total),
            left.exponent,
        )

    def __radd__(self, other: LargeNumber | Decimal | int | float | str) -> LargeNumber:
        return self + other

    def __sub__(self, other: LargeNumber | Decimal | int | float | str) -> LargeNumber:
        return self + -LargeNumber(other)

    def __rsub__(self, other: LargeNumber | Decimal | int | float | str) -> LargeNumber:
        return LargeNumber(other) - self

    def __mul__(self, other: LargeNumber | Decimal | int | float | str) -> LargeNumber:
        right = LargeNumber(other)
        if not self or not right:
            return LargeNumber(0)
        with localcontext() as context:
            context.prec = ARITHMETIC_PRECISION
            product = self.significand * right.significand
        return self._from_parts(self.sign * right.sign, product, self.exponent + right.exponent)

    def __rmul__(self, other: LargeNumber | Decimal | int | float | str) -> LargeNumber:
        return self * other

    def __truediv__(self, other: LargeNumber | Decimal | int | float | str) -> LargeNumber:
        right = LargeNumber(other)
        if not right:
            raise ZeroDivisionError("LargeNumber division by zero")
        if not self:
            return LargeNumber(0)
        with localcontext() as context:
            context.prec = ARITHMETIC_PRECISION
            quotient = self.significand / right.significand
        return self._from_parts(self.sign * right.sign, quotient, self.exponent - right.exponent)

    def __rtruediv__(self, other: LargeNumber | Decimal | int | float | str) -> LargeNumber:
        return LargeNumber(other) / self

    def __pow__(self, power: int) -> LargeNumber:
        if type(power) is not int:
            return NotImplemented
        if power == 0:
            if not self:
                raise ZeroDivisionError("0 cannot be raised to power 0")
            return LargeNumber(1)
        if power < 0:
            if not self:
                raise ZeroDivisionError(
                    "zero cannot be raised to a negative power")
            return LargeNumber(1) / (self ** -power)
        if not self:
            return LargeNumber(0)
        result = LargeNumber(1)
        factor = self
        remaining = power
        while remaining:
            if remaining & 1:
                result *= factor
            remaining >>= 1
            if remaining:
                factor *= factor
        return result

    def _compare_magnitude(self, other: LargeNumber) -> int:
        if self.exponent != other.exponent:
            return 1 if self.exponent > other.exponent else -1
        if self.significand == other.significand:
            return 0
        return 1 if self.significand > other.significand else -1

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (LargeNumber, Decimal, int, float, str)):
            return NotImplemented
        right = LargeNumber(other)
        return (self.sign == right.sign and
                (not self.sign or (self.exponent == right.exponent and
                                   self.significand == right.significand)))

    def __lt__(self, other: LargeNumber | Decimal | int | float | str) -> bool:
        right = LargeNumber(other)
        if self.sign != right.sign:
            return self.sign < right.sign
        if not self.sign:
            return False
        comparison = self._compare_magnitude(right)
        return comparison < 0 if self.sign > 0 else comparison > 0

    def __le__(self, other: LargeNumber | Decimal | int | float | str) -> bool:
        return self == other or self < other

    def __gt__(self, other: LargeNumber | Decimal | int | float | str) -> bool:
        return not self <= other

    def __ge__(self, other: LargeNumber | Decimal | int | float | str) -> bool:
        return not self < other

    def to_float(self) -> float:
        """Convert only when the finite value survives as a nonzero float."""
        if not self:
            return 0.0
        try:
            result = float(f"{self.sign * self.significand}e{self.exponent}")
        except (OverflowError, ValueError) as exc:
            raise OverflowError(
                "LargeNumber is outside the finite float range") from exc
        if not math.isfinite(result) or result == 0.0:
            raise OverflowError(
                "LargeNumber is outside the representable float range")
        return result

    def format_scientific(self, significant_digits: int = 6) -> str:
        if type(significant_digits) is not int or significant_digits < 1:
            raise ValueError("significant_digits must be a positive integer")
        if not self:
            return "0"
        with localcontext() as context:
            context.prec = max(significant_digits, 1)
            rendered = format(self.significand, f".{significant_digits - 1}g")
        _, normalized, shift = _coefficient_parts(Decimal(rendered))
        return f"{'-' if self.sign < 0 else ''}{normalized}e{self.exponent + shift:+d}"

    def __str__(self) -> str:
        if not self:
            return "0"
        if -6 <= self.exponent <= 15:
            _, digits, significand_exponent = self.significand.as_tuple()
            coefficient = "".join(str(digit) for digit in digits)
            decimal_exponent = significand_exponent + self.exponent
            point = len(coefficient) + decimal_exponent
            if point <= 0:
                rendered = "0." + "0" * -point + coefficient
            elif point >= len(coefficient):
                rendered = coefficient + "0" * (point - len(coefficient))
            else:
                rendered = coefficient[:point] + "." + coefficient[point:]
            if "." in rendered:
                rendered = rendered.rstrip("0").rstrip(".")
            return f"{'-' if self.sign < 0 else ''}{rendered}"
        return self.format_scientific()

    def __repr__(self) -> str:
        return f"LargeNumber('{self.format_scientific(17)}')"
