"""In-cell bar visualisations."""
from __future__ import annotations

from typing import Iterable, Sequence

from ..core.model import Cell, Table
from .base import PluginBase, map_body_cells, merge_cell_style
from .color import _coerce_float

__all__ = ["DataBarPlugin"]


class DataBarPlugin(PluginBase):
    """Render horizontal bars inside numeric cells."""

    def __init__(
        self,
        columns: str | Sequence[str],
        *,
        bar_color: str = "#2563eb",
        base_color: str = "rgba(148, 163, 184, 0.16)",
        axis_color: str | None = "rgba(148, 163, 184, 0.8)",
    ) -> None:
        self._columns = tuple(columns) if isinstance(columns, Sequence) and not isinstance(columns, str) else (columns,)
        self._bar_color = bar_color
        self._base_color = base_color
        self._axis_color = axis_color

    def before_render(self, table: Table) -> Table:
        numeric_values = _collect_numeric_values(table, self._columns)
        if not numeric_values:
            return table
        minimum = min(numeric_values)
        maximum = max(numeric_values)
        span = maximum - minimum or 1.0
        baseline = 0.0
        if minimum > 0:
            baseline = minimum
        elif maximum < 0:
            baseline = maximum

        def decorate(cell: Cell, _row: int, _column: int) -> Cell:
            if cell.column_id not in self._columns or cell.kind != "body":
                return cell
            numeric = _coerce_float(cell.value)
            if numeric is None:
                return cell
            fraction = (numeric - minimum) / span
            width = max(0.0, min(1.0, fraction)) * 100.0
            background = (
                f"linear-gradient(90deg, {self._bar_color} {width:.2f}%, {self._base_color} {width:.2f}%)"
            )
            updated = merge_cell_style(
                cell,
                {
                    "background-image": background,
                    "background-size": "100% 100%",
                    "background-repeat": "no-repeat",
                    "font-variant-numeric": "tabular-nums",
                },
            )
            if self._axis_color is not None and baseline > minimum:
                position = (baseline - minimum) / span * 100.0
                axis_style = {
                    "box-shadow": f"inset {position:.2f}% 0 0 0 {self._axis_color}",
                }
                updated = merge_cell_style(updated, axis_style)
            return updated

        return map_body_cells(table, decorate)


def _collect_numeric_values(table: Table, columns: Iterable[str]) -> list[float]:
    targets = set(columns)
    values: list[float] = []
    for row in table.body_rows:
        for cell in row.cells:
            if cell.kind != "body" or cell.column_id not in targets:
                continue
            numeric = _coerce_float(cell.value)
            if numeric is not None:
                values.append(numeric)
    return values
