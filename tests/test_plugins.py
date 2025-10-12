from __future__ import annotations

import pandas as pd

from richframe import (
    ColorScalePlugin,
    DataBarPlugin,
    IconRule,
    IconSetPlugin,
    conditional_format,
    to_html,
)


def test_color_scale_plugin_applies_gradient() -> None:
    frame = pd.DataFrame({"score": [10, 20, 30]})

    html = to_html(frame, inline_styles=True, theme="light", plugins=[ColorScalePlugin("score")])

    assert "background-color: #1d4ed8" in html


def test_data_bar_plugin_renders_linear_gradient() -> None:
    frame = pd.DataFrame({"amount": [5, 15, 30]})

    html = to_html(frame, inline_styles=True, theme="light", plugins=[DataBarPlugin("amount")])

    assert "linear-gradient(90deg" in html


def test_icon_set_plugin_prefixes_text() -> None:
    frame = pd.DataFrame({"trend": [0.2, -0.1]})
    plugin = IconSetPlugin(
        "trend",
        rules=(
            IconRule(lambda value: value is not None and value > 0, "🔺", {"color": "#16a34a"}),
            IconRule(lambda value: value is not None and value <= 0, "🔻", {"color": "#dc2626"}),
        ),
    )

    html = to_html(frame, inline_styles=True, theme="light", plugins=[plugin])

    assert "🔺" in html and "🔻" in html


def test_conditional_formatting_rules_apply_styles() -> None:
    frame = pd.DataFrame({"ratio": [0.1, 0.35]})
    rules = (
        conditional_format()
        .when(column="ratio", predicate=lambda value: value is not None and value > 0.3)
        .style(background_color="#fee2e2", color="#b91c1c")
    )

    html = to_html(frame, inline_styles=True, theme="light", plugins=[rules])

    assert "background-color: #fee2e2" in html
