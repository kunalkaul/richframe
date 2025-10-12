from __future__ import annotations

import random
import time
from decimal import Decimal

import pandas as pd
import pytest

from richframe import to_html
from richframe.format import FormatContext, NumberFormatter
from richframe.io.pandas_adapter import dataframe_to_table


@pytest.mark.parametrize("seed", [3, 17])
def test_number_formatter_randomised_precision(seed: int) -> None:
    rng = random.Random(seed)
    formatter = NumberFormatter(
        precision=None,
        max_precision=4,
        min_precision=0,
        trim_trailing_zeros=True,
        use_grouping=False,
    )
    context = FormatContext(column_id="value")
    for _ in range(200):
        value = rng.uniform(-10_000, 10_000) * rng.choice([1, 0.1, 0.01])
        result = formatter(value, context)
        assert result  # formatter should always return a non-empty string
        as_decimal = Decimal(result)
        original = Decimal(str(value))
        assert abs(as_decimal - original) <= Decimal("0.0002")


def test_randomised_merge_span_integrity() -> None:
    rng = random.Random(42)
    regions = ["North", "South", "East"]
    cities = ["Austin", "Dallas", "Denver", "Miami"]
    tuples = [(rng.choice(regions), rng.choice(cities)) for _ in range(24)]
    index = pd.MultiIndex.from_tuples(tuples, names=["Region", "City"])
    columns = pd.MultiIndex.from_product(
        [["Revenue", "Units"], ["Q1", "Q2"]],
        names=["Metric", "Quarter"],
    )
    data = {
        column: [rng.randint(0, 500) for _ in range(len(index))]
        for column in columns
    }
    frame = pd.DataFrame(data, index=index)
    table = dataframe_to_table(frame, include_index=True)

    duplicates_present = any(
        table.body_rows[i].cells[0].text == table.body_rows[i - 1].cells[0].text
        for i in range(1, len(table.body_rows))
    )
    rowspans = [
        cell.rowspan
        for row in table.body_rows
        for cell in row.cells
        if cell.rowspan > 1
    ]
    colspans = [
        cell.colspan
        for row in table.header_rows
        for cell in row.cells
        if cell.colspan > 1
    ]
    assert all(span <= len(table.body_rows) for span in rowspans)
    assert all(span <= len(table.header_rows[0].cells) for span in colspans)
    if duplicates_present:
        assert rowspans, "Expected row spans when duplicate index labels exist"
    assert colspans, "Multi-level columns should produce colspan merges"


@pytest.mark.performance
def test_to_html_large_frame_baseline() -> None:
    rows, cols = 300, 24
    frame = pd.DataFrame(
        {f"Col {i}": [i * j % 97 for j in range(rows)] for i in range(cols)}
    )
    start = time.perf_counter()
    html = to_html(frame, zebra_striping=True, sticky_header=True)
    duration = time.perf_counter() - start
    assert html.startswith("<style>")
    assert duration < 1.2, f"to_html took {duration:.3f}s, expected < 1.2s"
