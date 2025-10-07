"""Public API surface for richframe."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any

import pandas as pd

from .core.model import Table
from .io.pandas_adapter import dataframe_to_table
from .render.html_renderer import HTMLRenderer
from .format import Formatter
from .layout import ColumnConfig
from .plugins import Plugin
from .style import RowStyle, Theme, resolve_theme

__all__ = ["to_html"]


def to_html(
    value: Table | pd.DataFrame,
    *,
    include_index: bool = True,
    caption: str | None = None,
    theme: str | Theme | None = "minimal",
    inline_styles: bool = False,
    formatters: Mapping[str, Formatter | str | None] | None = None,
    locale: str | None = None,
    column_layout: Mapping[str, ColumnConfig | Mapping[str, object] | None] | None = None,
    sticky_header: bool = False,
    zebra_striping: bool = False,
    row_predicates: Sequence[tuple[Callable[[Any, Sequence[Any]], bool], RowStyle | Mapping[str, str] | None]] | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    renderer: HTMLRenderer | None = None,
    plugins: Sequence[Plugin | None] | None = None,
) -> str:
    """Render a supported tabular structure into HTML.

    Parameters
    ----------
    value:
        Either a :class:`~richframe.core.model.Table` produced by richframe or a
        :class:`pandas.DataFrame`. DataFrames are converted using the pandas
        adapter prior to rendering.
    include_index:
        When ``True`` the DataFrame index becomes the first column in the
        rendered table. Ignored when ``value`` is already a
        :class:`~richframe.core.model.Table`. Defaults to ``True``.
    caption:
        Optional caption to embed in the table output. Overrides any caption
        present on the :class:`~richframe.core.model.Table` instance provided.
    title:
        Optional title rendered above the table caption.
    subtitle:
        Optional subtitle rendered below the title.
    theme:
        Name of a registered theme (``"minimal"``, ``"light"``, ``"dark"``) or a
        :class:`~richframe.style.theme.Theme` instance. ``None`` skips theming
        entirely. Defaults to ``"minimal"``.
    inline_styles:
        When ``True`` all CSS declarations are applied inline on the elements,
        which is useful for HTML emails or contexts where external stylesheets
        are stripped. When ``False`` the renderer emits a `<style>` block with
        hashed class names. Defaults to ``False``.
    formatters:
        Optional mapping of column identifiers to formatter names or callables.
        Formatter strings resolve to the built-in helpers (``"number"``,
        ``"currency"``, ``"percent"``, ``"date"``). Only applied when ``value``
        is a :class:`pandas.DataFrame`.
    locale:
        Optional locale string passed to locale-aware formatters. Requires the
        ``babel`` extra when used with date formatting.
    column_layout:
        Mapping of column identifiers to layout configuration. Values may be
        :class:`~richframe.layout.column.ColumnConfig` instances or dictionaries
        containing ``width``, ``align``, ``visible``, and ``sticky`` keys.
    sticky_header:
        When ``True`` the table header row remains visible while scrolling.
    zebra_striping:
        Set to ``True`` to alternate row backgrounds for readability.
    row_predicates:
        Sequence of ``(predicate, style)`` tuples applied to body rows. Each
        predicate receives ``(index, values)`` and, when true, applies the
        provided :class:`~richframe.style.model.RowStyle` (or a style mapping).
    renderer:
        Optional :class:`~richframe.render.html_renderer.HTMLRenderer`
        instance. Supply this when you need to reuse a configured renderer or
        template. One will be created automatically when omitted.
    plugins:
        Optional sequence of plugin instances executed after formatting
        (pre-theme) and immediately before rendering. Use this to add color
        scales, data bars, icon sets, or custom conditional styling.

    Returns
    -------
    str
        A complete HTML snippet containing the table markup ready for
        insertion into notebook cells, web responses, or other HTML-aware
        surfaces.
    """

    table = _coerce_to_table(
        value,
        include_index=include_index,
        caption=caption,
        formatters=formatters,
        locale=locale,
        column_layout=column_layout,
        sticky_header=sticky_header,
        zebra_striping=zebra_striping,
        row_predicates=row_predicates,
        title=title,
        subtitle=subtitle,
    )
    table = _run_plugins(table, plugins, stage="after_format")
    resolved_theme = resolve_theme(theme)
    if resolved_theme is not None:
        table = resolved_theme.apply(table)
    table = _run_plugins(table, plugins, stage="before_render")
    active_renderer = renderer or HTMLRenderer(inline_styles=inline_styles)
    return active_renderer.render(table)


def _run_plugins(table: Table, plugins: Sequence[Plugin | None] | None, *, stage: str) -> Table:
    if not plugins:
        return table
    current = table
    for plugin in plugins:
        if plugin is None:
            continue
        hook = getattr(plugin, stage, None)
        if hook is None:
            continue
        result = hook(current)
        if not isinstance(result, Table):  # pragma: no cover - defensive
            raise TypeError(f"Plugin hook '{stage}' must return a Table")
        current = result
    return current


def _coerce_to_table(
    value: Table | pd.DataFrame,
    *,
    include_index: bool,
    caption: str | None,
    formatters: Mapping[str, Formatter | str | None] | None,
    locale: str | None,
    column_layout: Mapping[str, ColumnConfig | Mapping[str, object] | None] | None,
    sticky_header: bool,
    zebra_striping: bool,
    row_predicates: Sequence[tuple[Callable[[Any, Sequence[Any]], bool], RowStyle | Mapping[str, str] | None]] | None,
    title: str | None,
    subtitle: str | None,
) -> Table:
    if isinstance(value, Table):
        if caption is not None and value.caption != caption:
            value = replace(value, caption=caption)
        if title is not None or subtitle is not None:
            metadata = dict(value.metadata)
            if title is not None:
                metadata["title"] = title
            if subtitle is not None:
                metadata["subtitle"] = subtitle
            value = replace(value, metadata=metadata)
        if any([formatters, locale, column_layout, sticky_header, zebra_striping, row_predicates]):
            raise ValueError(
                "Formatters, layout, and predicate options are only supported for DataFrame inputs"
            )
        return value
    if isinstance(value, pd.DataFrame):
        return dataframe_to_table(
            value,
            include_index=include_index,
            caption=caption,
            formatters=formatters,
            locale=locale,
            column_layout=column_layout,
            sticky_header=sticky_header,
            zebra_striping=zebra_striping,
            row_predicates=row_predicates,
            title=title,
            subtitle=subtitle,
        )
    raise TypeError("Unsupported value passed to to_html")
