from __future__ import annotations

import pytest

from richframe.core.model import Cell, Row, Table


@pytest.fixture
def simple_table() -> Table:
    header = Row(
        cells=(
            Cell(value="A", text="A", kind="header"),
            Cell(value="B", text="B", kind="header"),
        ),
        kind="header",
    )
    body = Row(
        cells=(
            Cell(value=1, text="1", column_id="A"),
            Cell(value=2, text="2", column_id="B"),
        ),
        kind="body",
    )
    return Table(
        columns=("A", "B"),
        header_rows=(header,),
        body_rows=(body,),
    )
