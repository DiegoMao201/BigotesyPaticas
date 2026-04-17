from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

import gspread
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import streamlit as st


COLOR_PRIMARIO = "#0f766e"
COLOR_SECUNDARIO = "#164e63"
COLOR_ACENTO = "#f59e0b"
COLOR_CORAL = "#dc6b4c"
COLOR_FONDO = "#f4f1ea"
COLOR_PANEL = "#fffdf8"
COLOR_TEXTO = "#1f2937"
COLOR_MUTED = "#6b7280"
COLOR_OK = "#187f77"
COLOR_ALERTA = "#b45309"
COLOR_PELIGRO = "#b91c1c"


st.set_page_config(
    page_title="Producto 360 | Bigotes y Paticas",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Source+Sans+3:wght@400;600;700&display=swap');

.stApp {{
    background:
        radial-gradient(circle at top left, rgba(245, 158, 11, 0.14), transparent 28%),
        radial-gradient(circle at top right, rgba(15, 118, 110, 0.12), transparent 32%),
        linear-gradient(180deg, #faf7f2 0%, {COLOR_FONDO} 100%);
    color: {COLOR_TEXTO};
}}

html, body, [class*="css"] {{
    font-family: 'Source Sans 3', sans-serif;
}}

h1, h2, h3, h4 {{
    font-family: 'Space Grotesk', sans-serif;
    color: {COLOR_TEXTO};
}}

.hero-360 {{
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, {COLOR_PRIMARIO} 0%, {COLOR_SECUNDARIO} 52%, #082f49 100%);
    color: white;
    border-radius: 24px;
    padding: 28px 30px;
    box-shadow: 0 22px 52px rgba(8, 47, 73, 0.22);
    margin-bottom: 18px;
}}

.hero-360::after {{
    content: "";
    position: absolute;
    inset: auto -40px -70px auto;
    width: 240px;
    height: 240px;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(245, 158, 11, 0.38) 0%, rgba(245, 158, 11, 0.08) 45%, transparent 70%);
}}

.eyebrow {{
    text-transform: uppercase;
    letter-spacing: .14em;
    font-size: .76rem;
    font-weight: 700;
    opacity: .78;
}}

.hero-title {{
    font-size: 2.15rem;
    line-height: 1.05;
    font-weight: 700;
    margin: .3rem 0 .5rem 0;
}}

.hero-sub {{
    font-size: 1.02rem;
    opacity: .92;
    max-width: 980px;
}}

.chip-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 14px;
}}

.chip {{
    background: rgba(255,255,255,0.14);
    color: white;
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 999px;
    padding: 7px 12px;
    font-size: .86rem;
    font-weight: 600;
}}

.section-card {{
    background: rgba(255,255,255,0.86);
    border: 1px solid rgba(15, 23, 42, 0.06);
    border-radius: 20px;
    padding: 18px;
    box-shadow: 0 14px 38px rgba(15, 23, 42, 0.07);
}}

.metric-grid {{
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
    margin: 10px 0 18px 0;
}}

.metric-card-360 {{
    background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(255,252,246,0.98) 100%);
    border: 1px solid rgba(15,23,42,0.06);
    border-radius: 18px;
    padding: 16px 14px;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
}}

.metric-label-360 {{
    color: {COLOR_MUTED};
    font-size: .78rem;
    text-transform: uppercase;
    letter-spacing: .06em;
    font-weight: 700;
}}

.metric-value-360 {{
    color: {COLOR_TEXTO};
    font-size: 1.38rem;
    font-weight: 800;
    margin-top: 6px;
}}

.metric-foot-360 {{
    color: {COLOR_MUTED};
    font-size: .85rem;
    margin-top: 4px;
}}

.alert-card {{
    border-radius: 18px;
    padding: 14px 16px;
    border: 1px solid rgba(0,0,0,0.06);
    margin-bottom: 10px;
}}

.alert-ok {{ background: rgba(24, 127, 119, 0.09); border-color: rgba(24, 127, 119, 0.20); }}
.alert-warn {{ background: rgba(245, 158, 11, 0.10); border-color: rgba(180, 83, 9, 0.22); }}
.alert-bad {{ background: rgba(185, 28, 28, 0.08); border-color: rgba(185, 28, 28, 0.18); }}

.alert-title {{
    font-weight: 800;
    margin-bottom: 4px;
    color: {COLOR_TEXTO};
}}

.alert-body {{
    color: {COLOR_MUTED};
}}

.note-card {{
    background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(252,249,243,0.98) 100%);
    border: 1px solid rgba(15,23,42,0.06);
    border-radius: 18px;
    padding: 16px 18px;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
    margin: 8px 0 14px 0;
}}

.note-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    color: {COLOR_TEXTO};
    margin-bottom: 6px;
}}

.note-body {{
    color: {COLOR_MUTED};
    line-height: 1.45;
}}

.mini-list {{
    margin: 0;
    padding-left: 18px;
    color: {COLOR_MUTED};
}}

.mini-list li {{
    margin-bottom: 5px;
}}

div[data-testid="stMetric"] {{
    background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(255,252,246,0.98) 100%);
    border: 1px solid rgba(15,23,42,0.06);
    padding: 12px 14px;
    border-radius: 18px;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 10px;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 999px;
    background: rgba(255,255,255,0.65);
    border: 1px solid rgba(15,23,42,0.06);
    padding: 10px 16px;
    font-weight: 700;
}}

.stButton>button {{
    border-radius: 14px;
    border: 1px solid rgba(15,23,42,0.06);
    font-weight: 700;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
}}

@media (max-width: 1200px) {{
    .metric-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
}}

@media (max-width: 720px) {{
    .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .hero-title {{ font-size: 1.7rem; }}
}}
</style>
""",
    unsafe_allow_html=True,
)


def money_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (np.integer, int)):
        return float(val)
    if isinstance(val, (np.floating, float)):
        try:
            if np.isnan(val) or np.isinf(val):
                return 0.0
        except Exception:
            return 0.0
        return float(val)

    s = str(val).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return 0.0

    neg = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    s = s.strip("()")
    s = s.replace("$", "").replace("COP", "").replace("cop", "").replace(" ", "")
    s = re.sub(r"[^0-9,\.\-]", "", s)
    s = s.lstrip("-")
    if not s:
        return 0.0

    if "," in s and "." in s:
        decimal_sep = "," if s.rfind(",") > s.rfind(".") else "."
        thousand_sep = "." if decimal_sep == "," else ","
        s = s.replace(thousand_sep, "")
        if decimal_sep == ",":
            s = s.replace(",", ".")
    elif s.count(",") > 1:
        s = s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif "," in s:
        left, right = s.rsplit(",", 1)
        s = f"{left}.{right}" if len(right) <= 2 else left + right
    elif "." in s:
        left, right = s.rsplit(".", 1)
        s = f"{left}.{right}" if len(right) <= 2 else left + right

    try:
        out = float(s)
    except Exception:
        out = float(re.sub(r"[^0-9]", "", s) or 0)
    return -out if neg else out


def money_int(val) -> int:
    return int(round(money_float(val)))


def normalizar_id_producto(id_prod):
    if pd.isna(id_prod) or str(id_prod).strip() == "":
        return "SIN_ID"
    val = str(id_prod).strip().upper()
    val = val.replace(".", "").replace(",", "").replace("\t", "").replace("\n", "").lstrip("0")
    return val if val else "SIN_ID"


def safe_google_op(func, *args, **kwargs):
    wait = 2
    for attempt in range(5):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e).lower() or "quota" in str(e).lower():
                if attempt < 4:
                    import time
                    time.sleep(wait)
                    wait *= 2
                    continue
            raise e


@st.cache_resource(ttl=900)
def conectar_db():
    gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
    return gc.open_by_url(st.secrets["SHEET_URL"])


def get_ws_safe(sh, name: str):
    try:
        return sh.worksheet(name)
    except Exception:
        return None


def ws_to_df(ws, defaults: dict | None = None) -> pd.DataFrame:
    if ws is None:
        df = pd.DataFrame()
    else:
        records = safe_google_op(ws.get_all_records)
        df = pd.DataFrame(records)
    defaults = defaults or {}
    if df.empty:
        return pd.DataFrame(columns=list(defaults.keys()))
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val
    return df


@st.cache_data(ttl=300)
def cargar_datos():
    sh = conectar_db()
    df_inv = ws_to_df(get_ws_safe(sh, "Inventario"), {
        "Producto_UID": "", "ID_Producto": "", "ID_Producto_Norm": "", "Nombre": "",
        "Stock": 0.0, "Costo": 0.0, "Precio": 0.0, "Categoria": "", "Iva": 0.0,
    })
    df_ven = ws_to_df(get_ws_safe(sh, "Ventas"), {
        "ID_Venta": "", "Fecha": "", "Nombre_Cliente": "", "Metodo_Pago": "",
        "Total": 0.0, "Items": "", "Items_Detalle": "", "Costo_Total": 0.0, "Mascota": "",
        "Estado_Envio": "", "Direccion_Envio": "", "Direccion": "", "Banco_Destino": "",
        "Estado_Pago": "", "Abono_Recibido": 0.0, "Saldo_Pendiente": 0.0,
        "Fecha_Promesa_Pago": "", "Nota_Pago": "", "Items_JSON": "",
    })
    df_hist = ws_to_df(get_ws_safe(sh, "Historial_Recepciones"), {
        "Fecha": "", "Folio": "", "Proveedor": "", "Recepcion_ID": "", "ID_Proveedor": "",
        "Producto_UID": "", "SKU_Interno": "", "SKU_Proveedor": "", "Nombre_Producto": "",
        "Cantidad_Pack": 0.0, "Factor_Pack": 1.0, "Unidades": 0.0, "Costo_Unitario": 0.0,
        "Costo_Total": 0.0, "Precio_Unitario": 0.0, "IVA_Porcentaje": 0.0, "Origen": "",
    })
    df_map = ws_to_df(get_ws_safe(sh, "Maestro_Proveedores"), {
        "Producto_UID": "", "SKU_Interno": "", "Nombre_Proveedor": "", "SKU_Proveedor": "",
        "Factor_Pack": 1.0, "Costo_Proveedor": 0.0, "Ultima_Actualizacion": "", "Ultimo_IVA": 0.0,
    })

    if not df_inv.empty:
        df_inv["ID_Producto_Norm"] = np.where(
            df_inv["ID_Producto_Norm"].astype(str).str.strip().eq(""),
            df_inv["ID_Producto"].apply(normalizar_id_producto),
            df_inv["ID_Producto_Norm"].apply(normalizar_id_producto),
        )
        for col in ["Stock", "Costo", "Precio", "Iva"]:
            if col in df_inv.columns:
                df_inv[col] = df_inv[col].apply(money_float)

    if not df_hist.empty:
        df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"], errors="coerce")
        for col in ["Cantidad_Pack", "Factor_Pack", "Unidades", "Costo_Unitario", "Costo_Total", "Precio_Unitario", "IVA_Porcentaje"]:
            if col in df_hist.columns:
                df_hist[col] = df_hist[col].apply(money_float)
        df_hist["SKU_Interno_Norm"] = df_hist["SKU_Interno"].apply(normalizar_id_producto)

    if not df_ven.empty:
        df_ven["Fecha"] = pd.to_datetime(df_ven["Fecha"], errors="coerce")
        for col in ["Total", "Costo_Total"]:
            if col in df_ven.columns:
                df_ven[col] = df_ven[col].apply(money_float)

    if not df_map.empty:
        df_map["SKU_Interno_Norm"] = df_map["SKU_Interno"].apply(normalizar_id_producto)
        if "Costo_Proveedor" in df_map.columns:
            df_map["Costo_Proveedor"] = df_map["Costo_Proveedor"].apply(money_float)
        if "Factor_Pack" in df_map.columns:
            df_map["Factor_Pack"] = pd.to_numeric(df_map["Factor_Pack"], errors="coerce").fillna(1.0)

    return df_inv, df_ven, df_hist, df_map


def parse_json_list(raw):
    if isinstance(raw, list):
        return raw
    if raw is None:
        return []
    txt = str(raw).strip()
    if not txt:
        return []
    try:
        data = json.loads(txt)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def parse_items_text(items_txt: str):
    items = []
    for part in str(items_txt or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "x " in part:
            try:
                cantidad, nombre = part.split("x ", 1)
                qty = money_float(cantidad.replace("x", ""))
                items.append({"Nombre": nombre.strip(), "Cantidad": qty if qty > 0 else 1.0})
                continue
            except Exception:
                pass
        items.append({"Nombre": part, "Cantidad": 1.0})
    return items


def coalesce_number(*values):
    for val in values:
        num = money_float(val)
        if num > 0:
            return num
    return 0.0


def expandir_ventas(df_ven: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if df_ven is None or df_ven.empty:
        return pd.DataFrame()

    for _, sale in df_ven.iterrows():
        fecha = sale.get("Fecha")
        venta_total = money_float(sale.get("Total", 0))
        costo_total = money_float(sale.get("Costo_Total", 0))
        detalles = parse_json_list(sale.get("Items_Detalle", ""))
        if not detalles:
            detalles = parse_items_text(sale.get("Items", ""))
        if not detalles:
            continue

        total_lineas = len(detalles)
        for item in detalles:
            qty = money_float(item.get("Cantidad", item.get("cantidad", item.get("qty", 0))))
            qty = qty if qty > 0 else 1.0
            precio_unit = coalesce_number(item.get("Precio_Unitario"), item.get("Precio"), item.get("precio_unitario"), item.get("precio"))
            descuento_unit = coalesce_number(item.get("Descuento_Unitario"), item.get("Descuento"), item.get("descuento_unitario"), item.get("descuento"))
            costo_unit = coalesce_number(item.get("Costo_Unitario"), item.get("Costo"), item.get("costo_unitario"), item.get("costo"))
            subtotal_linea = coalesce_number(item.get("Subtotal_Linea"), item.get("Subtotal"), item.get("subtotal_linea"), item.get("subtotal"))
            fuente_detalle = "Exacto"

            if subtotal_linea <= 0 and precio_unit > 0:
                subtotal_linea = max(precio_unit - descuento_unit, 0.0) * qty

            if total_lineas == 1:
                if subtotal_linea <= 0 and venta_total > 0:
                    subtotal_linea = venta_total
                if precio_unit <= 0 and subtotal_linea > 0:
                    precio_unit = subtotal_linea / qty
                if costo_unit <= 0 and costo_total > 0:
                    costo_unit = costo_total / qty
                if fuente_detalle != "Exacto" or (precio_unit > 0 and costo_unit > 0):
                    fuente_detalle = "Exacto" if any(k in item for k in ["Precio_Unitario", "Precio", "Costo_Unitario", "Costo"]) else "Inferido de venta de una sola línea"
            elif precio_unit <= 0 and subtotal_linea > 0:
                precio_unit = subtotal_linea / qty
                fuente_detalle = "Parcial"
            elif precio_unit <= 0 or costo_unit <= 0:
                fuente_detalle = "Histórico sin detalle unitario"

            costo_total_linea = costo_unit * qty if costo_unit > 0 else np.nan
            ingreso_linea = subtotal_linea if subtotal_linea > 0 else np.nan
            margen_linea = ingreso_linea - costo_total_linea if pd.notna(ingreso_linea) and pd.notna(costo_total_linea) else np.nan

            rows.append({
                "Fecha": fecha,
                "ID_Venta": str(sale.get("ID_Venta", "")).strip(),
                "Producto_UID": str(item.get("Producto_UID", "")).strip(),
                "ID_Producto": str(item.get("ID", item.get("ID_Producto", ""))).strip(),
                "ID_Producto_Norm": normalizar_id_producto(item.get("ID_Producto_Norm", item.get("ID", item.get("ID_Producto", "")))),
                "Nombre_Producto": str(item.get("Nombre", item.get("Nombre_Producto", ""))).strip(),
                "Cantidad": qty,
                "Precio_Unitario": precio_unit if precio_unit > 0 else np.nan,
                "Descuento_Unitario": descuento_unit if descuento_unit > 0 else 0.0,
                "Ingreso_Linea": ingreso_linea,
                "Costo_Unitario": costo_unit if costo_unit > 0 else np.nan,
                "Costo_Total_Linea": costo_total_linea,
                "Margen_Linea": margen_linea,
                "Nombre_Cliente": str(sale.get("Nombre_Cliente", "")).strip(),
                "Mascota": str(sale.get("Mascota", "")).strip(),
                "Metodo_Pago": str(sale.get("Metodo_Pago", "")).strip(),
                "Estado_Envio": str(sale.get("Estado_Envio", "")).strip(),
                "Detalle_Fuente": fuente_detalle,
            })

    out = pd.DataFrame(rows)
    if not out.empty:
        out["Fecha"] = pd.to_datetime(out["Fecha"], errors="coerce")
    return out


def filtrar_producto(df: pd.DataFrame, producto_uid: str, sku_norm: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    mask = pd.Series(False, index=df.index)
    if producto_uid and "Producto_UID" in df.columns:
        mask = mask | (df["Producto_UID"].astype(str).str.strip() == producto_uid)
    if sku_norm:
        if "ID_Producto_Norm" in df.columns:
            mask = mask | (df["ID_Producto_Norm"].astype(str).apply(normalizar_id_producto) == sku_norm)
        if "SKU_Interno_Norm" in df.columns:
            mask = mask | (df["SKU_Interno_Norm"].astype(str).apply(normalizar_id_producto) == sku_norm)
    return df[mask].copy()


def money_fmt(val):
    return f"${money_float(val):,.0f}"


def qty_fmt(val):
    q = money_float(val)
    return f"{int(q):,}" if float(q).is_integer() else f"{q:,.2f}"


def pct_fmt(val):
    try:
        return f"{float(val) * 100:.1f}%"
    except Exception:
        return "0.0%"


def badge(text: str) -> str:
    return f'<span class="chip">{text}</span>'


def render_metric_grid(metrics: list[dict]):
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, item in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-card-360">
                    <div class="metric-label-360">{item['label']}</div>
                    <div class="metric-value-360">{item['value']}</div>
                    <div class="metric-foot-360">{item.get('foot', '')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_note(title: str, body: str):
    st.markdown(
        f"""
        <div class="note-card">
            <div class="note-title">{title}</div>
            <div class="note-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_bullets(title: str, bullets: list[str]):
    if not bullets:
        return
    items = "".join([f"<li>{b}</li>" for b in bullets])
    st.markdown(
        f"""
        <div class="note-card">
            <div class="note-title">{title}</div>
            <div class="note-body">
                <ul class="mini-list">{items}</ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_alerts(producto, compras_df, ventas_df, costo_ref_actual):
    alerts = []
    costo_actual = money_float(producto.get("Costo", 0))
    precio_actual = money_float(producto.get("Precio", 0))
    stock_actual = money_float(producto.get("Stock", 0))

    ultimo_costo_compra = money_float(compras_df["Costo_Unitario"].iloc[-1]) if not compras_df.empty else 0.0
    ultimo_precio_venta = money_float(ventas_df["Precio_Unitario"].dropna().iloc[-1]) if not ventas_df["Precio_Unitario"].dropna().empty else 0.0

    if ultimo_costo_compra > 0 and ultimo_precio_venta > 0 and ultimo_precio_venta <= ultimo_costo_compra:
        alerts.append(("bad", "Última venta por debajo del último costo", f"Último precio facturado {money_fmt(ultimo_precio_venta)} vs último costo recibido {money_fmt(ultimo_costo_compra)}."))

    margen_actual = ((precio_actual - costo_actual) / precio_actual) if precio_actual > 0 and costo_actual > 0 else np.nan
    if pd.notna(margen_actual) and margen_actual < 0.20:
        alerts.append(("warn", "Margen actual estrecho", f"El margen actual del producto está en {pct_fmt(margen_actual)} sobre el precio vigente."))

    if costo_ref_actual > 0 and costo_actual > 0:
        gap = abs(costo_actual - costo_ref_actual) / max(costo_actual, 1.0)
        if gap > 0.35:
            alerts.append(("warn", "Costo inventario y proveedor muy separados", f"Costo inventario {money_fmt(costo_actual)} vs referencia proveedor {money_fmt(costo_ref_actual)}."))

    if stock_actual > 0 and not ventas_df.empty:
        ultima_venta = ventas_df["Fecha"].max()
        if pd.notna(ultima_venta) and ultima_venta < pd.Timestamp.now() - pd.Timedelta(days=45):
            alerts.append(("warn", "Producto con stock y baja rotación reciente", f"Tiene stock disponible, pero no registra ventas desde {ultima_venta.strftime('%Y-%m-%d')}."))

    if not alerts:
        alerts.append(("ok", "Lectura sana del producto", "La trazabilidad principal está disponible y no se detectan alertas críticas inmediatas en costo, precio o rotación."))

    return alerts


def build_storyline(producto, compras_df, ventas_df, costo_ref_actual, compras_unidades, ventas_unidades, compras_total, ventas_total, margen_real):
    story = []
    nombre = str(producto.get("Nombre", "Producto")).strip() or "Producto"
    costo_actual = money_float(producto.get("Costo", 0))
    precio_actual = money_float(producto.get("Precio", 0))

    if compras_unidades > 0:
        story.append(f"{nombre} recibió {qty_fmt(compras_unidades)} unidades en el rango analizado, con una inversión acumulada de {money_fmt(compras_total)}.")
    else:
        story.append(f"{nombre} no tiene recepciones registradas en el rango analizado.")

    if ventas_unidades > 0:
        story.append(f"Se facturaron {qty_fmt(ventas_unidades)} unidades por {money_fmt(ventas_total)} y el margen bruto realizado del periodo fue {money_fmt(margen_real)}.")
    else:
        story.append(f"No se encontraron ventas del producto dentro del rango seleccionado.")

    if costo_ref_actual > 0:
        story.append(f"El costo de referencia del proveedor está en {money_fmt(costo_ref_actual)}, mientras que en inventario el costo vigente está en {money_fmt(costo_actual)}.")

    if costo_actual > 0 and precio_actual > 0:
        margen_actual = (precio_actual - costo_actual) / precio_actual if precio_actual > 0 else 0.0
        story.append(f"Con el precio actual de {money_fmt(precio_actual)}, el margen teórico vigente del producto es {pct_fmt(margen_actual)}.")

    return story


def fig_base(fig, title: str, height: int = 360):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=56, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.78)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        title=dict(text=title, x=0.02, xanchor="left", font=dict(size=18)),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(15,23,42,0.08)")
    return fig


def main():
    st.markdown(
        """
        <div class="hero-360">
            <div class="eyebrow">Nexus Product Intelligence</div>
            <div class="hero-title">Producto 360</div>
            <div class="hero-sub">
                Radiografía completa del producto: entradas por compras, salidas por ventas, costos recibidos,
                precios facturados, márgenes realizados, ritmo de movimiento y trazabilidad cronológica.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        df_inv, df_ven, df_hist, df_map = cargar_datos()
    except Exception as e:
        st.error(f"No fue posible cargar la trazabilidad del producto: {e}")
        return

    if df_inv.empty:
        st.warning("Inventario vacío. No hay productos para analizar.")
        return

    ventas_expand = expandir_ventas(df_ven)

    buscador = st.text_input("Buscar producto por nombre, SKU o referencia")
    inv_view = df_inv.copy()
    inv_view["Display"] = inv_view.apply(
        lambda r: f"{str(r.get('ID_Producto', '')).strip()} | {str(r.get('Nombre', '')).strip()}",
        axis=1,
    )
    if buscador:
        mask = (
            inv_view["Display"].astype(str).str.contains(buscador, case=False, na=False) |
            inv_view["ID_Producto_Norm"].astype(str).str.contains(buscador, case=False, na=False) |
            inv_view["Categoria"].astype(str).str.contains(buscador, case=False, na=False)
        )
        inv_view = inv_view[mask].copy()

    if inv_view.empty:
        st.info("No hay coincidencias con ese filtro.")
        return

    opciones = inv_view.sort_values(["Nombre", "ID_Producto"]) ["Display"].tolist()
    selected_display = st.selectbox("Producto a analizar", opciones)
    producto = inv_view[inv_view["Display"] == selected_display].iloc[0].to_dict()

    producto_uid = str(producto.get("Producto_UID", "")).strip()
    sku_norm = normalizar_id_producto(producto.get("ID_Producto_Norm", producto.get("ID_Producto", "")))

    compras_producto = filtrar_producto(df_hist, producto_uid, sku_norm).sort_values("Fecha")
    ventas_producto = filtrar_producto(ventas_expand, producto_uid, sku_norm).sort_values("Fecha")
    mapa_producto = filtrar_producto(df_map, producto_uid, sku_norm).sort_values("Ultima_Actualizacion") if not df_map.empty else pd.DataFrame()

    min_date_candidates = []
    if not compras_producto.empty:
        min_date_candidates.append(compras_producto["Fecha"].min())
    if not ventas_producto.empty:
        min_date_candidates.append(ventas_producto["Fecha"].min())
    default_start = (min(min_date_candidates).date() if min_date_candidates else (datetime.now() - timedelta(days=120)).date())
    default_end = datetime.now().date()
    date_range = st.date_input("Rango de análisis", value=(default_start, default_end))
    if isinstance(date_range, tuple) and len(date_range) == 2:
        fecha_ini = pd.Timestamp(date_range[0])
        fecha_fin = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    else:
        fecha_ini = pd.Timestamp(default_start)
        fecha_fin = pd.Timestamp(default_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    if not compras_producto.empty:
        compras_producto = compras_producto[(compras_producto["Fecha"] >= fecha_ini) & (compras_producto["Fecha"] <= fecha_fin)].copy()
    if not ventas_producto.empty:
        ventas_producto = ventas_producto[(ventas_producto["Fecha"] >= fecha_ini) & (ventas_producto["Fecha"] <= fecha_fin)].copy()

    costo_ref_actual = money_float(mapa_producto["Costo_Proveedor"].iloc[-1]) if not mapa_producto.empty else 0.0
    proveedor_actual = str(mapa_producto["Nombre_Proveedor"].iloc[-1]).strip() if not mapa_producto.empty else "Sin asignar"

    compras_unidades = float(compras_producto["Unidades"].sum()) if not compras_producto.empty else 0.0
    ventas_unidades = float(ventas_producto["Cantidad"].sum()) if not ventas_producto.empty else 0.0
    compras_total = float(compras_producto["Costo_Total"].sum()) if not compras_producto.empty else 0.0
    ventas_total = float(ventas_producto["Ingreso_Linea"].fillna(0).sum()) if not ventas_producto.empty else 0.0
    costo_vendido = float(ventas_producto["Costo_Total_Linea"].fillna(0).sum()) if not ventas_producto.empty else 0.0
    margen_real = ventas_total - costo_vendido
    margen_pct = (margen_real / ventas_total) if ventas_total > 0 else 0.0
    costo_prom_compra = (compras_total / compras_unidades) if compras_unidades > 0 else 0.0
    precio_prom_venta = (ventas_total / ventas_unidades) if ventas_unidades > 0 else 0.0
    cobertura_precio = float((ventas_producto["Detalle_Fuente"].eq("Exacto") | ventas_producto["Detalle_Fuente"].eq("Inferido de venta de una sola línea")).mean()) if not ventas_producto.empty else 0.0
    utilidad_potencial_actual = (money_float(producto.get("Precio", 0)) - money_float(producto.get("Costo", 0))) * money_float(producto.get("Stock", 0))
    rotacion_neta = ventas_unidades - compras_unidades
    avg_ticket_producto = ventas_total / len(ventas_producto["ID_Venta"].dropna().unique()) if not ventas_producto.empty and len(ventas_producto["ID_Venta"].dropna().unique()) > 0 else 0.0
    storyline = build_storyline(
        producto,
        compras_producto,
        ventas_producto,
        costo_ref_actual,
        compras_unidades,
        ventas_unidades,
        compras_total,
        ventas_total,
        margen_real,
    )

    chips = [
        badge(f"SKU {str(producto.get('ID_Producto', '')).strip() or 'Sin SKU'}"),
        badge(f"Categoría {str(producto.get('Categoria', 'Sin Categoría')).strip() or 'Sin Categoría'}"),
        badge(f"Proveedor {proveedor_actual or 'Sin asignar'}"),
        badge(f"Stock actual {qty_fmt(producto.get('Stock', 0))}"),
        badge(f"Costo vigente {money_fmt(producto.get('Costo', 0))}"),
        badge(f"Precio vigente {money_fmt(producto.get('Precio', 0))}"),
    ]

    st.markdown(
        f"""
        <div class="section-card" style="margin-bottom:14px;">
            <div class="eyebrow" style="color:{COLOR_PRIMARIO}; opacity:1;">Ficha ejecutiva</div>
            <div class="hero-title" style="font-size:1.9rem; color:{COLOR_TEXTO}; margin-top:6px;">{str(producto.get('Nombre', 'Producto sin nombre')).strip()}</div>
            <div class="hero-sub" style="color:{COLOR_MUTED};">Seguimiento integral del producto entre compras, ventas, costo recibido, precio facturado, proveedor, margen y ritmo de salida.</div>
            <div class="chip-row">{''.join(chips)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_metric_grid([
        {"label": "Entradas", "value": qty_fmt(compras_unidades), "foot": f"{len(compras_producto)} movimientos de compra"},
        {"label": "Salidas", "value": qty_fmt(ventas_unidades), "foot": f"{len(ventas_producto)} líneas de venta"},
        {"label": "Costo Prom. Compra", "value": money_fmt(costo_prom_compra), "foot": f"Comprado por {money_fmt(compras_total)}"},
        {"label": "Precio Prom. Venta", "value": money_fmt(precio_prom_venta), "foot": f"Facturado por {money_fmt(ventas_total)}"},
        {"label": "Margen Realizado", "value": money_fmt(margen_real), "foot": pct_fmt(margen_pct)},
        {"label": "Cobertura Detalle Venta", "value": pct_fmt(cobertura_precio), "foot": "Qué tanto del historial tiene precio/costo unitario utilizable"},
    ])

    render_metric_grid([
        {"label": "Stock Actual", "value": qty_fmt(producto.get("Stock", 0)), "foot": f"Costo vigente {money_fmt(producto.get('Costo', 0))}"},
        {"label": "Precio Vigente", "value": money_fmt(producto.get("Precio", 0)), "foot": f"Costo proveedor {money_fmt(costo_ref_actual)}"},
        {"label": "Utilidad Potencial Stock", "value": money_fmt(utilidad_potencial_actual), "foot": "Con precio y costo vigentes"},
        {"label": "Rotación Neta", "value": qty_fmt(rotacion_neta), "foot": "Ventas menos compras del rango"},
        {"label": "Compradores Únicos", "value": qty_fmt(ventas_producto['Nombre_Cliente'].fillna('').replace('', np.nan).dropna().nunique()), "foot": "Clientes distintos del periodo"},
        {"label": "Ticket Prom. Producto", "value": money_fmt(avg_ticket_producto), "foot": "Promedio por venta donde apareció"},
    ])

    tabs = st.tabs(["Resumen", "Kardex", "Clientes y Proveedores", "Diagnóstico", "Evolución"])

    with tabs[0]:
        render_bullets("Lectura ejecutiva del producto", storyline)

        col_a, col_b = st.columns([1.35, 1])

        with col_a:
            render_note(
                "Qué muestra esta gráfica",
                "Las barras verdes muestran entradas por compras y las barras rojas las salidas por ventas. Las líneas muestran cómo se ha movido el costo recibido y el precio realmente facturado para que puedas detectar si el margen se está estrechando o ampliando.",
            )
            if compras_producto.empty and ventas_producto.empty:
                st.info("Este producto no tiene movimientos dentro del rango seleccionado.")
            else:
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                if not compras_producto.empty:
                    fig.add_trace(
                        go.Bar(
                            x=compras_producto["Fecha"],
                            y=compras_producto["Unidades"],
                            name="Entradas",
                            marker_color=COLOR_OK,
                            opacity=0.65,
                            hovertemplate="Compra<br>%{x|%Y-%m-%d}<br>Unidades %{y}<extra></extra>",
                        ),
                        secondary_y=False,
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=compras_producto["Fecha"],
                            y=compras_producto["Costo_Unitario"],
                            mode="lines+markers",
                            name="Costo recibido",
                            line=dict(color=COLOR_PRIMARIO, width=3),
                            marker=dict(size=8),
                            hovertemplate="Costo compra<br>%{x|%Y-%m-%d}<br>%{y:$,.0f}<extra></extra>",
                        ),
                        secondary_y=True,
                    )

                ventas_precio = ventas_producto.dropna(subset=["Precio_Unitario"]).copy()
                if not ventas_producto.empty:
                    fig.add_trace(
                        go.Bar(
                            x=ventas_producto["Fecha"],
                            y=-ventas_producto["Cantidad"],
                            name="Salidas",
                            marker_color=COLOR_CORAL,
                            opacity=0.45,
                            hovertemplate="Venta<br>%{x|%Y-%m-%d}<br>Unidades %{y}<extra></extra>",
                        ),
                        secondary_y=False,
                    )
                if not ventas_precio.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=ventas_precio["Fecha"],
                            y=ventas_precio["Precio_Unitario"],
                            mode="lines+markers",
                            name="Precio facturado",
                            line=dict(color=COLOR_ACENTO, width=3, dash="dot"),
                            marker=dict(size=8),
                            hovertemplate="Precio venta<br>%{x|%Y-%m-%d}<br>%{y:$,.0f}<extra></extra>",
                        ),
                        secondary_y=True,
                    )

                fig = fig_base(fig, "Ritmo de movimiento, costo recibido y precio facturado", height=470)
                fig.update_layout(bargap=0.22)
                fig.update_yaxes(title_text="Unidades", secondary_y=False, zeroline=True, zerolinecolor="rgba(0,0,0,0.08)")
                fig.update_yaxes(title_text="Valor unitario", secondary_y=True, tickprefix="$")
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("### Lectura rápida")
            ultima_compra = compras_producto.iloc[-1] if not compras_producto.empty else None
            ultima_venta = ventas_producto.iloc[-1] if not ventas_producto.empty else None
            penultima_compra = compras_producto.iloc[-2] if len(compras_producto) >= 2 else None
            penultima_venta = ventas_producto.dropna(subset=["Precio_Unitario"]).iloc[-2] if len(ventas_producto.dropna(subset=["Precio_Unitario"])) >= 2 else None

            resumen_rows = []
            if ultima_compra is not None:
                delta_costo = ""
                if penultima_compra is not None:
                    delta_costo_val = money_float(ultima_compra.get("Costo_Unitario", 0)) - money_float(penultima_compra.get("Costo_Unitario", 0))
                    delta_costo = f" | Delta {money_fmt(delta_costo_val)}"
                resumen_rows.append(f"Última compra: {ultima_compra['Fecha'].strftime('%Y-%m-%d')} por {money_fmt(ultima_compra.get('Costo_Unitario', 0))}{delta_costo}")
            if ultima_venta is not None and pd.notna(ultima_venta.get("Precio_Unitario", np.nan)):
                delta_precio = ""
                if penultima_venta is not None:
                    delta_precio_val = money_float(ultima_venta.get("Precio_Unitario", 0)) - money_float(penultima_venta.get("Precio_Unitario", 0))
                    delta_precio = f" | Delta {money_fmt(delta_precio_val)}"
                resumen_rows.append(f"Última venta: {ultima_venta['Fecha'].strftime('%Y-%m-%d')} por {money_fmt(ultima_venta.get('Precio_Unitario', 0))}{delta_precio}")
            resumen_rows.append(f"Costo actual en inventario: {money_fmt(producto.get('Costo', 0))}")
            resumen_rows.append(f"Precio actual en inventario: {money_fmt(producto.get('Precio', 0))}")
            resumen_rows.append(f"Costo proveedor vigente: {money_fmt(costo_ref_actual)}")
            resumen_rows.append(f"Stock actual: {qty_fmt(producto.get('Stock', 0))}")
            render_bullets("Lo más importante hoy", resumen_rows)

            compras_cliente = ventas_producto.groupby("Nombre_Cliente", dropna=False).agg(
                Unidades=("Cantidad", "sum"),
                Facturacion=("Ingreso_Linea", "sum"),
            ).reset_index().sort_values(["Unidades", "Facturacion"], ascending=False).head(5)
            if not compras_cliente.empty:
                st.markdown("### Top clientes")
                st.dataframe(
                    compras_cliente,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Unidades": st.column_config.NumberColumn("Unidades", format="%.0f"),
                        "Facturacion": st.column_config.NumberColumn("Facturación", format="$%.0f"),
                    },
                )

        col_c1, col_c2 = st.columns([1, 1])
        with col_c1:
            render_note(
                "Interpretación de costo vs precio",
                "Esta línea compara el costo promedio de compra frente al precio promedio de venta a lo largo del tiempo. Si ambas curvas se acercan, el margen se está comprimiendo y conviene revisar precio o costo negociado.",
            )
            fig_mix = go.Figure()
            if not compras_producto.empty:
                compra_daily = compras_producto.groupby(compras_producto["Fecha"].dt.date).agg(Costo_Compra=("Costo_Unitario", "mean")).reset_index()
                fig_mix.add_trace(go.Scatter(x=compra_daily["Fecha"], y=compra_daily["Costo_Compra"], mode="lines+markers", name="Costo compra", line=dict(color=COLOR_PRIMARIO, width=3)))
            if not ventas_producto.dropna(subset=["Precio_Unitario"]).empty:
                venta_daily = ventas_producto.dropna(subset=["Precio_Unitario"]).groupby(ventas_producto.dropna(subset=["Precio_Unitario"])["Fecha"].dt.date).agg(Precio_Venta=("Precio_Unitario", "mean")).reset_index()
                fig_mix.add_trace(go.Scatter(x=venta_daily["Fecha"], y=venta_daily["Precio_Venta"], mode="lines+markers", name="Precio venta", line=dict(color=COLOR_ACENTO, width=3, dash="dot")))
            fig_mix = fig_base(fig_mix, "Tendencia promedio de costo vs precio", height=360)
            fig_mix.update_yaxes(tickprefix="$", title="Valor unitario")
            st.plotly_chart(fig_mix, use_container_width=True)

        with col_c2:
            render_note(
                "Interpretación de flujo económico",
                "Este comparativo resume cuánto dinero entró por ventas frente a cuánto dinero salió por compras del producto dentro del rango. Ayuda a entender si el producto está convirtiendo capital en caja o si está acumulando inversión sin suficiente salida.",
            )
            fig_cash = go.Figure()
            fig_cash.add_trace(go.Bar(
                x=["Compras", "Ventas", "Margen"],
                y=[compras_total, ventas_total, margen_real],
                marker_color=[COLOR_PRIMARIO, COLOR_ACENTO, COLOR_OK if margen_real >= 0 else COLOR_PELIGRO],
                text=[money_fmt(compras_total), money_fmt(ventas_total), money_fmt(margen_real)],
                textposition="outside",
            ))
            fig_cash = fig_base(fig_cash, "Dinero invertido, facturado y margen generado", height=360)
            fig_cash.update_yaxes(tickprefix="$", title="Valor")
            st.plotly_chart(fig_cash, use_container_width=True)

    with tabs[1]:
        render_note(
            "Qué estás viendo en el kardex",
            "Aquí se unifican compras y ventas del producto en una sola trazabilidad cronológica. Unidades positivas son entradas al inventario; unidades negativas son salidas por facturación.",
        )
        kardex_cols = st.columns([1, 1, 1])
        movimiento_tipo = kardex_cols[0].selectbox("Ver en kardex", ["Todos", "Compras", "Ventas"])
        incluir_sin_detalle = kardex_cols[1].checkbox("Incluir ventas históricas sin detalle unitario", value=True)
        descargar = kardex_cols[2].checkbox("Preparar descarga CSV", value=False)

        compras_k = compras_producto.copy()
        compras_k["Tipo"] = "Compra"
        compras_k["Tercero"] = compras_k["Proveedor"].astype(str)
        compras_k["Referencia"] = compras_k["Folio"].astype(str)
        compras_k["Unidades_Mov"] = compras_k["Unidades"]
        compras_k["Valor_Unitario"] = compras_k["Costo_Unitario"]
        compras_k["Valor_Total"] = compras_k["Costo_Total"]
        compras_k["Costo_Base"] = compras_k["Costo_Unitario"]
        compras_k["Precio_Facturado"] = compras_k["Precio_Unitario"]
        compras_k["Detalle"] = compras_k["Origen"].astype(str)

        ventas_k = ventas_producto.copy()
        if not incluir_sin_detalle:
            ventas_k = ventas_k[ventas_k["Detalle_Fuente"].ne("Histórico sin detalle unitario")].copy()
        ventas_k["Tipo"] = "Venta"
        ventas_k["Tercero"] = ventas_k["Nombre_Cliente"].astype(str)
        ventas_k["Referencia"] = ventas_k["ID_Venta"].astype(str)
        ventas_k["Unidades_Mov"] = -ventas_k["Cantidad"]
        ventas_k["Valor_Unitario"] = ventas_k["Precio_Unitario"]
        ventas_k["Valor_Total"] = ventas_k["Ingreso_Linea"]
        ventas_k["Costo_Base"] = ventas_k["Costo_Unitario"]
        ventas_k["Precio_Facturado"] = ventas_k["Precio_Unitario"]
        ventas_k["Detalle"] = ventas_k["Detalle_Fuente"].astype(str)

        frames = []
        if movimiento_tipo in ["Todos", "Compras"] and not compras_k.empty:
            frames.append(compras_k[["Fecha", "Tipo", "Referencia", "Tercero", "Nombre_Producto", "Unidades_Mov", "Valor_Unitario", "Valor_Total", "Costo_Base", "Precio_Facturado", "Detalle"]].rename(columns={"Nombre_Producto": "Producto"}))
        if movimiento_tipo in ["Todos", "Ventas"] and not ventas_k.empty:
            frames.append(ventas_k[["Fecha", "Tipo", "Referencia", "Tercero", "Nombre_Producto", "Unidades_Mov", "Valor_Unitario", "Valor_Total", "Costo_Base", "Precio_Facturado", "Detalle"]].rename(columns={"Nombre_Producto": "Producto"}))

        kardex_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["Fecha", "Tipo", "Referencia", "Tercero", "Producto", "Unidades_Mov", "Valor_Unitario", "Valor_Total", "Costo_Base", "Precio_Facturado", "Detalle"])
        if not kardex_df.empty:
            kardex_df = kardex_df.sort_values("Fecha", ascending=False)
        st.dataframe(
            kardex_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Fecha": st.column_config.DatetimeColumn("Fecha", format="YYYY-MM-DD HH:mm"),
                "Unidades_Mov": st.column_config.NumberColumn("Unid. Mov.", format="%.0f"),
                "Valor_Unitario": st.column_config.NumberColumn("Valor Unit.", format="$%.0f"),
                "Valor_Total": st.column_config.NumberColumn("Valor Total", format="$%.0f"),
                "Costo_Base": st.column_config.NumberColumn("Costo Unit.", format="$%.0f"),
                "Precio_Facturado": st.column_config.NumberColumn("Precio Fact.", format="$%.0f"),
            },
            height=420,
        )
        if descargar and not kardex_df.empty:
            st.download_button(
                "Descargar kardex CSV",
                data=kardex_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"kardex_producto_{sku_norm}.csv",
                mime="text/csv",
            )

        col_c, col_v = st.columns(2)
        with col_c:
            st.markdown("### Recepciones de compra")
            if compras_producto.empty:
                st.info("No hay compras del producto en el rango.")
            else:
                st.dataframe(
                    compras_producto[["Fecha", "Folio", "Proveedor", "Unidades", "Costo_Unitario", "Costo_Total", "IVA_Porcentaje", "Origen"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Fecha": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
                        "Unidades": st.column_config.NumberColumn(format="%.0f"),
                        "Costo_Unitario": st.column_config.NumberColumn("Costo Unit.", format="$%.0f"),
                        "Costo_Total": st.column_config.NumberColumn("Costo Total", format="$%.0f"),
                        "IVA_Porcentaje": st.column_config.NumberColumn("IVA %", format="%.0f"),
                    },
                )
        with col_v:
            st.markdown("### Facturación en ventas")
            if ventas_producto.empty:
                st.info("No hay ventas del producto en el rango.")
            else:
                st.dataframe(
                    ventas_producto[["Fecha", "ID_Venta", "Nombre_Cliente", "Mascota", "Cantidad", "Precio_Unitario", "Ingreso_Linea", "Costo_Unitario", "Margen_Linea", "Detalle_Fuente"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Fecha": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
                        "Cantidad": st.column_config.NumberColumn(format="%.0f"),
                        "Precio_Unitario": st.column_config.NumberColumn("Precio Fact.", format="$%.0f"),
                        "Ingreso_Linea": st.column_config.NumberColumn("Ingreso", format="$%.0f"),
                        "Costo_Unitario": st.column_config.NumberColumn("Costo", format="$%.0f"),
                        "Margen_Linea": st.column_config.NumberColumn("Margen", format="$%.0f"),
                    },
                )

    with tabs[2]:
        render_note(
            "Lectura de relaciones comerciales",
            "A la izquierda ves a quién le compras este producto y en qué condiciones promedio llega. A la derecha ves quién te lo compra, cuánto factura y qué margen te deja cada cliente en el periodo.",
        )
        col_p, col_q = st.columns([1, 1])
        with col_p:
            st.markdown("### Relación con proveedores")
            if compras_producto.empty:
                st.info("Sin compras del producto dentro del rango.")
            else:
                prov_df = compras_producto.groupby("Proveedor", dropna=False).agg(
                    Entradas=("Unidades", "sum"),
                    Inversion=("Costo_Total", "sum"),
                    Costo_Prom=("Costo_Unitario", "mean"),
                    Ultima_Compra=("Fecha", "max"),
                ).reset_index().sort_values(["Entradas", "Inversion"], ascending=False)
                st.dataframe(
                    prov_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Entradas": st.column_config.NumberColumn(format="%.0f"),
                        "Inversion": st.column_config.NumberColumn(format="$%.0f"),
                        "Costo_Prom": st.column_config.NumberColumn("Costo Prom.", format="$%.0f"),
                        "Ultima_Compra": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
                    },
                )

                fig_prov = px.bar(
                    prov_df,
                    x="Proveedor",
                    y="Entradas",
                    color="Costo_Prom",
                    color_continuous_scale=[COLOR_OK, COLOR_ACENTO, COLOR_CORAL],
                    title="Volumen por proveedor",
                )
                fig_prov = fig_base(fig_prov, "Volumen por proveedor", height=320)
                st.plotly_chart(fig_prov, use_container_width=True)

        with col_q:
            st.markdown("### Relación con clientes")
            if ventas_producto.empty:
                st.info("Sin ventas del producto dentro del rango.")
            else:
                cli_df = ventas_producto.groupby("Nombre_Cliente", dropna=False).agg(
                    Unidades=("Cantidad", "sum"),
                    Facturacion=("Ingreso_Linea", "sum"),
                    Margen=("Margen_Linea", "sum"),
                    Ultima_Venta=("Fecha", "max"),
                ).reset_index().sort_values(["Facturacion", "Unidades"], ascending=False)
                st.dataframe(
                    cli_df.head(15),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Unidades": st.column_config.NumberColumn(format="%.0f"),
                        "Facturacion": st.column_config.NumberColumn(format="$%.0f"),
                        "Margen": st.column_config.NumberColumn(format="$%.0f"),
                        "Ultima_Venta": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
                    },
                )

                fig_cli = px.bar(
                    cli_df.head(10),
                    x="Nombre_Cliente",
                    y="Facturacion",
                    color="Margen",
                    color_continuous_scale=[COLOR_CORAL, COLOR_ACENTO, COLOR_OK],
                    title="Facturación por cliente",
                )
                fig_cli = fig_base(fig_cli, "Facturación por cliente", height=320)
                st.plotly_chart(fig_cli, use_container_width=True)

    with tabs[3]:
        render_note(
            "Diagnóstico ejecutivo",
            "Este bloque concentra alertas de margen, brechas de costo y señales de rotación. Está pensado para decidir rápido si el problema del producto está en compra, precio, salida o consistencia del dato.",
        )
        st.markdown("### Alertas y lectura analítica")
        for level, title, body in build_alerts(producto, compras_producto, ventas_producto, costo_ref_actual):
            st.markdown(
                f"""
                <div class="alert-card alert-{'ok' if level == 'ok' else 'warn' if level == 'warn' else 'bad'}">
                    <div class="alert-title">{title}</div>
                    <div class="alert-body">{body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### Radiografía numérica")
        diag = {
            "Stock actual": qty_fmt(producto.get("Stock", 0)),
            "Costo actual inventario": money_fmt(producto.get("Costo", 0)),
            "Precio actual inventario": money_fmt(producto.get("Precio", 0)),
            "Costo referencia proveedor": money_fmt(costo_ref_actual),
            "Última compra": compras_producto["Fecha"].max().strftime("%Y-%m-%d %H:%M") if not compras_producto.empty and pd.notna(compras_producto["Fecha"].max()) else "Sin registro",
            "Última venta": ventas_producto["Fecha"].max().strftime("%Y-%m-%d %H:%M") if not ventas_producto.empty and pd.notna(ventas_producto["Fecha"].max()) else "Sin registro",
            "Comprado en el periodo": qty_fmt(compras_unidades),
            "Vendido en el periodo": qty_fmt(ventas_unidades),
            "Invertido en compras": money_fmt(compras_total),
            "Facturado en ventas": money_fmt(ventas_total),
            "Costo de lo vendido": money_fmt(costo_vendido),
            "Margen logrado": money_fmt(margen_real),
            "Margen logrado %": pct_fmt(margen_pct),
        }
        st.dataframe(
            pd.DataFrame({"Indicador": list(diag.keys()), "Valor": list(diag.values())}),
            use_container_width=True,
            hide_index=True,
        )

    with tabs[4]:
        render_note(
            "Evolución temporal del producto",
            "Aquí se profundiza en cómo se ha comportado el producto por periodos: compras, ventas, precios, costos y margen por bloque de tiempo para detectar tendencias y cambios estructurales.",
        )
        frecuencia = st.selectbox("Frecuencia de análisis", ["Diaria", "Semanal", "Mensual"], index=2)
        freq_map = {"Diaria": "D", "Semanal": "W", "Mensual": "M"}
        freq = freq_map[frecuencia]

        compras_ev = compras_producto.copy()
        ventas_ev = ventas_producto.copy()
        if not compras_ev.empty:
            compras_ev["Periodo"] = compras_ev["Fecha"].dt.to_period("M" if freq == "M" else ("W" if freq == "W" else "D")).dt.to_timestamp()
            compras_agg = compras_ev.groupby("Periodo").agg(
                Unidades_Compradas=("Unidades", "sum"),
                Costo_Comprado=("Costo_Total", "sum"),
                Costo_Unit_Prom=("Costo_Unitario", "mean"),
            ).reset_index()
        else:
            compras_agg = pd.DataFrame(columns=["Periodo", "Unidades_Compradas", "Costo_Comprado", "Costo_Unit_Prom"])

        if not ventas_ev.empty:
            ventas_ev["Periodo"] = ventas_ev["Fecha"].dt.to_period("M" if freq == "M" else ("W" if freq == "W" else "D")).dt.to_timestamp()
            ventas_agg = ventas_ev.groupby("Periodo").agg(
                Unidades_Vendidas=("Cantidad", "sum"),
                Facturacion=("Ingreso_Linea", "sum"),
                Costo_Vendido=("Costo_Total_Linea", "sum"),
                Precio_Unit_Prom=("Precio_Unitario", "mean"),
            ).reset_index()
            ventas_agg["Margen"] = ventas_agg["Facturacion"] - ventas_agg["Costo_Vendido"]
        else:
            ventas_agg = pd.DataFrame(columns=["Periodo", "Unidades_Vendidas", "Facturacion", "Costo_Vendido", "Precio_Unit_Prom", "Margen"])

        evo = pd.merge(compras_agg, ventas_agg, on="Periodo", how="outer").sort_values("Periodo").fillna(0)
        if evo.empty:
            st.info("No hay suficiente historial para construir evolución del producto en este rango.")
        else:
            col_e1, col_e2 = st.columns([1.15, 1])
            with col_e1:
                fig_evo = go.Figure()
                fig_evo.add_trace(go.Bar(x=evo["Periodo"], y=evo["Unidades_Compradas"], name="Compradas", marker_color=COLOR_OK, opacity=0.60))
                fig_evo.add_trace(go.Bar(x=evo["Periodo"], y=-evo["Unidades_Vendidas"], name="Vendidas", marker_color=COLOR_CORAL, opacity=0.50))
                fig_evo = fig_base(fig_evo, "Balance de unidades por periodo", height=360)
                fig_evo.update_layout(barmode="relative")
                fig_evo.update_yaxes(title="Unidades")
                st.plotly_chart(fig_evo, use_container_width=True)
            with col_e2:
                fig_evo2 = go.Figure()
                if "Costo_Unit_Prom" in evo.columns:
                    fig_evo2.add_trace(go.Scatter(x=evo["Periodo"], y=evo["Costo_Unit_Prom"], mode="lines+markers", name="Costo unitario prom.", line=dict(color=COLOR_PRIMARIO, width=3)))
                if "Precio_Unit_Prom" in evo.columns:
                    fig_evo2.add_trace(go.Scatter(x=evo["Periodo"], y=evo["Precio_Unit_Prom"], mode="lines+markers", name="Precio unitario prom.", line=dict(color=COLOR_ACENTO, width=3, dash="dot")))
                fig_evo2 = fig_base(fig_evo2, "Evolución de costo y precio promedio", height=360)
                fig_evo2.update_yaxes(tickprefix="$", title="Valor unitario")
                st.plotly_chart(fig_evo2, use_container_width=True)

            st.dataframe(
                evo,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Periodo": st.column_config.DatetimeColumn(format="YYYY-MM-DD"),
                    "Unidades_Compradas": st.column_config.NumberColumn(format="%.0f"),
                    "Costo_Comprado": st.column_config.NumberColumn(format="$%.0f"),
                    "Costo_Unit_Prom": st.column_config.NumberColumn(format="$%.0f"),
                    "Unidades_Vendidas": st.column_config.NumberColumn(format="%.0f"),
                    "Facturacion": st.column_config.NumberColumn(format="$%.0f"),
                    "Costo_Vendido": st.column_config.NumberColumn(format="$%.0f"),
                    "Precio_Unit_Prom": st.column_config.NumberColumn(format="$%.0f"),
                    "Margen": st.column_config.NumberColumn(format="$%.0f"),
                },
            )


if __name__ == "__main__":
    main()