"""Normalización de SKUs / IDs de producto — bit-exact a `normalizar_id_producto`."""
from __future__ import annotations

from typing import Any

try:
    import pandas as pd  # type: ignore

    def _is_na(v: Any) -> bool:
        try:
            return bool(pd.isna(v))
        except Exception:
            return v is None
except Exception:  # pragma: no cover
    def _is_na(v: Any) -> bool:
        return v is None


def normalizar_id_producto(id_prod: Any) -> str:
    """Canonicaliza un SKU.

    - Strip + upper.
    - Elimina espacios, comas y puntos.
    - Si queda numérico puro, quita ceros a la izquierda.
    - Si termina en `00` y el resto es numérico, quita los dos ceros finales
      (regla legacy heredada de Sheets — ver `BigotesyPaticas.py`).
    """
    if _is_na(id_prod):
        return ""
    s = str(id_prod).strip().upper()
    s = s.replace(" ", "").replace(",", "").replace(".", "")
    if s.isdigit():
        s = str(int(s))
    if s.endswith("00") and s[:-2].isdigit():
        s = s[:-2]
    return s


def limpiar_tel(tel: Any) -> str:
    """Normaliza un teléfono colombiano. Bit-exact a `BigotesyPaticas.py::limpiar_tel`."""
    t = (
        str(tel)
        .replace(" ", "")
        .replace("+", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .strip()
    )
    if len(t) == 10 and not t.startswith("57"):
        t = "57" + t
    return t
