"""Built-in themes for richframe tables."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Iterable

from ..core.model import Cell, Row, Table
from .model import CellStyle, RowStyle, TableStyle

__all__ = ["Theme", "get_theme", "list_themes", "resolve_theme"]


@dataclass(frozen=True, slots=True)
class Theme:
    """Collection of default styles applied to a table."""

    name: str
    table_style: TableStyle | None = None
    header_row_style: RowStyle | None = None
    header_cell_style: CellStyle | None = None
    body_row_style: RowStyle | None = None
    body_cell_style: CellStyle | None = None

    def apply(self, table: Table) -> Table:
        table_style = table.table_style or self.table_style
        header_rows = tuple(
            self._apply_row(
                row,
                default_row_style=self.header_row_style,
                default_cell_style=self.header_cell_style,
            )
            for row in table.header_rows
        )
        body_rows = tuple(
            self._apply_row(
                row,
                default_row_style=self.body_row_style,
                default_cell_style=self.body_cell_style,
            )
            for row in table.body_rows
        )
        return replace(
            table,
            table_style=table_style,
            header_rows=header_rows,
            body_rows=body_rows,
        )

    @staticmethod
    def _apply_row(
        row: Row,
        *,
        default_row_style: RowStyle | None,
        default_cell_style: CellStyle | None,
    ) -> Row:
        applied_row_style = row.style or default_row_style
        applied_cells = tuple(
            Theme._apply_cell(cell, default_cell_style=default_cell_style)
            for cell in row.cells
        )
        return replace(row, style=applied_row_style, cells=applied_cells)

    @staticmethod
    def _apply_cell(
        cell: Cell,
        *,
        default_cell_style: CellStyle | None,
    ) -> Cell:
        if cell.style is not None or default_cell_style is None:
            return cell
        return replace(cell, style=default_cell_style)


_LIGHT_THEME = Theme(
    name="light",
    table_style=TableStyle(
        border_collapse="collapse",
        border="1px solid #d0d7de",
        background_color="#ffffff",
        color="#1f2328",
        font_family="'Segoe UI', sans-serif",
        font_size="14px",
    ),
    header_cell_style=CellStyle(
        background_color="#f6f8fa",
        font_weight="600",
        text_align="left",
        padding="8px 12px",
        border="1px solid #d0d7de",
        color="#1f2328",
    ),
    body_cell_style=CellStyle(
        padding="8px 12px",
        border="1px solid #d0d7de",
        color="#1f2328",
    ),
)

_MINIMAL_THEME = Theme(name="minimal")

_DARK_THEME = Theme(
    name="dark",
    table_style=TableStyle(
        border_collapse="collapse",
        border="1px solid #374151",
        background_color="#1f2937",
        color="#f9fafb",
        font_family="'Source Sans Pro', sans-serif",
        font_size="14px",
    ),
    header_cell_style=CellStyle(
        background_color="#111827",
        color="#f9fafb",
        font_weight="600",
        text_align="left",
        padding="8px 12px",
        border="1px solid #374151",
    ),
    body_cell_style=CellStyle(
        padding="8px 12px",
        border="1px solid #374151",
    ),
)

_THEMES: Dict[str, Theme] = {
    theme.name: theme
    for theme in (_LIGHT_THEME, _MINIMAL_THEME, _DARK_THEME)
}


def get_theme(name: str) -> Theme:
    try:
        return _THEMES[name]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise KeyError(f"Unknown theme '{name}'. Available: {', '.join(sorted(_THEMES))}") from exc


def list_themes() -> Iterable[str]:
    return sorted(_THEMES)


def resolve_theme(theme: str | Theme | None) -> Theme | None:
    if theme is None:
        return None
    if isinstance(theme, Theme):
        return theme
    if isinstance(theme, str):
        return get_theme(theme)
    raise TypeError("Theme must be provided as a string name or Theme instance")
