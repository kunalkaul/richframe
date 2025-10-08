"""HTML rendering for richframe tables."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Iterable, Sequence

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from ..core.model import Cell, Row, Table
from ..layout import ColumnConfig, LayoutOptions
from ..style import StyleRegistry

__all__ = ["HTMLRenderer"]

_BASE_STYLES = """\
.richframe-container {
  position: relative;
  max-width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.richframe-table {
  width: min(100%, max-content);
  border-collapse: separate;
  border-spacing: 0;
}
.richframe-table--sticky-header thead th {
  position: sticky;
  top: 0;
  z-index: 3;
}
.richframe-cell--sticky {
  box-shadow: 1px 0 0 rgba(17, 24, 39, 0.08);
}
.richframe-row--zebra:nth-child(even) {
  background-color: inherit;
}
"""

_CONTAINER_STYLE = (
    "max-width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; position: relative;"
)
_DEFAULT_STICKY_WIDTH = 120.0


@dataclass(slots=True)
class RenderedCell:
    text: str
    colspan: int
    rowspan: int
    class_attr: str
    style_attr: str | None
    tag: str
    scope_attr: str | None
    headers_attr: str | None
    id_attr: str | None


@dataclass(slots=True)
class RenderedRow:
    cells: tuple[RenderedCell, ...]
    class_attr: str
    style_attr: str | None


@dataclass(slots=True)
class RenderedTable:
    caption: str | None
    header_rows: tuple[RenderedRow, ...]
    body_rows: tuple[RenderedRow, ...]
    class_attr: str
    style_attr: str | None
    layout: LayoutOptions
    title: str | None
    subtitle: str | None


class HTMLRenderer:
    """Render :class:`~richframe.core.model.Table` instances to HTML."""

    def __init__(
        self,
        *,
        template_name: str = "table.html.j2",
        inline_styles: bool = False,
    ) -> None:
        self._template = self._load_template(template_name)
        self._inline_styles = inline_styles

    def render(self, table: Table) -> str:
        registry = StyleRegistry()
        rendered_table = self._materialize_table(table, registry)
        stylesheet = None if self._inline_styles else self._compose_stylesheet(registry)
        return self._template.render(
            table=rendered_table,
            container_style=_CONTAINER_STYLE,
            stylesheet=stylesheet,
        )

    def _compose_stylesheet(self, registry: StyleRegistry) -> str:
        rules = [_BASE_STYLES.strip()]
        dynamic = registry.stylesheet()
        if dynamic:
            rules.append(dynamic)
        return "\n".join(rule for rule in rules if rule)

    def _materialize_table(
        self,
        table: Table,
        registry: StyleRegistry,
    ) -> RenderedTable:
        layout = table.layout or LayoutOptions.empty()
        visible_columns = layout.columns.visible_columns(table.columns)
        visible_set = set(visible_columns)
        column_style_map, sticky_columns = self._build_column_styles(layout, visible_columns)

        table_style_class = registry.register(table.table_style)
        sticky_table_class = "richframe-table--sticky-header" if layout.sticky_header else None
        table_class_attr = _compose_classes("richframe-table", table_style_class, sticky_table_class)
        table_style_attr = _style_attribute(table.table_style, inline=self._inline_styles)

        header_rows = tuple(
            self._materialize_row(
                row,
                table,
                registry,
                column_style_map,
                sticky_columns,
                visible_set,
                layout,
                body_index=None,
            )
            for row in table.header_rows
        )
        body_rows = tuple(
            self._materialize_row(
                row,
                table,
                registry,
                column_style_map,
                sticky_columns,
                visible_set,
                layout,
                body_index=index,
            )
            for index, row in enumerate(table.body_rows)
        )
        return RenderedTable(
            caption=table.caption,
            header_rows=header_rows,
            body_rows=body_rows,
            class_attr=table_class_attr,
            style_attr=table_style_attr,
            layout=layout,
            title=table.metadata.get("title") if isinstance(table.metadata, dict) else None,
            subtitle=table.metadata.get("subtitle") if isinstance(table.metadata, dict) else None,
        )

    def _materialize_row(
        self,
        row: Row,
        table: Table,
        registry: StyleRegistry,
        column_style_map: dict[str, str],
        sticky_columns: dict[str, str],
        visible_columns: set[str],
        layout: LayoutOptions,
        *,
        body_index: int | None,
    ) -> RenderedRow:
        row_style_class = registry.register(row.style)
        base_class = "richframe-row--header" if row.kind == "header" else "richframe-row--body"
        zebra_class = None
        zebra_style = None
        if (
            row.kind == "body"
            and layout.zebra_striping
            and row.style is None
            and body_index is not None
            and body_index % 2 == 1
        ):
            zebra_class = "richframe-row--zebra"
            zebra_style = _derive_zebra_background(row, table)
        row_class_attr = _compose_classes("richframe-row", base_class, row_style_class, zebra_class)
        row_style_attr = _merge_inline_styles(
            _style_attribute(row.style, inline=self._inline_styles),
            zebra_style,
        )
        cells = tuple(
            self._materialize_cell(
                cell,
                registry,
                column_style_map,
                sticky_columns,
                layout,
            )
            for cell in row.cells
            if cell.column_id is None or cell.column_id in visible_columns
        )
        return RenderedRow(
            cells=cells,
            class_attr=row_class_attr,
            style_attr=row_style_attr,
        )

    def _materialize_cell(
        self,
        cell: Cell,
        registry: StyleRegistry,
        column_style_map: dict[str, str],
        sticky_columns: dict[str, str],
        layout: LayoutOptions,
    ) -> RenderedCell:
        cell_style_class = registry.register(cell.style)
        base_class = "richframe-cell--header" if cell.kind == "header" else "richframe-cell--body"
        sticky_class = None
        layout_style = None
        if cell.column_id is not None:
            layout_style = column_style_map.get(cell.column_id)
            if cell.column_id in sticky_columns:
                sticky_class = "richframe-cell--sticky"
                sticky_offset = sticky_columns[cell.column_id]
                layout_style = _merge_inline_styles(
                    layout_style,
                    f"position: sticky; left: {sticky_offset}; z-index: 2; background: inherit; box-shadow: 1px 0 0 rgba(17, 24, 39, 0.08)",
                )
        cell_class_attr = _compose_classes("richframe-cell", base_class, cell_style_class, sticky_class)
        cell_style_attr = _style_attribute(cell.style, inline=self._inline_styles)
        if cell.kind == "header" and layout.sticky_header:
            cell_style_attr = _merge_inline_styles(
                cell_style_attr,
                "position: sticky; top: 0; z-index: 3; background: inherit",
            )
        if layout_style:
            cell_style_attr = _merge_inline_styles(cell_style_attr, layout_style)
        headers_attr = None
        if cell.headers:
            headers_attr = " ".join(cell.headers)
        tag = "th" if cell.kind == "header" else "td"
        return RenderedCell(
            text=cell.text,
            colspan=cell.colspan,
            rowspan=cell.rowspan,
            class_attr=cell_class_attr,
            style_attr=cell_style_attr,
            tag=tag,
            scope_attr=cell.scope,
            headers_attr=headers_attr,
            id_attr=cell.id,
        )

    @staticmethod
    def _load_template(template_name: str) -> Template:
        package = resources.files("richframe.templates")
        environment = Environment(
            loader=FileSystemLoader(str(package)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        return environment.get_template(template_name)

    def _build_column_styles(
        self,
        layout: LayoutOptions,
        columns: Sequence[str],
    ) -> tuple[dict[str, str | None], dict[str, str]]:
        column_styles: dict[str, str | None] = {}
        sticky_offsets: dict[str, str] = {}
        sticky_left = 0.0
        for column_id in columns:
            config = layout.columns.get(column_id) or ColumnConfig(column_id)
            style_parts: list[str] = []
            if config.width:
                style_parts.append(f"width: {config.width}")
                style_parts.append(f"min-width: {config.width}")
            if config.align:
                style_parts.append(f"text-align: {config.align}")
            if config.sticky:
                offset = f"{sticky_left:g}px"
                sticky_offsets[column_id] = offset
                if config.width:
                    sticky_left += _parse_width_px(config.width)
                else:
                    sticky_left += _DEFAULT_STICKY_WIDTH
                    style_parts.append(f"min-width: {_DEFAULT_STICKY_WIDTH:g}px")
            column_styles[column_id] = "; ".join(style_parts) if style_parts else None
        return column_styles, sticky_offsets


def _compose_classes(*parts: str | None) -> str:
    tokens = [part for part in parts if part]
    return " ".join(tokens)


def _style_attribute(style: object, *, inline: bool) -> str | None:
    if not inline:
        return None
    if style is None:
        return None
    # style is a BaseStyle, but we avoid importing here to sidestep cycles.
    css_text = getattr(style, "inline_style")
    if not callable(css_text):  # pragma: no cover - defensive
        return None
    declaration = css_text()
    return declaration if declaration else None


def _merge_inline_styles(existing: str | None, addition: str | None) -> str | None:
    if not addition:
        return existing
    if existing:
        if existing.endswith(";"):
            return f"{existing} {addition}"
        return f"{existing}; {addition}"
    return addition


def _parse_width_px(value: str) -> float:
    try:
        stripped = value.strip()
        if stripped.endswith("px"):
            return float(stripped[:-2])
        return 120.0
    except Exception:  # pragma: no cover - fallback
        return 120.0


def _derive_zebra_background(row: Row, table: Table) -> str:
    base = _extract_background_color(row)
    if base is None:
        base = _extract_table_background(table)
    if base is None:
        base = "#ffffff"
    luminosity = _luminance(base)
    if luminosity is not None and luminosity < 0.5:
        return "background-color: rgba(255, 255, 255, 0.08)"
    alpha = 0.04
    if luminosity is not None:
        if luminosity >= 0.8:
            alpha = 0.08
        elif luminosity >= 0.6:
            alpha = 0.06
    return f"background-color: rgba(0, 0, 0, {alpha:.2f})"


def _extract_background_color(row: Row) -> str | None:
    for cell in row.cells:
        style = getattr(cell, "style", None)
        if style is None:
            continue
        color = dict(style.properties).get("background-color")
        if color:
            return color
    return None


def _extract_table_background(table: Table) -> str | None:
    if table.table_style is None:
        return None
    return dict(table.table_style.properties).get("background-color")


def _is_dark_color(color: str) -> bool:
    rgb = _to_rgb(color)
    if rgb is None:
        return False
    r, g, b = [component / 255.0 for component in rgb]
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance < 0.5


def _luminance(color: str) -> float | None:
    rgb = _to_rgb(color)
    if rgb is None:
        return None
    r, g, b = [component / 255.0 for component in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _to_rgb(color: str) -> tuple[int, int, int] | None:
    color = color.strip()
    if color.startswith("#"):
        color = color[1:]
        if len(color) == 3:
            color = "".join(ch * 2 for ch in color)
        if len(color) == 6:
            try:
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
                return r, g, b
            except ValueError:  # pragma: no cover - invalid hex
                return None
    elif color.startswith("rgb"):
        try:
            values = color[color.index("(") + 1 : color.index(")")]
            parts = [part.strip() for part in values.split(",")]
            if len(parts) >= 3:
                return tuple(int(float(part) * 255 if float(part) <= 1 else float(part)) for part in parts[:3])  # type: ignore[misc]
        except Exception:  # pragma: no cover - defensive
            return None
    return None
