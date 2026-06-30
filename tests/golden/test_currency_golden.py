"""Golden tests para `bp_common.currency.clean_currency`.

Cada caso documenta el input y el output esperado bit-exact respecto a
`BigotesyPaticas.py::clean_currency`.
"""

from __future__ import annotations

import pytest

from bp_common.currency import clean_currency, format_cop, money_float, money_int


@pytest.mark.parametrize(
    "raw, expected",
    [
        # ints / floats / numpy
        (0, 0),
        (1500, 1500),
        (-1500, -1500),
        (1500.0, 1500),
        (1500.4, 1500),
        (1500.6, 1501),
        (None, 0),
        ("", 0),
        # strings simples
        ("0", 0),
        ("100", 100),
        ("-100", -100),
        ("$1.200", 1200),
        ("$ 1.200 ", 1200),
        ("1,200", 1200),  # 3 dígitos a la derecha + 1 izquierda → miles
        ("1.200", 1200),
        ("12,500", 12500),
        ("12.500", 12500),
        ("1.234.567", 1234567),
        ("1,234,567", 1234567),
        # mezclas
        ("1.234,56", 1235),  # 1234.56 → 1235 (round half-up)
        ("1,234.56", 1235),
        # decimales — la heurística legacy con 1-2 dígitos tras el separador trata
        # el separador como decimal y trunca al int (sin redondeo float→int explícito
        # cuando el resultado del parseo da 100.5 → int(100.5) = 100)
        ("100,5", 100),
        ("100.5", 100),
        ("100,49", 100),
        ("100.49", 100),
        # vacíos / basura
        ("abc", 0),
        ("--", 0),
        # con prefijos
        ("$-500", -500),
    ],
)
def test_clean_currency(raw, expected):
    assert clean_currency(raw) == expected


def test_money_int_alias():
    assert money_int("$1.500") == 1500


def test_money_float():
    assert money_float("$1.500") == 1500.0
    assert isinstance(money_float("100"), float)


@pytest.mark.parametrize(
    "raw, expected",
    [
        (0, "$0"),
        (1500, "$1.500"),
        (-1500, "-$1.500"),
        (1234567, "$1.234.567"),
    ],
)
def test_format_cop(raw, expected):
    assert format_cop(raw) == expected


def test_clean_currency_numpy():
    np = pytest.importorskip("numpy")
    assert clean_currency(np.int64(1500)) == 1500
    assert clean_currency(np.float64(1500.7)) == 1501
