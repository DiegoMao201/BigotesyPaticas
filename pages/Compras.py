import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime
import math
import re
import uuid
from difflib import SequenceMatcher

try:
    # si normalizar_id_producto vive en el módulo principal
    from BigotesyPaticas import normalizar_id_producto
except Exception:
    # fallback defensivo si ya existe localmente con otro nombre
    def normalizar_id_producto(x):
        return str(x or "").strip().upper()

def money_int(val) -> int:
    return int(round(money_float(val)))


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

# ==========================================
# 3. FUNCIONES DE ACTUALIZACIÓN DE MAPEO PROVEEDORES
# ==========================================

def _upsert_maestro_proveedores(ws_map, meta_xml, sku_prov, sku_interno, producto_uid, factor, costo_prov, iva_pct):
    """
    Inserta o actualiza la relación entre SKU_Proveedor, SKU_Interno y Producto_UID en Maestro_Proveedores.
    Si ya existe la fila (por SKU_Proveedor y SKU_Interno), actualiza los datos; si no, inserta una nueva.
    """
    try:
        ordered_headers = [
            "ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Factor_Pack",
            "Ultima_Actualizacion", "Email", "Costo_Proveedor", "Producto_UID", "Ultimo_IVA"
        ]
        headers = _ensure_sheet_schema(ws_map, ordered_headers)
        recs = ws_map.get_all_records()
        df = pd.DataFrame(recs)
        for col in ordered_headers:
            if col not in df.columns:
                df[col] = ""

        mask = (
            (df["SKU_Proveedor"].astype(str).str.strip().str.upper() == str(sku_prov).strip().upper()) &
            (df["SKU_Interno"].astype(str).str.strip().str.upper() == str(sku_interno).strip().upper())
        )
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        id_prov = meta_xml.get("ID_Proveedor", "") if meta_xml else ""
        nombre_prov = meta_xml.get("Nombre_Proveedor") or meta_xml.get("Proveedor", "") if meta_xml else ""
        email = meta_xml.get("Email_Proveedor", "") if meta_xml else ""
        row_map = {
            "ID_Proveedor": id_prov,
            "Nombre_Proveedor": nombre_prov,
            "SKU_Proveedor": sku_prov,
            "SKU_Interno": sku_interno,
            "Factor_Pack": factor,
            "Ultima_Actualizacion": now,
            "Email": email,
            "Costo_Proveedor": costo_prov,
            "Producto_UID": producto_uid,
            "Ultimo_IVA": iva_pct,
        }
        row_data = [row_map.get(header, "") for header in headers]

        if mask.any():
            idx = mask[mask].index[0] + 2
            start_a1 = gspread.utils.rowcol_to_a1(idx, 1)
            end_a1 = gspread.utils.rowcol_to_a1(idx, len(headers))
            ws_map.update(f"{start_a1}:{end_a1}", [row_data])
        else:
            ws_map.append_row(row_data)
    except Exception as e:
        st.warning(f"Error actualizando Maestro_Proveedores: {e}")

def _registrar_gasto_compra(ws_gas, meta_xml, info_pago, total_compra):
    headers = _ensure_sheet_schema(ws_gas, [
        "ID_Gasto", "Fecha", "Tipo_Gasto", "Categoria", "Descripcion", "Monto", "Metodo_Pago", "Banco_Origen"
    ])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gasto_id = f"GAS-{int(time.time())}"
    proveedor = str(meta_xml.get("Proveedor", "")).strip()
    folio = str(meta_xml.get("Folio", "")).strip()
    descripcion = f"[PROV: {proveedor}] [REF: {folio}] - Compra Mercancía"
    row_map = {
        "ID_Gasto": gasto_id,
        "Fecha": now,
        "Tipo_Gasto": "Variable",
        "Categoria": "Compra Inventario",
        "Descripcion": descripcion,
        "Monto": total_compra,
        "Metodo_Pago": info_pago.get("Origen", ""),
        "Banco_Origen": info_pago.get("Origen", ""),
    }
    ws_gas.append_row([row_map.get(header, "") for header in headers])
# 1. CONFIGURACIÓN Y ESTILOS (NEXUS PRO THEME)
# ==========================================

COLOR_PRIMARIO = "#187f77"      # Cian Oscuro
COLOR_SECUNDARIO = "#125e58"    # Variante oscura
COLOR_ACENTO = "#f5a641"        # Naranja
COLOR_FONDO = "#f8f9fa"         # Gris claro
COLOR_BLANCO = "#ffffff"

st.set_page_config(
    page_title="Compras & Recepción | Nexus Pro", 
    page_icon="📥", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    .stApp {{ background-color: {COLOR_FONDO}; font-family: 'Inter', sans-serif; }}
    
    h1, h2, h3 {{ color: {COLOR_PRIMARIO}; font-weight: 700; }}
    
    .main-header {{ 
        font-size: 2.5rem; 
        font-weight: 800; 
        color: {COLOR_PRIMARIO}; 
        margin-top: 1rem;
        margin-bottom: 0.5rem; 
        text-align: center; 
    }}
    
    .sub-header {{ 
        font-size: 1.1rem; 
        color: #64748b; 
        margin-bottom: 2rem; 
        text-align: center; 
    }}

    .metric-container {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }}
    .metric-card {{
        background-color: {COLOR_BLANCO};
        border-radius: 12px;
        padding: 20px;
        width: 30%;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid {COLOR_ACENTO};
        text-align: center;
    }}
    .metric-label {{ color: #64748b; font-size: 0.85rem; text-transform: uppercase; font-weight: 600; margin-bottom: 5px; }}
    .metric-value {{ color: {COLOR_PRIMARIO}; font-size: 1.5rem; font-weight: 800; }}

    .stButton>button {{ border-radius: 8px; font-weight: bold; height: 3rem; transition: all 0.3s ease; }}
    div[data-testid="stExpander"] {{ background-color: {COLOR_BLANCO}; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: none; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UTILIDADES MATEMÁTICAS
# ==========================================

MARGEN_BRUTO_OBJ = 0.20  # 20%

def precio_con_margen(costo_neto_unit: float, margen: float = MARGEN_BRUTO_OBJ) -> float:
    """Margen bruto sobre precio: P = C / (1 - m)."""
    try:
        c = float(costo_neto_unit or 0.0)
        m = float(margen or 0.0)
        if c <= 0:
            return 0.0
        m = max(0.0, min(0.95, m))
        return c / (1.0 - m)
    except Exception:
        return 0.0

def _fmt_qty(x):
    """Evita 1.0, 2.0 cuando son enteros."""
    try:
        f = float(x)
        return int(f) if f.is_integer() else f
    except Exception:
        return x

def _get_meta_safe():
    """Meta robusto (evita KeyError en step 2)."""
    meta = st.session_state.get("invoice_meta") or {}
    return {
        "Proveedor": meta.get("Proveedor", "").strip(),
        "ID_Proveedor": meta.get("ID_Proveedor", "").strip(),
        "Folio": meta.get("Folio", "").strip(),
        "Total": money_int(meta.get("Total", 0)),
    }

def normalizar_str(valor):
    if pd.isna(valor) or valor == "": return ""
    # Eliminar espacios internos y convertir a mayúsculas
    return str(valor).replace(" ","").strip().upper()


def normalizar_nombre_producto(valor) -> str:
    s = str(valor or "").upper().strip()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def tokens_nombre_producto(valor) -> set[str]:
    stopwords = {
        "DE", "DEL", "LA", "EL", "LOS", "LAS", "PARA", "CON", "SIN", "Y", "EN", "POR",
        "UND", "UN", "U", "X"
    }
    tokens = []
    for tok in normalizar_nombre_producto(valor).split():
        if len(tok) <= 1:
            continue
        if tok in stopwords:
            continue
        tokens.append(tok)
    return set(tokens)


def score_match_producto(nombre_origen: str, nombre_destino: str) -> float:
    src = normalizar_nombre_producto(nombre_origen)
    dst = normalizar_nombre_producto(nombre_destino)
    if not src or not dst:
        return 0.0
    if src == dst:
        return 1.0

    src_tokens = tokens_nombre_producto(src)
    dst_tokens = tokens_nombre_producto(dst)
    overlap = len(src_tokens & dst_tokens) / max(len(src_tokens | dst_tokens), 1)
    seq_ratio = SequenceMatcher(None, src, dst).ratio()
    contains_bonus = 1.0 if (src in dst or dst in src) else 0.0
    return (seq_ratio * 0.55) + (overlap * 0.35) + (contains_bonus * 0.10)


def safe_text(node, default=""):
    return str(node.text).strip() if node is not None and node.text is not None else default

def clean_currency(val):
    return money_int(val)

def sanitizar_para_sheet(val):
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    return val

def redondear_centena(valor):
    if not valor: return 0.0
    return math.ceil(valor / 100.0) * 100.0

# ==========================================
# 3. CONEXIÓN A GOOGLE SHEETS
# ==========================================

def _ensure_headers(ws, required_cols: list[str]) -> list[str]:
    """
    Asegura que existan columnas en la fila 1 (headers) de una worksheet.
    Retorna la lista final de headers.
    """
    headers = ws.row_values(1) or []
    headers = [h.strip() for h in headers]

    changed = False
    for col in required_cols:
        if col not in headers:
            headers.append(col)
            ws.update_cell(1, len(headers), col)
            changed = True

    return ws.row_values(1) if changed else headers

def _ensure_sheet_schema(ws, ordered_headers: list[str]) -> list[str]:
    """
    Asegura que la hoja tenga los encabezados requeridos en el orden indicado.
    Si la hoja ya tiene datos con otro orden, reescribe la tabla preservando los valores por nombre de columna.
    """
    values = ws.get_all_values() or []
    if not values:
        ws.update("A1", [ordered_headers])
        return ordered_headers

    current_headers = [str(h).strip() for h in values[0]]
    extras = [h for h in current_headers if h and h not in ordered_headers]
    final_headers = ordered_headers + extras

    if current_headers == final_headers:
        return final_headers

    if len(values) == 1:
        ws.update("A1", [final_headers])
        return final_headers

    rewritten_rows = [final_headers]
    for raw_row in values[1:]:
        row_map = {
            header: raw_row[idx] if idx < len(raw_row) else ""
            for idx, header in enumerate(current_headers)
        }
        rewritten_rows.append([row_map.get(header, "") for header in final_headers])

    ws.clear()
    ws.update("A1", rewritten_rows)
    return final_headers

def _build_inv_indexes(ws_inv):
    """
    Índices para Inventario (Sheets) usados por compras XML/manual.
    Retorna: headers, idx_uid, idx_id, idx_norm, idx_stock, idx_costo, idx_precio, idx_nombre, uid_to_row, norm_to_row, norm_to_uid
    """
    headers = _ensure_headers(
        ws_inv,
        ["Producto_UID", "ID_Producto", "ID_Producto_Norm", "SKU_Proveedor", "Nombre", "Stock", "Costo", "Precio", "Categoria", "Iva"]
    )

    data = ws_inv.get_all_values() or []
    if not data:
        idx_uid = headers.index("Producto_UID")
        idx_id = headers.index("ID_Producto")
        idx_norm = headers.index("ID_Producto_Norm")
        idx_sku_prov = headers.index("SKU_Proveedor") if "SKU_Proveedor" in headers else None
        idx_nombre = headers.index("Nombre")
        idx_stock = headers.index("Stock")
        idx_costo = headers.index("Costo")
        idx_precio = headers.index("Precio")
        idx_categoria = headers.index("Categoria") if "Categoria" in headers else None
        idx_iva = headers.index("Iva") if "Iva" in headers else None
        return (headers, idx_uid, idx_id, idx_norm, idx_sku_prov, idx_stock, idx_costo, idx_precio, idx_nombre, idx_categoria, idx_iva, {}, {}, {})

    headers = data[0]

    # Reasegurar por si la fila 1 está vacía en la hoja
    if "Producto_UID" not in headers or "ID_Producto" not in headers or "ID_Producto_Norm" not in headers:
        headers = _ensure_headers(
            ws_inv,
            ["Producto_UID", "ID_Producto", "ID_Producto_Norm", "SKU_Proveedor", "Nombre", "Stock", "Costo", "Precio", "Categoria", "Iva"]
        )
        data = ws_inv.get_all_values() or []
        headers = data[0] if data else headers

    idx_uid = headers.index("Producto_UID")
    idx_id = headers.index("ID_Producto")
    idx_norm = headers.index("ID_Producto_Norm")
    idx_sku_prov = headers.index("SKU_Proveedor") if "SKU_Proveedor" in headers else None
    idx_nombre = headers.index("Nombre") if "Nombre" in headers else None
    idx_stock = headers.index("Stock") if "Stock" in headers else None
    idx_costo = headers.index("Costo") if "Costo" in headers else None
    idx_precio = headers.index("Precio") if "Precio" in headers else None
    idx_categoria = headers.index("Categoria") if "Categoria" in headers else None
    idx_iva = headers.index("Iva") if "Iva" in headers else None

    uid_to_row, norm_to_row, norm_to_uid = {}, {}, {}

    for sheet_row, r in enumerate(data[1:], start=2):
        uid = str(r[idx_uid]).strip() if idx_uid < len(r) else ""
        pid = str(r[idx_id]).strip() if idx_id < len(r) else ""
        norm = str(r[idx_norm]).strip() if idx_norm < len(r) else ""

        if not norm and pid:
            norm = normalizar_str(pid) # Fallback simple

        if uid:
            uid_to_row[uid] = sheet_row
        if norm:
            norm_to_row[norm] = sheet_row
        if uid and norm:
            norm_to_uid[norm] = uid

    return (
        headers,
        idx_uid, idx_id, idx_norm, idx_sku_prov, idx_stock, idx_costo, idx_precio, idx_nombre, idx_categoria, idx_iva,
        uid_to_row, norm_to_row, norm_to_uid
    )

@st.cache_resource(ttl=600)
def conectar_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración en secrets.toml")
            st.stop()

        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])

        try:
            ws_inv = sh.worksheet("Inventario")
        except:
            st.error("Falta hoja 'Inventario'")
            st.stop()

        # ✅ ya no falla: helper existe
        _ensure_headers(ws_inv, ["Producto_UID", "ID_Producto", "ID_Producto_Norm", "SKU_Proveedor", "Stock", "Costo", "Precio", "Nombre", "Categoria", "Iva"])

        try: ws_map = sh.worksheet("Maestro_Proveedores")
        except:
            ws_map = sh.add_worksheet("Maestro_Proveedores", 1000, 10)
            ws_map.append_row([
                "ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor",
                "SKU_Interno", "Factor_Pack", "Ultima_Actualizacion",
                "Email", "Costo_Proveedor", "Producto_UID", "Ultimo_IVA"
            ])

        _ensure_sheet_schema(ws_map, [
            "ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Factor_Pack",
            "Ultima_Actualizacion", "Email", "Costo_Proveedor", "Producto_UID", "Ultimo_IVA"
        ])

        try: ws_hist = sh.worksheet("Historial_Recepciones")
        except:
            ws_hist = sh.add_worksheet("Historial_Recepciones", 1000, 24)

        _ensure_sheet_schema(ws_hist, [
            "Fecha", "Folio", "Proveedor", "Items", "Total", "Usuario", "Estado",
            "Recepcion_ID", "ID_Proveedor", "Producto_UID", "SKU_Interno", "SKU_Proveedor", "Nombre_Producto",
            "Cantidad_Pack", "Factor_Pack", "Unidades", "Costo_Unitario", "Costo_Total", "Precio_Unitario",
            "IVA_Porcentaje", "Origen", "Transporte_Prorrateado", "Descuento_Prorrateado"
        ])
        
        try: ws_gas = sh.worksheet("Gastos")
        except:
            ws_gas = sh.add_worksheet("Gastos", 1000, 8)
            ws_gas.append_row(["ID_Gasto","Fecha","Tipo_Gasto","Categoria","Descripcion","Monto","Metodo_Pago","Banco_Origen"])

        _ensure_sheet_schema(ws_gas, [
            "ID_Gasto", "Fecha", "Tipo_Gasto", "Categoria", "Descripcion", "Monto", "Metodo_Pago", "Banco_Origen"
        ])

        return sh, ws_inv, ws_map, ws_hist, ws_gas
    except Exception as e:
        st.error(f"Error Conexión Sheets: {e}")
        st.stop()

# ==========================================
# 4. CEREBRO Y MEMORIA
# ==========================================

@st.cache_data(ttl=120)
def cargar_proveedores(_ws_map) -> tuple[list[str], dict[str, str]]:
    """
    Retorna:
      - lista_nombres (para selectbox)
      - nombre_to_id (Nombre_Proveedor -> ID_Proveedor)
    """
    try:
        recs = _ws_map.get_all_records()
        if not recs:
            return (["(Nuevo proveedor)"], {})
        df = pd.DataFrame(recs)
        if "Nombre_Proveedor" not in df.columns:
            return (["(Nuevo proveedor)"], {})
        df["Nombre_Proveedor"] = df["Nombre_Proveedor"].fillna("").astype(str).str.strip()
        if "ID_Proveedor" in df.columns:
            df["ID_Proveedor"] = df["ID_Proveedor"].fillna("").astype(str).str.strip()
        df = df[df["Nombre_Proveedor"] != ""].drop_duplicates(subset=["Nombre_Proveedor"])
        nombres = sorted(df["Nombre_Proveedor"].tolist())
        nombres = ["(Nuevo proveedor)"] + nombres
        nombre_to_id = {}
        if "ID_Proveedor" in df.columns:
            nombre_to_id = dict(zip(df["Nombre_Proveedor"], df["ID_Proveedor"]))
        return (nombres, nombre_to_id)
    except Exception:
        return (["(Nuevo proveedor)"], {})

@st.cache_data(ttl=60)
def cargar_cerebro(_ws_inv, _ws_map):
    try:
        d_inv = _ws_inv.get_all_records()
        df_inv = pd.DataFrame(d_inv)
        col_id = next((c for c in df_inv.columns if 'ID' in c or 'SKU' in c), 'ID_Producto')
        col_nm = next((c for c in df_inv.columns if 'Nombre' in c), 'Nombre')
        df_inv['Display'] = df_inv[col_id].astype(str) + " | " + df_inv[col_nm].astype(str)
        lista_prods = sorted(df_inv['Display'].unique().tolist())
        lista_prods.insert(0, "NUEVO (Crear Producto)")
        dict_prods = pd.Series(df_inv['Display'].values, index=df_inv[col_id].apply(normalizar_id_producto)).to_dict()
    except:
        lista_prods, dict_prods = ["NUEVO (Crear Producto)"], {}

    memoria = {}
    try:
        d_map = _ws_map.get_all_records()
        for r in d_map:
            k = f"{normalizar_str(r.get('ID_Proveedor'))}_{normalizar_str(r.get('SKU_Proveedor'))}"
            iva_guardado = r.get('Ultimo_IVA')
            iva_val = int(float(iva_guardado)) if iva_guardado in [0, 5, 19, "0", "5", "19", 0.0, 5.0, 19.0] else 0
            memoria[k] = {
                "SKU_Interno": normalizar_str(r.get("SKU_Interno")),
                "Producto_UID": str(r.get("Producto_UID", "")).strip(),   # ✅ NUEVO
                "Factor": float(r.get("Factor_Pack", 1)) if r.get("Factor_Pack") else 1.0,
                "IVA_Aprendido": iva_val
            }
    except:
        pass

    return lista_prods, dict_prods, memoria


@st.cache_data(ttl=60)
def cargar_catalogo_inventario(_ws_inv):
    try:
        df_inv = pd.DataFrame(_ws_inv.get_all_records())
        if df_inv.empty:
            return []

        col_id = "ID_Producto" if "ID_Producto" in df_inv.columns else next((c for c in df_inv.columns if 'ID' in c or 'SKU' in c), 'ID_Producto')
        col_nm = "Nombre" if "Nombre" in df_inv.columns else next((c for c in df_inv.columns if 'Nombre' in c), 'Nombre')
        col_cat = "Categoria" if "Categoria" in df_inv.columns else ("Categoría" if "Categoría" in df_inv.columns else None)
        col_iva = "Iva" if "Iva" in df_inv.columns else ("IVA" if "IVA" in df_inv.columns else None)

        catalogo = []
        for _, row in df_inv.iterrows():
            sku = str(row.get(col_id, "")).strip()
            nombre = str(row.get(col_nm, "")).strip()
            if not sku and not nombre:
                continue
            catalogo.append({
                "display": f"{sku} | {nombre}" if sku else nombre,
                "sku": sku,
                "sku_norm": normalizar_id_producto(sku),
                "nombre": nombre,
                "nombre_norm": normalizar_nombre_producto(nombre),
                "uid": str(row.get("Producto_UID", "")).strip(),
                "categoria": str(row.get(col_cat, "Sin Categoría")).strip() if col_cat else "Sin Categoría",
                "iva": float(money_float(row.get(col_iva, 0))) if col_iva else 0.0,
            })
        return catalogo
    except Exception:
        return []


def buscar_producto_en_catalogo(catalogo, sku_interno="", producto_uid="", nombre=""):
    sku_norm = normalizar_id_producto(sku_interno)
    nombre_norm = normalizar_nombre_producto(nombre)
    for prod in catalogo:
        if producto_uid and prod.get("uid") and prod.get("uid") == producto_uid:
            return prod
        if sku_norm and prod.get("sku_norm") == sku_norm:
            return prod
        if nombre_norm and prod.get("nombre_norm") == nombre_norm:
            return prod
    return None


def sugerir_producto_para_item(meta, item, memoria, catalogo):
    nit_prov_norm = normalizar_str(meta.get('ID_Proveedor', ''))
    sku_prov_norm = normalizar_str(item.get('SKU_Proveedor', 'S/C'))
    nombre_item = str(item.get('Descripcion', '') or '').strip()
    clave_memoria = f"{nit_prov_norm}_{sku_prov_norm}"

    sugerencia = {
        "display": "NUEVO (Crear Producto)",
        "nombre": nombre_item,
        "categoria": "Sin Categoría",
        "iva": 0.0,
        "factor": 1.0,
        "motivo": "Nuevo producto"
    }

    recuerdo = memoria.get(clave_memoria)
    if recuerdo is None and sku_prov_norm != "S/C":
        recuerdo = next((r for k, r in memoria.items() if k.endswith(f"_{sku_prov_norm}")), None)

    if recuerdo:
        prod = buscar_producto_en_catalogo(
            catalogo,
            sku_interno=recuerdo.get("SKU_Interno", ""),
            producto_uid=recuerdo.get("Producto_UID", ""),
            nombre=nombre_item,
        )
        if prod:
            sugerencia.update({
                "display": prod.get("display", sugerencia["display"]),
                "nombre": prod.get("nombre", sugerencia["nombre"]),
                "categoria": prod.get("categoria") or "Sin Categoría",
                "iva": float(recuerdo.get("IVA_Aprendido", prod.get("iva", 0.0)) or 0.0),
                "factor": float(recuerdo.get("Factor", 1.0) or 1.0),
                "motivo": "Memoria de proveedor"
            })
            return sugerencia

    if sku_prov_norm and sku_prov_norm != "S/C":
        prod = next((p for p in catalogo if p.get("sku_norm") == sku_prov_norm), None)
        if prod:
            sugerencia.update({
                "display": prod.get("display", sugerencia["display"]),
                "nombre": prod.get("nombre", sugerencia["nombre"]),
                "categoria": prod.get("categoria") or "Sin Categoría",
                "iva": float(prod.get("iva", 0.0) or 0.0),
                "motivo": "SKU proveedor coincide con inventario"
            })
            return sugerencia

    nombre_norm = normalizar_nombre_producto(nombre_item)
    prod_nombre = next((p for p in catalogo if p.get("nombre_norm") == nombre_norm), None)
    if prod_nombre:
        sugerencia.update({
            "display": prod_nombre.get("display", sugerencia["display"]),
            "nombre": prod_nombre.get("nombre", sugerencia["nombre"]),
            "categoria": prod_nombre.get("categoria") or "Sin Categoría",
            "iva": float(prod_nombre.get("iva", 0.0) or 0.0),
            "motivo": "Nombre exacto inventario"
        })
        return sugerencia

    mejor = None
    mejor_score = 0.0
    for prod in catalogo:
        score = score_match_producto(nombre_item, prod.get("nombre", ""))
        if score > mejor_score:
            mejor_score = score
            mejor = prod

    if mejor is not None and mejor_score >= 0.62:
        sugerencia.update({
            "display": mejor.get("display", sugerencia["display"]),
            "nombre": mejor.get("nombre", sugerencia["nombre"]),
            "categoria": mejor.get("categoria") or "Sin Categoría",
            "iva": float(mejor.get("iva", 0.0) or 0.0),
            "motivo": f"Coincidencia sugerida ({mejor_score:.0%})"
        })

    return sugerencia

# ==========================================
# 5. PARSER XML COLOMBIA
# ==========================================

def parsear_xml_colombia(archivo):
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        ns_map = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }

        invoice_root = root
        if 'AttachedDocument' in root.tag:
            desc_node = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
            if desc_node is not None and desc_node.text and "<Invoice" in desc_node.text:
                xml_string = desc_node.text.strip()
                xml_string = xml_string[xml_string.find("<Invoice"):]
                invoice_root = ET.fromstring(xml_string)

        ns = ns_map 
        try:
            prov_node = invoice_root.find('.//cac:AccountingSupplierParty/cac:Party', ns)
            prov_tax = prov_node.find('.//cac:PartyTaxScheme', ns)
            nombre_prov = safe_text(prov_tax.find('cbc:RegistrationName', ns), "Proveedor Desconocido")
            nit_prov = safe_text(prov_tax.find('cbc:CompanyID', ns), "000000")
        except:
            nombre_prov = "Proveedor Desconocido"
            nit_prov = "000000"

        email_prov = safe_text(invoice_root.find('.//cac:AccountingSupplierParty//cbc:ElectronicMail', ns), "")

        try: folio = safe_text(invoice_root.find('cbc:ID', ns), "S/F")
        except: folio = "S/F"

        try: total_pagar_factura = money_int(safe_text(invoice_root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns), 0))
        except: total_pagar_factura = 0

        items = []
        lines = invoice_root.findall('.//cac:InvoiceLine', ns)
        
        for line in lines:
            try:
                qty = money_float(safe_text(line.find('cbc:InvoicedQuantity', ns), 0))
                if qty <= 0:
                    qty = 1.0

                price_node = line.find('.//cac:Price/cbc:PriceAmount', ns)
                base_qty_node = line.find('.//cac:Price/cbc:BaseQuantity', ns)
                price_base_qty = money_float(safe_text(base_qty_node, 1)) or 1.0

                if price_node is not None and safe_text(price_node, ""):
                    base_price = money_float(price_node.text)
                else:
                    line_extension = money_float(safe_text(line.find('cbc:LineExtensionAmount', ns), 0))
                    divisor = qty if qty > 0 else 1.0
                    base_price = line_extension / divisor

                if price_base_qty > 0 and abs(price_base_qty - qty) < 0.0001 and qty > 0:
                    base_price = base_price / qty
                
                discount_amount = 0.0
                allowances = line.findall('.//cac:AllowanceCharge', ns)
                if allowances:
                    for allowance in allowances:
                        charge_indicator = safe_text(allowance.find('cbc:ChargeIndicator', ns), "false").lower()
                        val = money_float(safe_text(allowance.find('cbc:Amount', ns), 0))
                        if charge_indicator == 'false':
                            discount_amount += val
                        else:
                            discount_amount -= val

                final_base_price = money_int(base_price - (discount_amount / max(qty, 1.0)))
                
                item_node = line.find('cac:Item', ns)
                desc = safe_text(item_node.find('cbc:Description', ns), "Producto XML")

                iva_pct = money_float(safe_text(line.find('.//cac:TaxCategory/cbc:Percent', ns), 0))
                
                sku_prov = "S/C"
                std_id = item_node.find('.//cac:StandardItemIdentification/cbc:ID', ns)
                seller_id = item_node.find('.//cac:SellersItemIdentification/cbc:ID', ns)
                line_id = line.find('cbc:ID', ns)
                
                if std_id is not None and std_id.text: sku_prov = std_id.text
                elif seller_id is not None and seller_id.text: sku_prov = seller_id.text
                elif line_id is not None and line_id.text: sku_prov = line_id.text
                
                items.append({
                    'SKU_Proveedor': sku_prov,
                    'Descripcion': desc,
                    'Cantidad': qty,
                    'Costo_Base_Unitario': final_base_price,
                    'IVA_Porcentaje': iva_pct,
                })
            except Exception:
                continue

        return {
            'Proveedor': nombre_prov,
            'ID_Proveedor': nit_prov,
            'Email_Proveedor': email_prov,
            'Folio': folio,
            'Total': total_pagar_factura,
            'Items': items
        }

    except Exception as e:
        st.error(f"Error parseando XML: {e}")
        return None

# ==========================================
# 6. LÓGICA DE GUARDADO
# ==========================================

def procesar_guardado(ws_map, ws_inv, ws_hist, ws_gas, df_final, meta_xml, info_pago):
    logs = []

    if not isinstance(df_final, pd.DataFrame):
        return False, ["Error: df_final no es un DataFrame."]
    if df_final.empty:
        return False, ["Error: df_final está vacío."]
    if not isinstance(meta_xml, dict):
        return False, ["Error: meta_xml no es un dict."]
    if not isinstance(info_pago, dict):
        return False, ["Error: info_pago no es un dict."]

    for campo in ["Origen", "Transporte", "Descuento"]:
        if campo not in info_pago:
            return False, [f"Error: Falta campo '{campo}' en info_pago."]

    if "SKU_Interno_Seleccionado" not in df_final.columns:
        return False, ["Falta columna SKU_Interno_Seleccionado en df_final (selección del usuario)."]

    try:
        (inv_headers, idx_uid, idx_id, idx_norm, idx_sku_prov, idx_stock, idx_costo, idx_precio, idx_nombre, idx_categoria, idx_iva,
         uid_to_row, norm_to_row, norm_to_uid) = _build_inv_indexes(ws_inv)

        total_items = len(df_final)
        pr_trans = float(info_pago.get("Transporte", 0.0) or 0.0)
        pr_desc = float(info_pago.get("Descuento", 0.0) or 0.0)
        updates = []
        appends = []
        hist_rows = []
        recepcion_id = f"REC-{int(time.time())}"

        for _, row in df_final.iterrows():
            sel = str(row.get("SKU_Interno_Seleccionado", "")).strip()
            sku_prov = str(row.get("SKU_Proveedor", "")).strip()
            item_label = sku_prov or str(row.get("Descripcion", "")).strip() or sel or "ITEM"

            factor = float(row.get("Factor_Pack", 1) or 1)
            if factor <= 0:
                factor = 1.0

            cant_pack = float(row.get("Cantidad_Recibida", 0) or 0)
            iva_pct = float(row.get("IVA_Porcentaje", 0) or 0)
            costo_base_xml = money_int(row.get("Costo_Base_Unitario", 0))
            pr_item_trans = (pr_trans / total_items) if total_items else 0.0
            pr_item_desc = (pr_desc / total_items) if total_items else 0.0

            costo_base_unit = (costo_base_xml + pr_item_trans - pr_item_desc) / factor
            iva_unit = costo_base_unit * (iva_pct / 100.0)
            costo_neto_unit = money_int(costo_base_unit + iva_unit)
            unidades = cant_pack * factor

            precio_editado = row.get("Precio_Sugerido", None)
            precio_auto_original = row.get("_Precio_Auto_Unitario", None)
            factor_inicial = row.get("_Factor_Pack_Inicial", factor)
            try:
                precio_editado = float(precio_editado) if precio_editado not in (None, "", "None") else 0.0
            except Exception:
                precio_editado = 0.0
            try:
                precio_auto_original = float(precio_auto_original) if precio_auto_original not in (None, "", "None") else 0.0
            except Exception:
                precio_auto_original = 0.0
            try:
                factor_inicial = float(factor_inicial) if factor_inicial not in (None, "", "None") else factor
            except Exception:
                factor_inicial = factor

            precio_unitario_calculado = redondear_centena(precio_con_margen(costo_neto_unit, MARGEN_BRUTO_OBJ))
            factor_modificado = abs(float(factor) - float(factor_inicial)) > 0.0001

            if precio_editado <= 0:
                precio_final = precio_unitario_calculado
            elif factor_modificado and precio_auto_original > 0 and abs(precio_editado - precio_auto_original) < 0.01:
                precio_final = money_int(precio_unitario_calculado)
                logs.append(f"PRECIO RECALCULADO por factor: {item_label} -> {precio_final}")
            elif factor > 1 and precio_unitario_calculado > 0 and precio_editado >= (precio_unitario_calculado * factor * 0.7):
                precio_final = money_int(redondear_centena(precio_editado / factor))
                logs.append(f"PRECIO NORMALIZADO a unitario: {item_label} {precio_editado} / factor {factor} = {precio_final}")
            else:
                precio_final = money_int(precio_editado)

            es_nuevo = ("NUEVO" in sel.upper()) or (sel == "") or sel.upper().startswith("NUEVO")
            if es_nuevo:
                sku_interno = sku_prov if sku_prov and sku_prov != "S/C" else f"N-{int(time.time())}"
                producto_uid = uuid.uuid4().hex
            else:
                sku_interno = sel.split(" | ")[0].strip()
                producto_uid = norm_to_uid.get(normalizar_id_producto(sku_interno), "")

            sku_norm = normalizar_id_producto(sku_interno)
            nombre_inventario = str(row.get("Nombre_Inventario", row.get("Descripcion", ""))).strip()
            categoria = str(row.get("Categoría", row.get("Categoria", "Sin Categoría"))).strip() or "Sin Categoría"

            if sku_prov and sku_prov != "S/C":
                costo_prov_pack = money_int(costo_neto_unit * factor)
                _upsert_maestro_proveedores(
                    ws_map=ws_map,
                    meta_xml=meta_xml,
                    sku_prov=sku_prov,
                    sku_interno=sku_interno,
                    producto_uid=producto_uid,
                    factor=factor,
                    costo_prov=costo_prov_pack,
                    iva_pct=iva_pct,
                )

            fila = uid_to_row.get(producto_uid) if producto_uid else None
            if fila is None and sku_norm:
                fila = norm_to_row.get(sku_norm)

            if fila is not None and not producto_uid:
                producto_uid = uuid.uuid4().hex
                updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_uid + 1), "values": [[producto_uid]]})
                updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_norm + 1), "values": [[sku_norm]]})
                logs.append(f"CURADO inventario: {sku_interno} ahora tiene UID {producto_uid[:8]}...")

            nombre_historial = nombre_inventario
            if fila is not None:
                fila_actual = ws_inv.row_values(fila)
                if idx_nombre is not None and idx_nombre < len(fila_actual) and str(fila_actual[idx_nombre]).strip():
                    nombre_historial = str(fila_actual[idx_nombre]).strip()

            if fila is None:
                new_row = [""] * len(inv_headers)
                new_row[idx_id] = sku_interno
                new_row[idx_uid] = producto_uid
                new_row[idx_norm] = sku_norm
                if idx_sku_prov is not None:
                    new_row[idx_sku_prov] = sku_prov

                if idx_nombre is not None:
                    new_row[idx_nombre] = nombre_inventario
                if idx_stock is not None:
                    new_row[idx_stock] = str(unidades)
                if idx_costo is not None:
                    new_row[idx_costo] = str(money_int(costo_neto_unit))
                if idx_precio is not None:
                    new_row[idx_precio] = str(money_int(precio_final))
                if idx_categoria is not None:
                    new_row[idx_categoria] = categoria
                if idx_iva is not None:
                    new_row[idx_iva] = str(iva_pct)

                appends.append(new_row)
                logs.append(f"CREADO inventario: {sku_interno} | UID {producto_uid[:8]}... (+{unidades})")
            else:
                stock_actual = 0.0
                if idx_stock is not None:
                    try:
                        valor_stock = ws_inv.cell(fila, idx_stock + 1).value
                        stock_actual = float(str(valor_stock).replace(",", "").strip() or 0)
                    except Exception:
                        stock_actual = 0.0

                nuevo_stock = stock_actual + unidades
                if idx_stock is not None:
                    updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_stock + 1), "values": [[nuevo_stock]]})
                if idx_costo is not None:
                    updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_costo + 1), "values": [[money_int(costo_neto_unit)]]})
                if idx_precio is not None:
                    updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_precio + 1), "values": [[money_int(precio_final)]]})
                updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_uid + 1), "values": [[producto_uid]]})
                updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_norm + 1), "values": [[sku_norm]]})
                logs.append(f"ACTUALIZADO inventario: {sku_interno} | UID {producto_uid[:8]}... Stock {stock_actual}->{nuevo_stock}")

            hist_rows.append([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(meta_xml.get("Folio", "")),
                str(meta_xml.get("Proveedor", "")),
                len(df_final),
                money_int(meta_xml.get("Total", 0)),
                "Admin Nexus",
                "OK",
                recepcion_id,
                str(meta_xml.get("ID_Proveedor", "")),
                producto_uid,
                sku_interno,
                sku_prov,
                nombre_historial,
                _fmt_qty(cant_pack),
                _fmt_qty(factor),
                _fmt_qty(unidades),
                money_int(costo_neto_unit),
                money_int(costo_neto_unit * unidades),
                money_int(precio_final),
                iva_pct,
                str(info_pago.get("Origen", "")),
                money_int(pr_item_trans),
                money_int(pr_item_desc),
            ])

        if updates:
            ws_inv.batch_update(updates)
        if appends:
            ws_inv.append_rows(appends)
        if hist_rows:
            ws_hist.append_rows(hist_rows)

        total_compra = money_int(meta_xml.get("Total", 0))
        _registrar_gasto_compra(ws_gas, meta_xml, info_pago, total_compra)

        return True, logs
    except Exception as e:
        return False, [f"Error del Sistema: {e}"]

# ==========================================
# 7. INTERFAZ PRINCIPAL (STREAMLIT) - REFACTORIZADA
# ==========================================

def main():
    st.markdown('<div class="main-header">Recepción & Compras 📥</div>', unsafe_allow_html=True)
    
    # === CONTROL DE ESTADOS ===
    if 'step' not in st.session_state: st.session_state.step = 1
    if 'invoice_meta' not in st.session_state: st.session_state.invoice_meta = {}
    if 'invoice_items' not in st.session_state: st.session_state.invoice_items = []

    # Conexión
    sh, ws_inv, ws_map, ws_hist, ws_gas = conectar_sheets()

    # ✅ Botón para recargar catálogo (cuando alguien cambia Sheets)
    cR1, cR2 = st.columns([1, 3])
    if cR1.button("🔄 Recargar catálogo", help="Recarga Inventario/Proveedores/Memory"):
        st.cache_data.clear()
        for k in ["lst_prods_cache", "dct_prods_cache", "memoria_cache", "proveedores_cache", "prov_id_cache"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    # Cerebro (productos + memoria)
    if "lst_prods_cache" not in st.session_state:
        l, d, m = cargar_cerebro(ws_inv, ws_map)
        st.session_state.lst_prods_cache = l
        st.session_state.dct_prods_cache = d
        st.session_state.memoria_cache = m
    if "catalogo_inv_cache" not in st.session_state:
        st.session_state.catalogo_inv_cache = cargar_catalogo_inventario(ws_inv)

    # ✅ Proveedores (para manual)
    if "proveedores_cache" not in st.session_state:
        provs, prov_to_id = cargar_proveedores(ws_map)
        st.session_state.proveedores_cache = provs
        st.session_state.prov_id_cache = prov_to_id

    # ✅ Categorías reales desde Inventario
    categorias = []
    try:
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        col_cat = "Categoria" if "Categoria" in df_inv.columns else ("Categoría" if "Categoría" in df_inv.columns else None)
        if col_cat:
            categorias = sorted([c for c in df_inv[col_cat].fillna("").astype(str).unique().tolist() if c.strip()])
    except Exception:
        categorias = []
    if not categorias:
        categorias = ["Sin Categoría"]

    # ==========================================
    # PASO 1: CARGA DE DATOS (XML O MANUAL)
    # ==========================================
    if st.session_state.step == 1:
        st.markdown('<div class="sub-header">Selecciona el método de ingreso</div>', unsafe_allow_html=True)
        
        tab_xml, tab_manual = st.tabs(["📂 Cargar XML (Factura Electrónica)", "✍️ Ingreso Manual"])
        
        # OPCIÓN A: XML
        with tab_xml:
            st.info("Arrastra tu Factura XML de la DIAN para autocompletar.")
            uploaded = st.file_uploader("📂 Sube tu Factura XML DIAN aquí", type=['xml'], key="xml_upl")
            
            if uploaded:
                with st.spinner("🤖 Analizando XML y Consultando Memoria..."):
                    data = parsear_xml_colombia(uploaded)
                    if not data:
                        st.error("❌ El XML no pudo ser leído. Verifica que sea una factura DIAN válida o consulta soporte.")
                        st.stop()
                    
                    # Guardar en sesión y avanzar
                    st.session_state.invoice_meta = {
                        "Proveedor": data["Proveedor"], "ID_Proveedor": data["ID_Proveedor"],
                        "Folio": data["Folio"], "Total": data["Total"]
                    }
                    st.session_state.invoice_items = data["Items"]
                    st.session_state.step = 2
                    st.rerun()

        # OPCIÓN B: MANUAL
        with tab_manual:
            with st.form("form_manual_ingreso"):
                c1, c2, c3 = st.columns(3)

                prov_sel = c1.selectbox(
                    "Proveedor",
                    options=st.session_state.get("proveedores_cache", ["(Nuevo proveedor)"]),
                )

                prov_man = prov_sel
                nit_default = st.session_state.get("prov_id_cache", {}).get(prov_sel, "") if prov_sel != "(Nuevo proveedor)" else ""

                if prov_sel == "(Nuevo proveedor)":
                    prov_man = c1.text_input("Nombre proveedor (nuevo)", placeholder="Ej: Italcol")

                nit_man = c2.text_input("NIT / ID Proveedor", value=nit_default or "000")

                folio_man = c3.text_input("No. Factura", placeholder="FAC-123")

                st.markdown("---")
                st.write("📝 **Items de la Factura**")

                df_template = pd.DataFrame([{
                    "Descripción": "", "Cantidad": 1, "Costo_Total_Línea": 0.0
                }])

                edited_manual = st.data_editor(
                    df_template, num_rows="dynamic", use_container_width=True,
                    column_config={
                        "Descripción": st.column_config.TextColumn("Descripción del Producto", required=True),
                        "Cantidad": st.column_config.NumberColumn("Cant.", min_value=1),
                        "Costo_Total_Línea": st.column_config.NumberColumn("Costo Total ($)", min_value=0.0)
                    }
                )

                submit_manual = st.form_submit_button("Siguiente Paso ➡️")
                
                if submit_manual:
                    if not prov_man or not folio_man:
                        st.error("⚠️ Falta Proveedor o Factura.")
                    else:
                        items_std = []
                        total_manual = 0
                        for i, row in edited_manual.iterrows():
                            if row["Descripción"]:
                                qty = float(row["Cantidad"])
                                c_tot = money_int(row["Costo_Total_Línea"])
                                base_unit = money_int((c_tot / qty) if qty > 0 else 0)
                                total_manual += c_tot
                                
                                items_std.append({
                                    'SKU_Proveedor': "S/C",
                                    'Descripcion': row["Descripción"],
                                    'Cantidad': qty,
                                    'Costo_Base_Unitario': base_unit,
                                    'IVA_Porcentaje': 0,
                                })

                        if not items_std:
                            st.error("⚠️ Debes agregar al menos un producto válido.")
                            st.stop()
                        
                        st.session_state.invoice_meta = {
                            "Proveedor": prov_man, "ID_Proveedor": nit_man,
                            "Folio": folio_man, "Total": total_manual
                        }
                        st.session_state.invoice_items = items_std
                        st.session_state.step = 2
                        st.rerun()

    # ==========================================
    # PASO 2: REVISIÓN, MAPEO Y GUARDADO
    # ==========================================
    elif st.session_state.step == 2:
        st.markdown('<div class="sub-header">Revisión, Mapeo y Finanzas</div>', unsafe_allow_html=True)

        # ✅ meta robusto (NO KeyError)
        meta = _get_meta_safe()
        if not meta["Proveedor"] or not meta["Folio"]:
            st.error("⚠️ No hay cabecera de compra válida (Proveedor/Folio). Vuelve a ingresar la compra.")
            st.session_state.step = 1
            st.rerun()

        st.info(
            f"🏢 **Proveedor:** {meta.get('Proveedor','—')} | "
            f"📄 **Folio:** {meta.get('Folio','—')} | "
            f"💰 **Total Base:** ${money_int(meta.get('Total',0)):,.0f}"
        )

        # --- LÓGICA DE MEMORIA (CEREBRO) ---
        df_revision_data = []

        for item in st.session_state.invoice_items:
            qty = float(item.get("Cantidad", 1) or 1)
            sugerencia = sugerir_producto_para_item(
                meta=meta,
                item=item,
                memoria=st.session_state.memoria_cache,
                catalogo=st.session_state.catalogo_inv_cache,
            )

            prod_interno_val = sugerencia.get("display", "NUEVO (Crear Producto)")
            iva_val = sugerencia.get("iva", item.get("IVA_Porcentaje", 0))
            factor_val = sugerencia.get("factor", 1.0)
            categoria_val = sugerencia.get("categoria", "Sin Categoría")
            nombre_sugerido = sugerencia.get("nombre", item.get('Descripcion', ''))
            motivo_sugerencia = sugerencia.get("motivo", "Nuevo producto")

            base_unit = money_int(item.get("Costo_Base_Unitario", 0))
            factor_val = float(factor_val or 1.0)
            if factor_val <= 0:
                factor_val = 1.0
            iva_val = float(iva_val or 0.0)

            costo_base_unit_est = base_unit / factor_val
            costo_neto_unit_est = costo_base_unit_est * (1.0 + (iva_val / 100.0))
            precio_sug_est = redondear_centena(precio_con_margen(costo_neto_unit_est, MARGEN_BRUTO_OBJ))

            df_revision_data.append({
                "SKU_Proveedor": item.get('SKU_Proveedor', 'S/C'),
                "Descripcion": item.get('Descripcion', ''),
                "Nombre_Inventario": nombre_sugerido,
                "Cantidad": _fmt_qty(qty),
                "Costo_Base_Unitario": base_unit,
                "📌 Producto_Interno": prod_interno_val,
                "IVA_%": int(iva_val) if float(iva_val).is_integer() else iva_val,
                "Factor_Pack": factor_val,
                "Precio_Sugerido": money_int(precio_sug_est or 0),
                "_Precio_Auto_Unitario": money_int(precio_sug_est or 0),
                "_Factor_Pack_Inicial": float(factor_val or 1.0),
                "Categoría": categoria_val,
                "Sugerencia": motivo_sugerencia
            })

        df_revision = pd.DataFrame(df_revision_data)

        edited_revision = st.data_editor(
            df_revision,
            use_container_width=True,
            hide_index=True,
            column_order=[
                "SKU_Proveedor", "Descripcion", "Nombre_Inventario", "📌 Producto_Interno",
                "Sugerencia", "IVA_%", "Categoría", "Cantidad", "Costo_Base_Unitario", "Factor_Pack", "Precio_Sugerido"
            ],
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("SKU Prov.", disabled=True),
                "Descripcion": st.column_config.TextColumn("Desc. Factura", disabled=True),
                "Nombre_Inventario": st.column_config.TextColumn("✍️ Nombre si es nuevo", disabled=False, width="medium"),
                "Sugerencia": st.column_config.TextColumn("🤖 Sugerencia", disabled=True, width="medium"),

                # ✅ Asociar a inventario (lista real)
                "📌 Producto_Interno": st.column_config.SelectboxColumn(
                    "📌 Asociar a",
                    options=st.session_state.lst_prods_cache,
                    required=True,
                ),

                # ✅ IVA seleccionable
                "IVA_%": st.column_config.SelectboxColumn(
                    "IVA %",
                    options=[0, 5, 19],
                    required=True,
                ),

                # ✅ Categoría seleccionable
                "Categoría": st.column_config.SelectboxColumn(
                    "Categoría",
                    options=categorias,
                    required=True,
                ),

                "Cantidad": st.column_config.NumberColumn("Cant.", disabled=True, step=1, format="%.0f"),  # ✅ sin 1.0
                "Costo_Base_Unitario": st.column_config.NumberColumn("Costo Unit. Base", format="$%.0f", disabled=True),
                "Factor_Pack": st.column_config.NumberColumn("Factor/Caja", min_value=1.0, step=1.0, format="%.0f"),  # ✅
                "Precio_Sugerido": st.column_config.NumberColumn("Precio Unitario Sugerido", format="$%.0f", min_value=0.0),
            },
        )

        st.markdown("---")
        st.markdown("### 2. Liquidación y Pago")
        
        c1, c2, c3 = st.columns(3)
        c_transporte = c1.number_input("Costo Transporte ($)", min_value=0.0, value=0.0)
        c_descuento = c2.number_input("Descuento Total ($)", min_value=0.0, value=0.0)
        origen_pago = c3.selectbox("Cuenta de Egreso (Gastos)", ["Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata", "Efectivo", "Caja General", "Crédito Proveedor (CxP)"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Confirmar y Guardar en Base de Datos", type="primary", use_container_width=True):
            
            df_to_save = edited_revision.copy()
            df_to_save = df_to_save.rename(columns={
                "📌 Producto_Interno": "SKU_Interno_Seleccionado",
                "IVA_%": "IVA_Porcentaje",
                "Cantidad": "Cantidad_Recibida"
            })
            
            info_pago = {
                "Origen": origen_pago,
                "Transporte": float(c_transporte),
                "Descuento": float(c_descuento)
            }
            
            with st.spinner("Guardando en Google Sheets..."):
                ok, logs = procesar_guardado(ws_map, ws_inv, ws_hist, ws_gas, df_to_save, meta, info_pago)
            
            if ok:
                st.success("¡Compra registrada correctamente!")
                st.balloons()
                with st.expander("Ver bitácora de operaciones"):
                    for l in logs: st.text(l)

                # Limpiar caché y recargar memoria para sugerencias inmediatas
                st.cache_data.clear()
                for k in ["lst_prods_cache", "dct_prods_cache", "memoria_cache", "proveedores_cache", "prov_id_cache"]:
                    if k in st.session_state:
                        del st.session_state[k]

                # Resetear la sesión
                st.session_state.invoice_meta = {}
                st.session_state.invoice_items = []

                if st.button("Volver al Inicio"):
                    st.session_state.step = 1
                    st.rerun()
            else:
                st.error("Error guardando datos.")
                for l in logs: st.error(l)

if __name__ == "__main__":
    main()