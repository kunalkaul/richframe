from __future__ import annotations

from datetime import date
from decimal import Decimal

import math
import pytest

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


def test_number_formatter_trims_trailing_zero_when_requested() -> None:
    formatter = NumberFormatter(precision=4, trim_trailing_zeros=True, min_precision=1)
    context = FormatContext(column_id="value")

    assert formatter(Decimal("1.2300"), context) == "1.23"


def test_number_formatter_infers_precision_when_not_fixed() -> None:
    formatter = NumberFormatter(precision=None, max_precision=3, trim_trailing_zeros=True)
    context = FormatContext(column_id="value")

    assert formatter(3.14159, context) == "3.142"


def test_number_formatter_locale_separators() -> None:
    pytest.importorskip("babel.numbers")
    formatter = NumberFormatter()
    context = FormatContext(column_id="value", locale="fr_FR")

    result = formatter(1234.567, context)

    assert result.endswith(",57")
    assert "\u202f" in result or "\xa0" in result


def test_number_formatter_preserves_non_numeric_values() -> None:
    formatter = NumberFormatter()
    context = FormatContext(column_id="value")

    assert formatter("n/a", context) == "n/a"
