from __future__ import annotations

from typing import Sequence

import pandas as pd
import pytest

from richframe import ColumnConfig, RowStyle, to_html
from richframe.format import PercentageFormatter
from richframe.style import compose_theme, register_theme


def test_to_html_renders_dataframe() -> None:
    frame = pd.DataFrame({"A": [1, 2], "B": ["foo", "bar"]})

    html = to_html(frame)

    assert "<style>" in html
    assert ".richframe-container" in html
    assert '<div class="richframe-container"' in html
    assert "class=\"richframe-table" in html
    assert 'scope="col"' in html
    assert '<th id="rf-h0-0"' in html
    assert '<td' in html and 'class="richframe-cell richframe-cell--body"' in html
    assert "1.00" in html
    assert "2.00" in html


def test_to_html_supports_caption_override() -> None:
    frame = pd.DataFrame({"A": [1]})

    html = to_html(frame, caption="My Caption")

    assert "<caption>My Caption</caption>" in html


def test_to_html_supports_inline_styles() -> None:
    frame = pd.DataFrame({"A": [1]})

    html = to_html(frame, inline_styles=True, theme="light")

    assert "style=\"background-color" in html
    assert "padding: 8px 12px" in html
    assert "class=\"richframe-cell" in html


def test_to_html_applies_named_theme() -> None:
    frame = pd.DataFrame({"A": [1]})

    html = to_html(frame, theme="dark")

    assert "#1f2937" in html  # dark table background


def test_to_html_allows_light_theme() -> None:
    frame = pd.DataFrame({"A": [1]})

    html = to_html(frame, theme="light")

    assert "#f6f8fa" in html  # light header background


def test_to_html_applies_custom_formatters() -> None:
    frame = pd.DataFrame({"price": [1234.5], "ratio": [0.257]}, index=["row1"])

    html = to_html(
        frame,
        formatters={"price": "currency", "ratio": PercentageFormatter(precision=2)},
    )

    assert "$1,234.50" in html
    assert "25.70%" in html


def test_to_html_rejects_formatters_for_table_objects(simple_table) -> None:
    table = simple_table

    with pytest.raises(ValueError):
        to_html(table, formatters={"A": "number"})


def test_to_html_applies_column_layout_visibility_and_alignment() -> None:
    frame = pd.DataFrame({"A": [1], "B": [2]})

    html = to_html(
        frame,
        column_layout={
            "A": ColumnConfig(id="A", align="right"),
            "B": {"visible": False},
        },
    )

    assert "<td" in html and "2.00" not in html
    assert "text-align: right" in html


def test_to_html_supports_sticky_header_and_columns() -> None:
    frame = pd.DataFrame({"A": [1], "B": [2]})

    html = to_html(
        frame,
        sticky_header=True,
        column_layout={"A": {"sticky": True, "width": "120px"}},
    )

    assert "top: 0" in html  # header stickiness
    assert "position: sticky" in html and "left: 0px" in html
    assert "min-width: 120px" in html


def test_to_html_assigns_min_width_to_sticky_columns_without_width() -> None:
    frame = pd.DataFrame({"A": [1], "B": [2]})

    html = to_html(
        frame,
        sticky_header=True,
        column_layout={"A": {"sticky": True}},
    )

    assert "min-width: 120px" in html


def test_to_html_supports_composed_theme() -> None:
    frame = pd.DataFrame({"A": [1]})
    theme = compose_theme(
        "light",
        name="brand-test",
        header_cell_style={"background_color": "#123456"},
    )
    register_theme(theme)

    html = to_html(frame, theme="brand-test", inline_styles=True)

    assert "#123456" in html


def test_to_html_zebra_striping() -> None:
    frame = pd.DataFrame({"A": [1, 2, 3]})

    html = to_html(frame, zebra_striping=True)

    assert "background-color: rgba(0, 0, 0, 0.08)" in html


def test_to_html_applies_row_predicate_styles() -> None:
    frame = pd.DataFrame({"value": [10, 25]}, index=["low", "high"])

    def highlight_high(index: str, _values: Sequence[object]) -> bool:
        return index == "high"

    html = to_html(
        frame,
        row_predicates=[(highlight_high, RowStyle(background_color="#ffeeee"))],
        inline_styles=True,
    )

    assert "#ffeeee" in html


def test_to_html_renders_titles_and_subtitles() -> None:
    frame = pd.DataFrame({"A": [1]})

    html = to_html(frame, title="Overview", subtitle="FY24")

    assert '<div class="richframe-title">Overview</div>' in html
    assert '<div class="richframe-subtitle">FY24</div>' in html


def test_to_html_zebra_striping_in_dark_theme() -> None:
    frame = pd.DataFrame({"A": [1, 2, 3]})

    html = to_html(frame, zebra_striping=True, theme="dark")

    assert "background-color: rgba(255, 255, 255, 0.08)" in html


def test_to_html_merges_multiindex_columns() -> None:
    columns = pd.MultiIndex.from_tuples(
        [
            ("North", "Q1"),
            ("North", "Q2"),
            ("South", "Q1"),
        ],
        names=["Region", "Quarter"],
    )
    frame = pd.DataFrame([[10, 12, 8], [9, 11, 7]], columns=columns)

    html = to_html(frame)

    assert 'colspan="2"' in html  # merged quarter headings under Region
    assert 'scope="colgroup"' in html  # grouped header scope
    assert 'headers="' in html and "rf-h0-0" in html  # column headers referenced


def test_to_html_merges_multiindex_index_rows() -> None:
    index = pd.MultiIndex.from_tuples(
        [
            ("North", "Austin"),
            ("North", "Dallas"),
            ("South", "Austin"),
        ],
        names=["Region", "City"],
    )
    frame = pd.DataFrame({"Sales": [10, 12, 8]}, index=index)

    html = to_html(frame)

    assert 'rowspan="2"' in html  # Region "North" merged across two rows
    assert '<th id="rf-r0-idx0" scope="rowgroup"' in html  # primary row header
    assert 'headers="' in html and "rf-r0-idx0" in html  # body cells reference row headers


def test_to_html_merges_three_level_multiindex_columns() -> None:
    columns = pd.MultiIndex.from_tuples(
        [
            ("North", "Retail", "Q1"),
            ("North", "Retail", "Q2"),
            ("North", "Wholesale", "Q1"),
            ("South", "Retail", "Q1"),
        ],
        names=["Region", "Channel", "Quarter"],
    )
    frame = pd.DataFrame([[10, 12, 8, 7], [9, 11, 7, 6]], columns=columns)

    html = to_html(frame)

    assert 'colspan="3">North' in html  # ragged top-level colspan
    assert 'colspan="2">Retail' in html  # second-level merged span
    assert 'scope="colgroup"' in html  # grouped header scopes still applied


def test_to_html_merges_three_level_multiindex_index_rows() -> None:
    index = pd.MultiIndex.from_tuples(
        [
            ("North", "Austin", "Store 1"),
            ("North", "Austin", "Store 2"),
            ("North", "Dallas", "Store 3"),
            ("South", "Houston", "Store 4"),
        ],
        names=["Region", "City", "Store"],
    )
    frame = pd.DataFrame({"Sales": [10, 12, 8, 9]}, index=index)

    html = to_html(frame)

    assert '<th id="rf-r0-idx0"' in html and 'rowspan="3">North' in html
    assert '<th id="rf-r0-idx1"' in html and 'rowspan="2">Austin' in html
    assert 'headers="' in html and "rf-r0-idx1" in html  # body cells inherit nested row headers
