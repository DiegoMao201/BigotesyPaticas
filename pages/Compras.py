import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime
import math
import re

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================

st.set_page_config(
    page_title="Recepción Inteligente Colombia v9.0 FINAL", 
    page_icon="🇨🇴", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS Profesionales
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main-header { font-size: 2.5rem; font-weight: 800; color: #1e3a8a; margin-bottom: 0.5rem; text-align: center; font-family: 'Helvetica', sans-serif; }
    .sub-header { font-size: 1.1rem; color: #64748b; margin-bottom: 2rem; text-align: center; }
    .metric-row { display: flex; justify-content: space-around; margin-bottom: 20px; }
    .metric-item { background: #ffffff; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); width: 30%; border-top: 4px solid #3b82f6; }
    .metric-val { font-size: 1.8rem; font-weight: bold; color: #0f172a; margin-top: 5px; }
    .metric-lbl { font-size: 0.9rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UTILIDADES Y MATEMÁTICAS
# ==========================================

def normalizar_str(valor):
    """Estandariza textos para comparaciones (Upper + Trim + Strings vacíos)."""
    if pd.isna(valor) or valor == "":
        return ""
    return str(valor).strip().upper()

def clean_currency(val):
    """Convierte strings de dinero ($1.000,00 o 1,000.00) a float puro."""
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').strip()
        if not val: return 0.0
        try:
            # Detección automática de formato decimal (coma vs punto)
            if ',' in val and '.' in val:
                if val.find('.') < val.find(','): # 1.000,00 -> Latino
                    val = val.replace('.', '').replace(',', '.')
                else: # 1,000.00 -> Gringo
                    val = val.replace(',', '')
            elif ',' in val: # 1000,00 -> Latino simple
                val = val.replace(',', '.')
            return float(val)
        except:
            return 0.0
    return 0.0

def sanitizar_para_sheet(val):
    """Convierte tipos de numpy a tipos nativos de Python para Gspread."""
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    return val

def redondear_centena(valor):
    """
    Redondea hacia ARRIBA a la centena más cercana.
    Ej: 1420 -> 1500, 1500 -> 1500, 1501 -> 1600.
    """
    if not valor: return 0.0
    return math.ceil(valor / 100.0) * 100.0

# ==========================================
# 3. CONEXIÓN A GOOGLE SHEETS
# ==========================================

@st.cache_resource
def conectar_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ CRÍTICO: Falta configuración 'google_service_account' en secrets.toml")
            st.stop()
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Verificar o Crear Hojas necesarias
        try: ws_inv = sh.worksheet("Inventario")
        except: st.error("❌ Falta la hoja 'Inventario'. Créala con columnas: ID, Nombre, Stock, Costo, Precio"); st.stop()
        
        try: ws_map = sh.worksheet("Maestro_Proveedores")
        except: 
            ws_map = sh.add_worksheet("Maestro_Proveedores", 1000, 6)
            ws_map.append_row(["ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Factor_Pack", "Ultima_Actualizacion"])

        try: ws_hist = sh.worksheet("Historial_Recepciones")
        except:
            ws_hist = sh.add_worksheet("Historial_Recepciones", 1000, 7)
            ws_hist.append_row(["Fecha", "Folio", "Proveedor", "Items", "Total", "Usuario", "Estado"])

        return sh, ws_inv, ws_map, ws_hist
    except Exception as e:
        st.error(f"Error Conexión Sheets: {e}")
        st.stop()

# ==========================================
# 4. CEREBRO Y MEMORIA (Aquí se arregla lo del NOMBRE)
# ==========================================

@st.cache_data(ttl=60)
def cargar_cerebro(_ws_inv, _ws_map):
    # 1. Cargar Inventario Interno
    try:
        d_inv = _ws_inv.get_all_records()
        df_inv = pd.DataFrame(d_inv)
        
        # --- LÓGICA DE COLUMNAS MEJORADA ---
        cols = df_inv.columns
        
        # A. Buscar columna ID
        col_id = next((c for c in cols if 'ID' in c or 'SKU' in c or 'Ref' in c), None)
        
        # B. Buscar columna NOMBRE (Prioridad estricta a 'Nombre')
        col_nm = next((c for c in cols if 'Nombre' in c), None)
        if not col_nm:
            # Fallback si no hay "Nombre", busca "Desc" o "Prod"
            col_nm = next((c for c in cols if 'Desc' in c or 'Prod' in c), None)
        
        if not col_id: return [], {}, {}
        
        # Si no encuentra columna nombre, usa el ID (para que no falle), pero avisa
        if not col_nm: col_nm = col_id 

        # Crear lista display visual: "1010 | CHUNKY POLLO"
        df_inv['Display'] = df_inv[col_id].astype(str) + " | " + df_inv[col_nm].astype(str)
        
        lista_prods = sorted(df_inv['Display'].unique().tolist())
        lista_prods.insert(0, "NUEVO (Crear Producto)")
        
        # Diccionario para búsqueda rápida
        dict_prods = pd.Series(df_inv['Display'].values, index=df_inv[col_id].apply(normalizar_str)).to_dict()
    except Exception as e:
        print(f"Error cargando cerebro: {e}")
        lista_prods, dict_prods = ["NUEVO (Crear Producto)"], {}

    # 2. Cargar Mapeo Proveedores (Memoria)
    memoria = {}
    try:
        d_map = _ws_map.get_all_records()
        for r in d_map:
            # Clave única: NIT_PROVEEDOR + "_" + SKU_PROVEEDOR
            k = f"{normalizar_str(r.get('ID_Proveedor'))}_{normalizar_str(r.get('SKU_Proveedor'))}"
            memoria[k] = {
                'SKU_Interno': normalizar_str(r.get('SKU_Interno')),
                'Factor': float(r.get('Factor_Pack', 1)) if r.get('Factor_Pack') else 1.0
            }
    except: pass

    return lista_prods, dict_prods, memoria

# ==========================================
# 5. PARSER XML COLOMBIA (UBL 2.1)
# ==========================================

def parsear_xml_colombia(archivo):
    """
    Lee XMLs de Facturación Electrónica Colombia.
    Extrae datos del AttachedDocument o Invoice directo.
    """
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        # Namespaces globales
        ns_map = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'
        }

        # 1. Manejo de AttachedDocument (Contenedor DIAN)
        invoice_root = root
        if 'AttachedDocument' in root.tag:
            desc_node = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
            if desc_node is not None and desc_node.text:
                xml_string = desc_node.text.strip()
                if "<Invoice" in xml_string:
                    xml_string = xml_string[xml_string.find("<Invoice"):]
                invoice_root = ET.fromstring(xml_string)
            else:
                st.error("XML inválido: AttachedDocument vacío.")
                return None

        # 2. Extracción de Datos Header
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

        try: total = float(invoice_root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns).text)
        except: total = 0.0

        # 3. Extracción de Items
        items = []
        lines = invoice_root.findall('.//cac:InvoiceLine', ns)
        
        for line in lines:
            try:
                qty = float(line.find('cbc:InvoicedQuantity', ns).text)
                
                # Precio Unitario
                price_node = line.find('.//cac:Price/cbc:PriceAmount', ns)
                price = float(price_node.text) if price_node is not None else 0.0
                
                item_node = line.find('cac:Item', ns)
                desc = item_node.find('cbc:Description', ns).text
                
                # SKU Proveedor
                sku_prov = "S/C"
                seller_id = item_node.find('.//cac:SellersItemIdentification/cbc:ID', ns)
                std_id = item_node.find('.//cac:StandardItemIdentification/cbc:ID', ns)
                
                if seller_id is not None: sku_prov = seller_id.text
                elif std_id is not None: sku_prov = std_id.text
                
                items.append({
                    'SKU_Proveedor': sku_prov,
                    'Descripcion': desc,
                    'Cantidad': qty,
                    'Costo_Unitario': price
                })
            except: continue

        return {
            'Proveedor': nombre_prov,
            'ID_Proveedor': nit_prov,
            'Folio': folio,
            'Total': total,
            'Items': items
        }

    except Exception as e:
        st.error(f"Error parseando XML: {e}")
        return None

# ==========================================
# 6. LÓGICA DE GUARDADO (Cerebro de Precios)
# ==========================================

def procesar_guardado(ws_map, ws_inv, ws_hist, df_final, meta_xml):
    """
    Actualiza Inventario, Precios, Costos y Memoria.
    """
    try:
        fecha = datetime.now().strftime("%Y-%m-%d")

        # --- A. APRENDIZAJE (Guardar en Maestro) ---
        new_mappings = []
        for _, row in df_final.iterrows():
            sel = row['SKU_Interno_Seleccionado']
            if "NUEVO" not in sel:
                sku_int = sel.split(" | ")[0].strip()
                new_mappings.append([
                    str(meta_xml['ID_Proveedor']),
                    str(meta_xml['Proveedor']),
                    str(row['SKU_Proveedor']),
                    sku_int,
                    float(row['Factor_Pack']),
                    fecha
                ])
        if new_mappings: ws_map.append_rows(new_mappings)

        # --- B. LECTURA DE INVENTARIO ACTUAL ---
        inv_data = ws_inv.get_all_values()
        header = inv_data[0]
        
        # --- BÚSQUEDA DE INDICES DE COLUMNAS (Para saber dónde escribir) ---
        try:
            # 1. ID
            idx_id = 0 
            
            # 2. NOMBRE (Buscamos 'Nombre' o 'Desc')
            idx_nombre = next(i for i, c in enumerate(header) if 'Nombre' in c or 'Nom' in c or 'Desc' in c)
            
            # 3. STOCK
            idx_stock = next(i for i, c in enumerate(header) if 'Stock' in c)
            
            # 4. COSTO
            idx_costo = next(i for i, c in enumerate(header) if 'Costo' in c)
            
            # 5. PRECIO VENTA
            idx_precio = next(i for i, c in enumerate(header) if any(x in c for x in ['Precio', 'Venta', 'PVP']))
            
        except StopIteration:
            return False, ["❌ Error Crítico: Revisa las columnas de tu hoja Inventario. Necesitas: 'Nombre', 'Stock', 'Costo', 'Precio'."]
        except Exception as e:
            # Fallback por si acaso
            idx_nombre = 1
            idx_stock = 2
            idx_costo = 3
            idx_precio = 4

        # Mapa de filas para actualizaciones rápidas
        mapa_filas = {normalizar_str(r[idx_id]): i+1 for i, r in enumerate(inv_data)}

        updates = []
        appends = []
        logs = []

        # --- C. BUCLE PRINCIPAL ---
        for _, row in df_final.iterrows():
            sel = row['SKU_Interno_Seleccionado']
            
            # Datos de Entrada
            factor = float(row['Factor_Pack']) if row['Factor_Pack'] > 0 else 1.0
            cant_recibida_xml = float(row['Cantidad_Recibida'])
            cant_total_unidades = cant_recibida_xml * factor
            
            # CÁLCULO DE COSTO CON IVA (5%)
            costo_unitario_xml = float(row['Costo_Unitario']) / factor
            costo_nuevo_con_iva = costo_unitario_xml * 1.05 # +5%
            
            if "NUEVO" in sel:
                # --- NUEVO PRODUCTO ---
                new_id = str(row['SKU_Proveedor']) if row['SKU_Proveedor'] != "S/C" else f"N-{int(time.time())}"
                
                # Precio Sugerido (Costo + 30% + Redondeo)
                precio_sugerido = redondear_centena(costo_nuevo_con_iva * 1.30)
                
                new_row = [""] * len(header)
                new_row[0] = new_id
                
                # Asegurar que escribimos en la columna correcta del NOMBRE
                if idx_nombre < len(new_row):
                    new_row[idx_nombre] = row['Descripcion'] # Nombre desde factura
                
                if idx_stock < len(new_row): new_row[idx_stock] = sanitizar_para_sheet(cant_total_unidades)
                if idx_costo < len(new_row): new_row[idx_costo] = sanitizar_para_sheet(costo_nuevo_con_iva)
                if idx_precio < len(new_row): new_row[idx_precio] = sanitizar_para_sheet(precio_sugerido)
                
                appends.append(new_row)
                logs.append(f"✨ CREADO: {new_id} ({row['Descripcion']}) | Costo: ${costo_nuevo_con_iva:,.0f} | Venta: ${precio_sugerido:,.0f}")
            
            else:
                # --- ACTUALIZAR EXISTENTE ---
                sku_int = normalizar_str(sel.split(" | ")[0])
                
                if sku_int in mapa_filas:
                    fila = mapa_filas[sku_int]
                    row_actual = inv_data[fila-1]
                    
                    # Leer datos actuales
                    try: stock_curr = clean_currency(row_actual[idx_stock])
                    except: stock_curr = 0.0
                    try: costo_curr = clean_currency(row_actual[idx_costo])
                    except: costo_curr = 0.0
                    try: precio_curr = clean_currency(row_actual[idx_precio])
                    except: precio_curr = 0.0
                    
                    # 1. Actualizar Stock
                    new_stock = stock_curr + cant_total_unidades
                    updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_stock+1), 'values': [[new_stock]]})
                    
                    # 2. Actualizar Costo (Siempre)
                    updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_costo+1), 'values': [[costo_nuevo_con_iva]]})
                    
                    # 3. Lógica Precio
                    nuevo_precio_final = precio_curr 
                    
                    # SUBIDA DE COSTO
                    if costo_nuevo_con_iva > costo_curr:
                        margen_anterior = (precio_curr / costo_curr) if costo_curr > 0 else 1.30
                        if margen_anterior < 1: margen_anterior = 1.30
                        
                        precio_teorico = costo_nuevo_con_iva * margen_anterior
                        nuevo_precio_final = redondear_centena(precio_teorico)
                        
                        updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_precio+1), 'values': [[nuevo_precio_final]]})
                        logs.append(f"📈 SUBIÓ: {sku_int} | Costo: {costo_curr:,.0f}->{costo_nuevo_con_iva:,.0f} | Precio: {precio_curr:,.0f}->{nuevo_precio_final:,.0f}")
                    
                    # BAJADA DE COSTO
                    elif costo_nuevo_con_iva < costo_curr:
                        logs.append(f"💰 MEJOR MARGEN: {sku_int} | Costo bajó. Precio se mantiene.")
                    
                    else:
                        logs.append(f"🔄 STOCK UP: {sku_int}")

        if updates: ws_inv.batch_update(updates)
        if appends: ws_inv.append_rows(appends)

        # --- D. HISTORIAL ---
        ws_hist.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(meta_xml['Folio']),
            str(meta_xml['Proveedor']),
            len(df_final),
            meta_xml['Total'],
            "Admin",
            "OK"
        ])

        return True, logs

    except Exception as e:
        return False, [f"Error del Sistema: {str(e)}"]

# ==========================================
# 7. INTERFAZ PRINCIPAL (STREAMLIT)
# ==========================================

def main():
    st.markdown('<div class="main-header">Recepción Inteligente 🇨🇴</div>', unsafe_allow_html=True)
    
    if 'step' not in st.session_state: st.session_state.step = 1
    
    # Conexión
    sh, ws_inv, ws_map, ws_hist = conectar_sheets()

    # --- PASO 1: CARGA ---
    if st.session_state.step == 1:
        st.markdown('<div class="sub-header">Arrastra tu Factura XML aquí</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("", type=['xml'])
        
        if uploaded:
            with st.spinner("🤖 Analizando estructura DIAN..."):
                data = parsear_xml_colombia(uploaded)
                if not data: st.stop()
                
                # Cargar Memoria
                lst_prods, dct_prods, memoria = cargar_cerebro(ws_inv, ws_map)
                
                # Session
                st.session_state.xml_data = data
                st.session_state.lst_prods = lst_prods
                st.session_state.dct_prods = dct_prods
                st.session_state.memoria = memoria
                st.session_state.step = 2
                st.rerun()

    # --- PASO 2: VERIFICACIÓN ---
    elif st.session_state.step == 2:
        d = st.session_state.xml_data
        mem = st.session_state.memoria
        dct = st.session_state.dct_prods
        
        # Tarjetas Métricas
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-item'><div class='metric-lbl'>Proveedor</div><div class='metric-val'>{d['Proveedor'][:15]}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-item'><div class='metric-lbl'>Factura</div><div class='metric-val'>{d['Folio']}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-item'><div class='metric-lbl'>Total</div><div class='metric-val'>${d['Total']:,.0f}</div></div>", unsafe_allow_html=True)
        
        st.write("---")
        
        # Pre-llenado inteligente
        nit_clean = normalizar_str(d['ID_Proveedor'])
        rows_edit = []
        matches = 0
        
        for it in d['Items']:
            sku_prov = it['SKU_Proveedor']
            key = f"{nit_clean}_{normalizar_str(sku_prov)}"
            
            sel_def = "NUEVO (Crear Producto)"
            fac_def = 1.0
            
            if key in mem:
                sku_int = mem[key]['SKU_Interno']
                if sku_int in dct:
                    sel_def = dct[sku_int]
                    fac_def = mem[key]['Factor']
                    matches += 1
            
            rows_edit.append({
                "SKU_Proveedor": sku_prov,
                "Descripcion": it['Descripcion'],
                "SKU_Interno_Seleccionado": sel_def,
                "Factor_Pack": fac_def,
                "Cantidad_XML": it['Cantidad'],
                "Cantidad_Recibida": it['Cantidad'],
                "Costo_Unitario": it['Costo_Unitario']
            })
        
        if matches > 0: st.success(f"🧠 {matches} productos identificados automáticamente.")
        else: st.info("ℹ️ Asocia los productos por primera vez. El sistema aprenderá para la próxima.")

        # Editor
        df_show = pd.DataFrame(rows_edit)
        edited = st.data_editor(
            df_show,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True),
                "Descripcion": st.column_config.TextColumn("Producto Factura", disabled=True, width="medium"),
                "SKU_Interno_Seleccionado": st.column_config.SelectboxColumn("📌 Tu Inventario", options=st.session_state.lst_prods, required=True, width="large"),
                "Factor_Pack": st.column_config.NumberColumn("Factor (Uds/Caja)", min_value=0.1, help="Si llega 1 caja de 12, pon 12"),
                "Cantidad_XML": st.column_config.NumberColumn("Cant. Fac", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ Recibido"),
                "Costo_Unitario": st.column_config.NumberColumn("Costo Base", format="$%d", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            height=500
        )
        
        # Botones Acción
        colA, colB = st.columns([1, 4])
        if colA.button("🔙 Cancelar"):
            st.session_state.step = 1
            st.rerun()
        
        if colB.button("🚀 PROCESAR ENTRADA Y ACTUALIZAR PRECIOS", type="primary", use_container_width=True):
            with st.status("⚙️ Aplicando lógica de negocio...", expanded=True):
                st.write("Calculando IVA 5% y redondeos...")
                ok, logs = procesar_guardado(ws_map, ws_inv, ws_hist, edited, d)
                
                if ok:
                    st.write("✅ Inventario Actualizado")
                    st.write("✅ Precios Recalculados")
                    time.sleep(1)
                    st.balloons()
                    st.success("¡Proceso Terminado Exitosamente!")
                    
                    with st.expander("📄 Ver Reporte de Cambios (Logs)"):
                        for l in logs:
                            if "SUBIÓ" in l: st.warning(l)
                            elif "BAJÓ" in l: st.success(l)
                            else: st.text(l)
                    
                    if st.button("Nueva Factura"):
                        st.session_state.step = 1
                        st.rerun()
                else:
                    st.error("Hubo un error guardando.")
                    for l in logs: st.error(l)

if __name__ == "__main__":
    main()
