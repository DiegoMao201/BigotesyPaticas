import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime, date

# --- 1. CONFIGURACIÓN Y ESTILOS ---

COLOR_PRIMARIO = "#2ecc71"
COLOR_SECUNDARIO = "#e67e22"
COLOR_FONDO = "#f4f6f9"
COLOR_INFO = "#3498db"

st.set_page_config(page_title="Recepción Inteligente 3.0 - Pro", page_icon="📦", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_FONDO}; }}
    .big-title {{ font-family: 'Helvetica Neue', sans-serif; font-size: 2.5em; color: #2c3e50; font-weight: 800; margin-bottom: 0px; }}
    .sub-title {{ font-size: 1.2em; color: #7f8c8d; margin-bottom: 20px; }}
    .stButton button[type="primary"] {{
        background: linear-gradient(45deg, {COLOR_PRIMARIO}, #27ae60);
        border: none; color: white; font-weight: bold; border-radius: 8px; padding: 0.6rem 1.2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .metric-card {{
        background-color: white; padding: 20px; border-radius: 12px;
        border-left: 5px solid {COLOR_INFO};
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center;
    }}
    .metric-label {{ font-size: 0.9em; color: #7f8c8d; font-weight: 600; text-transform: uppercase; }}
    .metric-value {{ font-size: 1.8em; color: #2c3e50; font-weight: bold; }}
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN Y UTILIDADES ---

@st.cache_resource(ttl=600)
def conectar_sheets():
    """Conecta a Google Sheets y asegura que existan las hojas necesarias."""
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account).")
            return None, None, None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        
        if "SHEET_URL" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (SHEET_URL).")
            return None, None, None, None
            
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # 1. Hoja Inventario (Principal)
        try:
            ws_inv = sh.worksheet("Inventario")
        except:
            st.error("No se encontró la pestaña 'Inventario'.")
            return None, None, None, None

        # 2. Hoja Maestro_Proveedores (Memoria de SKUs)
        try:
            ws_map = sh.worksheet("Maestro_Proveedores")
        except:
            ws_map = sh.add_worksheet(title="Maestro_Proveedores", rows=1000, cols=10)
            ws_map.append_row(["ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Factor_Pack", "Ultima_Actualizacion"])
        
        # 3. Hoja Historial_Recepciones (Lead Time y Logs)
        try:
            ws_hist = sh.worksheet("Historial_Recepciones")
        except:
            ws_hist = sh.add_worksheet(title="Historial_Recepciones", rows=1000, cols=10)
            ws_hist.append_row(["Fecha_Recepcion", "Folio_Factura", "Proveedor", "Fecha_Emision_Factura", "Dias_Entrega", "Total_Items", "Total_Costo"])

        return sh, ws_inv, ws_map, ws_hist

    except Exception as e:
        st.error(f"Error conexión a Google Sheets: {e}")
        return None, None, None, None

def sanitizar_dato(dato):
    if isinstance(dato, (np.int64, np.int32)): return int(dato)
    if isinstance(dato, (np.float64, np.float32)): return float(dato)
    return dato

def limpiar_moneda(valor):
    if isinstance(valor, (int, float)): return float(valor)
    if isinstance(valor, str):
        limpio = valor.replace('$', '').replace(',', '').strip()
        try: return float(limpio)
        except: return 0.0
    return 0.0

# --- 3. FUNCIONES DE LECTURA DE INVENTARIO PARA BÚSQUEDA ---

def obtener_lista_inventario(ws_inv):
    """Obtiene una lista formateada 'SKU | Nombre' para el dropdown."""
    try:
        data = ws_inv.get_all_records()
        df = pd.DataFrame(data)
        
        # Aseguramos nombres de columnas estándar
        mapa_cols = {c: c for c in df.columns}
        for c in df.columns:
            if 'sku' in c.lower() and 'prov' not in c.lower(): mapa_cols[c] = 'SKU'
            if 'nomb' in c.lower() or 'desc' in c.lower(): mapa_cols[c] = 'Nombre'
        
        df = df.rename(columns=mapa_cols)
        
        if 'SKU' not in df.columns or 'Nombre' not in df.columns:
            return []

        # Crear lista combinada para el selectbox
        df['Display'] = df['SKU'].astype(str) + " | " + df['Nombre'].astype(str)
        lista = df['Display'].tolist()
        lista.insert(0, "NUEVO (Crear Automáticamente)") # Opción por defecto para nuevos
        return lista
    except Exception as e:
        st.warning(f"No se pudo cargar la lista de inventario para búsqueda: {e}")
        return ["NUEVO (Crear Automáticamente)"]

# --- 4. MOTOR DE MEMORIA Y APRENDIZAJE ---

def cargar_memoria(ws_map):
    try:
        data = ws_map.get_all_records()
        memoria = {}
        for row in data:
            key = f"{str(row['ID_Proveedor'])}_{str(row['SKU_Proveedor'])}"
            memoria[key] = {
                'SKU_Interno': str(row['SKU_Interno']),
                'Factor_Pack': float(row['Factor_Pack']) if row['Factor_Pack'] else 1.0
            }
        return memoria
    except Exception:
        return {}

def guardar_aprendizaje(ws_map, nuevos_datos):
    try:
        registros = ws_map.get_all_records()
        df_map = pd.DataFrame(registros)
        
        filas_nuevas = []
        updates = []
        mapa_filas = {} 
        
        if not df_map.empty:
            for idx, row in df_map.iterrows():
                key = f"{str(row['ID_Proveedor'])}_{str(row['SKU_Proveedor'])}"
                mapa_filas[key] = idx + 2 # +2 por header y base 1

        for item in nuevos_datos:
            # Extraer SKU interno limpio (quitando el nombre si viene del dropdown)
            sku_interno_raw = str(item['SKU_Interno_Seleccionado'])
            if " | " in sku_interno_raw:
                sku_interno = sku_interno_raw.split(" | ")[0].strip()
            elif "NUEVO" in sku_interno_raw:
                sku_interno = str(item['SKU_Proveedor']) # Usamos el del proveedor si es nuevo
            else:
                sku_interno = sku_interno_raw

            proveedor_id = str(item['ID_Proveedor'])
            sku_prov = str(item['SKU_Proveedor'])
            factor = item['Factor_Pack']
            nombre_prov = item['Proveedor_Nombre']
            
            key = f"{proveedor_id}_{sku_prov}"
            
            if key in mapa_filas:
                # Actualizar SKU Interno y Factor si ya existe
                row_idx = mapa_filas[key]
                updates.append({'range': f"D{row_idx}", 'values': [[sku_interno]]})
                updates.append({'range': f"E{row_idx}", 'values': [[factor]]})
            else:
                # Aprender nueva asociación
                filas_nuevas.append([proveedor_id, nombre_prov, sku_prov, sku_interno, factor, str(datetime.now())])

        if updates: ws_map.batch_update(updates)
        if filas_nuevas: ws_map.append_rows(filas_nuevas)
        return True
    except Exception as e:
        st.error(f"Error guardando memoria: {e}")
        return False

def registrar_historial_recepcion(ws_hist, datos_xml, total_costo):
    """Guarda los metadatos de la recepción para medir tiempos."""
    try:
        fecha_recepcion = datetime.now().strftime("%Y-%m-%d")
        dias_entrega = datos_xml.get('Dias_Entrega', 0)
        
        row = [
            fecha_recepcion,
            datos_xml['Folio'],
            datos_xml['Proveedor'],
            datos_xml.get('Fecha_Emision', ''),
            dias_entrega,
            len(datos_xml['Items']),
            total_costo
        ]
        ws_hist.append_row(row)
    except Exception as e:
        print(f"Error historial: {e}")

# --- 5. PARSING XML (FACTURA) ---

def parsear_xml_factura(archivo):
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        # Namespaces comunes en facturación electrónica
        ns_map = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }

        # Intentar extraer Invoice anidado (común en algunos PACs)
        desc_tag = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
        if desc_tag is not None and desc_tag.text and "Invoice" in desc_tag.text:
            try:
                root_invoice = ET.fromstring(desc_tag.text.strip())
            except:
                root_invoice = root
        else:
            root_invoice = root

        ns_inv = ns_map # Reutilizar namespaces

        # 1. Datos Proveedor
        prov_node = root_invoice.find('.//cac:AccountingSupplierParty/cac:Party', ns_inv)
        if prov_node is not None:
            nombre_prov = prov_node.find('.//cac:PartyTaxScheme/cbc:RegistrationName', ns_inv).text
            id_prov = prov_node.find('.//cac:PartyTaxScheme/cbc:CompanyID', ns_inv).text
        else:
            nombre_prov = "Desconocido"
            id_prov = "GENERICO"
        
        # 2. Datos Generales Factura
        folio = root_invoice.find('.//cbc:ID', ns_inv).text
        
        # Fecha de Emisión y cálculo de días
        fecha_emision_str = root_invoice.find('.//cbc:IssueDate', ns_inv).text
        try:
            fecha_emision = datetime.strptime(fecha_emision_str, "%Y-%m-%d").date()
            dias_entrega = (datetime.now().date() - fecha_emision).days
        except:
            fecha_emision_str = "N/A"
            dias_entrega = 0

        # Total Factura
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
                
                # Buscar SKU en varios tags posibles
                sku_tag = line.find('.//cac:Item/cac:StandardItemIdentification/cbc:ID', ns_inv)
                if sku_tag is None:
                    sku_tag = line.find('.//cac:Item/cac:SellersItemIdentification/cbc:ID', ns_inv)
                sku = sku_tag.text if sku_tag is not None else "S/C"

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
        st.error(f"Error procesando XML: {str(e)}")
        return None

# --- 6. LÓGICA DE ACTUALIZACIÓN ---

def procesar_inventario(ws_inv, df_final):
    # Leer Inventario
    try:
        data = ws_inv.get_all_values()
        if not data: return False, ["El inventario está vacío"]
        headers = data[0]
    except: return False, ["Error leyendo inventario"]

    # Mapear columnas dinámicamente
    try:
        # Buscamos columnas clave ignorando mayúsculas
        header_map = {h.lower(): i for i, h in enumerate(headers)}
        
        col_sku = -1
        col_stock = -1
        col_costo = -1
        col_precio = -1
        col_nombre = -1

        for h, idx in header_map.items():
            if 'sku' in h and 'prov' not in h: col_sku = idx
            if 'stock' in h or 'cantidad' in h: col_stock = idx
            if 'costo' in h: col_costo = idx
            if 'precio' in h or 'venta' in h: col_precio = idx
            if 'nombre' in h or 'desc' in h: col_nombre = idx

        if col_sku == -1 or col_stock == -1:
            return False, [f"No se encontraron columnas SKU o Stock en el inventario. Encabezados: {headers}"]

    except Exception as e:
        return False, [f"Error mapeando columnas: {e}"]

    inv_map = {}
    # Crear índice rápido del inventario
    for i, row in enumerate(data[1:], start=2):
        if len(row) <= col_sku: continue
        sku_val = str(row[col_sku]).strip()
        if sku_val:
            inv_map[sku_val] = {
                'fila': i,
                'stock': limpiar_moneda(row[col_stock]) if len(row) > col_stock else 0,
                'costo': limpiar_moneda(row[col_costo]) if col_costo != -1 and len(row) > col_costo else 0,
                'precio': limpiar_moneda(row[col_precio]) if col_precio != -1 and len(row) > col_precio else 0,
                'nombre': row[col_nombre] if col_nombre != -1 and len(row) > col_nombre else "Sin Nombre"
            }

    updates = []
    new_rows = []
    log = []

    for _, row in df_final.iterrows():
        # Limpiar selección del dropdown (quitar " | Nombre")
        sku_raw = str(row['SKU_Interno_Seleccionado'])
        if " | " in sku_raw:
            sku_interno = sku_raw.split(" | ")[0].strip()
        elif "NUEVO" in sku_raw:
            sku_interno = str(row['SKU_Proveedor']).strip() # Usamos SKU prov si es nuevo
        else:
            sku_interno = sku_raw.strip()
            
        nombre_prod = row['Descripcion_Factura']
        
        # Usamos Cantidad RECIBIDA (Física), no la facturada
        cant_recibida = row['Cantidad_Recibida']
        factor = row['Factor_Pack']
        costo_pack = row['Costo_Pack_Factura']
        
        unidades_reales = cant_recibida * factor
        costo_unitario_real = costo_pack / factor if factor > 0 else costo_pack
        
        # Lógica de Actualización
        if sku_interno in inv_map:
            # ACTUALIZAR EXISTENTE
            info = inv_map[sku_interno]
            fila = info['fila']
            stock_actual = info['stock']
            costo_actual = info['costo']
            
            # Stock
            nuevo_stock = stock_actual + unidades_reales
            updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_stock + 1)}", 'values': [[sanitizar_dato(nuevo_stock)]]})

            # Precios y Costos (Solo si cambiaron significativamente)
            msg_precio = ""
            if col_costo != -1:
                updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_costo + 1)}", 'values': [[sanitizar_dato(costo_unitario_real)]]})
                
                if costo_unitario_real > costo_actual:
                    msg_precio = "📈 Costo subió."
                    # Opcional: Actualizar precio venta si se desea automatizar
                    if col_precio != -1:
                        nuevo_precio = costo_unitario_real / 0.70 # Ejemplo margen 30%
                        updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_precio + 1)}", 'values': [[sanitizar_dato(nuevo_precio)]]})
                elif costo_unitario_real < costo_actual:
                    msg_precio = "💰 Costo bajó."
            
            log.append(f"🔄 **{sku_interno}**: Stock {stock_actual} -> {nuevo_stock}. {msg_precio}")

        else:
            # CREAR NUEVO PRODUCTO
            new_row = [""] * len(headers)
            new_row[col_sku] = sku_interno
            if col_nombre != -1: new_row[col_nombre] = nombre_prod
            new_row[col_stock] = sanitizar_dato(unidades_reales)
            if col_costo != -1: new_row[col_costo] = sanitizar_dato(costo_unitario_real)
            if col_precio != -1: new_row[col_precio] = sanitizar_dato(costo_unitario_real / 0.70) # Margen sugerido
            
            new_rows.append(new_row)
            log.append(f"✨ **NUEVO**: {sku_interno} | {nombre_prod} | Stock Inicial: {unidades_reales}")

    try:
        if updates: ws_inv.batch_update(updates)
        if new_rows: ws_inv.append_rows(new_rows)
        return True, log
    except Exception as e:
        return False, [f"Error escribiendo Sheets: {e}"]

# --- 7. INTERFAZ DE USUARIO (MAIN) ---

def main():
    st.markdown('<p class="big-title">Recepción Inteligente 3.0</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Carga facturas, asocia inventario y verifica recepción física.</p>', unsafe_allow_html=True)
    
    # Conexión
    sh, ws_inv, ws_map, ws_hist = conectar_sheets()
    if not ws_inv: st.stop()

    # Session State
    if 'paso' not in st.session_state: st.session_state.paso = 1
    if 'xml_data' not in st.session_state: st.session_state.xml_data = None
    if 'df_mapped' not in st.session_state: st.session_state.df_mapped = None
    if 'lista_inventario' not in st.session_state: st.session_state.lista_inventario = []

    # ==========================================
    # PASO 1: CARGA DE FACTURA
    # ==========================================
    if st.session_state.paso == 1:
        st.markdown("### 1️⃣ Cargar XML de Factura")
        uploaded_file = st.file_uploader("Arrastra tu archivo XML aquí", type=['xml'])
        
        if uploaded_file:
            with st.spinner("Analizando factura y descargando inventario..."):
                datos = parsear_xml_factura(uploaded_file)
                
                # Cargar inventario para el dropdown
                st.session_state.lista_inventario = obtener_lista_inventario(ws_inv)
                
                if datos and datos['Items']:
                    st.session_state.xml_data = datos
                    st.session_state.memoria = cargar_memoria(ws_map)
                    st.session_state.paso = 2
                    st.rerun()
                else:
                    st.error("No se pudieron leer items del XML.")

    # ==========================================
    # PASO 2: ASOCIACIÓN (MAPPING) INTELIGENTE
    # ==========================================
    elif st.session_state.paso == 2:
        data = st.session_state.xml_data
        memoria = st.session_state.memoria
        
        # Header Informativo
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-card'><div class='metric-label'>Proveedor</div><div class='metric-value' style='font-size:1.2em'>{data['Proveedor'][:15]}..</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-label'>Fecha Emisión</div><div class='metric-value'>{data['Fecha_Emision']}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-label'>Días Entrega</div><div class='metric-value'>{data['Dias_Entrega']}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-card'><div class='metric-label'>Total Factura</div><div class='metric-value'>${data['Total_Factura']:,.0f}</div></div>", unsafe_allow_html=True)
        
        st.divider()
        st.markdown("### 2️⃣ Asocia los productos a tu Inventario")
        st.info("ℹ️ Selecciona tu producto en la columna **'🔍 TU PRODUCTO (Buscador)'**. El sistema recordará esto la próxima vez.")

        # Preparar Dataframe para Editor
        filas = []
        for item in data['Items']:
            key = f"{data['ID_Proveedor']}_{item['SKU_Proveedor']}"
            
            # Predicción basada en memoria
            sku_interno_default = "NUEVO (Crear Automáticamente)" # Default
            factor_prev = 1.0
            
            if key in memoria:
                sku_mem = memoria[key]['SKU_Interno']
                # Intentar buscar el string completo en la lista cargada
                match = next((s for s in st.session_state.lista_inventario if s.startswith(sku_mem + " |")), None)
                if match:
                    sku_interno_default = match
                else:
                    # Si está en memoria pero no en lista actual (raro), mantener lo que hay
                    sku_interno_default = sku_mem 
                
                factor_prev = memoria[key]['Factor_Pack']

            filas.append({
                "SKU_Proveedor": item['SKU_Proveedor'],
                "Descripcion_Factura": item['Descripcion_Factura'],
                "SKU_Interno_Seleccionado": sku_interno_default,
                "Factor_Pack": factor_prev,
                "Cantidad_Facturada": item['Cantidad_Facturada'],
                "Costo_Pack_Factura": item['Costo_Pack_Factura'],
                "ID_Proveedor": data['ID_Proveedor'],
                "Proveedor_Nombre": data['Proveedor']
            })
            
        df = pd.DataFrame(filas)

        # Editor de Datos con Selectbox
        edited_df = st.data_editor(
            df,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True, width="small"),
                "Descripcion_Factura": st.column_config.TextColumn("Producto en Factura", disabled=True, width="medium"),
                "SKU_Interno_Seleccionado": st.column_config.SelectboxColumn(
                    "🔍 TU PRODUCTO (Buscador)",
                    options=st.session_state.lista_inventario,
                    required=True,
                    width="large",
                    help="Escribe para buscar en tu inventario"
                ),
                "Factor_Pack": st.column_config.NumberColumn("📦 Unids/Caja", min_value=1, step=1),
                "Cantidad_Facturada": st.column_config.NumberColumn("Cant. Factura", disabled=True),
                "Costo_Pack_Factura": st.column_config.NumberColumn("Costo Caja", format="$%.2f", disabled=True),
                # Ocultos
                "ID_Proveedor": None, "Proveedor_Nombre": None
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            height=400
        )

        col1, col2 = st.columns([1, 4])
        if col1.button("⬅️ Cancelar"):
            st.session_state.paso = 1
            st.rerun()
        
        if col2.button("Ir a Recepción Física ➡️", type="primary"):
            st.session_state.df_mapped = edited_df
            st.session_state.paso = 3
            st.rerun()

    # ==========================================
    # PASO 3: RECEPCIÓN FÍSICA Y VERIFICACIÓN
    # ==========================================
    elif st.session_state.paso == 3:
        st.markdown("### 3️⃣ Recepción Física (Conteo Ciego)")
        st.warning("👇 Confirma cuántas cajas llegaron realmente. Si faltó algo, edita la columna 'Recibido Real'.")
        
        df_verif = st.session_state.df_mapped.copy()
        
        # Inicializar Recibido igual a Facturado
        if 'Cantidad_Recibida' not in df_verif.columns:
            df_verif['Cantidad_Recibida'] = df_verif['Cantidad_Facturada']
        
        # Calcular unidades totales para referencia visual
        df_verif['Total_Unidades'] = df_verif['Cantidad_Recibida'] * df_verif['Factor_Pack']

        # Editor Final
        final_df = st.data_editor(
            df_verif,
            column_config={
                "SKU_Interno_Seleccionado": st.column_config.TextColumn("Producto Asignado", disabled=True),
                "Descripcion_Factura": st.column_config.TextColumn("Ref. Factura", disabled=True),
                "Cantidad_Facturada": st.column_config.NumberColumn("Cant. Factura", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ RECIBIDO REAL", min_value=0, step=1, required=True),
                "Factor_Pack": st.column_config.NumberColumn("Factor", disabled=True),
                "Total_Unidades": st.column_config.ProgressColumn("Total Unidades Sueltas", format="%d", min_value=0, max_value=1000),
                # Ocultar resto
                "SKU_Proveedor": None, "Costo_Pack_Factura": None, "ID_Proveedor": None, "Proveedor_Nombre": None
            },
            use_container_width=True,
            hide_index=True
        )

        # Validación visual de discrepancias
        diff = final_df['Cantidad_Facturada'] - final_df['Cantidad_Recibida']
        if diff.sum() > 0:
            st.error(f"⚠️ Hay una diferencia de {diff.sum()} cajas faltantes respecto a la factura.")
        elif diff.sum() < 0:
            st.warning(f"⚠️ Estás recibiendo {-diff.sum()} cajas DE MÁS respecto a la factura.")
        else:
            st.success("✅ La recepción cuadra perfectamente con la factura.")

        st.divider()
        c1, c2 = st.columns([1, 4])
        
        if c1.button("⬅️ Atrás"):
            st.session_state.paso = 2
            st.rerun()
            
        if c2.button("💾 FINALIZAR Y ACTUALIZAR INVENTARIO", type="primary"):
            with st.spinner("Procesando... Guardando Aprendizaje... Actualizando Stocks..."):
                
                # 1. Guardar Memoria (Aprendizaje)
                records = final_df.to_dict('records')
                guardar_aprendizaje(ws_map, records)
                
                # 2. Guardar Historial de Tiempos
                costo_total_real = (final_df['Cantidad_Recibida'] * final_df['Costo_Pack_Factura']).sum()
                registrar_historial_recepcion(ws_hist, st.session_state.xml_data, costo_total_real)
                
                # 3. Actualizar Inventario Real
                exito, logs = procesar_inventario(ws_inv, final_df)
                
                if exito:
                    st.balloons()
                    st.success("¡Inventario Actualizado Exitosamente!")
                    with st.expander("Ver Bitácora de Cambios"):
                        for l in logs: st.write(l)
                    
                    time.sleep(5)
                    st.session_state.paso = 1
                    st.session_state.xml_data = None
                    st.rerun()
                else:
                    st.error("Hubo un error al actualizar:")
                    for l in logs: st.error(l)

if __name__ == "__main__":
    main()
