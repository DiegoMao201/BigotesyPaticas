import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta
import math

# ==========================================
# 1. CONFIGURACIÓN "NEXUS PLATINUM"
# ==========================================

st.set_page_config(
    page_title="Nexus: Inventory & Procurement AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS Profesionales
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; color: #1e293b; }
    .stApp { background-color: #f8fafc; }
    
    /* KPI Cards */
    div[data-testid="metric-container"] {
        background: white;
        padding: 15px 20px;
        border-radius: 12px;
        border-left: 5px solid #6366f1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Headers */
    h1 { color: #0f172a; font-weight: 800; }
    h2, h3 { color: #334155; font-weight: 600; }
    
    /* Tablas */
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    
    /* Botones de Acción */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES DE LIMPIEZA ROBUSTA
# ==========================================

def clean_currency_latam(val):
    """
    Limpia formatos de moneda latinos (1.000,00) y US (1,000.00).
    Prioriza la coma como decimal si existe ambigüedad latina.
    """
    if isinstance(val, (int, float, np.number)):
        return float(val)
    
    if isinstance(val, str):
        val = val.replace('$', '').replace('€', '').replace('COP', '').replace(' ', '').strip()
        if not val: return 0.0
        
        # Lógica heurística
        if '.' in val and ',' in val:
            if val.find('.') < val.find(','): # 1.000,00
                val = val.replace('.', '').replace(',', '.')
            else: # 1,000.00
                val = val.replace(',', '')
        elif ',' in val:
            parts = val.split(',')
            if len(parts[-1]) == 2 or len(parts[-1]) == 1: # Decimales (,00 o ,5)
                val = val.replace(',', '.')
            else:
                val = val.replace(',', '') # Miles
        elif '.' in val:
            if val.count('.') > 1: # 1.000.000
                val = val.replace('.', '')
            else:
                parts = val.split('.')
                if len(parts[-1]) == 3: # 1.500 (mil quinientos)
                    val = val.replace('.', '')
                # Si no, asume decimal normal
        
        try: return float(val)
        except: return 0.0
    return 0.0

def safe_int(val):
    try: return int(float(val))
    except: return 1

# ==========================================
# 3. CONEXIÓN Y CARGA DE DATOS
# ==========================================

@st.cache_resource
def conectar_db():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Faltan secretos de Google Service Account.")
            return None, None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        try: ws_inv = sh.worksheet("Inventario")
        except: ws_inv = None
        
        try: ws_ven = sh.worksheet("Ventas")
        except: ws_ven = None
        
        try: ws_prov = sh.worksheet("Maestro_Proovedores")
        except: ws_prov = None
            
        return ws_inv, ws_ven, ws_prov
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return None, None, None

def normalizar_columnas(df):
    # Evita columnas duplicadas que rompen Pandas/Plotly
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique(): 
        cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols
    return df

@st.cache_data(ttl=300)
def obtener_datos(_ws_inv, _ws_ven, _ws_prov):
    # --- 1. INVENTARIO ---
    if not _ws_inv: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df_inv = pd.DataFrame(_ws_inv.get_all_records())
    mapa_inv = {
        'ID_Producto': 'ID', 'SKU_Proveedor': 'SKU', 'Nombre': 'Nombre',
        'Stock': 'Stock', 'Precio': 'Precio', 'Costo': 'Costo', 'Categoria': 'Categoria'
    }
    # Renombrar si las columnas existen
    df_inv = df_inv.rename(columns={k:v for k,v in mapa_inv.items() if k in df_inv.columns})
    df_inv = normalizar_columnas(df_inv)
    
    # Limpieza numérica
    for col in ['Stock', 'Precio', 'Costo']:
        if col in df_inv.columns:
            df_inv[col] = df_inv[col].apply(clean_currency_latam)
    if 'Stock' in df_inv.columns: df_inv['Stock'] = df_inv['Stock'].fillna(0)

    # --- 2. VENTAS ---
    df_ven = pd.DataFrame()
    if _ws_ven:
        df_ven = pd.DataFrame(_ws_ven.get_all_records())
        if not df_ven.empty:
            df_ven = df_ven.rename(columns={'Fecha': 'Fecha', 'Items': 'Items'})
            df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')

    # --- 3. PROVEEDORES (NUEVO REQUERIMIENTO) ---
    df_prov = pd.DataFrame()
    if _ws_prov:
        df_prov = pd.DataFrame(_ws_prov.get_all_records())
        # Asegurar tipos de datos en proveedores
        if 'Factor_Pack' in df_prov.columns:
            df_prov['Factor_Pack'] = df_prov['Factor_Pack'].apply(safe_int)
        else:
            df_prov['Factor_Pack'] = 1 # Default

    return df_inv, df_ven, df_prov

# ==========================================
# 4. MOTOR LÓGICO Y CÁLCULOS
# ==========================================

def procesar_logica(df_inv, df_ven, df_prov):
    if df_inv.empty: return pd.DataFrame(), pd.DataFrame()

    # --- A. CÁLCULO DE VELOCIDAD DE VENTAS ---
    ventas_90d = {}
    historial_ventas = []
    
    if not df_ven.empty:
        cutoff = datetime.now() - timedelta(days=90)
        df_ven_act = df_ven[df_ven['Fecha'] >= cutoff]
        
        for _, row in df_ven_act.iterrows():
            items = str(row.get('Items', ''))
            fecha = row['Fecha']
            if items and items.lower() != 'nan':
                for p_str in items.split(','):
                    try:
                        p_str = p_str.strip()
                        cant = 1
                        nombre = p_str
                        if "(x" in p_str:
                            parts = p_str.split("(x")
                            nombre = parts[0].strip()
                            cant = int(parts[1].replace(")", ""))
                        
                        ventas_90d[nombre] = ventas_90d.get(nombre, 0) + cant
                        historial_ventas.append({'Fecha': fecha, 'Nombre': nombre, 'Cantidad': cant})
                    except: continue

    # --- B. MERGE INVENTARIO + VENTAS ---
    df_metrics = pd.DataFrame(list(ventas_90d.items()), columns=['Nombre', 'Ventas_90d'])
    df_master = pd.merge(df_inv, df_metrics, on='Nombre', how='left')
    
    # Rellenar vacíos críticos para evitar errores
    df_master['Ventas_90d'] = df_master['Ventas_90d'].fillna(0)
    df_master['Velocidad_Diaria'] = df_master['Ventas_90d'] / 90
    df_master['Costo'] = df_master['Costo'].replace(0, 0.01)
    df_master['Precio'] = df_master['Precio'].replace(0, 0.01)
    
    # --- C. MERGE CON PROVEEDORES (NUEVO) ---
    # Usamos SKU del Inventario vs SKU_Interno del Proveedor
    if not df_prov.empty and 'SKU_Interno' in df_prov.columns:
        # Asegurar que ambos sean strings para el merge
        df_master['SKU'] = df_master['SKU'].astype(str).str.strip()
        df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str).str.strip()
        
        # Merge
        df_master = pd.merge(df_master, df_prov, left_on='SKU', right_on='SKU_Interno', how='left')
        
        # Rellenar datos de proveedor faltantes
        if 'Nombre_Proveedor' not in df_master.columns: df_master['Nombre_Proveedor'] = 'Desconocido'
        df_master['Nombre_Proveedor'] = df_master['Nombre_Proveedor'].fillna('Genérico')
        df_master['Factor_Pack'] = df_master['Factor_Pack'].fillna(1)
    else:
        df_master['Nombre_Proveedor'] = 'No Configurado'
        df_master['Factor_Pack'] = 1

    # --- D. LÓGICA DE REABASTECIMIENTO ---
    LEAD_TIME = 15 # Días
    SAFETY_STOCK_DAYS = 7 
    
    df_master['Punto_Reorden'] = (df_master['Velocidad_Diaria'] * LEAD_TIME) + (df_master['Velocidad_Diaria'] * SAFETY_STOCK_DAYS)
    df_master['Stock_Objetivo'] = df_master['Punto_Reorden'] * 2 # Queremos stock para el doble del tiempo
    
    # Cálculo de Unidades a Pedir
    df_master['Unidades_Faltantes'] = (df_master['Stock_Objetivo'] - df_master['Stock']).clip(lower=0)
    
    # Lógica de Packs (Round Up)
    df_master['Packs_A_Pedir'] = np.ceil(df_master['Unidades_Faltantes'] / df_master['Factor_Pack'])
    df_master['Inversion_Estimada'] = df_master['Unidades_Faltantes'] * df_master['Costo']

    # Estados
    df_master['Estado'] = "✅ OK"
    df_master.loc[df_master['Stock'] == 0, 'Estado'] = "🚨 AGOTADO"
    df_master.loc[(df_master['Stock'] > 0) & (df_master['Stock'] <= df_master['Punto_Reorden']), 'Estado'] = "⚠️ Reordenar"
    
    # Cálculo Financiero
    df_master['Valor_Inv_Costo'] = df_master['Stock'] * df_master['Costo']
    
    # Limpieza final para el Sunburst (SOLUCIÓN DEL ERROR)
    if 'Categoria' not in df_master.columns: df_master['Categoria'] = 'Sin Categoria'
    df_master['Categoria'] = df_master['Categoria'].fillna('General').replace('', 'General')
    df_master['Nombre'] = df_master['Nombre'].fillna('Sin Nombre')
    
    return df_master, pd.DataFrame(historial_ventas)

# ==========================================
# 5. GENERADOR DE ORDEN DE COMPRA (EXCEL)
# ==========================================

def generar_orden_compra(df_compras):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Hoja Resumen
        df_compras.to_excel(writer, sheet_name='Orden_Global', index=False)
        
        # Hoja por Proveedor
        proveedores = df_compras['Nombre_Proveedor'].unique()
        for prov in proveedores:
            # Limpiar nombre hoja excel (max 31 chars)
            sheet_name = str(prov)[:30].replace('/', '-')
            df_p = df_compras[df_compras['Nombre_Proveedor'] == prov]
            df_p.to_excel(writer, sheet_name=sheet_name, index=False)
            
    return output.getvalue()

# ==========================================
# 6. INTERFAZ DE USUARIO PRINCIPAL
# ==========================================

def main():
    # --- CARGA ---
    ws_inv, ws_ven, ws_prov = conectar_db()
    if not ws_inv: return

    with st.spinner("🧠 Sincronizando Cerebro Nexus..."):
        df_inv_raw, df_ven_raw, df_prov_raw = obtener_datos(ws_inv, ws_ven, ws_prov)
        
        if df_inv_raw.empty:
            st.error("El inventario está vacío. Revisa la hoja de Google Sheets.")
            return

        df_master, df_hist = procesar_logica(df_inv_raw, df_ven_raw, df_prov_raw)

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("Nexus Control")
        st.caption("v.Platinum Edition")
        st.metric("Total SKUs", len(df_master))
        if 'Nombre_Proveedor' in df_master.columns:
            provs_count = df_master['Nombre_Proveedor'].nunique()
            st.metric("Proveedores Activos", provs_count)

    # --- HEADER KPIS ---
    c1, c2, c3, c4 = st.columns(4)
    inv_val = df_master['Valor_Inv_Costo'].sum()
    compra_nec = df_master[df_master['Unidades_Faltantes'] > 0]['Inversion_Estimada'].sum()
    agotados = len(df_master[df_master['Estado'] == "🚨 AGOTADO"])
    
    c1.metric("Valor Inventario", f"${inv_val:,.0f}")
    c2.metric("Inversión Requerida", f"${compra_nec:,.0f}", delta="Para Stock Óptimo", delta_color="inverse")
    c3.metric("Productos Agotados", agotados, delta="Crítico", delta_color="inverse")
    c4.metric("Nivel de Servicio", f"{(1 - (agotados/len(df_master)))*100:.1f}%")

    st.markdown("---")

    # --- TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🛒 Centro de Compras", "🤖 Tendencias IA", "📁 Datos"])

    # ----------------------------------------------------
    # TAB 1: DASHBOARD (CON FIX DE ERROR SUNBURST)
    # ----------------------------------------------------
    with tab1:
        st.subheader("Mapa de Capital y Riesgo")
        
        # FILTRO DE SEGURIDAD PARA EL ERROR SUNBURST
        # Eliminamos filas con valor 0 o negativo para el gráfico, y rellenamos nulos
        df_plot = df_master.copy()
        df_plot = df_plot[df_plot['Valor_Inv_Costo'] > 0] # Sunburst falla con 0
        
        if not df_plot.empty:
            try:
                fig_sun = px.sunburst(
                    df_plot,
                    path=['Categoria', 'Estado', 'Nombre'],
                    values='Valor_Inv_Costo',
                    color='Estado',
                    color_discrete_map={
                        "✅ OK": "#10b981", 
                        "⚠️ Reordenar": "#f59e0b", 
                        "🚨 AGOTADO": "#ef4444"
                    },
                    title="Distribución de Dinero en Inventario"
                )
                fig_sun.update_layout(height=600)
                st.plotly_chart(fig_sun, use_container_width=True)
            except Exception as e:
                st.warning(f"No se pudo generar el gráfico detallado: {e}")
                st.bar_chart(df_master['Estado'].value_counts())
        else:
            st.info("El inventario actual tiene valor 0, no se puede graficar el mapa de calor financiero.")

    # ----------------------------------------------------
    # TAB 2: CENTRO DE COMPRAS (NUEVO REQUERIMIENTO)
    # ----------------------------------------------------
    with tab2:
        st.header("Gestión de Abastecimiento")
        
        # Filtro: Solo lo que necesita compra
        df_compras = df_master[df_master['Unidades_Faltantes'] > 0].copy()
        
        if df_compras.empty:
            st.balloons()
            st.success("✅ ¡Todo está en orden! No se requieren compras en este momento.")
        else:
            c_filter1, c_filter2 = st.columns([1, 3])
            with c_filter1:
                prov_filter = st.multiselect("Filtrar por Proveedor", df_compras['Nombre_Proveedor'].unique())
            
            if prov_filter:
                df_compras = df_compras[df_compras['Nombre_Proveedor'].isin(prov_filter)]

            # Tabla Interactiva de Compra
            st.markdown("### 📋 Sugerencia de Pedido")
            
            cols_view = ['SKU', 'Nombre', 'Nombre_Proveedor', 'Stock', 'Stock_Objetivo', 
                         'Factor_Pack', 'Packs_A_Pedir', 'Inversion_Estimada']
            
            # Formateo de columnas para mostrar solo lo que existe
            cols_final = [c for c in cols_view if c in df_compras.columns]
            
            st.dataframe(
                df_compras[cols_final].sort_values('Nombre_Proveedor'),
                column_config={
                    "Packs_A_Pedir": st.column_config.NumberColumn("📦 PACKS A PEDIR", format="%.0f"),
                    "Inversion_Estimada": st.column_config.NumberColumn("Costo Aprox", format="$%.2f"),
                    "Factor_Pack": st.column_config.NumberColumn("Unidades/Pack", help="Cuántas unidades vienen en una caja")
                },
                use_container_width=True,
                hide_index=True
            )
            
            total_pedido = df_compras['Inversion_Estimada'].sum()
            st.markdown(f"### 💰 Total Orden: **${total_pedido:,.2f}**")
            
            # Botón Generador
            excel_data = generar_orden_compra(df_compras[cols_final])
            st.download_button(
                label="📥 Generar Órdenes de Compra (Excel)",
                data=excel_data,
                file_name=f"Orden_Compra_Nexus_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

    # ----------------------------------------------------
    # TAB 3: TENDENCIAS IA
    # ----------------------------------------------------
    with tab3:
        st.subheader("IA Predictiva")
        if not df_hist.empty:
            df_hist['Fecha'] = pd.to_datetime(df_hist['Fecha'])
            # Agrupar por semana
            ventas_time = df_hist.groupby([pd.Grouper(key='Fecha', freq='W-MON'), 'Nombre'])['Cantidad'].sum().reset_index()
            
            prods = st.multiselect("Analizar Tendencia:", df_master['Nombre'].unique())
            if prods:
                data_chart = ventas_time[ventas_time['Nombre'].isin(prods)]
                fig_line = px.line(data_chart, x='Fecha', y='Cantidad', color='Nombre', markers=True)
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Selecciona productos para ver su evolución temporal.")
        else:
            st.warning("No hay suficientes datos de ventas para generar tendencias.")

    # ----------------------------------------------------
    # TAB 4: DATOS CRUDOS
    # ----------------------------------------------------
    with tab4:
        st.dataframe(df_master)

if __name__ == "__main__":
    main()
