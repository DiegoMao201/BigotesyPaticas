import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================

st.set_page_config(
    page_title="Recepción Inteligente v6.0 (Master Brain)", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS para una interfaz profesional
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1e3a8a; margin-bottom: 0.5rem; text-align: center; }
    .sub-header { font-size: 1.2rem; color: #64748b; margin-bottom: 2rem; text-align: center; }
    .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .success-box { background-color: #dcfce7; color: #166534; padding: 10px; border-radius: 8px; border: 1px solid #bbf7d0; text-align: center; font-weight: bold; }
    .warning-box { background-color: #fef9c3; color: #854d0e; padding: 10px; border-radius: 8px; border: 1px solid #fde047; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES DE LIMPIEZA Y UTILIDADES
# ==========================================

def normalizar_str(valor):
    """Limpia textos para comparaciones exactas (quita espacios y pone mayúsculas)."""
    if pd.isna(valor) or valor == "":
        return ""
    return str(valor).strip().upper()

def clean_currency(val):
    """Convierte formatos de moneda ($1.200,00) a float puro."""
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').strip()
        # Manejo de coma vs punto
        if ',' in val and '.' in val:
            val = val.replace(',', '') # Asumimos miles con coma
        elif ',' in val:
            val = val.replace(',', '.') # Asumimos decimal con coma
        try:
            return float(val)
        except:
            return 0.0
    return 0.0

def sanitizar_para_sheet(val):
    """Convierte tipos de Numpy a tipos nativos de Python para evitar errores JSON."""
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    return val

# ==========================================
# 3. CONEXIÓN A GOOGLE SHEETS
# ==========================================

@st.cache_resource
def conectar_sheets():
    """Conecta a Google Sheets y asegura que existan las pestañas necesarias."""
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Error: No se encontraron las credenciales en secrets.toml")
            st.stop()
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # 1. Hoja Inventario
        try: ws_inv = sh.worksheet("Inventario")
        except: st.error("❌ No existe la hoja 'Inventario'. Por favor créala."); st.stop()
        
        # 2. Hoja Maestro_Proveedores (Cerebro)
        try: 
            ws_map = sh.worksheet("Maestro_Proveedores")
        except: 
            # Si no existe, la creamos con las columnas que pediste
            ws_map = sh.add_worksheet("Maestro_Proveedores", 1000, 6)
            ws_map.append_row(["ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Factor_Pack", "Ultima_Actualizacion"])

        # 3. Hoja Historial
        try: 
            ws_hist = sh.worksheet("Historial_Recepciones")
        except:
            ws_hist = sh.add_worksheet("Historial_Recepciones", 1000, 7)
            ws_hist.append_row(["Fecha", "Folio", "Proveedor", "Items_Procesados", "Monto_Total", "Usuario", "Estado"])

        return sh, ws_inv, ws_map, ws_hist
    except Exception as e:
        st.error(f"Error Crítico de Conexión: {e}")
        st.stop()

# ==========================================
# 4. LÓGICA DE CEREBRO (MEMORIA Y CATÁLOGO)
# ==========================================

@st.cache_data(ttl=60)
def cargar_datos_sistema(_ws_inv, _ws_map):
    """
    Carga dos cosas vitales:
    1. Catálogo actual (Lista de productos internos).
    2. Memoria de aprendizaje (Relación Proveedor -> Interno).
    """
    # --- A. CARGAR INVENTARIO ---
    try:
        data_inv = _ws_inv.get_all_records()
        df_inv = pd.DataFrame(data_inv)
        
        # Verificamos columna clave
        col_id = 'ID_Producto' if 'ID_Producto' in df_inv.columns else 'SKU'
        col_nom = 'Nombre' if 'Nombre' in df_inv.columns else 'Descripcion'
        
        if col_id not in df_inv.columns:
            st.error(f"Falta la columna '{col_id}' en Inventario.")
            return [], {}, {}

        # Crear lista para dropdown y diccionario de búsqueda
        df_inv['Display'] = df_inv[col_id].astype(str) + " | " + df_inv[col_nom].astype(str)
        lista_productos = sorted(df_inv['Display'].unique().tolist())
        lista_productos.insert(0, "NUEVO (Crear Producto)")
        
        # Diccionario: ID_Limpio -> Display
        diccionario_productos = pd.Series(df_inv.Display.values, index=df_inv[col_id].apply(normalizar_str)).to_dict()
        
    except Exception as e:
        st.error(f"Error leyendo Inventario: {e}")
        return [], {}, {}

    # --- B. CARGAR MAESTRO PROVEEDORES (MEMORIA) ---
    memoria = {}
    try:
        data_map = _ws_map.get_all_records()
        # Ordenamos por fecha (si existe) para tener la última versión, o simplemente leemos todo
        # La clave será: ID_PROVEEDOR_LIMPIO + "_" + SKU_PROVEEDOR_LIMPIO
        
        for row in data_map:
            id_prov = normalizar_str(row.get('ID_Proveedor', ''))
            sku_prov = normalizar_str(row.get('SKU_Proveedor', ''))
            
            if id_prov and sku_prov:
                key = f"{id_prov}_{sku_prov}"
                memoria[key] = {
                    'SKU_Interno': normalizar_str(row.get('SKU_Interno', '')),
                    'Factor_Pack': float(row.get('Factor_Pack', 1.0)) if row.get('Factor_Pack') else 1.0
                }
    except Exception as e:
        st.warning(f"No se pudo cargar la memoria de proveedores (posible hoja vacía): {e}")

    return lista_productos, diccionario_productos, memoria

# ==========================================
# 5. LECTOR DE XML (FACTURA ELECTRÓNICA)
# ==========================================

def parsear_xml(archivo):
    """Lee el XML y extrae datos clave."""
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        # Namespaces comunes en Facturación Electrónica (UBL)
        ns = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cfdi': 'http://www.sat.gob.mx/cfd/4' # Ejemplo México, ajustable
        }
        
        # Intentamos extraer descripción si es un XML anidado (común en algunos ERPs)
        try:
            desc_b64 = root.find('.//cac:Attachment//cbc:Description', ns)
            if desc_b64 is not None and "Invoice" in desc_b64.text:
                # Aquí iría lógica si el XML está dentro de un CDATA, por simplicidad asumimos estructura UBL estándar o CFDI
                pass
        except: pass

        # Datos Generales
        # Nota: Ajustado para buscar nodos genéricos, funciona con la mayoría de UBL 2.1
        try:
            # Proveedor
            prov_node = root.find('.//cac:AccountingSupplierParty/cac:Party', ns)
            if prov_node:
                prov_name = prov_node.find('.//cbc:RegistrationName', ns).text
                prov_id = prov_node.find('.//cbc:CompanyID', ns).text
            else:
                # Intento fallback para CFDI simple
                prov_node = root.find('.//{http://www.sat.gob.mx/cfd/4}Emisor')
                prov_name = prov_node.attrib.get('Nombre') if prov_node is not None else "Desconocido"
                prov_id = prov_node.attrib.get('Rfc') if prov_node is not None else "GENERICO"

            # Folio y Total
            folio = root.find('.//cbc:ID', ns).text if root.find('.//cbc:ID', ns) is not None else "S/F"
            total_node = root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns)
            total = float(total_node.text) if total_node is not None else 0.0

        except:
            prov_name = "Proveedor Manual"
            prov_id = "MANUAL"
            folio = "000"
            total = 0.0

        items = []
        # Iterar lineas
        lines = root.findall('.//cac:InvoiceLine', ns)
        if not lines:
            # Fallback CFDI Conceptos
            lines = root.findall('.//{http://www.sat.gob.mx/cfd/4}Concepto')
            es_cfdi = True
        else:
            es_cfdi = False

        for line in lines:
            if not es_cfdi:
                # Lógica UBL
                sku_prov = "S/C"
                id_node = line.find('.//cac:Item/cac:SellersItemIdentification/cbc:ID', ns)
                if id_node is None: id_node = line.find('.//cac:Item/cac:StandardItemIdentification/cbc:ID', ns)
                if id_node is not None: sku_prov = id_node.text
                
                desc = line.find('.//cac:Item/cbc:Description', ns).text
                qty = float(line.find('.//cbc:InvoicedQuantity', ns).text)
                
                price_node = line.find('.//cac:Price/cbc:PriceAmount', ns)
                price = float(price_node.text) if price_node is not None else 0.0
            else:
                # Lógica CFDI
                sku_prov = line.attrib.get('NoIdentificacion', 'S/C')
                desc = line.attrib.get('Descripcion', '')
                qty = float(line.attrib.get('Cantidad', 0))
                price = float(line.attrib.get('ValorUnitario', 0))

            items.append({
                'SKU_Proveedor': sku_prov,
                'Descripcion': desc,
                'Cantidad': qty,
                'Costo_Unitario_XML': price
            })

        return {'Proveedor': prov_name, 'ID_Proveedor': prov_id, 'Folio': folio, 'Total': total, 'Items': items}

    except Exception as e:
        st.error(f"Error parseando estructura XML: {e}")
        return None

# ==========================================
# 6. LOGICA DE ACTUALIZACIÓN Y APRENDIZAJE
# ==========================================

def guardar_aprendizaje(ws_map, df_final, id_proveedor_raw, nombre_proveedor):
    """
    Guarda las nuevas relaciones en la hoja Maestro_Proveedores.
    Solo guarda si el usuario seleccionó un producto interno válido (no NUEVO).
    """
    nuevas_relaciones = []
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    for _, row in df_final.iterrows():
        seleccion = row['SKU_Interno_Seleccionado']
        
        # Solo aprendemos si ya existe el producto interno y no es uno nuevo temporal
        if "NUEVO" not in seleccion:
            sku_interno = seleccion.split(" | ")[0].strip()
            
            nuevas_relaciones.append([
                str(id_proveedor_raw),      # ID_Proveedor
                str(nombre_proveedor),      # Nombre_Proveedor
                str(row['SKU_Proveedor']),  # SKU_Proveedor
                sku_interno,                # SKU_Interno
                float(row['Factor_Pack']),  # Factor_Pack
                fecha_hoy                   # Ultima_Actualizacion
            ])
            
    if nuevas_relaciones:
        # Añadimos al final. Podrías implementar lógica para borrar anteriores, 
        # pero añadir al final y leer el último es más seguro para historial.
        ws_map.append_rows(nuevas_relaciones)
        return len(nuevas_relaciones)
    return 0

def ejecutar_actualizacion_inventario(ws_inv, df_final):
    """
    Actualiza Stock y Costos en la hoja Inventario.
    Crea filas si es producto nuevo.
    """
    try:
        data_inv = ws_inv.get_all_values()
        headers = data_inv[0]
        
        # Mapeo de índices de columnas
        try:
            idx_id = headers.index("ID_Producto") # o SKU
            idx_stock = headers.index("Stock")
            idx_costo = headers.index("Costo")
            # Opcionales
            idx_nombre = headers.index("Nombre") if "Nombre" in headers else -1
            idx_prov_ref = headers.index("SKU_Proveedor") if "SKU_Proveedor" in headers else -1
        except ValueError as ve:
            return False, [f"❌ Error: Faltan columnas obligatorias en tu hoja Inventario (ID_Producto, Stock, Costo). Detalle: {ve}"]

        # Mapa de filas para búsqueda rápida: ID -> Indice Fila (empezando en 0 para data_inv, o 1 para gspread A1)
        # Gspread usa 1-based index. Data_inv es lista de listas.
        mapa_filas = {}
        for i, row in enumerate(data_inv):
            if i == 0: continue # saltar header
            val_id = normalizar_str(row[idx_id])
            if val_id: mapa_filas[val_id] = i + 1 # Guardamos el indice 1-based real de la hoja

        updates_batch = []
        filas_nuevas = []
        logs = []

        for _, row in df_final.iterrows():
            seleccion = row['SKU_Interno_Seleccionado']
            cant_recibida = row['Cantidad_Recibida']
            factor = row['Factor_Pack']
            total_unidades = cant_recibida * factor
            costo_unitario_real = row['Costo_Unitario_XML'] / factor if factor > 0 else 0
            
            # --- CASO 1: PRODUCTO NUEVO ---
            if "NUEVO" in seleccion:
                # Usamos el SKU del proveedor como ID temporal
                nuevo_id = str(row['SKU_Proveedor']).strip()
                if not nuevo_id or nuevo_id == "S/C": 
                    nuevo_id = f"N-{int(time.time())}" # ID aleatorio si no hay SKU
                
                nueva_fila = [""] * len(headers)
                nueva_fila[idx_id] = nuevo_id
                if idx_nombre != -1: nueva_fila[idx_nombre] = row['Descripcion']
                nueva_fila[idx_stock] = sanitizar_para_sheet(total_unidades)
                nueva_fila[idx_costo] = sanitizar_para_sheet(costo_unitario_real)
                if idx_prov_ref != -1: nueva_fila[idx_prov_ref] = row['SKU_Proveedor']
                
                filas_nuevas.append(nueva_fila)
                logs.append(f"✨ CREADO: {nuevo_id} | Stock: {total_unidades}")

            # --- CASO 2: PRODUCTO EXISTENTE ---
            else:
                sku_interno = normalizar_str(seleccion.split(" | ")[0])
                
                if sku_interno in mapa_filas:
                    row_num = mapa_filas[sku_interno]
                    
                    # Leer stock actual (lo leemos de la data cargada en memoria para evitar mil lecturas API)
                    stock_actual_raw = data_inv[row_num-1][idx_stock]
                    stock_actual = clean_currency(stock_actual_raw)
                    
                    nuevo_stock = stock_actual + total_unidades
                    
                    # Preparamos updates (Stock y Costo Promedio o Ultimo Costo)
                    # Aquí actualizamos a Ultimo Costo
                    updates_batch.append({
                        'range': gspread.utils.rowcol_to_a1(row_num, idx_stock + 1),
                        'values': [[sanitizar_para_sheet(nuevo_stock)]]
                    })
                    updates_batch.append({
                        'range': gspread.utils.rowcol_to_a1(row_num, idx_costo + 1),
                        'values': [[sanitizar_para_sheet(costo_unitario_real)]]
                    })
                    logs.append(f"🔄 ACTUALIZADO: {sku_interno} | Stock: {stock_actual} -> {nuevo_stock} | Costo: ${costo_unitario_real:.2f}")
                else:
                    logs.append(f"⚠️ ERROR: El ID {sku_interno} estaba en catálogo pero no encontré la fila en la hoja.")

        # Ejecutar cambios en lotes
        if updates_batch: ws_inv.batch_update(updates_batch)
        if filas_nuevas: ws_inv.append_rows(filas_nuevas)
        
        return True, logs

    except Exception as e:
        return False, [f"Error crítico en actualización: {e}"]

# ==========================================
# 7. INTERFAZ PRINCIPAL (MAIN)
# ==========================================

def main():
    st.markdown('<div class="main-header">Recepción Inteligente 🧠</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Procesamiento de Facturas con Aprendizaje Automático</div>', unsafe_allow_html=True)

    # Inicialización de estado
    if 'step' not in st.session_state: st.session_state.step = 1
    
    # Conexión
    sh, ws_inv, ws_map, ws_hist = conectar_sheets()
    
    # --- PASO 1: CARGA DE DATOS ---
    if st.session_state.step == 1:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### 1. Sube tu Factura XML")
            uploaded_file = st.file_uploader("", type=['xml'], help="Arrastra tu factura XML aquí")
        
        with col2:
            st.info("ℹ️ El sistema aprenderá automáticamente de tus correcciones.")
            if st.button("🔄 Recargar Memorias del Sistema"):
                st.cache_data.clear()
                st.rerun()

        if uploaded_file:
            with st.spinner("Analizando factura y consultando cerebro..."):
                # 1. Leer XML
                data_xml = parsear_xml(uploaded_file)
                if not data_xml: st.stop()
                
                # 2. Cargar Datos Sheet
                lista_prods, dict_prods, memoria = cargar_datos_sistema(ws_inv, ws_map)
                
                # Guardar en sesión
                st.session_state.xml_data = data_xml
                st.session_state.lista_prods = lista_prods
                st.session_state.dict_prods = dict_prods
                st.session_state.memoria = memoria
                st.session_state.step = 2
                st.rerun()

    # --- PASO 2: MATCHING Y EDICIÓN ---
    elif st.session_state.step == 2:
        xml = st.session_state.xml_data
        memoria = st.session_state.memoria
        dict_prods = st.session_state.dict_prods
        
        # Header Info
        st.markdown(f"""
        <div class="card">
            <h3 style="margin:0; color:#1e3a8a;">Proveedor: {xml['Proveedor']}</h3>
            <p style="margin:0; color:#64748b;">ID: {xml['ID_Proveedor']} | Folio: {xml['Folio']} | Total: ${xml['Total']:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 2. Asociación de Productos")
        st.write("Verifica las asociaciones. Si el sistema no sabe qué es, selecciona el producto correcto y **aprenderá para la próxima**.")

        # Construir tabla para el editor
        filas_editor = []
        id_prov_clean = normalizar_str(xml['ID_Proveedor'])
        matches_automaticos = 0
        
        for item in xml['Items']:
            sku_prov_clean = normalizar_str(item['SKU_Proveedor'])
            key = f"{id_prov_clean}_{sku_prov_clean}"
            
            # VALORES POR DEFECTO
            seleccion_defecto = "NUEVO (Crear Producto)"
            factor_defecto = 1.0
            
            # BUSCAR EN MEMORIA (CEREBRO)
            if key in memoria:
                sku_aprendido = memoria[key]['SKU_Interno']
                factor_aprendido = memoria[key]['Factor_Pack']
                
                # Verificar si el SKU aprendido aun existe en el catálogo actual
                if sku_aprendido in dict_prods:
                    seleccion_defecto = dict_prods[sku_aprendido]
                    factor_defecto = factor_aprendido
                    matches_automaticos += 1
            
            filas_editor.append({
                "SKU_Proveedor": item['SKU_Proveedor'],
                "Descripcion": item['Descripcion'],
                "SKU_Interno_Seleccionado": seleccion_defecto,
                "Factor_Pack": factor_defecto,
                "Cantidad_XML": item['Cantidad'],
                "Cantidad_Recibida": item['Cantidad'], # Por defecto igual
                "Costo_Unitario_XML": item['Costo_Unitario_XML']
            })
        
        if matches_automaticos > 0:
            st.markdown(f'<div class="success-box">✅ ¡He recordado automáticamente {matches_automaticos} productos de este proveedor!</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warning-box">🧠 Este proveedor o productos parecen nuevos. Relaciónalos y aprenderé.</div>', unsafe_allow_html=True)

        df_editor = pd.DataFrame(filas_editor)
        
        # EDITOR INTERACTIVO
        edited_df = st.data_editor(
            df_editor,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True, width="small"),
                "Descripcion": st.column_config.TextColumn("Descripción Factura", disabled=True),
                "SKU_Interno_Seleccionado": st.column_config.SelectboxColumn(
                    "📌 TUS PRODUCTOS (Match)",
                    options=st.session_state.lista_prods,
                    required=True,
                    width="large",
                    help="Selecciona el producto interno equivalente"
                ),
                "Factor_Pack": st.column_config.NumberColumn("📦 Pzs/Caja", min_value=0.01, format="%.2f", help="¿Cuántas unidades trae la caja?"),
                "Cantidad_XML": st.column_config.NumberColumn("Cant. Fac", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ Recibido Real", min_value=0),
                "Costo_Unitario_XML": st.column_config.NumberColumn("Costo Fac", format="$%.2f", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            height=500
        )
        
        col_btn1, col_btn2 = st.columns([1, 4])
        if col_btn1.button("⬅️ Cancelar"):
            st.session_state.step = 1
            st.rerun()
            
        if col_btn2.button("PROCESAR RECEPCIÓN 🚀", type="primary", use_container_width=True):
            st.session_state.final_df = edited_df
            st.session_state.step = 3
            st.rerun()

    # --- PASO 3: EJECUCIÓN Y RESULTADOS ---
    elif st.session_state.step == 3:
        st.markdown("### 3. Procesando Datos...")
        
        xml = st.session_state.xml_data
        df_final = st.session_state.final_df
        
        progreso = st.progress(0)
        status_text = st.empty()
        
        # 1. APRENDER RELACIONES
        status_text.text("🧠 Guardando nuevas relaciones en Maestro_Proveedores...")
        n_aprendidos = guardar_aprendizaje(ws_map, df_final, xml['ID_Proveedor'], xml['Proveedor'])
        progreso.progress(30)
        
        # 2. ACTUALIZAR INVENTARIO
        status_text.text("📦 Actualizando Stocks y Costos en Inventario...")
        exito, logs = ejecutar_actualizacion_inventario(ws_inv, df_final)
        progreso.progress(80)
        
        # 3. HISTORIAL
        status_text.text("📝 Registrando historial...")
        ws_hist.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(xml['Folio']),
            str(xml['Proveedor']),
            len(df_final),
            xml['Total'],
            "Admin",
            "OK" if exito else "Error"
        ])
        progreso.progress(100)
        
        st.divider()
        if exito:
            st.balloons()
            st.success("¡Recepción Exitosa!")
            
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric("Nuevas Relaciones Aprendidas", n_aprendidos)
            with col_res2:
                st.metric("Productos Procesados", len(df_final))
                
            with st.expander("Ver Detalles de Movimientos"):
                for l in logs: st.write(l)
                
            if st.button("Cargar Nueva Factura"):
                st.session_state.step = 1
                st.session_state.xml_data = None
                st.rerun()
        else:
            st.error("Hubo errores durante el proceso.")
            for l in logs: st.error(l)
            if st.button("Volver a intentar"):
                st.session_state.step = 2
                st.rerun()

if __name__ == "__main__":
    main()
