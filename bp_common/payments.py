"""Estados de pago — bit-exact a `BigotesyPaticas.py::_normalizar_estado_pago`."""

from __future__ import annotations

from typing import Any

from bp_common.currency import clean_currency

ESTADOS_PAGADO = {"pagado", "pago completo", "completo", "al día", "aldia"}
ESTADOS_PENDIENTE = {"pendiente", "por cobrar", "credito", "crédito", "sin pagar"}
ESTADOS_PARCIAL = {"abono parcial", "parcial", "abonado"}


def normalizar_estado_pago(valor: Any, saldo_pendiente: Any, total: Any) -> str:
    """Devuelve el estado canónico de pago: ``Pagado`` | ``Pendiente`` | ``Abono parcial``.

    Reglas (en orden):
      1. Si el texto entrante mapea explícitamente a un estado conocido, se respeta.
      2. Si saldo_pendiente ≤ 0 → ``Pagado``.
      3. Si total > 0 y saldo_pendiente ≥ total → ``Pendiente``.
      4. En cualquier otro caso → ``Abono parcial``.
    """
    saldo_pendiente_i = clean_currency(saldo_pendiente or 0)
    total_i = clean_currency(total or 0)
    txt = str(valor or "").strip().lower()
    if txt in ESTADOS_PAGADO:
        return "Pagado"
    if txt in ESTADOS_PENDIENTE:
        return "Pendiente"
    if txt in ESTADOS_PARCIAL:
        return "Abono parcial"
    if saldo_pendiente_i <= 0:
        return "Pagado"
    if total_i > 0 and saldo_pendiente_i >= total_i:
        return "Pendiente"
    return "Abono parcial"
