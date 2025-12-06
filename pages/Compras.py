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

st.set_page_config(page_title="Recepción Inteligente - Bigotes y Patitas", page_icon="🐱", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_FONDO}; }}
    .big-title {{ font-family: 'Helvetica Neue', sans-serif; font-size: 2.2em; color: #2c3e50; font-weight: 800; }}
    .stButton button[type="primary"] {{
        background: linear-gradient(45deg, {COLOR_PRIMARIO}, #27ae60);
        border: none; color: white; font-weight: bold; border-radius: 12px; padding: 0.5rem 1rem;
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

def limpiar_moneda(valor):
    """Convierte strings de moneda ($ 1.000) a float puro"""
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        # Eliminar símbolos de moneda, comas de miles (si usas punto decimal)
        # Asumimos formato internacional estándar o ajusta según tu locale
        limpio = valor.replace('$', '').replace(',', '').strip()
        try:
            return float(limpio)
        except:
            return 0.0
    return 0.0

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
        desc_tag = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
        
        if desc_tag is not None and desc_tag.text:
            root_invoice = ET.fromstring(desc_tag.text.strip())
        else:
            root_invoice = root

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
                
                # Costo Unitario
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
                continue 

        return {"Proveedor": proveedor, "Folio": folio, "Items": items}

    except Exception as e:
        st.error(f"Error procesando XML: {str(e)}")
        return None

# --- 4. LÓGICA INTELIGENTE DE ACTUALIZACIÓN ---

def procesar_actualizacion(ws, df_final):
    """
    Actualiza Stock.
    Logica Inteligente de Precios:
    - Nuevo Costo > Costo Actual -> Actualiza Costo y Sube Precio (Costo / 0.85)
    - Nuevo Costo < Costo Actual -> Actualiza Costo y MANTIENE Precio (Más ganancia)
    """
    
    # 1. Leer datos actuales
    try:
        data = ws.get_all_values()
    except Exception as e:
        return False, [f"Error leyendo hoja: {e}"]

    if not data:
        return False, ["La hoja de inventario está vacía."]

    headers = data[0]
    
    # Validar columnas necesarias
    required_cols = ['Stock', 'Costo', 'SKU_Proveedor', 'Precio']
    try:
        col_idxs = {name: headers.index(name) for name in required_cols}
        # Añadir opcionales si existen
        if 'Nombre' in headers: col_idxs['Nombre'] = headers.index('Nombre')
        elif 'Descripcion' in headers: col_idxs['Nombre'] = headers.index('Descripcion')
        else: col_idxs['Nombre'] = None
            
    except ValueError as e:
        return False, [f"Falta columna requerida en Sheets. Verifica que existan: {required_cols}. Error: {e}"]

    # Mapa SKU -> {fila, stock, costo, precio}
    sku_map = {}
    for i, row in enumerate(data):
        if i == 0: continue
        val_sku = str(row[col_idxs['SKU_Proveedor']]).strip()
        if val_sku:
            sku_map[val_sku] = {
                'fila': i + 1, # 1-based para gspread
                'stock': limpiar_moneda(row[col_idxs['Stock']] if len(row) > col_idxs['Stock'] else 0),
                'costo': limpiar_moneda(row[col_idxs['Costo']] if len(row) > col_idxs['Costo'] else 0),
                'precio': limpiar_moneda(row[col_idxs['Precio']] if len(row) > col_idxs['Precio'] else 0)
            }

    updates = []
    new_rows = []
    log = []

    for index, row in df_final.iterrows():
        sku = str(row['SKU_Proveedor']).strip()
        cant_recibida = row['Cantidad_Recibida']
        costo_nuevo_factura = float(row['Costo_Unitario'])
        nombre = row['Descripcion']
        
        if cant_recibida <= 0: continue
        
        if sku in sku_map:
            # --- PRODUCTO EXISTENTE ---
            info_actual = sku_map[sku]
            fila = info_actual['fila']
            stock_actual = info_actual['stock']
            costo_actual = info_actual['costo']
            precio_actual = info_actual['precio']
            
            # A. Actualizar Stock
            nuevo_stock = stock_actual + cant_recibida
            updates.append({
                'range': f"{gspread.utils.rowcol_to_a1(fila, col_idxs['Stock'] + 1)}",
                'values': [[sanitizar_dato(nuevo_stock)]]
            })
            
            # B. Lógica de Precios Inteligente
            precio_final = precio_actual # Por defecto se mantiene
            costo_final = costo_actual   # Por defecto
            mensaje_precio = ""

            if costo_nuevo_factura > costo_actual:
                # 🔴 SUBIÓ EL COSTO: Actualizamos costo y subimos precio para mantener margen
                costo_final = costo_nuevo_factura
                precio_final = costo_final / 0.85
                mensaje_precio = f"📈 Costo subió. Precio ajustado a ${precio_final:,.0f}"
                
                updates.append({
                    'range': f"{gspread.utils.rowcol_to_a1(fila, col_idxs['Costo'] + 1)}",
                    'values': [[sanitizar_dato(costo_final)]]
                })
                updates.append({
                    'range': f"{gspread.utils.rowcol_to_a1(fila, col_idxs['Precio'] + 1)}",
                    'values': [[sanitizar_dato(precio_final)]]
                })
                
            elif costo_nuevo_factura < costo_actual:
                # 🟢 BAJÓ EL COSTO (Descuento): Actualizamos costo, mantenemos precio alto
                costo_final = costo_nuevo_factura
                # precio_final SE QUEDA IGUAL (precio_actual)
                mensaje_precio = f"💰 Descuento detectado. Costo bajó, precio mantenido (Mayor Margen)."
                
                updates.append({
                    'range': f"{gspread.utils.rowcol_to_a1(fila, col_idxs['Costo'] + 1)}",
                    'values': [[sanitizar_dato(costo_final)]]
                })
                # No enviamos update de Precio
                
            else:
                mensaje_precio = "Costo sin cambios."

            log.append(f"🔄 **{nombre}**: Stock {stock_actual}->{nuevo_stock}. {mensaje_precio}")
            
        else:
            # --- PRODUCTO NUEVO ---
            nuevo_item_row = [""] * len(headers)
            
            # Llenar datos base
            nuevo_item_row[col_idxs['SKU_Proveedor']] = sku
            if col_idxs['Nombre'] is not None:
                nuevo_item_row[col_idxs['Nombre']] = nombre
            nuevo_item_row[col_idxs['Stock']] = sanitizar_dato(cant_recibida)
            nuevo_item_row[col_idxs['Costo']] = sanitizar_dato(costo_nuevo_factura)
            
            # Calcular Precio Sugerido (Divisor 0.85)
            precio_sugerido = costo_nuevo_factura / 0.85
            nuevo_item_row[col_idxs['Precio']] = sanitizar_dato(precio_sugerido)
            
            new_rows.append(nuevo_item_row)
            log.append(f"✨ **Nuevo Producto**: {nombre} | Costo: ${costo_nuevo_factura:,.0f} | Precio Venta: ${precio_sugerido:,.0f}")

    # EJECUTAR CAMBIOS EN LOTES
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
    st.markdown('<p class="big-title">📦 Recepción Inteligente de Compras</p>', unsafe_allow_html=True)
    st.caption("Sistema de gestión automatizada de inventario y precios para Bigotes y Patitas")
    st.markdown("---")

    ws_inv = conectar_sheets()
    
    if not ws_inv:
        st.stop()

    if 'xml_data' not in st.session_state: st.session_state.xml_data = None
    if 'paso' not in st.session_state: st.session_state.paso = 1

    # [PASO 1] CARGA DE ARCHIVO
    if st.session_state.paso == 1:
        col_up, col_info = st.columns([2, 1])
        
        with col_up:
            uploaded_file = st.file_uploader("Arrastra tu Factura Electrónica (XML)", type=['xml'])
            
            if uploaded_file is not None:
                with st.spinner("🧠 Analizando precios y estructura..."):
                    datos = parsear_xml_factura(uploaded_file)
                    
                    if datos and len(datos['Items']) > 0:
                        st.session_state.xml_data = datos
                        st.session_state.paso = 2
                        st.rerun()
                    else:
                        st.error("No se pudieron extraer items del XML o el formato no es válido.")

        with col_info:
            st.info("""
            **🤖 Modo Inteligente Activo:**
            
            1. **Subida de Costos:** Si el producto llega más caro, el sistema subirá el precio automáticamente (Costo / 0.85).
            
            2. **Descuentos:** Si el producto llega más barato, el sistema bajará el costo en inventario pero **mantendrá tu precio de venta** para que ganes más.
            """)

    # [PASO 2] CONCILIACIÓN Y VERIFICACIÓN
    elif st.session_state.paso == 2 and st.session_state.xml_data:
        data = st.session_state.xml_data
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Proveedor", data['Proveedor'])
        c2.metric("Folio Factura", data['Folio'])
        c3.metric("Items Detectados", len(data['Items']))
        
        st.markdown("### 🕵️ Verificación de Inventario")
        
        if 'df_editor' not in st.session_state:
            df = pd.DataFrame(data['Items'])
            df['Cantidad_Recibida'] = df['Cantidad_Facturada'] 
            st.session_state.df_editor = df

        edited_df = st.data_editor(
            st.session_state.df_editor,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Código", disabled=True),
                "Descripcion": st.column_config.TextColumn("Producto", disabled=True, width="large"),
                "Costo_Unitario": st.column_config.NumberColumn("Costo Nuevo", format="$%.2f", disabled=True),
                "Cantidad_Facturada": st.column_config.NumberColumn("Facturado", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ Recibido Real", min_value=0, required=True),
                "Total_Linea": st.column_config.NumberColumn("Total", disabled=True, format="$%.2f")
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )
        
        diff = edited_df['Cantidad_Recibida'].sum() - edited_df['Cantidad_Facturada'].sum()
        if diff != 0:
            st.warning(f"⚠️ Diferencia de {diff} unidades entre factura y recepción.")
        
        st.markdown("---")
        c_back, c_space, c_save = st.columns([1, 3, 2])
        
        if c_back.button("⬅️ Cancelar"):
            st.session_state.xml_data = None
            st.session_state.paso = 1
            if 'df_editor' in st.session_state: del st.session_state.df_editor
            st.rerun()
            
        if c_save.button("🧠 Procesar Compra Inteligente", type="primary"):
            with st.spinner("Aplicando lógica de precios y stock..."):
                exito, logs = procesar_actualizacion(ws_inv, edited_df)
                
                if exito:
                    st.balloons()
                    st.success("¡Inventario y Precios actualizados con éxito!")
                    with st.expander("📝 Ver reporte de cambios (Costos y Precios)"):
                        for l in logs:
                            if "Nuevo Producto" in l:
                                st.markdown(f"✨ {l}")
                            elif "Costo subió" in l:
                                st.markdown(f"🔴 {l}")
                            elif "Descuento" in l:
                                st.markdown(f"🟢 {l}")
                            else:
                                st.write(l)
                    
                    time.sleep(5)
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
