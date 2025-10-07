"""Number formatters."""
from __future__ import annotations

from dataclasses import dataclass

from .formatter import FormatContext, FormatResult, Formatter

__all__ = ["NumberFormatter", "CurrencyFormatter", "PercentageFormatter"]


@dataclass(slots=True)
class NumberFormatter:
    """Format floats and decimals with configurable precision."""

    precision: int = 2
    thousands: str = ","
    decimal: str = "."

    def __call__(self, value: object, context: FormatContext) -> FormatResult:
        if value is None or _is_nan(value):
            return ""
        try:
            number = float(value)
        except Exception:
            return str(value)
        formatted = f"{number:,.{self.precision}f}"
        if self.thousands != "," or self.decimal != ".":
            formatted = formatted.replace(",", "{COMMA}").replace(".", "{DOT}")
            formatted = (
                formatted.replace("{COMMA}", self.thousands)
                .replace("{DOT}", self.decimal)
            )
        return formatted


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

    precision: int = 1

    def __call__(self, value: object, context: FormatContext) -> FormatResult:
        if value is None or _is_nan(value):
            return ""
        try:
            number = float(value)
        except Exception:
            return str(value)
        return f"{number * 100:.{self.precision}f}%"


def _is_nan(value: object) -> bool:
    try:
        return float(value) != float(value)
    except Exception:
        return False
