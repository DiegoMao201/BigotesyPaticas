import streamlit as st
import pandas as pd
import gspread
import numpy as np
import json
import uuid
import time
import io
from datetime import datetime, timedelta, date
from urllib.parse import quote

# ==========================================
# 0. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================

st.set_page_config(
    page_title="Bigotes & Paticas | Nexus Pro AI",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS mejorados
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    :root { --primary-color: #187f77; --accent-color: #f5a641; }
    .stButton>button {
        border-radius: 8px; font-weight: 700; border: 2px solid #187f77;
        color: #187f77; background-color: white; transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #187f77; color: white; }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border-left: 5px solid #187f77;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. FUNCIONES UTILITARIAS Y DE LIMPIEZA
# ==========================================

def normalizar_id_producto(id_prod):
    """Normaliza SKUs para asegurar cruces perfectos."""
    if pd.isna(id_prod) or str(id_prod).strip() == "":
        return "SIN_ID"
    val = str(id_prod).strip().upper()
    val = val.replace(".", "").replace(",", "").replace("\t", "").replace("\n", "")
    val = val.lstrip("0")
    if not val: return "SIN_ID"
    return val

def clean_currency(x):
    """Limpia formatos de moneda."""
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        clean = x.replace('$', '').replace(',', '').replace(' ', '').strip()
        if not clean: return 0.0
        try: return float(clean)
        except: return 0.0
    return 0.0

# ==========================================
# 2. GESTIÓN DE API (Anti-Caídas)
# ==========================================

def safe_google_op(func, *args, **kwargs):
    """
    Wrapper para reintentar operaciones de Google Sheets si fallan por cuota.
    """
    max_retries = 5
    wait = 2
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg:
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    wait *= 2  # Backoff exponencial
                    continue
            st.error(f"Error de conexión con Google: {e}")
            raise e

@st.cache_resource
def conectar_db():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración en secrets.toml")
            return None
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        return sh
    except Exception as e:
        st.error(f"🔴 Error de Conexión Inicial: {e}")
        return None

def get_worksheet_safe(sh, name, headers):
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=max(len(headers), 20))
        ws.append_row(headers)
        return ws

# ==========================================
# 3. CARGA DE DATOS (OPTIMIZADA EN MEMORIA)
# ==========================================

def cargar_datos_snapshot():
    """
    Descarga TODOS los datos de una sola vez y los guarda en Session State.
    Esto reduce las llamadas a la API en un 90%.
    """
    sh = conectar_db()
    if not sh: return None

    # Definición de estructuras
    schemas = {
        "Inventario": ['ID_Producto', 'SKU_Proveedor', 'Nombre', 'Stock', 'Precio', 'Costo', 'Categoria'],
        "Ventas": ['ID_Venta','Fecha','Cedula_Cliente','Nombre_Cliente','Items','Total','Costo_Total'],
        "Maestro_Proveedores": ['ID_Proveedor', 'Nombre_Proveedor', 'SKU_Interno', 'Factor_Pack', 'Costo_Proveedor', 'Email'],
        "Historial_Ordenes": ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total_Dinero', 'Estado']
    }

    data_store = {}
    
    with st.spinner('🔄 Sincronizando base de datos completa...'):
        # Carga paralela simulada (secuencial pero protegida)
        for sheet_name, cols in schemas.items():
            ws = get_worksheet_safe(sh, sheet_name, cols)
            # Usamos safe_google_op para leer
            records = safe_google_op(ws.get_all_records)
            df = pd.DataFrame(records)
            
            # Asegurar columnas
            if df.empty:
                df = pd.DataFrame(columns=cols)
            else:
                for c in cols:
                    if c not in df.columns: df[c] = ""
            
            data_store[f"df_{sheet_name}"] = df
            data_store[f"ws_{sheet_name}"] = ws

    # --- PROCESAMIENTO INICIAL ---
    
    # 1. Inventario
    df_inv = data_store["df_Inventario"]
    df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
    df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
    df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
    df_inv['ID_Producto_Norm'] = df_inv['ID_Producto'].apply(normalizar_id_producto)

    # 2. Proveedores
    df_prov = data_store["df_Maestro_Proveedores"]
    df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
    df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)
    df_prov['SKU_Interno_Norm'] = df_prov['SKU_Interno'].apply(normalizar_id_producto)

    # 3. Ventas
    df_ven = data_store["df_Ventas"]
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')

    # Guardar en Session State
    st.session_state['data_store'] = data_store
    st.session_state['last_sync'] = datetime.now()
    
    return data_store

# ==========================================
# 4. LÓGICA DE NEGOCIO (AI & CÁLCULOS)
# ==========================================

def analizar_ventas(df_ven, df_inv):
    if df_ven.empty: return {}
    
    cutoff_90 = datetime.now() - timedelta(days=90)
    cutoff_30 = datetime.now() - timedelta(days=30)
    ven_recent = df_ven[df_ven['Fecha'] >= cutoff_90]
    
    stats = {}
    # Crear mapa de Nombres a IDs para búsqueda rápida
    mapa_nombre_id = dict(zip(df_inv['Nombre'].str.strip().str.upper(), df_inv['ID_Producto_Norm']))

    for _, row in ven_recent.iterrows():
        items_str = str(row.get('Items', ''))
        fecha = row['Fecha']
        lista = items_str.split(',')
        
        for item in lista:
            item = item.strip()
            qty = 1
            nombre = item
            
            # Parsear "2xNombre"
            if 'x' in item:
                parts = item.split('x', 1)
                if parts[0].strip().isdigit():
                    qty = int(parts[0].strip())
                    nombre = parts[1].strip()
            
            nombre_upper = nombre.upper()
            id_norm = mapa_nombre_id.get(nombre_upper)
            
            if id_norm:
                if id_norm not in stats: stats[id_norm] = {'v90': 0, 'v30': 0}
                stats[id_norm]['v90'] += qty
                if fecha >= cutoff_30:
                    stats[id_norm]['v30'] += qty
    return stats

def calcular_master_df():
    """Ejecuta la lógica de negocio sobre los datos en memoria."""
    data = st.session_state['data_store']
    df_inv = data['df_Inventario']
    df_prov = data['df_Maestro_Proveedores']
    df_ven = data['df_Ventas']
    
    stats = analizar_ventas(df_ven, df_inv)
    
    # Merge Inventario + Proveedores
    if not df_prov.empty:
        # Priorizar proveedor más barato si hay duplicados
        df_prov_clean = df_prov.sort_values('Costo_Proveedor', ascending=True).drop_duplicates('SKU_Interno_Norm')
        master = pd.merge(df_inv, df_prov_clean[['SKU_Interno_Norm', 'Nombre_Proveedor', 'Costo_Proveedor', 'Factor_Pack']], 
                          left_on='ID_Producto_Norm', right_on='SKU_Interno_Norm', how='left')
    else:
        master = df_inv.copy()
        master['Nombre_Proveedor'] = 'Generico'
        master['Costo_Proveedor'] = master['Costo']
        master['Factor_Pack'] = 1

    # Relleno de datos faltantes
    master['Nombre_Proveedor'] = master['Nombre_Proveedor'].fillna('Sin Asignar')
    master['Costo_Proveedor'] = np.where(master['Costo_Proveedor'].isna() | (master['Costo_Proveedor'] <= 0), 
                                         master['Costo'], master['Costo_Proveedor'])
    master['Factor_Pack'] = np.where(master['Factor_Pack'].isna() | (master['Factor_Pack'] <= 0), 
                                     1, master['Factor_Pack'])

    # Cálculo vectorial (Más rápido que iterar filas)
    master['v90'] = master['ID_Producto_Norm'].map(lambda x: stats.get(x, {}).get('v90', 0))
    master['v30'] = master['ID_Producto_Norm'].map(lambda x: stats.get(x, {}).get('v30', 0))
    
    master['Velocidad_Diaria'] = np.maximum(master['v90']/90, master['v30']/30)
    master['Dias_Cobertura'] = np.where(master['Velocidad_Diaria'] > 0, 
                                        master['Stock'] / master['Velocidad_Diaria'], 
                                        999)
    
    # Estado
    conditions = [
        (master['Stock'] <= 0),
        (master['Dias_Cobertura'] <= 15),
        (master['Dias_Cobertura'] <= 30)
    ]
    choices = ["💀 AGOTADO", "🚨 CRÍTICO", "⚠️ Bajo"]
    master['Estado'] = np.select(conditions, choices, default="✅ OK")
    
    # Sugerencia Compra
    stock_seguridad = master['Velocidad_Diaria'] * 7 # 7 días seguridad
    stock_objetivo = (master['Velocidad_Diaria'] * 45) + stock_seguridad # 45 días inventario
    
    master['Faltante'] = np.maximum(0, stock_objetivo - master['Stock'])
    master['Sugerencia_Cajas'] = np.ceil(master['Faltante'] / master['Factor_Pack'])
    master['Unidades_Pedir'] = master['Sugerencia_Cajas'] * master['Factor_Pack']
    master['Inversion_Est'] = master['Unidades_Pedir'] * master['Costo_Proveedor']
    
    return master

# ==========================================
# 5. FUNCIONES DE ESCRITURA (ACTIONS)
# ==========================================

def crear_orden_compra(proveedor, items_df):
    """Escribe la orden en Google Sheets y actualiza el estado local."""
    data = st.session_state['data_store']
    ws_ord = data['ws_Historial_Ordenes']
    
    id_orden = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    fecha = str(date.today())
    detalles = items_df[['ID_Producto', 'Nombre', 'Sugerencia_Cajas', 'Unidades_Pedir', 'Costo_Proveedor']].to_dict('records')
    total = items_df['Inversion_Est'].sum()
    
    # Row para Google Sheets
    # Cols: ID_Orden, Proveedor, Fecha_Orden, Items_JSON, Total_Dinero, Estado
    row = [id_orden, proveedor, fecha, json.dumps(detalles), total, "Pendiente"]
    
    # 1. Escribir en Google (Safe)
    safe_google_op(ws_ord.append_row, row)
    
    # 2. Actualizar memoria local (Para que se vea reflejado sin recargar todo)
    new_df_row = pd.DataFrame([row], columns=data['df_Historial_Ordenes'].columns)
    data['df_Historial_Ordenes'] = pd.concat([data['df_Historial_Ordenes'], new_df_row], ignore_index=True)
    st.session_state['data_store'] = data # Guardar cambios en sesión
    
    return id_orden

def procesar_recepcion(id_orden, items_json):
    """Actualiza stock en Inventario y cierra la orden."""
    data = st.session_state['data_store']
    ws_inv = data['ws_Inventario']
    ws_ord = data['ws_Historial_Ordenes']
    df_inv = data['df_Inventario']
    
    items = json.loads(items_json)
    
    # Actualización masiva es compleja en gspread celda a celda. 
    # Estrategia: Buscar celda del producto y actualizar stock.
    
    progreso = st.progress(0)
    for i, item in enumerate(items):
        prod_id = str(item['ID_Producto'])
        cantidad = float(item['Unidades_Pedir'])
        
        # 1. Encontrar celda en Sheet
        cell = safe_google_op(ws_inv.find, prod_id)
        if cell:
            # Asumimos columna Stock es la 4 (indice 3 en df, col 4 en sheet)
            # Pero mejor buscar el header
            col_stock = df_inv.columns.get_loc("Stock") + 1 
            current_stock_cell = safe_google_op(ws_inv.cell, cell.row, col_stock)
            nuevo_stock = float(current_stock_cell.value or 0) + cantidad
            safe_google_op(ws_inv.update_cell, cell.row, col_stock, nuevo_stock)
            
            # 2. Actualizar Localmente
            idx = df_inv[df_inv['ID_Producto'] == prod_id].index
            if not idx.empty:
                df_inv.at[idx[0], 'Stock'] += cantidad
        
        progreso.progress((i + 1) / len(items))

    # 3. Marcar Orden como Recibida
    cell_ord = safe_google_op(ws_ord.find, id_orden)
    if cell_ord:
        col_estado = data['df_Historial_Ordenes'].columns.get_loc("Estado") + 1
        safe_google_op(ws_ord.update_cell, cell_ord.row, col_estado, "Recibido")
        
        # Update Local Ord
        idx_ord = data['df_Historial_Ordenes'][data['df_Historial_Ordenes']['ID_Orden'] == id_orden].index
        if not idx_ord.empty:
            data['df_Historial_Ordenes'].at[idx_ord[0], 'Estado'] = "Recibido"

    st.success("Inventario actualizado exitosamente.")
    time.sleep(1)
    st.rerun()

# ==========================================
# 6. INTERFAZ GRÁFICA (UI)
# ==========================================

def main():
    # --- SIDEBAR DE CONTROL ---
    with st.sidebar:
        st.header("⚡ Panel de Control")
        
        # Verificar estado de datos
        if 'data_store' not in st.session_state:
            cargar_datos_snapshot()
        
        last_sync = st.session_state.get('last_sync', datetime.min)
        st.info(f"Última sinc: {last_sync.strftime('%H:%M:%S')}")
        
        if st.button("🔄 Sincronizar Datos", help="Descarga los cambios recientes de Google Sheets"):
            st.cache_resource.clear()
            cargar_datos_snapshot()
            st.rerun()
            
        st.markdown("---")
        st.caption("Nexus Pro AI v2.5 (Optimized)")

    # --- DATOS EN MEMORIA ---
    if 'data_store' not in st.session_state:
        st.error("No hay datos cargados. Presiona Sincronizar.")
        return

    # Procesamiento Local (Rápido)
    master_df = calcular_master_df()
    
    # --- DASHBOARD HEADER ---
    st.title("🐾 Bigotes & Paticas | Nexus WMS")
    
    c1, c2, c3, c4 = st.columns(4)
    valor_inv = (master_df['Stock'] * master_df['Costo']).sum()
    agotados = master_df[master_df['Stock'] <= 0].shape[0]
    criticos = master_df[master_df['Estado'] == '🚨 CRÍTICO'].shape[0]
    venta_est = master_df['v90'].sum() / 3
    
    c1.metric("💰 Valor Inventario", f"${valor_inv:,.0f}")
    c2.metric("💀 Agotados", agotados)
    c3.metric("🚨 Stock Crítico", criticos)
    c4.metric("📈 Salida Mensual", f"{int(venta_est)} unds")

    tabs = st.tabs(["📊 Auditoría", "🧠 Compras AI", "📥 Recepción", "⚙️ Exportar"])

    # === TAB 1: AUDITORÍA ===
    with tabs[0]:
        st.subheader("🕵️ Visor de Inventario")
        txt_search = st.text_input("Buscar producto por nombre o SKU...")
        
        df_view = master_df.copy()
        if txt_search:
            df_view = df_view[
                df_view['Nombre'].str.contains(txt_search, case=False, na=False) | 
                df_view['ID_Producto_Norm'].str.contains(txt_search, case=False, na=False)
            ]
        
        st.dataframe(
            df_view[['ID_Producto', 'Nombre', 'Stock', 'Estado', 'Dias_Cobertura', 'Costo', 'Nombre_Proveedor']],
            column_config={
                "Costo": st.column_config.NumberColumn(format="$%.0f"),
                "Dias_Cobertura": st.column_config.NumberColumn(format="%.1f d")
            },
            use_container_width=True,
            hide_index=True
        )

    # === TAB 2: COMPRAS AI ===
    with tabs[1]:
        st.subheader("🧠 Sugerencias de Reabastecimiento")
        
        # Filtro de sugerencias
        df_buy = master_df[master_df['Unidades_Pedir'] > 0].copy()
        df_buy = df_buy.sort_values(['Nombre_Proveedor', 'Estado'])
        
        if df_buy.empty:
            st.success("Todo en orden. No se requieren compras.")
        else:
            df_buy['Confirmar'] = True # Checkbox por defecto
            
            edited_buy = st.data_editor(
                df_buy[['Confirmar', 'Nombre_Proveedor', 'Nombre', 'Stock', 'Dias_Cobertura', 'Sugerencia_Cajas', 'Factor_Pack', 'Inversion_Est']],
                column_config={
                    "Inversion_Est": st.column_config.NumberColumn("Total $", format="$%.0f", disabled=True),
                    "Sugerencia_Cajas": st.column_config.NumberColumn("📦 Cajas", step=1),
                },
                use_container_width=True,
                hide_index=True,
                key="editor_compras"
            )
            
            seleccion = edited_buy[edited_buy['Confirmar'] == True]
            st.divider()
            
            # Generación de Órdenes
            total_buy = seleccion['Inversion_Est'].sum()
            st.markdown(f"### Total a Invertir: :green[${total_buy:,.0f}]")
            
            proveedores = seleccion['Nombre_Proveedor'].unique()
            cols_p = st.columns(len(proveedores)) if len(proveedores) < 4 else st.columns(3)
            
            for i, prov in enumerate(proveedores):
                items_prov = seleccion[seleccion['Nombre_Proveedor'] == prov]
                subtotal = items_prov['Inversion_Est'].sum()
                
                with st.expander(f"🛒 {prov} (${subtotal:,.0f})", expanded=True):
                    st.table(items_prov[['Nombre', 'Sugerencia_Cajas', 'Unidades_Pedir']])
                    
                    c_b1, c_b2 = st.columns(2)
                    if c_b1.button(f"Crear Orden {prov}", key=f"btn_{prov}"):
                        new_id = crear_orden_compra(prov, items_prov)
                        st.success(f"Orden {new_id} creada!")
                        time.sleep(1.5)
                        st.rerun()
                    
                    # Link WhatsApp
                    msg = f"Hola {prov}, pedido:\n"
                    for _, r in items_prov.iterrows():
                        msg += f"- {r['Sugerencia_Cajas']} cajas {r['Nombre']}\n"
                    link = f"https://wa.me/?text={quote(msg)}"
                    c_b2.markdown(f"[📲 WhatsApp]({link})", unsafe_allow_html=True)

    # === TAB 3: RECEPCIÓN ===
    with tabs[2]:
        st.subheader("📦 Recibir Mercancía")
        df_ord = st.session_state['data_store']['df_Historial_Ordenes']
        
        if df_ord.empty:
            st.info("No hay historial.")
        else:
            pendientes = df_ord[df_ord['Estado'] == 'Pendiente']
            if pendientes.empty:
                st.info("No hay órdenes pendientes.")
            else:
                opcion = st.selectbox("Seleccionar Orden Pendiente", 
                                     pendientes['ID_Orden'] + " | " + pendientes['Proveedor'])
                
                id_sel = opcion.split(" | ")[0]
                row_ord = pendientes[pendientes['ID_Orden'] == id_sel].iloc[0]
                
                st.write(f"**Fecha:** {row_ord['Fecha_Orden']} | **Total:** ${float(row_ord['Total_Dinero']):,.0f}")
                
                items_json = row_ord['Items_JSON']
                try:
                    detalles = json.loads(items_json)
                    df_det = pd.DataFrame(detalles)
                    st.dataframe(df_det[['Nombre', 'Unidades_Pedir']], hide_index=True)
                    
                    if st.button("✅ Confirmar Ingreso al Inventario", type="primary"):
                        procesar_recepcion(id_sel, items_json)
                except:
                    st.error("Error al leer detalle de items JSON.")

    # === TAB 4: EXPORTAR ===
    with tabs[3]:
        st.subheader("⚙️ Descargar Data")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            master_df.to_excel(writer, sheet_name='Master_AI', index=False)
            st.session_state['data_store']['df_Historial_Ordenes'].to_excel(writer, sheet_name='Ordenes', index=False)
            
        st.download_button(
            label="⬇️ Descargar Excel Completo",
            data=buffer,
            file_name="Nexus_Master_Data.xlsx",
            mime="application/vnd.ms-excel"
        )

if __name__ == "__main__":
    main()