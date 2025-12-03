import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import io
import time
import gspread # Dependencia de Bigotes y Patitas

# --- Funciones de Conexión a Google Sheets (COPIAR del script principal) ---

@st.cache_resource(ttl=3600)
def conectar_google_sheets():
    # Esta función debe ser idéntica a la que tienes en el script principal
    try:
        # Usar las credenciales de Streamlit Secrets
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        SHEET_URL = st.secrets["SHEET_URL"] 
        hoja = gc.open_by_url(SHEET_URL)
        return hoja.worksheet("Inventario"), hoja.worksheet("Clientes"), hoja.worksheet("Ventas"), hoja.worksheet("Gastos")
    except Exception as e:
        st.error(f"🚨 Error crítico al conectar con Google Sheets: {e}")
        return None, None, None, None

def leer_datos(ws, index_col=None):
    # Esta función debe ser idéntica a la que tienes en el script principal
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if index_col and not df.empty:
            df = df.set_index(index_col, drop=False) # Mantener ID_Producto como columna
        return df
    except:
        # Retorna DF vacío con las columnas esperadas en caso de error de lectura
        if ws and ws.title == "Inventario":
            return pd.DataFrame(columns=['ID_Producto', 'Nombre', 'Precio', 'Stock', 'Costo', 'SKU_Proveedor']).set_index('ID_Producto', drop=False)
        return pd.DataFrame()


# --- MOTOR DE PARSING XML (COPIAR de NEXUS) ---

def clean_tag(tag):
    """Elimina los namespaces {urn...} de los tags XML."""
    return tag.split('}', 1)[1] if '}' in tag else tag

def parse_dian_xml_engine(uploaded_file):
    """
    Lee el XML (AttachedDocument), extrae la factura interna (CDATA) y parsea los ítems,
    incluyendo la extracción de Totales de Impuestos. (Versión NEXUS)
    """
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()
        
        # 1. Extracción de Metadatos (Proveedor)
        namespaces = {'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
                      'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
                      'ad': 'urn:dian:gov:co:facturaelectronica:AttachedDocument'}
        
        proveedor_tag = root.find('.//cac:SenderParty/cac:PartyTaxScheme/cbc:RegistrationName', namespaces)
        proveedor = proveedor_tag.text if proveedor_tag is not None else "Proveedor Desconocido"
        
        # 2. Extraer el XML interno (CDATA dentro de Description)
        desc_tag = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', namespaces)
        
        if desc_tag is None or not desc_tag.text:
            return None, "No se encontró el contenido de la factura (Invoice) dentro del XML. Archivo Inválido."
            
        xml_content = desc_tag.text.strip()
        
        # Parsear el XML interno
        invoice_root = ET.fromstring(xml_content)
        
        # Namespace map para el Invoice interno
        ns_inv = {'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
                  'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'}
        
        # Datos Generales Factura
        folio = invoice_root.find('.//cbc:ID', ns_inv).text
        fecha = invoice_root.find('.//cbc:IssueDate', ns_inv).text
        
        # Totales Generales
        total_sin_imp_tag = invoice_root.find('.//cac:LegalMonetaryTotal/cbc:LineExtensionAmount', ns_inv)
        total_sin_imp = float(total_sin_imp_tag.text) if total_sin_imp_tag is not None else 0.0

        total_con_imp_tag = invoice_root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns_inv)
        total_con_imp = float(total_con_imp_tag.text) if total_con_imp_tag is not None else 0.0
        
        iva_total = 0.0
        tax_total_element = invoice_root.find('.//cac:TaxTotal/cbc:TaxAmount', ns_inv)
        if tax_total_element is not None:
             iva_total = float(tax_total_element.text)
        else:
             iva_total = total_con_imp - total_sin_imp

        # 3. Extraer Líneas (Ítems)
        items = []
        for i, line in enumerate(invoice_root.findall('.//cac:InvoiceLine', ns_inv)):
            line_id = i + 1 
            
            qty_tag = line.find('.//cbc:InvoicedQuantity', ns_inv)
            qty = float(qty_tag.text) if qty_tag is not None else 0.0
            
            desc_tag = line.find('.//cac:Item/cbc:Description', ns_inv)
            desc = desc_tag.text if desc_tag is not None else "Sin Descripción"
            
            # Referencia / SKU
            sku = "GENERICO"
            # Priorizar StandardItemIdentification (EAN/GTIN) o SellersItemIdentification (Ref. Proveedor)
            std_id = line.find('.//cac:Item/cac:StandardItemIdentification/cbc:ID', ns_inv)
            seller_id = line.find('.//cac:Item/cac:SellersItemIdentification/cbc:ID', ns_inv)
            
            if std_id is not None and std_id.text: sku = std_id.text
            elif seller_id is not None and seller_id.text: sku = seller_id.text
            
            # Precios
            price_tag = line.find('.//cac:Price/cbc:PriceAmount', ns_inv)
            price_unit = float(price_tag.text) if price_tag is not None else 0.0
            
            total_tag = line.find('.//cbc:LineExtensionAmount', ns_inv)
            line_subtotal = float(total_tag.text) if total_tag is not None else 0.0
            
            # Impuestos de Línea
            line_tax_amount = 0.0
            tax_tag = line.find('.//cac:TaxTotal/cbc:TaxAmount', ns_inv)
            if tax_tag is not None:
                line_tax_amount = float(tax_tag.text)
            
            items.append({
                'Line_ID': line_id,
                'SKU_Proveedor': sku,
                'Descripcion_Factura': desc,
                'Cantidad_Facturada': qty,
                'Precio_Unitario': price_unit, # Este es el costo de compra unitario (sin IVA)
                'Subtotal_Linea': line_subtotal,
                'Impuesto_Linea': line_tax_amount,
                'Total_Linea': line_subtotal + line_tax_amount
            })
            
        header_data = {
            'Proveedor': proveedor,
            'Folio': folio,
            'Fecha': fecha,
            'Subtotal_Factura': total_sin_imp,
            'IVA_Factura': iva_total,
            'Total_Factura': total_con_imp
        }
        
        return header_data, pd.DataFrame(items)
        
    except Exception as e:
        return None, f"Error procesando XML. Asegúrese de que es un AttachedDocument (DIAN): {str(e)}"

# --- LÓGICA DE ACTUALIZACIÓN ESPECÍFICA PARA GOOGLE SHEETS ---

def actualizar_inventario_gsheets(ws_inventario, df_recepcion_final):
    """
    Actualiza el stock y el costo de la Hoja de Inventario en Google Sheets.
    Crea nuevos productos si no existen.
    """
    # Leer el inventario actual de Google Sheets para hacer el merge correcto
    inventario_gs_df = leer_datos(ws_inventario, index_col='ID_Producto')
    
    # 1. Preparar DF para la actualización
    # Solo incluimos los ítems que realmente se recibieron (Cant_Recibida > 0)
    df_actualizar = df_recepcion_final[df_recepcion_final['Cant_Recibida'] > 0].copy()
    
    if df_actualizar.empty:
        return False, "No hay productos con cantidad recibida > 0 para actualizar."

    # Usaremos el SKU_Proveedor para mapear, que será nuestra "clave de sintonía"
    # Sin embargo, la columna de la DB es ID_Producto. Agregamos el SKU_Proveedor a la DB.
    
    
    # --- PROCESO DE ACTUALIZACIÓN (REQUIERE UN GET_ALL_VALUES para mapear filas) ---
    try:
        # Obtenemos todos los valores (incluyendo el ID de la fila en GSheets)
        data = ws_inventario.get_all_values()
        
        # Mapeo de la cabecera para encontrar las columnas de interés
        if not data: return False, "La hoja de inventario está vacía."
        
        header = data[0]
        # Índices de las columnas que necesitamos (ajustar según el orden real de tu GSHEETS)
        try:
            IDX_ID_PRODUCTO = header.index('ID_Producto') + 1 # +1 porque gspread es 1-based
            IDX_NOMBRE = header.index('Nombre') + 1
            IDX_PRECIO = header.index('Precio') + 1 # Precio de Venta (se mantiene)
            IDX_STOCK = header.index('Stock') + 1
            IDX_COSTO = header.index('Costo') + 1 # Costo de Compra (se actualiza)
            # Asumimos que has añadido la columna SKU_Proveedor a tu Google Sheet
            IDX_SKU_PROV = header.index('SKU_Proveedor') + 1 
        except ValueError as e:
             return False, f"🚨 Error: Columna '{str(e).split(' ')[-1]}' no encontrada en la cabecera de la hoja 'Inventario'. Asegúrate de que las columnas 'ID_Producto', 'Nombre', 'Precio', 'Stock', 'Costo' y 'SKU_Proveedor' existen."


        # Mapeo de SKU_Proveedor a la fila de GSheets
        sku_to_row = {row[IDX_SKU_PROV - 1]: i + 1 for i, row in enumerate(data[1:])}
        
        updates = []
        new_products = []
        
        for _, row in df_actualizar.iterrows():
            sku_prov = str(row['SKU_Proveedor'])
            cant_recibida = int(row['Cant_Recibida'])
            nuevo_costo = row['Precio_Unitario'] # Costo unitario de la factura
            nombre_producto = row['Descripcion_Factura'] # Usamos la descripción del XML
            
            if sku_prov in sku_to_row:
                # --- Producto Existente ---
                gs_row_index = sku_to_row[sku_prov]
                gs_fila = data[gs_row_index]
                
                # Obtener el stock actual
                stock_actual = int(gs_fila[IDX_STOCK - 1])
                nuevo_stock = stock_actual + cant_recibida
                
                # Crear la celda de actualización [R, C, Value]
                updates.append({'range': ws_inventario.title + f'!R{gs_row_index + 1}C{IDX_STOCK}', 'values': [[nuevo_stock]]})
                updates.append({'range': ws_inventario.title + f'!R{gs_row_index + 1}C{IDX_COSTO}', 'values': [[f"{nuevo_costo:.2f}"]]})
                
            else:
                # --- Producto Nuevo ---
                # Generar ID_Producto Interno: Usamos el SKU_Proveedor como ID_Producto
                nuevo_id_producto = sku_prov 
                # Stock_Inicial: La cantidad recibida
                
                new_products.append([
                    nuevo_id_producto, # ID_Producto
                    nombre_producto, # Nombre
                    "", # Precio (Venta: Dejar vacío para que lo llenen manualmente después)
                    cant_recibida, # Stock
                    nuevo_costo, # Costo
                    sku_prov # SKU_Proveedor
                ])

        # 2. Ejecutar Actualizaciones Masivas (Más eficiente)
        if updates:
            ws_inventario.batch_update(updates)
            
        # 3. Insertar nuevos productos
        if new_products:
            ws_inventario.append_rows(new_products)

        return True, f"✅ Actualización completada: {len(updates)//2} ítems existentes actualizados. {len(new_products)} ítems nuevos creados."

    except Exception as e:
        return False, f"🚨 Error en la actualización de Google Sheets: {e}"


# --- PÁGINA PRINCIPAL DE RECEPCIÓN XML ---

def page_recepcion_compra_xml(ws_inventario):
    """
    Simula el proceso NEXUS para Bigotes y Patitas: Carga XML -> Conciliación -> Actualización GSheets.
    """
    st.header("📦 Recepción de Compras (Vía XML Factura Electrónica)")
    st.markdown("---")

    # Inicializar estado
    if 'xml_data' not in st.session_state:
        st.session_state.xml_data = None
    if 'step_compra' not in st.session_state:
        st.session_state.step_compra = 1 # 1: Carga, 2: Conteo/Conciliación, 3: Cierre/Actualización


    # --- PASO 1: CARGA Y PARSING ---
    if st.session_state.step_compra == 1:
        st.subheader("1️⃣ Carga de Factura Electrónica (DIAN)")
        st.info("Sube el archivo XML del proveedor (AttachedDocument). El sistema extrae los ítems y verifica si ya tienes la referencia.")
        
        uploaded_file = st.file_uploader("Arrastra el XML aquí:", type=['xml'])

        if uploaded_file is not None:
            # 1. Parsear el XML
            header, df_items_raw = parse_dian_xml_engine(uploaded_file)
            
            if df_items_raw is not None:
                # 2. Leer el inventario de GSheets
                inventario_df = leer_datos(ws_inventario, index_col='ID_Producto')
                
                # Asegurar columna SKU_Proveedor en el inventario
                if 'SKU_Proveedor' not in inventario_df.columns:
                    inventario_df['SKU_Proveedor'] = inventario_df.index # Fallback temporal
                
                # 3. Realizar Homologación (Cruzar con la BD de Inventario de GSheets)
                # Creamos una columna temporal para el merge
                df_temp = df_items_raw.copy()
                
                # Cruzar por SKU_Proveedor
                df_merged = pd.merge(df_temp, 
                                     inventario_df[['Nombre', 'Costo', 'SKU_Proveedor']], 
                                     on='SKU_Proveedor', 
                                     how='left', 
                                     suffixes=('_Factura', '_Maestro'))
                
                # Identificar si es nuevo (Usando Nombre como proxy si ID_Producto no está en el merge)
                df_merged['Estado_Producto'] = df_merged['Nombre'].apply(lambda x: '🆕 NUEVO' if pd.isna(x) else '✅ EXISTENTE')
                df_merged['Descripcion_Final'] = df_merged['Nombre'].fillna(df_merged['Descripcion_Factura'])
                df_merged['Costo_Ultima_Compra'] = df_merged['Costo'].fillna(0.0) # El costo anterior de GSHEETS
                
                # Calcular variación de precio
                df_merged['Diferencia_Precio_Pct'] = (
                    (df_merged['Precio_Unitario'] - df_merged['Costo_Ultima_Compra']) / df_merged['Costo_Ultima_Compra']
                ) * 100
                df_merged['Diferencia_Precio_Pct'] = df_merged['Diferencia_Precio_Pct'].fillna(0.0)
                
                st.session_state.xml_data = {
                    'header': header,
                    'items_conciliacion': df_merged,
                    # Inicializar conteo con 0.0, listo para el paso 2
                    'conteo_real': df_merged[['Line_ID', 'SKU_Proveedor', 'Descripcion_Factura', 'Cantidad_Facturada']].copy().assign(Cant_Recibida=0.0)
                }

                st.success(f"Factura {header['Folio']} de {header['Proveedor']} cargada. Total: ${header['Total_Factura']:,.0f}")
                
                st.markdown("### 🔍 Análisis de Precios y Homologación")
                # Mostrar tabla de items
                st.dataframe(
                    df_merged[['SKU_Proveedor', 'Descripcion_Factura', 'Estado_Producto', 'Cantidad_Facturada', 'Precio_Unitario', 'Costo_Ultima_Compra', 'Diferencia_Precio_Pct']]
                        .style.format({
                            'Precio_Unitario': 'COP {:,.0f}',
                            'Costo_Ultima_Compra': 'COP {:,.0f}',
                            'Diferencia_Precio_Pct': '{:+.1f}%',
                            'Cantidad_Facturada': '{:,.0f}'
                        }),
                    use_container_width=True
                )
                
                st.markdown("---")
                if st.button("➡️ Ir a Conteo Físico", type="primary", use_container_width=True):
                    st.session_state.step_compra = 2
                    st.rerun()
            else:
                st.error(df_items_raw) # Mostrar el mensaje de error

    # --- PASO 2: CONTEO FÍSICO / CONCILIACIÓN ---
    elif st.session_state.step_compra == 2 and st.session_state.xml_data:
        st.subheader("2️⃣ Conteo Físico y Verificación")
        st.warning("Verifique las unidades realmente recibidas e ingrese el conteo. Por defecto, se asume que las unidades facturadas son correctas.")
        
        df_conteo = st.session_state.xml_data['conteo_real']
        
        c_tools, c_grid = st.columns([1, 4])
        
        with c_tools:
             if st.button("⚡ TODO OK (Auto-Recibir)", help="Copia la cantidad facturada a recibida para todas las líneas", use_container_width=True):
                df_conteo['Cant_Recibida'] = df_conteo['Cantidad_Facturada']
                st.session_state.xml_data['conteo_real'] = df_conteo
                st.toast("Cantidades copiadas (Todo OK) ✅", icon="✅")
                st.rerun() 

        with c_grid:
            edited_conteo = st.data_editor(
                df_conteo,
                column_config={
                    "Line_ID": st.column_config.NumberColumn(disabled=True, width="hidden"),
                    "SKU_Proveedor": st.column_config.TextColumn("SKU Proveedor", disabled=True),
                    "Descripcion_Factura": st.column_config.TextColumn("Producto", disabled=True),
                    "Cantidad_Facturada": st.column_config.NumberColumn("Facturado", disabled=True, format="%.0f"),
                    "Cant_Recibida": st.column_config.NumberColumn("Conteo Físico", required=True, min_value=0.0, step=1.0, format="%.0f")
                },
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key="editor_conteo_compra"
            )

        st.markdown("---")
        col_prev, col_next = st.columns([1, 5])
        
        if col_prev.button("⬅️ Atrás (Carga XML)"):
            st.session_state.step_compra = 1
            st.session_state.xml_data = None # Reiniciar datos
            st.rerun()
            
        if col_next.button("➡️ Finalizar Recepción y Actualizar Inventario", type="primary"):
            # Guardar la edición final de la grilla
            st.session_state.xml_data['conteo_real'] = edited_conteo
            st.session_state.step_compra = 3
            st.rerun()


    # --- PASO 3: CIERRE Y ACTUALIZACIÓN ---
    elif st.session_state.step_compra == 3 and st.session_state.xml_data:
        st.subheader("3️⃣ Cierre y Actualización de Google Sheets")
        
        # Merge final para el resumen (usando Line_ID como clave de unicidad)
        df_base = st.session_state.xml_data['items_conciliacion']
        df_conteo = st.session_state.xml_data['conteo_real']
        header = st.session_state.xml_data['header']
        
        # Merge: Conteo + Precios/Estado del item base
        df_final = pd.merge(
            df_conteo,
            df_base[['Line_ID', 'Precio_Unitario', 'Estado_Producto']],
            on='Line_ID', 
            how='left'
        )
        
        df_final['Diferencia'] = df_final['Cant_Recibida'] - df_final['Cantidad_Facturada']
        df_final['Estado_Conciliacion'] = df_final['Diferencia'].apply(lambda x: '✅ OK' if x == 0 else ('🔴 FALTANTE' if x < 0 else '🟡 SOBRANTE'))

        # Resumen
        faltantes = df_final[df_final['Diferencia'] < 0]
        recibidos_total = int(df_final['Cant_Recibida'].sum())
        
        st.metric("Unidades Recibidas (Total)", recibidos_total)
        st.metric("Referencias con Faltantes", len(faltantes), delta_color="inverse")
        
        st.markdown("### 📋 Resumen Final de la Recepción")
        st.dataframe(
            df_final[['SKU_Proveedor', 'Descripcion_Factura', 'Cantidad_Facturada', 'Cant_Recibida', 'Diferencia', 'Estado_Conciliacion', 'Precio_Unitario']]
                .style.apply(lambda row: ['background-color: #ffebee'] * len(row) if row['Diferencia'] < 0 else [''], axis=1)
                .format({'Precio_Unitario': '$ {:,.2f}', 'Cantidad_Facturada': '{:,.0f}', 'Cant_Recibida': '{:,.0f}', 'Diferencia': '{:,.0f}'}),
            use_container_width=True
        )

        st.markdown("---")
        
        if not faltantes.empty:
            st.error("🚨 ¡Atención! Existen faltantes. El inventario se actualizará solo con lo contado.")

        if st.button("🚀 Confirmar y Aplicar Cambios al Inventario de Google Sheets", type="primary", use_container_width=True):
            with st.spinner("Actualizando Inventario en Google Sheets..."):
                success, message = actualizar_inventario_gsheets(ws_inventario, df_final)
                
                if success:
                    st.balloons()
                    st.success(message)
                    st.session_state.xml_data = None
                    st.session_state.step_compra = 1
                    # st.rerun() # Opcional: recargar si quieres volver al paso 1 inmediatamente
                else:
                    st.error(message)

    # Si no hay datos, mostrar la info de inicio
    else:
         st.info("Inicia el proceso subiendo un XML en el paso 1.")


# --- LLAMADA DESDE EL SCRIPT PRINCIPAL ---

# Para integrar esto en tu script principal, debes:
# 1. Copiar las funciones 'parse_dian_xml_engine' y 'actualizar_inventario_gsheets'.
# 2. Copiar la función 'page_recepcion_compra_xml'.
# 3. Añadir una opción al menú de navegación del script principal:

# En el 'main()':
# ... (código existente)
# opcion_gestion = st.sidebar.radio(
#     "Reportes y Control:",
#     ('📋 Inventario', '💸 Gastos', '💰 Cuadre de Caja', '📦 Recepción Compras XML'), # << AÑADIR ESTO
#     key="sidebar_management"
# )
# ...
# with tab_admin:
#     if opcion_gestion == '📋 Inventario':
#         ...
#     elif opcion_gestion == '💸 Gastos':
#         ...
#     elif opcion_gestion == '💰 Cuadre de Caja':
#         ...
#     elif opcion_gestion == '📦 Recepción Compras XML': # << AÑADIR ESTA NUEVA LÓGICA
#         page_recepcion_compra_xml(ws_inventario)
