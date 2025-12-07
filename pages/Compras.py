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
        # Creamos un diccionario clave: "IDProveedor_SKUProveedor" -> {SKU_Interno, Factor}
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
    """
    Guarda o actualiza las asociaciones en la hoja Maestro_Proveedores.
    nuevos_datos = lista de dicts con la nueva info validada por el usuario.
    """
    try:
        registros_actuales = ws_map.get_all_records()
        df_map = pd.DataFrame(registros_actuales)
        
        filas_nuevas = []
        updates = []
        
        # Obtenemos un mapa de filas existentes para actualizar rápido
        mapa_filas = {} # Clave -> Indice de fila (0-based en el df, +2 para sheets)
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
            
            if not sku_interno: continue # Si no asignaron SKU interno, no memorizamos

            key = f"{proveedor_id}_{sku_prov}"
            
            if key in mapa_filas:
                # Actualizamos registro existente
                row_idx = mapa_filas[key]
                # Actualizamos Columna D (SKU Interno) y E (Factor)
                updates.append({'range': f"D{row_idx}", 'values': [[sku_interno]]})
                updates.append({'range': f"E{row_idx}", 'values': [[factor]]})
            else:
                # Registro nuevo
                filas_nuevas.append([proveedor_id, nombre_prov, sku_prov, sku_interno, factor, str(pd.Timestamp.now())])

        if updates:
            ws_map.batch_update(updates)
        if filas_nuevas:
            ws_map.append_rows(filas_nuevas)
            
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
            root_invoice = ET.fromstring(desc_tag.text.strip())
        else:
            root_invoice = root

        ns_inv = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }

        # Datos del Proveedor (Vital para la memoria)
        prov_node = root_invoice.find('.//cac:AccountingSupplierParty/cac:Party', ns_inv)
        nombre_prov = prov_node.find('.//cac:PartyTaxScheme/cbc:RegistrationName', ns_inv).text
        # ID Proveedor (NIT/RUT)
        id_prov_tag = prov_node.find('.//cac:PartyTaxScheme/cbc:CompanyID', ns_inv)
        id_prov = id_prov_tag.text if id_prov_tag is not None else "GENERICO"
        
        folio = root_invoice.find('.//cbc:ID', ns_inv).text

        items = []
        for line in root_invoice.findall('.//cac:InvoiceLine', ns_inv):
            try:
                desc = line.find('.//cac:Item/cbc:Description', ns_inv).text
                qty = float(line.find('.//cbc:InvoicedQuantity', ns_inv).text)
                
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
                    "Cantidad_Facturada": qty,     # Paquetes facturados
                    "Costo_Pack_Factura": costo_unit, # Costo por paquete
                    "Total_Linea": qty * costo_unit
                })
            except: continue 

        return {"Proveedor": nombre_prov, "ID_Proveedor": id_prov, "Folio": folio, "Items": items}

    except Exception as e:
        st.error(f"Error procesando XML: {str(e)}")
        return None

# --- 5. LÓGICA DE ACTUALIZACIÓN DE INVENTARIO ---

def procesar_inventario(ws_inv, df_final):
    """
    Actualiza el inventario usando el SKU INTERNO y CALCULOS UNITARIOS.
    """
    # 1. Leer Inventario Actual
    try:
        data = ws_inv.get_all_values()
        headers = data[0]
    except: return False, ["Error leyendo inventario"]

    # Mapear columnas
    try:
        col_sku = headers.index('SKU_Proveedor') # Asumimos que esta columna guarda TU SKU Interno
        col_stock = headers.index('Stock')
        col_costo = headers.index('Costo')
        col_precio = headers.index('Precio')
        # Opcionales
        col_nombre = headers.index('Nombre') if 'Nombre' in headers else headers.index('Descripcion')
    except:
        return False, ["Estructura de inventario incorrecta. Faltan columnas clave (Stock, Costo, Precio, SKU_Proveedor)."]

    # Crear mapa de inventario actual: SKU_Interno -> {fila, datos}
    inv_map = {}
    for i, row in enumerate(data[1:], start=2): # Start=2 para coincidir con fila Excel
        sku_val = str(row[col_sku]).strip()
        if sku_val:
            inv_map[sku_val] = {
                'fila': i,
                'stock': limpiar_moneda(row[col_stock]),
                'costo': limpiar_moneda(row[col_costo]),
                'precio': limpiar_moneda(row[col_precio]),
                'nombre': row[col_nombre]
            }

    updates = []
    new_rows = []
    log = []

    for _, row in df_final.iterrows():
        # Datos ya procesados por el usuario
        sku_interno = str(row['SKU_Interno']).strip()
        nombre_prod = row['Descripcion_Factura'] # O el nombre del inventario
        
        cant_packs = row['Cantidad_Facturada']
        factor = row['Factor_Pack']
        costo_pack = row['Costo_Pack_Factura']
        
        # CÁLCULOS UNITARIOS REALES
        unidades_reales = cant_packs * factor
        costo_unitario_real = costo_pack / factor if factor > 0 else costo_pack
        
        if not sku_interno or sku_interno == "None" or sku_interno == "":
            log.append(f"⚠️ Saltado: {row['Descripcion_Factura']} (Sin SKU Interno asignado)")
            continue

        if sku_interno in inv_map:
            # --- PRODUCTO EXISTENTE ---
            info = inv_map[sku_interno]
            fila = info['fila']
            stock_actual = info['stock']
            costo_actual = info['costo']
            precio_actual = info['precio']
            nombre_real = info['nombre']

            # A. Stock
            nuevo_stock = stock_actual + unidades_reales
            updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_stock + 1)}", 'values': [[sanitizar_dato(nuevo_stock)]]})

            # B. Precios Inteligentes (Unitarios)
            nuevo_precio = precio_actual
            nuevo_costo = costo_actual
            msg_precio = ""

            if costo_unitario_real > costo_actual:
                # Costo Subió -> Subimos Precio
                nuevo_costo = costo_unitario_real
                nuevo_precio = nuevo_costo / 0.85
                msg_precio = f"📈 Subió costo unitario (${costo_actual:,.0f} -> ${nuevo_costo:,.0f}). Precio ajustado."
                
                updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_costo + 1)}", 'values': [[sanitizar_dato(nuevo_costo)]]})
                updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_precio + 1)}", 'values': [[sanitizar_dato(nuevo_precio)]]})
            
            elif costo_unitario_real < costo_actual:
                # Costo Bajó -> Mantenemos precio (Más margen)
                nuevo_costo = costo_unitario_real
                msg_precio = f"💰 Bajó costo unitario. Precio mantenido (Mayor margen)."
                updates.append({'range': f"{gspread.utils.rowcol_to_a1(fila, col_costo + 1)}", 'values': [[sanitizar_dato(nuevo_costo)]]})
            
            else:
                msg_precio = "Costo estable."

            log.append(f"🔄 **{nombre_real}**: +{unidades_reales:.0f} u. (Venían {cant_packs} packs de {factor}). {msg_precio}")

        else:
            # --- PRODUCTO NUEVO (Crear en inventario) ---
            new_row = [""] * len(headers)
            new_row[col_sku] = sku_interno
            new_row[col_nombre] = nombre_prod
            new_row[col_stock] = sanitizar_dato(unidades_reales)
            new_row[col_costo] = sanitizar_dato(costo_unitario_real)
            
            precio_sugerido = costo_unitario_real / 0.85
            new_row[col_precio] = sanitizar_dato(precio_sugerido)
            
            new_rows.append(new_row)
            log.append(f"✨ **Nuevo Item Creado**: {sku_interno} | {nombre_prod} | Stock: {unidades_reales} | Precio: ${precio_sugerido:,.0f}")

    # Escribir cambios
    try:
        if updates: ws_inv.batch_update(updates)
        if new_rows: ws_inv.append_rows(new_rows)
        return True, log
    except Exception as e:
        return False, [f"Error escribiendo Sheets: {e}"]

# --- 6. INTERFAZ DE USUARIO ---

def main():
    st.markdown('<p class="big-title">📦 Recepción Inteligente + Aprendizaje</p>', unsafe_allow_html=True)
    st.caption("Asocia productos de proveedores con tu inventario interno, maneja packs y actualiza precios unitarios.")
    
    ws_inv, ws_map = conectar_sheets()
    if not ws_inv: st.stop()

    if 'xml_data' not in st.session_state: st.session_state.xml_data = None
    if 'paso' not in st.session_state: st.session_state.paso = 1

    # PASO 1: CARGA
    if st.session_state.paso == 1:
        uploaded_file = st.file_uploader("Sube tu Factura Electrónica (XML)", type=['xml'])
        if uploaded_file:
            with st.spinner("Leyendo factura y consultando memoria..."):
                datos = parsear_xml_factura(uploaded_file)
                if datos:
                    st.session_state.xml_data = datos
                    st.session_state.memoria = cargar_memoria(ws_map) # Cargar memoria existente
                    st.session_state.paso = 2
                    st.rerun()

    # PASO 2: ASOCIACIÓN Y EDICIÓN
    elif st.session_state.paso == 2:
        data = st.session_state.xml_data
        memoria = st.session_state.memoria
        
        st.info(f"Proveedor: **{data['Proveedor']}** (ID: {data['ID_Proveedor']})")

        # Preparar DataFrame para el editor
        filas_editor = []
        for item in data['Items']:
            key = f"{data['ID_Proveedor']}_{item['SKU_Proveedor']}"
            
            # Buscamos en memoria si ya conocemos este producto
            sku_int_prev = ""
            factor_prev = 1.0
            
            if key in memoria:
                sku_int_prev = memoria[key]['SKU_Interno']
                factor_prev = memoria[key]['Factor_Pack']

            filas_editor.append({
                "SKU_Proveedor": item['SKU_Proveedor'],
                "Descripcion_Factura": item['Descripcion_Factura'],
                "SKU_Interno": sku_int_prev,  # Campo editable clave
                "Cantidad_Facturada": item['Cantidad_Facturada'],
                "Factor_Pack": factor_prev,   # Campo editable clave (Unidades por caja)
                "Costo_Pack_Factura": item['Costo_Pack_Factura'],
                "ID_Proveedor": data['ID_Proveedor'], # Oculto pero necesario
                "Proveedor_Nombre": data['Proveedor']
            })

        df = pd.DataFrame(filas_editor)
        
        st.markdown("### 🔗 Asociación de Productos")
        st.markdown("Asigna **Tu Código Interno** y cuántas unidades vienen por **Pack**.")

        edited_df = st.data_editor(
            df,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True, help="Código en la factura"),
                "Descripcion_Factura": st.column_config.TextColumn("Producto Factura", disabled=True, width="large"),
                
                "SKU_Interno": st.column_config.TextColumn(
                    "📝 TU CÓDIGO INTERNO", 
                    help="Escribe el código tal cual está en tu inventario. Si lo dejas vacío, se ignorará.",
                    required=True
                ),
                
                "Factor_Pack": st.column_config.NumberColumn(
                    "📦 Unids/Pack", 
                    help="¿Cuántas unidades trae este item? Si es una caja de 12 latas, pon 12.",
                    min_value=1, step=1, default=1
                ),
                
                "Cantidad_Facturada": st.column_config.NumberColumn("Cant. Factura", disabled=True),
                "Costo_Pack_Factura": st.column_config.NumberColumn("Costo Pack", format="$%.2f", disabled=True),
                "ID_Proveedor": None, # Ocultar
                "Proveedor_Nombre": None # Ocultar
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )

        # Previsualización de cálculos
        st.markdown("---")
        st.markdown("##### 👁️ Previsualización de Ingreso al Inventario")
        
        # Calculamos columnas visuales para que el usuario entienda qué va a pasar
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

        col1, col2 = st.columns([1, 4])
        if col1.button("Cancelar"):
            st.session_state.paso = 1
            st.rerun()
            
        if col2.button("💾 Procesar, Aprender y Actualizar", type="primary"):
            with st.spinner("Guardando memoria y actualizando stock..."):
                # 1. Guardar Aprendizaje (Mapeo)
                # Convertir a dict para la función
                datos_aprendizaje = edited_df.to_dict('records')
                guardar_aprendizaje(ws_map, datos_aprendizaje)
                
                # 2. Actualizar Inventario
                exito, logs = procesar_inventario(ws_inv, edited_df)
                
                if exito:
                    st.success("✅ ¡Proceso completado!")
                    with st.expander("Ver reporte detallado"):
                        for l in logs: st.write(l)
                    time.sleep(5)
                    st.session_state.paso = 1
                    st.rerun()
                else:
                    st.error("Hubo errores en la actualización:")
                    for l in logs: st.error(l)

if __name__ == "__main__":
    main()
