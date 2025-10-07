# richframe

`richframe` turns `pandas.DataFrame` objects into richly styled HTML tables with theming, formatting, and layout control.

## Installation

```bash
uv pip install -e .
```

## Quick start

```python
import pandas as pd
from richframe import to_html

sales = pd.DataFrame(
    {
        "Region": ["North", "South", "West", "East"],
        "Units": [120, 85, 102, 150],
        "Growth": [0.12, -0.05, 0.08, 0.21],
    },
    index=pd.Index(["Q1", "Q2", "Q3", "Q4"], name="Quarter"),
)

html = to_html(
    sales,
    theme="light",
    caption="Quarterly Sales",
    formatters={"Units": "number", "Growth": "percent"},
)
```

Render the `html` string in a Jupyter notebook using `IPython.display.HTML(html)` or embed it in any HTML-aware surface.

## Capabilities

- **Core Rendering** — Transform DataFrames into a structured `Table` model and emit accessible HTML through Jinja templates.
- **Theme & Style System** — Ship Minimal, Light, and Dark themes with class deduplication and an inline CSS mode for email-compatible output.
- **Formatting Toolkit** — Apply built-in number, currency, percentage, and date formatters, optionally locale-aware via the `babel` extra.
- **Layout Controls** — Configure widths, alignment, visibility, sticky columns, sticky headers, zebra striping, and rule-driven row styling.
- **Intelligent Merging** — Derive row/column spans for MultiIndex headers and indexes while preserving accessibility via `scope` and `headers` metadata.
- **Plugin Layer** — Compose color scales, in-cell data bars, icon sets, and fluent conditional formatting through a lightweight plugin pipeline.

## Layout & styling examples

```python
from typing import Sequence
from richframe import ColumnConfig, RowStyle, to_html

highlight = RowStyle(background_color="#fff3cd")

def high_growth(index: str, values: Sequence[object]) -> bool:
    return values[2] is not None and values[2] > 0.15

html = to_html(
    sales,
    theme="dark",
    title="Regional Performance",
    subtitle="FY24 Snapshot",
    column_layout={
        "Quarter": ColumnConfig(id="Quarter", sticky=True, width="110px"),
        "Region": {"width": "140px"},
        "Units": {"align": "right"},
        "Growth": {"align": "right"},
    },
    formatters={"Units": "number", "Growth": "percent"},
    sticky_header=True,
    zebra_striping=True,
    row_predicates=[(high_growth, highlight)],
)
```

The renderer automatically adjusts zebra striping and sticky column offsets to maintain readable output across themes.

## MultiIndex merging example

```python
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
        ("North", "Austin", "Store 1"),
        ("North", "Austin", "Store 2"),
        ("North", "Dallas", "Store 3"),
        ("South", "Houston", "Store 4"),
    ],
    names=["Region", "City", "Store"],
)

pivot = pd.DataFrame(
    [
        [10, 12, 8, 7],
        [9, 11, 7, 6],
        [13, 15, 9, 8],
        [14, 16, 10, 9],
    ],
    index=index,
    columns=columns,
)

html = to_html(pivot, theme="minimal", sticky_header=True, zebra_striping=True)
```

`richframe` merges repeated labels in both the header and index hierarchies, emits accurate `scope`/`headers` metadata, and keeps merged cells sticky when requested.

## Conditional styling plugins

```python
from richframe import (
    ColorScalePlugin,
    DataBarPlugin,
    IconRule,
    IconSetPlugin,
    conditional_format,
    to_html,
)

sales = pd.DataFrame(
    {
        "Region": ["North", "South", "West", "East"],
        "Units": [120, 85, 102, 150],
        "Growth": [0.12, -0.05, 0.08, 0.27],
    },
    index=pd.Index(["Q1", "Q2", "Q3", "Q4"], name="Quarter"),
)

plugins = [
    ColorScalePlugin("Growth", palette=("#ecfccb", "#15803d")),
    DataBarPlugin("Units"),
    IconSetPlugin(
        "Growth",
        rules=(
            IconRule(
                lambda v: isinstance(v, (int, float)) and v > 0.1,
                "🔺",
                {"color": "#16a34a"},
            ),
            IconRule(
                lambda v: isinstance(v, (int, float)) and v <= 0.0,
                "🔻",
                {"color": "#dc2626"},
            ),

        ),
    ),
    conditional_format()
    .when(
        column="Growth",
        predicate=lambda v: isinstance(v, (int, float)) and v > 0.2,
    )
    .style(border_bottom="2px solid #16a34a"),
]

html = to_html(
    sales,
    theme="light",
    inline_styles=True,
    plugins=plugins,
    title="Regional Performance",
    subtitle="Plugin showcase",
)
```

Plugins run after formatting and theming, letting you combine visual cues such as heatmaps, data bars, and icons without losing theme defaults.

## Testing

```bash
uv run pytest
```

---

Built with `uv`, `pandas`, and `jinja2`.
