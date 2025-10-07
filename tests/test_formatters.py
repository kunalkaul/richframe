from __future__ import annotations

from datetime import date

import math

from richframe.format import (
    CurrencyFormatter,
    DateFormatter,
    FormatContext,
    NumberFormatter,
    PercentageFormatter,
)


def test_number_formatter_default_precision() -> None:
    formatter = NumberFormatter()
    context = FormatContext(column_id="value")

    assert formatter(1234.567, context) == "1,234.57"


def test_number_formatter_handles_nan() -> None:
    formatter = NumberFormatter()
    context = FormatContext(column_id="value")

    assert formatter(math.nan, context) == ""


def test_currency_formatter_prefix() -> None:
    formatter = CurrencyFormatter(symbol="€")
    context = FormatContext(column_id="value")

    assert formatter(9.5, context) == "€9.50"


def test_percentage_formatter() -> None:
    formatter = PercentageFormatter(precision=2)
    context = FormatContext(column_id="ratio")

    assert formatter(0.2571, context) == "25.71%"


def test_date_formatter_iso_fallback() -> None:
    formatter = DateFormatter()
    context = FormatContext(column_id="when", locale=None)

    assert formatter(date(2024, 1, 15), context) == "2024-01-15"
