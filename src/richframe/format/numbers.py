"""Number formatters."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Any

from .formatter import FormatContext, FormatResult

try:  # pragma: no cover - optional dependency
    from babel.numbers import get_decimal_symbol, get_group_symbol
except Exception:  # pragma: no cover - fallback when babel missing
    get_decimal_symbol = None  # type: ignore[assignment]
    get_group_symbol = None  # type: ignore[assignment]

__all__ = ["NumberFormatter", "CurrencyFormatter", "PercentageFormatter"]


@dataclass(slots=True)
class NumberFormatter:
    """Format numeric values with configurable precision and locale support."""

    precision: int | None = 2
    min_precision: int = 0
    max_precision: int | None = None
    trim_trailing_zeros: bool = False
    use_grouping: bool = True
    thousands: str = ","
    decimal: str = "."
    locale: str | None = None

    def __call__(self, value: object, context: FormatContext) -> FormatResult:
        if value is None or _is_nan(value):
            return ""
        decimal_value = _coerce_decimal(value)
        if decimal_value is None:
            return str(value)
        scale = self._resolve_scale(decimal_value)
        quantized = self._quantize(decimal_value, scale)
        base = self._format_quantized(quantized, scale)
        if self.trim_trailing_zeros and scale > self.min_precision:
            base = _trim_trailing(base, ".", self.min_precision)
        thousands, decimal = self._resolve_separators(context)
        return _apply_separators(base, thousands, decimal, self.use_grouping)

    def _resolve_scale(self, value: Decimal) -> int:
        if self.precision is not None:
            return max(self.min_precision, self.precision)
        normalized = value.normalize()
        exponent = -normalized.as_tuple().exponent
        inferred = max(exponent, 0)
        scale = max(self.min_precision, inferred)
        if self.max_precision is not None:
            scale = min(scale, self.max_precision)
        return max(scale, 0)

    def _quantize(self, value: Decimal, scale: int) -> Decimal:
        if scale == 0:
            quant = Decimal("1")
        else:
            quant = Decimal("1").scaleb(-scale)
        with localcontext() as ctx:
            ctx.rounding = ROUND_HALF_UP
            try:
                return value.quantize(quant, context=ctx)
            except InvalidOperation:
                return value

    def _format_quantized(self, value: Decimal, scale: int) -> str:
        format_spec = f",.{scale}f" if self.use_grouping else f".{scale}f"
        return format(value, format_spec)

    def _resolve_separators(self, context: FormatContext) -> tuple[str, str]:
        locale = self.locale or context.locale
        thousands = self.thousands
        decimal = self.decimal
        if locale and get_decimal_symbol and get_group_symbol:
            if self.thousands == ",":
                try:
                    thousands = get_group_symbol(locale)
                except Exception:  # pragma: no cover - defensive
                    thousands = self.thousands
            if self.decimal == ".":
                try:
                    decimal = get_decimal_symbol(locale)
                except Exception:  # pragma: no cover - defensive
                    decimal = self.decimal
        if not self.use_grouping:
            thousands = ""
        return thousands, decimal


@dataclass(slots=True)
class CurrencyFormatter(NumberFormatter):
    """Format values as currency strings."""

    symbol: str = "$"
    trailing_symbol: bool = False

    def __call__(self, value: object, context: FormatContext) -> FormatResult:
        base = NumberFormatter.__call__(self, value, context)
        if not base:
            return base
        return f"{base}{self.symbol}" if self.trailing_symbol else f"{self.symbol}{base}"


@dataclass(slots=True)
class PercentageFormatter(NumberFormatter):
    """Format values as a percentage."""

    precision: int | None = 1

    def __call__(self, value: object, context: FormatContext) -> FormatResult:
        if value is None or _is_nan(value):
            return ""
        decimal_value = _coerce_decimal(value)
        if decimal_value is None:
            return str(value)
        scaled = decimal_value * Decimal(100)
        formatted = NumberFormatter.__call__(self, scaled, context)
        return "" if formatted == "" else f"{formatted}%"


def _coerce_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value.is_nan():
            return None
        return value
    if isinstance(value, (int, float)):
        if _is_nan(value):
            return None
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return Decimal(stripped)
        except InvalidOperation:
            return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _apply_separators(text: str, thousands: str, decimal: str, use_grouping: bool) -> str:
    result = text
    if use_grouping and thousands and thousands != ",":
        result = result.replace(",", "{COMMA}")
        result = result.replace("{COMMA}", thousands)
    if not use_grouping:
        result = result.replace(",", "")
    if decimal != ".":
        result = result.replace(".", decimal)
    return result


def _trim_trailing(value: str, decimal_point: str, min_digits: int) -> str:
    if decimal_point not in value:
        return value
    head, tail = value.split(decimal_point, 1)
    trimmed = tail.rstrip("0")
    if len(trimmed) < min_digits:
        trimmed = trimmed + "0" * (min_digits - len(trimmed))
    if trimmed:
        return f"{head}{decimal_point}{trimmed}"
    return head if min_digits == 0 else f"{head}{decimal_point}{'0' * min_digits}"


def _is_nan(value: object) -> bool:
    try:
        number = float(value)  # type: ignore[arg-type]
    except Exception:
        return False
    return number != number
