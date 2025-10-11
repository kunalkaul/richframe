"""Adapters for turning pandas objects into richframe tables."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pandas as pd

from ..core.builder import TableBuilder
from ..core.model import Table
from ..format import Formatter, NumberFormatter, DateFormatter, resolve_formatter
from ..layout import ColumnConfig, FilterConfig, SortConfig
from ..merge import apply_merges
from ..style import RowStyle
from pandas.api import types as pd_types

__all__ = ["dataframe_to_table"]


def dataframe_to_table(
    frame: pd.DataFrame,
    *,
    include_index: bool = True,
    caption: str | None = None,
    formatters: Mapping[str, Formatter | str | None] | None = None,
    locale: str | None = None,
    column_layout: Mapping[str, ColumnConfig | Mapping[str, object] | None] | None = None,
    sticky_header: bool = False,
    zebra_striping: bool = False,
    row_predicates: Sequence[tuple[Callable[[Any, Sequence[Any]], bool], RowStyle | Mapping[str, str] | None]] | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    filters: Sequence[FilterConfig] | None = None,
    sorts: Sequence[SortConfig] | None = None,
    interactive_controls: bool = False,
    resizable_columns: bool = False,
) -> Table:
    """Convert a :class:`pandas.DataFrame` into a :class:`~richframe.core.model.Table`.

    Parameters
    ----------
    frame:
        Source DataFrame.
    include_index:
        When ``True`` the DataFrame index becomes the first column. Defaults to ``True``.
    caption:
        Optional table caption to propagate to the renderer.
    """

    working_frame = frame
    if filters:
        working_frame = _apply_filters(working_frame, filters)
    if sorts:
        working_frame = _apply_sorts(working_frame, sorts)

    index_columns: list[str] = _build_index_columns(working_frame.index) if include_index else []
    data_columns, column_levels = _build_column_levels(working_frame.columns)
    column_ids = index_columns + data_columns
    metadata: dict[str, Any] = {}
    if title is not None:
        metadata["title"] = title
    if subtitle is not None:
        metadata["subtitle"] = subtitle
    if filters:
        metadata["filters"] = [config.to_dict() for config in filters]
    if sorts:
        metadata["sorts"] = [config.to_dict() for config in sorts]
    if interactive_controls:
        metadata["interactive_controls"] = True
    if resizable_columns:
        metadata["resizable_columns"] = True
    if index_columns:
        metadata["index_columns"] = list(index_columns)
    if len(column_levels) > 1:
        metadata["column_levels"] = column_levels
    builder = TableBuilder(
        column_ids,
        caption=caption,
        metadata=metadata or None,
    )
    if locale is not None:
        builder.set_locale(locale)
    if formatters:
        resolved: dict[str, Formatter] = {}
        for column, formatter in formatters.items():
            if formatter is None:
                continue
            resolved[str(column)] = resolve_formatter(formatter)
        builder.set_formatters(resolved)
    _apply_automatic_formatters(builder, working_frame, include_index=include_index, index_columns=index_columns)
    if column_layout:
        _apply_column_layout(builder, column_layout)
    if sticky_header or zebra_striping:
        builder.set_layout_options(
            sticky_header=sticky_header,
            zebra_striping=zebra_striping,
        )
    if row_predicates:
        for predicate, style in row_predicates:
            builder.add_row_predicate(predicate, row_style=_coerce_row_style(style))

    for header_row in _compose_header_rows(index_columns, column_levels):
        builder.add_header_row(header_row)

    if include_index:
        index_levels = working_frame.index.nlevels if isinstance(working_frame.index, pd.MultiIndex) else 1
        for row in working_frame.itertuples(index=True, name=None):
            raw_index, *values = row
            index_values = [raw_index] if index_levels == 1 else list(raw_index)
            builder.add_body_row([*index_values, *values], index=raw_index)
    else:
        for row in working_frame.itertuples(index=False, name=None):
            builder.add_body_row(list(row))

    table = builder.build()
    return apply_merges(table, index_columns=index_columns)


def _apply_filters(frame: pd.DataFrame, filters: Sequence[FilterConfig]) -> pd.DataFrame:
    if not filters:
        return frame
    mask = pd.Series(True, index=frame.index)
    current = frame
    for config in filters:
        if config.axis == "column":
            column = _resolve_column_label(current.columns, config.key)
            series = current[column]
        else:
            series = _series_from_index(current, config.key)
        column_mask = _mask_from_series(series, config)
        mask = mask & column_mask
    return frame.loc[mask]


def _apply_sorts(frame: pd.DataFrame, sorts: Sequence[SortConfig]) -> pd.DataFrame:
    if not sorts:
        return frame
    result = frame
    column_sorts = [config for config in sorts if config.axis == "column"]
    index_sorts = [config for config in sorts if config.axis == "index"]

    for config in reversed(column_sorts):
        column = _resolve_column_label(result.columns, config.key)
        result = result.sort_values(
            by=column,
            ascending=config.ascending,
            kind="mergesort",
            na_position=config.na_position,
        )

    for config in reversed(index_sorts):
        if isinstance(result.index, pd.MultiIndex):
            level = _resolve_index_selector(result.index, config.key)
            result = result.sort_index(
                level=level,
                ascending=config.ascending,
                sort_remaining=False,
                na_position=config.na_position,
            )
        else:
            _validate_single_index_key(result.index, config.key)
            result = result.sort_index(
                ascending=config.ascending,
                na_position=config.na_position,
            )
    return result


def _resolve_column_label(columns: pd.Index, key: str):
    if key in columns:
        return key
    matches = [column for column in columns if str(column) == key]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"Column '{key}' not found in DataFrame")


def _resolve_index_selector(index: pd.MultiIndex, key: str) -> int | str:
    names = list(index.names)
    for level, name in enumerate(names):
        formatted = _format_index_label(name)
        if key in {formatted, str(name), f"level_{level}"}:
            return name if name is not None else level
    try:
        numeric = int(key)
    except (TypeError, ValueError):
        pass
    else:
        if 0 <= numeric < index.nlevels:
            return numeric
    raise KeyError(f"Index level '{key}' not found in DataFrame index")


def _validate_single_index_key(index: pd.Index, key: str) -> None:
    normalized = str(key)
    candidate_labels = {
        _format_index_label(index.name),
        str(index.name) if index.name is not None else "None",
        "index",
        "row",
        "level_0",
        "__index__",
    }
    if normalized in candidate_labels:
        return
    raise KeyError(f"Index key '{key}' not valid for single-level index")


def _series_from_index(frame: pd.DataFrame, key: str) -> pd.Series:
    index = frame.index
    if isinstance(index, pd.MultiIndex):
        selector = _resolve_index_selector(index, key)
        values = index.get_level_values(selector)
        return pd.Series(values, index=index, name=str(key))
    _validate_single_index_key(index, key)
    return pd.Series(index, index=index, name=str(key))


def _mask_from_series(series: pd.Series, config: FilterConfig) -> pd.Series:
    op = config.operator
    value = config.value
    if op == "contains":
        mask = series.astype(str).str.contains(str(value), na=False)
    elif op == "in":
        mask = series.isin(config.value)
    elif op == "between":
        mask = series.between(config.value, config.upper, inclusive="both")
    elif op == "eq":
        mask = series.isna() if value is None else series.eq(value)
    elif op == "ne":
        mask = series.notna() if value is None else series.ne(value)
    elif op == "gt":
        mask = series.gt(value)
    elif op == "ge":
        mask = series.ge(value)
    elif op == "lt":
        mask = series.lt(value)
    elif op == "le":
        mask = series.le(value)
    else:  # pragma: no cover - should be prevented by validation
        raise ValueError(f"Unsupported operator '{config.operator}'")
    return mask.fillna(False)


def _build_index_columns(index: pd.Index) -> list[str]:
    if isinstance(index, pd.MultiIndex):
        labels: list[str] = []
        for level, name in enumerate(index.names):
            label = _format_index_label(name)
            if not label:
                label = f"level_{level}"
            labels.append(label)
        return labels
    return [_format_index_label(index.name)]


def _build_column_levels(columns: pd.Index) -> tuple[list[str], list[list[str]]]:
    if isinstance(columns, pd.MultiIndex):
        identifiers = [str(column) for column in columns]
        levels = []
        for level in range(columns.nlevels):
            values = [_format_header_value(value) for value in columns.get_level_values(level)]
            levels.append(values)
        return identifiers, levels
    labels = [_format_header_value(column) for column in columns]
    return labels, [labels or []]


def _compose_header_rows(
    index_columns: Sequence[str],
    column_levels: Sequence[Sequence[str]],
) -> list[list[str]]:
    if not column_levels:
        column_levels = [[]]
    row_count = len(column_levels)
    header_rows: list[list[str]] = []
    for row_index in range(row_count):
        row: list[str] = []
        for label in index_columns:
            if row_count == 1 or row_index == row_count - 1:
                row.append(label)
            else:
                row.append("")
        row.extend(column_levels[row_index])
        header_rows.append(row)
    return header_rows


def _format_index_label(label: Any) -> str:
    if label is None:
        return ""
    return str(label)


def _format_header_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _apply_automatic_formatters(
    builder: TableBuilder,
    frame: pd.DataFrame,
    *,
    include_index: bool,
    index_columns: Sequence[str],
) -> None:
    for column in frame.columns:
        column_id = str(column)
        if builder.has_formatter(column_id):
            continue
        if pd_types.is_datetime64_any_dtype(frame[column]):
            builder.set_formatter(column_id, DateFormatter())
        elif pd_types.is_numeric_dtype(frame[column]):
            builder.set_formatter(column_id, NumberFormatter())

    if include_index:
        if isinstance(frame.index, pd.MultiIndex):
            for level, label in enumerate(index_columns):
                if builder.has_formatter(label):
                    continue
                level_values = frame.index.get_level_values(level)
                if pd_types.is_datetime64_any_dtype(level_values):
                    builder.set_formatter(label, DateFormatter())
                elif pd_types.is_numeric_dtype(level_values):
                    builder.set_formatter(label, NumberFormatter(precision=0))
        else:
            index_label = index_columns[0] if index_columns else _format_index_label(frame.index.name)
            if builder.has_formatter(index_label):
                return
            if pd_types.is_datetime64_any_dtype(frame.index):
                builder.set_formatter(index_label, DateFormatter())
            elif pd_types.is_numeric_dtype(frame.index):
                builder.set_formatter(index_label, NumberFormatter(precision=0))


def _apply_column_layout(
    builder: TableBuilder,
    column_layout: Mapping[str, ColumnConfig | Mapping[str, object] | None],
) -> None:
    for column_id, config in column_layout.items():
        if config is None:
            continue
        if isinstance(config, ColumnConfig):
            builder.set_column_config(config)
        elif isinstance(config, Mapping):
            builder.set_column_config(ColumnConfig(id=str(column_id), **config))
        else:  # pragma: no cover - defensive path
            raise TypeError("Column layout entries must be ColumnConfig or mapping")


def _coerce_row_style(style: RowStyle | Mapping[str, str] | None) -> RowStyle | None:
    if style is None:
        return None
    if isinstance(style, RowStyle):
        return style
    if isinstance(style, Mapping):
        return RowStyle(style)
    raise TypeError("Row predicate style must be RowStyle or mapping")
