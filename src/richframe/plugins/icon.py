"""Icon-based conditional formatting plugins."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Iterable, Sequence

from ..core.model import Cell, Table
from ..style import CellStyle
from .base import PluginBase, map_body_cells, merge_cell_style

__all__ = ["IconRule", "IconSetPlugin"]


@dataclass(frozen=True, slots=True)
class IconRule:
    """Rule mapping a predicate to an icon and optional style."""

    predicate: Callable[[object], bool]
    icon: str
    style: CellStyle | dict[str, str] | None = None


class IconSetPlugin(PluginBase):
    """Prefix or suffix cell text with icons based on rule matches."""

    def __init__(
        self,
        columns: str | Sequence[str],
        rules: Iterable[IconRule],
        *,
        position: str = "prefix",
        separator: str = " ",
    ) -> None:
        self._columns = tuple(columns) if isinstance(columns, Sequence) and not isinstance(columns, str) else (columns,)
        self._rules = tuple(rules)
        if position not in {"prefix", "suffix"}:
            raise ValueError("position must be 'prefix' or 'suffix'")
        self._position = position
        self._separator = separator

    def before_render(self, table: Table) -> Table:
        if not self._rules:
            return table

        def decorate(cell: Cell, _row: int, _column: int) -> Cell:
            if cell.column_id not in self._columns or cell.kind != "body":
                return cell
            for rule in self._rules:
                try:
                    matched = rule.predicate(cell.value)
                except Exception:  # pragma: no cover - defensive
                    matched = False
                if not matched:
                    continue
                icon = rule.icon
                if not icon:
                    continue
                if self._position == "prefix":
                    if cell.text.startswith(icon):
                        updated_text = cell.text
                    else:
                        updated_text = f"{icon}{self._separator}{cell.text}".strip()
                else:
                    if cell.text.endswith(icon):
                        updated_text = cell.text
                    else:
                        updated_text = f"{cell.text}{self._separator}{icon}".strip()
                updated = replace(cell, text=updated_text)
                if rule.style:
                    updated = merge_cell_style(updated, rule.style)
                return updated
            return cell

        return map_body_cells(table, decorate)
