"""Core plugin definitions and helpers."""
from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterable, Protocol, Sequence

from ..core.model import Cell, Row, Table
from ..style import CellStyle

__all__ = ["Plugin", "PluginBase", "map_body_cells", "merge_cell_style"]


class Plugin(Protocol):
    """Protocol implemented by render-time plugins."""

    def after_format(self, table: Table) -> Table:
        """Run after data is formatted but before theming is applied."""

    def before_render(self, table: Table) -> Table:
        """Run after theming but before HTML rendering."""


class PluginBase:
    """Base class providing no-op implementations of plugin hooks."""

    def after_format(self, table: Table) -> Table:
        return table

    def before_render(self, table: Table) -> Table:
        return table


def map_body_cells(table: Table, mapper: Callable[[Cell, int, int], Cell]) -> Table:
    """Apply ``mapper`` to every body cell in ``table``."""

    updated_rows: list[Row] = []
    changed = False
    for row_index, row in enumerate(table.body_rows):
        new_cells: list[Cell] = []
        row_changed = False
        for cell_index, cell in enumerate(row.cells):
            new_cell = mapper(cell, row_index, cell_index)
            if new_cell is not cell:
                row_changed = True
            new_cells.append(new_cell)
        if row_changed:
            changed = True
            updated_rows.append(replace(row, cells=tuple(new_cells)))
        else:
            updated_rows.append(row)
    if not changed:
        return table
    return replace(table, body_rows=tuple(updated_rows))


def merge_cell_style(cell: Cell, style: CellStyle | dict[str, str]) -> Cell:
    """Merge ``style`` into ``cell`` and return an updated cell."""

    if isinstance(style, CellStyle):
        additions = dict(style.properties)
    else:
        additions = {key.replace("_", "-"): str(value) for key, value in style.items() if value is not None}
    base = dict(cell.style.properties) if cell.style is not None else {}
    modified = False
    for key, value in additions.items():
        if base.get(key) == value:
            continue
        base[key] = value
        modified = True
    if not modified:
        return cell
    return replace(cell, style=CellStyle(base))
