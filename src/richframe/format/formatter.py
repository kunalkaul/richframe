"""Core formatting abstractions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

FormatResult = str
Formatter = Callable[[Any, "FormatContext"], FormatResult]


@dataclass(slots=True, frozen=True)
class FormatContext:
    """Context passed to formatters to supply metadata."""

    column_id: str | None = None
    row_index: Any | None = None
    locale: str | None = None


class FormatRegistry:
    """Register and resolve formatters for columns."""

    def __init__(self) -> None:
        self._column_formatters: dict[str, Formatter] = {}

    def register(self, column_id: str, formatter: Formatter) -> None:
        self._column_formatters[column_id] = formatter

    def get(self, column_id: str) -> Formatter | None:
        return self._column_formatters.get(column_id)

    def items(self) -> Iterable[tuple[str, Formatter]]:
        return self._column_formatters.items()


def default_formatters() -> dict[str, Formatter]:
    return {}
