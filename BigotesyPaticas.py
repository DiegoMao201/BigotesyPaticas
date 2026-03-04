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
import uuid  # <-- NUEVO

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

def msg_venta(nombre, mascota, items_str, total):
    return f"""🧾 Hola {nombre}, gracias por tu compra en Bigotes y Patitas.
🐶 Mascota: {mascota or 'tu peludito'}
🛍️ Items: {items_str}
💰 Total: ${total:,.0f}
🚚 Si necesitas algo más, avísanos. ¡Gracias! 🐾"""

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

# ==========================================
# 4. FUNCIONES DE ESCRITURA (OPTIMIZADAS)
# ==========================================

def registrar_venta(fila_datos, carrito):
    """Escribe en Sheet y actualiza Session State localmente"""
    sh = conectar_google_sheets()
    ws_ven = obtener_worksheets(sh)["ven"]
    ws_inv = obtener_worksheets(sh)["inv"]

    # 1. Escribir Venta en la Nube (con retry)
    safe_api_call(ws_ven.append_row, fila_datos)

    # 2. Actualizar Stock (prioridad: Producto_UID)
    df_inv = st.session_state.db["inv"].copy()

    # Normalizaciones mínimas
    if "ID_Producto_Norm" not in df_inv.columns and "ID_Producto" in df_inv.columns:
        df_inv["ID_Producto_Norm"] = df_inv["ID_Producto"].apply(normalizar_id_producto)
    if "Producto_UID" not in df_inv.columns:
        df_inv["Producto_UID"] = ""

    # Headers nube (para ubicar columnas)
    headers = safe_api_call(ws_inv.row_values, 1) or []
    if "Stock" not in headers:
        st.error("No existe columna 'Stock' en Inventario (nube).")
        return
    col_stock = headers.index("Stock") + 1

    # Opcional: usar Producto_UID si existe en nube
    col_uid = (headers.index("Producto_UID") + 1) if "Producto_UID" in headers else None

    for item in carrito:
        cant = float(item.get("Cantidad", 0) or 0)
        if cant <= 0:
            continue

        uid = str(item.get("Producto_UID", "")).strip()
        id_norm = str(item.get("ID_Producto_Norm", "")).strip() or normalizar_id_producto(item.get("ID_Producto", ""))

        match = pd.DataFrame()
        if uid:
            match = df_inv[df_inv["Producto_UID"].astype(str).str.strip() == uid]
        if match.empty and id_norm:
            match = df_inv[df_inv["ID_Producto_Norm"].astype(str).str.strip() == id_norm]

        if match.empty:
            continue

        idx = match.index[0]
        stock_actual = float(match.iloc[0].get("Stock", 0) or 0)
        nuevo_stock = stock_actual - cant

        # Actualizar LOCAL
        st.session_state.db["inv"].at[idx, "Stock"] = nuevo_stock

        # Actualizar NUBE (find por UID si existe; fallback a ID_Producto original)
        try:
            cell = None
            if uid:
                cell = safe_api_call(ws_inv.find, uid)
            if (cell is None) and ("ID_Producto" in match.columns):
                id_original = str(match.iloc[0]["ID_Producto"])
                cell = safe_api_call(ws_inv.find, id_original)

            if cell:
                safe_api_call(ws_inv.update_cell, cell.row, col_stock, nuevo_stock)
        except Exception as e:
            print(f"Error actualizando stock nube: {e}")

    # 3. Actualizar Venta LOCALMENTE
    cols = st.session_state.db["ven"].columns
    if len(fila_datos) < len(cols):
        fila_datos += [""] * (len(cols) - len(fila_datos))
    nuevo_df = pd.DataFrame([fila_datos], columns=cols)
    if "Total" in nuevo_df.columns:
        nuevo_df["Total"] = pd.to_numeric(nuevo_df["Total"])
    if "Fecha" in nuevo_df.columns:
        nuevo_df["Fecha"] = pd.to_datetime(nuevo_df["Fecha"])
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

    # --- 2. PRODUCTOS ---
    st.markdown("### 🛒 Productos")
    if not df_inv.empty:
        # Crear columna de busqueda visual
        df_inv['Display'] = df_inv.apply(lambda x: f"{x['Nombre']} | Stock: {int(x['Stock'])} | ${int(x['Precio']):,}", axis=1)
        # Diccionario para mapear display -> ID
        # Necesitamos normalizar para keys consistentes
        df_inv['ID_Norm'] = df_inv['ID_Producto'].apply(normalizar_id_producto)
        mapa_prod = dict(zip(df_inv['Display'], df_inv['ID_Norm']))
        
        prod_sel = st.selectbox("Buscar Producto", df_inv['Display'].tolist())
        
        if prod_sel:
            id_sel = mapa_prod[prod_sel]
            row_prod = df_inv[df_inv["ID_Norm"] == id_sel].iloc[0]
            producto_uid = str(row_prod.get("Producto_UID", "")).strip()

            # --- 3. CARRITO Y CIERRE ---
            if st.session_state.carrito:
                st.markdown("### 🧺 Detalle de Compra")
                df_car = pd.DataFrame(st.session_state.carrito)
                
                edited_car = st.data_editor(
                    df_car, 
                    key="editor_carrito",
                    column_config={"Subtotal": st.column_config.NumberColumn(disabled=True)},
                    num_rows="dynamic"
                )
                
                # Recalcular si hubo cambios
                if not df_car.equals(edited_car):
                    for i, r in edited_car.iterrows():
                        edited_car.at[i, 'Subtotal'] = (r['Precio'] - r['Descuento']) * r['Cantidad']
                    st.session_state.carrito = edited_car.to_dict('records')
                    st.rerun()
                    
                total = sum([x['Subtotal'] for x in st.session_state.carrito])
                st.markdown(f'<div class="carrito-total">TOTAL: ${total:,.0f}</div>', unsafe_allow_html=True)
                
                if st.button("🗑️ Vaciar Carrito"):
                    st.session_state.carrito = []
                    st.rerun()
                    
                st.markdown("---")
                c1, c2 = st.columns(2)
                metodo = c1.selectbox("Pago", ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"])
                entrega = c2.selectbox("Entrega", ["Local", "Domicilio"])
                dir_envio = st.text_input("Dirección", value=st.session_state.cliente_actual.get('Direccion', '') if st.session_state.cliente_actual else "")

                if st.button("✅ FINALIZAR VENTA", type="primary", use_container_width=True):
                    if not st.session_state.cliente_actual:
                        st.error("Falta seleccionar cliente")
                    else:
                        with st.spinner("Procesando..."):
                            id_venta = f"VEN-{int(now_co().timestamp())}"
                            fecha = now_co().strftime("%Y-%m-%d %H:%M:%S")
                            items_str = ", ".join([f"{x['Cantidad']}x {x['Nombre_Producto']}" for x in st.session_state.carrito])
                            items_json = json.dumps([
                                {
                                    "Producto_UID": x.get("Producto_UID", ""),          # <-- NUEVO
                                    "ID": x["ID_Producto"],
                                    "ID_Producto_Norm": x["ID_Producto_Norm"],
                                    "Nombre": x["Nombre_Producto"],
                                    "Cantidad": x["Cantidad"]
                                } for x in st.session_state.carrito
                            ])
                            costo_total = sum([x.get('Costo',0)*x['Cantidad'] for x in st.session_state.carrito])
                            
                            fila = [
                                id_venta, fecha, 
                                st.session_state.cliente_actual.get('Cedula',''),
                                st.session_state.cliente_actual.get('Nombre',''),
                                entrega, dir_envio, 
                                "Pendiente" if entrega != "Local" else "Entregado",
                                metodo, "", total, items_str, items_json, costo_total,
                                st.session_state.mascota_seleccionada
                            ]
                            
                            # REGISTRAR (NUBE Y LOCAL)
                            registrar_venta(fila, st.session_state.carrito)
                            
                            # GENERAR DOCUMENTOS
                            venta_dict = {
                                'ID': id_venta, 'Fecha': fecha, 'Cliente': st.session_state.cliente_actual.get('Nombre'),
                                'Cedula_Cliente': st.session_state.cliente_actual.get('Cedula'), 'Direccion': dir_envio,
                                'Mascota': st.session_state.mascota_seleccionada, 'Metodo_Pago': metodo, 'Tipo_Entrega': entrega, 'Total': total
                            }
                            pdf = generar_pdf_html(venta_dict, st.session_state.carrito)
                            st.session_state.ultimo_pdf = pdf
                            st.session_state.ultima_venta_id = id_venta
                            
                            tel = limpiar_tel(st.session_state.cliente_actual.get('Telefono',''))
                            if tel:
                                txt = msg_venta(venta_dict['Cliente'], venta_dict['Mascota'], items_str, total)
                                st.session_state.whatsapp_link = f"https://wa.me/{tel}?text={urllib.parse.quote(txt)}"
                            
                            st.session_state.carrito = []
                            st.success("Venta Exitosa")
                            st.rerun()

    if st.session_state.ultimo_pdf:
        c1, c2 = st.columns(2)
        c1.download_button("📄 PDF Factura", st.session_state.ultimo_pdf, file_name=f"Factura_{st.session_state.ultima_venta_id}.pdf", mime="application/pdf")
        if st.session_state.whatsapp_link:
            c2.markdown(f'<a href="{st.session_state.whatsapp_link}" target="_blank" class="btn-factura">📲 Enviar WhatsApp</a>', unsafe_allow_html=True)

    # Botón para limpiar todo y empezar una nueva venta
    if st.button("🆕 Nueva Venta", help="Iniciar una venta desde cero"):
        st.session_state.carrito = []
        st.session_state.cliente_actual = None
        st.session_state.mascota_seleccionada = None
        st.session_state.ultimo_pdf = None
        st.session_state.ultima_venta_id = None
        st.session_state.whatsapp_link = None
        st.rerun()

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