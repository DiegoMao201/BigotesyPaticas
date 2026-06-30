"""Golden tests para `bp_common.pricing.precio_con_margen`."""

from __future__ import annotations

import math

import pytest

from bp_common.pricing import MARGEN_BRUTO_OBJ_DEFAULT, precio_con_margen


def test_default_margin_is_20_percent():
    assert MARGEN_BRUTO_OBJ_DEFAULT == 0.20


def test_zero_or_negative_cost_returns_zero():
    assert precio_con_margen(0) == 0.0
    assert precio_con_margen(-100) == 0.0
    assert precio_con_margen(None) == 0.0  # type: ignore[arg-type]


def test_basic_formula():
    # P = C / (1 - m); con C=100, m=0.20 → 125.0
    assert precio_con_margen(100, 0.20) == pytest.approx(125.0)
    # C=1000, m=0.5 → 2000
    assert precio_con_margen(1000, 0.5) == pytest.approx(2000.0)


def test_margin_clamped_to_max_95():
    # m > 0.95 se clampa a 0.95 → P = C / 0.05 = C * 20
    p = precio_con_margen(100, 0.999)
    assert p == pytest.approx(2000.0)


def test_margin_clamped_to_min_0():
    # m < 0 se clampa a 0 → P = C
    assert precio_con_margen(100, -0.5) == pytest.approx(100.0)


def test_invalid_inputs_return_zero():
    assert precio_con_margen("not a number", 0.2) == 0.0  # type: ignore[arg-type]
    assert precio_con_margen(100, "bad") == 0.0  # type: ignore[arg-type]


def test_no_division_by_zero():
    # Aunque m=1.0 daría div/0, está clampado a 0.95
    p = precio_con_margen(50, 1.0)
    assert math.isfinite(p)
    assert p > 0
