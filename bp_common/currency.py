"""Currency parsing — equivalente exacto a `clean_currency` en BigotesyPaticas.py."""

from __future__ import annotations

import re
from typing import Any

try:  # opcional, sólo si pandas/numpy están disponibles
    import numpy as np  # type: ignore

    _NP_INT = (np.integer,)
    _NP_FLOAT = (np.floating,)
except Exception:  # pragma: no cover
    _NP_INT = ()
    _NP_FLOAT = ()


def clean_currency(val: Any) -> int:
    """Parsea cualquier representación de moneda colombiana a entero.

    Reglas:
      - Acepta int/float/np.integer/np.floating directos.
      - Strip de "$", espacios.
      - Soporta separadores ",", "." en cualquier orden.
      - Heurística: si la parte derecha tiene 3 dígitos y la izquierda > 3,
        se trata como separador de miles.
      - Negativos con prefijo "-".
      - Devuelve siempre `int` (COP sin decimales).

    Bit-exact respecto a `BigotesyPaticas.py::clean_currency`.
    """
    if isinstance(val, bool):  # bool es subclass de int — descartar
        return int(val)
    if isinstance(val, (*_NP_INT, int)):
        return int(val)
    if isinstance(val, (*_NP_FLOAT, float)):
        return int(round(float(val)))

    s = str(val or "").strip().replace("$", "").replace(" ", "")
    if not s:
        return 0
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    s = re.sub(r"[^0-9,\.]", "", s)
    if not s:
        return 0

    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(",") > 1:
        s = s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif "," in s:
        left, right = s.split(",", 1)
        if len(right) <= 2:
            s = f"{left}.{right}"
        elif len(right) == 3 and len(left) <= 3:
            s = left + right
        elif len(right) == 3 and len(left) > 3:
            s = f"{left}.{right}"
        else:
            s = left + right
    elif "." in s:
        left, right = s.split(".", 1)
        if len(right) <= 2:
            s = f"{left}.{right}"
        elif len(right) == 3 and len(left) <= 3:
            s = left + right
        elif len(right) == 3 and len(left) > 3:
            s = f"{left}.{right}"
        else:
            s = left + right

    try:
        out = int(round(float(s)))
    except Exception:
        out = int(re.sub(r"[^0-9]", "", s) or 0)
    return -out if neg else out


def money_int(val: Any) -> int:
    """Alias usado por las páginas. Idéntico a clean_currency."""
    return clean_currency(val)


def money_float(val: Any) -> float:
    """Versión float (se usa en cálculos intermedios de pricing/margen)."""
    return float(clean_currency(val))


def format_cop(val: Any) -> str:
    """Formato visual `$1.234.567` (separador de miles con punto, estilo CO)."""
    n = clean_currency(val)
    sign = "-" if n < 0 else ""
    return f"{sign}${abs(n):,}".replace(",", ".")
