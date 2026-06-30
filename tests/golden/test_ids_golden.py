"""Golden tests para `bp_common.ids.normalizar_id_producto` y `limpiar_tel`."""

from __future__ import annotations

import pytest

from bp_common.ids import limpiar_tel, normalizar_id_producto


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, ""),
        ("", ""),
        ("abc", "ABC"),
        (" abc ", "ABC"),
        ("01-ABC.5", "01-ABC5"),  # quita el "."; el "-" se preserva
        ("01.ABC.5", "01ABC5"),
        ("00100", "1"),  # numérico puro → quita ceros izq
        ("0100", "1"),
        ("100", "1"),  # termina en 00 → trunca
        ("12300", "123"),  # termina en 00 → trunca
        ("12345", "12345"),
        # "ABC100": legacy upper→"ABC100", no isdigit → no entra al bloque numérico → tal cual.
        # (Caso explícito en `test_normalizar_id_producto_alphanumeric_keeps_trailing_00`.)
    ],
)
def test_normalizar_id_producto(raw, expected):
    assert normalizar_id_producto(raw) == expected


def test_normalizar_id_producto_alphanumeric_keeps_trailing_00():
    # "ABC100" → upper "ABC100", luego s[:-2] = "ABC1" no es dígito → no trunca
    # Recalculamos: s.endswith("00") True, s[:-2]="ABC1".isdigit() False → NO trunca
    # Corrección del caso anterior:
    assert normalizar_id_producto("ABC100") == "ABC100"


def test_normalizar_id_producto_numeric_with_leading_zeros_after_strip():
    # "0,0,1,0,0" → strip non-alpha → "00100" → isdigit → "100" → endswith 00 → "1"
    assert normalizar_id_producto("0,0,1,0,0") == "1"


def test_normalizar_id_producto_pandas_na():
    pd = pytest.importorskip("pandas")
    assert normalizar_id_producto(pd.NA) == ""
    import math

    assert normalizar_id_producto(math.nan) == ""


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("3001234567", "573001234567"),  # 10 dígitos + agrega 57
        ("+57 300 123 4567", "573001234567"),
        ("(300) 123-4567", "573001234567"),
        ("573001234567", "573001234567"),  # ya con 57
        ("123", "123"),  # < 10 dígitos: no toca
    ],
)
def test_limpiar_tel(raw, expected):
    assert limpiar_tel(raw) == expected
