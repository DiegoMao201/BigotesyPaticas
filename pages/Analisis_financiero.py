import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# ==========================================================
# CENTRO DE CONTROL FINANCIERO (Nexus Executive Finance)
# ==========================================================

COLOR_PRIMARIO = "#187f77"
COLOR_SECUNDARIO = "#125e58"
COLOR_ACENTO = "#f5a641"
COLOR_FONDO = "#f8f9fa"
COLOR_BLANCO = "#ffffff"
COLOR_TEXTO = "#262730"

st.set_page_config(
    page_title="Centro de Control Financiero | Bigotes y Patitas",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    f"""
<style>
    .stApp {{ background-color: {COLOR_FONDO}; font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial; }}

    .hero {{
        background: linear-gradient(135deg, {COLOR_PRIMARIO} 0%, {COLOR_SECUNDARIO} 100%);
        color: white; padding: 22px 24px; border-radius: 16px;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.10);
        margin-bottom: 14px;
    }}
    .hero h1 {{ margin: 0; font-size: 1.8rem; font-weight: 900; }}
    .hero p {{ margin: 4px 0 0 0; opacity: 0.95; }}

    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 12px;
        margin: 12px 0 18px 0;
    }}
    .kpi {{
        background: {COLOR_BLANCO};
        border-radius: 14px;
        padding: 14px 14px;
        border-left: 5px solid {COLOR_ACENTO};
        box-shadow: 0 6px 18px rgba(0,0,0,0.05);
    }}
    .kpi .label {{ color: #64748b; font-size: 0.78rem; font-weight: 700; text-transform: uppercase; }}
    .kpi .value {{ color: {COLOR_TEXTO}; font-size: 1.18rem; font-weight: 900; margin-top: 4px; }}
    .kpi .delta {{ color: #64748b; font-size: 0.85rem; margin-top: 2px; }}

    .panel {{
        background: {COLOR_BLANCO};
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.05);
        border: 1px solid rgba(0,0,0,0.06);
    }}

    .badge {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-weight: 800;
        font-size: 0.78rem;
        background: rgba(245,166,65,0.18);
        color: #8a4b00;
        border: 1px solid rgba(245,166,65,0.35);
    }}
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================================
# UTILIDADES
# ==========================================================

def _money(x: float) -> str:
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return "$0"

def _pct(x: float, digits: int = 1) -> str:
    try:
        return f"{float(x) * 100:.{digits}f}%"
    except Exception:
        return "0.0%"

def _col_pick(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Retorna la primera columna que exista (case-insensitive, strip)."""
    if df is None or df.empty:
        return None
    norm = {c.strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand.strip().lower() in norm:
            return norm[cand.strip().lower()]
    return None

def _safe_datetime(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def _date_bounds(*series_list: pd.Series):
    mins = []
    maxs = []
    for s in series_list:
        try:
            s2 = pd.to_datetime(s, errors="coerce")
            mins.append(s2.min())
            maxs.append(s2.max())
        except Exception:
            pass
    mins = [m for m in mins if pd.notna(m)]
    maxs = [m for m in maxs if pd.notna(m)]
    if not mins or not maxs:
        hoy = pd.Timestamp.now().normalize()
        return hoy - pd.Timedelta(days=30), hoy
    return min(mins), max(maxs)

def _periodize(dt: pd.Series, freq: str) -> pd.Series:
    # freq: 'D', 'W', 'M'
    if freq == "D":
        return dt.dt.floor("D")
    if freq == "W":
        # semana iniciando lunes
        return (dt.dt.to_period("W-MON").dt.start_time)
    # mensual por defecto
    return dt.dt.to_period("M").dt.to_timestamp()

def _rolling_growth(series: pd.Series, periods: int = 3) -> float:
    """Crecimiento promedio reciente (para sugerir un g)."""
    s = series.dropna()
    if len(s) < periods + 1:
        return 0.0
    # crecimiento compuesto aproximado vs hace 'periods'
    s = s.sort_index()
    a = float(s.iloc[-periods-1])
    b = float(s.iloc[-1])
    if a <= 0:
        return 0.0
    return (b / a) ** (1 / periods) - 1

# ==========================================================
# CARGA DE DATOS DESDE SESSION_STATE (TU BASE REAL)
# ==========================================================

def cargar_datos():
    """Carga ventas/gastos/cierres desde st.session_state.db (si existe)."""
    if "db" not in st.session_state:
        st.error("Primero debes sincronizar los datos desde la app principal.")
        st.stop()

    df_ven = st.session_state.db.get("ven", pd.DataFrame()).copy()
    df_gas = st.session_state.db.get("gas", pd.DataFrame()).copy()
    df_cie = st.session_state.db.get("cie", pd.DataFrame()).copy()  # opcional

    return df_ven, df_gas, df_cie

def preparar_ventas(df_ven: pd.DataFrame) -> pd.DataFrame:
    df = df_ven.copy()
    if df.empty:
        return df

    col_fecha = _col_pick(df, ["Fecha"])
    if not col_fecha:
        return pd.DataFrame()

    df = _safe_datetime(df, col_fecha)
    df = df.rename(columns={col_fecha: "Fecha"})

    col_total = _col_pick(df, ["Total", "Monto", "Valor"])
    if col_total and col_total != "Total":
        df = df.rename(columns={col_total: "Total"})
    if "Total" not in df.columns:
        df["Total"] = 0.0
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0.0)

    # Costo (si existe)
    col_costo = _col_pick(df, ["Costo_Total", "Costo total", "Costo", "COGS"])
    if col_costo and col_costo != "Costo_Total":
        df = df.rename(columns={col_costo: "Costo_Total"})
    if "Costo_Total" not in df.columns:
        df["Costo_Total"] = 0.0
    df["Costo_Total"] = pd.to_numeric(df["Costo_Total"], errors="coerce").fillna(0.0)

    # Método de pago (si existe)
    col_pago = _col_pick(df, ["Metodo_Pago", "Método_Pago", "Metodo", "Pago"])
    if col_pago and col_pago != "Metodo_Pago":
        df = df.rename(columns={col_pago: "Metodo_Pago"})
    if "Metodo_Pago" not in df.columns:
        df["Metodo_Pago"] = "NoDef"

    # Cliente (si existe) -> para conteos
    col_cliente = _col_pick(df, ["Nombre_Cliente", "Cliente", "Nombre"])
    if col_cliente and col_cliente != "Nombre_Cliente":
        df = df.rename(columns={col_cliente: "Nombre_Cliente"})
    if "Nombre_Cliente" not in df.columns:
        df["Nombre_Cliente"] = "N/A"

    df = df[df["Fecha"].notna()].copy()
    return df

def preparar_gastos(df_gas: pd.DataFrame) -> pd.DataFrame:
    df = df_gas.copy()
    if df.empty:
        return df

    col_fecha = _col_pick(df, ["Fecha"])
    if not col_fecha:
        return pd.DataFrame()

    df = _safe_datetime(df, col_fecha)
    df = df.rename(columns={col_fecha: "Fecha"})

    col_monto = _col_pick(df, ["Monto", "Total", "Valor"])
    if col_monto and col_monto != "Monto":
        df = df.rename(columns={col_monto: "Monto"})
    if "Monto" not in df.columns:
        df["Monto"] = 0.0
    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)

    # Tipo gasto (en tu app principal es Tipo_Gasto)
    col_tipo = _col_pick(df, ["Tipo_Gasto", "Tipo", "tipo", "Tipo gasto"])
    if col_tipo and col_tipo != "Tipo_Gasto":
        df = df.rename(columns={col_tipo: "Tipo_Gasto"})
    if "Tipo_Gasto" not in df.columns:
        df["Tipo_Gasto"] = "Variable"

    # Categoría
    col_cat = _col_pick(df, ["Categoria", "Categoría", "Categoria_Gasto", "Category"])
    if col_cat and col_cat != "Categoria":
        df = df.rename(columns={col_cat: "Categoria"})
    if "Categoria" not in df.columns:
        df["Categoria"] = "Sin Categoría"
    df["Categoria"] = df["Categoria"].fillna("Sin Categoría").astype(str)

    # Método (para caja)
    col_pago = _col_pick(df, ["Metodo_Pago", "Método_Pago", "Metodo", "Pago"])
    if col_pago and col_pago != "Metodo_Pago":
        df = df.rename(columns={col_pago: "Metodo_Pago"})
    if "Metodo_Pago" not in df.columns:
        df["Metodo_Pago"] = "NoDef"

    df = df[df["Fecha"].notna()].copy()
    return df

def preparar_cierres(df_cie: pd.DataFrame) -> pd.DataFrame:
    df = df_cie.copy()
    if df.empty:
        return df

    # En tu hoja "Cierres" (cie) se guardan: Fecha, Hora, ... Saldo_Real, etc.
    col_fecha = _col_pick(df, ["Fecha"])
    if not col_fecha:
        return pd.DataFrame()

    df = _safe_datetime(df, col_fecha)
    df = df.rename(columns={col_fecha: "Fecha"})
    df = df[df["Fecha"].notna()].copy()

    # Normalizar Saldo_Real si existe
    if "Saldo_Real" in df.columns:
        df["Saldo_Real"] = pd.to_numeric(df["Saldo_Real"], errors="coerce").fillna(0.0)

    return df

def filtrar_por_fecha(df: pd.DataFrame, desde: pd.Timestamp, hasta: pd.Timestamp) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    if "Fecha" not in df.columns:
        return pd.DataFrame()
    return df[(df["Fecha"] >= desde) & (df["Fecha"] <= hasta)].copy()

# ==========================================================
# MOTORES: P&L, CAJA, FORECAST
# ==========================================================

def construir_pl(df_ven_f: pd.DataFrame, df_gas_f: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Estado de Resultados (P&L) agregado por período."""
    if (df_ven_f is None or df_ven_f.empty) and (df_gas_f is None or df_gas_f.empty):
        return pd.DataFrame()

    # Ventas
    if df_ven_f is not None and not df_ven_f.empty:
        v = df_ven_f.copy()
        v["Periodo"] = _periodize(v["Fecha"], freq)
        ven = v.groupby("Periodo", as_index=False).agg(
            Ventas=("Total", "sum"),
            Costo_Ventas=("Costo_Total", "sum"),
            Transacciones=("Total", "count"),
        )
    else:
        ven = pd.DataFrame(columns=["Periodo", "Ventas", "Costo_Ventas", "Transacciones"])

    # Gastos
    if df_gas_f is not None and not df_gas_f.empty:
        g = df_gas_f.copy()
        g["Periodo"] = _periodize(g["Fecha"], freq)
        g["Tipo_Gasto"] = g["Tipo_Gasto"].astype(str).str.strip().str.title()
        g["Es_Fijo"] = g["Tipo_Gasto"].isin(["Fijo", "Fija", "Fixed"])
        gas_all = g.groupby("Periodo", as_index=False)["Monto"].sum().rename(columns={"Monto": "Gastos"})
        gas_fx = g[g["Es_Fijo"]].groupby("Periodo", as_index=False)["Monto"].sum().rename(columns={"Monto": "Gastos_Fijos"})
        gas_vr = g[~g["Es_Fijo"]].groupby("Periodo", as_index=False)["Monto"].sum().rename(columns={"Monto": "Gastos_Variables"})
    else:
        gas_all = pd.DataFrame(columns=["Periodo", "Gastos"])
        gas_fx = pd.DataFrame(columns=["Periodo", "Gastos_Fijos"])
        gas_vr = pd.DataFrame(columns=["Periodo", "Gastos_Variables"])

    pl = ven.merge(gas_all, on="Periodo", how="outer").merge(gas_fx, on="Periodo", how="outer").merge(gas_vr, on="Periodo", how="outer")
    for c in ["Ventas", "Costo_Ventas", "Gastos", "Gastos_Fijos", "Gastos_Variables", "Transacciones"]:
        if c not in pl.columns:
            pl[c] = 0.0
        pl[c] = pd.to_numeric(pl[c], errors="coerce").fillna(0.0)

    pl = pl.sort_values("Periodo")
    pl["Utilidad_Bruta"] = pl["Ventas"] - pl["Costo_Ventas"]
    pl["Margen_Bruto_%"] = np.where(pl["Ventas"] > 0, pl["Utilidad_Bruta"] / pl["Ventas"], 0.0)
    pl["EBITDA"] = pl["Utilidad_Bruta"] - pl["Gastos"]
    pl["EBITDA_%"] = np.where(pl["Ventas"] > 0, pl["EBITDA"] / pl["Ventas"], 0.0)
    pl["Ticket_Prom"] = np.where(pl["Transacciones"] > 0, pl["Ventas"] / pl["Transacciones"], 0.0)

    return pl

def construir_caja(df_ven_f: pd.DataFrame, df_gas_f: pd.DataFrame, df_cie_f: pd.DataFrame, desde: pd.Timestamp, hasta: pd.Timestamp):
    """Modelo de caja simple (entrada/salida) con conciliación si hay cierres."""
    # Entradas por método
    ingresos = pd.DataFrame()
    if df_ven_f is not None and not df_ven_f.empty:
        ingresos = df_ven_f.groupby("Metodo_Pago", as_index=False)["Total"].sum().rename(columns={"Total": "Ingresos"})

    egresos = pd.DataFrame()
    if df_gas_f is not None and not df_gas_f.empty:
        egresos = df_gas_f.groupby("Metodo_Pago", as_index=False)["Monto"].sum().rename(columns={"Monto": "Egresos"})

    mix = ingresos.merge(egresos, on="Metodo_Pago", how="outer").fillna(0.0)
    mix["Neto"] = mix["Ingresos"] - mix["Egresos"]
    mix = mix.sort_values("Ingresos", ascending=False)

    # Caja estimada (si hay cierres)
    saldo_inicial = None
    saldo_final = None
    cierre_ref = None
    if df_cie_f is not None and not df_cie_f.empty and "Saldo_Real" in df_cie_f.columns:
        # saldo inicial: último cierre anterior al rango
        prev = df_cie_f[df_cie_f["Fecha"] < desde].sort_values("Fecha", ascending=False)
        if not prev.empty:
            saldo_inicial = float(prev.iloc[0]["Saldo_Real"])
        # saldo final: último cierre dentro del rango
        dentro = df_cie_f[(df_cie_f["Fecha"] >= desde) & (df_cie_f["Fecha"] <= hasta)].sort_values("Fecha", ascending=False)
        if not dentro.empty:
            saldo_final = float(dentro.iloc[0]["Saldo_Real"])
            cierre_ref = dentro.iloc[0]

    return mix, saldo_inicial, saldo_final, cierre_ref

def forecast_escenarios(pl_m: pd.DataFrame, meses: int, g_ventas: float, margen_obj: float, inflacion_gastos: float, gastos_fijos_base: float | None = None):
    """Proyección mensual basada en series históricas + supuestos."""
    if pl_m is None or pl_m.empty:
        return pd.DataFrame()

    hist = pl_m.copy().sort_values("Periodo")
    hist = hist[hist["Periodo"].notna()].copy()

    # último mes observado
    last_period = hist["Periodo"].max()
    last_sales = float(hist[hist["Periodo"] == last_period]["Ventas"].iloc[0]) if "Ventas" in hist.columns and not hist.empty else 0.0

    # baseline de gastos: últimos 3 meses promedio
    tail = hist.tail(3)
    base_gastos = float(tail["Gastos"].mean()) if "Gastos" in tail.columns and not tail.empty else 0.0
    base_fijos = float(tail["Gastos_Fijos"].mean()) if "Gastos_Fijos" in tail.columns and not tail.empty else 0.0
    base_vars = float(tail["Gastos_Variables"].mean()) if "Gastos_Variables" in tail.columns and not tail.empty else max(0.0, base_gastos - base_fijos)

    if gastos_fijos_base is not None:
        base_fijos = float(gastos_fijos_base)
        base_vars = max(0.0, base_gastos - base_fijos)

    # Proyección
    rows = []
    for i in range(1, meses + 1):
        periodo = (last_period + pd.offsets.MonthBegin(i)).to_pydatetime()
        ventas = last_sales * ((1.0 + g_ventas) ** i)
        utilidad_bruta = ventas * margen_obj
        cogs = ventas - utilidad_bruta

        # gastos crecen por inflación (aplica a todo por simplicidad)
        gastos_f = base_fijos * ((1.0 + inflacion_gastos) ** i)
        gastos_v = base_vars * ((1.0 + inflacion_gastos) ** i)
        gastos = gastos_f + gastos_v

        ebitda = utilidad_bruta - gastos

        rows.append(
            {
                "Periodo": pd.Timestamp(periodo),
                "Ventas_Proy": ventas,
                "Costo_Ventas_Proy": cogs,
                "Utilidad_Bruta_Proy": utilidad_bruta,
                "Gastos_Fijos_Proy": gastos_f,
                "Gastos_Variables_Proy": gastos_v,
                "Gastos_Proy": gastos,
                "EBITDA_Proy": ebitda,
                "EBITDA_%_Proy": (ebitda / ventas) if ventas > 0 else 0.0,
            }
        )

    return pd.DataFrame(rows)

# ==========================================================
# UI PRINCIPAL
# ==========================================================

def main():
    df_ven_raw, df_gas_raw, df_cie_raw = cargar_datos()

    df_ven = preparar_ventas(df_ven_raw)
    df_gas = preparar_gastos(df_gas_raw)
    df_cie = preparar_cierres(df_cie_raw)

    # Bounds de fechas
    min_dt, max_dt = _date_bounds(
        df_ven["Fecha"] if not df_ven.empty else pd.Series(dtype="datetime64[ns]"),
        df_gas["Fecha"] if not df_gas.empty else pd.Series(dtype="datetime64[ns]"),
        df_cie["Fecha"] if not df_cie.empty else pd.Series(dtype="datetime64[ns]"),
    )
    min_date = min_dt.date()
    max_date = max_dt.date()

    # Sidebar de control
    with st.sidebar:
        st.markdown("## 🎛️ Controles")
        st.caption("Ajusta el período, granularidad y supuestos de proyección.")
        st.divider()

        # Fechas
        desde = st.date_input("Desde", value=max(min_date, (max_dt - pd.Timedelta(days=90)).date()), min_value=min_date, max_value=max_date)
        hasta = st.date_input("Hasta", value=max_date, min_value=min_date, max_value=max_date)

        desde_dt = pd.to_datetime(desde)
        hasta_dt = pd.to_datetime(hasta) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

        freq = st.selectbox("Granularidad", ["Mensual", "Semanal", "Diaria"], index=0)
        freq_map = {"Mensual": "M", "Semanal": "W", "Diaria": "D"}
        freq_key = freq_map[freq]

        st.divider()
        st.markdown("## 🔮 Proyección (Escenarios)")
        meses_proj = st.slider("Meses a proyectar", 3, 18, 12)

        # Sugerencias automáticas de crecimiento basado en tendencia mensual
        pl_m_ref = construir_pl(
            filtrar_por_fecha(df_ven, min_dt, max_dt),
            filtrar_por_fecha(df_gas, min_dt, max_dt),
            "M",
        )
        g_sug = _rolling_growth(pl_m_ref.set_index("Periodo")["Ventas"] if not pl_m_ref.empty else pd.Series(dtype=float), periods=3)

        g_ventas = st.number_input("Crecimiento mensual ventas", value=float(max(-0.3, min(0.5, g_sug))), step=0.01, format="%.2f")
        margen_obj = st.number_input("Margen bruto objetivo", value=float(pl_m_ref["Margen_Bruto_%"].tail(3).mean() if not pl_m_ref.empty else 0.30), step=0.01, format="%.2f")
        inflacion_gastos = st.number_input("Inflación mensual gastos", value=0.01, step=0.01, format="%.2f")

        # Caja inicial (si no hay cierres)
        caja_inicial = st.number_input("Caja inicial (si no hay cierre)", value=40_000_000.0, step=100_000.0)

    # Filtro por fecha
    df_ven_f = filtrar_por_fecha(df_ven, desde_dt, hasta_dt)
    df_gas_f = filtrar_por_fecha(df_gas, desde_dt, hasta_dt)
    df_cie_f = filtrar_por_fecha(df_cie, min_dt, max_dt)  # cierres completos para buscar previos

    # Hero
    st.markdown(
        f"""
<div class="hero">
  <div>
    <h1>Centro de Control Financiero</h1>
    <p>Panel ejecutivo: P&L, Caja, Alertas y Proyección • <span class="badge">{desde_dt.date()} → {hasta_dt.date()}</span></p>
  </div>
  <div style="text-align:right;">
    <div style="font-weight:900; font-size: 1.1rem;">Bigotes y Patitas</div>
    <div style="opacity:0.9;">Nexus Finance</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Construir P&L
    pl = construir_pl(df_ven_f, df_gas_f, freq_key)
    pl_m = construir_pl(df_ven_f, df_gas_f, "M")

    # KPIs principales
    ventas = float(df_ven_f["Total"].sum()) if not df_ven_f.empty else 0.0
    cogs = float(df_ven_f["Costo_Total"].sum()) if not df_ven_f.empty else 0.0
    gastos = float(df_gas_f["Monto"].sum()) if not df_gas_f.empty else 0.0
    utilidad_bruta = ventas - cogs
    margen_bruto = (utilidad_bruta / ventas) if ventas > 0 else 0.0
    ebitda = utilidad_bruta - gastos
    ebitda_pct = (ebitda / ventas) if ventas > 0 else 0.0
    tx = int(df_ven_f.shape[0]) if not df_ven_f.empty else 0
    ticket = (ventas / tx) if tx > 0 else 0.0

    # Caja / conciliación
    mix, saldo_ini, saldo_fin, cierre_ref = construir_caja(df_ven_f, df_gas_f, df_cie_f, desde_dt, hasta_dt)
    cash_sales = float(df_ven_f[df_ven_f["Metodo_Pago"] == "Efectivo"]["Total"].sum()) if not df_ven_f.empty else 0.0
    cash_exp = float(df_gas_f[df_gas_f["Metodo_Pago"] == "Efectivo"]["Monto"].sum()) if not df_gas_f.empty else 0.0

    # Caja estimada (si hay saldo inicial, simula delta efectivo)
    caja_est = None
    if saldo_ini is not None:
        caja_est = saldo_ini + cash_sales - cash_exp

    # Runway (meses) usando EBITDA mensual promedio reciente
    ebitda_m = 0.0
    if not pl_m.empty:
        ebitda_m = float(pl_m.tail(3)["EBITDA"].mean())
    burn = -ebitda_m if ebitda_m < 0 else 0.0
    caja_base_runway = saldo_fin if saldo_fin is not None else (caja_est if caja_est is not None else float(caja_inicial))
    runway_meses = (caja_base_runway / burn) if burn > 0 else np.inf

    # Grid de KPIs (tipo ejecutivo)
    st.markdown(
        f"""
<div class="kpi-grid">
  <div class="kpi"><div class="label">Ventas</div><div class="value">{_money(ventas)}</div><div class="delta">Rango seleccionado</div></div>
  <div class="kpi"><div class="label">Utilidad Bruta</div><div class="value">{_money(utilidad_bruta)}</div><div class="delta">Margen: {_pct(margen_bruto)}</div></div>
  <div class="kpi"><div class="label">Gastos</div><div class="value">{_money(gastos)}</div><div class="delta">Fijos+Variables</div></div>
  <div class="kpi"><div class="label">EBITDA</div><div class="value">{_money(ebitda)}</div><div class="delta">EBITDA: {_pct(ebitda_pct)}</div></div>
  <div class="kpi"><div class="label">Ticket Promedio</div><div class="value">{_money(ticket)}</div><div class="delta">Transacciones: {tx}</div></div>
  <div class="kpi"><div class="label">Caja / Runway</div><div class="value">{_money(caja_base_runway)}</div><div class="delta">Runway: {"∞" if runway_meses == np.inf else f"{runway_meses:.1f} meses"}</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["📌 Resumen Ejecutivo", "📈 P&L (Estado de Resultados)", "💵 Caja & Mix de Pagos", "🔮 Proyección & Escenarios", "🚨 Alertas & Recomendaciones", "⬇️ Exportar"])

    # ==========================================================
    # TAB 1: RESUMEN
    # ==========================================================
    with tabs[0]:
        cA, cB = st.columns([1.15, 0.85], gap="large")

        with cA:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.subheader("Tendencia (Ventas vs Gastos vs EBITDA)")

            if pl.empty:
                st.info("No hay datos suficientes en el rango.")
            else:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=pl["Periodo"], y=pl["Ventas"], mode="lines+markers", name="Ventas", line=dict(color=COLOR_PRIMARIO, width=3)))
                fig.add_trace(go.Scatter(x=pl["Periodo"], y=pl["Gastos"], mode="lines+markers", name="Gastos", line=dict(color=COLOR_ACENTO, width=3)))
                fig.add_trace(go.Bar(x=pl["Periodo"], y=pl["EBITDA"], name="EBITDA", marker_color="#64748b", opacity=0.55))
                fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

        with cB:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.subheader("Radiografía rápida")

            # Mix de gastos por categoría (top)
            if df_gas_f is not None and not df_gas_f.empty:
                top_cat = df_gas_f.groupby("Categoria", as_index=False)["Monto"].sum().sort_values("Monto", ascending=False).head(8)
                fig2 = px.bar(top_cat, x="Monto", y="Categoria", orientation="h", title="Top categorías de gasto", color_discrete_sequence=[COLOR_ACENTO])
                fig2.update_layout(height=330, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Sin gastos en el rango.")

            st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # TAB 2: P&L
    # ==========================================================
    with tabs[1]:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Estado de Resultados (P&L)")

        if pl.empty:
            st.info("No hay datos para construir P&L.")
        else:
            df_pl_view = pl.copy()
            df_pl_view["Margen_Bruto_%"] = (df_pl_view["Margen_Bruto_%"] * 100).round(1)
            df_pl_view["EBITDA_%"] = (df_pl_view["EBITDA_%"] * 100).round(1)

            st.dataframe(
                df_pl_view[["Periodo", "Ventas", "Costo_Ventas", "Utilidad_Bruta", "Margen_Bruto_%", "Gastos", "EBITDA", "EBITDA_%", "Transacciones", "Ticket_Prom"]],
                use_container_width=True,
                hide_index=True,
            )

            # Waterfall último período
            last = pl.tail(1).iloc[0]
            wf = go.Figure(
                go.Waterfall(
                    name="P&L",
                    orientation="v",
                    measure=["relative", "relative", "relative", "total"],
                    x=["Ventas", "Costo Ventas", "Gastos", "EBITDA"],
                    y=[last["Ventas"], -last["Costo_Ventas"], -last["Gastos"], last["EBITDA"]],
                    text=[_money(last["Ventas"]), _money(-last["Costo_Ventas"]), _money(-last["Gastos"]), _money(last["EBITDA"])],
                    connector={"line": {"color": "rgba(0,0,0,0.2)"}},
                )
            )
            wf.update_layout(title="Waterfall del último período", height=340, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(wf, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # TAB 3: CAJA & PAGOS
    # ==========================================================
    with tabs[2]:
        c1, c2 = st.columns([1, 1], gap="large")

        with c1:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.subheader("Mix de pagos (Ingresos/Egresos por método)")
            if mix is None or mix.empty:
                st.info("No hay movimientos suficientes.")
            else:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=mix["Metodo_Pago"], y=mix["Ingresos"], name="Ingresos", marker_color=COLOR_PRIMARIO))
                fig.add_trace(go.Bar(x=mix["Metodo_Pago"], y=mix["Egresos"], name="Egresos", marker_color=COLOR_ACENTO))
                fig.update_layout(barmode="group", height=360, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(mix, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.subheader("Conciliación de Caja (si hay cierres)")

            if saldo_ini is None and saldo_fin is None:
                st.info("No detecté cierres en `db['cie']`. Usaré caja inicial manual para runway.")
            else:
                st.write(f"**Saldo inicial (previo):** {_money(saldo_ini) if saldo_ini is not None else 'N/D'}")
                st.write(f"**Ventas Efectivo:** {_money(cash_sales)}")
                st.write(f"**Gastos Efectivo:** {_money(cash_exp)}")
                if caja_est is not None:
                    st.write(f"**Caja estimada (sin depósitos a bancos):** {_money(caja_est)}")
                if saldo_fin is not None:
                    st.write(f"**Último Saldo Real (cierre):** {_money(saldo_fin)}")

                if cierre_ref is not None:
                    st.caption("Cierre de referencia (último dentro del rango):")
                    st.json(cierre_ref.to_dict())

            st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # TAB 4: FORECAST
    # ==========================================================
    with tabs[3]:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Proyección Ejecutiva (Ventas, Gastos, EBITDA)")

        if pl_m.empty:
            st.info("Necesito al menos datos mensuales para proyectar.")
        else:
            # Limitar margen objetivo
            margen_obj_clamped = float(max(0.05, min(0.85, margen_obj)))

            proj = forecast_escenarios(
                pl_m=pl_m,
                meses=meses_proj,
                g_ventas=float(g_ventas),
                margen_obj=margen_obj_clamped,
                inflacion_gastos=float(inflacion_gastos),
            )

            if proj.empty:
                st.info("No se pudo generar proyección.")
            else:
                # Combinar histórico + proyección para gráfico
                hist = pl_m[["Periodo", "Ventas", "Gastos", "EBITDA"]].copy()
                hist = hist.rename(columns={"Ventas": "Ventas_Proy", "Gastos": "Gastos_Proy", "EBITDA": "EBITDA_Proy"})
                hist["Tipo"] = "Histórico"
                proj2 = proj[["Periodo", "Ventas_Proy", "Gastos_Proy", "EBITDA_Proy"]].copy()
                proj2["Tipo"] = "Proyección"
                comb = pd.concat([hist, proj2], ignore_index=True).sort_values("Periodo")

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=comb["Periodo"], y=comb["Ventas_Proy"], mode="lines+markers", name="Ventas", line=dict(color=COLOR_PRIMARIO, width=3)))
                fig.add_trace(go.Scatter(x=comb["Periodo"], y=comb["Gastos_Proy"], mode="lines+markers", name="Gastos", line=dict(color=COLOR_ACENTO, width=3)))
                fig.add_trace(go.Bar(x=comb["Periodo"], y=comb["EBITDA_Proy"], name="EBITDA", marker_color="#64748b", opacity=0.45))
                fig.add_vline(x=pl_m["Periodo"].max(), line_width=2, line_dash="dash", line_color="rgba(0,0,0,0.35)")
                fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)

                cA, cB, cC = st.columns(3)
                with cA:
                    st.metric("Supuesto: Crec. mensual ventas", f"{g_ventas*100:.1f}%")
                with cB:
                    st.metric("Supuesto: Margen bruto objetivo", f"{margen_obj_clamped*100:.1f}%")
                with cC:
                    st.metric("Supuesto: Inflación gastos", f"{inflacion_gastos*100:.1f}%")

                st.markdown("#### Tabla de proyección")
                view = proj.copy()
                view["Margen_Bruto_%_Proy"] = np.where(view["Ventas_Proy"] > 0, view["Utilidad_Bruta_Proy"] / view["Ventas_Proy"], 0.0)
                view["Margen_Bruto_%_Proy"] = (view["Margen_Bruto_%_Proy"] * 100).round(1)
                view["EBITDA_%_Proy"] = (view["EBITDA_%_Proy"] * 100).round(1)

                st.dataframe(
                    view[
                        [
                            "Periodo",
                            "Ventas_Proy",
                            "Costo_Ventas_Proy",
                            "Utilidad_Bruta_Proy",
                            "Margen_Bruto_%_Proy",
                            "Gastos_Proy",
                            "EBITDA_Proy",
                            "EBITDA_%_Proy",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # TAB 5: ALERTAS
    # ==========================================================
    with tabs[4]:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Alertas & Recomendaciones (automáticas)")

        alerts = []

        # Alertas de margen
        if ventas > 0 and margen_bruto < 0.25:
            alerts.append(("🟠 Margen bajo", f"Margen bruto actual {_pct(margen_bruto)}. Revisa precios/costos y descuentos."))
        if ventas > 0 and ebitda_pct < 0:
            alerts.append(("🔴 EBITDA negativo", f"EBITDA {_money(ebitda)} ({_pct(ebitda_pct)}). Estás perdiendo caja en el período."))

        # Spike de gastos vs promedio
        if not pl_m.empty and len(pl_m) >= 4:
            g_last = float(pl_m.tail(1)["Gastos"].iloc[0])
            g_avg = float(pl_m.tail(4)["Gastos"].mean())
            if g_avg > 0 and (g_last / g_avg) > 1.35:
                alerts.append(("🟠 Pico de gastos", f"Último mes gastaste {_money(g_last)} vs promedio {_money(g_avg)} (↑{(g_last/g_avg-1)*100:.0f}%)."))

        # Concentración de gastos por categoría
        if df_gas_f is not None and not df_gas_f.empty:
            by_cat = df_gas_f.groupby("Categoria", as_index=False)["Monto"].sum().sort_values("Monto", ascending=False)
            if not by_cat.empty and gastos > 0:
                share = float(by_cat.iloc[0]["Monto"]) / gastos
                if share > 0.45:
                    alerts.append(("🟡 Concentración de gasto", f"'{by_cat.iloc[0]['Categoria']}' representa {share*100:.0f}% de tus gastos del período."))

        # Runway
        if runway_meses != np.inf and runway_meses < 3:
            alerts.append(("🔴 Runway crítico", f"Con el burn actual, runway estimado: {runway_meses:.1f} meses."))

        if not alerts:
            st.success("Sin alertas críticas detectadas con los umbrales actuales.")
        else:
            for titulo, detalle in alerts:
                st.warning(f"**{titulo}** — {detalle}")

        st.markdown("---")
        st.markdown("#### Acciones recomendadas (1-click mental)")
        acciones = []

        if ventas > 0 and margen_bruto < 0.30:
            acciones.append("Revisar lista de precios: subir precios en SKUs con alta rotación o costo subiendo.")
            acciones.append("Auditar compras: validar prorrateos (transporte/descuentos) y costo neto.")
        if gastos > 0:
            acciones.append("Recortar gastos variables no esenciales esta semana (top 3 categorías).")
        if cash_sales > 0 and saldo_fin is None:
            acciones.append("Registrar cierre de caja diariamente (para conciliación real y control de fugas).")

        if acciones:
            for a in acciones:
                st.write(f"- {a}")
        else:
            st.write("- Mantener disciplina: cierres diarios + revisión semanal de margen y top gastos.")

        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # TAB 6: EXPORTAR
    # ==========================================================
    with tabs[5]:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Exportar (para contador / junta / archivo)")

        exp = {}

        exp["P&L_" + ("Mensual" if freq_key == "M" else "Periodo")] = pl.copy() if not pl.empty else pd.DataFrame()
        exp["P&L_Mensual_Base"] = pl_m.copy() if not pl_m.empty else pd.DataFrame()
        exp["Mix_Pagos"] = mix.copy() if mix is not None and not mix.empty else pd.DataFrame()

        # Excel en memoria
        output = None
        try:
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                for name, df in exp.items():
                    if df is None or df.empty:
                        continue
                    df2 = df.copy()
                    df2.to_excel(writer, sheet_name=name[:31], index=False)
            output.seek(0)
        except Exception as e:
            st.error(f"No pude generar Excel: {e}")

        if output:
            st.download_button(
                "⬇️ Descargar Reporte Financiero (Excel)",
                data=output,
                file_name=f"Reporte_Financiero_{desde_dt.date()}_a_{hasta_dt.date()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        st.caption("Incluye P&L, P&L mensual base, y mix de pagos/egresos. (Se puede extender a inventario y compras si lo conectamos.)")
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()