"""Style model definitions used throughout richframe."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = ["BaseStyle", "CellStyle", "RowStyle", "TableStyle"]


@dataclass(frozen=True, slots=True)
class BaseStyle:
    """Immutable representation of a CSS style declaration."""

    _properties: tuple[tuple[str, str], ...]
    name: str | None = None

    def __init__(
        self,
        properties: Mapping[str, str] | None = None,
        *,
        name: str | None = None,
        **inline_properties: str,
    ) -> None:
        merged: dict[str, str] = {}
        if properties:
            merged.update(properties)
        merged.update(inline_properties)
        normalised = tuple(
            sorted(
                (self._normalise_key(key), str(value))
                for key, value in merged.items()
                if value is not None
            )
        )
        object.__setattr__(self, "_properties", normalised)
        object.__setattr__(self, "name", name)

    @property
    def properties(self) -> tuple[tuple[str, str], ...]:
        return self._properties

    def is_empty(self) -> bool:
        return not self._properties

    def css_text(self) -> str:
        return "; ".join(f"{key}: {value}" for key, value in self._properties)

    def inline_style(self) -> str:
        return "; ".join(f"{key}: {value}" for key, value in self._properties)

    @staticmethod
    def _normalise_key(key: str) -> str:
        return key.replace("_", "-").strip()


class TableStyle(BaseStyle):
    """CSS declaration applied to a table element."""


class RowStyle(BaseStyle):
    """CSS declaration applied to a table row."""


class CellStyle(BaseStyle):
    """CSS declaration applied to a table cell."""
