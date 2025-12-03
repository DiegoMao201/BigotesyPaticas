import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time

# --- 1. CONFIGURACIÓN Y ESTILOS ---

COLOR_PRIMARIO = "#2ecc71"
COLOR_SECUNDARIO = "#e67e22"
COLOR_FONDO = "#f4f6f9"

st.set_page_config(page_title="Recepción Compras XML - Bigotes y Patitas", page_icon="📦", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_FONDO}; }}
    .big-title {{ font-family: 'Helvetica Neue', sans-serif; font-size: 2em; color: #2c3e50; font-weight: 800; }}
    .stButton button[type="primary"] {{
        background: linear-gradient(45deg, {COLOR_PRIMARIO}, #27ae60);
        border: none; color: white; font-weight: bold; border-radius: 12px;
    }}
    .metric-card {{
        background-color: white; padding: 15px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN Y UTILIDADES ---

@st.cache_resource(ttl=600)
def conectar_sheets():
    """Conecta a Google Sheets usando st.secrets"""
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account).")
            return None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        
        if "SHEET_URL" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (SHEET_URL).")
            return None
            
        hoja = gc.open_by_url(st.secrets["SHEET_URL"])
        return hoja.worksheet("Inventario")
    except Exception as e:
        st.error(f"Error conexión a Google Sheets: {e}")
        return None

def sanitizar_dato(dato):
    """Evita error JSON con tipos numpy al enviar a GSheets"""
    if isinstance(dato, (np.int64, np.int32)): return int(dato)
    if isinstance(dato, (np.float64, np.float32)): return float(dato)
    return dato

# --- 3. MOTOR DE PARSING XML (FACTURA ELECTRÓNICA DIAN) ---



def parsear_xml_factura(archivo):
    """
    Analiza el XML (AttachedDocument o Invoice), extrae items, cantidades y costos.
    """
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        # Namespaces comunes en facturación UBL 2.1 / DIAN
        ns_map = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ad': 'urn:dian:gov:co:facturaelectronica:AttachedDocument'
        }

        # 1. Determinar si es AttachedDocument (XML dentro de XML) o Invoice directo
        # Intentamos buscar la descripción dentro de AttachedDocument
        desc_tag = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
        
        if desc_tag is not None and desc_tag.text:
            # Parsear el XML interno (CDATA) que es la factura real
            root_invoice = ET.fromstring(desc_tag.text.strip())
        else:
            # Asumir que el archivo subido es directamente el Invoice
            root_invoice = root

        # Actualizar namespaces para el Invoice interno (a veces varían ligeramente, pero usaremos los estándar)
        ns_inv = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }

        # 2. Extraer Cabecera
        prov_tag = root_invoice.find('.//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:RegistrationName', ns_inv)
        proveedor = prov_tag.text if prov_tag is not None else "Proveedor Desconocido"
        
        folio_tag = root_invoice.find('.//cbc:ID', ns_inv)
        folio = folio_tag.text if folio_tag is not None else "---"

        # 3. Extraer Líneas (Items)
        items = []
        for line in root_invoice.findall('.//cac:InvoiceLine', ns_inv):
            try:
                # Descripción
                desc = line.find('.//cac:Item/cbc:Description', ns_inv).text
                
                # Cantidad
                qty = float(line.find('.//cbc:InvoicedQuantity', ns_inv).text)
                
                # Costo Unitario (PrecioAmount dentro de Price suele ser el valor sin impuestos unitario)
                price_tag = line.find('.//cac:Price/cbc:PriceAmount', ns_inv)
                costo_unit = float(price_tag.text) if price_tag is not None else 0.0
                
                # SKU del proveedor
                sku_tag = line.find('.//cac:Item/cac:StandardItemIdentification/cbc:ID', ns_inv)
                if sku_tag is None:
                    sku_tag = line.find('.//cac:Item/cac:SellersItemIdentification/cbc:ID', ns_inv)
                
                sku = sku_tag.text if sku_tag is not None else "GENERICO"

                items.append({
                    "SKU_Proveedor": sku,
                    "Descripcion": desc,
                    "Cantidad_Facturada": qty,
                    "Costo_Unitario": costo_unit,
                    "Total_Linea": qty * costo_unit
                })
            except Exception:
                continue # Saltar línea si falla algo específico

        return {"Proveedor": proveedor, "Folio": folio, "Items": items}

    except Exception as e:
        st.error(f"Error procesando XML: {str(e)}")
        return None

# --- 4. LÓGICA DE ACTUALIZACIÓN EN SHEETS ---

def procesar_actualizacion(ws, df_final):
    """
    Actualiza Stock y Costo si existe el SKU/ID, o crea producto nuevo.
    Usa batch update para eficiencia.
    """
    # 1. Obtener todos los datos de la hoja para mapear filas
    try:
        data = ws.get_all_values()
    except Exception as e:
        return False, [f"Error leyendo hoja: {e}"]

    if not data:
        return False, ["La hoja de inventario está vacía."]

    headers = data[0]
    
    # Mapeo de columnas (Asegúrate que estos nombres sean EXACTOS en tu Google Sheet)
    try:
        col_stock_idx = headers.index('Stock')
        col_costo_idx = headers.index('Costo')
        col_sku_idx = headers.index('SKU_Proveedor')
    except ValueError as e:
        return False, [f"Falta columna requerida en GSheets: {e}. Verifica 'Stock', 'Costo', 'SKU_Proveedor'."]

    # Crear mapa de SKU -> Número de Fila (0-based en la lista 'data', 1-based para GSpread)
    # data[0] es header, data[1] es fila 2 de excel.
    sku_map = {}
    for i, row in enumerate(data):
        if i == 0: continue # Saltar header
        # row[col_sku_idx] es el valor del SKU en esa fila
        val_sku = str(row[col_sku_idx]).strip()
        if val_sku:
            sku_map[val_sku] = i + 1 # Guardamos el índice 1-based (fila Excel)

    updates = [] # Lista de actualizaciones por celdas
    new_rows = [] # Lista de filas nuevas
    log = []

    # Iterar sobre lo que recibimos en la app
    for index, row in df_final.iterrows():
        sku = str(row['SKU_Proveedor']).strip()
        cant_recibida = row['Cantidad_Recibida']
        costo_nuevo = row['Costo_Unitario']
        nombre = row['Descripcion']
        
        if cant_recibida <= 0: 
            continue # No hacemos nada si se recibió 0
        
        if sku in sku_map:
            # --- ACTUALIZAR EXISTENTE ---
            fila_excel = sku_map[sku]
            
            # Obtener stock actual de los datos que ya leímos (memoria)
            # data[fila_excel - 1] porque data es 0-based
            try:
                stock_actual_str = data[fila_excel - 1][col_stock_idx]
                stock_actual = float(stock_actual_str) if stock_actual_str else 0.0
            except:
                stock_actual = 0.0
                
            nuevo_stock = stock_actual + cant_recibida
            
            # Preparar update: (fila, columna, valor)
            # GSpread usa (row, col) 1-based.
            updates.append({
                'range': f"{gspread.utils.rowcol_to_a1(fila_excel, col_stock_idx + 1)}",
                'values': [[sanitizar_dato(nuevo_stock)]]
            })
            updates.append({
                'range': f"{gspread.utils.rowcol_to_a1(fila_excel, col_costo_idx + 1)}",
                'values': [[sanitizar_dato(costo_nuevo)]]
            })
            
            log.append(f"🔄 Actualizado: {nombre} (Stock: {stock_actual} -> {nuevo_stock})")
            
        else:
            # --- CREAR NUEVO ---
            # Asumimos estructura: ID_Producto, Nombre, Precio, Stock, Costo, SKU_Proveedor
            # Ajusta este orden según tus columnas reales
            nuevo_item_row = [""] * len(headers) # Fila vacía del tamaño correcto
            
            # Rellenar datos conocidos
            try:
                # Si tienes columna ID_Producto, úsala. Si no, usa SKU.
                if 'ID_Producto' in headers:
                    nuevo_item_row[headers.index('ID_Producto')] = sku
                
                nuevo_item_row[headers.index('Nombre')] = nombre
                nuevo_item_row[headers.index('Stock')] = sanitizar_dato(cant_recibida)
                nuevo_item_row[headers.index('Costo')] = sanitizar_dato(costo_nuevo)
                nuevo_item_row[headers.index('SKU_Proveedor')] = sku
                
                # Precio venta en 0 por defecto
                if 'Precio' in headers:
                    nuevo_item_row[headers.index('Precio')] = 0
                    
            except Exception as e:
                log.append(f"⚠️ Error preparando nuevo item {nombre}: {e}")
                continue

            new_rows.append(nuevo_item_row)
            log.append(f"✨ Nuevo creado: {nombre}")

    # EJECUTAR CAMBIOS EN LOTES (BATCH)
    try:
        if updates:
            ws.batch_update(updates)
        
        if new_rows:
            ws.append_rows(new_rows)
            
        return True, log
    except Exception as e:
        return False, [f"Error escribiendo en Sheets: {e}"]

# --- 5. INTERFAZ DE USUARIO (MAIN) ---

def main():
    st.markdown('<p class="big-title">📦 Recepción de Compras (XML)</p>', unsafe_allow_html=True)
    st.markdown("---")

    ws_inv = conectar_sheets()
    
    if not ws_inv:
        st.stop() # Detener si no hay conexión

    # --- ESTADO DE LA APLICACIÓN ---
    if 'xml_data' not in st.session_state: st.session_state.xml_data = None
    if 'paso' not in st.session_state: st.session_state.paso = 1

    # [PASO 1] CARGA DE ARCHIVO
    if st.session_state.paso == 1:
        col_up, col_info = st.columns([2, 1])
        
        with col_up:
            uploaded_file = st.file_uploader("Arrastra tu Factura Electrónica (XML)", type=['xml'])
            
            if uploaded_file is not None:
                with st.spinner("Analizando estructura XML..."):
                    datos = parsear_xml_factura(uploaded_file)
                    
                    if datos and len(datos['Items']) > 0:
                        st.session_state.xml_data = datos
                        st.session_state.paso = 2
                        st.rerun()
                    else:
                        st.error("No se pudieron extraer items del XML o el formato no es válido.")

        with col_info:
            st.info("""
            **Instrucciones:**
            1. Sube el archivo `.xml` (AttachedDocument) de tu proveedor.
            2. El sistema extraerá automáticamente costos y cantidades.
            3. Verifica y ajusta el "Conteo Físico".
            4. Guarda para actualizar el inventario.
            """)

    # [PASO 2] CONCILIACIÓN Y VERIFICACIÓN
    elif st.session_state.paso == 2 and st.session_state.xml_data:
        data = st.session_state.xml_data
        
        # Header de la factura
        c1, c2, c3 = st.columns(3)
        c1.metric("Proveedor", data['Proveedor'])
        c2.metric("Folio Factura", data['Folio'])
        c3.metric("Items Detectados", len(data['Items']))
        
        st.markdown("### 🕵️ Verificación de Inventario")
        st.caption("Por favor, confirma que la cantidad física recibida coincide con la factura.")
        
        # Convertir a DataFrame para edición
        if 'df_editor' not in st.session_state:
            df = pd.DataFrame(data['Items'])
            df['Cantidad_Recibida'] = df['Cantidad_Facturada'] # Por defecto igual
            st.session_state.df_editor = df

        # EDITOR DE DATOS
        edited_df = st.data_editor(
            st.session_state.df_editor,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("SKU / Código", disabled=True),
                "Descripcion": st.column_config.TextColumn("Producto", disabled=True, width="large"),
                "Costo_Unitario": st.column_config.NumberColumn("Costo Unit.", format="$%.2f", disabled=True),
                "Cantidad_Facturada": st.column_config.NumberColumn("Facturado", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ Conteo Físico", min_value=0, required=True),
                "Total_Linea": st.column_config.NumberColumn("Total Línea", disabled=True, format="$%.2f")
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )
        
        # Calcular diferencias
        diff = edited_df['Cantidad_Recibida'].sum() - edited_df['Cantidad_Facturada'].sum()
        if diff != 0:
            st.warning(f"⚠️ Hay una diferencia de {diff} unidades entre lo facturado y lo contado.")
        
        st.markdown("---")
        c_back, c_space, c_save = st.columns([1, 3, 2])
        
        if c_back.button("⬅️ Cancelar y Volver"):
            st.session_state.xml_data = None
            st.session_state.paso = 1
            if 'df_editor' in st.session_state: del st.session_state.df_editor
            st.rerun()
            
        if c_save.button("💾 Guardar y Actualizar Inventario", type="primary"):
            with st.spinner("Actualizando Google Sheets..."):
                exito, logs = procesar_actualizacion(ws_inv, edited_df)
                
                if exito:
                    st.balloons()
                    st.success("¡Inventario actualizado correctamente!")
                    with st.expander("Ver detalles de cambios"):
                        for l in logs:
                            st.write(l)
                    
                    # Resetear estado después de 5 segundos o manual
                    time.sleep(3)
                    st.session_state.xml_data = None
                    st.session_state.paso = 1
                    del st.session_state.df_editor
                    st.rerun()
                else:
                    st.error("Error al guardar:")
                    for l in logs:
                        st.error(l)

if __name__ == "__main__":
    main()
