import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date, timedelta
import json
import urllib.parse
import jinja2
from weasyprint import HTML
from io import BytesIO
import pytz
import numpy as np
import time  # Necesario para manejar las esperas en el error 429
import uuid  # ya lo tienes; mantener

# --- CONFIGURACIÓN DE ZONA HORARIA ---
TZ_CO = pytz.timezone("America/Bogota")

def now_co():
    return datetime.now(TZ_CO)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Nexus Pro | Bigotes y Patitas", page_icon="🐾", layout="wide")

# ==========================================
# 1. SISTEMA ANTI-BLOQUEO (RETRY LOGIC)
# ==========================================
def safe_api_call(func, *args, **kwargs):
    """
    Ejecuta cualquier función de gspread. Si da error 429 (Cuota excedida),
    espera y reintenta hasta 5 veces.
    """
    max_retries = 5
    wait_time = 2  # Segundos iniciales de espera
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota exceeded" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    wait_time *= 2  # Espera exponencial (2s, 4s, 8s...)
                    continue
                else:
                    st.error("⚠️ La API de Google está saturada. Por favor espera 1 minuto.")
                    raise e
            else:
                raise e

# ==========================================
# 2. CONEXIÓN Y LECTURA OPTIMIZADA
# ==========================================
@st.cache_resource(ttl=3600)
def conectar_google_sheets():
    """Conecta a Google Sheets y devuelve el objeto Spreadsheet principal"""
    try:
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        return sh
    except Exception as e:
        st.error(f"Error crítico conectando a Google Sheets: {e}")
        st.stop()

def obtener_worksheets(sh):
    """Devuelve un diccionario con las hojas para fácil acceso"""
    return {
        "inv": sh.worksheet("Inventario"),
        "cli": sh.worksheet("Clientes"),
        "ven": sh.worksheet("Ventas"),
        "gas": sh.worksheet("Gastos"),
        "cie": sh.worksheet("Cierres"),
        # Agrega las otras si las usas activamente, por ahora estas son las vitales para el POS
    }

def limpiar_dataframe(raw_data):
    """Convierte datos crudos de Sheets a DataFrame limpio"""
    if not raw_data:
        return pd.DataFrame()
    
    header = raw_data[0]
    # Limpieza de encabezados duplicados o vacíos
    seen = {}
    clean_header = []
    for i, h in enumerate(header):
        if not h or h.strip() == "":
            h = f"Col_{i+1}"
        h = h.strip()
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0
        clean_header.append(h)

    df = pd.DataFrame(raw_data[1:], columns=clean_header)

    # Convertir columnas numéricas y fechas
    cols_num = ['Precio', 'Stock', 'Costo', 'Monto', 'Total', 'Costo_Total', 
                'Base_Inicial', 'Ventas_Efectivo', 'Gastos_Efectivo', 
                'Dinero_A_Bancos', 'Saldo_Teorico', 'Saldo_Real', 'Diferencia']
    
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        
    return df

def cargar_datos_iniciales():
    """Carga TODOS los datos al Session State de una sola vez."""
    sh = conectar_google_sheets()
    h = obtener_worksheets(sh)
    
    with st.spinner("🔄 Sincronizando datos con la nube..."):
        # Usamos safe_api_call para leer
        data_inv = safe_api_call(h["inv"].get_all_values)
        data_cli = safe_api_call(h["cli"].get_all_values)
        data_ven = safe_api_call(h["ven"].get_all_values)
        data_gas = safe_api_call(h["gas"].get_all_values)
        data_cie = safe_api_call(h["cie"].get_all_values)

        st.session_state.db = {
            "inv": limpiar_dataframe(data_inv),
            "cli": limpiar_dataframe(data_cli),
            "ven": limpiar_dataframe(data_ven),
            "gas": limpiar_dataframe(data_gas),
            "cie": limpiar_dataframe(data_cie)
        }
        st.session_state.ultima_sincronizacion = now_co()

# ==========================================
# 3. FUNCIONES DE UTILIDAD (Tus funciones originales)
# ==========================================
def sanitizar_para_sheet(val):
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    if isinstance(val, (pd.Timestamp, datetime, date)): return val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(val, datetime) else val.strftime("%Y-%m-%d")
    return val

def normalizar_id_producto(id_prod):
    if pd.isna(id_prod): return ""
    s = str(id_prod).strip().upper()
    s = s.replace(" ", "").replace(",", "").replace(".", "")
    if s.isdigit(): s = str(int(s))
    if s.endswith("00") and s[:-2].isdigit(): s = s[:-2]
    return s

def limpiar_tel(tel):
    t = str(tel).replace(" ", "").replace("+", "").replace("-", "").replace("(", "").replace(")", "").strip()
    if len(t) == 10 and not t.startswith("57"): t = "57" + t
    return t

def msg_venta(nombre: str, mascota: str, items_str: str, total: float) -> str:
    nombre = (nombre or "Cliente").strip()
    mascota = (mascota or "tu peludito").strip()
    items_str = (items_str or "").strip()

    # Mensaje corto, amable, fidelizador (sin emojis)
    return (
        f"Hola {nombre}, gracias por tu compra en Bigotes y Patitas.\n"
        f"Mascota: {mascota}\n"
        f"Productos: {items_str}\n"
        f"Total: ${total:,.0f}\n\n"
        f"Si necesitas ayuda con recomendaciones o con la próxima compra, escríbenos y con gusto te ayudamos.\n"
        f"Que {mascota} lo disfrute. Gracias por confiar en nosotros."
    )

def msg_bienvenida(nombre, mascota):
    return f"""🐾 ¡Hola {nombre}! Bienvenido/a a Bigotes y Patitas.
🎉 Estamos felices de consentir a {mascota or 'tu peludito'}.
📦 Necesites comida, snacks o juguetes, aquí estamos.
🤗 Gracias por confiar en nosotros."""

def generar_pdf_html(venta_data, items):
    try:
        try:
            with open("factura.html", "r", encoding="utf-8") as f:
                template_str = f.read()
        except FileNotFoundError:
            # Plantilla de respaldo por si falla la lectura del archivo
            template_str = "<html><body><h1>Factura {{id_venta}}</h1><p>Total: {{total}}</p></body></html>"

        context = {
            "id_venta": venta_data['ID'],
            "fecha": venta_data['Fecha'],
            "cliente_nombre": venta_data.get('Cliente', 'Consumidor Final'),
            "cliente_cedula": venta_data.get('Cedula_Cliente', '---'),
            "cliente_direccion": venta_data.get('Direccion', 'Local'),
            "cliente_mascota": venta_data.get('Mascota', '---'),
            "metodo_pago": venta_data.get('Metodo_Pago', 'Efectivo'),
            "tipo_entrega": venta_data.get('Tipo_Entrega', 'Local'),
            "items": items,
            "total": venta_data['Total']
        }
        template = jinja2.Template(template_str)
        html_renderizado = template.render(context)
        pdf_file = HTML(string=html_renderizado).write_pdf()
        return pdf_file
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None

def normalizar_todas_las_referencias():
    sh = conectar_google_sheets()
    ws_inv = sh.worksheet("Inventario")
    df = st.session_state.db['inv']
    
    if 'ID_Producto' not in df.columns:
        st.error("No se encontró ID_Producto")
        return

    col_valores = [normalizar_id_producto(x) for x in df['ID_Producto']]
    
    # Encontrar indice de columna
    headers = safe_api_call(ws_inv.row_values, 1)
    if 'ID_Producto_Norm' not in headers:
        safe_api_call(ws_inv.update_cell, 1, len(headers)+1, 'ID_Producto_Norm')
        col_idx = len(headers) + 1
    else:
        col_idx = headers.index('ID_Producto_Norm') + 1

    # Update masivo (vertical)
    valores_lista = [[v] for v in col_valores]
    rango = f"{gspread.utils.rowcol_to_a1(2, col_idx)}:{gspread.utils.rowcol_to_a1(len(valores_lista)+1, col_idx)}"
    safe_api_call(ws_inv.update, rango, valores_lista)
    st.success("Referencias normalizadas en la Nube. Recarga los datos.")

# ==============================
# NUEVO: Reparación robusta UID
# ==============================

def _ensure_sheet_columns(ws, required_cols):
    """Asegura columnas en fila 1. Retorna headers finales."""
    headers = safe_api_call(ws.row_values, 1) or []
    changed = False
    for c in required_cols:
        if c not in headers:
            headers.append(c)
            safe_api_call(ws.update_cell, 1, len(headers), c)
            changed = True
    if changed:
        headers = safe_api_call(ws.row_values, 1) or headers
    return headers


def asegurar_ids_inventario_nube():
    """
    One-shot: crea/llena Producto_UID e ID_Producto_Norm en Inventario (nube + session_state.db['inv']).
    Debe estar DEFINIDA a nivel módulo (sin indentación) para que main() la pueda llamar.
    """
    if "db" not in st.session_state or "inv" not in st.session_state.db:
        st.error("Primero debes usar '🔄 Sincronizar Datos' para cargar Inventario en memoria.")
        return

    df = st.session_state.db["inv"].copy()
    if df.empty:
        st.warning("Inventario está vacío en memoria. Sincroniza y reintenta.")
        return

    if "ID_Producto" not in df.columns:
        st.error("Inventario no tiene columna 'ID_Producto'.")
        return

    # 1) Asegurar columnas locales
    if "ID_Producto_Norm" not in df.columns:
        df["ID_Producto_Norm"] = df["ID_Producto"].apply(normalizar_id_producto)

    if "Producto_UID" not in df.columns:
        df["Producto_UID"] = ""

    # 2) Generar UIDs faltantes
    uid_ser = df["Producto_UID"].fillna("").astype(str).str.strip()
    mask_missing = uid_ser.eq("")
    if mask_missing.any():
        df.loc[mask_missing, "Producto_UID"] = [uuid.uuid4().hex for _ in range(int(mask_missing.sum()))]

    # 3) Subir a Google Sheets
    sh = conectar_google_sheets()
    ws_inv = obtener_worksheets(sh)["inv"]

    headers = _ensure_sheet_columns(ws_inv, ["Producto_UID", "ID_Producto_Norm"])
    col_uid = headers.index("Producto_UID") + 1
    col_norm = headers.index("ID_Producto_Norm") + 1

    uid_vals = [[str(x)] for x in df["Producto_UID"].astype(str).tolist()]
    norm_vals = [[str(x)] for x in df["ID_Producto_Norm"].astype(str).tolist()]

    rango_uid = f"{gspread.utils.rowcol_to_a1(2, col_uid)}:{gspread.utils.rowcol_to_a1(len(uid_vals)+1, col_uid)}"
    rango_norm = f"{gspread.utils.rowcol_to_a1(2, col_norm)}:{gspread.utils.rowcol_to_a1(len(norm_vals)+1, col_norm)}"

    safe_api_call(ws_inv.update, rango_uid, uid_vals)
    safe_api_call(ws_inv.update, rango_norm, norm_vals)

    # 4) Persistir en memoria
    st.session_state.db["inv"] = df
    st.success("✅ Reparación lista: Producto_UID + ID_Producto_Norm actualizados en Inventario (nube y memoria).")

# ==========================================
# 4. FUNCIONES DE ESCRITURA (OPTIMIZADAS)
# ==========================================

# ...existing code...

def _to_float(x, default=0.0):
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return float(s.replace(",", ""))
    except Exception:
        return default

def _build_inventory_index(ws_inv):
    """
    Index seguro del Inventario (nube) para descontar stock sin ws.find().
    Retorna: headers, rows, col_stock, col_uid, col_norm, uid_to_row, norm_to_row
    """
    headers = safe_api_call(ws_inv.row_values, 1) or []

    # Asegurar columnas críticas
    if "Producto_UID" not in headers or "ID_Producto_Norm" not in headers:
        headers = _ensure_sheet_columns(ws_inv, ["Producto_UID", "ID_Producto_Norm"])

    all_vals = safe_api_call(ws_inv.get_all_values) or []
    if not all_vals:
        return [], [], None, None, None, {}, {}

    headers = all_vals[0]
    rows = all_vals[1:]

    if "Stock" not in headers:
        raise ValueError("Inventario nube no tiene columna 'Stock'.")

    col_stock = headers.index("Stock")
    col_uid = headers.index("Producto_UID") if "Producto_UID" in headers else None
    col_norm = headers.index("ID_Producto_Norm") if "ID_Producto_Norm" in headers else None

    uid_to_row = {}
    norm_to_row = {}

    for sheet_row, r in enumerate(rows, start=2):
        if col_uid is not None and col_uid < len(r):
            uid = str(r[col_uid]).strip()
            if uid:
                uid_to_row[uid] = sheet_row
        if col_norm is not None and col_norm < len(r):
            norm = str(r[col_norm]).strip()
            if norm:
                norm_to_row[norm] = sheet_row

    return headers, rows, col_stock, col_uid, col_norm, uid_to_row, norm_to_row

# ...existing code...
def registrar_venta(fila_datos, carrito):
    """Escribe venta y descuenta stock de forma confiable por Producto_UID."""
    sh = conectar_google_sheets()
    ws_ven = obtener_worksheets(sh)["ven"]
    ws_inv = obtener_worksheets(sh)["inv"]

    # 1) Escribir venta
    safe_api_call(ws_ven.append_row, fila_datos)

    # 2) Preparar inventario local
    df_inv = st.session_state.db["inv"].copy()
    if "Producto_UID" not in df_inv.columns:
        df_inv["Producto_UID"] = ""
    if "ID_Producto_Norm" not in df_inv.columns and "ID_Producto" in df_inv.columns:
        df_inv["ID_Producto_Norm"] = df_inv["ID_Producto"].apply(normalizar_id_producto)

    df_inv["Producto_UID"] = df_inv["Producto_UID"].fillna("").astype(str).str.strip()
    df_inv["ID_Producto_Norm"] = df_inv["ID_Producto_Norm"].fillna("").astype(str).str.strip()

    # 3) Index nube (sin ws.find)
    headers, rows, col_stock, col_uid, col_norm, uid_to_row, norm_to_row = _build_inventory_index(ws_inv)

    # 4) Acumular deltas por fila (por si se repite un producto en carrito)
    deltas_by_row = {}  # row -> total_delta (negativo)
    local_updates = []  # (idx_df, new_stock)

    for item in carrito:
        cant = _to_float(item.get("Cantidad", 0), 0.0)
        if cant <= 0:
            continue

        uid = str(item.get("Producto_UID", "")).strip()
        id_norm = str(item.get("ID_Producto_Norm", "")).strip()
        if not id_norm:
            id_norm = normalizar_id_producto(item.get("ID_Producto", ""))

        sheet_row = None
        if uid:
            sheet_row = uid_to_row.get(uid)
        if sheet_row is None and id_norm:
            sheet_row = norm_to_row.get(id_norm)

        if sheet_row is None:
            # no descontar a ciegas: si no se encuentra, se omite (y se debe corregir el inventario)
            continue

        deltas_by_row[sheet_row] = deltas_by_row.get(sheet_row, 0.0) - cant

        # update local por UID preferido
        m = pd.DataFrame()
        if uid:
            m = df_inv[df_inv["Producto_UID"] == uid]
        if m.empty and id_norm:
            m = df_inv[df_inv["ID_Producto_Norm"] == id_norm]
        if not m.empty:
            idx = m.index[0]
            stock_actual_local = _to_float(df_inv.at[idx, "Stock"], 0.0)
            df_inv.at[idx, "Stock"] = stock_actual_local - cant

    # 5) Batch update nube (calcular stock actual desde snapshot rows)
    updates = []
    # map fila->stock actual desde rows
    for sheet_row, delta in deltas_by_row.items():
        r = rows[sheet_row - 2]  # rows empieza en fila 2
        stock_actual = _to_float(r[col_stock] if col_stock < len(r) else 0.0, 0.0)
        nuevo_stock = stock_actual + delta
        cell_a1 = gspread.utils.rowcol_to_a1(sheet_row, col_stock + 1)
        updates.append({"range": cell_a1, "values": [[nuevo_stock]]})

    if updates:
        safe_api_call(ws_inv.batch_update, updates)

    # 6) Persistir inventario local
    st.session_state.db["inv"] = df_inv

    # 7) Actualizar Venta LOCAL (lo tuyo)
    cols = st.session_state.db["ven"].columns
    if len(fila_datos) < len(cols):
        fila_datos += [""] * (len(cols) - len(fila_datos))
    nuevo_df = pd.DataFrame([fila_datos], columns=cols)
    if "Total" in nuevo_df.columns:
        nuevo_df["Total"] = pd.to_numeric(nuevo_df["Total"], errors="coerce")
    if "Fecha" in nuevo_df.columns:
        nuevo_df["Fecha"] = pd.to_datetime(nuevo_df["Fecha"], errors="coerce")
    st.session_state.db["ven"] = pd.concat([st.session_state.db["ven"], nuevo_df], ignore_index=True)

def registrar_gasto(fila_datos):
    sh = conectar_google_sheets()
    ws_gas = obtener_worksheets(sh)["gas"]
    
    safe_api_call(ws_gas.append_row, fila_datos)
    
    # Update local
    cols = st.session_state.db['gas'].columns
    if len(fila_datos) < len(cols): fila_datos += [""] * (len(cols) - len(fila_datos))
    nuevo_df = pd.DataFrame([fila_datos], columns=cols)
    if 'Monto' in nuevo_df.columns: nuevo_df['Monto'] = pd.to_numeric(nuevo_df['Monto'])
    st.session_state.db['gas'] = pd.concat([st.session_state.db['gas'], nuevo_df], ignore_index=True)

def registrar_cliente(fila_datos, update=False, row_idx=None):
    sh = conectar_google_sheets()
    ws_cli = obtener_worksheets(sh)["cli"]
    
    if update and row_idx:
        # Update rango A:J (asumiendo 10 columnas)
        rango = f"A{row_idx}:J{row_idx}"
        safe_api_call(ws_cli.update, rango, [fila_datos])
        # Para simplificar la consistencia en edición, forzamos recarga completa la próxima vez
        # o podríamos actualizar el DF local buscando por índice.
        # Por seguridad en datos maestros:
        cargar_datos_iniciales()
    else:
        safe_api_call(ws_cli.append_row, fila_datos)
        # Update local append
        cols = st.session_state.db['cli'].columns
        if len(fila_datos) < len(cols): fila_datos += [""] * (len(cols) - len(fila_datos))
        nuevo_df = pd.DataFrame([fila_datos], columns=cols)
        st.session_state.db['cli'] = pd.concat([st.session_state.db['cli'], nuevo_df], ignore_index=True)

def actualizar_estado_envio(id_venta, nuevo_estado):
    sh = conectar_google_sheets()
    ws_ven = obtener_worksheets(sh)["ven"]
    
    try:
        cell = safe_api_call(ws_ven.find, str(id_venta))
        if cell:
            # Buscar columna estado
            headers = safe_api_call(ws_ven.row_values, 1)
            col_idx = headers.index("Estado_Envio") + 1
            safe_api_call(ws_ven.update_cell, cell.row, col_idx, nuevo_estado)
            
            # Update Local
            df_ven = st.session_state.db['ven']
            idx = df_ven[df_ven['ID_Venta'] == id_venta].index
            if not idx.empty:
                st.session_state.db['ven'].at[idx[0], 'Estado_Envio'] = nuevo_estado
            return True
    except:
        return False

# ==========================================
# 5. PESTAÑAS (UI)
# ==========================================

def tab_pos():
    st.markdown("""
        <style>
        .main-title { color: #187f77; font-size: 2.2rem; font-weight: 800; margin-bottom: 0.5rem; }
        .sub-title { color: #f5a641; font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem; }
        .mascota-box { background: #f8f9fa; border-radius: 12px; padding: 10px 18px; margin-bottom: 10px; border-left: 5px solid #f5a641; }
        .carrito-total { background: #f5a641; color: white; font-size: 1.5rem; font-weight: bold; border-radius: 10px; padding: 12px 24px; text-align: right; margin-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">🐾 Punto de Venta Bigotes y Patitas</div>', unsafe_allow_html=True)
    
    # Inicializar variables POS
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'mascota_seleccionada' not in st.session_state: st.session_state.mascota_seleccionada = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None
    if 'whatsapp_link' not in st.session_state: st.session_state.whatsapp_link = None

    df_c = st.session_state.db['cli']
    df_inv = st.session_state.db['inv']

    # --- 1. BUSCAR CLIENTE ---
    st.markdown("### 👤 Cliente")
    if not df_c.empty:
        search = st.text_input("Buscar cliente (Nombre, Cédula, Mascota)", key="busca_cli_pos")
        if search:
            mask = (
                df_c['Nombre'].astype(str).str.contains(search, case=False, na=False) |
                df_c['Cedula'].astype(str).str.contains(search, case=False, na=False) |
                df_c['Mascota'].astype(str).str.contains(search, case=False, na=False)
            )
            resultados = df_c[mask]
        else:
            resultados = df_c.head(0) # No mostrar nada si no hay busqueda

        if not resultados.empty:
            selected_idx = st.selectbox("Seleccionar:", resultados.index, format_func=lambda i: f"{resultados.loc[i, 'Nombre']} - {resultados.loc[i, 'Cedula']}")
            
            if st.button("Cargar Cliente"):
                cliente_data = resultados.loc[selected_idx].to_dict()
                # Parsear mascotas
                mascotas_lista = []
                try:
                    raw_json = cliente_data.get('Info_Mascotas', '')
                    if raw_json and str(raw_json).strip():
                        parsed = json.loads(str(raw_json))
                        if isinstance(parsed, list):
                            mascotas_lista = [m.get('Nombre') for m in parsed if m.get('Nombre')]
                except: pass
                
                if not mascotas_lista:
                    old_m = cliente_data.get('Mascota', '')
                    if old_m: mascotas_lista = [old_m]
                
                if not mascotas_lista: mascotas_lista = ["Varios"]
                
                cliente_data['Lista_Mascotas'] = mascotas_lista
                st.session_state.cliente_actual = cliente_data
                st.session_state.mascota_seleccionada = mascotas_lista[0]
                st.toast("Cliente cargado", icon="✅")
                st.rerun()

    if st.session_state.cliente_actual:
        c_act = st.session_state.cliente_actual
        st.info(f"Cliente: **{c_act['Nombre']}** | Mascota: **{st.session_state.mascota_seleccionada}**")

    # --- 2. PRODUCTOS (SELECCIÓN + AGREGAR) ---
    st.markdown("### 🛒 Productos")

    if df_inv is None or df_inv.empty:
        st.info("No hay productos en inventario.")
        return

    # Asegurar columnas claves
    if "Producto_UID" not in df_inv.columns:
        df_inv["Producto_UID"] = ""
    if "ID_Producto_Norm" not in df_inv.columns:
        df_inv["ID_Producto_Norm"] = df_inv["ID_Producto"].apply(normalizar_id_producto)

    df_inv["Producto_UID"] = df_inv["Producto_UID"].fillna("").astype(str).str.strip()

    # Display humano
    df_inv["Display"] = df_inv.apply(
        lambda x: f"{x.get('Nombre','')} | ID: {x.get('ID_Producto','')} | Stock: {int(float(x.get('Stock',0) or 0))} | ${int(float(x.get('Precio',0) or 0)):,}",
        axis=1,
    )
    mapa_display_a_uid = dict(zip(df_inv["Display"], df_inv["Producto_UID"]))

    prod_sel = st.selectbox("Buscar Producto", df_inv["Display"].tolist(), key="pos_prod_sel")

    # Resolver producto seleccionado (por UID preferido)
    uid_sel = str(mapa_display_a_uid.get(prod_sel, "")).strip()
    row_prod = None
    if uid_sel:
        m = df_inv[df_inv["Producto_UID"].astype(str).str.strip() == uid_sel]
        if not m.empty:
            row_prod = m.iloc[0]

    # Fallback si falta UID en alguna fila (no ideal, pero evita bloquear POS)
    if row_prod is None:
        df_inv["__ID_Norm"] = df_inv["ID_Producto"].apply(normalizar_id_producto)
        id_sel = df_inv.loc[df_inv["Display"] == prod_sel, "__ID_Norm"].iloc[0]
        mm = df_inv[df_inv["__ID_Norm"] == id_sel]
        if not mm.empty:
            row_prod = mm.iloc[0]

    if row_prod is None:
        st.error("No pude resolver el producto seleccionado.")
        return

    producto_uid = str(row_prod.get("Producto_UID", "")).strip()
    id_prod = str(row_prod.get("ID_Producto", "")).strip()
    id_norm = str(row_prod.get("ID_Producto_Norm", normalizar_id_producto(id_prod))).strip()
    nombre = str(row_prod.get("Nombre", "")).strip()
    stock_disp = float(row_prod.get("Stock", 0) or 0)
    precio_base = float(row_prod.get("Precio", 0) or 0)
    costo_base = float(row_prod.get("Costo", 0) or 0)

    # =========================
    # FIX: Reset de inputs por producto
    # =========================
    # Si no hay UID, usamos el id_norm como fallback estable
    producto_key = producto_uid if producto_uid else f"NORM:{id_norm}"

    if st.session_state.get("pos_last_producto_key") != producto_key:
        st.session_state["pos_last_producto_key"] = producto_key
        st.session_state["pos_cant"] = 1.0
        st.session_state["pos_precio"] = float(precio_base or 0.0)
        st.session_state["pos_desc"] = 0.0

    # =========================
    # UI: Tarjeta ejecutiva del producto seleccionado
    # =========================
    st.markdown(
        f"""
<div style="background:#ffffff;border:1px solid rgba(0,0,0,0.06);border-radius:14px;padding:14px 16px;margin:8px 0 14px 0;box-shadow:0 6px 18px rgba(0,0,0,0.05);">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
    <div>
      <div style="font-weight:900;color:#187f77;font-size:1.05rem;line-height:1.15;">{nombre}</div>
      <div style="color:#64748b;font-size:0.85rem;margin-top:4px;">ID: <b>{id_prod}</b></div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:0.85rem;color:#64748b;">Stock</div>
      <div style="font-weight:900;font-size:1.25rem;">{int(stock_disp):,}</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    cA, cB, cC, cD = st.columns([1, 1, 1, 1])
    with cA:
        cant = st.number_input("Cantidad", min_value=1.0, step=1.0, key="pos_cant")
    with cB:
        precio = st.number_input("Precio unit.", min_value=0.0, step=100.0, key="pos_precio")
    with cC:
        descuento = st.number_input("Descuento unit.", min_value=0.0, step=100.0, key="pos_desc")
    with cD:
        # Vista rápida de totales de línea (profesional)
        subtotal_linea = (float(precio or 0) - float(descuento or 0)) * float(cant or 0)
        st.caption("Subtotal línea")
        st.write(f"${subtotal_linea:,.0f}")

    if st.button("➕ Agregar al carrito", type="primary", key="pos_add"):
        # si ya existe en carrito por UID (o por ID_norm), sumar cantidad
        existe = False
        for it in st.session_state.carrito:
            if (producto_uid and str(it.get("Producto_UID", "")).strip() == producto_uid) or (
                (not producto_uid) and str(it.get("ID_Producto_Norm", "")).strip() == id_norm
            ):
                it["Cantidad"] = float(it.get("Cantidad", 0) or 0) + float(cant)
                it["Precio"] = float(precio)
                it["Descuento"] = float(descuento)
                it["Subtotal"] = (float(it["Precio"]) - float(it["Descuento"])) * float(it["Cantidad"])
                existe = True
                break

        if not existe:
            st.session_state.carrito.append(
                {
                    "Producto_UID": producto_uid,
                    "ID_Producto": id_prod,
                    "ID_Producto_Norm": id_norm,
                    "Nombre_Producto": nombre,
                    "Cantidad": float(cant),
                    "Precio": float(precio),
                    "Descuento": float(descuento),
                    "Costo": float(costo_base),
                    "Subtotal": (float(precio) - float(descuento)) * float(cant),
                }
            )
        st.rerun()

    # --- 3. CARRITO (FUERA del bloque de selección) ---
    st.markdown("### 🧺 Detalle de Compra")

    if not st.session_state.carrito:
        st.info("Carrito vacío. Agrega productos para continuar.")
        return

    df_car = pd.DataFrame(st.session_state.carrito).copy()

    # Tipos numéricos (evita que el editor “no aplique” bien)
    for c in ["Cantidad", "Precio", "Descuento", "Costo", "Subtotal"]:
        if c in df_car.columns:
            df_car[c] = pd.to_numeric(df_car[c], errors="coerce").fillna(0.0)

    # Columna acción para eliminar (se ve al lado en la tabla)
    if "🗑️ Eliminar" not in df_car.columns:
        df_car.insert(0, "🗑️ Eliminar", False)

    # Subtotal siempre consistente
    if "Subtotal" not in df_car.columns:
        df_car["Subtotal"] = (df_car["Precio"] - df_car["Descuento"]) * df_car["Cantidad"]

    with st.form("pos_carrito_form", clear_on_submit=False):
        edited_car = st.data_editor(
            df_car,
            key="editor_carrito",
            num_rows="fixed",
            hide_index=True,
            column_config={
                "🗑️ Eliminar": st.column_config.CheckboxColumn("🗑️", help="Marca para eliminar esta línea"),
                "Producto_UID": st.column_config.TextColumn("Producto_UID", disabled=True, width="small"),
                "ID_Producto": st.column_config.TextColumn("ID_Producto", disabled=True, width="small"),
                "ID_Producto_Norm": st.column_config.TextColumn("ID_Producto_Norm", disabled=True, width="small"),
                "Nombre_Producto": st.column_config.TextColumn("Producto", disabled=True, width="large"),
                "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0),
                "Precio": st.column_config.NumberColumn("Precio", format="$%.0f", step=100.0),
                "Descuento": st.column_config.NumberColumn("Desc.", format="$%.0f", step=100.0),
                "Costo": st.column_config.NumberColumn("Costo", format="$%.0f", step=100.0),
                "Subtotal": st.column_config.NumberColumn("Subtotal", format="$%.0f", disabled=True),
            },
        )

        cA, cB, cC = st.columns([1, 1, 2])
        aplicar = cA.form_submit_button("💾 Aplicar cambios", type="primary")
        vaciar = cB.form_submit_button("🗑️ Vaciar carrito")

        if vaciar:
            st.session_state.carrito = []
            st.rerun()

        if aplicar:
            # 1) Eliminar marcados
            if "🗑️ Eliminar" in edited_car.columns:
                edited_car = edited_car[edited_car["🗑️ Eliminar"] != True].copy()

            # 2) Recalcular subtotal SIEMPRE (aquí se arregla “no cambia el precio”)
            for c in ["Cantidad", "Precio", "Descuento", "Costo"]:
                if c in edited_car.columns:
                    edited_car[c] = pd.to_numeric(edited_car[c], errors="coerce").fillna(0.0)

            if not edited_car.empty:
                edited_car["Subtotal"] = (edited_car["Precio"] - edited_car["Descuento"]) * edited_car["Cantidad"]

            # 3) Guardar en session_state (sin columna de acción)
            if "🗑️ Eliminar" in edited_car.columns:
                edited_car = edited_car.drop(columns=["🗑️ Eliminar"])

            st.session_state.carrito = edited_car.to_dict("records")
            st.rerun()

    # Total (fuera del form)
    if st.session_state.carrito:
        df_total = pd.DataFrame(st.session_state.carrito)
        for c in ["Cantidad", "Precio", "Descuento", "Subtotal"]:
            if c in df_total.columns:
                df_total[c] = pd.to_numeric(df_total[c], errors="coerce").fillna(0.0)
        if "Subtotal" not in df_total.columns and {"Precio", "Descuento", "Cantidad"}.issubset(df_total.columns):
            df_total["Subtotal"] = (df_total["Precio"] - df_total["Descuento"]) * df_total["Cantidad"]
        total = float(df_total["Subtotal"].sum()) if "Subtotal" in df_total.columns else 0.0
    else:
        total = 0.0

    st.markdown(f"**TOTAL:** ${total:,.0f}")

    # --- 4. PAGO + FINALIZAR (FUERA del bloque del carrito) ---
    st.markdown("---")
    c1, c2 = st.columns(2)
    metodo = c1.selectbox("Pago", ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"], key="pos_metodo")
    entrega = c2.selectbox("Entrega", ["Local", "Domicilio"], key="pos_entrega")
    dir_envio = st.text_input(
        "Dirección",
        value=st.session_state.cliente_actual.get("Direccion", "") if st.session_state.cliente_actual else "",
        key="pos_dir",
    )

    if st.button("✅ FINALIZAR VENTA", type="primary", width="stretch", key="pos_fin"):
        if not st.session_state.cliente_actual:
            st.error("Falta seleccionar cliente")
            return

        with st.spinner("Procesando..."):
            id_venta = f"VEN-{int(now_co().timestamp())}"
            fecha = now_co().strftime("%Y-%m-%d %H:%M:%S")

            items_str = ", ".join([f"{x['Cantidad']}x {x['Nombre_Producto']}" for x in st.session_state.carrito])

            # total ya lo calculas más arriba; asegurar float
            total_num = float(total or 0.0)

            items_json = json.dumps(
                [
                    {
                        "Producto_UID": x.get("Producto_UID", ""),
                        "ID": x.get("ID_Producto", ""),
                        "ID_Producto_Norm": x.get("ID_Producto_Norm", ""),
                        "Nombre": x.get("Nombre_Producto", ""),
                        "Cantidad": x.get("Cantidad", 0),
                    }
                    for x in st.session_state.carrito
                ]
            )

            costo_total = sum(
                [float(x.get("Costo", 0) or 0) * float(x.get("Cantidad", 0) or 0) for x in st.session_state.carrito]
            )

            fila = [
                id_venta,
                fecha,
                st.session_state.cliente_actual.get("Cedula", ""),
                st.session_state.cliente_actual.get("Nombre", ""),
                entrega,
                dir_envio,
                "Pendiente" if entrega != "Local" else "Entregado",
                metodo,
                "",
                total_num,
                items_str,
                items_json,
                costo_total,
                st.session_state.mascota_seleccionada,
            ]

            registrar_venta(fila, st.session_state.carrito)

            # ===== POST-VENTA: preparar WhatsApp (persistente) =====
            tel_raw = _get_cliente_tel(st.session_state.cliente_actual)
            tel = limpiar_tel(tel_raw) if tel_raw else ""
            msg = msg_venta_fidelidad(
                st.session_state.cliente_actual.get("Nombre", ""),
                st.session_state.mascota_seleccionada,
                items_str,
                total_num,
            )
            st.session_state.ultima_venta_id = id_venta
            st.session_state.whatsapp_link = (
                f"https://wa.me/{tel}?text={urllib.parse.quote(msg)}" if tel else None
            )

            # limpiar carrito pero NO borrar whatsapp_link
            st.session_state.carrito = []
            st.success("Venta registrada. Acciones post-venta disponibles abajo.")

    # ===== UI POST-VENTA (botón WhatsApp) =====
    if st.session_state.get("ultima_venta_id"):
        st.markdown("### Acciones post-venta")
        link = st.session_state.get("whatsapp_link")

        c1, c2 = st.columns([1, 1])
        with c1:
            if link:
                try:
                    st.link_button("Enviar WhatsApp al cliente", link, type="primary")
                except Exception:
                    st.markdown(f"[Enviar WhatsApp al cliente]({link})")
            else:
                st.warning("No hay teléfono válido para WhatsApp en este cliente.")

        with c2:
            # Botón “Nueva venta” (opcional, para resetear post-venta cuando tú quieras)
            if st.button("Nueva venta", key="pos_new_sale"):
                st.session_state.ultima_venta_id = None
                st.session_state.whatsapp_link = None
                st.rerun()

    # ...existing code... (descarga PDF/WhatsApp si ya tienes bloques)

def _get_cliente_tel(cliente: dict) -> str:
    """Obtiene teléfono de forma robusta desde el dict de cliente."""
    if not cliente:
        return ""
    for k in ["Telefono", "Teléfono", "Celular", "Movil", "Móvil"]:
        v = cliente.get(k, "")
        if v and str(v).strip():
            return str(v).strip()
    return ""

def tab_clientes_ui():
    st.header("Gestión de Clientes")
    # Formulario creación
    with st.expander("Nuevo Cliente"):
        with st.form("nuevo_cli"):
            cedula = st.text_input("Cédula")
            nombre = st.text_input("Nombre")
            tel = st.text_input("Teléfono")
            email = st.text_input("Email")
            dir = st.text_input("Dirección")
            mascota = st.text_input("Nombre Mascota Principal")
            tipo = st.selectbox("Tipo", ["Perro", "Gato", "Otro"])
            cumple = st.date_input("Cumpleaños Mascota")
            
            if st.form_submit_button("Guardar"):
                # Crear JSON simple
                info_m = json.dumps([{"Nombre": mascota, "Tipo": tipo, "Cumpleaños": str(cumple)}])
                fila = [cedula, nombre, tel, email, dir, mascota, tipo, str(cumple), now_co().strftime("%Y-%m-%d"), info_m]
                
                # Check si existe (local)
                df = st.session_state.db['cli']
                existe = df[df['Cedula'].astype(str) == str(cedula)]
                
                if not existe.empty:
                    # Update (más complejo, requeriría row_idx, por simplicidad en versión fixed sugerimos append o avisar)
                    st.warning("Cliente ya existe con esa cédula (Lógica update pendiente)")
                else:
                    registrar_cliente(fila)
                    st.success("Cliente guardado")
                    
                    # Generar link bienvenida
                    link = f"https://wa.me/{limpiar_tel(tel)}?text={urllib.parse.quote(msg_bienvenida(nombre, mascota))}"
                    st.markdown(f"[📲 Enviar Bienvenida]({link})")

    st.dataframe(st.session_state.db['cli'], use_container_width=True)

    # Botón para limpiar selección y permitir crear un nuevo cliente
    if st.button("🆕 Nuevo Cliente", help="Registrar un cliente desde cero"):
        st.session_state.cliente_actual = None
        st.session_state.mascota_seleccionada = None
        st.rerun()

def tab_despachos_ui():
    st.header("🚚 Despachos")
    df = st.session_state.db['ven']
    pendientes = df[df['Estado_Envio'].isin(["Pendiente", "En camino"])]
    
    if pendientes.empty:
        st.info("No hay despachos pendientes")
    else:
        st.dataframe(pendientes)
        sel_id = st.selectbox("Actualizar ID", pendientes['ID_Venta'])
        nuevo = st.selectbox("Nuevo Estado", ["Entregado", "Pagado", "Cancelado"])
        if st.button("Actualizar"):
            ok = actualizar_estado_envio(sel_id, nuevo)
            if ok: 
                st.success("Actualizado")
                st.rerun()
            else: st.error("Error al actualizar")

def tab_gastos_ui():
    st.header("Gastos")
    with st.form("gastos"):
        tipo = st.selectbox("Tipo", ["Variable", "Fijo"])
        cat = st.selectbox("Categoría", ["Inventario", "Servicios", "Nómina", "Otro"])
        desc = st.text_input("Descripción")
        monto = st.number_input("Monto", min_value=0.0)
        metodo = st.selectbox("Pago", ["Efectivo", "Bancos", "Nequi"])
        
        if st.form_submit_button("Registrar"):
            ts = int(now_co().timestamp())
            fila = [f"GAS-{ts}", now_co().strftime("%Y-%m-%d"), tipo, cat, desc, monto, metodo, ""]
            registrar_gasto(fila)
            st.success("Gasto guardado")

def tab_cuadre_ui():
    st.header("Cuadre de Caja")

    # --- NUEVO: Registro de Gastos/Pagos desde Cuadre de Caja ---
    with st.expander("Registrar Gasto o Pago (afecta cuadre)", expanded=False):
        with st.form("gasto_cuadre"):
            tipo = st.selectbox("Tipo", ["Variable", "Fijo"])
            cat = st.selectbox("Categoría", ["Inventario", "Servicios", "Nómina", "Otro"])
            desc = st.text_input("Descripción")
            monto = st.number_input("Monto", min_value=0.0)
            metodo = st.selectbox("Pago", ["Efectivo", "Bancos", "Nequi"])
            
            if st.form_submit_button("Registrar Gasto/Pago"):
                ts = int(now_co().timestamp())
                fila = [f"GAS-{ts}", now_co().strftime("%Y-%m-%d"), tipo, cat, desc, monto, metodo, ""]
                registrar_gasto(fila)
                st.success("Gasto/Pago guardado y descontado del cuadre")
                st.rerun()

    df_ven = st.session_state.db['ven']
    df_gas = st.session_state.db['gas']
    df_cie = st.session_state.db['cie']

    fecha = st.date_input("Fecha", now_co().date())

    # --- 1. Saldos previos (último cierre) ---
    base_inicial = 0.0
    if not df_cie.empty:
        df_cie['Fecha_dt'] = pd.to_datetime(df_cie['Fecha'], errors='coerce').dt.date
        prev_cierre = df_cie[df_cie['Fecha_dt'] < fecha].sort_values('Fecha_dt', ascending=False)
        if not prev_cierre.empty:
            base_inicial = prev_cierre.iloc[0]['Saldo_Real']
    # Forzar tipo float
    try:
        base_inicial = float(base_inicial)
    except Exception:
        base_inicial = 0.0

    # --- 2. Filtros locales ---
    df_ven['Fecha_dt'] = pd.to_datetime(df_ven['Fecha']).dt.date
    if 'Fecha' in df_gas.columns:
        df_gas['Fecha_dt'] = pd.to_datetime(df_gas['Fecha'], errors='coerce').dt.date
    else:
        df_gas['Fecha_dt'] = None

    v_dia = df_ven[df_ven['Fecha_dt'] == fecha]
    g_dia = df_gas[df_gas['Fecha_dt'] == fecha]

    # --- 3. Ventas por método ---
    v_efec = v_dia[v_dia['Metodo_Pago'] == 'Efectivo']['Total'].sum()
    v_tarj = v_dia[v_dia['Metodo_Pago'] == 'Tarjeta']['Total'].sum()
    v_digi = v_dia[v_dia['Metodo_Pago'].isin(['Nequi', 'Daviplata', 'Transferencia'])]['Total'].sum()
    v_elec = v_tarj + v_digi

    # --- 4. Gastos efectivo ---
    g_efec = g_dia[g_dia['Metodo_Pago'] == 'Efectivo']['Monto'].sum()

    # --- 5. Costo mercancía y margen ---
    costo_merc = v_dia['Costo_Total'].sum() if 'Costo_Total' in v_dia.columns else 0.0
    margen_ganado = v_dia['Total'].sum() - costo_merc
    margen_pct = (margen_ganado / costo_merc * 100) if costo_merc > 0 else 0

    # --- 6. KPIs ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Ventas Efectivo", f"${v_efec:,.0f}")
    c2.metric("Ventas Electrónico", f"${v_elec:,.0f}")
    c3.metric("Ventas Tarjeta", f"${v_tarj:,.0f}")
    c4.metric("Gastos Efectivo", f"${g_efec:,.0f}")
    c5.metric("Margen Ganado", f"${margen_ganado:,.0f}", f"{margen_pct:.1f}%")

    st.markdown("---")
    with st.form("cierre_caja"):
        base = st.number_input("Base Inicial", value=base_inicial, min_value=0.0)
        bancos = st.number_input("Enviado a Bancos", 0.0)
        real = st.number_input("Saldo Real (Conteo)", 0.0)
        notas = st.text_area("Notas")

        teorico = base + v_efec - g_efec - bancos
        dif = real - teorico
        st.caption(f"Teórico: ${teorico:,.0f} | Diferencia: ${dif:,.0f}")

        if st.form_submit_button("Guardar Cierre"):
            sh = conectar_google_sheets()
            ws_cie = obtener_worksheets(sh)["cie"]
            fila = [
                fecha.strftime("%Y-%m-%d"),
                now_co().strftime("%H:%M:%S"),
                base,
                v_efec,
                v_elec,
                g_efec,
                bancos,
                teorico,
                real,
                dif,
                notas,
                costo_merc,
                margen_ganado
            ]
            fila = [sanitizar_para_sheet(x) for x in fila]
            safe_api_call(ws_cie.append_row, fila)
            st.success("Cierre guardado en la nube")

def tab_resumen_ui():
    st.header("Resumen Gerencial")
    df = st.session_state.db['ven']
    if not df.empty:
        total = df['Total'].sum()
        st.metric("Ventas Históricas", f"${total:,.0f}")
        
        # Grafico simple
        df['Fecha_D'] = pd.to_datetime(df['Fecha']).dt.date
        diario = df.groupby('Fecha_D')['Total'].sum()
        st.bar_chart(diario)

# ==========================================
# 6. MAIN APP
# ==========================================

def main():
    # Inicialización de DB
    if 'db' not in st.session_state:
        cargar_datos_iniciales()
    
    # Barra Lateral
    with st.sidebar:
        st.title("Nexus Pro")
        if st.button("🔄 Sincronizar Datos", help="Trae cambios de la nube si alguien más editó el Excel"):
            st.cache_resource.clear()
            cargar_datos_iniciales()
            st.rerun()
        st.caption(f"Última sinc: {st.session_state.get('ultima_sincronizacion', 'Nunca').strftime('%H:%M:%S')}")
        
        st.divider()
        if st.button("🧱 Reparar IDs (Producto_UID + Norm)"):
            asegurar_ids_inventario_nube()

    # Tabs
    tabs = st.tabs(["🛒 POS", "👤 Clientes", "🚚 Despachos", "💳 Gastos", "💵 Cuadre", "📊 Resumen"])
    
    with tabs[0]: tab_pos()
    with tabs[1]: tab_clientes_ui()
    with tabs[2]: tab_despachos_ui()
    with tabs[3]: tab_gastos_ui()
    with tabs[4]: tab_cuadre_ui()
    with tabs[5]: tab_resumen_ui()

if __name__ == "__main__":
    main()