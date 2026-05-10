"""Sheet sanitization — bit-exact a `BigotesyPaticas.py::sanitizar_para_sheet`."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

try:
    import numpy as np  # type: ignore
    _NP_INT = (np.int64, np.int32)
    _NP_FLOAT = (np.float64, np.float32)
except Exception:  # pragma: no cover
    _NP_INT = ()
    _NP_FLOAT = ()

try:
    import pandas as pd  # type: ignore
    _PD_TS = (pd.Timestamp,)
except Exception:  # pragma: no cover
    _PD_TS = ()


def sanitizar_para_sheet(val: Any) -> Any:
    """Convierte tipos Python/NumPy/Pandas a primitivos seguros para Google Sheets."""
    if isinstance(val, _NP_INT):
        return int(val)
    if isinstance(val, _NP_FLOAT) or isinstance(val, float):
        return int(round(float(val)))
    if isinstance(val, _PD_TS) or isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    return val
