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
    page_title="Recepción Inteligente v5.0 (Auto-Aprendizaje)", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS
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
# 2. FUNCIONES DE LIMPIEZA (CRÍTICO PARA EL MATCHING)
# ==========================================

def normalizar_str(valor):
    """
    Convierte cualquier dato (int, float, str) a un string limpio.
    Esto soluciona que '123' (num) no coincida con '123 ' (str).
    """
    if pd.isna(valor) or valor == "":
        return ""
    # Convertir a string, quitar espacios inicio/fin y pasar a mayúsculas
    return str(valor).strip().upper()

def clean_currency(val):
    """Convierte dinero ($1.200,00) a float."""
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').strip()
        if ',' in val and '.' in val:
            val = val.replace(',', '') 
        elif ',' in val:
            val = val.replace(',', '.') 
        try:
            return float(val)
        except:
            return 0.0
    return 0.0

def sanitizar_para_sheet(val):
    """Prepara datos numéricos para Google Sheets."""
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    return val

# ==========================================
# 3. CONEXIÓN A SHEETS
# ==========================================

@st.cache_resource
def conectar_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración en secrets.toml")
            st.stop()
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        try: ws_inv = sh.worksheet("Inventario")
        except: st.error("❌ No existe hoja 'Inventario'"); st.stop()
        
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
# 4. MEMORIA Y CATALOGO (EL CEREBRO)
# ==========================================

@st.cache_data(ttl=60)
def obtener_catalogo_y_diccionario(_ws_inv):
    """
    Devuelve dos cosas:
    1. Lista para el Dropdown ["101 | Coca Cola", ...]
    2. Diccionario para búsqueda rápida {"101": "101 | Coca Cola"}
    """
    try:
        data = _ws_inv.get_all_records()
        df = pd.DataFrame(data)
        
        cols_necesarias = ['ID_Producto', 'Nombre']
        if not all(col in df.columns for col in cols_necesarias):
            st.error(f"Faltan columnas ID_Producto o Nombre en Inventario.")
            return [], {}

        # Crear columna combinada
        df['ID_Limpio'] = df['ID_Producto'].apply(normalizar_str)
        df['Buscador'] = df['ID_Producto'].astype(str) + " | " + df['Nombre'].astype(str)
        
        lista_opciones = sorted(df['Buscador'].unique().tolist())
        lista_opciones.insert(0, "NUEVO (Crear Producto)")
        
        # Diccionario para mapeo inverso rápido: ID -> "ID | Nombre"
        diccionario = pd.Series(df.Buscador.values, index=df.ID_Limpio).to_dict()
        
        return lista_opciones, diccionario
    except Exception as e:
        st.error(f"Error leyendo inventario: {e}")
        return [], {}

def cargar_memoria_aprendizaje(ws_map):
    """
    Carga la memoria histórica.
    CLAVE: Normaliza ID Proveedor y SKU para que coincidan siempre.
    """
    try:
        data = ws_map.get_all_records()
        memoria = {}
        for row in data:
            # Clave robusta: ID_PROV_LIMPIO + "_" + SKU_PROV_LIMPIO
            id_prov = normalizar_str(row['ID_Proveedor'])
            sku_prov = normalizar_str(row['SKU_Proveedor'])
            key = f"{id_prov}_{sku_prov}"
            
            memoria[key] = {
                'ID_Interno': normalizar_str(row['ID_Producto_Interno']),
                'Factor': float(row['Factor_Pack']) if row['Factor_Pack'] else 1.0
            }
        return memoria
    except:
        return {}

# ==========================================
# 5. LECTOR XML
# ==========================================

def leer_xml(archivo):
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        ns = {'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
              'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'}
        
        # Buscar Invoice anidado
        desc = root.find('.//cac:Attachment//cbc:Description', ns)
        if desc is not None and "Invoice" in desc.text:
            root = ET.fromstring(desc.text)

        # Cabecera
        try:
            prov_node = root.find('.//cac:AccountingSupplierParty/cac:Party', ns)
            prov_name = prov_node.find('.//cbc:RegistrationName', ns).text
            prov_id = prov_node.find('.//cbc:CompanyID', ns).text
        except:
            prov_name = "Proveedor Desconocido"
            prov_id = "GENERICO"

        folio = root.find('.//cbc:ID', ns).text if root.find('.//cbc:ID', ns) is not None else "S/F"
        total_node = root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns)
        total = float(total_node.text) if total_node is not None else 0.0

        items = []
        for line in root.findall('.//cac:InvoiceLine', ns):
            sku_prov = "S/C"
            # Buscar SKU en varios nodos posibles
            id_node = line.find('.//cac:Item/cac:StandardItemIdentification/cbc:ID', ns)
            if id_node is None: id_node = line.find('.//cac:Item/cac:SellersItemIdentification/cbc:ID', ns)
            if id_node is not None: sku_prov = id_node.text

            desc_txt = line.find('.//cac:Item/cbc:Description', ns).text
            qty = float(line.find('.//cbc:InvoicedQuantity', ns).text)
            price_node = line.find('.//cac:Price/cbc:PriceAmount', ns)
            price = float(price_node.text) if price_node is not None else 0.0

            items.append({
                'SKU_Proveedor': sku_prov,
                'Descripcion': desc_txt,
                'Cantidad': qty,
                'Costo_Unitario_XML': price
            })

        return {'Proveedor': prov_name, 'ID_Proveedor': prov_id, 'Folio': folio, 'Total': total, 'Items': items}
    except Exception as e:
        st.error(f"Error parseando XML: {e}")
        return None

# ==========================================
# 6. LOGICA DE ACTUALIZACION
# ==========================================

def guardar_maestro(ws_map, datos):
    """Guarda nuevas relaciones aprendidas."""
    try:
        new_rows = []
        fecha = datetime.now().strftime("%Y-%m-%d")
        
        # Obtenemos lo que ya existe para no duplicar filas innecesariamente (opcional, pero buena práctica)
        # Por simplicidad aquí, agregamos al final. En producción podrías limpiar duplicados.
        
        for row in datos:
            sel = row['ID_Interno_Seleccionado']
            if "NUEVO" not in sel:
                id_interno = sel.split(" | ")[0].strip()
                new_rows.append([
                    str(row['ID_Proveedor']),
                    str(row['Proveedor_Nombre']),
                    str(row['SKU_Proveedor']), # El SKU original
                    id_interno,               # El ID Interno al que se asoció
                    row['Factor_Pack'],
                    fecha
                ])
        if new_rows: ws_map.append_rows(new_rows)
    except Exception as e:
        print(f"Error guardando maestro: {e}")

def actualizar_inventario(ws_inv, df_final):
    try:
        data_inv = ws_inv.get_all_values()
        headers = data_inv[0]
        
        try:
            idx_id = headers.index("ID_Producto")
            idx_stock = headers.index("Stock")
            idx_costo = headers.index("Costo")
            idx_precio = headers.index("Precio")
            idx_nombre = headers.index("Nombre") if "Nombre" in headers else -1
            idx_sku_prov = headers.index("SKU_Proveedor") if "SKU_Proveedor" in headers else -1
        except ValueError as ve:
            return False, [f"❌ Faltan columnas clave en Inventario: {ve}"]

        # Mapa de filas: ID Normalizado -> Número de Fila
        mapa_filas = {}
        for i, row in enumerate(data_inv[1:], start=2):
            val_id = normalizar_str(row[idx_id])
            if val_id: mapa_filas[val_id] = i

        updates = []
        nuevas_filas = []
        logs = []

        for _, row in df_final.iterrows():
            seleccion = str(row['ID_Interno_Seleccionado'])
            
            # === CREACIÓN DE NUEVO PRODUCTO ===
            if "NUEVO" in seleccion:
                # Usamos el SKU del proveedor como ID temporal si es nuevo
                id_nuevo = str(row['SKU_Proveedor']).strip()
                desc_nueva = row['Descripcion']
                cant_real = row['Cantidad_Recibida'] * row['Factor_Pack']
                costo_nuevo = row['Costo_Unitario_XML'] / row['Factor_Pack']
                precio_nuevo = costo_nuevo / 0.70 # Margen 30%

                new_row = [""] * len(headers)
                new_row[idx_id] = id_nuevo
                if idx_nombre != -1: new_row[idx_nombre] = desc_nueva
                new_row[idx_stock] = sanitizar_para_sheet(cant_real)
                new_row[idx_costo] = sanitizar_para_sheet(costo_nuevo)
                new_row[idx_precio] = sanitizar_para_sheet(precio_nuevo)
                if idx_sku_prov != -1: new_row[idx_sku_prov] = row['SKU_Proveedor']
                
                nuevas_filas.append(new_row)
                logs.append(f"✨ CREADO: {id_nuevo} ({desc_nueva}) | Stock +{cant_real}")
            
            # === ACTUALIZACIÓN EXISTENTE ===
            else:
                id_interno_raw = seleccion.split(" | ")[0]
                id_interno = normalizar_str(id_interno_raw)
                
                if id_interno in mapa_filas:
                    fila_num = mapa_filas[id_interno]
                    cant_entrante = row['Cantidad_Recibida'] * row['Factor_Pack']
                    costo_unit = row['Costo_Unitario_XML'] / row['Factor_Pack']
                    
                    # Leer stock actual
                    val_stock = data_inv[fila_num-1][idx_stock]
                    stock_actual = clean_currency(val_stock)
                    stock_final = stock_actual + cant_entrante

                    # Updates
                    updates.append({
                        'range': gspread.utils.rowcol_to_a1(fila_num, idx_stock + 1),
                        'values': [[sanitizar_para_sheet(stock_final)]]
                    })
                    updates.append({
                        'range': gspread.utils.rowcol_to_a1(fila_num, idx_costo + 1),
                        'values': [[sanitizar_para_sheet(costo_unit)]]
                    })
                    # Opcional: Actualizar precio
                    # updates.append({
                    #     'range': gspread.utils.rowcol_to_a1(fila_num, idx_precio + 1),
                    #     'values': [[sanitizar_para_sheet(costo_unit / 0.7)]]
                    # })

                    logs.append(f"🔄 {id_interno_raw}: Stock {stock_actual} -> {stock_final}")
                else:
                    logs.append(f"⚠️ Error: ID {id_interno} no encontrado en filas.")

        if updates: ws_inv.batch_update(updates)
        if nuevas_filas: ws_inv.append_rows(nuevas_filas)
        
        return True, logs

    except Exception as e:
        return False, [f"Error crítico: {e}"]

# ==========================================
# 7. INTERFAZ PRINCIPAL
# ==========================================

def main():
    st.markdown('<div class="main-header">Recepción Inteligente 5.0</div>', unsafe_allow_html=True)
    
    if 'step' not in st.session_state: st.session_state.step = 1
    if 'xml_data' not in st.session_state: st.session_state.xml_data = None
    
    sh, ws_inv, ws_map, ws_hist = conectar_sheets()

    # PASO 1: SUBIR XML
    if st.session_state.step == 1:
        st.markdown('<div class="sub-header">Paso 1: Sube tu Factura XML</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Arrastra tu XML aquí", type=['xml'])
        
        if st.button("🔄 Refrescar Memoria del Sistema"):
            st.cache_data.clear()
            st.success("Memoria refrescada.")

        if uploaded_file:
            with st.spinner("Analizando factura y memoria..."):
                # Leer XML
                data_xml = leer_xml(uploaded_file)
                if not data_xml: st.stop()
                
                # Cargar Catalogo y Diccionario
                lista_cat, dict_cat = obtener_catalogo_y_diccionario(ws_inv)
                
                # Cargar Memoria de Aprendizaje
                memoria = cargar_memoria_aprendizaje(ws_map)
                
                st.session_state.xml_data = data_xml
                st.session_state.lista_catalogo = lista_cat
                st.session_state.dict_catalogo = dict_cat # Para búsqueda rápida
                st.session_state.memoria = memoria
                st.session_state.step = 2
                st.rerun()

    # PASO 2: MATCHING (AQUI OCURRE LA MAGIA)
    elif st.session_state.step == 2:
        data = st.session_state.xml_data
        mem = st.session_state.memoria
        dict_cat = st.session_state.dict_catalogo
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-box'><div class='metric-lbl'>Proveedor</div><div class='metric-val'>{data['Proveedor'][:15]}..</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-box'><div class='metric-lbl'>Items</div><div class='metric-val'>{len(data['Items'])}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-box'><div class='metric-lbl'>Total</div><div class='metric-val'>${data['Total']:,.2f}</div></div>", unsafe_allow_html=True)
        
        st.write("---")
        st.subheader("🤖 Asociación Automática de Productos")
        
        rows = []
        # Preparamos el ID Proveedor limpio para la clave
        prov_id_clean = normalizar_str(data['ID_Proveedor'])

        contador_autos = 0

        for item in data['Items']:
            sku_clean = normalizar_str(item['SKU_Proveedor'])
            
            # GENERAMOS LA LLAVE DE BÚSQUEDA EN MEMORIA
            key = f"{prov_id_clean}_{sku_clean}"
            
            # Valores por defecto
            pred_seleccion = "NUEVO (Crear Producto)"
            pred_factor = 1.0
            
            # --- LÓGICA DE CEREBRO ---
            if key in mem:
                # ¡ENCONTRÓ UNA RELACIÓN PREVIA!
                id_interno_aprendido = mem[key]['ID_Interno'] # Ej: "105"
                
                # Buscamos la cadena completa en el diccionario: "105" -> "105 | Coca Cola"
                if id_interno_aprendido in dict_cat:
                    pred_seleccion = dict_cat[id_interno_aprendido]
                    pred_factor = mem[key]['Factor']
                    contador_autos += 1
            # -------------------------

            rows.append({
                "SKU_Proveedor": item['SKU_Proveedor'],
                "Descripcion": item['Descripcion'],
                "ID_Interno_Seleccionado": pred_seleccion, # Aquí va lo que aprendió
                "Factor_Pack": pred_factor,
                "Cantidad_XML": item['Cantidad'],
                "Costo_Unitario_XML": item['Costo_Unitario_XML'],
                "ID_Proveedor": data['ID_Proveedor'],
                "Proveedor_Nombre": data['Proveedor']
            })

        if contador_autos > 0:
            st.success(f"🧠 ¡He recordado y asociado automáticamente {contador_autos} productos!")
        else:
            st.info("ℹ️ No reconozco estos productos aún. Relaciónalos manualmente y aprenderé para la próxima.")

        df = pd.DataFrame(rows)

        edited_df = st.data_editor(
            df,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True, width="small"),
                "Descripcion": st.column_config.TextColumn("Descripción Factura", disabled=True, width="medium"),
                "ID_Interno_Seleccionado": st.column_config.SelectboxColumn(
                    "📌 TU PRODUCTO (Match)",
                    options=st.session_state.lista_catalogo,
                    required=True,
                    width="large"
                ),
                "Factor_Pack": st.column_config.NumberColumn("📦 Unid/Caja", min_value=1),
                "Cantidad_XML": st.column_config.NumberColumn("Cant.", disabled=True),
                "Costo_Unitario_XML": st.column_config.NumberColumn("Costo Fac", format="$%.2f", disabled=True),
                "ID_Proveedor": None, "Proveedor_Nombre": None
            },
            hide_index=True,
            use_container_width=True,
            height=500
        )

        c_back, c_next = st.columns([1, 5])
        if c_back.button("⬅️ Cancelar"):
            st.session_state.step = 1
            st.rerun()
        if c_next.button("Verificar Recepción ➡️", type="primary"):
            st.session_state.mapped_df = edited_df
            st.session_state.step = 3
            st.rerun()

    # PASO 3: CONFIRMACIÓN
    elif st.session_state.step == 3:
        st.markdown('<div class="sub-header">Paso 3: Verificación Física</div>', unsafe_allow_html=True)
        df_final = st.session_state.mapped_df.copy()
        
        if 'Cantidad_Recibida' not in df_final.columns:
            df_final['Cantidad_Recibida'] = df_final['Cantidad_XML']
        
        df_final['Total_Unidades'] = df_final['Cantidad_Recibida'] * df_final['Factor_Pack']

        verified_df = st.data_editor(
            df_final,
            column_config={
                "ID_Interno_Seleccionado": st.column_config.TextColumn("Producto", disabled=True),
                "Descripcion": st.column_config.TextColumn("Ref Factura", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ RECIBIDO REAL", min_value=0),
                "Total_Unidades": st.column_config.NumberColumn("Total Unids", disabled=True),
                "Factor_Pack": st.column_config.NumberColumn("Factor", disabled=True),
                "Cantidad_XML": None, "SKU_Proveedor": None, "Costo_Unitario_XML": None, "ID_Proveedor": None
            },
            hide_index=True,
            use_container_width=True
        )

        st.divider()
        if st.button("🚀 FINALIZAR Y ACTUALIZAR", type="primary", use_container_width=True):
            with st.status("Procesando...", expanded=True) as status:
                
                # 1. APRENDER (Guardar en Maestro_Proveedores)
                st.write("🧠 Aprendiendo nuevas relaciones...")
                guardar_maestro(ws_map, verified_df.to_dict('records'))
                
                # 2. ACTUALIZAR STOCK
                st.write("📦 Actualizando inventario...")
                exito, logs = actualizar_inventario(ws_inv, verified_df)
                
                # 3. HISTORIAL
                ws_hist.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    st.session_state.xml_data['Folio'],
                    st.session_state.xml_data['Proveedor'],
                    len(verified_df),
                    st.session_state.xml_data['Total'],
                    "App v5.0"
                ])
                
                if exito:
                    status.update(label="¡Proceso Completado!", state="complete", expanded=False)
                    st.balloons()
                    st.success("Inventario Actualizado y Relaciones Guardadas.")
                    with st.expander("Ver Log de Cambios"):
                        for l in logs: st.write(l)
                    time.sleep(4)
                    st.session_state.step = 1
                    st.session_state.xml_data = None
                    st.rerun()
                else:
                    status.update(label="Error", state="error")
                    for l in logs: st.error(l)

if __name__ == "__main__":
    main()
