"""Golden tests para `bp_common.payments.normalizar_estado_pago`."""

from __future__ import annotations

import pytest

from bp_common.payments import normalizar_estado_pago


@pytest.mark.parametrize(
    "valor, saldo, total, expected",
    [
        # Valores explícitos pisan la lógica
        ("Pagado", 5000, 10000, "Pagado"),
        ("pago completo", 5000, 10000, "Pagado"),
        ("AL DÍA", 5000, 10000, "Pagado"),
        ("Pendiente", 0, 10000, "Pendiente"),
        ("crédito", 0, 10000, "Pendiente"),
        ("abono parcial", 0, 10000, "Abono parcial"),
        # Lógica por saldo cuando no hay etiqueta
        ("", 0, 10000, "Pagado"),
        ("", -100, 10000, "Pagado"),
        ("", 10000, 10000, "Pendiente"),
        ("", 5000, 10000, "Abono parcial"),
        ("", 15000, 10000, "Pendiente"),
        # Edge: total 0 y saldo 0 → Pagado
        ("", 0, 0, "Pagado"),
        # Acepta strings de moneda
        ("", "$5.000", "$10.000", "Abono parcial"),
        ("", "10000", "10000", "Pendiente"),
    ],
)
def test_normalizar_estado_pago(valor, saldo, total, expected):
    assert normalizar_estado_pago(valor, saldo, total) == expected
