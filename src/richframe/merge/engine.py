"""Implement row and column span logic for table rendering."""
from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from ..core.model import Cell, Row, Table

__all__ = ["apply_merges"]


def apply_merges(table: Table, *, index_columns: Sequence[str]) -> Table:
    """Return a new table with header colspans and body rowspans applied."""

    header_rows = _merge_header_rows(table.header_rows)
    header_rows, column_header_map = _assign_header_metadata(header_rows, table.columns)
    body_rows, row_header_ids = _merge_index_columns(table.body_rows, index_columns)
    body_rows = _assign_body_headers(body_rows, column_header_map, row_header_ids)
    metadata = dict(table.metadata) if isinstance(table.metadata, dict) else {}
    return Table(
        columns=table.columns,
        header_rows=header_rows,
        body_rows=body_rows,
        caption=table.caption,
        metadata=metadata,
        table_style=table.table_style,
        layout=table.layout,
    )


def _merge_header_rows(header_rows: Sequence[Row]) -> tuple[Row, ...]:
    merged_rows: list[Row] = []
    for row in header_rows:
        if not row.cells:
            merged_rows.append(row)
            continue
        new_cells: list[Cell] = []
        cells = list(row.cells)
        idx = 0
        while idx < len(cells):
            current = cells[idx]
            span = 1
            while idx + span < len(cells):
                candidate = cells[idx + span]
                if not _should_merge_header_cells(current, candidate):
                    break
                span += 1
            new_cells.append(replace(current, colspan=span))
            idx += span
        merged_rows.append(Row(tuple(new_cells), kind=row.kind, index=row.index, style=row.style))
    return tuple(merged_rows)


def _should_merge_header_cells(left: Cell, right: Cell) -> bool:
    return (
        left.text == right.text
        and left.kind == right.kind
        and left.style == right.style
    )


def _assign_header_metadata(
    header_rows: Sequence[Row],
    columns: Sequence[str],
) -> tuple[tuple[Row, ...], dict[str, tuple[str, ...]]]:
    column_to_headers: dict[str, list[str]] = {column: [] for column in columns}
    updated_rows: list[Row] = []
    for row_index, row in enumerate(header_rows):
        pointer = 0
        resolved_cells: list[Cell] = []
        for cell_index, cell in enumerate(row.cells):
            span = cell.colspan if cell.colspan > 0 else 1
            cell_id = cell.id or f"rf-h{row_index}-{cell_index}"
            scope = cell.scope or ("colgroup" if span > 1 else "col")
            coverage = columns[pointer : pointer + span]
            for column_id in coverage:
                column_to_headers[column_id].append(cell_id)
            pointer += span
            resolved_cells.append(replace(cell, id=cell_id, scope=scope))
        updated_rows.append(Row(tuple(resolved_cells), kind=row.kind, index=row.index, style=row.style))
    column_header_map = {column: tuple(ids) for column, ids in column_to_headers.items()}
    return tuple(updated_rows), column_header_map


def _merge_index_columns(
    body_rows: Sequence[Row],
    index_columns: Sequence[str],
) -> tuple[tuple[Row, ...], list[list[str]]]:
    if not index_columns:
        return tuple(body_rows), [[] for _ in body_rows]

    index_values = [
        [_cell_text_for_column(row, column_id) for column_id in index_columns]
        for row in body_rows
    ]
    rowspan_overrides: list[dict[str, int]] = [dict() for _ in body_rows]
    hidden_cells: list[set[str]] = [set() for _ in body_rows]

    for column_offset, column_id in enumerate(index_columns):
        row_idx = 0
        while row_idx < len(body_rows):
            if column_id in hidden_cells[row_idx]:
                row_idx += 1
                continue
            label = index_values[row_idx][column_offset]
            if label in (None, ""):
                row_idx += 1
                continue
            group_size = 1
            probe = row_idx + 1
            while probe < len(body_rows):
                if column_id in hidden_cells[probe]:
                    break
                if index_values[probe][column_offset] != label:
                    break
                if any(
                    index_values[row_idx][prev] != index_values[probe][prev]
                    for prev in range(column_offset)
                ):
                    break
                group_size += 1
                probe += 1
            if group_size > 1:
                rowspan_overrides[row_idx][column_id] = group_size
                for hidden_idx in range(row_idx + 1, row_idx + group_size):
                    hidden_cells[hidden_idx].add(column_id)
            row_idx += group_size

    updated_rows: list[Row] = []
    row_header_ids: list[list[str]] = []
    for row_index, row in enumerate(body_rows):
        headers_for_row: list[str] = []
        new_cells: list[Cell] = []
        header_position = 0
        for cell in row.cells:
            column_id = cell.column_id
            if column_id is not None and column_id in hidden_cells[row_index]:
                continue
            span = rowspan_overrides[row_index].get(column_id, cell.rowspan)
            if column_id is not None and column_id in index_columns:
                scope = "rowgroup" if span > 1 else "row"
                cell_id = cell.id or f"rf-r{row_index}-idx{header_position}"
                header_position += 1
                headers_for_row.append(cell_id)
                new_cell = replace(
                    cell,
                    kind="header",
                    rowspan=span,
                    scope=scope,
                    id=cell_id,
                )
            elif span != cell.rowspan:
                new_cell = replace(cell, rowspan=span)
            else:
                new_cell = cell
            new_cells.append(new_cell)
        updated_rows.append(Row(tuple(new_cells), kind=row.kind, index=row.index, style=row.style))
        row_header_ids.append(headers_for_row)
    return tuple(updated_rows), row_header_ids


def _assign_body_headers(
    body_rows: Sequence[Row],
    column_header_map: dict[str, tuple[str, ...]],
    row_header_ids: Sequence[Sequence[str]],
) -> tuple[Row, ...]:
    updated_rows: list[Row] = []
    for row_index, row in enumerate(body_rows):
        row_headers = tuple(row_header_ids[row_index]) if row_index < len(row_header_ids) else tuple()
        new_cells: list[Cell] = []
        for cell in row.cells:
            column_id = cell.column_id
            column_headers = column_header_map.get(column_id, tuple()) if column_id is not None else tuple()
            if cell.kind == "body":
                combined = tuple(column_headers) + row_headers
                headers = combined or None
            elif cell.kind == "header":
                headers = tuple(column_headers) if column_headers else None
            else:
                headers = cell.headers
            if headers == cell.headers:
                new_cell = cell
            else:
                new_cell = replace(cell, headers=headers)
            new_cells.append(new_cell)
        updated_rows.append(Row(tuple(new_cells), kind=row.kind, index=row.index, style=row.style))
    return tuple(updated_rows)


def _cell_text_for_column(row: Row, column_id: str) -> str | None:
    for cell in row.cells:
        if cell.column_id == column_id:
            return cell.text
    return None
