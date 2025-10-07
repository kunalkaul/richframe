"""Color scale plugin implementations."""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Sequence

from ..core.model import Cell, Table
from ..style import CellStyle
from .base import PluginBase, map_body_cells, merge_cell_style

__all__ = ["ColorScalePlugin"]


class ColorScalePlugin(PluginBase):
    """Apply a background color scale to numeric columns."""

    def __init__(
        self,
        columns: str | Sequence[str],
        *,
        palette: tuple[str, str] = ("#f1f5f9", "#1d4ed8"),
        text_contrast: bool = True,
        null_color: str | None = "#f8fafc",
    ) -> None:
        self._columns = tuple(columns) if isinstance(columns, Sequence) and not isinstance(columns, str) else (columns,)
        self._start_color = palette[0]
        self._end_color = palette[1]
        self._text_contrast = text_contrast
        self._null_color = null_color

    def before_render(self, table: Table) -> Table:
        numeric_values = _collect_numeric_values(table, self._columns)
        if not numeric_values:
            return table
        minimum = min(numeric_values)
        maximum = max(numeric_values)
        if minimum == maximum:
            maximum = minimum + 1.0

        def apply_scale(cell: Cell, _row: int, _column: int) -> Cell:
            if cell.column_id not in self._columns or cell.kind != "body":
                return cell
            value = _coerce_float(cell.value)
            if value is None:
                if self._null_color is None:
                    return cell
                return merge_cell_style(cell, {"background-color": self._null_color})
            fraction = (value - minimum) / (maximum - minimum)
            background = _interpolate_hex(self._start_color, self._end_color, fraction)
            updated = merge_cell_style(cell, {"background-color": background})
            if not self._text_contrast:
                return updated
            if _relative_luminance(background) < 0.4:
                return merge_cell_style(updated, {"color": "#f8fafc"})
            return updated

        return map_body_cells(table, apply_scale)


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


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:  # NaN check
        return None
    return numeric


def _parse_hex(color: str) -> tuple[int, int, int]:
    clean = color.lstrip("#")
    if len(clean) == 3:
        clean = "".join(ch * 2 for ch in clean)
    if len(clean) != 6:
        raise ValueError(f"Invalid hex color '{color}'")
    r = int(clean[0:2], 16)
    g = int(clean[2:4], 16)
    b = int(clean[4:6], 16)
    return r, g, b


def _format_hex(rgb: tuple[float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, round(rgb[0]))),
        max(0, min(255, round(rgb[1]))),
        max(0, min(255, round(rgb[2]))),
    )


def _interpolate_hex(start: str, end: str, fraction: float) -> str:
    fraction = max(0.0, min(1.0, fraction))
    sr, sg, sb = _parse_hex(start)
    er, eg, eb = _parse_hex(end)
    rgb = (
        sr + (er - sr) * fraction,
        sg + (eg - sg) * fraction,
        sb + (eb - sb) * fraction,
    )
    return _format_hex(rgb)


def _relative_luminance(color: str) -> float:
    r, g, b = _parse_hex(color)
    return 0.2126 * (r / 255.0) + 0.7152 * (g / 255.0) + 0.0722 * (b / 255.0)
