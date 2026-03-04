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
import xlsxwriter

# ==========================================
# 0. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================

st.set_page_config(
    page_title="Bigotes & Paticas | WMS Avanzado",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        background-color: #f8f9fa; border-left: 5px solid #f5a641;
        padding: 15px; border-radius: 8px; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. FUNCIONES UTILITARIAS Y DE LIMPIEZA
# ==========================================

def normalizar_id_producto(id_prod):
    if pd.isna(id_prod) or str(id_prod).strip() == "": return "SIN_ID"
    val = str(id_prod).strip().upper()
    val = val.replace(".", "").replace(",", "").replace("\t", "").replace("\n", "").lstrip("0")
    return val if val else "SIN_ID"

def clean_currency(x):
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        clean = x.replace('$', '').replace(',', '').replace(' ', '').strip()
        try: return float(clean)
        except: return 0.0
    return 0.0

# ==========================================
# 2. GESTIÓN DE API (Anti-Caídas)
# ==========================================

def safe_google_op(func, *args, **kwargs):
    max_retries = 5
    wait = 2
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e).lower() or "quota" in str(e).lower():
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    wait *= 2 
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
        return gc.open_by_url(st.secrets["SHEET_URL"])
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
# 3. CARGA DE DATOS (NUEVOS ESQUEMAS)
# ==========================================

def cargar_datos_snapshot():
    sh = conectar_db()
    if not sh: return None

    schemas = {
        "Inventario": [
            "Producto_UID",  # <-- NUEVO (robusto)
            "ID_Producto", "ID_Producto_Norm", "SKU_Proveedor", "Nombre", "Stock",
            "Precio", "Costo", "Categoria", "Iva"
        ],
        "Ventas": ['ID_Venta', 'Fecha', 'Cedula_Cliente', 'Nombre_Cliente', 'Tipo_Entrega', 'Direccion_Envio', 'Estado_Envio', 'Metodo_Pago', 'Banco_Destino', 'Total', 'Items', 'Items_Detalle', 'Costo_Total', 'Mascota'],
        "Gastos": ['ID_Gasto', 'Fecha', 'Tipo_Gasto', 'Categoria', 'Descripcion', 'Monto', 'Metodo_Pago', 'Banco_Origen'],
        "Maestro_Proveedores": ['ID_Proveedor', 'Nombre_Proveedor', 'SKU_Interno', 'Factor_Pack', 'Costo_Proveedor', 'Email'],
        "Historial_Ordenes": ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total_Dinero', 'Estado']
    }

    data_store = {}
    with st.spinner('🔄 Sincronizando Core de Datos...'):
        for sheet_name, cols in schemas.items():
            ws = get_worksheet_safe(sh, sheet_name, cols)
            records = safe_google_op(ws.get_all_records)
            df = pd.DataFrame(records)
            if df.empty: df = pd.DataFrame(columns=cols)
            else:
                for c in cols:
                    if c not in df.columns: df[c] = ""
            data_store[f"df_{sheet_name}"] = df
            data_store[f"ws_{sheet_name}"] = ws

    # Limpieza Inventario
    df_inv = data_store["df_Inventario"]
    if "Producto_UID" not in df_inv.columns:
        df_inv["Producto_UID"] = ""
    df_inv["Producto_UID"] = df_inv["Producto_UID"].fillna("").astype(str).str.strip()

    df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
    df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
    df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
    df_inv['ID_Producto_Norm'] = df_inv['ID_Producto'].apply(normalizar_id_producto)
    df_inv['Categoria'] = df_inv['Categoria'].replace('', 'Sin Categoría').fillna('Sin Categoría')

    # Limpieza Ventas & Gastos
    data_store["df_Ventas"]['Fecha'] = pd.to_datetime(data_store["df_Ventas"]['Fecha'], errors='coerce')
    data_store["df_Gastos"]['Fecha'] = pd.to_datetime(data_store["df_Gastos"]['Fecha'], errors='coerce')
    data_store["df_Gastos"]['Monto'] = data_store["df_Gastos"]['Monto'].apply(clean_currency)

    # Limpieza Proveedores
    df_prov = data_store["df_Maestro_Proveedores"]
    df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
    df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)
    df_prov['SKU_Interno_Norm'] = df_prov['SKU_Interno'].apply(normalizar_id_producto)

    st.session_state['data_store'] = data_store
    st.session_state['last_sync'] = datetime.now()
    return data_store

# ==========================================
# 4. MOTOR ANALÍTICO AVANZADO (ABC & COMPRAS)
# ==========================================

def analizar_ventas(df_ven, df_inv):
    if df_ven.empty: return {}
    cutoff_90 = datetime.now() - timedelta(days=90)
    cutoff_30 = datetime.now() - timedelta(days=30)
    ven_recent = df_ven[df_ven['Fecha'] >= cutoff_90]
    
    stats = {}
    mapa_nombre_id = dict(zip(df_inv['Nombre'].str.strip().str.upper(), df_inv['ID_Producto_Norm']))
    mapa_id_nombre = dict(zip(df_inv['ID_Producto_Norm'], df_inv['Nombre'].str.strip().str.upper()))

    for _, row in ven_recent.iterrows():
        # Usar Items_Detalle si es JSON válido
        try:
            if str(row.get('Items_Detalle', '')).startswith('['):
                detalles = json.loads(row['Items_Detalle'])
                for d in detalles:
                    # Usa ID_Producto_Norm si existe, si no usa ID
                    id_norm = normalizar_id_producto(d.get('ID_Producto_Norm', d.get('ID', '')))
                    qty = float(d.get('Cantidad', 1))
                    fecha = row['Fecha']
                    if id_norm not in stats: stats[id_norm] = {'v90': 0, 'v30': 0}
                    stats[id_norm]['v90'] += qty
                    if fecha >= cutoff_30: stats[id_norm]['v30'] += qty
                continue
        except: pass

        # Si falla, usar Items por nombre
        items_str = str(row.get('Items', ''))
        lista = items_str.split(',')
        for item in lista:
            if not item.strip(): continue
            qty = 1
            nombre = item.strip()
            if 'x' in item.lower():
                parts = item.lower().split('x', 1)
                if parts[0].strip().isdigit():
                    qty = int(parts[0].strip())
                    nombre = parts[1].strip()
            # Buscar por nombre o por ID
            id_norm = mapa_nombre_id.get(nombre.upper())
            if not id_norm and nombre.isdigit():
                id_norm = normalizar_id_producto(nombre)
            if id_norm:
                if id_norm not in stats: stats[id_norm] = {'v90': 0, 'v30': 0}
                stats[id_norm]['v90'] += qty
                if row['Fecha'] >= cutoff_30: stats[id_norm]['v30'] += qty
    return stats

def calcular_master_df():
    data = st.session_state['data_store']
    df_inv, df_prov, df_ven = data['df_Inventario'], data['df_Maestro_Proveedores'], data['df_Ventas']
    
    stats = analizar_ventas(df_ven, df_inv)
    
    if not df_prov.empty:
        df_prov_clean = df_prov.sort_values('Costo_Proveedor').drop_duplicates('SKU_Interno_Norm')
        master = pd.merge(df_inv, df_prov_clean[['SKU_Interno_Norm', 'Nombre_Proveedor', 'Costo_Proveedor', 'Factor_Pack']], 
                          left_on='ID_Producto_Norm', right_on='SKU_Interno_Norm', how='left')
    else:
        master = df_inv.copy()
        master['Nombre_Proveedor'] = 'Generico'
        master['Costo_Proveedor'] = master['Costo']
        master['Factor_Pack'] = 1

    master['Nombre_Proveedor'] = master['Nombre_Proveedor'].fillna('Sin Asignar')
    master['Costo_Proveedor'] = np.where(master['Costo_Proveedor'].isna() | (master['Costo_Proveedor'] <= 0), master['Costo'], master['Costo_Proveedor'])
    master['Factor_Pack'] = np.where(master['Factor_Pack'].isna() | (master['Factor_Pack'] <= 0), 1, master['Factor_Pack'])

    # Métricas Base
    master['v90'] = master['ID_Producto_Norm'].map(lambda x: stats.get(x, {}).get('v90', 0))
    master['v30'] = master['ID_Producto_Norm'].map(lambda x: stats.get(x, {}).get('v30', 0))
    # Ajusta velocidad mínima si hay ventas en 30 días
    master['Velocidad_Diaria'] = np.where(master['v30'] > 0, master['v30']/30, master['v90']/90)
    master['Velocidad_Diaria'] = pd.to_numeric(master["Velocidad_Diaria"], errors="coerce").fillna(0.0)

    # (quita el piso artificial 0.033 para no inflar compras de productos sin rotación)
    # master['Velocidad_Diaria'] = np.where(master['Velocidad_Diaria'] < 0.033, 0.033, master['Velocidad_Diaria'])

    master["Dias_Cobertura"] = np.where(
        master["Velocidad_Diaria"] > 0,
        master["Stock"] / master["Velocidad_Diaria"],
        999,
    )

    # === FINANZAS Y MÁRGENES ===
    master['Margen_$'] = master['Precio'] - master['Costo']
    master['Margen_%'] = np.where(master['Precio'] > 0, (master['Margen_$'] / master['Precio']), 0)

    # === CLASIFICACIÓN ABC (Ley de Pareto) ===
    master['Ingresos_Proyectados_90d'] = master['v90'] * master['Precio']
    total_ingresos = master['Ingresos_Proyectados_90d'].sum()

    if total_ingresos > 0:
        master = master.sort_values('Ingresos_Proyectados_90d', ascending=False)
        master['Cum_Rev_Pct'] = master['Ingresos_Proyectados_90d'].cumsum() / total_ingresos
        master['Clase_ABC'] = pd.cut(master['Cum_Rev_Pct'], bins=[-1, 0.8, 0.95, 2], labels=['A', 'B', 'C'])
    else:
        master['Clase_ABC'] = 'C'

    # === LÓGICA DE COMPRAS DINÁMICA ===
    DIAS_OBJETIVO = 8          # <-- pedido: no quedarse sin nada en 8 días
    DIAS_SEGURIDAD = 1         # colchón pequeño (capital bajo)
    LEAD_TIME_DIAS = 5         # si tu proveedor demora menos, bájalo (ej: 2-3)

    # Factor pack seguro
    master["Factor_Pack"] = pd.to_numeric(master.get("Factor_Pack", 1), errors="coerce").fillna(1.0)
    master["Factor_Pack"] = np.where(master["Factor_Pack"] <= 0, 1.0, master["Factor_Pack"])

    stock_seguridad = master["Velocidad_Diaria"] * DIAS_SEGURIDAD
    punto_reorden = (master["Velocidad_Diaria"] * LEAD_TIME_DIAS) + stock_seguridad
    stock_objetivo = (master["Velocidad_Diaria"] * DIAS_OBJETIVO) + stock_seguridad

    # ✅ Solo comprar si hay rotación (>0)
    master["Requiere_Compra"] = (master["Velocidad_Diaria"] > 0) & (master["Stock"] <= punto_reorden)

    master["Faltante"] = np.where(
        master["Requiere_Compra"],
        np.maximum(0, stock_objetivo - master["Stock"]),
        0,
    )

    master["Sugerencia_Cajas"] = np.ceil(master["Faltante"] / master["Factor_Pack"])
    master["Unidades_Pedir"] = master["Sugerencia_Cajas"] * master["Factor_Pack"]

    # Costo proveedor ya lo manejas arriba; mantener
    master["Inversion_Est"] = master["Unidades_Pedir"] * master["Costo_Proveedor"]

    # === ALERTAS DE ESTADO ===
    conditions = [
        (master['Stock'] <= 0),
        (master['Requiere_Compra'] == True) & (master['Clase_ABC'] == 'A'),
        (master['Requiere_Compra'] == True),
        (master['Dias_Cobertura'] > 120) & (master['Stock'] > 0)
    ]
    choices = ["💀 AGOTADO", "🚨 CRÍTICO (A)", "⚠️ Comprar", "🧊 Sobre-Stock"]
    master['Estado'] = np.select(conditions, choices, default="✅ OK")

    return master

# (Las funciones crear_orden_compra y procesar_recepcion se mantienen igual, usando las lógicas del script anterior)
def crear_orden_compra(proveedor, items_df):
    data = st.session_state["data_store"]
    ws_ord = data["ws_Historial_Ordenes"]

    # Guardar UID para recepción 100% confiable
    cols = ["Producto_UID", "ID_Producto", "ID_Producto_Norm", "Nombre", "Sugerencia_Cajas", "Unidades_Pedir", "Costo_Proveedor"]
    for c in cols:
        if c not in items_df.columns:
            items_df[c] = ""

    detalles = items_df[cols].to_dict("records")
    total = items_df["Inversion_Est"].sum()
    id_orden = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    row = [id_orden, proveedor, str(date.today()), json.dumps(detalles), total, "Pendiente"]
    safe_google_op(ws_ord.append_row, row)

    new_df_row = pd.DataFrame([row], columns=data["df_Historial_Ordenes"].columns)
    data["df_Historial_Ordenes"] = pd.concat([data["df_Historial_Ordenes"], new_df_row], ignore_index=True)
    st.session_state["data_store"] = data
    return id_orden

def procesar_recepcion(id_orden, items_json):
    data = st.session_state["data_store"]
    ws_inv, ws_ord = data["ws_Inventario"], data["ws_Historial_Ordenes"]
    df_inv = data["df_Inventario"]
    items = json.loads(items_json)

    progreso = st.progress(0)

    # ubicar columnas en DF local
    if "Producto_UID" not in df_inv.columns:
        df_inv["Producto_UID"] = ""
    df_inv["Producto_UID"] = df_inv["Producto_UID"].fillna("").astype(str).str.strip()

    for i, item in enumerate(items):
        uid = str(item.get("Producto_UID", "")).strip()
        prod_id = str(item.get("ID_Producto", "")).strip()
        cantidad = float(item.get("Unidades_Pedir", 0) or 0)

        cell = None
        if uid:
            cell = safe_google_op(ws_inv.find, uid)
        if (cell is None) and prod_id:
            cell = safe_google_op(ws_inv.find, prod_id)

        if cell:
            col_stock = df_inv.columns.get_loc("Stock") + 1
            current = float(safe_google_op(ws_inv.cell, cell.row, col_stock).value or 0)
            safe_google_op(ws_inv.update_cell, cell.row, col_stock, current + cantidad)

            # Update local por UID preferido
            if uid:
                idx = df_inv[df_inv["Producto_UID"] == uid].index
            else:
                idx = df_inv[df_inv["ID_Producto"] == prod_id].index
            if not idx.empty:
                df_inv.at[idx[0], "Stock"] = float(df_inv.at[idx[0], "Stock"] or 0) + cantidad

        progreso.progress((i + 1) / len(items))

    cell_ord = safe_google_op(ws_ord.find, id_orden)
    if cell_ord:
        col_est = data["df_Historial_Ordenes"].columns.get_loc("Estado") + 1
        safe_google_op(ws_ord.update_cell, cell_ord.row, col_est, "Recibido")
        idx_ord = data["df_Historial_Ordenes"][data["df_Historial_Ordenes"]["ID_Orden"] == id_orden].index
        if not idx_ord.empty: data["df_Historial_Ordenes"].at[idx_ord[0], "Estado"] = "Recibido"

    st.success("Ingresado con éxito al Sistema de Inventario.")
    time.sleep(1)
    st.rerun()

# ==========================================
# 5. INTERFAZ GRÁFICA (SUPER PODEROSA)
# ==========================================

def main():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/1864/1864470.png", width=80)
        st.header("Centro de Mando")
        
        if 'data_store' not in st.session_state:
            cargar_datos_snapshot()
        
        st.info(f"Última sinc: {st.session_state.get('last_sync', datetime.min).strftime('%H:%M:%S')}")
        if st.button("🔄 Forzar Sincronización"):
            st.cache_resource.clear()
            cargar_datos_snapshot()
            st.rerun()
            
        st.markdown("---")
        st.subheader("🎯 Filtros Globales")
        
        if 'data_store' in st.session_state:
            categorias = st.session_state['data_store']['df_Inventario']['Categoria'].unique().tolist()
            cat_filter = st.multiselect("Filtrar por Categoría", categorias, default=[])
            abc_filter = st.multiselect("Clasificación ABC", ['A', 'B', 'C'], default=[])

    if 'data_store' not in st.session_state:
        st.error("No hay datos cargados.")
        return

    # Generación de Datos
    master_df = calcular_master_df()
    
    # Aplicar Filtros Globales
    if cat_filter: master_df = master_df[master_df['Categoria'].isin(cat_filter)]
    if abc_filter: master_df = master_df[master_df['Clase_ABC'].isin(abc_filter)]

    # --- MÉTRICAS DE IMPACTO ---
    st.title("🐾 Panel Principal de Operaciones")
    
    c1, c2, c3, c4 = st.columns(4)
    valor_inv = (master_df['Stock'] * master_df['Costo']).sum()
    agotados = master_df[master_df['Stock'] <= 0].shape[0]
    margen_promedio = master_df[master_df['Stock'] > 0]['Margen_%'].mean() * 100
    df_gastos = st.session_state['data_store']['df_Gastos']
    gastos_mes = df_gastos[df_gastos['Fecha'].dt.month == datetime.now().month]['Monto'].sum() if not df_gastos.empty else 0

    c1.metric("💰 Capital en Inventario", f"${valor_inv:,.0f}")
    c2.metric("📈 Margen Promedio", f"{margen_promedio:.1f}%")
    c3.metric("🚨 Alertas de Quiebre", agotados + master_df[master_df['Estado'] == '🚨 CRÍTICO (A)'].shape[0])
    c4.metric("💸 Gastos del Mes", f"${gastos_mes:,.0f}")

    tabs = st.tabs(["📊 Visión 360", "🧠 Compras Inteligentes", "📥 Recepción", "💸 Finanzas & Gastos"])

    # === TAB 1: VISIÓN 360 ===
    with tabs[0]:
        c_busq, c_est = st.columns([2, 1])
        txt_search = c_busq.text_input("🔍 Búsqueda Rápida (Nombre, SKU, ID)...")
        est_filter = c_est.selectbox("Filtrar por Estado de Stock", ["Todos", "💀 AGOTADO", "🚨 CRÍTICO (A)", "⚠️ Comprar", "🧊 Sobre-Stock", "✅ OK"])
        
        df_view = master_df.copy()
        if txt_search:
            df_view = df_view[df_view['Nombre'].str.contains(txt_search, case=False) | df_view['ID_Producto_Norm'].str.contains(txt_search, case=False)]
        if est_filter != "Todos":
            df_view = df_view[df_view['Estado'] == est_filter]

        # --- NUEVO: Botón para descargar Excel de conteo físico ---
        st.markdown("### 📋 Descargar Formato de Conteo Físico")
        conteo_excel = descargar_excel_conteo(df_view[['ID_Producto', 'Nombre', 'Categoria', 'Stock']].reset_index(drop=True))
        st.download_button(
            label="⬇️ Descargar Excel de Conteo Físico",
            data=conteo_excel,
            file_name="Conteo_Fisico_BigotesyPatitas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.dataframe(
            df_view[['ID_Producto', 'Nombre', 'Categoria', 'Clase_ABC', 'Stock', 'Estado', 'Velocidad_Diaria', 'Margen_%', 'Costo', 'Precio']],
            column_config={
                "Clase_ABC": st.column_config.TextColumn("ABC", help="A: Genera el 80% de ingresos. C: Baja rotación."),
                "Velocidad_Diaria": st.column_config.NumberColumn("Ventas/Día", format="%.2f"),
                "Margen_%": st.column_config.NumberColumn("Margen Bruto", format="%.1f%%", help="Ganancia sobre el precio de venta"),
                "Costo": st.column_config.NumberColumn(format="$%.0f"),
                "Precio": st.column_config.NumberColumn(format="$%.0f")
            },
            use_container_width=True, hide_index=True, height=500
        )

    # === TAB 2: COMPRAS INTELIGENTES ===
    with tabs[1]:
        st.markdown("### Algoritmo de Sugerencia de Reabastecimiento")
        st.info("💡 **¿Cómo funciona?** El sistema asegura stock para **45 días** de los productos Clase A, **30 días** para los B, y **15 días** para los C, basándose en la velocidad de venta de los últimos 90 días y teniendo en cuenta los empaques del proveedor.")
        
        df_buy = master_df[master_df['Unidades_Pedir'] > 0].copy()
        if df_buy.empty:
            st.success("🎉 ¡Niveles óptimos! El algoritmo no sugiere compras en este momento.")
        else:
            df_buy['Confirmar'] = True
            df_buy = df_buy.sort_values(['Clase_ABC', 'Nombre_Proveedor'])
            
            edited_buy = st.data_editor(
                df_buy[['Confirmar', 'Nombre_Proveedor', 'Clase_ABC', 'Nombre', 'Stock', 'Sugerencia_Cajas', 'Factor_Pack', 'Inversion_Est']],
                column_config={
                    "Inversion_Est": st.column_config.NumberColumn("Inversión $", format="$%.0f", disabled=True),
                    "Sugerencia_Cajas": st.column_config.NumberColumn("📦 Cajas a Pedir", step=1),
                },
                use_container_width=True, hide_index=True
            )
            
            seleccion = edited_buy[edited_buy['Confirmar'] == True]
            st.divider()
            
            st.markdown(f"### Total de Inversión Sugerida: :green[${seleccion['Inversion_Est'].sum():,.0f}]")
            
            for prov in seleccion['Nombre_Proveedor'].unique():
                items_prov = seleccion[seleccion['Nombre_Proveedor'] == prov]
                with st.expander(f"🛒 Proveedor: {prov} | Total: ${items_prov['Inversion_Est'].sum():,.0f}", expanded=True):
                    st.table(items_prov[['Nombre', 'Clase_ABC', 'Sugerencia_Cajas', 'Inversion_Est']])
                    
                    c_btn, c_wa = st.columns([1, 4])
                    if c_btn.button(f"Emitir Orden ({prov})", key=f"btn_{prov}"):
                        new_id = crear_orden_compra(prov, items_prov)
                        st.success(f"Orden {new_id} generada y registrada en el historial.")
                        time.sleep(1.5)
                        st.rerun()
                    
                    # Generar texto de WhatsApp
                    msg = f"Hola {prov}, solicito el siguiente pedido para Bigotes & Paticas:\n"
                    for _, r in items_prov.iterrows(): msg += f"- {r['Sugerencia_Cajas']} cajas de {r['Nombre']}\n"
                    link = f"https://wa.me/?text={quote(msg)}"
                    c_wa.markdown(f"*(Opcional)* [📲 Enviar pedido por WhatsApp]({link})", unsafe_allow_html=True)

    # === TAB 3: RECEPCIÓN ===
    with tabs[2]:
        df_ord = st.session_state['data_store']['df_Historial_Ordenes']
        if df_ord.empty: st.info("No hay órdenes registradas.")
        else:
            pendientes = df_ord[df_ord['Estado'] == 'Pendiente']
            if pendientes.empty: st.success("Todo al día. No hay mercancía en tránsito.")
            else:
                opcion = st.selectbox("Órdenes en Tránsito", pendientes['ID_Orden'] + " | " + pendientes['Proveedor'])
                id_sel = opcion.split(" | ")[0]
                row_ord = pendientes[pendientes['ID_Orden'] == id_sel].iloc[0]
                
                st.write(f"**Fecha Emitida:** {row_ord['Fecha_Orden']} | **Valor:** ${float(row_ord['Total_Dinero']):,.0f}")
                try:
                    df_det = pd.DataFrame(json.loads(row_ord['Items_JSON']))
                    st.dataframe(df_det[['Nombre', 'Unidades_Pedir']], hide_index=True)
                    if st.button("📦 Recibir y Actualizar Stock", type="primary"):
                        procesar_recepcion(id_sel, row_ord['Items_JSON'])
                except: st.error("Error leyendo detalles.")

    # === TAB 4: FINANZAS & GASTOS ===
    with tabs[3]:
        st.subheader("💸 Control de Egresos y Márgenes")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("**Top 5 Productos más Rentables (Por Margen de Ganancia)**")
            top_margen = master_df.sort_values('Margen_$', ascending=False).head(5)
            st.dataframe(top_margen[['Nombre', 'Costo', 'Precio', 'Margen_$']], hide_index=True)
            
        with col_g2:
            st.markdown("**Resumen de Gastos Registrados**")
            if not df_gastos.empty:
                resumen_gastos = df_gastos.groupby('Categoria')['Monto'].sum().reset_index()
                st.dataframe(resumen_gastos, hide_index=True)
            else:
                st.info("Aún no hay gastos registrados en la pestaña de Gastos.")

def descargar_excel_conteo(df, nombre_archivo="Conteo_Fisico.xlsx"):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Conteo Físico")

    # --- Formatos ---
    header_format = workbook.add_format({
        'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#187f77',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 12
    })
    cell_format = workbook.add_format({'border': 1, 'font_size': 11, 'align': 'left'})
    stock_format = workbook.add_format({'border': 1, 'font_size': 11, 'align': 'center', 'bg_color': '#f5a641', 'bold': True})
    conteo_format = workbook.add_format({'border': 1, 'font_size': 12, 'align': 'center', 'bg_color': '#f8f9fa', 'bold': True})

    # --- Título y branding ---
    worksheet.merge_range('A1:H1', 'CONTEO FÍSICO DE INVENTARIO - BIGOTES Y PATITAS', header_format)
    worksheet.write('A2', 'Fecha de generación:', cell_format)
    worksheet.write('B2', datetime.now().strftime('%Y-%m-%d %H:%M'), cell_format)

    # --- Encabezados en fila 3 ---
    headers = ["#", "ID Producto", "Nombre Producto", "Categoría", "Stock Sistema", "Conteo Físico", "Diferencia", "Observaciones"]
    worksheet.write_row(2, 0, headers, header_format)

    # --- Datos desde fila 4 ---
    for idx, row in df.iterrows():
        worksheet.write(idx+3, 0, idx+1, cell_format)  # Número consecutivo
        worksheet.write(idx+3, 1, row['ID_Producto'], cell_format)
        worksheet.write(idx+3, 2, row['Nombre'], cell_format)
        worksheet.write(idx+3, 3, row.get('Categoria', ''), cell_format)
        worksheet.write(idx+3, 4, row['Stock'], stock_format)
        worksheet.write(idx+3, 5, "", conteo_format)  # Para que escriban el conteo físico
        worksheet.write_formula(idx+3, 6, f"=F{idx+4}-E{idx+4}", conteo_format)  # Diferencia
        worksheet.write(idx+3, 7, "", cell_format)  # Observaciones

    # --- Ajuste de columnas ---
    worksheet.set_column('A:A', 5)
    worksheet.set_column('B:B', 18)
    worksheet.set_column('C:C', 38)
    worksheet.set_column('D:D', 18)
    worksheet.set_column('E:E', 14)
    worksheet.set_column('F:F', 14)
    worksheet.set_column('G:G', 14)
    worksheet.set_column('H:H', 24)

    workbook.close()
    output.seek(0)
    return output

if __name__ == "__main__":
    main()