"""Pricing — fórmula de precio con margen bruto sobre precio.

Fórmula vigente y NO negociable: ``P = C / (1 - m)``.
Cualquier cambio invalida toda la política de pricing del negocio.
"""

from __future__ import annotations

MARGEN_BRUTO_OBJ_DEFAULT: float = 0.20  # 20%


def precio_con_margen(costo_neto_unit: float, margen: float = MARGEN_BRUTO_OBJ_DEFAULT) -> float:
    """Calcula el precio dado un costo neto y un margen bruto sobre precio.

    Bit-exact a `pages/Compras.py::precio_con_margen` y `pages/Inventario_Nexus.py::precio_con_margen`.

    Args:
        costo_neto_unit: costo unitario neto (≥ 0).
        margen: margen bruto sobre precio (0..0.95, clamp aplicado).

    Returns:
        Precio sugerido en float. Devuelve 0.0 si costo ≤ 0 o si hay error.
    """
    try:
        c = float(costo_neto_unit or 0.0)
        m = float(margen or 0.0)
        if c <= 0:
            return 0.0
        m = max(0.0, min(0.95, m))
        return c / (1.0 - m)
    except Exception:
        return 0.0
