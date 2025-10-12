"""Rule-based conditional styling."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from ..core.model import Cell, Table
from ..style import CellStyle
from .base import PluginBase, map_body_cells, merge_cell_style

__all__ = ["conditional_format"]


class ConditionalFormatPlugin(PluginBase):
    """Fluent rule builder that maps predicates onto styles."""

    def __init__(self) -> None:
        self._rules: list[_Rule] = []

    def when(
        self,
        *,
        column: str | Sequence[str] | None = None,
        predicate: Callable[[object], bool],
    ) -> "_RuleBuilder":
        if predicate is None:
            raise ValueError("predicate must be provided")
        columns = _normalise_columns(column)
        return _RuleBuilder(self, columns, predicate)

    def before_render(self, table: Table) -> Table:
        if not self._rules:
            return table

        def apply_rules(cell: Cell, _row: int, _column: int) -> Cell:
            if cell.kind != "body":
                return cell
            updated = cell
            for rule in self._rules:
                if rule.columns and (cell.column_id not in rule.columns):
                    continue
                try:
                    matched = rule.predicate(cell.value)
                except Exception:  # pragma: no cover - defensive
                    matched = False
                if not matched:
                    continue
                updated = merge_cell_style(updated, rule.style)
            return updated

        return map_body_cells(table, apply_rules)


def conditional_format() -> ConditionalFormatPlugin:
    """Create a conditional formatting plugin."""

    return ConditionalFormatPlugin()


@dataclass(slots=True)
class _Rule:
    columns: tuple[str, ...] | None
    predicate: Callable[[object], bool]
    style: CellStyle | dict[str, str]


class _RuleBuilder:
    def __init__(
        self,
        plugin: ConditionalFormatPlugin,
        columns: tuple[str, ...] | None,
        predicate: Callable[[object], bool],
    ) -> None:
        self._plugin = plugin
        self._columns = columns
        self._predicate = predicate

    def style(
        self,
        style: CellStyle | Mapping[str, str] | None = None,
        **properties: str,
    ) -> ConditionalFormatPlugin:
        if style is None and not properties:
            raise ValueError("style or keyword properties must be provided")
        resolved = _coerce_style(style, properties)
        self._plugin._rules.append(_Rule(self._columns, self._predicate, resolved))
        return self._plugin


def _normalise_columns(column: str | Sequence[str] | None) -> tuple[str, ...] | None:
    if column is None:
        return None
    if isinstance(column, str):
        return (column,)
    return tuple(column)


def _coerce_style(
    style: CellStyle | Mapping[str, str] | None,
    properties: Mapping[str, str],
) -> CellStyle | dict[str, str]:
    if isinstance(style, CellStyle):
        base = dict(style.properties)
        for key, value in properties.items():
            if value is None:
                continue
            base[key.replace("_", "-")] = str(value)
        return CellStyle(base)
    if style is not None:
        combined = {key.replace("_", "-"): str(value) for key, value in style.items() if value is not None}
    else:
        combined = {}
    for key, value in properties.items():
        if value is None:
            continue
        combined[key.replace("_", "-")] = str(value)
    return combined
