import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==========================================

st.set_page_config(
    page_title="Recepción Inteligente v4.0", 
    page_icon="📦", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS para limpieza visual
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1a202c; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #4a5568; margin-bottom: 2rem; }
    .metric-box {
        background: white; padding: 15px; border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center;
        border-top: 4px solid #3182ce;
    }
    .metric-lbl { font-size: 0.8rem; text-transform: uppercase; color: #718096; font-weight: 600; }
    .metric-val { font-size: 1.5rem; font-weight: 800; color: #2d3748; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN A GOOGLE SHEETS
# ==========================================

@st.cache_resource
def conectar_sheets():
    """Conexión persistente a Google Sheets."""
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración en secrets.toml")
            st.stop()
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Intentar obtener las hojas, si no existen las crea en memoria (y en sheets si se escribe)
        try: ws_inv = sh.worksheet("Inventario")
        except: st.error("❌ No encuentro la hoja 'Inventario'."); st.stop()
        
        try: ws_map = sh.worksheet("Maestro_Proveedores")
        except: 
            ws_map = sh.add_worksheet("Maestro_Proveedores", 1000, 6)
            ws_map.append_row(["ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "ID_Producto_Interno", "Factor_Pack", "Ultima_Act"])

        try: ws_hist = sh.worksheet("Historial_Recepciones")
        except:
            ws_hist = sh.add_worksheet("Historial_Recepciones", 1000, 8)
            ws_hist.append_row(["Fecha", "Folio", "Proveedor", "Items", "Costo_Total", "Usuario"])

        return sh, ws_inv, ws_map, ws_hist
    except Exception as e:
        st.error(f"Error de Conexión: {e}")
        st.stop()

# ==========================================
# 3. FUNCIONES DE AYUDA (LIMPIEZA DE DATOS)
# ==========================================

def clean_currency(val):
    """Convierte strings de dinero ($1.200,00) a float puro."""
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        # Quitar símbolos de moneda y espacios
        val = val.replace('$', '').replace(' ', '').strip()
        # Manejo de coma vs punto (asumiendo formato latino 1.000,00 o US 1,000.00)
        # Si tiene coma y punto, asumimos que la coma es decimal si está al final
        if ',' in val and '.' in val:
            val = val.replace(',', '') # Quitamos coma de miles (Formato US)
        elif ',' in val:
            val = val.replace(',', '.') # Coma decimal a punto
        try:
            return float(val)
        except:
            return 0.0
    return 0.0

def sanitizar_para_sheet(val):
    """Prepara datos de numpy para JSON."""
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    return val

# ==========================================
# 4. LECTURA DE INVENTARIO (EL CEREBRO)
# ==========================================

@st.cache_data(ttl=60)
def obtener_catalogo(_ws_inv):
    """
    Lee TU hoja de inventario buscando EXACTAMENTE tus columnas:
    ID_Producto | Nombre
    """
    try:
        data = _ws_inv.get_all_records()
        df = pd.DataFrame(data)
        
        # Verificar que existen tus columnas clave
        cols_necesarias = ['ID_Producto', 'Nombre']
        if not all(col in df.columns for col in cols_necesarias):
            st.error(f"🚨 Error: Tu hoja 'Inventario' DEBE tener las columnas: {cols_necesarias}. Columnas encontradas: {list(df.columns)}")
            return []

        # Crear lista para el buscador: "1001 | Taladro Percutor"
        # Convertimos a string para evitar errores si ID es numérico
        df['Buscador'] = df['ID_Producto'].astype(str) + " | " + df['Nombre'].astype(str)
        
        lista = sorted(df['Buscador'].unique().tolist())
        lista.insert(0, "NUEVO (Crear Producto)")
        return lista
    except Exception as e:
        st.error(f"Error leyendo inventario: {e}")
        return []

def cargar_memoria_aprendizaje(ws_map):
    """Carga relaciones guardadas: SKU_Proveedor -> ID_Producto_Interno"""
    try:
        data = ws_map.get_all_records()
        memoria = {}
        for row in data:
            # Clave única: ID_Proveedor + SKU_Proveedor
            key = f"{str(row['ID_Proveedor']).strip()}_{str(row['SKU_Proveedor']).strip()}"
            memoria[key] = {
                'ID_Interno': str(row['ID_Producto_Interno']),
                'Factor': float(row['Factor_Pack']) if row['Factor_Pack'] else 1.0
            }
        return memoria
    except:
        return {}

# ==========================================
# 5. PARSER XML (LECTOR DE FACTURAS)
# ==========================================

def leer_xml(archivo):
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        # Namespaces comunes en facturación electrónica
        ns = {'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
              'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'}
        
        # Intentar encontrar Invoice anidado (común en Latinoamérica)
        desc = root.find('.//cac:Attachment//cbc:Description', ns)
        if desc is not None and "Invoice" in desc.text:
            root = ET.fromstring(desc.text)

        # Datos Cabecera
        try:
            prov_node = root.find('.//cac:AccountingSupplierParty/cac:Party', ns)
            prov_name = prov_node.find('.//cbc:RegistrationName', ns).text
            prov_id = prov_node.find('.//cbc:CompanyID', ns).text
        except:
            prov_name = "Proveedor Desconocido"
            prov_id = "GENERICO"

        folio = root.find('.//cbc:ID', ns).text if root.find('.//cbc:ID', ns) is not None else "S/F"
        total = float(root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns).text)

        # Items
        items = []
        for line in root.findall('.//cac:InvoiceLine', ns):
            sku_prov = "S/C"
            # Buscar SKU en Standard o Sellers ID
            id_node = line.find('.//cac:Item/cac:StandardItemIdentification/cbc:ID', ns)
            if id_node is None: id_node = line.find('.//cac:Item/cac:SellersItemIdentification/cbc:ID', ns)
            if id_node is not None: sku_prov = id_node.text

            desc = line.find('.//cac:Item/cbc:Description', ns).text
            qty = float(line.find('.//cbc:InvoicedQuantity', ns).text)
            price = float(line.find('.//cac:Price/cbc:PriceAmount', ns).text)

            items.append({
                'SKU_Proveedor': sku_prov,
                'Descripcion': desc,
                'Cantidad': qty,
                'Costo_Unitario_XML': price,
                'Total_Linea': qty * price
            })

        return {'Proveedor': prov_name, 'ID_Proveedor': prov_id, 'Folio': folio, 'Total': total, 'Items': items}
    except Exception as e:
        st.error(f"Error parseando XML: {e}")
        return None

# ==========================================
# 6. LÓGICA DE ACTUALIZACIÓN (EL CEREBRO DE ESCRITURA)
# ==========================================

def actualizar_inventario(ws_inv, df_final):
    """
    Actualiza: Stock, Costo y Precio usando TUS COLUMNAS:
    ID_Producto, SKU_Proveedor, Nombre, Stock, Precio, Costo
    """
    try:
        # 1. Obtener todo el inventario actual
        data_inv = ws_inv.get_all_values()
        headers = data_inv[0]
        
        # Mapear índices de columnas (0-based)
        try:
            idx_id = headers.index("ID_Producto")
            idx_stock = headers.index("Stock")
            idx_costo = headers.index("Costo")
            idx_precio = headers.index("Precio")
            # Opcionales
            idx_nombre = headers.index("Nombre") if "Nombre" in headers else -1
            idx_sku_prov_inv = headers.index("SKU_Proveedor") if "SKU_Proveedor" in headers else -1
        except ValueError as ve:
            return False, [f"❌ Faltan columnas en Google Sheets. Revisa que existan exactamente: ID_Producto, Stock, Costo, Precio. Error: {ve}"]

        # Mapa para búsqueda rápida: ID_Producto -> Número de Fila (1-based para gspread)
        # Usamos ID_Producto como clave única
        mapa_filas = {}
        for i, row in enumerate(data_inv[1:], start=2): # start=2 porque row 1 es header
            id_prod = str(row[idx_id]).strip()
            if id_prod:
                mapa_filas[id_prod] = i

        updates = []
        nuevas_filas = []
        logs = []

        for _, row in df_final.iterrows():
            # Obtener ID Interno limpio del dropdown
            seleccion = str(row['ID_Interno_Seleccionado'])
            
            if "NUEVO" in seleccion:
                # === CREAR NUEVO ===
                id_nuevo = row['SKU_Proveedor'] # Usamos SKU prov como ID temporal si es nuevo
                desc_nueva = row['Descripcion']
                cant_real = row['Cantidad_Recibida'] * row['Factor_Pack']
                costo_nuevo = row['Costo_Unitario_XML'] / row['Factor_Pack']
                precio_nuevo = costo_nuevo / 0.70 # Margen 30% por defecto
                
                # Crear fila vacía del tamaño correcto
                new_row = [""] * len(headers)
                new_row[idx_id] = id_nuevo
                if idx_nombre != -1: new_row[idx_nombre] = desc_nueva
                new_row[idx_stock] = sanitizar_para_sheet(cant_real)
                new_row[idx_costo] = sanitizar_para_sheet(costo_nuevo)
                new_row[idx_precio] = sanitizar_para_sheet(precio_nuevo)
                if idx_sku_prov_inv != -1: new_row[idx_sku_prov_inv] = row['SKU_Proveedor']
                
                nuevas_filas.append(new_row)
                logs.append(f"✨ CREADO: {id_nuevo} | Stock: {cant_real}")
            
            else:
                # === ACTUALIZAR EXISTENTE ===
                id_interno = seleccion.split(" | ")[0].strip()
                
                if id_interno in mapa_filas:
                    fila_num = mapa_filas[id_interno]
                    
                    # Cálculos
                    cant_entrante = row['Cantidad_Recibida'] * row['Factor_Pack']
                    if cant_entrante == 0: continue

                    costo_nuevo_unit = row['Costo_Unitario_XML'] / row['Factor_Pack']
                    
                    # 1. Leer valores actuales (para sumar stock)
                    stock_actual = clean_currency(data_inv[fila_num-1][idx_stock])
                    stock_final = stock_actual + cant_entrante
                    
                    # 2. Preparar Updates (Batch)
                    # Columna Stock (idx + 1 para A1 notation)
                    updates.append({
                        'range': gspread.utils.rowcol_to_a1(fila_num, idx_stock + 1),
                        'values': [[sanitizar_para_sheet(stock_final)]]
                    })
                    
                    # Columna Costo (Sobrescribir con el último costo de factura)
                    updates.append({
                        'range': gspread.utils.rowcol_to_a1(fila_num, idx_costo + 1),
                        'values': [[sanitizar_para_sheet(costo_nuevo_unit)]]
                    })
                    
                    # Columna Precio (Opcional: Solo si el costo sube mucho o quieres automatizar)
                    # Aquí aplicamos regla: Precio = Costo / 0.7 (Margen 30%)
                    # Si prefieres NO tocar el precio, comenta estas 4 lineas:
                    precio_sugerido = costo_nuevo_unit / 0.70
                    updates.append({
                        'range': gspread.utils.rowcol_to_a1(fila_num, idx_precio + 1),
                        'values': [[sanitizar_para_sheet(precio_sugerido)]]
                    })

                    logs.append(f"🔄 {id_interno}: Stock {stock_actual} -> {stock_final} | Costo actualizado a ${costo_nuevo_unit:,.2f}")
                else:
                    logs.append(f"⚠️ Error: El ID {id_interno} estaba en la lista pero no lo encontré en la hoja al guardar.")

        # Ejecutar cambios en Google Sheets
        if updates: ws_inv.batch_update(updates)
        if nuevas_filas: ws_inv.append_rows(nuevas_filas)
        
        return True, logs

    except Exception as e:
        return False, [f"Error crítico en script de actualización: {e}"]

def guardar_maestro(ws_map, datos):
    """Guarda la relación SKU Prov <-> ID Producto para la próxima vez."""
    try:
        new_rows = []
        fecha = datetime.now().strftime("%Y-%m-%d")
        for row in datos:
            sel = row['ID_Interno_Seleccionado']
            if "NUEVO" not in sel:
                id_interno = sel.split(" | ")[0].strip()
                new_rows.append([
                    str(row['ID_Proveedor']),
                    str(row['Proveedor_Nombre']),
                    str(row['SKU_Proveedor']),
                    id_interno,
                    row['Factor_Pack'],
                    fecha
                ])
        if new_rows: ws_map.append_rows(new_rows)
    except: pass

# ==========================================
# 7. INTERFAZ DE USUARIO (MAIN APP)
# ==========================================

def main():
    st.markdown('<div class="main-header">Recepción Inteligente 4.0</div>', unsafe_allow_html=True)
    
    # Manejo de sesión
    if 'step' not in st.session_state: st.session_state.step = 1
    if 'xml_data' not in st.session_state: st.session_state.xml_data = None
    if 'catalogo' not in st.session_state: st.session_state.catalogo = []
    
    sh, ws_inv, ws_map, ws_hist = conectar_sheets()

    # ---------------------------------------------------------
    # PASO 1: CARGAR XML
    # ---------------------------------------------------------
    if st.session_state.step == 1:
        st.markdown('<div class="sub-header">Paso 1: Sube tu Factura XML</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("Arrastra tu XML aquí", type=['xml'])
        with col2:
            st.info("💡 El sistema buscará coincidencias en tus columnas: **ID_Producto, Nombre, Stock, Costo, Precio**.")
            if st.button("🔄 Refrescar Memoria del Inventario"):
                st.cache_data.clear()
                st.success("Caché limpiado.")

        if uploaded_file:
            with st.spinner("Leyendo XML y descargando Inventario..."):
                # 1. Leer XML
                data_xml = leer_xml(uploaded_file)
                if not data_xml: st.stop()
                
                # 2. Descargar Catálogo
                catalogo = obtener_catalogo(ws_inv)
                if not catalogo: st.stop()

                # 3. Guardar en sesión
                st.session_state.xml_data = data_xml
                st.session_state.catalogo = catalogo
                st.session_state.memoria = cargar_memoria_aprendizaje(ws_map)
                st.session_state.step = 2
                st.rerun()

    # ---------------------------------------------------------
    # PASO 2: VINCULAR PRODUCTOS (MATCHING)
    # ---------------------------------------------------------
    elif st.session_state.step == 2:
        data = st.session_state.xml_data
        mem = st.session_state.memoria
        
        # Tarjetas Métricas
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-box'><div class='metric-lbl'>Proveedor</div><div class='metric-val'>{data['Proveedor'][:15]}..</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-box'><div class='metric-lbl'>Items</div><div class='metric-val'>{len(data['Items'])}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-box'><div class='metric-lbl'>Total Factura</div><div class='metric-val'>${data['Total']:,.2f}</div></div>", unsafe_allow_html=True)
        
        st.write("---")
        st.subheader("🔍 Vincula los productos de la factura con TU Inventario")
        
        # Preparar DataFrame para el Editor
        rows = []
        for item in data['Items']:
            key = f"{data['ID_Proveedor']}_{item['SKU_Proveedor']}"
            
            # Predicción basada en memoria
            pred_id = "NUEVO (Crear Producto)"
            pred_factor = 1.0
            
            if key in mem:
                id_mem = mem[key]['ID_Interno']
                # Buscar ese ID en el catálogo actual para seleccionarlo en el dropdown
                match = next((x for x in st.session_state.catalogo if x.startswith(id_mem + " |")), None)
                if match: pred_id = match
                pred_factor = mem[key]['Factor']

            rows.append({
                "SKU_Proveedor": item['SKU_Proveedor'],
                "Descripcion": item['Descripcion'],
                "ID_Interno_Seleccionado": pred_id,
                "Factor_Pack": pred_factor,
                "Cantidad_XML": item['Cantidad'],
                "Costo_Unitario_XML": item['Costo_Unitario_XML'],
                "ID_Proveedor": data['ID_Proveedor'],
                "Proveedor_Nombre": data['Proveedor']
            })

        df = pd.DataFrame(rows)

        # CONFIGURACIÓN DEL EDITOR (Aquí está la magia de la UI)
        edited_df = st.data_editor(
            df,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True, width="small"),
                "Descripcion": st.column_config.TextColumn("Descripción Factura", disabled=True, width="medium"),
                
                # DROPDOWN INTELIGENTE
                "ID_Interno_Seleccionado": st.column_config.SelectboxColumn(
                    "📌 TU PRODUCTO (ID | Nombre)",
                    options=st.session_state.catalogo,
                    required=True,
                    width="large",
                    help="Selecciona el producto de tu inventario que corresponde."
                ),
                
                "Factor_Pack": st.column_config.NumberColumn("📦 Unid/Caja", min_value=1, step=1, help="Si viene en caja de 12, pon 12."),
                "Cantidad_XML": st.column_config.NumberColumn("Cant.", disabled=True),
                "Costo_Unitario_XML": st.column_config.NumberColumn("Costo Fac", format="$%.2f", disabled=True),
                "ID_Proveedor": None, "Proveedor_Nombre": None # Ocultos
            },
            hide_index=True,
            use_container_width=True,
            height=500
        )

        col_back, col_next = st.columns([1, 5])
        if col_back.button("⬅️ Atrás"):
            st.session_state.step = 1
            st.rerun()
        
        if col_next.button("Verificar Recepción Física ➡️", type="primary"):
            st.session_state.mapped_df = edited_df
            st.session_state.step = 3
            st.rerun()

    # ---------------------------------------------------------
    # PASO 3: CONFIRMACIÓN Y ESCRITURA
    # ---------------------------------------------------------
    elif st.session_state.step == 3:
        st.markdown('<div class="sub-header">Paso 3: Verificación Física</div>', unsafe_allow_html=True)
        
        df_final = st.session_state.mapped_df.copy()
        
        # Columna para ajustar si llegó menos mercancía
        if 'Cantidad_Recibida' not in df_final.columns:
            df_final['Cantidad_Recibida'] = df_final['Cantidad_XML']
        
        df_final['Total_Unidades_Reales'] = df_final['Cantidad_Recibida'] * df_final['Factor_Pack']

        st.info("👇 Ajusta la columna **'RECIBIDO REAL'** si hay faltantes. Si todo está bien, solo dale a Finalizar.")

        verified_df = st.data_editor(
            df_final,
            column_config={
                "ID_Interno_Seleccionado": st.column_config.TextColumn("Tu Producto", disabled=True),
                "Descripcion": st.column_config.TextColumn("Desc. Factura", disabled=True),
                "Cantidad_XML": st.column_config.NumberColumn("Facturado", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ RECIBIDO REAL", min_value=0),
                "Total_Unidades_Reales": st.column_config.NumberColumn("Total Unidades a Sumar", disabled=True),
                "Factor_Pack": st.column_config.NumberColumn("Factor", disabled=True),
                "SKU_Proveedor": None, "Costo_Unitario_XML": None, "ID_Proveedor": None
            },
            hide_index=True,
            use_container_width=True
        )

        st.divider()
        if st.button("🚀 FINALIZAR Y ACTUALIZAR INVENTARIO", type="primary", use_container_width=True):
            
            with st.status("Procesando datos...", expanded=True) as status:
                
                # 1. Guardar Aprendizaje
                st.write("🧠 Guardando relaciones de productos...")
                guardar_maestro(ws_map, verified_df.to_dict('records'))
                
                # 2. Actualizar Inventario (Stock, Costo, Precio)
                st.write("📦 Actualizando Stocks, Costos y Precios en Sheets...")
                exito, log_msgs = actualizar_inventario(ws_inv, verified_df)
                
                # 3. Historial
                st.write("📄 Firmando historial...")
                ws_hist.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    st.session_state.xml_data['Folio'],
                    st.session_state.xml_data['Proveedor'],
                    len(verified_df),
                    st.session_state.xml_data['Total'],
                    "Streamlit App"
                ])
                
                if exito:
                    status.update(label="¡Completado con Éxito!", state="complete", expanded=False)
                    st.balloons()
                    st.success("✅ Inventario actualizado correctamente.")
                    with st.expander("Ver detalles de cambios"):
                        for msg in log_msgs: st.write(msg)
                    
                    time.sleep(3)
                    st.session_state.step = 1
                    st.session_state.xml_data = None
                    st.rerun()
                else:
                    status.update(label="Error", state="error")
                    st.error("Hubo errores:")
                    for msg in log_msgs: st.error(msg)

if __name__ == "__main__":
    main()
