import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime
import math

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS (NEXUS PRO THEME)
# ==========================================

# Paleta de Colores Nexus Pro
COLOR_PRIMARIO = "#187f77"      # Cian Oscuro
COLOR_SECUNDARIO = "#125e58"    # Variante oscura
COLOR_ACENTO = "#f5a641"        # Naranja
COLOR_FONDO = "#f8f9fa"         # Gris claro
COLOR_BLANCO = "#ffffff"

st.set_page_config(
    page_title="Compras & Recepción | Nexus Pro", 
    page_icon="📥", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS idénticos a tu app principal
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    .stApp {{ background-color: {COLOR_FONDO}; font-family: 'Inter', sans-serif; }}
    
    h1, h2, h3 {{ color: {COLOR_PRIMARIO}; font-weight: 700; }}
    
    /* Header Principal */
    .main-header {{ 
        font-size: 2.5rem; 
        font-weight: 800; 
        color: {COLOR_PRIMARIO}; 
        margin-top: 1rem;
        margin-bottom: 0.5rem; 
        text-align: center; 
    }}
    
    .sub-header {{ 
        font-size: 1.1rem; 
        color: #64748b; 
        margin-bottom: 2rem; 
        text-align: center; 
    }}

    /* Tarjetas Métricas */
    .metric-container {{
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-bottom: 30px;
    }}

    .metric-card {{
        background-color: {COLOR_BLANCO};
        border-radius: 12px;
        padding: 20px;
        width: 30%;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid {COLOR_ACENTO};
        text-align: center;
    }}

    .metric-label {{
        color: #64748b;
        font-size: 0.85rem;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 5px;
    }}

    .metric-value {{
        color: {COLOR_PRIMARIO};
        font-size: 1.5rem;
        font-weight: 800;
    }}

    /* Botones */
    .stButton>button {{
        border-radius: 8px;
        font-weight: bold;
        height: 3rem;
        transition: all 0.3s ease;
    }}
    
    div[data-testid="stExpander"] {{ 
        background-color: {COLOR_BLANCO}; 
        border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        border: none;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UTILIDADES MATEMÁTICAS
# ==========================================

def normalizar_str(valor):
    """Limpieza de strings para búsquedas (Mayúsculas, sin espacios extra)."""
    if pd.isna(valor) or valor == "":
        return ""
    return str(valor).strip().upper()

def clean_currency(val):
    """Convierte strings de dinero ($1.000,00) a float."""
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').strip()
        if not val: return 0.0
        try:
            # Lógica para detectar formato latino (1.000,00) vs gringo (1,000.00)
            if ',' in val and '.' in val:
                if val.find('.') < val.find(','): # 1.000,00
                    val = val.replace('.', '').replace(',', '.')
                else: # 1,000.00
                    val = val.replace(',', '')
            elif ',' in val: 
                val = val.replace(',', '.')
            return float(val)
        except:
            return 0.0
    return 0.0

def sanitizar_para_sheet(val):
    """Tipos numpy a nativos python."""
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    return val

def redondear_centena(valor):
    """Redondea hacia ARRIBA a la centena más cercana (Ej: 1420 -> 1500)."""
    if not valor: return 0.0
    return math.ceil(valor / 100.0) * 100.0

# ==========================================
# 3. CONEXIÓN A GOOGLE SHEETS
# ==========================================

@st.cache_resource(ttl=600)
def conectar_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración en secrets.toml")
            st.stop()
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Hojas necesarias
        try: ws_inv = sh.worksheet("Inventario")
        except: st.error("Falta hoja 'Inventario'"); st.stop()
        
        try: ws_map = sh.worksheet("Maestro_Proveedores")
        except: 
            ws_map = sh.add_worksheet("Maestro_Proveedores", 1000, 7)
            ws_map.append_row(["ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Factor_Pack", "Ultima_Actualizacion", "Ultimo_IVA"])

        try: ws_hist = sh.worksheet("Historial_Recepciones")
        except:
            ws_hist = sh.add_worksheet("Historial_Recepciones", 1000, 7)
            ws_hist.append_row(["Fecha", "Folio", "Proveedor", "Items", "Total", "Usuario", "Estado"])
        
        try: ws_gas = sh.worksheet("Gastos")
        except:
            ws_gas = sh.add_worksheet("Gastos", 1000, 8)
            ws_gas.append_row(["Timestamp", "Fecha", "Tipo", "Categoria", "Descripcion", "Monto", "Responsable", "Banco_Origen"])

        return sh, ws_inv, ws_map, ws_hist, ws_gas
    except Exception as e:
        st.error(f"Error Conexión Sheets: {e}")
        st.stop()

# ==========================================
# 4. CEREBRO Y MEMORIA (Carga IVA y SKU)
# ==========================================

@st.cache_data(ttl=60)
def cargar_cerebro(_ws_inv, _ws_map):
    # 1. Cargar Inventario Interno
    try:
        d_inv = _ws_inv.get_all_records()
        df_inv = pd.DataFrame(d_inv)
        
        # Columnas clave
        cols = df_inv.columns
        col_id = next((c for c in cols if 'ID' in c or 'SKU' in c), 'ID_Producto')
        col_nm = next((c for c in cols if 'Nombre' in c), 'Nombre')

        # Crear lista visual
        df_inv['Display'] = df_inv[col_id].astype(str) + " | " + df_inv[col_nm].astype(str)
        lista_prods = sorted(df_inv['Display'].unique().tolist())
        lista_prods.insert(0, "NUEVO (Crear Producto)")
        
        # Diccionario para búsqueda rápida
        dict_prods = pd.Series(df_inv['Display'].values, index=df_inv[col_id].apply(normalizar_str)).to_dict()
    except:
        lista_prods, dict_prods = ["NUEVO (Crear Producto)"], {}

    # 2. Cargar Mapeo Proveedores (Memoria de IVA y Factor)
    memoria = {}
    try:
        d_map = _ws_map.get_all_records()
        # Asegurarnos de que existan las columnas aunque la hoja sea vieja
        for r in d_map:
            # Clave: NIT_PROVEEDOR + SKU_PROVEEDOR
            k = f"{normalizar_str(r.get('ID_Proveedor'))}_{normalizar_str(r.get('SKU_Proveedor'))}"
            
            # Recuperar IVA aprendido
            iva_guardado = r.get('Ultimo_IVA')
            if iva_guardado in [0, 5, 19, "0", "5", "19", 0.0, 5.0, 19.0]:
                iva_val = int(float(iva_guardado))
            else:
                iva_val = 0 # Default si no sabe
            
            memoria[k] = {
                'SKU_Interno': normalizar_str(r.get('SKU_Interno')),
                'Factor': float(r.get('Factor_Pack', 1)) if r.get('Factor_Pack') else 1.0,
                'IVA_Aprendido': iva_val
            }
    except: pass

    return lista_prods, dict_prods, memoria

# ==========================================
# 5. PARSER XML COLOMBIA (UBL 2.1)
# ==========================================

def parsear_xml_colombia(archivo):
    """
    Lee XML UBL 2.1. Extrae precio BASE (sin impuestos).
    La UI se encargará de asignar el impuesto correcto.
    """
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        ns_map = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }

        # 1. AttachedDocument (Contenedor DIAN)
        invoice_root = root
        if 'AttachedDocument' in root.tag:
            desc_node = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
            if desc_node is not None and desc_node.text and "<Invoice" in desc_node.text:
                xml_string = desc_node.text.strip()
                xml_string = xml_string[xml_string.find("<Invoice"):]
                invoice_root = ET.fromstring(xml_string)

        # 2. Header
        ns = ns_map 
        try:
            prov_node = invoice_root.find('.//cac:AccountingSupplierParty/cac:Party', ns)
            prov_tax = prov_node.find('.//cac:PartyTaxScheme', ns)
            nombre_prov = prov_tax.find('cbc:RegistrationName', ns).text
            nit_prov = prov_tax.find('cbc:CompanyID', ns).text
        except:
            nombre_prov = "Proveedor Desconocido"
            nit_prov = "000000"

        try: folio = invoice_root.find('cbc:ID', ns).text
        except: folio = "S/F"

        try: total_pagar_factura = float(invoice_root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns).text)
        except: total_pagar_factura = 0.0

        # 3. Items
        items = []
        lines = invoice_root.findall('.//cac:InvoiceLine', ns)
        
        for line in lines:
            try:
                qty = float(line.find('cbc:InvoicedQuantity', ns).text)
                
                # Precio Base (Antes de IVA)
                price_node = line.find('.//cac:Price/cbc:PriceAmount', ns)
                base_price = float(price_node.text) if price_node is not None else 0.0
                
                # Descuentos a nivel de línea
                discount_amount = 0.0
                allowances = line.findall('.//cac:AllowanceCharge', ns)
                if allowances:
                    first_allowance = allowances[0] 
                    is_charge = first_allowance.find('cbc:ChargeIndicator', ns).text
                    if is_charge == 'false': # Es descuento
                        val = first_allowance.find('cbc:Amount', ns).text
                        discount_amount = float(val) if val else 0.0

                # Precio Base Neto = Precio Lista - Descuento (Aún sin IVA)
                final_base_price = base_price - discount_amount
                
                # Descripción y Referencia
                item_node = line.find('cac:Item', ns)
                desc = item_node.find('cbc:Description', ns).text
                
                sku_prov = "S/C"
                std_id = item_node.find('.//cac:StandardItemIdentification/cbc:ID', ns)
                seller_id = item_node.find('.//cac:SellersItemIdentification/cbc:ID', ns)
                
                if std_id is not None and std_id.text: sku_prov = std_id.text
                elif seller_id is not None: sku_prov = seller_id.text
                
                items.append({
                    'SKU_Proveedor': sku_prov,
                    'Descripcion': desc,
                    'Cantidad': qty,
                    'Costo_Base_Unitario': final_base_price 
                })
            except: continue

        return {
            'Proveedor': nombre_prov,
            'ID_Proveedor': nit_prov,
            'Folio': folio,
            'Total': total_pagar_factura,
            'Items': items
        }

    except Exception as e:
        st.error(f"Error parseando XML: {e}")
        return None

# ==========================================
# 6. LÓGICA DE GUARDADO Y APRENDIZAJE
# ==========================================

def procesar_guardado(ws_map, ws_inv, ws_hist, ws_gas, df_final, meta_xml, info_pago):
    """
    Actualiza Inventario, Precios con Fórmula / 0.85, Memoria (IVA) y Gasto.
    """
    try:
        fecha = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # --- A. LEER INVENTARIO ACTUAL ---
        inv_data = ws_inv.get_all_values()
        header = inv_data[0]
        
        # Detectar columnas dinámicamente
        try:
            idx_id = 0 
            idx_nombre = next(i for i, c in enumerate(header) if 'Nombre' in c)
            idx_stock = next(i for i, c in enumerate(header) if 'Stock' in c)
            idx_costo = next(i for i, c in enumerate(header) if 'Costo' in c)
            idx_precio = next(i for i, c in enumerate(header) if 'Precio' in c)
        except:
            # Fallback estructura estándar
            idx_nombre = 1; idx_stock = 2; idx_costo = 3; idx_precio = 4

        # Mapa de filas para actualizaciones rápidas {ID_PRODUCTO: NUM_FILA}
        mapa_filas = {normalizar_str(r[idx_id]): i+1 for i, r in enumerate(inv_data)}

        new_mappings = []
        updates = []
        appends = []
        logs = []
        
        # --- B. BUCLE PRINCIPAL (INVENTARIO) ---
        for index_row, row in df_final.iterrows():
            sel = row['SKU_Interno_Seleccionado']
            sku_prov_factura = str(row['SKU_Proveedor'])
            
            # Datos Numéricos de la Interfaz
            factor = float(row['Factor_Pack']) if row['Factor_Pack'] > 0 else 1.0
            cant_recibida_xml = float(row['Cantidad_Recibida'])
            iva_seleccionado = float(row['IVA_Porcentaje']) # 0, 5, 19
            costo_base_xml = float(row['Costo_Base_Unitario'])
            
            # CÁLCULOS MATEMÁTICOS DE COSTO Y PRECIO
            # 1. Costo Base Unitario Real (por unidad suelta)
            costo_base_unitario_real = costo_base_xml + st.session_state.get("c_transporte", 0.0) - st.session_state.get("c_descuento", 0.0)
            costo_base_unitario_real = costo_base_unitario_real / factor
            
            # 2. Costo Neto (Costo Base + IVA)
            iva_monto_unitario = costo_base_unitario_real * (iva_seleccionado / 100.0)
            costo_neto_final = costo_base_unitario_real + iva_monto_unitario
            
            # 3. Cantidad Total a ingresar al stock
            cant_total_unidades = cant_recibida_xml * factor
            
            # 4. Precio de Venta (Fórmula Solicitada: Costo / 0.85)
            # Esto da un margen del 15% sobre el precio de venta (aprox 17.6% sobre costo)
            precio_sugerido_calculado = costo_neto_final / 0.85
            precio_sugerido_redondeado = redondear_centena(precio_sugerido_calculado)

            # --- DETERMINAR ID INTERNO ---
            final_internal_id = ""
            es_producto_nuevo = False
            
            if "NUEVO" in sel:
                es_producto_nuevo = True
                if sku_prov_factura and sku_prov_factura != "S/C":
                    final_internal_id = sku_prov_factura
                else:
                    final_internal_id = f"N-{int(time.time())}-{index_row}"
            else:
                final_internal_id = sel.split(" | ")[0].strip()
            
            # --- APRENDIZAJE: ACTUALIZAR MEMORIA (MAPEO + IVA) ---
            # Si tiene referencia de proveedor, guardamos que este proveedor vende este producto con ESTE IVA
            if sku_prov_factura != "S/C":
                # Borramos mapeos anteriores de este par (opcional, aquí solo agregamos al final, Gspread es append-only fácil)
                # Formato Mapeo: [ID_Prov, Nom_Prov, SKU_Prov, SKU_Int, Factor, Fecha, IVA_Detectado]
                new_mappings.append([
                    str(meta_xml['ID_Proveedor']),
                    str(meta_xml['Proveedor']),
                    sku_prov_factura,
                    final_internal_id, 
                    factor,
                    fecha,
                    iva_seleccionado # <--- AQUÍ GUARDA EL IVA PARA LA PRÓXIMA
                ])
            
            # --- ACTUALIZAR INVENTARIO ---
            if es_producto_nuevo:
                new_row = [""] * len(header)
                new_row[0] = final_internal_id # ID
                if idx_nombre < len(new_row): new_row[idx_nombre] = row['Descripcion']
                if idx_stock < len(new_row): new_row[idx_stock] = sanitizar_para_sheet(cant_total_unidades)
                if idx_costo < len(new_row): new_row[idx_costo] = sanitizar_para_sheet(costo_neto_final)
                if idx_precio < len(new_row): new_row[idx_precio] = sanitizar_para_sheet(precio_sugerido_redondeado)
                
                appends.append(new_row)
                logs.append(f"✨ CREADO: {row['Descripcion']} | Precio: ${precio_sugerido_redondeado:,.0f} (IVA {iva_seleccionado}%)")
                
                # Actualizar mapa temporal por si se repite en el mismo XML
                mapa_filas[normalizar_str(final_internal_id)] = len(inv_data) + len(appends)
            
            else:
                sku_norm = normalizar_str(final_internal_id)
                if sku_norm in mapa_filas:
                    fila = mapa_filas[sku_norm]
                    row_actual = inv_data[fila-1]
                    
                    try: stock_curr = clean_currency(row_actual[idx_stock])
                    except: stock_curr = 0.0
                    try: precio_curr = clean_currency(row_actual[idx_precio])
                    except: precio_curr = 0.0
                    
                    # Nuevos Valores
                    new_stock = stock_curr + cant_total_unidades
                    
                    # Actualizar Stock
                    updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_stock+1), 'values': [[new_stock]]})
                    # Actualizar Costo (Siempre actualizamos al último costo de reposición)
                    updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_costo+1), 'values': [[costo_neto_final]]})
                    
                    # Actualizar Precio: Solo si el nuevo sugerido es MAYOR al actual (para no perder margen)
                    # Opcional: Puedes forzar siempre el nuevo precio si prefieres. Aquí uso lógica "Smart"
                    if precio_sugerido_redondeado > precio_curr:
                        updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_precio+1), 'values': [[precio_sugerido_redondeado]]})
                        logs.append(f"📈 SUBIÓ PRECIO: {final_internal_id} a ${precio_sugerido_redondeado:,.0f} (Costo subió)")
                    else:
                        logs.append(f"📦 STOCK: {final_internal_id} (+{cant_total_unidades}) - Precio mantenido")

        # --- C. EJECUTAR ESCRITURAS ---
        if new_mappings: ws_map.append_rows(new_mappings)
        if updates: ws_inv.batch_update(updates)
        if appends: ws_inv.append_rows(appends)

        # --- D. HISTORIAL ---
        ws_hist.append_row([
            timestamp,
            str(meta_xml['Folio']),
            str(meta_xml['Proveedor']),
            len(df_final),
            meta_xml['Total'],
            "Admin Nexus",
            "OK"
        ])

        # --- E. REGISTRAR GASTO (Costo de Venta) ---
        try:
            descripcion_gasto = f"[PROV: {meta_xml['Proveedor']}] [REF: {meta_xml['Folio']}] - Compra Mercancía"
            monto_total_gasto = meta_xml['Total'] + float(info_pago.get("Transporte", 0.0)) - float(info_pago.get("Descuento", 0.0))
            datos_gasto = [
                timestamp,
                fecha,
                "Costo de Venta",    # Tipo fijo para separar en P&L
                "Compra Inventario", # Categoría
                descripcion_gasto,
                monto_total_gasto,   # Monto Total Factura
                "Módulo Compras",
                info_pago['Origen']  # Banco seleccionado
            ]
            ws_gas.append_row(datos_gasto)
            logs.append(f"💰 Gasto Registrado: ${monto_total_gasto:,.0f} desde {info_pago['Origen']}")
        except Exception as ex_gas:
            logs.append(f"⚠️ Alerta: No se registró en Gastos: {ex_gas}")

        return True, logs

    except Exception as e:
        return False, [f"Error del Sistema: {str(e)}"]

# ==========================================
# 7. INTERFAZ PRINCIPAL (STREAMLIT)
# ==========================================

def main():
    st.markdown('<div class="main-header">Recepción & Compras 📥</div>', unsafe_allow_html=True)
    
    if 'step' not in st.session_state: st.session_state.step = 1
    
    # Conexión
    sh, ws_inv, ws_map, ws_hist, ws_gas = conectar_sheets()

    # --- PASO 1: CARGA DE DATOS ---
    if st.session_state.step == 1:
        st.markdown('<div class="sub-header">Selecciona el método de ingreso</div>', unsafe_allow_html=True)
        
        tab_xml, tab_manual = st.tabs(["📂 Cargar XML (Factura Electrónica)", "✍️ Ingreso Manual"])
        
        # OPCIÓN A: XML
        with tab_xml:
            st.info("Arrastra tu Factura XML de la DIAN para autocompletar.")
            uploaded = st.file_uploader("", type=['xml'], key="xml_upl")
            
            if uploaded:
                with st.spinner("🤖 Analizando XML y Consultando Memoria..."):
                    data = parsear_xml_colombia(uploaded)
                    if not data: st.stop()
                    
                    # Cargar Memoria
                    lst_prods, dct_prods, memoria = cargar_cerebro(ws_inv, ws_map)
                    
                    st.session_state.xml_data = data
                    st.session_state.lst_prods = lst_prods
                    st.session_state.dct_prods = dct_prods
                    st.session_state.memoria = memoria
                    st.session_state.origen_datos = "XML"
                    st.session_state.step = 2
                    st.rerun()

            c1, c2 = st.columns(2)
            c_transporte = c1.number_input("Costo Transporte ($)", min_value=0.0, value=0.0, help="Costo total de transporte para la factura", key="transporte_tab_xml")
            c_descuento = c2.number_input("Descuento Total ($)", min_value=0.0, value=0.0, help="Descuento total aplicado por el proveedor", key="descuento_tab_xml")
            st.session_state.c_transporte = c_transporte
            st.session_state.c_descuento = c_descuento

        # OPCIÓN B: MANUAL
        with tab_manual:
            with st.form("form_manual_header"):
                c1, c2, c3 = st.columns(3)
                prov_man = c1.text_input("Proveedor", placeholder="Ej: Italcol")
                nit_man = c2.text_input("NIT / ID Proveedor", value="000")
                folio_man = c3.text_input("No. Factura", placeholder="FAC-123")
                
                st.markdown("---")
                st.write("📝 **Items de la Factura**")
                
                # Cargar inventario para el selectbox
                if 'lst_prods_cache' not in st.session_state:
                    l, d, m = cargar_cerebro(ws_inv, ws_map)
                    st.session_state.lst_prods_cache = l
                    st.session_state.dct_prods_cache = d
                    st.session_state.memoria_cache = m

                # Data Editor para Manual
                df_template = pd.DataFrame([{
                    "Producto": "", 
                    "Cantidad": 1, 
                    "Costo_Total_Item": 0.0,
                    "IVA_Porc": 0
                }])
                
                edited_manual = st.data_editor(
                    df_template,
                    num_rows="dynamic",
                    column_config={
                        "Producto": st.column_config.SelectboxColumn("Producto", options=st.session_state.lst_prods_cache, width="large"),
                        "Cantidad": st.column_config.NumberColumn("Cant.", min_value=1),
                        "Costo_Total_Item": st.column_config.NumberColumn("Costo Total Línea ($)", min_value=0.0),
                        "IVA_Porc": st.column_config.SelectboxColumn("IVA %", options=[0, 5, 19], required=True)
                    },
                    use_container_width=True
                )

                if st.form_submit_button("Siguiente Paso ➡️"):
                    if not prov_man or not folio_man:
                        st.error("Falta Proveedor o Factura.")
                    else:
                        items_std = []
                        total_manual = 0.0
                        
                        for i, row in edited_manual.iterrows():
                            if row["Producto"]:
                                c_tot = float(row["Costo_Total_Item"])
                                qty = float(row["Cantidad"])
                                iva_p = int(row["IVA_Porc"])
                                
                                # Calcular Costo Base Unitario (Antes de IVA) para estandarizar con XML
                                # Costo Total = (Base + IVA) * Cantidad
                                # Base_Unit = (Total / Cantidad) / (1 + IVA%)
                                c_unit_con_iva = c_tot / qty if qty > 0 else 0
                                c_base_unit = c_unit_con_iva / (1 + (iva_p/100.0))
                                
                                total_manual += c_tot
                                
                                items_std.append({
                                    'SKU_Proveedor': "S/C",
                                    'Descripcion': row["Producto"].split(" | ")[1] if " | " in row["Producto"] else row["Producto"],
                                    'Cantidad': qty,
                                    'Costo_Base_Unitario': c_base_unit,
                                    'IVA_Manual': iva_p # Dato extra para prellenar
                                })
                        
                        if items_std:
                            st.session_state.xml_data = {
                                'Proveedor': prov_man, 'ID_Proveedor': nit_man, 'Folio': folio_man,
                                'Total': total_manual, 'Items': items_std
                            }
                            st.session_state.lst_prods = st.session_state.lst_prods_cache
                            st.session_state.dct_prods = st.session_state.dct_prods_cache
                            st.session_state.memoria = st.session_state.memoria_cache
                            st.session_state.origen_datos = "MANUAL"
                            st.session_state.step = 2
                            st.rerun()

            c1, c2 = st.columns(2)
            c_transporte = c1.number_input("Costo Transporte ($)", min_value=0.0, value=0.0, help="Costo total de transporte para la factura", key="transporte_tab_manual")
            c_descuento = c2.number_input("Descuento Total ($)", min_value=0.0, value=0.0, help="Descuento total aplicado por el proveedor", key="descuento_tab_manual")
            st.session_state.c_transporte = c_transporte
            st.session_state.c_descuento = c_descuento

    # --- PASO 2: VERIFICACIÓN Y ASIGNACIÓN DE IVA ---
    elif st.session_state.step == 2:
        d = st.session_state.xml_data
        mem = st.session_state.memoria
        dct = st.session_state.dct_prods
        origen = st.session_state.origen_datos
        
        # Tarjetas KPIs
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-card">
                    <div class="metric-label">PROVEEDOR</div>
                    <div class="metric-value">{d['Proveedor'][:15]}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">FACTURA</div>
                    <div class="metric-value">{d['Folio']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">TOTAL A PAGAR</div>
                    <div class="metric-value">${d['Total']:,.0f}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Preparar datos para el Editor
        nit_clean = normalizar_str(d['ID_Proveedor'])
        rows_edit = []
        matches = 0
        
        for it in d['Items']:
            sku_prov = it['SKU_Proveedor']
            key = f"{nit_clean}_{normalizar_str(sku_prov)}"
            
            # Valores por defecto
            sel_def = "NUEVO (Crear Producto)"
            fac_def = 1.0
            iva_def = 0 # Por defecto exento
            
            # Si viene manual, usamos lo que puso el usuario
            if origen == "MANUAL":
                iva_def = it.get('IVA_Manual', 0)
                # Buscar nombre en lista
                for p in st.session_state.lst_prods:
                    if it['Descripcion'] in p:
                        sel_def = p; break
            
            # Si viene de XML, usamos MEMORIA
            else:
                if key in mem:
                    # Encontramos este producto de este proveedor antes
                    sku_int = mem[key]['SKU_Interno']
                    if sku_int in dct:
                        sel_def = dct[sku_int]
                        fac_def = mem[key]['Factor']
                        iva_def = mem[key]['IVA_Aprendido'] # <--- AQUÍ RECUPERA EL IVA
                        matches += 1
            
            rows_edit.append({
                "SKU_Proveedor": sku_prov,
                "Descripcion": it['Descripcion'],
                "SKU_Interno_Seleccionado": sel_def,
                "Factor_Pack": fac_def,
                "IVA_Porcentaje": iva_def, # Columna clave para tu lógica
                "Cantidad_XML": it['Cantidad'],
                "Cantidad_Recibida": it['Cantidad'],
                "Costo_Base_Unitario": it['Costo_Base_Unitario']
            })
        
        if origen == "XML":
            if matches > 0: st.success(f"🧠 {matches} productos identificados con su IVA histórico.")
            else: st.info("ℹ️ Asigna los productos e IVAs. El sistema aprenderá para la próxima.")

        # EDITOR PRINCIPAL
        st.markdown("### 🕵️ Verificación de Productos e Impuestos")
        st.caption("Ajusta el IVA (0, 5, 19). El sistema calculará el Costo Neto y aplicará el margen del 15%.")
        
        df_show = pd.DataFrame(rows_edit)
        
        edited = st.data_editor(
            df_show,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True, width="small"),
                "Descripcion": st.column_config.TextColumn("Producto Factura", disabled=True, width="medium"),
                "SKU_Interno_Seleccionado": st.column_config.SelectboxColumn("📌 Tu Inventario", options=st.session_state.lst_prods, required=True, width="large"),
                "Factor_Pack": st.column_config.NumberColumn("Factor", min_value=1.0, help="Unidades por caja"),
                "IVA_Porcentaje": st.column_config.SelectboxColumn("IVA %", options=[0, 5, 19], required=True, help="Selecciona el IVA para calcular el costo real"),
                "Cantidad_XML": st.column_config.NumberColumn("Cant. Fac", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ Recibido"),
                "Costo_Base_Unitario": st.column_config.NumberColumn("Costo Base", format="$%d", disabled=True, help="Precio antes de IVA")
            },
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.markdown("---")
        
        # SECCIÓN DE PAGO (FINANZAS)
        with st.container(border=True):
            st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>💰</span> Origen del Pago", unsafe_allow_html=True)
            col_b, col_msg = st.columns([1, 2])
            origen_pago = col_b.selectbox(
                "Cuenta de Egreso", 
                ["Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata", "Efectivo", "Caja General", "Crédito Proveedor (CxP)"]
            )
            col_msg.info("El total se registrará automáticamente en el módulo de Gastos > Costo de Venta.")

        # BOTONES FINALES
        colA, colB = st.columns([1, 4])
        if colA.button("🔙 Volver"):
            st.session_state.step = 1
            st.rerun()
        
        if colB.button("🚀 PROCESAR ENTRADA", type="primary", use_container_width=True):
            with st.status("⚙️ Aplicando lógica de negocio...", expanded=True):
                st.write("Calculando Costos Netos (Base + IVA)...")
                st.write("Aplicando margen del 15% (Costo / 0.85)...")
                st.write("Aprendiendo preferencias de IVA...")
                
                info_pago = {"Origen": origen_pago, "Transporte": st.session_state.get("c_transporte", 0.0), "Descuento": st.session_state.get("c_descuento", 0.0)}
                
                # LLAMADA A GUARDADO
                ok, logs = procesar_guardado(ws_map, ws_inv, ws_hist, ws_gas, edited, d, info_pago)
                
                if ok:
                    st.write("✅ Inventario Actualizado")
                    st.write("✅ Precios Recalculados")
                    st.write("✅ Gasto Insertado")
                    time.sleep(1)
                    st.balloons()
                    st.success("¡Recepción Completada!")
                    
                    with st.expander("📄 Ver Detalles de la Operación"):
                        for l in logs:
                            if "SUBIÓ" in l: st.warning(l)
                            elif "Gasto" in l: st.info(l)
                            else: st.text(l)
                    
                    if st.button("Nueva Factura"):
                        st.session_state.step = 1
                        st.rerun()
                else:
                    st.error("Error guardando datos.")
                    for l in logs: st.error(l)

def actualizar_stock_gsheets(ws_inv, id_producto, unidades_sumar):
    try:
        id_producto_norm = normalizar_id_producto(id_producto)
        # Busca todas las filas y compara el ID normalizado
        all_rows = ws_inv.get_all_values()
        for idx, row in enumerate(all_rows):
            if idx == 0: continue  # Saltar encabezado
            if normalizar_id_producto(row[0]) == id_producto_norm:
                col_stock = 4
                val_act = ws_inv.cell(idx+1, col_stock).value
                nuevo = float(val_act if val_act else 0) + unidades_sumar
                ws_inv.update_cell(idx+1, col_stock, nuevo)
                break
    except Exception as e:
        print(f"Error stock: {e}")

if __name__ == "__main__":
    main()
