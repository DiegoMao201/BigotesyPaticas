import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime
import math
from BigotesyPaticas import normalizar_id_producto

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS (NEXUS PRO THEME)
# ==========================================

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

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    .stApp {{ background-color: {COLOR_FONDO}; font-family: 'Inter', sans-serif; }}
    
    h1, h2, h3 {{ color: {COLOR_PRIMARIO}; font-weight: 700; }}
    
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

    .metric-container {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }}
    .metric-card {{
        background-color: {COLOR_BLANCO};
        border-radius: 12px;
        padding: 20px;
        width: 30%;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid {COLOR_ACENTO};
        text-align: center;
    }}
    .metric-label {{ color: #64748b; font-size: 0.85rem; text-transform: uppercase; font-weight: 600; margin-bottom: 5px; }}
    .metric-value {{ color: {COLOR_PRIMARIO}; font-size: 1.5rem; font-weight: 800; }}

    .stButton>button {{ border-radius: 8px; font-weight: bold; height: 3rem; transition: all 0.3s ease; }}
    div[data-testid="stExpander"] {{ background-color: {COLOR_BLANCO}; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: none; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UTILIDADES MATEMÁTICAS
# ==========================================

def normalizar_str(valor):
    if pd.isna(valor) or valor == "": return ""
    return str(valor).strip().upper()

def clean_currency(val):
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').strip()
        if not val: return 0.0
        try:
            if ',' in val and '.' in val:
                if val.find('.') < val.find(','): val = val.replace('.', '').replace(',', '.')
                else: val = val.replace(',', '')
            elif ',' in val: val = val.replace(',', '.')
            return float(val)
        except: return 0.0
    return 0.0

def sanitizar_para_sheet(val):
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    return val

def redondear_centena(valor):
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
        
        try: ws_inv = sh.worksheet("Inventario")
        except: st.error("Falta hoja 'Inventario'"); st.stop()
        
        try: ws_map = sh.worksheet("Maestro_Proveedores")
        except: 
            ws_map = sh.add_worksheet("Maestro_Proveedores", 1000, 9)
            ws_map.append_row(["ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Factor_Pack", "Ultima_Actualizacion", "Email", "Costo_Proveedor", "Ultimo_IVA"])

        try: ws_hist = sh.worksheet("Historial_Recepciones")
        except:
            ws_hist = sh.add_worksheet("Historial_Recepciones", 1000, 7)
            ws_hist.append_row(["Fecha", "Folio", "Proveedor", "Items", "Total", "Usuario", "Estado"])
        
        try: ws_gas = sh.worksheet("Gastos")
        except:
            ws_gas = sh.add_worksheet("Gastos", 1000, 8)
            ws_gas.append_row(["ID_Gasto","Fecha","Tipo_Gasto","Categoria","Descripcion","Monto","Metodo_Pago","Banco_Origen"])

        return sh, ws_inv, ws_map, ws_hist, ws_gas
    except Exception as e:
        st.error(f"Error Conexión Sheets: {e}")
        st.stop()

# ==========================================
# 4. CEREBRO Y MEMORIA
# ==========================================

@st.cache_data(ttl=60)
def cargar_cerebro(_ws_inv, _ws_map):
    try:
        d_inv = _ws_inv.get_all_records()
        df_inv = pd.DataFrame(d_inv)
        col_id = next((c for c in df_inv.columns if 'ID' in c or 'SKU' in c), 'ID_Producto')
        col_nm = next((c for c in df_inv.columns if 'Nombre' in c), 'Nombre')
        df_inv['Display'] = df_inv[col_id].astype(str) + " | " + df_inv[col_nm].astype(str)
        lista_prods = sorted(df_inv['Display'].unique().tolist())
        lista_prods.insert(0, "NUEVO (Crear Producto)")
        dict_prods = pd.Series(df_inv['Display'].values, index=df_inv[col_id].apply(normalizar_id_producto)).to_dict()
    except:
        lista_prods, dict_prods = ["NUEVO (Crear Producto)"], {}

    memoria = {}
    try:
        d_map = _ws_map.get_all_records()
        for r in d_map:
            k = f"{normalizar_str(r.get('ID_Proveedor'))}_{normalizar_str(r.get('SKU_Proveedor'))}"
            iva_guardado = r.get('Ultimo_IVA')
            iva_val = int(float(iva_guardado)) if iva_guardado in [0, 5, 19, "0", "5", "19", 0.0, 5.0, 19.0] else 0
            memoria[k] = {
                'SKU_Interno': normalizar_str(r.get('SKU_Interno')),
                'Factor': float(r.get('Factor_Pack', 1)) if r.get('Factor_Pack') else 1.0,
                'IVA_Aprendido': iva_val
            }
    except: pass

    return lista_prods, dict_prods, memoria

# ==========================================
# 5. PARSER XML COLOMBIA
# ==========================================

def parsear_xml_colombia(archivo):
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        ns_map = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }

        invoice_root = root
        if 'AttachedDocument' in root.tag:
            desc_node = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
            if desc_node is not None and desc_node.text and "<Invoice" in desc_node.text:
                xml_string = desc_node.text.strip()
                xml_string = xml_string[xml_string.find("<Invoice"):]
                invoice_root = ET.fromstring(xml_string)

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

        items = []
        lines = invoice_root.findall('.//cac:InvoiceLine', ns)
        
        for line in lines:
            try:
                qty = float(line.find('cbc:InvoicedQuantity', ns).text)
                price_node = line.find('.//cac:Price/cbc:PriceAmount', ns)
                base_price = float(price_node.text) if price_node is not None else 0.0
                
                discount_amount = 0.0
                allowances = line.findall('.//cac:AllowanceCharge', ns)
                if allowances:
                    first_allowance = allowances[0] 
                    if first_allowance.find('cbc:ChargeIndicator', ns).text == 'false':
                        val = first_allowance.find('cbc:Amount', ns).text
                        discount_amount = float(val) if val else 0.0

                final_base_price = base_price - discount_amount
                
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
# 6. LÓGICA DE GUARDADO
# ==========================================

def procesar_guardado(ws_map, ws_inv, ws_hist, ws_gas, df_final, meta_xml, info_pago):
    try:
        fecha = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        inv_data = ws_inv.get_all_values()
        header = inv_data[0]
        
        try:
            idx_id = 0 
            idx_nombre = next(i for i, c in enumerate(header) if 'Nombre' in c)
            idx_stock = next(i for i, c in enumerate(header) if 'Stock' in c)
            idx_costo = next(i for i, c in enumerate(header) if 'Costo' in c)
            idx_precio = next(i for i, c in enumerate(header) if 'Precio' in c)
        except:
            idx_nombre = 1; idx_stock = 2; idx_costo = 3; idx_precio = 4

        mapa_filas = {normalizar_id_producto(r[idx_id]): i+1 for i, r in enumerate(inv_data)}

        new_mappings = []
        updates = []
        appends = []
        logs = []
        
        total_items_factura = len(df_final)
        
        for index_row, row in df_final.iterrows():
            sel = row['SKU_Interno_Seleccionado']
            sku_prov_factura = str(row['SKU_Proveedor'])
            
            factor = float(row['Factor_Pack']) if row['Factor_Pack'] > 0 else 1.0
            cant_recibida_xml = float(row['Cantidad_Recibida'])
            iva_seleccionado = float(row['IVA_Porcentaje']) 
            costo_base_xml = float(row['Costo_Base_Unitario'])
            
            # Prorratear transporte y descuento equitativamente entre los items para no inflar el unitario
            prorrateo_transporte = (float(info_pago.get("Transporte", 0.0)) / total_items_factura) if total_items_factura > 0 else 0
            prorrateo_descuento = (float(info_pago.get("Descuento", 0.0)) / total_items_factura) if total_items_factura > 0 else 0
            
            costo_base_unitario_real = costo_base_xml + prorrateo_transporte - prorrateo_descuento
            costo_base_unitario_real = costo_base_unitario_real / factor
            
            iva_monto_unitario = costo_base_unitario_real * (iva_seleccionado / 100.0)
            costo_neto_final = costo_base_unitario_real + iva_monto_unitario
            cant_total_unidades = cant_recibida_xml * factor
            
            precio_sugerido_calculado = costo_neto_final / 0.85
            precio_sugerido_redondeado = redondear_centena(precio_sugerido_calculado)

            final_internal_id = ""
            es_producto_nuevo = False
            
            if "NUEVO" in sel:
                es_producto_nuevo = True
                if sku_prov_factura and sku_prov_factura != "S/C": final_internal_id = sku_prov_factura
                else: final_internal_id = f"N-{int(time.time())}-{index_row}"
            else:
                final_internal_id = sel.split(" | ")[0].strip()
            
            if sku_prov_factura != "S/C":
                costo_pack = costo_neto_final * factor
                new_mappings.append([
                    str(meta_xml['ID_Proveedor']), str(meta_xml['Proveedor']), sku_prov_factura,
                    final_internal_id, factor, fecha, "", costo_pack, iva_seleccionado 
                ])
            
            if es_producto_nuevo:
                new_row = [""] * len(header)
                new_row[0] = final_internal_id 
                # AQUÍ USAMOS EL NUEVO NOMBRE EDITADO (O LA DESCRIPCIÓN ORIGINAL SI LO DEJARON IGUAL)
                if idx_nombre < len(new_row): new_row[idx_nombre] = row.get('Nombre_Inventario', row['Descripcion'])
                if idx_stock < len(new_row): new_row[idx_stock] = sanitizar_para_sheet(cant_total_unidades)
                if idx_costo < len(new_row): new_row[idx_costo] = sanitizar_para_sheet(costo_neto_final)
                if idx_precio < len(new_row): new_row[idx_precio] = sanitizar_para_sheet(precio_sugerido_redondeado)

                if 'ID_Producto_Norm' in header:
                    idx_norm = header.index('ID_Producto_Norm')
                    new_row[idx_norm] = normalizar_id_producto(final_internal_id)

                if 'Categoria' in header:
                    idx_cat = header.index('Categoria')
                    new_row[idx_cat] = row.get('Categoria', 'Sin Categoría')
                if 'Iva' in header:
                    idx_iva = header.index('Iva')
                    new_row[idx_iva] = iva_seleccionado

                appends.append(new_row)
                logs.append(f"✨ CREADO: {row.get('Nombre_Inventario', row['Descripcion'])} | Precio: ${precio_sugerido_redondeado:,.0f} (IVA {iva_seleccionado}%)")
                mapa_filas[normalizar_str(final_internal_id)] = len(inv_data) + len(appends)
            else:
                sku_norm = normalizar_id_producto(final_internal_id)
                if sku_norm in mapa_filas:
                    fila = mapa_filas[sku_norm]
                    row_actual = inv_data[fila-1]
                    
                    try: stock_curr = clean_currency(row_actual[idx_stock])
                    except: stock_curr = 0.0
                    try: precio_curr = clean_currency(row_actual[idx_precio])
                    except: precio_curr = 0.0
                    
                    new_stock = stock_curr + cant_total_unidades
                    
                    updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_stock+1), 'values': [[new_stock]]})
                    updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_costo+1), 'values': [[costo_neto_final]]})
                    
                    if precio_sugerido_redondeado > precio_curr:
                        updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_precio+1), 'values': [[precio_sugerido_redondeado]]})
                        logs.append(f"📈 SUBIÓ PRECIO: {final_internal_id} a ${precio_sugerido_redondeado:,.0f} (Costo subió)")
                    else:
                        logs.append(f"📦 STOCK: {final_internal_id} (+{cant_total_unidades}) - Precio mantenido")

        if new_mappings: ws_map.append_rows(new_mappings)
        if updates: ws_inv.batch_update(updates)
        if appends: ws_inv.append_rows(appends)

        ws_hist.append_row([
            timestamp, str(meta_xml['Folio']), str(meta_xml['Proveedor']),
            len(df_final), meta_xml['Total'], "Admin Nexus", "OK"
        ])

        try:
            descripcion_gasto = f"[PROV: {meta_xml['Proveedor']}] [REF: {meta_xml['Folio']}] - Compra Mercancía"
            monto_total_gasto = meta_xml['Total'] + float(info_pago.get("Transporte", 0.0)) - float(info_pago.get("Descuento", 0.0))
            ts = int(time.time())
            datos_gasto = [
                f"GAS-{ts}", fecha, "Variable", "Compra Inventario", descripcion_gasto,
                monto_total_gasto, info_pago['Origen'], info_pago['Origen'] 
            ]
            ws_gas.append_row(datos_gasto)
            logs.append(f"💰 Gasto Registrado: ${monto_total_gasto:,.0f} desde {info_pago['Origen']}")
        except Exception as ex_gas:
            logs.append(f"⚠️ Alerta: No se registró en Gastos: {ex_gas}")

        return True, logs

    except Exception as e:
        return False, [f"Error del Sistema: {str(e)}"]

# ==========================================
# 7. INTERFAZ PRINCIPAL (STREAMLIT) - REFACTORIZADA
# ==========================================

def main():
    st.markdown('<div class="main-header">Recepción & Compras 📥</div>', unsafe_allow_html=True)
    
    # === CONTROL DE ESTADOS ===
    if 'step' not in st.session_state: st.session_state.step = 1
    if 'invoice_meta' not in st.session_state: st.session_state.invoice_meta = {}
    if 'invoice_items' not in st.session_state: st.session_state.invoice_items = []

    # Conexión
    sh, ws_inv, ws_map, ws_hist, ws_gas = conectar_sheets()

    # Cargar Cerebro (Inventario)
    if 'lst_prods_cache' not in st.session_state:
        l, d, m = cargar_cerebro(ws_inv, ws_map)
        st.session_state.lst_prods_cache = l
        st.session_state.dct_prods_cache = d
        st.session_state.memoria_cache = m

    # Obtener categorías únicas desde la hoja de inventario
    categorias = []
    try:
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        if 'Categoria' in df_inv.columns:
            categorias = sorted([c for c in df_inv['Categoria'].dropna().unique() if c and c.strip()])
        if not categorias:
            categorias = ["Sin Categoría"]
    except:
        categorias = ["Sin Categoría"]

    # ==========================================
    # PASO 1: CARGA DE DATOS (XML O MANUAL)
    # ==========================================
    if st.session_state.step == 1:
        st.markdown('<div class="sub-header">Selecciona el método de ingreso</div>', unsafe_allow_html=True)
        
        tab_xml, tab_manual = st.tabs(["📂 Cargar XML (Factura Electrónica)", "✍️ Ingreso Manual"])
        
        # OPCIÓN A: XML
        with tab_xml:
            st.info("Arrastra tu Factura XML de la DIAN para autocompletar.")
            uploaded = st.file_uploader("📂 Sube tu Factura XML DIAN aquí", type=['xml'], key="xml_upl")
            
            if uploaded:
                with st.spinner("🤖 Analizando XML y Consultando Memoria..."):
                    data = parsear_xml_colombia(uploaded)
                    if not data:
                        st.error("❌ El XML no pudo ser leído. Verifica que sea una factura DIAN válida o consulta soporte.")
                        st.stop()
                    
                    # Guardar en sesión y avanzar
                    st.session_state.invoice_meta = {
                        "Proveedor": data["Proveedor"], "ID_Proveedor": data["ID_Proveedor"],
                        "Folio": data["Folio"], "Total": data["Total"]
                    }
                    st.session_state.invoice_items = data["Items"]
                    st.session_state.step = 2
                    st.rerun()

        # OPCIÓN B: MANUAL
        with tab_manual:
            with st.form("form_manual_ingreso"):
                c1, c2, c3 = st.columns(3)
                prov_man = c1.text_input("Proveedor", placeholder="Ej: Italcol")
                nit_man = c2.text_input("NIT / ID Proveedor", value="000")
                folio_man = c3.text_input("No. Factura", placeholder="FAC-123")
                
                st.markdown("---")
                st.write("📝 **Items de la Factura**")
                
                df_template = pd.DataFrame([{
                    "Descripción": "", "Cantidad": 1, "Costo_Total_Línea": 0.0
                }])

                edited_manual = st.data_editor(
                    df_template, num_rows="dynamic", use_container_width=True,
                    column_config={
                        "Descripción": st.column_config.TextColumn("Descripción del Producto", required=True),
                        "Cantidad": st.column_config.NumberColumn("Cant.", min_value=1),
                        "Costo_Total_Línea": st.column_config.NumberColumn("Costo Total ($)", min_value=0.0)
                    }
                )

                submit_manual = st.form_submit_button("Siguiente Paso ➡️")
                
                if submit_manual:
                    if not prov_man or not folio_man:
                        st.error("⚠️ Falta Proveedor o Factura.")
                    else:
                        items_std = []
                        total_manual = 0.0
                        for i, row in edited_manual.iterrows():
                            if row["Descripción"]:
                                qty = float(row["Cantidad"])
                                c_tot = float(row["Costo_Total_Línea"])
                                base_unit = (c_tot / qty) if qty > 0 else 0.0
                                total_manual += c_tot
                                
                                items_std.append({
                                    'SKU_Proveedor': "S/C",
                                    'Descripcion': row["Descripción"],
                                    'Cantidad': qty,
                                    'Costo_Base_Unitario': base_unit
                                })
                        
                        st.session_state.invoice_meta = {
                            "Proveedor": prov_man, "ID_Proveedor": nit_man,
                            "Folio": folio_man, "Total": total_manual
                        }
                        st.session_state.invoice_items = items_std
                        st.session_state.step = 2
                        st.rerun()

    # ==========================================
    # PASO 2: REVISIÓN, MAPEO Y GUARDADO
    # ==========================================
    elif st.session_state.step == 2:
        st.markdown('<div class="sub-header">Revisión, Mapeo y Finanzas</div>', unsafe_allow_html=True)
        
        meta = st.session_state.invoice_meta
        
        # Mostrar resumen de cabecera
        st.info(f"🏢 **Proveedor:** {meta['Proveedor']} | 📄 **Folio:** {meta['Folio']} | 💰 **Total Base:** ${meta['Total']:,.2f}")
        
        if st.button("⬅️ Cancelar y Volver"):
            st.session_state.step = 1
            st.rerun()

        st.markdown("### 1. Asignar al Inventario Interno")
        
        # --- LÓGICA DE MEMORIA (CEREBRO) ---
        df_revision_data = []
        
        for item in st.session_state.invoice_items:
            # 1. Armar la clave de memoria idéntica a como se guarda: NIT_SKU
            nit_prov_norm = normalizar_str(meta['ID_Proveedor'])
            sku_prov_norm = normalizar_str(item.get('SKU_Proveedor', 'S/C'))
            clave_memoria = f"{nit_prov_norm}_{sku_prov_norm}"
            
            # 2. Valores por defecto
            prod_interno_val = "NUEVO (Crear Producto)"
            iva_val = 0
            factor_val = 1.0
            
            # 3. Buscar en el cerebro si ya lo conocemos
            if clave_memoria in st.session_state.memoria_cache:
                recuerdo = st.session_state.memoria_cache[clave_memoria]
                sku_interno_recordado = recuerdo['SKU_Interno']
                
                # Buscar cómo se llama en la lista desplegable actual de inventario
                match = next((p for p in st.session_state.lst_prods_cache if p.startswith(sku_interno_recordado + " |")), None)
                
                if match:
                    prod_interno_val = match
                
                iva_val = recuerdo['IVA_Aprendido']
                factor_val = recuerdo['Factor']

            # 4. Construir la fila (SE AGREGA LA COLUMNA Nombre_Inventario EDITABLE)
            df_revision_data.append({
                "SKU_Proveedor": item.get('SKU_Proveedor', 'S/C'),
                "Descripcion": item.get('Descripcion', ''),
                "Nombre_Inventario": item.get('Descripcion', ''), # <--- COLUMNA PARA EDITAR EL NOMBRE NUEVO
                "Cantidad": item.get('Cantidad', 1),
                "Costo_Base_Unitario": item.get('Costo_Base_Unitario', 0.0),
                "📌 Producto_Interno": prod_interno_val,
                "IVA_%": iva_val,
                "Factor_Pack": factor_val,
                "Categoría": "Sin Categoría"
            })

        df_revision = pd.DataFrame(df_revision_data)
        
        edited_revision = st.data_editor(
            df_revision,
            use_container_width=True,
            hide_index=True,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("SKU Prov.", disabled=True),
                "Descripcion": st.column_config.TextColumn("Desc. Factura", disabled=True),
                "Nombre_Inventario": st.column_config.TextColumn("✍️ Nombre a Crear (Editable)", disabled=False, width="medium"),
                "Cantidad": st.column_config.NumberColumn("Cant.", disabled=True),
                "Costo_Base_Unitario": st.column_config.NumberColumn("Costo Unit. Base", format="$%f", disabled=True),
                "📌 Producto_Interno": st.column_config.SelectboxColumn("📌 Asociar a:", options=st.session_state.lst_prods_cache, width="large", required=True),
                "IVA_%": st.column_config.SelectboxColumn("IVA %", options=[0, 5, 19], required=True),
                "Factor_Pack": st.column_config.NumberColumn("Factor/Caja", min_value=1.0),
                # Cambia a SelectboxColumn con las categorías del inventario
                "Categoría": st.column_config.SelectboxColumn("Categoría", options=categorias, required=True)
            }
        )

        st.markdown("---")
        st.markdown("### 2. Liquidación y Pago")
        
        c1, c2, c3 = st.columns(3)
        c_transporte = c1.number_input("Costo Transporte ($)", min_value=0.0, value=0.0)
        c_descuento = c2.number_input("Descuento Total ($)", min_value=0.0, value=0.0)
        origen_pago = c3.selectbox("Cuenta de Egreso (Gastos)", ["Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata", "Efectivo", "Caja General", "Crédito Proveedor (CxP)"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Confirmar y Guardar en Base de Datos", type="primary", use_container_width=True):
            
            df_to_save = edited_revision.copy()
            df_to_save = df_to_save.rename(columns={
                "📌 Producto_Interno": "SKU_Interno_Seleccionado",
                "IVA_%": "IVA_Porcentaje",
                "Cantidad": "Cantidad_Recibida"
            })
            
            info_pago = {
                "Origen": origen_pago,
                "Transporte": float(c_transporte),
                "Descuento": float(c_descuento)
            }
            
            with st.spinner("Guardando en Google Sheets..."):
                ok, logs = procesar_guardado(ws_map, ws_inv, ws_hist, ws_gas, df_to_save, meta, info_pago)
            
            if ok:
                st.success("¡Compra registrada correctamente!")
                st.balloons()
                with st.expander("Ver bitácora de operaciones"):
                    for l in logs: st.text(l)
                
                # Resetear la sesión
                st.session_state.invoice_meta = {}
                st.session_state.invoice_items = []
                
                if st.button("Volver al Inicio"):
                    st.session_state.step = 1
                    # Limpiamos el cache para que vuelva a leer la hoja fresca la próxima vez
                    st.cache_data.clear() 
                    st.rerun()
            else:
                st.error("Error guardando datos.")
                for l in logs: st.error(l)

if __name__ == "__main__":
    main()