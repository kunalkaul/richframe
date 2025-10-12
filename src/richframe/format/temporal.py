"""Date and time formatting helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .formatter import FormatContext, FormatResult

try:  # pragma: no cover - optional dependency
    from babel.dates import format_datetime
except Exception:  # pragma: no cover - fallback when babel missing
    format_datetime = None  # type: ignore

__all__ = ["DateFormatter"]


@dataclass(slots=True)
class DateFormatter:
    """Format date or datetime values."""

    pattern: str = "medium"

    def __call__(self, value: object, context: FormatContext) -> FormatResult:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return self._format_datetime(value, context)
        if isinstance(value, date):
            return self._format_date(value, context)
        return str(value)

    def _format_datetime(self, value: datetime, context: FormatContext) -> str:
        if format_datetime is None or context.locale is None:
            return value.isoformat()
        return format_datetime(value, format=self.pattern, locale=context.locale)

    def _format_date(self, value: date, context: FormatContext) -> str:
        if format_datetime is None or context.locale is None:
            return value.isoformat()
        return format_datetime(value, format=self.pattern, locale=context.locale)
