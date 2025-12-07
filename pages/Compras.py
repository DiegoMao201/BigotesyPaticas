import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime, date

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS (PROFESIONAL)
# ==========================================

COLOR_PRIMARIO = "#2ecc71"
COLOR_SECUNDARIO = "#e67e22"
COLOR_FONDO = "#f4f6f9"
COLOR_INFO = "#3498db"

st.set_page_config(page_title="Recepción Inteligente 3.0 - Ultimate", page_icon="📦", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_FONDO}; }}
    .big-title {{ font-family: 'Helvetica Neue', sans-serif; font-size: 2.5em; color: #2c3e50; font-weight: 800; margin-bottom: 0px; }}
    .sub-title {{ font-size: 1.2em; color: #7f8c8d; margin-bottom: 20px; }}
    /* Botones más bonitos y grandes */
    .stButton button[type="primary"] {{
        background: linear-gradient(45deg, {COLOR_PRIMARIO}, #27ae60);
        border: none; color: white; font-weight: bold; border-radius: 8px; padding: 0.8rem 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }}
    .stButton button[type="primary"]:hover {{ transform: scale(1.02); box-shadow: 0 6px 8px rgba(0,0,0,0.15); }}
    
    /* Tarjetas de métricas */
    .metric-card {{
        background-color: white; padding: 20px; border-radius: 12px;
        border-left: 5px solid {COLOR_INFO};
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; margin-bottom: 10px;
    }}
    .metric-label {{ font-size: 0.9em; color: #7f8c8d; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
    .metric-value {{ font-size: 1.8em; color: #2c3e50; font-weight: bold; }}
    
    /* Ajuste para que el Editor ocupe el ancho completo */
    .stDataFrame {{ width: 100%; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y UTILIDADES (OPTIMIZADO)
# ==========================================

@st.cache_resource(ttl=600)
def conectar_sheets():
    """Conecta a Google Sheets. Caché de 10 min para no reconectar a cada rato."""
    try:
        # Validación de secretos
        if "google_service_account" not in st.secrets:
            st.error("🚨 Error Crítico: Falta 'google_service_account' en secrets.toml")
            st.stop()
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        
        if "SHEET_URL" not in st.secrets:
            st.error("🚨 Error Crítico: Falta 'SHEET_URL' en secrets.toml")
            st.stop()
            
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # 1. Hoja Inventario (Principal)
        try:
            ws_inv = sh.worksheet("Inventario")
        except:
            st.error("🚨 No se encontró la pestaña 'Inventario'. Créala en tu Google Sheet.")
            st.stop()

        # 2. Hoja Maestro_Proveedores (Memoria)
        try:
            ws_map = sh.worksheet("Maestro_Proveedores")
        except:
            ws_map = sh.add_worksheet(title="Maestro_Proveedores", rows=2000, cols=10)
            ws_map.append_row(["ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Factor_Pack", "Ultima_Actualizacion"])
        
        # 3. Hoja Historial_Recepciones (Logs)
        try:
            ws_hist = sh.worksheet("Historial_Recepciones")
        except:
            ws_hist = sh.add_worksheet(title="Historial_Recepciones", rows=2000, cols=10)
            ws_hist.append_row(["Fecha_Recepcion", "Folio_Factura", "Proveedor", "Fecha_Emision_Factura", "Dias_Entrega", "Total_Items", "Total_Costo"])

        return sh, ws_inv, ws_map, ws_hist

    except Exception as e:
        st.error(f"Error fatal de conexión: {e}")
        st.stop()

def sanitizar_dato(dato):
    """Convierte numpy types a tipos nativos de Python para JSON/Sheets."""
    if isinstance(dato, (np.int64, np.int32)): return int(dato)
    if isinstance(dato, (np.float64, np.float32)): return float(dato)
    return dato

def limpiar_moneda(valor):
    """Limpia strings de dinero ($1,200.00) a float."""
    if isinstance(valor, (int, float)): return float(valor)
    if isinstance(valor, str):
        limpio = valor.replace('$', '').replace(',', '').strip()
        if not limpio: return 0.0
        try: return float(limpio)
        except: return 0.0
    return 0.0

# ==========================================
# 3. LECTURA DE INVENTARIO (EL CEREBRO DE BÚSQUEDA)
# ==========================================

# Usamos cache_data para que leer 600 lineas sea instantáneo tras la primera vez
@st.cache_data(ttl=300) 
def obtener_lista_inventario(_ws_inv):
    """
    Descarga TODO el inventario y crea la lista 'SKU | Nombre' para el buscador.
    El guión bajo en _ws_inv le dice a Streamlit que no hashee el objeto worksheet.
    """
    try:
        data = _ws_inv.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty: return ["Inventario Vacío"]

        # Normalización de columnas (quita espacios y mayúsculas)
        df.columns = [c.strip() for c in df.columns]
        mapa_cols = {c: c for c in df.columns}
        
        col_sku_real = None
        col_nom_real = None

        # Buscador inteligente de columnas
        for c in df.columns:
            cl = c.lower()
            if ('sku' in cl or 'codigo' in cl or 'ref' in cl) and 'prov' not in cl: 
                col_sku_real = c
            if ('nomb' in cl or 'desc' in cl or 'prod' in cl) and 'fact' not in cl: 
                col_nom_real = c
        
        if not col_sku_real or not col_nom_real:
            # Fallback si no encuentra columnas obvias
            return ["Error: Revisa encabezados (necesito SKU y Nombre)"]

        # Crear lista combinada limpia
        # Convertimos a string y quitamos NaN
        df['Display'] = df[col_sku_real].fillna('').astype(str) + " | " + df[col_nom_real].fillna('').astype(str)
        
        # Filtramos vacíos y duplicados
        lista = sorted(list(set(df['Display'].tolist())))
        lista = [x for x in lista if len(x) > 3] # Quitar basura corta
        
        lista.insert(0, "NUEVO (Crear Automáticamente)") 
        return lista
    except Exception as e:
        st.warning(f"Advertencia cargando lista: {e}")
        return ["NUEVO (Crear Automáticamente)"]

# ==========================================
# 4. MEMORIA Y APRENDIZAJE
# ==========================================

def cargar_memoria(ws_map):
    """Carga el cerebro: Qué SKU de proveedor corresponde a cuál interno."""
    try:
        data = ws_map.get_all_records()
        memoria = {}
        for row in data:
            # Clave compuesta única
            key = f"{str(row['ID_Proveedor']).strip()}_{str(row['SKU_Proveedor']).strip()}"
            memoria[key] = {
                'SKU_Interno': str(row['SKU_Interno']),
                'Factor_Pack': float(row['Factor_Pack']) if row['Factor_Pack'] else 1.0
            }
        return memoria
    except Exception:
        return {}

def guardar_aprendizaje(ws_map, nuevos_datos):
    """Guarda las nuevas relaciones en la hoja Maestro."""
    try:
        registros = ws_map.get_all_records()
        # Mapa de claves existentes para saber si actualizar o crear
        mapa_filas = {} 
        if registros:
            for idx, row in enumerate(registros):
                key = f"{str(row['ID_Proveedor']).strip()}_{str(row['SKU_Proveedor']).strip()}"
                mapa_filas[key] = idx + 2 # +2 por header y base 1 de Sheets

        filas_nuevas = []
        updates = []
        fecha_hoy = str(datetime.now())

        for item in nuevos_datos:
            # Limpieza del SKU seleccionado (quitar " | Nombre")
            val_sel = str(item['SKU_Interno_Seleccionado'])
            if " | " in val_sel:
                sku_interno = val_sel.split(" | ")[0].strip()
            elif "NUEVO" in val_sel:
                sku_interno = str(item['SKU_Proveedor']).strip()
            else:
                sku_interno = val_sel.strip()

            id_prov = str(item['ID_Proveedor']).strip()
            sku_prov = str(item['SKU_Proveedor']).strip()
            factor = item['Factor_Pack']
            nom_prov = item['Proveedor_Nombre']
            
            key = f"{id_prov}_{sku_prov}"
            
            if key in mapa_filas:
                # Si ya existe, actualizamos la relación (por si corrigieron algo)
                row_idx = mapa_filas[key]
                updates.append({'range': f"D{row_idx}", 'values': [[sku_interno]]})
                updates.append({'range': f"E{row_idx}", 'values': [[factor]]})
                updates.append({'range': f"F{row_idx}", 'values': [[fecha_hoy]]})
            else:
                # Si es nuevo, aprendemos
                filas_nuevas.append([id_prov, nom_prov, sku_prov, sku_interno, factor, fecha_hoy])

        if updates: ws_map.batch_update(updates)
        if filas_nuevas: ws_map.append_rows(filas_nuevas)
        return True
    except Exception as e:
        st.error(f"Error guardando memoria: {e}")
        return False

def registrar_historial_recepcion(ws_hist, datos_xml, total_costo):
    """Log de auditoría."""
    try:
        fecha_recepcion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            fecha_recepcion,
            datos_xml['Folio'],
            datos_xml['Proveedor'],
            datos_xml.get('Fecha_Emision', ''),
            datos_xml.get('Dias_Entrega', 0),
            len(datos_xml['Items']),
            total_costo
        ]
        ws_hist.append_row(row)
    except Exception as e:
        print(f"Error historial: {e}")

# ==========================================
# 5. PARSEO XML (LECTURA DE FACTURA)
# ==========================================

def parsear_xml_factura(archivo):
    """Lee el XML, soporta Namespaces complejos y extrae datos."""
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        ns_map = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }

        # Manejo de "AttachedDocument" (Factura anidada en Description)
        # Esto pasa mucho en facturación Latam
        desc_tag = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
        if desc_tag is not None and desc_tag.text and "Invoice" in desc_tag.text:
            try:
                root_invoice = ET.fromstring(desc_tag.text.strip())
            except:
                root_invoice = root
        else:
            root_invoice = root

        ns_inv = ns_map 

        # 1. Proveedor
        prov_node = root_invoice.find('.//cac:AccountingSupplierParty/cac:Party', ns_inv)
        if prov_node is not None:
            nombre_prov = prov_node.find('.//cac:PartyTaxScheme/cbc:RegistrationName', ns_inv).text
            id_prov = prov_node.find('.//cac:PartyTaxScheme/cbc:CompanyID', ns_inv).text
        else:
            nombre_prov = "PROVEEDOR DESCONOCIDO"
            id_prov = "GENERICO"
        
        # 2. Generales
        folio_node = root_invoice.find('.//cbc:ID', ns_inv)
        folio = folio_node.text if folio_node is not None else "S/F"
        
        fecha_node = root_invoice.find('.//cbc:IssueDate', ns_inv)
        fecha_emision_str = fecha_node.text if fecha_node is not None else datetime.now().strftime("%Y-%m-%d")
        
        try:
            f_emi = datetime.strptime(fecha_emision_str, "%Y-%m-%d").date()
            dias_entrega = (datetime.now().date() - f_emi).days
        except:
            dias_entrega = 0

        total_tag = root_invoice.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns_inv)
        total_factura = float(total_tag.text) if total_tag is not None else 0.0

        # 3. Items
        items = []
        for line in root_invoice.findall('.//cac:InvoiceLine', ns_inv):
            try:
                desc = line.find('.//cac:Item/cbc:Description', ns_inv).text
                qty = float(line.find('.//cbc:InvoicedQuantity', ns_inv).text)
                
                price_node = line.find('.//cac:Price/cbc:PriceAmount', ns_inv)
                costo_unit = float(price_node.text) if price_node is not None else 0.0
                
                # Buscar SKU en varios lugares
                sku = "S/C"
                sku_tag = line.find('.//cac:Item/cac:StandardItemIdentification/cbc:ID', ns_inv)
                if sku_tag is not None: sku = sku_tag.text
                else:
                    sku_tag_vend = line.find('.//cac:Item/cac:SellersItemIdentification/cbc:ID', ns_inv)
                    if sku_tag_vend is not None: sku = sku_tag_vend.text

                items.append({
                    "ID_Proveedor": id_prov,
                    "Proveedor_Nombre": nombre_prov,
                    "SKU_Proveedor": sku,
                    "Descripcion_Factura": desc,
                    "Cantidad_Facturada": qty,
                    "Costo_Pack_Factura": costo_unit,
                    "Total_Linea": qty * costo_unit
                })
            except: continue 

        return {
            "Proveedor": nombre_prov, 
            "ID_Proveedor": id_prov, 
            "Folio": folio, 
            "Fecha_Emision": fecha_emision_str,
            "Dias_Entrega": dias_entrega,
            "Total_Factura": total_factura,
            "Items": items
        }

    except Exception as e:
        st.error(f"Error leyendo XML: {str(e)}")
        return None

# ==========================================
# 6. ESCRITURA EN INVENTARIO (UPDATE)
# ==========================================

def procesar_inventario(ws_inv, df_final):
    """
    Actualiza el inventario sumando cantidades.
    Soporta hojas grandes (600+ filas) eficientemente.
    """
    try:
        data = ws_inv.get_all_values()
        if not data: return False, ["El inventario está vacío"]
        headers = [h.strip().lower() for h in data[0]]
    except: return False, ["Error leyendo inventario"]

    # Mapeo flexible de columnas
    col_sku = -1
    col_stock = -1
    col_costo = -1
    col_precio = -1
    col_nombre = -1

    for i, h in enumerate(headers):
        if ('sku' in h or 'codigo' in h) and 'prov' not in h: col_sku = i
        if 'stock' in h or 'cantidad' in h: col_stock = i
        if 'costo' in h: col_costo = i
        if 'precio' in h or 'venta' in h: col_precio = i
        if 'nomb' in h or 'desc' in h or 'prod' in h: col_nombre = i

    if col_sku == -1 or col_stock == -1:
        return False, [f"No encontré columnas SKU o Stock. Encabezados detectados: {data[0]}"]

    # Mapa rápido de SKU -> Fila (O(1) lookup)
    inv_map = {}
    for idx, row in enumerate(data):
        if idx == 0: continue # saltar header
        if len(row) > col_sku:
            sku_val = str(row[col_sku]).strip()
            if sku_val:
                # Guardamos info relevante para comparar precios
                inv_map[sku_val] = {
                    'fila': idx + 1, # Base 1 para GSpread
                    'stock_val': row[col_stock] if len(row) > col_stock else "0",
                    'costo_val': row[col_costo] if col_costo != -1 and len(row) > col_costo else "0"
                }

    updates = []
    new_rows = []
    log = []

    for _, row in df_final.iterrows():
        # Limpieza SKU Interno
        sel = str(row['SKU_Interno_Seleccionado'])
        if " | " in sel: sku_interno = sel.split(" | ")[0].strip()
        elif "NUEVO" in sel: sku_interno = str(row['SKU_Proveedor']).strip()
        else: sku_interno = sel.strip()
        
        # Cálculos Reales
        cant_recibida = row['Cantidad_Recibida']
        factor = row['Factor_Pack']
        costo_pack = row['Costo_Pack_Factura']
        
        unidades_reales = cant_recibida * factor
        if unidades_reales == 0: continue # Saltar si es 0

        costo_unitario_real = costo_pack / factor if factor > 0 else costo_pack
        nombre_prod = row['Descripcion_Factura']

        if sku_interno in inv_map:
            # === PRODUCTO EXISTENTE ===
            info = inv_map[sku_interno]
            fila = info['fila']
            
            # Stock
            stock_actual = limpiar_moneda(info['stock_val'])
            nuevo_stock = stock_actual + unidades_reales
            updates.append({'range': gspread.utils.rowcol_to_a1(fila, col_stock + 1), 'values': [[sanitizar_dato(nuevo_stock)]]})
            
            # Costo (Actualizar siempre al último o promedio, aquí usamos último)
            msg_precio = ""
            if col_costo != -1:
                costo_actual = limpiar_moneda(info['costo_val'])
                updates.append({'range': gspread.utils.rowcol_to_a1(fila, col_costo + 1), 'values': [[sanitizar_dato(costo_unitario_real)]]})
                
                if costo_unitario_real > costo_actual: msg_precio = "📈 Costo subió."
                elif costo_unitario_real < costo_actual: msg_precio = "💰 Costo bajó."
                
                # Regla de Precio Venta (Opcional: Margen 30%)
                if col_precio != -1:
                    nuevo_precio = costo_unitario_real / 0.70
                    updates.append({'range': gspread.utils.rowcol_to_a1(fila, col_precio + 1), 'values': [[sanitizar_dato(nuevo_precio)]]})

            log.append(f"🔄 **{sku_interno}**: Stock {stock_actual} -> {nuevo_stock}. {msg_precio}")
        
        else:
            # === PRODUCTO NUEVO ===
            # Creamos una fila vacía del tamaño correcto
            new_row = [""] * len(data[0])
            new_row[col_sku] = sku_interno
            new_row[col_stock] = sanitizar_dato(unidades_reales)
            if col_nombre != -1: new_row[col_nombre] = nombre_prod
            if col_costo != -1: new_row[col_costo] = sanitizar_dato(costo_unitario_real)
            if col_precio != -1: new_row[col_precio] = sanitizar_dato(costo_unitario_real / 0.70)
            
            new_rows.append(new_row)
            log.append(f"✨ **NUEVO**: {sku_interno} | {nombre_prod} | Stock Ini: {unidades_reales}")

    try:
        if updates: ws_inv.batch_update(updates)
        if new_rows: ws_inv.append_rows(new_rows)
        return True, log
    except Exception as e:
        return False, [f"Error escribiendo en Sheets: {e}"]

# ==========================================
# 7. MAIN APP UI
# ==========================================

def main():
    st.markdown('<p class="big-title">Recepción Inteligente 3.0 Ultimate</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Gestión masiva de inventario (600+ items), aprendizaje automático y XML.</p>', unsafe_allow_html=True)
    
    # Init Session
    if 'paso' not in st.session_state: st.session_state.paso = 1
    if 'xml_data' not in st.session_state: st.session_state.xml_data = None
    if 'df_mapped' not in st.session_state: st.session_state.df_mapped = None
    if 'catalogo' not in st.session_state: st.session_state.catalogo = []

    # Conexión
    sh, ws_inv, ws_map, ws_hist = conectar_sheets()
    if not sh: st.stop()

    # ------------------------------------------------------------------
    # PASO 1: CARGA
    # ------------------------------------------------------------------
    if st.session_state.paso == 1:
        st.markdown("### 1️⃣ Cargar Factura (XML)")
        
        # Botón para recargar inventario manualmente si cambias algo en el Excel
        if st.button("🔄 Refrescar Inventario de Google Sheets"):
            st.cache_data.clear()
            st.success("Caché limpiado. Se descargará el inventario fresco.")

        uploaded_file = st.file_uploader("Sube tu XML aquí", type=['xml'])
        
        if uploaded_file:
            with st.spinner("🚀 Analizando XML y descargando tu inventario completo..."):
                # 1. Parsear XML
                datos = parsear_xml_factura(uploaded_file)
                
                # 2. Cargar Catálogo (Cacheado)
                catalogo = obtener_lista_inventario(ws_inv)
                st.session_state.catalogo = catalogo # Guardar en sesión
                
                if datos and datos['Items']:
                    st.session_state.xml_data = datos
                    st.session_state.memoria = cargar_memoria(ws_map)
                    st.session_state.paso = 2
                    st.rerun()
                else:
                    st.error("Error: El XML no tiene items válidos o no se pudo leer.")

    # ------------------------------------------------------------------
    # PASO 2: ASOCIACIÓN (EL BUSCADOR INTELIGENTE)
    # ------------------------------------------------------------------
    elif st.session_state.paso == 2:
        data = st.session_state.xml_data
        memoria = st.session_state.memoria
        
        # Métricas
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><div class='metric-label'>Proveedor</div><div class='metric-value' style='font-size:1.2em'>{data['Proveedor'][:15]}..</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-label'>Folio</div><div class='metric-value'>{data['Folio']}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-label'>Items</div><div class='metric-value'>{len(data['Items'])}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-card'><div class='metric-label'>Total</div><div class='metric-value'>${data['Total_Factura']:,.0f}</div></div>", unsafe_allow_html=True)
        
        st.divider()
        st.markdown("### 2️⃣ Vinculación de Productos")
        st.info("💡 Escribe en la columna **'TU PRODUCTO'** (ej: 'chunk') para buscar en tu inventario de 600+ items. El sistema aprenderá tu elección.")

        # Construcción de la tabla
        filas = []
        catalogo = st.session_state.catalogo 

        for item in data['Items']:
            key = f"{str(data['ID_Proveedor']).strip()}_{str(item['SKU_Proveedor']).strip()}"
            
            # Valores por defecto
            sku_defecto = "NUEVO (Crear Automáticamente)"
            factor_defecto = 1.0
            
            # ¿Lo conocemos?
            if key in memoria:
                sku_mem = memoria[key]['SKU_Interno']
                # Buscamos coincidencias en el catálogo actual para preseleccionar
                # Esto asegura que el dropdown funcione aunque el nombre haya cambiado ligeramente
                match = next((s for s in catalogo if s.startswith(sku_mem + " |")), None)
                if match: sku_defecto = match
                else: sku_defecto = sku_mem # Fallback visual
                
                factor_defecto = memoria[key]['Factor_Pack']

            filas.append({
                "SKU_Proveedor": item['SKU_Proveedor'],
                "Descripcion_Factura": item['Descripcion_Factura'],
                "SKU_Interno_Seleccionado": sku_defecto,
                "Factor_Pack": factor_defecto,
                "Cantidad_Facturada": item['Cantidad_Facturada'],
                "Costo_Pack_Factura": item['Costo_Pack_Factura'],
                "ID_Proveedor": data['ID_Proveedor'],
                "Proveedor_Nombre": data['Proveedor']
            })
            
        df = pd.DataFrame(filas)

        # EDITOR PODEROSO
        edited_df = st.data_editor(
            df,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True, width="small"),
                "Descripcion_Factura": st.column_config.TextColumn("En Factura", disabled=True, width="medium"),
                
                # --- LA MAGIA: SELECTBOX BUSCABLE ---
                "SKU_Interno_Seleccionado": st.column_config.SelectboxColumn(
                    "🔍 TU PRODUCTO (Buscador)",
                    options=catalogo, # Aquí pasamos la lista completa cargada en Paso 1
                    required=True,
                    width="large",
                    help="Escribe para filtrar tu inventario..."
                ),
                # ------------------------------------
                
                "Factor_Pack": st.column_config.NumberColumn("📦 Unids/Caja", min_value=1, step=1),
                "Cantidad_Facturada": st.column_config.NumberColumn("Cant. Fac", disabled=True),
                "Costo_Pack_Factura": st.column_config.NumberColumn("Costo Caja", format="$%.2f", disabled=True),
                "ID_Proveedor": None, "Proveedor_Nombre": None # Ocultos
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            height=500
        )

        c1, c2 = st.columns([1, 4])
        if c1.button("⬅️ Cancelar"):
            st.session_state.paso = 1
            st.rerun()
        
        if c2.button("Siguiente: Verificar Físico ➡️", type="primary"):
            st.session_state.df_mapped = edited_df
            st.session_state.paso = 3
            st.rerun()

    # ------------------------------------------------------------------
    # PASO 3: VERIFICACIÓN FÍSICA Y GUARDADO
    # ------------------------------------------------------------------
    elif st.session_state.paso == 3:
        st.markdown("### 3️⃣ Recepción Física (Check Final)")
        st.warning("👇 Ajusta la columna **'RECIBIDO REAL'** si llegó menos mercancía.")
        
        df_verif = st.session_state.df_mapped.copy()
        
        # Init columna recepción
        if 'Cantidad_Recibida' not in df_verif.columns:
            df_verif['Cantidad_Recibida'] = df_verif['Cantidad_Facturada']
        
        # Cálculo visual total
        df_verif['Total_Unidades'] = df_verif['Cantidad_Recibida'] * df_verif['Factor_Pack']

        final_df = st.data_editor(
            df_verif,
            column_config={
                "SKU_Interno_Seleccionado": st.column_config.TextColumn("Producto", disabled=True),
                "Descripcion_Factura": st.column_config.TextColumn("Ref.", disabled=True),
                "Cantidad_Facturada": st.column_config.NumberColumn("Cant. Fac", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ RECIBIDO REAL", min_value=0, step=1),
                "Factor_Pack": st.column_config.NumberColumn("Factor", disabled=True),
                "Total_Unidades": st.column_config.ProgressColumn("Unidades Totales", format="%d", min_value=0, max_value=200),
                "SKU_Proveedor": None, "Costo_Pack_Factura": None, "ID_Proveedor": None, "Proveedor_Nombre": None
            },
            use_container_width=True,
            hide_index=True,
            height=500
        )

        # Validación
        diff = final_df['Cantidad_Facturada'] - final_df['Cantidad_Recibida']
        if diff.sum() > 0: st.error(f"⚠️ Faltan {diff.sum()} cajas vs Factura.")
        elif diff.sum() < 0: st.warning(f"⚠️ Sobran {-diff.sum()} cajas vs Factura.")
        else: st.success("✅ Todo cuadra perfecto.")

        st.divider()
        c1, c2 = st.columns([1, 4])
        if c1.button("⬅️ Atrás"):
            st.session_state.paso = 2
            st.rerun()

        if c2.button("💾 FINALIZAR Y ACTUALIZAR TODO", type="primary"):
            with st.status("🚀 Procesando actualización masiva...", expanded=True) as status:
                
                st.write("🧠 Aprendiendo nuevas vinculaciones de productos...")
                records = final_df.to_dict('records')
                guardar_aprendizaje(ws_map, records)
                
                st.write("📊 Guardando historial de tiempos y costos...")
                costo_total = (final_df['Cantidad_Recibida'] * final_df['Costo_Pack_Factura']).sum()
                registrar_historial_recepcion(ws_hist, st.session_state.xml_data, costo_total)
                
                st.write("📦 Actualizando stocks y precios en Inventario...")
                exito, logs = procesar_inventario(ws_inv, final_df)
                
                if exito:
                    status.update(label="¡Éxito Total!", state="complete", expanded=False)
                    st.balloons()
                    st.success("¡Inventario Actualizado!")
                    
                    with st.expander("📄 Ver Reporte de Cambios"):
                        for l in logs: st.write(l)
                    
                    time.sleep(5)
                    st.session_state.paso = 1
                    st.session_state.xml_data = None
                    st.rerun()
                else:
                    status.update(label="Error", state="error")
                    st.error("Hubo errores:")
                    for l in logs: st.error(l)

if __name__ == "__main__":
    main()
