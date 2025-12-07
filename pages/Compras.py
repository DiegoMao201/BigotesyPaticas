import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime
import re

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================

st.set_page_config(
    page_title="Recepción Inteligente Colombia v7.0", 
    page_icon="🇨🇴", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS Profesionales
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    .main-header { font-size: 2.2rem; font-weight: 800; color: #1e3a8a; margin-bottom: 0.5rem; text-align: center; }
    .sub-header { font-size: 1.1rem; color: #64748b; margin-bottom: 2rem; text-align: center; }
    .card-box { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.06); border-left: 5px solid #3b82f6; }
    .metric-row { display: flex; justify-content: space-around; margin-bottom: 20px; }
    .metric-item { background: #fff; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); width: 30%; }
    .metric-val { font-size: 1.4rem; font-weight: bold; color: #0f172a; }
    .metric-lbl { font-size: 0.85rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UTILIDADES DE LIMPIEZA
# ==========================================

def normalizar_str(valor):
    """Estandariza textos para comparaciones (Upper + Trim)."""
    if pd.isna(valor) or valor == "":
        return ""
    return str(valor).strip().upper()

def clean_currency(val):
    """Manejo robusto de moneda."""
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').strip()
        # Manejo: si hay coma y punto, asumimos formato latino (1.000,00) o gringo (1,000.00)
        # Prioridad formato Colombia: punto mil, coma decimal, pero el XML suele venir con punto decimal.
        try:
            return float(val)
        except:
            return 0.0
    return 0.0

def sanitizar_para_sheet(val):
    """Convierte numpy types a nativos de Python para JSON serializable."""
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    return val

# ==========================================
# 3. CONEXIÓN A GOOGLE SHEETS
# ==========================================

@st.cache_resource
def conectar_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración 'google_service_account' en secrets.toml")
            st.stop()
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Verificar/Crear Hojas
        try: ws_inv = sh.worksheet("Inventario")
        except: st.error("❌ Crea la hoja 'Inventario' (cols: ID_Producto, Nombre, Stock, Costo)"); st.stop()
        
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
# 4. LÓGICA DE CEREBRO (MEMORIA)
# ==========================================

@st.cache_data(ttl=60)
def cargar_cerebro(_ws_inv, _ws_map):
    # 1. Cargar Inventario Interno
    try:
        d_inv = _ws_inv.get_all_records()
        df_inv = pd.DataFrame(d_inv)
        # Validar columnas mínimas
        col_id = next((c for c in df_inv.columns if 'ID' in c or 'SKU' in c), None)
        col_nm = next((c for c in df_inv.columns if 'Nom' in c or 'Desc' in c), None)
        
        if not col_id: return [], {}, {}
        
        df_inv['Display'] = df_inv[col_id].astype(str) + " | " + df_inv[col_nm].astype(str)
        lista_prods = sorted(df_inv['Display'].unique().tolist())
        lista_prods.insert(0, "NUEVO (Crear Producto)")
        
        dict_prods = pd.Series(df_inv['Display'].values, index=df_inv[col_id].apply(normalizar_str)).to_dict()
    except:
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
# 5. PARSER XML COLOMBIA (EL CORAZÓN)
# ==========================================

def parsear_xml_colombia(archivo):
    """
    Lee XMLs de Facturación Electrónica Colombia.
    Maneja 'AttachedDocument' extrayendo el 'Invoice' del CDATA.
    """
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        
        # Namespaces globales del contenedor
        ns_container = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'
        }

        # 1. Detectar si es AttachedDocument (Contenedor)
        invoice_root = root
        es_contenedor = False
        
        if 'AttachedDocument' in root.tag:
            es_contenedor = True
            # Buscar el nodo Description donde vive la factura real en CDATA
            # Ruta típica: cac:Attachment -> cac:ExternalReference -> cbc:Description
            desc_node = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_container)
            
            if desc_node is not None and desc_node.text:
                xml_string = desc_node.text.strip()
                # A veces viene con caracteres raros al inicio, limpiamos
                if "<Invoice" in xml_string:
                    xml_string = xml_string[xml_string.find("<Invoice"):]
                
                # Parsear el XML interno (La Factura Real)
                invoice_root = ET.fromstring(xml_string)
            else:
                st.error("Es un AttachedDocument pero no encontré la factura interna en Description.")
                return None

        # 2. Extraer datos del Invoice (ya sea directo o extraído)
        # Namespaces internos del Invoice (suelen ser los mismos UBL 2.1)
        ns = ns_container 
        
        # -- Cabecera --
        try:
            # Proveedor
            prov_node = invoice_root.find('.//cac:AccountingSupplierParty/cac:Party', ns)
            prov_tax = prov_node.find('.//cac:PartyTaxScheme', ns)
            nombre_prov = prov_tax.find('cbc:RegistrationName', ns).text
            nit_prov = prov_tax.find('cbc:CompanyID', ns).text
        except:
            nombre_prov = "Proveedor Desconocido"
            nit_prov = "000000"

        try:
            folio = invoice_root.find('cbc:ID', ns).text
        except: folio = "S/F"

        try:
            total = float(invoice_root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns).text)
        except: total = 0.0

        # -- Items (Lineas) --
        items = []
        lines = invoice_root.findall('.//cac:InvoiceLine', ns)
        
        for line in lines:
            try:
                # Cantidad
                qty = float(line.find('cbc:InvoicedQuantity', ns).text)
                
                # Precio Unitario (Ojo: PriceAmount suele ser base, LineExtensionAmount es total linea sin impto)
                # Buscamos precio unitario explícito
                price_node = line.find('.//cac:Price/cbc:PriceAmount', ns)
                price = float(price_node.text) if price_node is not None else 0.0
                
                # Descripción
                item_node = line.find('cac:Item', ns)
                desc = item_node.find('cbc:Description', ns).text
                
                # SKU Proveedor: Puede estar en SellersItemIdentification o StandardItemIdentification
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
            except Exception as e:
                print(f"Error leyendo linea: {e}")
                continue

        return {
            'Proveedor': nombre_prov,
            'ID_Proveedor': nit_prov,
            'Folio': folio,
            'Total': total,
            'Items': items
        }

    except Exception as e:
        st.error(f"Error crítico parseando XML: {e}")
        return None

# ==========================================
# 6. GUARDAR Y ACTUALIZAR
# ==========================================

def procesar_guardado(ws_map, ws_inv, ws_hist, df_final, meta_xml):
    """Ejecuta la actualización de las 3 hojas."""
    try:
        # 1. APRENDIZAJE (Maestro)
        new_mappings = []
        fecha = datetime.now().strftime("%Y-%m-%d")
        
        for _, row in df_final.iterrows():
            sel = row['SKU_Interno_Seleccionado']
            if "NUEVO" not in sel:
                sku_int = sel.split(" | ")[0].strip()
                # Agregamos solo si seleccionó un producto existente para enseñar al sistema
                new_mappings.append([
                    str(meta_xml['ID_Proveedor']),
                    str(meta_xml['Proveedor']),
                    str(row['SKU_Proveedor']),
                    sku_int,
                    float(row['Factor_Pack']),
                    fecha
                ])
        if new_mappings:
            ws_map.append_rows(new_mappings)

        # 2. INVENTARIO
        inv_data = ws_inv.get_all_values()
        header = inv_data[0]
        # Índices
        try:
            idx_id = 0 # Asumimos col A es ID
            idx_stock = next(i for i, c in enumerate(header) if 'Stock' in c)
            idx_costo = next(i for i, c in enumerate(header) if 'Costo' in c)
        except: return False, ["❌ Error en columnas de Inventario (Revisa nombres 'Stock', 'Costo')"]

        mapa_filas = {normalizar_str(r[idx_id]): i+1 for i, r in enumerate(inv_data)} # i+1 es fila sheet (1-based)

        updates = []
        appends = []
        logs = []

        for _, row in df_final.iterrows():
            sel = row['SKU_Interno_Seleccionado']
            cant_total = row['Cantidad_Recibida'] * row['Factor_Pack']
            costo_unit = row['Costo_Unitario'] / row['Factor_Pack'] if row['Factor_Pack'] else 0

            if "NUEVO" in sel:
                # Crear nuevo
                new_id = str(row['SKU_Proveedor']) if row['SKU_Proveedor'] != "S/C" else f"N-{int(time.time())}"
                new_row = [""] * len(header)
                new_row[0] = new_id # ID
                new_row[1] = row['Descripcion'] # Nombre (asumiendo col B)
                new_row[idx_stock] = sanitizar_para_sheet(cant_total)
                new_row[idx_costo] = sanitizar_para_sheet(costo_unit)
                appends.append(new_row)
                logs.append(f"✨ Nuevo Item: {new_id}")
            else:
                # Actualizar existente
                sku_int = normalizar_str(sel.split(" | ")[0])
                if sku_int in mapa_filas:
                    fila = mapa_filas[sku_int]
                    # Leemos stock actual del data en memoria
                    try:
                        stock_curr = clean_currency(inv_data[fila-1][idx_stock])
                    except: stock_curr = 0
                    
                    new_stock = stock_curr + cant_total
                    
                    updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_stock+1), 'values': [[new_stock]]})
                    updates.append({'range': gspread.utils.rowcol_to_a1(fila, idx_costo+1), 'values': [[costo_unit]]}) # Actualiza costo ultimo
                    logs.append(f"🔄 Upd: {sku_int} | Stock {stock_curr}->{new_stock}")

        if updates: ws_inv.batch_update(updates)
        if appends: ws_inv.append_rows(appends)

        # 3. HISTORIAL
        ws_hist.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(meta_xml['Folio']),
            str(meta_xml['Proveedor']),
            len(df_final),
            meta_xml['Total'],
            "Usuario",
            "Exitoso"
        ])

        return True, logs

    except Exception as e:
        return False, [str(e)]

# ==========================================
# 7. APP PRINCIPAL
# ==========================================

def main():
    st.markdown('<div class="main-header">Recepción Inteligente Colombia 🇨🇴</div>', unsafe_allow_html=True)
    
    # Init Session
    if 'step' not in st.session_state: st.session_state.step = 1
    
    # Conexión
    sh, ws_inv, ws_map, ws_hist = conectar_sheets()

    # --- PASO 1: CARGA ---
    if st.session_state.step == 1:
        st.markdown('<div class="sub-header">Carga tu XML (AttachedDocument o Factura)</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("Arrastra XML aquí", type=['xml'])
        
        if uploaded:
            with st.spinner("Desempaquetando XML de la DIAN..."):
                # Parsear
                data = parsear_xml_colombia(uploaded)
                if not data: st.stop()
                
                # Cargar Cerebro
                lst_prods, dct_prods, memoria = cargar_cerebro(ws_inv, ws_map)
                
                # Guardar en sesión
                st.session_state.xml_data = data
                st.session_state.lst_prods = lst_prods
                st.session_state.dct_prods = dct_prods
                st.session_state.memoria = memoria
                st.session_state.step = 2
                st.rerun()

    # --- PASO 2: MATCHING ---
    elif st.session_state.step == 2:
        d = st.session_state.xml_data
        mem = st.session_state.memoria
        dct = st.session_state.dct_prods
        
        # Info Card
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-item'><div class='metric-lbl'>Proveedor</div><div class='metric-val'>{d['Proveedor'][:15]}..</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-item'><div class='metric-lbl'>Factura #</div><div class='metric-val'>{d['Folio']}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-item'><div class='metric-lbl'>Total</div><div class='metric-val'>${d['Total']:,.0f}</div></div>", unsafe_allow_html=True)
        
        st.write("---")
        
        # Preparar datos para editor
        nit_clean = normalizar_str(d['ID_Proveedor'])
        rows_edit = []
        
        matches = 0
        for it in d['Items']:
            sku_prov = it['SKU_Proveedor']
            # Key de memoria
            key = f"{nit_clean}_{normalizar_str(sku_prov)}"
            
            sel_def = "NUEVO (Crear Producto)"
            fac_def = 1.0
            
            # Cerebro check
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
            
        if matches > 0: st.success(f"🧠 Memoria activada: {matches} productos reconocidos.")
        else: st.info("ℹ️ Proveedor nuevo o productos nuevos. Asocia manualmente y aprenderé.")
        
        df_show = pd.DataFrame(rows_edit)
        
        edited = st.data_editor(
            df_show,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("Ref. Prov", disabled=True),
                "Descripcion": st.column_config.TextColumn("Desc. Factura", disabled=True, width="medium"),
                "SKU_Interno_Seleccionado": st.column_config.SelectboxColumn(
                    "📌 Tu Producto (Match)",
                    options=st.session_state.lst_prods,
                    required=True,
                    width="large"
                ),
                "Factor_Pack": st.column_config.NumberColumn("Factor (Unds/Caja)", min_value=0.1),
                "Cantidad_XML": st.column_config.NumberColumn("Cant. Fac", disabled=True),
                "Cantidad_Recibida": st.column_config.NumberColumn("✅ Recibido", min_value=0),
                "Costo_Unitario": st.column_config.NumberColumn("Costo Fac", format="$%d", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            height=500
        )
        
        c_l, c_r = st.columns([1, 4])
        if c_l.button("Cancelar"):
            st.session_state.step = 1
            st.rerun()
        
        if c_r.button("PROCESAR ENTRADA 🚀", type="primary", use_container_width=True):
            with st.status("Actualizando sistema...", expanded=True):
                st.write("🧠 Guardando aprendizaje...")
                ok, logs = procesar_guardado(ws_map, ws_inv, ws_hist, edited, d)
                
                if ok:
                    st.write("✅ Inventario actualizado.")
                    st.write("✅ Historial registrado.")
                    st.balloons()
                    time.sleep(1)
                    st.success("¡Proceso Terminado!")
                    with st.expander("Ver Logs"):
                        for l in logs: st.text(l)
                    
                    if st.button("Nueva Factura"):
                        st.session_state.step = 1
                        st.rerun()
                else:
                    st.error("Error guardando datos.")
                    for l in logs: st.error(l)

if __name__ == "__main__":
    main()
