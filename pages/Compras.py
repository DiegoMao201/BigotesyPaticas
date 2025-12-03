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
        # Usar las credenciales de Streamlit import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time

# --- 1. CONFIGURACIÓN Y ESTILOS (Idéntico al Main para consistencia) ---

COLOR_PRIMARIO = "#2ecc71"
COLOR_SECUNDARIO = "#e67e22"
COLOR_FONDO = "#f4f6f9"

st.set_page_config(page_title="Recepción Compras XML", page_icon="📦", layout="wide")

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

# --- 2. CONEXIÓN Y UTILIDADES (Repetimos para que sea autónomo) ---

@st.cache_resource(ttl=600)
def conectar_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos.")
            return None
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        hoja = gc.open_by_url(st.secrets["SHEET_URL"])
        return hoja.worksheet("Inventario")
    except Exception as e:
        st.error(f"Error conexión: {e}")
        return None

def leer_inventario(ws):
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        # Convertir columnas clave a numérico
        for col in ['Stock', 'Costo', 'Precio']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=['ID_Producto', 'Nombre', 'Stock', 'Costo', 'Precio', 'SKU_Proveedor'])

def sanitizar_dato(dato):
    """Evita error JSON con tipos numpy"""
    if isinstance(dato, (np.int64, np.int32)): return int(dato)
    if isinstance(dato, (np.float64, np.float32)): return float(dato)
    return dato

# --- 3. MOTOR DE PARSING XML (FACTURA ELECTRÓNICA) ---
# 

[Image of XML parsing logic flowchart]


def parsear_xml_factura(archivo):
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        # Namespaces comunes en facturación UBL 2.1
        ns = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ad': 'urn:dian:gov:co:facturaelectronica:AttachedDocument'
        }

        # 1. Intentar encontrar el Invoice dentro de AttachedDocument (XML anidado)
        # Esto es típico en Colombia (AttachedDocument contiene la factura y la firma)
        desc_tag = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns)
        
        if desc_tag is not None and desc_tag.text:
            # Parsear el XML interno (CDATA)
            root_invoice = ET.fromstring(desc_tag.text)
        else:
            # Si no es AttachedDocument, asumir que es el Invoice directo
            root_invoice = root

        # Actualizar namespaces para el Invoice
        ns_inv = {'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
                  'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'}

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
                
                # Costo Unitario
                price = float(line.find('.//cac:Price/cbc:PriceAmount', ns_inv).text)
                
                # Identificación (SKU del proveedor)
                # Intentamos buscar StandardItemIdentification o SellersItemIdentification
                sku_tag = line.find('.//cac:Item/cac:StandardItemIdentification/cbc:ID', ns_inv)
                if sku_tag is None:
                    sku_tag = line.find('.//cac:Item/cac:SellersItemIdentification/cbc:ID', ns_inv)
                
                sku = sku_tag.text if sku_tag is not None else "GENERICO"

                items.append({
                    "SKU_Proveedor": sku,
                    "Descripcion": desc,
                    "Cantidad_Facturada": qty,
                    "Costo_Unitario": price,
                    "Total_Linea": qty * price
                })
            except Exception as e:
                continue # Saltar línea si falla

        return {"Proveedor": proveedor, "Folio": folio, "Items": items}

    except Exception as e:
        st.error(f"Error procesando XML: {str(e)}")
        return None

# --- 4. LÓGICA DE ACTUALIZACIÓN ---

def procesar_actualizacion(ws, df_final):
    """
    Actualiza Stock y Costo si existe el SKU/ID, o crea producto nuevo.
    """
    # Leer inventario actual completo para ubicar filas
    inventario_data = ws.get_all_records()
    df_inv = pd.DataFrame(inventario_data)
    
    # Asegurar que ID_Producto sea string para comparar
    if not df_inv.empty:
        df_inv['ID_Producto'] = df_inv['ID_Producto'].astype(str)
        df_inv['SKU_Proveedor'] = df_inv['SKU_Proveedor'].astype(str)
    
    updates = [] # Lista de celdas a actualizar
    new_rows = [] # Filas nuevas
    
    # Headers mapping (ajusta según tu hoja real)
    # Suponemos columnas: ID_Producto, Nombre, Precio, Stock, Costo, SKU_Proveedor
    try:
        # Encontrar índices de columnas (gspread usa 1-based index)
        headers = ws.row_values(1)
        col_stock = headers.index('Stock') + 1
        col_costo = headers.index('Costo') + 1
        col_sku = headers.index('SKU_Proveedor') + 1
    except ValueError:
        return False, "Estructura de hoja inválida. Faltan columnas (Stock, Costo, SKU_Proveedor)."

    log = []

    for index, row in df_final.iterrows():
        sku = str(row['SKU_Proveedor'])
        cant = row['Cantidad_Recibida']
        costo = row['Costo_Unitario']
        nombre = row['Descripcion']
        
        if cant <= 0: continue # Ignorar items en 0
        
        # Buscar en inventario existente por SKU
        match = df_inv[df_inv['SKU_Proveedor'] == sku]
        
        if not match.empty:
            # --- ACTUALIZAR EXISTENTE ---
            fila_idx = match.index[0]
            fila_real = fila_idx + 2 # +2 (1 por header, 1 por 0-index)
            
            stock_actual = float(match.iloc[0]['Stock'])
            nuevo_stock = stock_actual + cant
            
            # Preparar actualizaciones batch (más seguro que update_cell en bucle)
            ws.update_cell(fila_real, col_stock, sanitizar_dato(nuevo_stock))
            ws.update_cell(fila_real, col_costo, sanitizar_dato(costo))
            log.append(f"🔄 Actualizado: {nombre} (+{cant})")
            
        else:
            # --- CREAR NUEVO ---
            # ID_Producto, Nombre, Precio, Stock, Costo, SKU_Proveedor, Categoria, ...
            nuevo_item = [
                sku,       # ID_Producto (Usamos SKU como ID inicial)
                nombre,    # Nombre
                0,         # Precio Venta (Pendiente definir)
                cant,      # Stock
                costo,     # Costo
                sku,       # SKU_Proveedor
                "General"  # Categoria default
            ]
            # Rellenar con vacíos si hay más columnas en tu hoja
            while len(nuevo_item) < len(headers):
                nuevo_item.append("")
                
            new_rows.append([sanitizar_dato(x) for x in nuevo_item])
            log.append(f"✨ Nuevo: {nombre}")

    if new_rows:
        ws.append_rows(new_rows)
        
    return True, log


# --- 5. INTERFAZ DE USUARIO (PAGE) ---

def main():
    st.markdown('<p class="big-title">📦 Recepción de Compras (XML)</p>', unsafe_allow_html=True)
    st.markdown("---")

    ws_inv = conectar_sheets()
    
    if not ws_inv:
        return

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
                        st.error("No se pudieron extraer items del XML.")

        with col_info:
            st.info("""
            **Instrucciones:**
            1. Sube el archivo `.xml` (AttachedDocument) que te envió tu proveedor.
            2. El sistema extraerá automáticamente costos y cantidades.
            3. Podrás verificar las cantidades antes de guardar.
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
                "Total_Linea": st.column_config.NumberColumn("Total", disabled=True, format="$%.2f")
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )
        
        # Calcular diferencias
        diff = edited_df['Cantidad_Recibida'].sum() - edited_df['Cantidad_Facturada'].sum()
        if diff != 0:
            st.warning(f"⚠️ Hay una diferencia de {diff} unidades entre lo facturado y lo recibido.")
        
        st.markdown("---")
        c_back, c_space, c_save = st.columns([1, 3, 2])
        
        if c_back.button("⬅️ Cancelar y Volver"):
            st.session_state.xml_data = None
            st.session_state.paso = 1
            if 'df_editor' in st.session_state: del st.session_state.df_editor
            st.rerun()
            
        if c_save.button("💾 Guardar y Actualizar Inventario", type="primary"):
            with st.spinner("Actualizando Google Sheets..."):
                exito, log = procesar_actualizacion(ws_inv, edited_df)
                
                if exito:
                    st.balloons()
                    st.success("¡Inventario actualizado correctamente!")
                    with st.expander("Ver detalles de cambios"):
                        for l in log:
                            st.write(l)
                    
                    # Resetear
                    time.sleep(4)
                    st.session_state.xml_data = None
                    st.session_state.paso = 1
                    del st.session_state.df_editor
                    st.rerun()
                else:
                    st.error(f"Error al guardar: {log}")

if __name__ == "__main__":
    main()
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
