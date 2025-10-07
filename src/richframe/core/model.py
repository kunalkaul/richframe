"""Core table data structures for richframe."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Tuple

CellKind = Literal["header", "body"]
RowKind = Literal["header", "body"]

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from ..layout import LayoutOptions
    from ..style import CellStyle, RowStyle, TableStyle


@dataclass(slots=True)
class Cell:
    """A single table cell."""

    value: Any
    text: str
    kind: CellKind = "body"
    column_id: str | None = None
    colspan: int = 1
    rowspan: int = 1
    style: "CellStyle | None" = None
    id: str | None = None
    scope: str | None = None
    headers: Tuple[str, ...] | None = None


@dataclass(slots=True)
class Row:
    """A table row containing one or more cells."""

    cells: Tuple[Cell, ...]
    kind: RowKind = "body"
    index: Any | None = None
    style: "RowStyle | None" = None

    def __post_init__(self) -> None:
        self.cells = tuple(self.cells)


@dataclass(slots=True)
class Table:
    """Representation of a logical table before rendering."""

    columns: Tuple[str, ...]
    header_rows: Tuple[Row, ...]
    body_rows: Tuple[Row, ...]
    caption: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    table_style: "TableStyle | None" = None
    layout: "LayoutOptions | None" = None

    def __post_init__(self) -> None:
        self.columns = tuple(self.columns)
        self.header_rows = tuple(self.header_rows)
        self.body_rows = tuple(self.body_rows)

    @property
    def column_count(self) -> int:
        """Return the number of logical columns the table has."""

        return len(self.columns)

    def is_empty(self) -> bool:
        """Return True when there are no body rows to display."""

        return len(self.body_rows) == 0


__all__ = ["Cell", "Row", "Table", "CellKind", "RowKind"]
