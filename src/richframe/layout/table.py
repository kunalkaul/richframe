"""Table-level layout options."""
from __future__ import annotations

from dataclasses import dataclass

from .column import ColumnLayout

__all__ = ["LayoutOptions"]


@dataclass(frozen=True, slots=True)
class LayoutOptions:
    """Layout configuration applied across a table."""

    columns: ColumnLayout
    sticky_header: bool = False
    zebra_striping: bool = False

    @classmethod
    def empty(cls) -> "LayoutOptions":
        return cls(columns=ColumnLayout())
