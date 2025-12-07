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

st.set_page_config(page_title="Recepción Inteligente 2.0 - Bigotes y Patitas", page_icon="🐱", layout="wide")

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
    """Conecta a Google Sheets y asegura que existan las hojas necesarias."""
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account).")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        
        if "SHEET_URL" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (SHEET_URL).")
            return None, None
            
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # 1. Hoja Inventario (Principal)
        try:
            ws_inv = sh.worksheet("Inventario")
        except:
            st.error("No se encontró la pestaña 'Inventario'.")
            return None, None

        # 2. Hoja Maestro_Proveedores (Memoria)
        try:
            ws_map = sh.worksheet("Maestro_Proveedores")
        except:
            # Si no existe, la creamos automáticamente
            ws_map = sh.add_worksheet(title="Maestro_Proveedores", rows=1000, cols=10)
            ws_map.append_row(["ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Factor_Pack", "Ultima_Actualizacion"])
        
        return ws_inv, ws_map

    except Exception as e:
        st.error(f"Error conexión a Google Sheets: {e}")
        return None, None

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

# --- 3. MOTOR DE MEMORIA Y APRENDIZAJE ---

def cargar_memoria(ws_map):
    """Descarga la memoria de asociaciones para pre-llenar datos."""
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
    """Guarda o actualiza las asociaciones en la hoja Maestro_Proveedores."""
    try:
        registros_actuales = ws_map.get_all_records()
        df_map = pd.DataFrame(registros_actuales)
        
        filas_nuevas = []
        updates = []
        
        mapa_filas = {} 
        if not df_map.empty:
            for idx, row in df_map.iterrows():
                key = f"{str(row['ID_Proveedor'])}_{str(row['SKU_Proveedor'])}"
                mapa_filas[key] = idx + 2

        for item in nuevos_datos:
            proveedor_id = str(item['ID_Proveedor'])
            sku_prov = str(item['SKU_Proveedor'])
            sku_interno = str(item['SKU_Interno']).strip()
            factor = item['Factor_Pack']
            nombre_prov = item['Proveedor_Nombre']
            
            if not sku_interno or sku_interno == "None": continue 

            key = f"{proveedor_id}_{sku_prov}"
            
            if key in mapa_filas:
                row_idx = mapa_filas[key]
                updates.append({'range': f"D{row_idx}", 'values': [[sku_interno]]})
                updates.append({'range': f"E{row_idx}", 'values': [[factor]]})
            else:
                filas_nuevas.append([proveedor_id, nombre_prov, sku_prov, sku_interno, factor, str(pd.Timestamp.now())])

        if updates: ws_map.batch_update(updates)
        if filas_nuevas: ws_map.append_rows(filas_nuevas)
            
        return True
    except Exception as e:
        st.error(f"Error guardando memoria: {e}")
        return False

# --- 4. PARSING XML ---

def parsear_xml_factura(archivo):
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        ns_map = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }

        # Extraer Invoice interno si es AttachedDocument
        desc_tag = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
        if desc_tag is not None and desc_tag.text:
            try:
                root_invoice = ET.fromstring(desc_tag.text.strip())
            except:
                root_invoice = root
        else:
            root_invoice = root

        ns_inv = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }

        # Datos del Proveedor
        prov_node = root_invoice.find('.//cac:AccountingSupplierParty/cac:Party', ns_inv)
        if prov_node is not None:
            nombre_prov_tag = prov_node.find('.//cac:PartyTaxScheme/cbc:RegistrationName', ns_inv)
            nombre_prov = nombre_prov_tag.text if nombre_prov_tag is not None else "Proveedor Desconocido"
            
            id_prov_tag = prov_node.find('.//cac:PartyTaxScheme/cbc:CompanyID', ns_inv)
            id_prov = id_prov_tag.text if id_prov_tag is not None else "GENERICO"
        else:
            nombre_prov = "Desconocido"
            id_prov = "GENERICO"
        
        folio_tag = root_invoice.find('.//cbc:ID', ns_inv)
        folio = folio_tag.text if folio_tag is not None else "---"

        items = []
        for line in root_invoice.findall('.//cac:InvoiceLine', ns_inv):
            try:
                desc_tag = line.find('.//cac:Item/cbc:Description', ns_inv)
                desc = desc_tag.text if desc_tag is not None else "Producto sin nombre"
                
                qty_tag = line.find('.//cbc:InvoicedQuantity', ns_inv)
                qty = float(qty_tag.text) if qty_tag is not None else 0.0
                
                price_tag = line.find('.//cac:Price/cbc:PriceAmount', ns_inv)
                costo_unit = float(price_tag.text) if price_tag is not None else 0.0
                
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
            except Exception:
                continue 

        return {"Proveedor": nombre_prov, "ID_Proveedor": id_prov, "Folio": folio, "Items": items}

    except Exception as e:
        st.error(f"Error procesando XML: {str(e)}")
        return None

# --- 5. LÓGICA DE ACTUALIZACIÓN ---

def procesar_inventario(ws_inv, df_final):
    # 1. Leer Inventario
    try:
        data = ws_inv.get_all_values()
        if not data: return False, ["El inventario está vacío"]
        headers = data[0]
    except: return False, ["Error leyendo inventario"]

    # Mapear columnas
    try:
        col_sku = headers.index('SKU_Proveedor') 
        col_stock = headers.index('Stock')
        col_costo = headers.index('Costo')
        col_precio = headers.index('Precio')
        
        if 'Nombre' in headers: col_nombre = headers.index('Nombre')
        elif 'Descripcion' in headers: col_nombre = headers.index('Descripcion')
        else: col_nombre = 0
            
    except:
        return False, ["Estructura de inventario incorrecta. Revisa columnas: SKU_Proveedor, Stock, Costo, Precio."]

    inv_map = {}
    for i, row in enumerate(data[1:], start=2):
        if len(row) <= col_sku: continue
        sku_val = str(row[col_sku]).strip()
        if sku_val:
            inv_map[sku_val] = {
                'fila': i,
                'stock': limpiar_moneda(row[col_stock]) if len(row) > col_stock else 0,
                'costo': limpiar_moneda(row[col_costo]) if len(row) > col_costo else 0,
                'precio': limpiar_moneda(row[col_precio]) if len(row) > col_precio else 0,
                'nombre': row[col_nombre] if len(row) > col_nombre else "Sin Nombre"
            }

    updates = []
    new_rows = []
    log = []

    for _, row in df_final.iterrows():
        sku_interno = str(row['SKU_Interno']).strip()
        nombre_prod = row['Descripcion_Factura']
        
        cant_packs = row['Cantidad_Facturada']
        factor = row['Factor_Pack']
        costo_pack = row['Costo_Pack_Factura']
        
        unidades_reales = cant_packs * factor
        costo_unitario_real = costo_pack / factor if factor > 0 else costo_pack
        
        if not sku_interno or sku_interno == "None" or sku_interno == "":
            log.append(f"⚠️ Saltado: {row['Descripcion_Factura']} (Sin SKU Interno asignado)")
            continue

        if sku_interno in inv_map:
            # ACTUALIZAR
            info = inv_map[sku_interno]
            fila = info['fila']
            stock_actual = info['stock']
            costo_actual = info['costo']
            precio_actual = info['precio']
            nombre_real = info['nombre']

            # A. Stock
            nuevo_stock = stock_actual + unidades_reales
            updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_stock + 1)}", 'values': [[sanitizar_dato(nuevo_stock)]]})

            # B. Precios
            nuevo_costo = costo_actual
            nuevo_precio = precio_actual
            msg_precio = ""

            if costo_unitario_real > costo_actual:
                nuevo_costo = costo_unitario_real
                nuevo_precio = nuevo_costo / 0.85
                msg_precio = f"📈 Costo subió. Precio ajustado."
                
                updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_costo + 1)}", 'values': [[sanitizar_dato(nuevo_costo)]]})
                updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_precio + 1)}", 'values': [[sanitizar_dato(nuevo_precio)]]})
            
            elif costo_unitario_real < costo_actual:
                nuevo_costo = costo_unitario_real
                msg_precio = f"💰 Costo bajó. Margen mejorado."
                updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_costo + 1)}", 'values': [[sanitizar_dato(nuevo_costo)]]})
            
            else:
                msg_precio = "Costo estable."

            log.append(f"🔄 **{nombre_real}**: +{unidades_reales:.0f} u. {msg_precio}")

        else:
            # NUEVO
            new_row = [""] * len(headers)
            new_row[col_sku] = sku_interno
            new_row[col_nombre] = nombre_prod
            new_row[col_stock] = sanitizar_dato(unidades_reales)
            new_row[col_costo] = sanitizar_dato(costo_unitario_real)
            
            precio_sugerido = costo_unitario_real / 0.85
            new_row[col_precio] = sanitizar_dato(precio_sugerido)
            
            new_rows.append(new_row)
            log.append(f"✨ **Nuevo**: {sku_interno} | {nombre_prod} | Stock: {unidades_reales}")

    try:
        if updates: ws_inv.batch_update(updates)
        if new_rows: ws_inv.append_rows(new_rows)
        return True, log
    except Exception as e:
        return False, [f"Error escribiendo Sheets: {e}"]

# --- 6. INTERFAZ DE USUARIO ---

def main():
    st.markdown('<p class="big-title">📦 Recepción Inteligente + Aprendizaje</p>', unsafe_allow_html=True)
    
    ws_inv, ws_map = conectar_sheets()
    if not ws_inv: st.stop()

    if 'xml_data' not in st.session_state: st.session_state.xml_data = None
    if 'paso' not in st.session_state: st.session_state.paso = 1

    # PASO 1: CARGA
    if st.session_state.paso == 1:
        uploaded_file = st.file_uploader("Sube tu Factura Electrónica (XML)", type=['xml'])
        if uploaded_file:
            with st.spinner("Leyendo factura..."):
                datos = parsear_xml_factura(uploaded_file)
                if datos and datos['Items']:
                    st.session_state.xml_data = datos
                    st.session_state.memoria = cargar_memoria(ws_map)
                    st.session_state.paso = 2
                    st.rerun()
                else:
                    st.error("No se pudieron leer items del XML. Verifica el formato.")

    # PASO 2: EDICIÓN
    elif st.session_state.paso == 2:
        data = st.session_state.xml_data
        memoria = st.session_state.memoria
        
        st.info(f"Proveedor: **{data['Proveedor']}**")

        filas_editor = []
        for item in data['Items']:
            key = f"{data['ID_Proveedor']}_{item['SKU_Proveedor']}"
            
            sku_int_prev = ""
            factor_prev = 1.0
            
            if key in memoria:
                sku_int_prev = memoria[key]['SKU_Interno']
                factor_prev = memoria[key]['Factor_Pack']

            filas_editor.append({
                "SKU_Proveedor": item['SKU_Proveedor'],
                "Descripcion_Factura": item['Descripcion_Factura'],
                "SKU_Interno": sku_int_prev,
                "Cantidad_Facturada": item['Cantidad_Facturada'],
                "Factor_Pack": factor_prev,
                "Costo_Pack_Factura": item['Costo_Pack_Factura'],
                "ID_Proveedor": data['ID_Proveedor'],
                "Proveedor_Nombre": data['Proveedor']
            })

        # --- CORRECCIÓN CRÍTICA: Asegurar que DataFrame tenga columnas siempre ---
        if filas_editor:
            df = pd.DataFrame(filas_editor)
        else:
            # Estructura vacía para evitar KeyError si la lista está vacía
            df = pd.DataFrame(columns=[
                "SKU_Proveedor", "Descripcion_Factura", "SKU_Interno", 
                "Cantidad_Facturada", "Factor_Pack", "Costo_Pack_Factura", 
                "ID_Proveedor", "Proveedor_Nombre"
            ])

        st.markdown("### 🔗 Asociación de Productos")

        edited_df = st.data_editor(
            df,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True),
                "Descripcion_Factura": st.column_config.TextColumn("Producto Factura", disabled=True, width="large"),
                "SKU_Interno": st.column_config.TextColumn("📝 TU CÓDIGO INTERNO", required=True),
                "Factor_Pack": st.column_config.NumberColumn("📦 Unids/Pack", min_value=1, step=1, default=1),
                "Cantidad_Facturada": st.column_config.NumberColumn("Cant. Factura", disabled=True),
                "Costo_Pack_Factura": st.column_config.NumberColumn("Costo Pack", format="$%.2f", disabled=True),
                "ID_Proveedor": None,
                "Proveedor_Nombre": None
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )

        st.markdown("---")
        st.markdown("##### 👁️ Previsualización")
        
        # --- CORRECCIÓN CRÍTICA: Validar que existan datos antes de calcular ---
        if not edited_df.empty and 'Cantidad_Facturada' in edited_df.columns:
            edited_df['Unidades_Totales'] = edited_df['Cantidad_Facturada'] * edited_df['Factor_Pack']
            edited_df['Costo_Unitario_Real'] = edited_df['Costo_Pack_Factura'] / edited_df['Factor_Pack']
            
            st.dataframe(
                edited_df[['SKU_Interno', 'Descripcion_Factura', 'Unidades_Totales', 'Costo_Unitario_Real']],
                column_config={
                    "Costo_Unitario_Real": st.column_config.NumberColumn("Costo Unitario Real", format="$%.2f"),
                    "Unidades_Totales": st.column_config.NumberColumn("Total Unidades a Sumar")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No hay items para previsualizar.")

        col1, col2 = st.columns([1, 4])
        if col1.button("Cancelar"):
            st.session_state.paso = 1
            st.rerun()
            
        if col2.button("💾 Procesar, Aprender y Actualizar", type="primary"):
            if edited_df.empty:
                st.error("No hay datos para procesar.")
            else:
                with st.spinner("Guardando..."):
                    datos_aprendizaje = edited_df.to_dict('records')
                    guardar_aprendizaje(ws_map, datos_aprendizaje)
                    
                    exito, logs = procesar_inventario(ws_inv, edited_df)
                    
                    if exito:
                        st.success("✅ ¡Proceso completado!")
                        with st.expander("Ver reporte"):
                            for l in logs: st.write(l)
                        time.sleep(5)
                        st.session_state.paso = 1
                        st.rerun()
                    else:
                        st.error("Error:")
                        for l in logs: st.error(l)

if __name__ == "__main__":
    main()
