import streamlit as st
import pandas as pd
import gspread
from io import BytesIO
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS PROFESIONALES
# ==========================================

st.set_page_config(
    page_title="Master de Inventario & Compras",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS Avanzados (Coherentes con tu sistema ERP)
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    
    /* Headers */
    h1, h2, h3 { 
        color: #1e3a8a; 
        font-family: 'Segoe UI', Tahoma, sans-serif; 
        font-weight: 700;
    }
    
    /* Métricas KPI */
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Tablas */
    div[data-testid="stDataFrame"] {
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 4px;
        padding: 10px 20px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e3a8a !important;
        color: white !important;
    }
    
    /* Botones */
    .stButton button[type="primary"] {
        background: linear-gradient(90deg, #1e3a8a, #2563eb);
        border: none;
        font-weight: bold;
        transition: transform 0.1s;
    }
    .stButton button[type="primary"]:hover { transform: scale(1.02); }
    
    /* Alertas visuales en texto */
    .status-agotado { color: #dc2626; font-weight: bold; }
    .status-critico { color: #ea580c; font-weight: bold; }
    .status-ok { color: #16a34a; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y UTILIDADES ROBUSTAS
# ==========================================

@st.cache_resource(ttl=600)
def conectar_db():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos.")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Intentamos obtener las hojas, si fallan devolvemos None
        try: ws_inv = sh.worksheet("Inventario")
        except: ws_inv = None
        
        try: ws_ven = sh.worksheet("Ventas")
        except: ws_ven = None
            
        return ws_inv, ws_ven
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return None, None

def clean_currency(val):
    """Limpia strings de moneda a float seguro."""
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').strip()
        if not val: return 0.0
        try:
            val = val.replace(',', '') # Asumimos formato 1,000.00
            return float(val)
        except: return 0.0
    return 0.0

def leer_data(ws):
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # Limpieza automática de columnas numéricas clave
        cols_num = ['Precio', 'Stock', 'Costo', 'Total']
        for c in cols_num:
            if c in df.columns:
                df[c] = df[c].apply(clean_currency)
                
        # Estandarizar Fechas
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
            
        return df
    except Exception as e:
        st.error(f"Error leyendo datos: {e}")
        return pd.DataFrame()

# ==========================================
# 3. MOTOR ANALÍTICO (CEREBRO)
# ==========================================

def motor_analisis_360(df_inv, df_ven):
    """
    Realiza un análisis profundo: Rotación, Clasificación ABC, Cobertura y Rentabilidad.
    """
    if df_inv.empty: return pd.DataFrame()

    # --- A. ANÁLISIS DE VENTAS (VELOCIDAD) ---
    ventas_por_producto = {}
    
    if not df_ven.empty:
        # Filtramos últimos 30 días para tendencia reciente
        fecha_limite = datetime.now() - timedelta(days=30)
        df_ven_30 = df_ven[df_ven['Fecha'] >= fecha_limite]
        
        for _, row in df_ven_30.iterrows():
            items_str = str(row.get('Items', ''))
            # Parsear string tipo "Prod A (x2), Prod B (x1)"
            if items_str:
                parts = items_str.split(", ")
                for p in parts:
                    try:
                        if "(x" in p:
                            nombre = p.split(" (x")[0]
                            cant = int(p.split(" (x")[1].replace(")", ""))
                        else:
                            nombre = p
                            cant = 1
                        
                        ventas_por_producto[nombre] = ventas_por_producto.get(nombre, 0) + cant
                    except: continue

    # Crear DF de Rotación
    df_rot = pd.DataFrame(list(ventas_por_producto.items()), columns=['Nombre', 'Ventas_30d'])
    df_rot['Velocidad_Diaria'] = df_rot['Ventas_30d'] / 30

    # --- B. MERGE CON INVENTARIO ---
    # Usamos 'Nombre' como clave. En un sistema ideal sería SKU/ID.
    df_full = pd.merge(df_inv, df_rot, on='Nombre', how='left')
    
    # Relleno de ceros
    df_full['Ventas_30d'] = df_full['Ventas_30d'].fillna(0)
    df_full['Velocidad_Diaria'] = df_full['Velocidad_Diaria'].fillna(0)
    
    # --- C. CÁLCULOS FINANCIEROS Y OPERATIVOS ---
    
    # 1. Costo Estimado (si no existe, asumimos 70% del PVP)
    if 'Costo' not in df_full.columns:
        df_full['Costo'] = df_full['Precio'] * 0.7
    
    # 2. Valoración
    df_full['Valor_Stock_Costo'] = df_full['Stock'] * df_full['Costo']
    df_full['Valor_Stock_Venta'] = df_full['Stock'] * df_full['Precio']
    df_full['Utilidad_Potencial'] = df_full['Valor_Stock_Venta'] - df_full['Valor_Stock_Costo']
    
    # 3. Cobertura (Días de Inventario)
    def calc_cobertura(row):
        if row['Velocidad_Diaria'] <= 0: return 999 # Infinito (Hueso)
        return row['Stock'] / row['Velocidad_Diaria']
        
    df_full['Dias_Cobertura'] = df_full.apply(calc_cobertura, axis=1)
    
    # 4. Clasificación ABC (Pareto por Valor de Venta Potencial)
    # Ordenamos por Ventas * Precio (Revenue potencial de rotación)
    df_full['Revenue_30d'] = df_full['Ventas_30d'] * df_full['Precio']
    df_full = df_full.sort_values('Revenue_30d', ascending=False)
    
    total_rev = df_full['Revenue_30d'].sum()
    if total_rev > 0:
        df_full['Acumulado_Pct'] = df_full['Revenue_30d'].cumsum() / total_rev
        
        def clasificar_abc(pct):
            if pct <= 0.80: return 'A (Alta Rotación/Valor)'
            elif pct <= 0.95: return 'B (Media)'
            else: return 'C (Baja/Hueso)'
            
        df_full['Clasificacion_ABC'] = df_full['Acumulado_Pct'].apply(clasificar_abc)
    else:
        df_full['Clasificacion_ABC'] = 'C (Sin Ventas)'

    # 5. Estado y Sugerencia de Compra (Target 15 Días)
    DIAS_OBJETIVO = 15
    df_full['Stock_Ideal'] = np.ceil(df_full['Velocidad_Diaria'] * DIAS_OBJETIVO)
    df_full['A_Comprar'] = (df_full['Stock_Ideal'] - df_full['Stock']).apply(lambda x: x if x > 0 else 0)
    
    # Estimación de Costo de Compra
    df_full['Inversion_Requerida'] = df_full['A_Comprar'] * df_full['Costo']

    # Etiquetas de Estado
    def etiquetar_estado(row):
        if row['Stock'] <= 0 and row['Velocidad_Diaria'] > 0: return "🚨 AGOTADO (Urgente)"
        if row['Stock'] <= 0: return "⚪ Sin Stock (Sin Venta)"
        if row['Dias_Cobertura'] < 5: return "🔴 Crítico (< 5 días)"
        if row['Dias_Cobertura'] < 10: return "🟡 Bajo (< 10 días)"
        if row['Dias_Cobertura'] > 45: return "🔵 Sobre-Stock (> 45 días)"
        return "🟢 Saludable"

    df_full['Estado'] = df_full.apply(etiquetar_estado, axis=1)
    
    # 6. Pérdida de Oportunidad (Dinero que dejo de ganar hoy por no tener stock)
    df_full['Perdida_Diaria'] = df_full.apply(
        lambda x: (x['Velocidad_Diaria'] * x['Precio']) if "AGOTADO" in x['Estado'] else 0, axis=1
    )

    return df_full

# ==========================================
# 4. GENERADOR EXCEL (XLSWRITER)
# ==========================================

def generar_excel_auditoria(df, filtro_texto=""):
    """Genera Excel profesional para conteo físico."""
    output = BytesIO()
    
    # Filtrar
    if filtro_texto:
        df = df[df['Nombre'].str.contains(filtro_texto, case=False, na=False)]
        
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # 1. Hoja de Conteo
    cols = ['ID_Producto', 'Nombre', 'Categoria', 'Stock', 'Costo'] # Ajustar según columnas reales
    # Asegurar que columnas existan
    cols_existentes = [c for c in cols if c in df.columns]
    
    df_export = df[cols_existentes].copy()
    df_export = df_export.rename(columns={'Stock': 'Stock_Sistema'})
    df_export['Conteo_Fisico'] = "" 
    df_export['Diferencia'] = ""
    df_export['Notas'] = ""
    
    sheet_name = "Auditoria_Fisica"
    df_export.to_excel(writer, sheet_name=sheet_name, index=False)
    
    # Formatos
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    fmt_header = workbook.add_format({'bold': True, 'bg_color': '#1e3a8a', 'font_color': 'white', 'border': 1})
    fmt_write = workbook.add_format({'bg_color': '#fffbeb', 'border': 1}) # Crema para escribir
    
    for col_num, value in enumerate(df_export.columns.values):
        worksheet.write(0, col_num, value, fmt_header)
        
    worksheet.set_column('A:A', 15)
    worksheet.set_column('B:B', 40)
    worksheet.set_column(len(cols_existentes), len(cols_existentes), 15, fmt_write) # Columna Conteo
    
    writer.close()
    return output.getvalue()

# ==========================================
# 5. INTERFAZ PRINCIPAL
# ==========================================

def main():
    st.markdown("## 🏭 Centro de Comando de Inventarios")
    st.markdown("Análisis estratégico, proyección de compras y auditoría operativa.")
    
    ws_inv, ws_ven = conectar_db()
    
    if not ws_inv or not ws_ven:
        st.warning("⏳ Conectando con la base de datos...")
        return

    # 1. Cargar Data
    df_inv_raw = leer_data(ws_inv)
    df_ven_raw = leer_data(ws_ven)
    
    if df_inv_raw.empty:
        st.error("El inventario está vacío. Agrega productos en la app principal.")
        return

    # 2. Procesar Lógica
    df = motor_analisis_360(df_inv_raw, df_ven_raw)

    # --- SIDEBAR: FILTROS GLOBALES ---
    with st.sidebar:
        st.header("🔍 Filtros de Análisis")
        
        cats = df['Categoria'].unique().tolist() if 'Categoria' in df.columns else []
        sel_cats = st.multiselect("Categoría", cats, default=cats)
        
        # Filtro ABC
        abc_opts = df['Clasificacion_ABC'].unique().tolist()
        sel_abc = st.multiselect("Clasificación ABC", abc_opts, default=abc_opts)
        
        # Aplicar filtros
        if sel_cats: df = df[df['Categoria'].isin(sel_cats)]
        if sel_abc: df = df[df['Clasificacion_ABC'].isin(sel_abc)]

    # --- KPI HEADER ---
    col1, col2, col3, col4, col5 = st.columns(5)
    
    val_costo = df['Valor_Stock_Costo'].sum()
    val_venta = df['Valor_Stock_Venta'].sum()
    items_criticos = len(df[df['Estado'].str.contains("Crítico|AGOTADO")])
    perdida_dia = df['Perdida_Diaria'].sum()
    inversion_nec = df['Inversion_Requerida'].sum()
    
    col1.metric("Valor Inventario (Costo)", f"${val_costo:,.0f}", help="Dinero invertido actualmente")
    col2.metric("Valor Venta Potencial", f"${val_venta:,.0f}", help="Si vendes todo hoy")
    col3.metric("Stock en Riesgo", items_criticos, delta="-Atención", delta_color="inverse")
    col4.metric("Pérdida Diaria (Agotados)", f"${perdida_dia:,.0f}", delta="Oportunidad", delta_color="inverse", help="Dinero que dejas de ganar hoy por no tener stock")
    col5.metric("Inversión para 15 Días", f"${inversion_nec:,.0f}", help="Costo para reabastecer a niveles óptimos")

    st.markdown("---")

    # --- TABS ESTRATÉGICOS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard 360", 
        "🧠 Matriz ABC & Rentabilidad", 
        "🛒 Planificador de Compras", 
        "📋 Auditoría Física"
    ])

    # 1. DASHBOARD GENERAL
    with tab1:
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("Estado de Salud del Inventario")
            # Agrupar por Estado
            df_status = df['Estado'].value_counts().reset_index()
            df_status.columns = ['Estado', 'Cantidad']
            
            fig = px.bar(df_status, x='Cantidad', y='Estado', orientation='h', 
                         color='Estado', text='Cantidad',
                         color_discrete_map={
                             "🚨 AGOTADO (Urgente)": "#dc2626",
                             "🔴 Crítico (< 5 días)": "#ea580c",
                             "🟢 Saludable": "#16a34a",
                             "🔵 Sobre-Stock (> 45 días)": "#2563eb",
                             "🟡 Bajo (< 10 días)": "#facc15"
                         })
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("Top 5 Productos (Revenue)")
            top_rev = df.nlargest(5, 'Revenue_30d')
            fig_pie = px.donut(top_rev, values='Revenue_30d', names='Nombre', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

    # 2. MATRIZ ABC
    with tab2:
        st.info("💡 **Análisis ABC:** Clasifica tus productos según su importancia. Los 'A' son tu mina de oro (80% ventas), los 'C' son de baja rotación.")
        
        col_abc1, col_abc2 = st.columns(2)
        
        with col_abc1:
            fig_sun = px.sunburst(df, path=['Clasificacion_ABC', 'Categoria' if 'Categoria' in df.columns else 'Estado'], 
                                  values='Valor_Stock_Costo', title="Dinero Invertido por Clasificación")
            st.plotly_chart(fig_sun, use_container_width=True)
            
        with col_abc2:
            # Scatter Plot: Velocidad vs Stock
            fig_scat = px.scatter(df, x='Velocidad_Diaria', y='Stock', 
                                  color='Clasificacion_ABC', hover_data=['Nombre'],
                                  size='Precio', title="Matriz: Rotación vs Stock Actual")
            st.plotly_chart(fig_scat, use_container_width=True)
            
        st.markdown("### Detalles de Rentabilidad")
        st.dataframe(
            df[['Nombre', 'Clasificacion_ABC', 'Costo', 'Precio', 'Utilidad_Potencial', 'Dias_Cobertura']]
            .sort_values('Utilidad_Potencial', ascending=False),
            use_container_width=True
        )

    # 3. PLANIFICADOR DE COMPRAS (SOLUCIÓN DEL ERROR MULTISELECT)
    with tab3:
        st.subheader("🛒 Sugerencia de Reabastecimiento (IA)")
        st.caption("Basado en la rotación de los últimos 30 días para cubrir 15 días futuros.")
        
        # --- SOLUCIÓN AL ERROR DEL MULTISELECT ---
        # 1. Obtenemos las opciones disponibles en el dataframe
        opciones_disponibles = df['Estado'].unique().tolist()
        
        # 2. Definimos las que QUEREMOS que estén por defecto
        objetivos_defecto = ["🚨 AGOTADO (Urgente)", "🔴 Crítico (< 5 días)", "🟡 Bajo (< 10 días)"]
        
        # 3. Calculamos la intersección: Solo ponemos por defecto las que EXISTEN
        defaults_validos = [op for op in objetivos_defecto if op in opciones_disponibles]
        
        filtro_urgencia = st.multiselect(
            "Filtrar por Urgencia:",
            options=opciones_disponibles,
            default=defaults_validos # <--- ESTO EVITA EL ERROR
        )
        
        # Filtrar tabla
        df_compra = df[df['Estado'].isin(filtro_urgencia)].copy()
        
        if not df_compra.empty:
            # Formato bonito
            st.dataframe(
                df_compra[[
                    'Nombre', 'Stock', 'Velocidad_Diaria', 
                    'Stock_Ideal', 'A_Comprar', 'Inversion_Requerida', 'Estado'
                ]].sort_values('A_Comprar', ascending=False),
                column_config={
                    "Velocidad_Diaria": st.column_config.NumberColumn("Venta Diaria", format="%.2f u"),
                    "Inversion_Requerida": st.column_config.NumberColumn("Costo Total", format="$%d"),
                    "A_Comprar": st.column_config.NumberColumn("PEDIR 🛒", help="Cantidad sugerida a comprar ya"),
                },
                use_container_width=True
            )
            
            total_inv_tab = df_compra['Inversion_Requerida'].sum()
            st.success(f"💰 Total necesario para esta orden de compra: **${total_inv_tab:,.0f}**")
        else:
            st.success("🎉 ¡Todo está bajo control! No hay productos en los estados seleccionados.")

    # 4. AUDITORÍA FÍSICA
    with tab4:
        st.subheader("📋 Generador de Hojas de Conteo")
        st.markdown("Descarga este Excel, imprímelo o úsalo en una tablet para verificar el inventario en bodega.")
        
        c_filt, c_down = st.columns([3, 1])
        with c_filt:
            txt_search = st.text_input("Filtrar por palabra clave (opcional)", placeholder="Ej: Premium, Gato, 500g...")
        
        with c_down:
            st.write("")
            st.write("")
            excel_data = generar_excel_auditoria(df, txt_search)
            st.download_button(
                label="📥 Descargar Hoja de Conteo",
                data=excel_data,
                file_name=f"Conteo_Fisico_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
        st.dataframe(df[['ID_Producto', 'Nombre', 'Categoria', 'Stock']], use_container_width=True, height=300)

if __name__ == "__main__":
    main()
