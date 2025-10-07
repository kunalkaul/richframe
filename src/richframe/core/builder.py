"""Utilities for constructing :mod:`richframe` table models."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, Dict, List, Mapping

from .model import Cell, Row, Table, CellKind
from ..format import FormatContext, Formatter, FormatRegistry, default_formatters
from ..layout import ColumnConfig, ColumnLayout, LayoutOptions

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from ..style import CellStyle, RowStyle, TableStyle


class TableBuilder:
    """Incrementally build a :class:`~richframe.core.model.Table`."""

    def __init__(
        self,
        columns: Sequence[str],
        *,
        caption: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        self._columns: List[str] = [str(column) for column in columns]
        self._caption = caption
        self._metadata: Dict[str, Any] = dict(metadata or {})
        self._header_rows: List[Row] = []
        self._body_rows: List[Row] = []
        self._table_style: "TableStyle | None" = None
        self._locale: str | None = None
        self._format_registry = FormatRegistry()
        for column_id, formatter in default_formatters().items():
            self._format_registry.register(column_id, formatter)
        self._column_layout = ColumnLayout()
        self._layout_options: LayoutOptions | None = None
        self._row_predicates: list[tuple[Callable[[Any, Sequence[Any]], bool], "RowStyle | None"]] = []

    @property
    def columns(self) -> Sequence[str]:
        return tuple(self._columns)

    def set_caption(self, caption: str | None) -> None:
        self._caption = caption

    def set_table_style(self, style: "TableStyle | None") -> None:
        self._table_style = style

    def set_locale(self, locale: str | None) -> None:
        self._locale = locale

    def set_formatter(self, column_id: str, formatter: Formatter) -> None:
        self._format_registry.register(str(column_id), formatter)

    def set_formatters(self, formatters: Mapping[str, Formatter]) -> None:
        for column_id, formatter in formatters.items():
            self.set_formatter(column_id, formatter)

    def has_formatter(self, column_id: str) -> bool:
        return self._format_registry.get(column_id) is not None

    def set_column_config(self, config: ColumnConfig) -> None:
        self._column_layout.set(config)

    def set_layout_options(
        self,
        *,
        sticky_header: bool | None = None,
        zebra_striping: bool | None = None,
    ) -> None:
        current = self._layout_options or LayoutOptions.empty()
        self._layout_options = LayoutOptions(
            columns=self._column_layout,
            sticky_header=current.sticky_header if sticky_header is None else sticky_header,
            zebra_striping=current.zebra_striping if zebra_striping is None else zebra_striping,
        )

    def add_row_predicate(
        self,
        predicate: Callable[[Any, Sequence[Any]], bool],
        *,
        row_style: "RowStyle | None" = None,
    ) -> None:
        self._row_predicates.append((predicate, row_style))

    def add_header_row(
        self,
        values: Sequence[Any] | Iterable[Any],
        *,
        row_style: "RowStyle | None" = None,
        cell_style: "CellStyle | None" = None,
    ) -> None:
        row = self._build_row(
            values,
            kind="header",
            row_style=row_style,
            cell_style=cell_style,
        )
        self._header_rows.append(row)

    def add_body_row(
        self,
        values: Sequence[Any] | Iterable[Any],
        *,
        index: Any | None = None,
        row_style: "RowStyle | None" = None,
        cell_style: "CellStyle | None" = None,
    ) -> None:
        resolved = list(values)
        if len(resolved) != len(self._columns):
            raise ValueError(
                "Row width does not match column definition: "
                f"expected {len(self._columns)}, received {len(resolved)}"
            )
        effective_row_style = row_style or self._resolve_row_style(index, resolved)
        row = self._build_row(
            resolved,
            kind="body",
            index=index,
            row_style=effective_row_style,
            cell_style=cell_style,
        )
        self._body_rows.append(row)

    def build(self) -> Table:
        if not self._header_rows:
            # ensure there is always at least one header row
            self.add_header_row(self._columns)
        return Table(
            columns=tuple(self._columns),
            header_rows=tuple(self._header_rows),
            body_rows=tuple(self._body_rows),
            caption=self._caption,
            metadata=dict(self._metadata),
            table_style=self._table_style,
            layout=self._layout_options or LayoutOptions(columns=self._column_layout),
        )

    def _build_row(
        self,
        values: Sequence[Any] | Iterable[Any],
        *,
        kind: CellKind,
        index: Any | None = None,
        row_style: "RowStyle | None" = None,
        cell_style: "CellStyle | None" = None,
    ) -> Row:
        resolved = list(values)
        if len(resolved) != len(self._columns):
            raise ValueError(
                "Row width does not match column definition: "
                f"expected {len(self._columns)}, received {len(resolved)}"
            )
        context = FormatContext(row_index=index, locale=self._locale)
        cells = []
        for column_id, value in zip(self._columns, resolved, strict=True):
            formatter = self._format_registry.get(column_id) if kind == "body" else None
            text = _coerce_text(value, formatter, column_id, context)
            cells.append(
                self._make_cell(
                    value,
                    column_id=column_id,
                    kind=kind,
                    cell_style=cell_style,
                    text=text,
                )
            )
        return Row(tuple(cells), kind=kind, index=index, style=row_style)

    def _resolve_row_style(self, index: Any, values: Sequence[Any]) -> "RowStyle | None":
        for predicate, style in self._row_predicates:
            try:
                if predicate(index, values):
                    return style
            except Exception:  # pragma: no cover - defensive guard
                continue
        return None

    @staticmethod
    def _make_cell(
        value: Any,
        *,
        column_id: str,
        kind: CellKind,
        cell_style: "CellStyle | None",
        text: str,
        cell_id: str | None = None,
        scope: str | None = None,
        headers: tuple[str, ...] | None = None,
    ) -> Cell:
        return Cell(
            value=value,
            text=text,
            column_id=column_id,
            kind=kind,
            style=cell_style,
            id=cell_id,
            scope=scope,
            headers=headers,
        )


def _coerce_text(
    value: Any,
    formatter: Formatter | None,
    column_id: str,
    context: FormatContext,
) -> str:
    if formatter is not None:
        context_with_column = FormatContext(
            column_id=column_id,
            row_index=context.row_index,
            locale=context.locale,
        )
        try:
            return formatter(value, context_with_column)
        except Exception:  # pragma: no cover - formatter errors fall back
            pass
    if _is_missing(value):
        return ""
    return str(value)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return value != value
    except Exception:  # noqa: BLE001 - fall back when comparison fails
        return False


__all__ = ["TableBuilder"]
