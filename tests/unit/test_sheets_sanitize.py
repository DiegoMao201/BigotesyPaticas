"""Tests para `bp_common.sheets_sanitize.sanitizar_para_sheet`."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from bp_common.sheets_sanitize import sanitizar_para_sheet


def test_int_passthrough():
    assert sanitizar_para_sheet(5) == 5


def test_float_to_int_round():
    assert sanitizar_para_sheet(1.4) == 1
    assert sanitizar_para_sheet(1.6) == 2


def test_date_iso():
    assert sanitizar_para_sheet(date(2026, 5, 10)) == "2026-05-10"


def test_datetime_iso():
    assert sanitizar_para_sheet(datetime(2026, 5, 10, 14, 30, 0)) == "2026-05-10 14:30:00"


def test_string_passthrough():
    assert sanitizar_para_sheet("hello") == "hello"


def test_numpy_optional():
    np = pytest.importorskip("numpy")
    assert sanitizar_para_sheet(np.int64(7)) == 7
    assert sanitizar_para_sheet(np.float64(7.5)) == 8


def test_pandas_timestamp_optional():
    pd = pytest.importorskip("pandas")
    ts = pd.Timestamp("2026-01-01 10:00:00")
    out = sanitizar_para_sheet(ts)
    assert out.startswith("2026-01-01")
