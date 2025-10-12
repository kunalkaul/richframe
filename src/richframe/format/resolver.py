"""Formatter resolution helpers."""
from __future__ import annotations

from typing import Callable

from .formatter import Formatter
from .numbers import CurrencyFormatter, NumberFormatter, PercentageFormatter
from .temporal import DateFormatter

__all__ = ["resolve_formatter"]


def resolve_formatter(value: Formatter | str | Callable[..., Formatter]) -> Formatter:
    if callable(value) and not isinstance(value, str):
        # Formatter instances are callable; return as-is.
        return value  # type: ignore[return-value]
    mapping: dict[str, Formatter] = {
        "number": NumberFormatter(),
        "currency": CurrencyFormatter(),
        "percent": PercentageFormatter(),
        "percentage": PercentageFormatter(),
        "date": DateFormatter(),
    }
    if isinstance(value, str):
        key = value.lower()
        try:
            return mapping[key]
        except KeyError as exc:  # pragma: no cover - defensive path
            raise KeyError(
                f"Unknown formatter '{value}'. Available keys: {', '.join(sorted(mapping))}"
            ) from exc
    raise TypeError("Formatter must be a callable or a known formatter name")
