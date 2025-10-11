from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from richframe import ColumnConfig, RowStyle, to_html
from richframe.format import NumberFormatter, PercentageFormatter
from richframe.plugins import ColorScalePlugin
from richframe.style import compose_theme, register_theme

GOLDEN_DIR = Path(__file__).parent / "golden"


def _read_golden(name: str) -> str:
    return (GOLDEN_DIR / name).read_text(encoding="utf-8")


def _normalise(html: str) -> str:
    return "\n".join(line.rstrip() for line in html.strip().splitlines())


@pytest.mark.snapshot
def test_styled_table_snapshot() -> None:
    frame = pd.DataFrame(
        {
            "Region": ["North", "South", "West"],
            "Units": [120, 85, 102],
            "Growth": [0.125, -0.045, 0.081],
        },
        index=pd.Index(["Q1", "Q2", "Q3"], name="Quarter"),
    )
    html = to_html(
        frame,
        theme="light",
        sticky_header=True,
        zebra_striping=True,
        column_layout={
            "Quarter": ColumnConfig(id="Quarter", sticky=True, width="110px"),
            "Region": {"width": "140px"},
            "Units": {"align": "right"},
            "Growth": {"align": "right"},
        },
        formatters={
            "Units": NumberFormatter(precision=None, trim_trailing_zeros=True),
            "Growth": PercentageFormatter(precision=1),
        },
    )
    assert _normalise(html) == _normalise(_read_golden("styled_table.html"))


@pytest.mark.snapshot
def test_merged_table_snapshot() -> None:
    columns = pd.MultiIndex.from_tuples(
        [
            ("North", "Retail", "Q1"),
            ("North", "Retail", "Q2"),
            ("North", "Wholesale", "Q1"),
            ("South", "Retail", "Q1"),
        ],
        names=["Region", "Channel", "Quarter"],
    )
    index = pd.MultiIndex.from_tuples(
        [
            ("North", "Austin"),
            ("North", "Austin"),
            ("North", "Dallas"),
            ("South", "Houston"),
        ],
        names=["Region", "City"],
    )
    frame = pd.DataFrame(
        [
            [10, 12, 8, 7],
            [9, 11, 7, 6],
            [13, 15, 9, 8],
            [14, 16, 10, 9],
        ],
        index=index,
        columns=columns,
    )
    html = to_html(frame, zebra_striping=True)
    assert _normalise(html) == _normalise(_read_golden("merged_table.html"))


@pytest.mark.snapshot
def test_conditional_table_snapshot() -> None:
    frame = pd.DataFrame(
        {
            "Region": ["North", "South", "West", "East"],
            "Units": [120, 85, 102, 150],
            "Growth": [0.12, -0.05, 0.08, 0.27],
        },
        index=pd.Index(["Q1", "Q2", "Q3", "Q4"], name="Quarter"),
    )
    theme = compose_theme(
        "minimal",
        name="snapshot-brand",
        header_cell_style={"background_color": "#0f172a", "color": "#e2e8f0"},
    )
    register_theme(theme)
    html = to_html(
        frame,
        theme="snapshot-brand",
        inline_styles=True,
        plugins=[ColorScalePlugin("Growth", palette=("#f1f5f9", "#1d4ed8"))],
        row_predicates=[
            (
                lambda idx, _values: isinstance(idx, str) and idx.endswith("4"),
                RowStyle(background_color="#fef3c7"),
            )
        ],
        formatters={
            "Units": NumberFormatter(precision=0, use_grouping=False),
            "Growth": PercentageFormatter(precision=1),
        },
    )
    assert _normalise(html) == _normalise(_read_golden("conditional_table.html"))
