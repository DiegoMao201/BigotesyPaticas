import streamlit as st
import pandas as pd
import gspread
import numpy as np
import json
import uuid
import time
import io
from datetime import datetime, timedelta, date
from urllib.parse import quote
import unicodedata

# ==========================================
# 0. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================

st.set_page_config(
    page_title="Bigotes & Paticas | WMS Avanzado",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    :root { --primary-color: #187f77; --accent-color: #f5a641; }
    .stButton>button {
        border-radius: 8px; font-weight: 700; border: 2px solid #187f77;
        color: #187f77; background-color: white; transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #187f77; color: white; }
    div[data-testid="metric-container"] {
        background-color: #f8f9fa; border-left: 5px solid #f5a641;
        padding: 15px; border-radius: 8px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 1. FUNCIONES UTILITARIAS Y DE LIMPIEZA
# ==========================================

def _norm_col(s: str) -> str:
    """Normaliza nombre de columna para comparación flexible."""
    s = "" if s is None else str(s)
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace(" ", "").replace("_", "")
    return s

def _find_col(df, candidates):
    """Busca columna en df que coincida con alguna de las opciones (soporta tildes, espacios, etc)."""
    if df is None or df.empty:
        return None
    norm_map = {_norm_col(c): c for c in df.columns}
    for cand in candidates:
        key = _norm_col(cand)
        if key in norm_map:
            return norm_map[key]
    # fallback: contains
    for cand in candidates:
        key = _norm_col(cand)
        for k, orig in norm_map.items():
            if key in k:
                return orig
    return None

def _ensure_cols(df: pd.DataFrame, defaults: dict) -> pd.DataFrame:
    """Asegura que el DataFrame tenga todas las columnas de defaults."""
    df = df.copy() if df is not None else pd.DataFrame()
    for c, v in defaults.items():
        if c not in df.columns:
            df[c] = v
    return df

def normalizar_id_producto(id_prod):
    if pd.isna(id_prod) or str(id_prod).strip() == "": return "SIN_ID"
    val = str(id_prod).strip().upper()
    val = val.replace(".", "").replace(",", "").replace("\t", "").replace("\n", "").lstrip("0")
    return val if val else "SIN_ID"

def clean_currency(x):
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        clean = x.replace('$', '').replace(',', '').replace(' ', '').strip()
        try: return float(clean)
        except: return 0.0
    return 0.0


# ==========================================
# 2. GESTIÓN DE API (Anti-Caídas)
# ==========================================

def safe_google_op(func, *args, **kwargs):
    max_retries = 5
    wait = 2
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e).lower() or "quota" in str(e).lower():
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    wait *= 2 
                    continue
            st.error(f"Error de conexión con Google: {e}")
            raise e

@st.cache_resource
def conectar_db():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración en secrets.toml")
            return None
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        return gc.open_by_url(st.secrets["SHEET_URL"])
    except Exception as e:
        st.error(f"🔴 Error de Conexión Inicial: {e}")
        return None

def get_worksheet_safe(sh, name, headers):
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=max(len(headers), 20))
        ws.append_row(headers)
        return ws


# ==========================================
# 3. CARGA DE DATOS (NUEVOS ESQUEMAS)
# ==========================================

def cargar_datos_snapshot():
    sh = conectar_db()
    if not sh: return None

    schemas = {
        "Inventario": [
            "Producto_UID", "ID_Producto", "ID_Producto_Norm", "SKU_Proveedor", "Nombre", "Stock",
            "Precio", "Costo", "Categoria", "Iva"
        ],
        "Ventas": ['ID_Venta', 'Fecha', 'Cedula_Cliente', 'Nombre_Cliente', 'Tipo_Entrega', 'Direccion_Envio', 'Estado_Envio', 'Metodo_Pago', 'Banco_Destino', 'Total', 'Items', 'Items_Detalle', 'Costo_Total', 'Mascota'],
        "Gastos": ['ID_Gasto', 'Fecha', 'Tipo_Gasto', 'Categoria', 'Descripcion', 'Monto', 'Metodo_Pago', 'Banco_Origen'],
        "Maestro_Proveedores": [
            'ID_Proveedor', 'Nombre_Proveedor', 'SKU_Proveedor', 'SKU_Interno', 'Factor_Pack',
            'Ultima_Actualizacion', 'Email', 'Costo_Proveedor', 'Producto_UID', 'Ultimo_IVA'
        ],
        "Historial_Ordenes": ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total_Dinero', 'Estado']
    }

    data_store = {}
    with st.spinner('🔄 Sincronizando Core de Datos...'):
        for sheet_name, cols in schemas.items():
            ws = get_worksheet_safe(sh, sheet_name, cols)
            records = safe_google_op(ws.get_all_records)
            df = pd.DataFrame(records)
            if df.empty: df = pd.DataFrame(columns=cols)
            else:
                for c in cols:
                    if c not in df.columns: df[c] = ""
            data_store[f"df_{sheet_name}"] = df
            data_store[f"ws_{sheet_name}"] = ws

    # Limpieza Inventario
    df_inv = data_store["df_Inventario"]
    df_prov = data_store.get("df_Maestro_Proveedores", pd.DataFrame())

    df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
    df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
    df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
    df_inv['ID_Producto_Norm'] = df_inv['ID_Producto'].apply(normalizar_id_producto)
    df_inv['Categoria'] = df_inv['Categoria'].replace('', 'Sin Categoría').fillna('Sin Categoría')

    # Limpieza Maestro_Proveedores
    if df_prov is not None and not df_prov.empty:
        if "Costo_Proveedor" not in df_prov.columns:
            df_prov["Costo_Proveedor"] = 0.0
        df_prov["Costo_Proveedor"] = df_prov["Costo_Proveedor"].apply(clean_currency)

        if "Factor_Pack" not in df_prov.columns:
            df_prov["Factor_Pack"] = 1.0
        df_prov["Factor_Pack"] = pd.to_numeric(df_prov["Factor_Pack"], errors="coerce").fillna(1.0)
        df_prov["Factor_Pack"] = np.where(df_prov["Factor_Pack"] <= 0, 1.0, df_prov["Factor_Pack"])
        df_prov["Costo_Proveedor_Unitario"] = np.where(
            df_prov["Factor_Pack"] > 0,
            df_prov["Costo_Proveedor"] / df_prov["Factor_Pack"],
            df_prov["Costo_Proveedor"]
        )

        data_store["df_Maestro_Proveedores"] = df_prov

    data_store["df_Inventario"] = df_inv
    st.session_state["data_store"] = data_store
    st.session_state["last_sync"] = datetime.now()
    return data_store


# ==========================================
# 4. MOTOR ANALÍTICO AVANZADO (ABC & COMPRAS)
# ==========================================

def _calc_clase_abc(master: pd.DataFrame) -> pd.Series:
    df = master.copy()
    if "Valor_Ventas_90d" not in df.columns:
        df["Valor_Ventas_90d"] = 0.0

    df["Valor_Ventas_90d"] = pd.to_numeric(df["Valor_Ventas_90d"], errors="coerce").fillna(0.0)
    total = float(df["Valor_Ventas_90d"].sum())
    if total <= 0:
        return pd.Series(["C"] * len(df), index=df.index)

    order = df["Valor_Ventas_90d"].sort_values(ascending=False).index
    cum = (df.loc[order, "Valor_Ventas_90d"].cumsum() / total).values

    clases = np.select([cum <= 0.80, cum <= 0.95], ["A", "B"], default="C")
    out = pd.Series(index=order, data=clases).reindex(df.index).fillna("C")
    return out

def calcular_master_df() -> pd.DataFrame:
    data = st.session_state.get("data_store", {})
    df_inv  = data.get("df_Inventario", pd.DataFrame()).copy()
    df_prov = data.get("df_Maestro_Proveedores", pd.DataFrame()).copy()
    df_ven  = data.get("df_Ventas", pd.DataFrame()).copy()

    # 1. INVENTARIO ROBUSTO
    col_cat = _find_col(df_inv, ["Categoria", "Categoría"])
    if col_cat and col_cat != "Categoria":
        df_inv = df_inv.rename(columns={col_cat: "Categoria"})

    df_inv = _ensure_cols(df_inv, {
        "ID_Producto": "", "Nombre": "", "Categoria": "Sin Categoría",
        "Stock": 0.0, "Costo": 0.0, "Precio": 0.0,
        "Producto_UID": "", "ID_Producto_Norm": "",
    })

    mask_empty = df_inv["ID_Producto_Norm"].astype(str).str.strip().eq("")
    if mask_empty.any():
        df_inv.loc[mask_empty, "ID_Producto_Norm"] = (
            df_inv.loc[mask_empty, "ID_Producto"].apply(normalizar_id_producto)
        )

    for c in ["Stock", "Costo", "Precio"]:
        df_inv[c] = df_inv[c].apply(clean_currency)

    # 2. PROVEEDORES ROBUSTO
    df_prov = _ensure_cols(df_prov, {
        "SKU_Interno": "", "Factor_Pack": 1.0,
        "Costo_Proveedor": 0.0, "Nombre_Proveedor": "Sin Asignar",
    })
    df_prov["Costo_Proveedor"] = df_prov["Costo_Proveedor"].apply(clean_currency)
    df_prov["Factor_Pack"]     = pd.to_numeric(df_prov["Factor_Pack"], errors="coerce").fillna(1.0)
    df_prov["Factor_Pack"]     = np.where(df_prov["Factor_Pack"] <= 0, 1.0, df_prov["Factor_Pack"])

    if "SKU_Interno_Norm" not in df_prov.columns:
        df_prov["SKU_Interno_Norm"] = df_prov["SKU_Interno"].apply(normalizar_id_producto)
    else:
        df_prov["SKU_Interno_Norm"] = df_prov["SKU_Interno_Norm"].apply(normalizar_id_producto)
    df_prov["Costo_Proveedor_Unitario"] = np.where(
        df_prov["Factor_Pack"] > 0,
        df_prov["Costo_Proveedor"] / df_prov["Factor_Pack"],
        df_prov["Costo_Proveedor"]
    )
    if "Ultima_Actualizacion" in df_prov.columns:
        df_prov["Ultima_Actualizacion"] = df_prov["Ultima_Actualizacion"].astype(str).str.strip()
        df_prov["Ultima_Actualizacion_dt"] = pd.to_datetime(df_prov["Ultima_Actualizacion"], errors="coerce")
    else:
        df_prov["Ultima_Actualizacion_dt"] = pd.NaT
    df_prov["Sort_Costo_Proveedor"] = pd.to_numeric(df_prov["Costo_Proveedor"], errors="coerce").fillna(0.0)

    # 3. MERGE
    if not df_prov.empty and "SKU_Interno_Norm" in df_prov.columns:
        sort_cols = ["Ultima_Actualizacion_dt", "Sort_Costo_Proveedor"]
        ascending = [False, False]
        df_prov_clean = (
            df_prov.sort_values(sort_cols, ascending=ascending, na_position="last")
            .drop_duplicates("SKU_Interno_Norm")
        )
        master = pd.merge(
            df_inv,
            df_prov_clean[["SKU_Interno_Norm", "Nombre_Proveedor", "Costo_Proveedor", "Costo_Proveedor_Unitario", "Factor_Pack"]],
            left_on="ID_Producto_Norm", right_on="SKU_Interno_Norm",
            how="left",
        )
    else:
        master = df_inv.copy()
        master["Nombre_Proveedor"] = "Sin Asignar"
        master["Costo_Proveedor"]  = 0.0
        master["Costo_Proveedor_Unitario"] = 0.0
        master["Factor_Pack"]      = 1.0

    master["Nombre_Proveedor"] = master["Nombre_Proveedor"].fillna("Sin Asignar")
    master["Costo_Proveedor"]  = pd.to_numeric(master["Costo_Proveedor"], errors="coerce").fillna(0.0)
    master["Costo_Proveedor_Unitario"] = pd.to_numeric(master["Costo_Proveedor_Unitario"], errors="coerce").fillna(0.0)
    master["Factor_Pack"]      = pd.to_numeric(master["Factor_Pack"], errors="coerce").fillna(1.0)
    master["Factor_Pack"]      = np.where(master["Factor_Pack"] <= 0, 1.0, master["Factor_Pack"])

    # 4. NUMÉRICOS BASE
    for c in ["Stock", "Costo", "Precio", "Costo_Proveedor", "Costo_Proveedor_Unitario", "Factor_Pack"]:
        master[c] = pd.to_numeric(master[c], errors="coerce").fillna(0.0)

    master["Costo_Inventario_Unitario"] = np.where(master["Costo"] > 0, master["Costo"], 0.0)
    master["Costo_Referencia_Proveedor_Unitario"] = np.where(
        master["Costo_Proveedor_Unitario"] > 0,
        master["Costo_Proveedor_Unitario"],
        0.0
    )
    master["Costo_Efectivo"] = np.where(
        master["Costo_Inventario_Unitario"] > 0,
        master["Costo_Inventario_Unitario"],
        master["Costo_Referencia_Proveedor_Unitario"],
    )

    master["Precio_Valido"] = master["Precio"] > 0
    master["Costo_Valido"] = master["Costo_Efectivo"] > 0
    master["Margen_%"] = np.where(
        master["Precio_Valido"] & master["Costo_Valido"],
        (master["Precio"] - master["Costo_Efectivo"]) / master["Precio"],
        0.0
    )
    master["Margen_$"] = np.where(
        master["Precio_Valido"] & master["Costo_Valido"],
        master["Precio"] - master["Costo_Efectivo"],
        0.0
    )
    master["Margen_Anomalo"] = (
        (~master["Precio_Valido"]) |
        (~master["Costo_Valido"]) |
        (master["Margen_%"] < -0.25) |
        (master["Margen_%"] > 0.95)
    )
    master["Alerta_Datos"] = np.select(
        [
            ~master["Precio_Valido"],
            ~master["Costo_Valido"],
            (master["Costo_Referencia_Proveedor_Unitario"] > 0) &
            (master["Costo_Inventario_Unitario"] > 0) &
            (np.abs(master["Costo_Inventario_Unitario"] - master["Costo_Referencia_Proveedor_Unitario"]) / np.maximum(master["Costo_Inventario_Unitario"], 1.0) > 1.5),
            master["Margen_%"] < -0.25,
            master["Margen_%"] > 0.95,
        ],
        [
            "Sin precio",
            "Sin costo",
            "Costo difiere vs proveedor",
            "Margen negativo anómalo",
            "Margen demasiado alto",
        ],
        default="OK"
    )

    # 5. VENTAS / ROTACIÓN
    stats = analizar_ventas(df_ven, master)
    def buscar_ventas(row, key):
        posibles = set()
        if "Producto_UID" in row and str(row["Producto_UID"]).strip():
            posibles.add(str(row["Producto_UID"]).strip().lower())
        if "ID_Producto_Norm" in row and str(row["ID_Producto_Norm"]).strip():
            posibles.add(str(row["ID_Producto_Norm"]).strip().lower())
        if "ID_Producto" in row and str(row["ID_Producto"]).strip():
            posibles.add(normalizar_id_producto(row["ID_Producto"]).lower())
        for k in posibles:
            if k in stats and key in stats[k]:
                return stats[k][key]
        return 0.0
    master["v90"] = master.apply(lambda row: buscar_ventas(row, "v90"), axis=1)
    master["v30"] = master.apply(lambda row: buscar_ventas(row, "v30"), axis=1)
    master["v90"] = pd.to_numeric(master["v90"], errors="coerce").fillna(0.0)
    master["v30"] = pd.to_numeric(master["v30"], errors="coerce").fillna(0.0)

    # 6. MODO DEMANDA
    master["Modo_Demanda"] = np.where(
        (master["v30"] <= 1) & (master["v90"] <= 1) & (master["v90"] > 0),
        "ARRANQUE",
        np.where(master["v90"] > 0, "ROTACION", "SIN_VENTAS"),
    )

    # 7. VELOCIDAD DIARIA
    vel_30 = master["v30"] / 30.0
    vel_90 = master["v90"] / 90.0
    vel_blend = (0.65 * vel_90) + (0.35 * vel_30)
    conf = np.clip(master["v90"] / 6.0, 0.0, 1.0)
    master["Velocidad_Diaria"] = np.where(
        master["Modo_Demanda"] == "ROTACION",
        pd.Series(vel_blend * conf, index=master.index).fillna(0.0),
        0.0,
    )
    master["Velocidad_Diaria"] = pd.to_numeric(master["Velocidad_Diaria"], errors="coerce").fillna(0.0)

    # 8. SUGERENCIA DE COMPRA
    DIAS_OBJETIVO = 8
    DIAS_SEGURIDAD = 1
    LEAD_TIME_DIAS = 5

    master["Min_Unidades"] = np.where(master["v90"] > 0, 1.0, 0.0)
    stock_seg = master["Velocidad_Diaria"] * DIAS_SEGURIDAD
    punto_reorden = (master["Velocidad_Diaria"] * LEAD_TIME_DIAS) + stock_seg
    stock_obj = (master["Velocidad_Diaria"] * DIAS_OBJETIVO) + stock_seg

    master["Factor_Pack_Efectivo"] = np.where(master["Modo_Demanda"] == "ARRANQUE", 1.0, master["Factor_Pack"])


    req_rot = (
        (master["Modo_Demanda"] == "ROTACION") &
        (master["Velocidad_Diaria"] > 0) &
        (master["Stock"] <= punto_reorden)
    )
    req_arr = (
        (master["Modo_Demanda"] == "ARRANQUE") &
        (master["Stock"] < master["Min_Unidades"])
    )
    req_sin_stock = (master["v90"] > 0) & (master["Stock"] <= 0)

    master["Requiere_Compra"] = req_rot | req_arr | req_sin_stock

    faltante_rot = np.maximum(0.0, np.maximum(stock_obj, master["Min_Unidades"]) - master["Stock"])
    faltante_arr = np.maximum(0.0, master["Min_Unidades"] - master["Stock"])

    master["Faltante"] = np.where(
        req_rot, faltante_rot,
        np.where(req_arr, faltante_arr, 0.0)
    )

    master["Sugerencia_Cajas"] = np.ceil(master["Faltante"] / master["Factor_Pack_Efectivo"])
    master["Unidades_Pedir"] = master["Sugerencia_Cajas"] * master["Factor_Pack_Efectivo"]
    master["Inversion_Est"] = master["Unidades_Pedir"] * master["Costo_Efectivo"]

    # 9. Motivo de sugerencia
    master["Motivo_Sugerencia"] = np.where(
        master["Modo_Demanda"] == "SIN_VENTAS",
        "No hay ventas en 90 días",
        np.where(
            master["Modo_Demanda"] == "ARRANQUE",
            "Venta aislada: solo 1 unidad sugerida",
            np.where(
                master["Requiere_Compra"],
                "Rotación detectada: sugerencia para 8 días",
                "Stock suficiente para 8 días"
            )
        )
    )

    # 10. ABC
    master["Valor_Ventas_90d"] = master["v90"] * master["Precio"]
    master["Clase_ABC"] = _calc_clase_abc(master)
    master["Clase_ABC"] = master["Clase_ABC"].fillna("C").astype(str)


    # 11. GARANTIZAR COLUMNAS CRÍTICAS ANTES DE USARLAS
    cols_garantizadas = {
        "ID_Producto": "", "Nombre": "", "Categoria": "Sin Categoría",
        "Clase_ABC": "C", "Stock": 0.0, "Estado": "✅ OK",
        "Velocidad_Diaria": 0.0, "Margen_%": 0.0,
        "Margen_$": 0.0, "Costo": 0.0, "Precio": 0.0,
        "Nombre_Proveedor": "Sin Asignar", "Sugerencia_Cajas": 0.0,
        "Unidades_Pedir": 0.0, "Inversion_Est": 0.0,
        "Factor_Pack": 1.0, "Costo_Efectivo": 0.0,
        "Dias_Cobertura": 999.0, "Modo_Demanda": "SIN_VENTAS",
        "ID_Producto_Norm": "",
        "Requiere_Compra": False
    }
    for col, default in cols_garantizadas.items():
        if col not in master.columns:
            master[col] = default
        master[col] = master[col].fillna(default) if isinstance(default, str) \
                      else pd.to_numeric(master[col], errors="coerce").fillna(default)

    # 12. ESTADO (ahora seguro)
    conditions = [
        master["Stock"] <= 0,
        (master["Requiere_Compra"]) & (master["Clase_ABC"] == "A"),
        master["Requiere_Compra"],
        (master["Dias_Cobertura"] > 120) & (master["Stock"] > 0),
    ]
    choices = ["💀 AGOTADO", "🚨 CRÍTICO (A)", "⚠️ Comprar", "🧊 Sobre-Stock"]
    master["Estado"] = np.select(conditions, choices, default="✅ OK")

    return master


# ==========================================
# 5. FUNCIONES DE SOPORTE UI
# ==========================================

def descargar_excel_conteo(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Conteo_Fisico")
    except Exception:
        df.to_csv(output, index=False)
    return output.getvalue()


def crear_orden_compra(proveedor: str, items_df: pd.DataFrame) -> str:
    try:
        data = st.session_state.get("data_store", {})
        ws_hist = data.get("ws_Historial_Ordenes")
        if ws_hist is None:
            return "ORD-LOCAL"
        ts = int(time.time())
        orden_id = f"ORD-{ts}"
        items_json = items_df[["Nombre", "Sugerencia_Cajas"]].to_json(orient="records")
        total = float(items_df["Inversion_Est"].sum())
        ws_hist.append_row([
            orden_id, proveedor,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            items_json, total, "Pendiente"
        ])
        return orden_id
    except Exception as e:
        return f"ORD-ERROR-{e}"


def analizar_ventas(df_ven: pd.DataFrame, df_inv: pd.DataFrame) -> dict:
    stats = {}

    try:
        if df_ven is None or df_ven.empty:
            return stats

        df = df_ven.copy()
        col_fecha = _find_col(df, ["Fecha"])
        if col_fecha is None:
            return stats

        df["_fecha"] = pd.to_datetime(df[col_fecha], errors="coerce")
        df = df[df["_fecha"].notna()]

        hoy = pd.Timestamp.now()
        df_90 = df[df["_fecha"] >= hoy - pd.Timedelta(days=90)]
        df_30 = df[df["_fecha"] >= hoy - pd.Timedelta(days=30)]

        col_items = _find_col(df, ["Items", "Items_Detalle", "Productos"])
        if col_items is None:
            return stats

        # Construir todos los posibles identificadores normalizados para cada producto del inventario
        prod_map = {}
        for _, row in df_inv.iterrows():
            keys = set()
            # UID
            if "Producto_UID" in row and str(row["Producto_UID"]).strip():
                keys.add(str(row["Producto_UID"]).strip().lower())
            # Normalizado
            if "ID_Producto_Norm" in row and str(row["ID_Producto_Norm"]).strip():
                keys.add(str(row["ID_Producto_Norm"]).strip().lower())
            # Referencia original
            if "ID_Producto" in row and str(row["ID_Producto"]).strip():
                keys.add(normalizar_id_producto(row["ID_Producto"]).lower())
            # Mapear todos los identificadores a la misma clave
            for k in keys:
                prod_map[k] = keys


        def _sumar_items(df_sub):
            totales = {}
            # Detectar si existe Items_Detalle y usarlo si tiene datos
            col_items_detalle = _find_col(df_sub, ["Items_Detalle"])
            col_items = _find_col(df_sub, ["Items", "Productos"])
            for idx, row in df_sub.iterrows():
                try:
                    items = []
                    # Usar Items_Detalle si existe y tiene datos
                    if col_items_detalle and isinstance(row[col_items_detalle], str) and row[col_items_detalle].strip().startswith("["):
                        items = json.loads(row[col_items_detalle])
                    # Si no, intentar parsear Items
                    elif col_items and isinstance(row[col_items], str):
                        items_str = row[col_items]
                        # String tipo '1.0x Nombre, 2.0x Otro'
                        for part in items_str.split(","):
                            part = part.strip()
                            if "x " in part:
                                try:
                                    cantidad, nombre = part.split("x ", 1)
                                    cantidad = float(cantidad.strip().replace("x", ""))
                                    items.append({"NOMBRE": nombre.strip(), "Cantidad": cantidad})
                                except Exception:
                                    items.append({"NOMBRE": part.strip(), "Cantidad": 1})
                            elif part:
                                items.append({"NOMBRE": part.strip(), "Cantidad": 1})
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        posibles = set()
                        # UID
                        if "Producto_UID" in it and str(it["Producto_UID"]).strip():
                            posibles.add(str(it["Producto_UID"]).strip().lower())
                        # Normalizado
                        if "ID_Producto_Norm" in it and str(it["ID_Producto_Norm"]).strip():
                            posibles.add(str(it["ID_Producto_Norm"]).strip().lower())
                        # Referencia original
                        if "ID_Producto" in it and str(it["ID_Producto"]).strip():
                            posibles.add(normalizar_id_producto(it["ID_Producto"]).lower())
                        # Solo ID (ventas antiguas)
                        if "ID" in it and str(it["ID"]).strip():
                            posibles.add(normalizar_id_producto(it["ID"]).lower())
                        # Por nombre (nuevo)
                        if "NOMBRE" in it and str(it["NOMBRE"]).strip():
                            posibles.add(_norm_col(it["NOMBRE"]))
                        qty = 1.0
                        # Buscar campo de cantidad flexible
                        for qk in ["Cantidad", "cantidad", "qty", "unidades", "cant"]:
                            if qk in it:
                                try:
                                    qty = float(it[qk])
                                    break
                                except:
                                    pass
                        for prod_norm, keys in prod_map.items():
                            if posibles & keys:
                                totales[list(keys)[0]] = totales.get(list(keys)[0], 0.0) + qty
                except Exception:
                    pass
            return totales

        t90 = _sumar_items(df_90)
        t30 = _sumar_items(df_30)

        all_keys = set(t90) | set(t30)
        for k in all_keys:
            stats[k] = {"v90": t90.get(k, 0.0), "v30": t30.get(k, 0.0)}

    except Exception:
        pass
    return stats


# ==========================================
# 6. INTERFAZ PRINCIPAL (ÚNICA Y DEFINITIVA)
# ==========================================

def main():
    # ── SIDEBAR ───────────────────────────────────────────────────────────
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/1864/1864470.png", width=80)
        st.header("Centro de Mando 🐾")

        if "data_store" not in st.session_state:
            cargar_datos_snapshot()

        ultima = st.session_state.get("last_sync", datetime.min)
        st.info(f"Última sinc: {ultima.strftime('%H:%M:%S')}")

        if st.button("🔄 Forzar Sincronización", key="btn_sync_sidebar"):
            st.cache_resource.clear()
            if "data_store" in st.session_state:
                del st.session_state["data_store"]
            cargar_datos_snapshot()
            st.rerun()

        st.markdown("---")
        st.subheader("🎯 Filtros Globales")

        cat_filter, abc_filter = [], []
        if "data_store" in st.session_state:
            df_inv_sb = st.session_state["data_store"].get("df_Inventario", pd.DataFrame())
            col_cat_sb = _find_col(df_inv_sb, ["Categoria", "Categoría"])
            if col_cat_sb:
                cats = sorted(
                    df_inv_sb[col_cat_sb]
                    .fillna("Sin Categoría").astype(str).str.strip()
                    .replace("", "Sin Categoría").unique().tolist()
                )
                cat_filter = st.multiselect("Filtrar por Categoría", cats, default=[])
            abc_filter = st.multiselect("Clasificación ABC", ["A", "B", "C"], default=[])

    # ── GUARD: sin datos ──────────────────────────────────────────────────
    if "data_store" not in st.session_state:
        st.warning("⚠️ No hay datos cargados.")
        if st.button("🔄 Cargar datos ahora", key="btn_load_data_main"):
            cargar_datos_snapshot()
            st.rerun()
        return

    # ── CALCULAR MASTER ───────────────────────────────────────────────────
    try:
        master_df = calcular_master_df()
    except Exception as e:
        st.error(f"❌ Error calculando datos: {e}")
        st.exception(e)
        return

    if master_df is None or master_df.empty:
        st.warning("El inventario está vacío. Agrega productos en la hoja 'Inventario'.")
        return

    # ── FILTROS ───────────────────────────────────────────────────────────
    if cat_filter:
        master_df = master_df[master_df["Categoria"].isin(cat_filter)]
    if abc_filter:
        master_df = master_df[master_df["Clase_ABC"].isin(abc_filter)]

    # ── KPIs ──────────────────────────────────────────────────────────────
    st.title("🐾 Panel Principal de Operaciones")

    valor_inv       = float((master_df["Stock"] * master_df["Costo_Efectivo"]).sum())
    agotados        = int(master_df["Stock"].le(0).sum())
    criticos        = int(master_df["Estado"].eq("🚨 CRÍTICO (A)").sum())
    margen_base_df  = master_df[
        (master_df["Stock"] > 0) &
        (master_df["Precio"] > 0) &
        (master_df["Costo_Efectivo"] > 0) &
        (~master_df["Margen_Anomalo"])
    ].copy()
    if not margen_base_df.empty:
        ventas_potenciales = (margen_base_df["Stock"] * margen_base_df["Precio"]).sum()
        utilidad_potencial = (margen_base_df["Stock"] * (margen_base_df["Precio"] - margen_base_df["Costo_Efectivo"])).sum()
        margen_promedio = float((utilidad_potencial / ventas_potenciales) * 100.0) if ventas_potenciales > 0 else 0.0
    else:
        margen_promedio = 0.0
    alertas_datos = int(master_df[master_df["Alerta_Datos"].ne("OK")].shape[0])

    df_gastos  = st.session_state["data_store"].get("df_Gastos", pd.DataFrame())
    gastos_mes = 0.0
    if not df_gastos.empty:
        col_fecha_g = _find_col(df_gastos, ["Fecha"])
        col_monto_g = _find_col(df_gastos, ["Monto", "Valor"])
        if col_fecha_g and col_monto_g:
            df_gastos["_fecha"] = pd.to_datetime(df_gastos[col_fecha_g], errors="coerce")
            df_gastos[col_monto_g] = pd.to_numeric(df_gastos[col_monto_g], errors="coerce").fillna(0.0)
            gastos_mes = float(
                df_gastos[df_gastos["_fecha"].dt.month == datetime.now().month][col_monto_g].sum()
            )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Capital en Inventario", f"${valor_inv:,.0f}")
    c2.metric("📈 Margen Promedio",        f"{margen_promedio:.1f}%")
    c3.metric("🚨 Alertas de Quiebre",     agotados + criticos)
    c4.metric("💸 Gastos del Mes",         f"${gastos_mes:,.0f}")

    if alertas_datos > 0:
        st.warning(f"Se detectaron {alertas_datos} productos con datos dudosos de costo/precio. El margen promedio excluye esos casos para evitar distorsiones.")

    # ── TABS ──────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📊 Visión 360",
        "🧠 Compras Inteligentes",
        "📥 Recepción",
        "💸 Finanzas & Gastos",
    ])

    # ── TAB 1: VISIÓN 360 ─────────────────────────────────────────────────
    with tabs[0]:
        c_busq, c_est = st.columns([2, 1])
        txt_search = c_busq.text_input("🔍 Búsqueda Rápida (Nombre, SKU, ID)...")
        est_filter = c_est.selectbox(
            "Estado de Stock",
            ["Todos", "💀 AGOTADO", "🚨 CRÍTICO (A)", "⚠️ Comprar", "🧊 Sobre-Stock", "✅ OK"],
        )

        df_view = master_df.copy()
        if txt_search:
            mask = (
                df_view["Nombre"].str.contains(txt_search, case=False, na=False) |
                df_view["ID_Producto_Norm"].str.contains(txt_search, case=False, na=False)
            )
            df_view = df_view[mask]
        if est_filter != "Todos":
            df_view = df_view[df_view["Estado"] == est_filter]

        # Excel conteo físico
        conteo_excel = descargar_excel_conteo(
            df_view[["ID_Producto", "Nombre", "Categoria", "Stock"]].reset_index(drop=True)
        )
        st.download_button(
            "⬇️ Descargar Excel de Conteo Físico",
            data=conteo_excel,
            file_name="Conteo_Fisico_BigotesyPatitas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        cols_vista = [
            "ID_Producto", "Nombre", "Categoria", "Clase_ABC",
            "Stock", "Estado", "Velocidad_Diaria", "Margen_%", "Costo_Efectivo", "Precio", "Alerta_Datos"
        ]
        cols_vista = [c for c in cols_vista if c in df_view.columns]
        st.dataframe(
            df_view[cols_vista],
            column_config={
                "Clase_ABC":        st.column_config.TextColumn("ABC"),
                "Velocidad_Diaria": st.column_config.NumberColumn("Ventas/Día",   format="%.2f"),
                "Margen_%":         st.column_config.NumberColumn("Margen Bruto", format="%.1f%%"),
                "Costo_Efectivo":   st.column_config.NumberColumn("Costo Unit.", format="$%.0f"),
                "Precio":           st.column_config.NumberColumn(format="$%.0f"),
                "Alerta_Datos":     st.column_config.TextColumn("Diagnóstico"),
            },
            use_container_width=True, hide_index=True, height=500,
        )

        with st.expander("Diagnóstico de calidad de datos"):
            diag = master_df[master_df["Alerta_Datos"].ne("OK")].copy()
            if diag.empty:
                st.success("No se detectaron inconsistencias relevantes de costo/precio en inventario.")
            else:
                diag_cols = [
                    "ID_Producto", "Nombre", "Costo_Inventario_Unitario", "Costo_Referencia_Proveedor_Unitario",
                    "Costo_Efectivo", "Precio", "Margen_%", "Alerta_Datos"
                ]
                diag_cols = [c for c in diag_cols if c in diag.columns]
                st.dataframe(
                    diag[diag_cols].sort_values(["Alerta_Datos", "Margen_%"], ascending=[True, True]),
                    column_config={
                        "Costo_Inventario_Unitario": st.column_config.NumberColumn("Costo Inv.", format="$%.0f"),
                        "Costo_Referencia_Proveedor_Unitario": st.column_config.NumberColumn("Costo Prov. Unit.", format="$%.0f"),
                        "Costo_Efectivo": st.column_config.NumberColumn("Costo Efectivo", format="$%.0f"),
                        "Precio": st.column_config.NumberColumn("Precio", format="$%.0f"),
                        "Margen_%": st.column_config.NumberColumn("Margen", format="%.1f%%"),
                    },
                    use_container_width=True,
                    hide_index=True,
                )

    # ── TAB 2: COMPRAS INTELIGENTES ───────────────────────────────────────
    with tabs[1]:
        st.markdown("### 🧠 Sugerencia de Reabastecimiento (8 días)")
        st.info(
            "💡 Cubre **8 días** de stock según rotación real (30/90d). "
            "Productos con 1 venta aislada → modo **ARRANQUE** (solo 1 unidad mínima)."
        )

        df_buy = master_df[master_df["Unidades_Pedir"] > 0].copy()
        # Filtro global por proveedor
        proveedores = sorted(df_buy["Nombre_Proveedor"].dropna().unique().tolist())
        proveedor_sel = st.selectbox("Filtrar por proveedor", ["Todos"] + proveedores, index=0)
        if proveedor_sel != "Todos":
            df_buy = df_buy[df_buy["Nombre_Proveedor"] == proveedor_sel]

        # Garantizar columnas requeridas
        cols_requeridas = [
            "Confirmar", "Nombre_Proveedor", "Clase_ABC", "Nombre",
            "Stock", "Sugerencia_Cajas", "Factor_Pack", "Inversion_Est", "Motivo_Sugerencia"
        ]
        for col in cols_requeridas:
            if col not in df_buy.columns:
                if col == "Confirmar":
                    df_buy[col] = False
                else:
                    df_buy[col] = ""
        # Asegurar tipo booleano para Confirmar
        df_buy["Confirmar"] = df_buy["Confirmar"].astype(bool)

        # Estado de selección masiva
        if "select_all_buy" not in st.session_state:
            st.session_state["select_all_buy"] = False

        c_sel, c_desel = st.columns([1,1])
        if c_sel.button("Seleccionar todos", key="btn_select_all_buy"):
            df_buy["Confirmar"] = True
            st.session_state["select_all_buy"] = True
        if c_desel.button("Deseleccionar todos", key="btn_deselect_all_buy"):
            df_buy["Confirmar"] = False
            st.session_state["select_all_buy"] = False

        if df_buy.empty:
            st.success("🎉 ¡Niveles óptimos! No se sugieren compras ahora.")
            # ✅ Mostrar motivos para los productos que no sugieren compra
            df_no_buy = master_df[master_df["Unidades_Pedir"] == 0].copy()
            if not df_no_buy.empty:
                st.markdown("#### Motivo por el que no se sugiere compra:")
                st.dataframe(df_no_buy[["Nombre", "Stock", "Modo_Demanda", "Motivo_Sugerencia"]], hide_index=True)
        else:
            edited_buy = st.data_editor(
                df_buy[cols_requeridas],
                use_container_width=True, hide_index=True,
                column_config={"Confirmar": st.column_config.CheckboxColumn("Confirmar")}
            )

            seleccion = edited_buy[edited_buy["Confirmar"] == True]
            st.divider()
            st.markdown(f"### Total Inversión Sugerida: :green[${seleccion['Inversion_Est'].sum():,.0f}]")

            for prov in seleccion["Nombre_Proveedor"].unique():
                items_prov = seleccion[seleccion["Nombre_Proveedor"] == prov]
                with st.expander(
                    f"🛒 Proveedor: {prov} | Total: ${items_prov['Inversion_Est'].sum():,.0f}",
                    expanded=True,
                ):
                    st.table(items_prov[["Nombre", "Clase_ABC", "Sugerencia_Cajas", "Inversion_Est"]])
                    c_btn, c_wa = st.columns([1, 4])
                    if c_btn.button(f"Emitir Orden ({prov})", key=f"btn_ord_{prov}"):
                        new_id = crear_orden_compra(prov, items_prov)
                        st.success(f"✅ Orden {new_id} generada.")
                        time.sleep(1)
                        st.rerun()
                    msg_wa = f"Hola {prov}, pedido Bigotes & Patitas:\n"
                    for _, r in items_prov.iterrows():
                        msg_wa += f"- {int(r['Sugerencia_Cajas'])} cajas de {r['Nombre']}\n"
                    c_wa.markdown(
                        f"*(Opcional)* [📲 Enviar por WhatsApp](https://wa.me/?text={quote(msg_wa)})"
                    )

    # ── TAB 3: RECEPCIÓN ──────────────────────────────────────────────────
    with tabs[2]:
        st.info("Para registrar recepciones de mercancía usa el módulo **📥 Compras** del menú lateral.")

    # ── TAB 4: FINANZAS ───────────────────────────────────────────────────
    with tabs[3]:
        st.subheader("💸 Control de Egresos y Márgenes")
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("**Top 5 Productos más Rentables ($)**")
            if "Margen_$" in master_df.columns:
                top_m = master_df[master_df["Margen_$"] > 0].sort_values("Margen_$", ascending=False).head(5)
                st.dataframe(
                    top_m[["Nombre", "Costo", "Precio", "Margen_$"]],
                    hide_index=True,
                    column_config={
                        "Costo":    st.column_config.NumberColumn(format="$%.0f"),
                        "Precio":   st.column_config.NumberColumn(format="$%.0f"),
                        "Margen_$": st.column_config.NumberColumn("Margen $", format="$%.0f"),
                    }
                )

        with col_g2:
            st.markdown("**Resumen de Gastos por Categoría**")
            if not df_gastos.empty:
                col_cat_g = _find_col(df_gastos, ["Categoria", "Categoría", "Tipo"])
                col_mon_g = _find_col(df_gastos, ["Monto", "Valor"])
                if col_cat_g and col_mon_g:
                    resumen_g = (
                        df_gastos.groupby(col_cat_g)[col_mon_g]
                        .sum().reset_index()
                        .sort_values(col_mon_g, ascending=False)
                    )
                    st.dataframe(resumen_g, hide_index=True)
                else:
                    st.info("Columnas de gastos no reconocidas.")
            else:
                st.info("Aún no hay gastos registrados.")

# ==========================================
# 7. ENTRY POINT - Lógica de Ejecución
# ==========================================

if __name__ == "__main__":
    main()