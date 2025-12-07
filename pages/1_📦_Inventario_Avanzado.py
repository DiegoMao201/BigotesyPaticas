import streamlit as st
import pandas as pd
import gspread
from io import BytesIO
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS "ENTERPRISE"
# ==========================================

st.set_page_config(
    page_title="Master Suite de Inventario & Rentabilidad",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Profesional con Diseño de Tarjetas y Métricas
st.markdown("""
    <style>
    /* Estructura Global */
    .stApp { background-color: #f8fafc; }
    
    /* Tipografía */
    h1, h2, h3 { color: #0f172a; font-family: 'Segoe UI', sans-serif; font-weight: 700; }
    p, div { color: #334155; }

    /* Métricas KPI Cards */
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="metric-container"] label { color: #64748b; font-size: 0.9rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #0f172a; font-size: 1.8rem; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 10px; 
        background-color: transparent;
        padding-bottom: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        border: 1px solid #e2e8f0;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: white !important;
        border-color: #2563eb;
    }

    /* Tablas */
    .stDataFrame { border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Alertas Personalizadas */
    .badge-danger { background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
    .badge-success { background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
    .badge-warning { background-color: #fef9c3; color: #854d0e; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y UTILIDADES ROBUSTAS
# ==========================================

@st.cache_resource(ttl=600)
def conectar_db():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos 'google_service_account' y 'SHEET_URL'.")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Intentamos obtener las hojas con manejo de error silencioso
        try: ws_inv = sh.worksheet("Inventario")
        except: ws_inv = None
        
        try: ws_ven = sh.worksheet("Ventas")
        except: ws_ven = None
            
        return ws_inv, ws_ven
    except Exception as e:
        st.error(f"Error crítico de conexión a Google Sheets: {e}")
        return None, None

def clean_currency(val):
    """Limpia strings de moneda a float de forma ultra-segura."""
    if isinstance(val, (int, float, np.number)): return float(val)
    if isinstance(val, str):
        # Eliminar símbolos comunes y espacios
        val = val.replace('$', '').replace('€', '').replace(' ', '').strip()
        if not val: return 0.0
        try:
            # Manejo básico de miles (,) y decimales (.)
            val = val.replace(',', '') 
            return float(val)
        except: return 0.0
    return 0.0

@st.cache_data(ttl=300)
def leer_data(_ws):
    """Lee datos con cache para velocidad."""
    if _ws is None: return pd.DataFrame()
    try:
        data = _ws.get_all_records()
        if not data: return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Limpieza de Nombres de Columnas (eliminar espacios extra)
        df.columns = df.columns.str.strip()
        
        # Limpieza automática de numéricos
        cols_num = ['Precio', 'Stock', 'Costo', 'Total', 'Cantidad']
        for c in cols_num:
            if c in df.columns:
                df[c] = df[c].apply(clean_currency)
                
        # Estandarizar Fechas
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
            
        return df
    except Exception as e:
        st.error(f"Error leyendo datos de la hoja: {e}")
        return pd.DataFrame()

# ==========================================
# 3. MOTOR ANALÍTICO "CEREBRO" (Optimizado)
# ==========================================

def motor_analisis_avanzado(df_inv, df_ven):
    """
    Realiza un análisis 360: Rotación, Márgenes, Pareto, Predicción.
    """
    if df_inv.empty: return pd.DataFrame()

    # --- A. ANÁLISIS DE VENTAS (Minado de Datos) ---
    ventas_por_producto = {}
    revenue_por_producto = {}
    
    if not df_ven.empty:
        # Filtramos últimos 30 días para calcular velocidad actual (Run Rate)
        fecha_limite = datetime.now() - timedelta(days=30)
        df_ven_30 = df_ven[df_ven['Fecha'] >= fecha_limite]
        
        for _, row in df_ven_30.iterrows():
            items_str = str(row.get('Items', ''))
            # Parsear string complejo tipo "Prod A (x2), Prod B (x1)"
            if items_str:
                parts = items_str.split(", ")
                for p in parts:
                    try:
                        if "(x" in p:
                            nombre_dirty = p.split(" (x")[0]
                            cant_str = p.split(" (x")[1].replace(")", "")
                            cant = int(cant_str)
                        else:
                            nombre_dirty = p
                            cant = 1
                        
                        nombre = nombre_dirty.strip()
                        ventas_por_producto[nombre] = ventas_por_producto.get(nombre, 0) + cant
                    except: continue

    # Crear DF de Rotación
    df_rot = pd.DataFrame(list(ventas_por_producto.items()), columns=['Nombre', 'Ventas_30d'])
    df_rot['Velocidad_Diaria'] = df_rot['Ventas_30d'] / 30

    # --- B. MERGE CON INVENTARIO MAESTRO ---
    # Merge Left para mantener todo el inventario aunque no tenga ventas
    df_full = pd.merge(df_inv, df_rot, on='Nombre', how='left')
    
    # Relleno de NaNs
    df_full['Ventas_30d'] = df_full['Ventas_30d'].fillna(0)
    df_full['Velocidad_Diaria'] = df_full['Velocidad_Diaria'].fillna(0)
    
    # --- C. INTELIGENCIA FINANCIERA ---
    
    # 1. Validación de Costos y Precios
    if 'Costo' not in df_full.columns:
        df_full['Costo'] = df_full['Precio'] * 0.65 # Fallback: asumimos 35% margen si no hay costo
    
    # Asegurar que no haya divisiones por cero o costos 0 irreales
    df_full['Costo'] = df_full['Costo'].replace(0, 0.01) 
    
    # 2. Métricas de Rentabilidad
    df_full['Margen_Unitario'] = df_full['Precio'] - df_full['Costo']
    df_full['Margen_Porcentaje'] = (df_full['Margen_Unitario'] / df_full['Precio']).fillna(0) * 100
    
    # 3. Valoración del Inventario
    df_full['Valor_Stock_Costo'] = df_full['Stock'] * df_full['Costo']
    df_full['Valor_Stock_Venta'] = df_full['Stock'] * df_full['Precio']
    df_full['Utilidad_Potencial_Stock'] = df_full['Valor_Stock_Venta'] - df_full['Valor_Stock_Costo']
    
    # 4. Análisis de Cobertura (Days of Inventory - DOI)
    def calc_cobertura(row):
        if row['Velocidad_Diaria'] <= 0.01: return 999 # Stock estancado
        return row['Stock'] / row['Velocidad_Diaria']
        
    df_full['Dias_Cobertura'] = df_full.apply(calc_cobertura, axis=1)
    
    # 5. Clasificación ABC (Pareto Real sobre Revenue 30d)
    df_full['Revenue_30d'] = df_full['Ventas_30d'] * df_full['Precio']
    df_full = df_full.sort_values('Revenue_30d', ascending=False)
    
    total_rev = df_full['Revenue_30d'].sum()
    if total_rev > 0:
        df_full['Acumulado_Pct'] = df_full['Revenue_30d'].cumsum() / total_rev
        def clasificar_abc(pct):
            if pct <= 0.80: return 'A (Estrellas)'
            elif pct <= 0.95: return 'B (Regulares)'
            else: return 'C (Lento Mov.)'
        df_full['Clasificacion_ABC'] = df_full['Acumulado_Pct'].apply(clasificar_abc)
    else:
        df_full['Clasificacion_ABC'] = 'C (Sin Ventas)'
        df_full['Acumulado_Pct'] = 1.0

    # 6. Estrategia de Abastecimiento (Target Dinámico)
    DIAS_OBJETIVO = 21 # Queremos stock para 3 semanas
    df_full['Stock_Ideal'] = np.ceil(df_full['Velocidad_Diaria'] * DIAS_OBJETIVO)
    df_full['A_Comprar'] = (df_full['Stock_Ideal'] - df_full['Stock']).apply(lambda x: x if x > 0 else 0)
    df_full['Inversion_Requerida'] = df_full['A_Comprar'] * df_full['Costo']

    # 7. Diagnóstico de Salud (Estados)
    def etiquetar_estado(row):
        # Prioridad 1: Agotados con demanda
        if row['Stock'] <= 0 and row['Velocidad_Diaria'] > 0: return "🚨 AGOTADO (Perdiendo Ventas)"
        # Prioridad 2: Sin stock y sin venta (Hueso vacío)
        if row['Stock'] <= 0: return "⚪ Agotado (Sin Demanda)"
        # Prioridad 3: Stock Crítico
        if row['Dias_Cobertura'] < 7: return "🔥 Crítico (< 1 semana)"
        # Prioridad 4: Stock Bajo
        if row['Dias_Cobertura'] < 15: return "⚠️ Bajo (< 2 semanas)"
        # Prioridad 5: Exceso / Dormido
        if row['Dias_Cobertura'] > 90: return "🧊 Sobre-Stock (> 3 meses)"
        if row['Ventas_30d'] == 0 and row['Stock'] > 0: return "💀 Stock Muerto (0 ventas)"
        
        return "✅ Saludable"

    df_full['Estado'] = df_full.apply(etiquetar_estado, axis=1)
    
    # 8. Cálculo de Costo de Oportunidad (Dinero perdido HOY por no tener stock)
    # Si está agotado y su velocidad diaria es X, pierdo X * Precio al día.
    df_full['Perdida_Diaria_Venta'] = df_full.apply(
        lambda x: (x['Velocidad_Diaria'] * x['Precio']) if "AGOTADO" in x['Estado'] else 0, axis=1
    )

    return df_full

# ==========================================
# 4. GENERADOR EXCEL AUDITORÍA
# ==========================================

def generar_excel_auditoria(df, filtro_texto=""):
    """Genera un archivo Excel profesional listo para imprimir."""
    output = BytesIO()
    
    # Filtrar
    if filtro_texto:
        df = df[df['Nombre'].str.contains(filtro_texto, case=False, na=False)]
        
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Seleccionar columnas lógicas
    cols_base = ['ID_Producto', 'Nombre', 'Categoria', 'Stock', 'Costo'] 
    cols_existentes = [c for c in cols_base if c in df.columns]
    
    df_export = df[cols_existentes].copy()
    df_export = df_export.rename(columns={'Stock': 'Stock_Sistema'})
    
    # Columnas para escribir a mano
    df_export['Conteo_Real'] = "" 
    df_export['Diferencia'] = ""
    df_export['Condición_Fisica'] = ""
    df_export['Notas'] = ""
    
    sheet_name = "Hoja_Conteo"
    df_export.to_excel(writer, sheet_name=sheet_name, index=False)
    
    # Formateo con XlsxWriter
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # Estilos
    header_fmt = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#1e3a8a', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
    cell_fmt = workbook.add_format({'border': 1})
    input_fmt = workbook.add_format({'bg_color': '#fef3c7', 'border': 1}) # Color amarillo suave para input manual
    
    # Aplicar formatos
    for col_num, value in enumerate(df_export.columns.values):
        worksheet.write(0, col_num, value, header_fmt)
        
    worksheet.set_column('A:A', 15) # ID
    worksheet.set_column('B:B', 45) # Nombre
    worksheet.set_column('C:E', 12) # Datos
    
    # Resaltar columnas de escritura
    start_input_col = len(cols_existentes)
    worksheet.set_column(start_input_col, start_input_col + 3, 18, input_fmt)
    
    writer.close()
    return output.getvalue()

# ==========================================
# 5. INTERFAZ PRINCIPAL (DASHBOARD)
# ==========================================

def main():
    # --- HEADER ---
    st.title("💎 Master Inventory Suite")
    st.markdown("Plataforma de inteligencia de inventarios, optimización de compras y auditoría.")

    # --- CARGA DE DATOS ---
    with st.spinner("🔄 Sincronizando con ERP y Analizando Datos..."):
        ws_inv, ws_ven = conectar_db()
        if not ws_inv: return

        df_inv_raw = leer_data(ws_inv)
        df_ven_raw = leer_data(ws_ven)
        
        if df_inv_raw.empty:
            st.warning("⚠️ No hay inventario registrado. Por favor carga productos en la base de datos.")
            return

        # EJECUTAR MOTOR ANALÍTICO
        df = motor_analisis_avanzado(df_inv_raw, df_ven_raw)

    # --- SIDEBAR: FILTROS ESTRATÉGICOS ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2897/2897785.png", width=60)
        st.markdown("### 🔍 Filtros de Inteligencia")
        
        # Filtro Categoría
        cats = sorted(df['Categoria'].unique().tolist()) if 'Categoria' in df.columns else []
        sel_cats = st.multiselect("Categoría", cats, default=cats, placeholder="Todas las categorías")
        
        # Filtro ABC
        abc_opts = sorted(df['Clasificacion_ABC'].unique().tolist())
        sel_abc = st.multiselect("Clasificación Pareto (ABC)", abc_opts, default=abc_opts)
        
        # Filtro Proveedor (Si existe)
        if 'Proveedor' in df.columns:
            provs = sorted(df['Proveedor'].unique().tolist())
            sel_prov = st.multiselect("Proveedor", provs, default=provs)
            if sel_prov: df = df[df['Proveedor'].isin(sel_prov)]

        # Aplicar Filtros Base
        if sel_cats: df = df[df['Categoria'].isin(sel_cats)]
        if sel_abc: df = df[df['Clasificacion_ABC'].isin(sel_abc)]
        
        st.divider()
        st.info(f"Mostrando **{len(df)}** productos filtrados.")

    # --- KPI CARDS (Primera Fila) ---
    st.markdown("### 🚀 Resumen Ejecutivo")
    
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    val_costo_total = df['Valor_Stock_Costo'].sum()
    val_venta_total = df['Valor_Stock_Venta'].sum()
    margen_global = ((val_venta_total - val_costo_total) / val_venta_total * 100) if val_venta_total > 0 else 0
    
    items_agotados_criticos = len(df[df['Estado'].str.contains("AGOTADO")])
    perdida_oportunidad = df['Perdida_Diaria_Venta'].sum()
    
    stock_muerto_val = df[df['Estado'].str.contains("Muerto|Sobre-Stock")]['Valor_Stock_Costo'].sum()

    kpi1.metric("Valor Inventario (Costo)", f"${val_costo_total:,.0f}", delta="Capital Invertido", delta_color="off")
    kpi2.metric("Margen Potencial Global", f"{margen_global:.1f}%", f"${(val_venta_total - val_costo_total):,.0f} Utilidad")
    kpi3.metric("Productos Agotados", items_agotados_criticos, delta="-Urgentísimo", delta_color="inverse")
    kpi4.metric("Pérdida Diaria (Stockout)", f"${perdida_oportunidad:,.0f}", delta="Dinero perdido hoy", delta_color="inverse")
    kpi5.metric("Capital 'Dormido' (Stock Muerto)", f"${stock_muerto_val:,.0f}", delta="Optimizar", delta_color="inverse")

    st.markdown("---")

    # --- NAVEGACIÓN PRINCIPAL ---
    tab_dash, tab_strat, tab_buy, tab_dead, tab_audit = st.tabs([
        "📊 Dashboard 360", 
        "🧠 Matriz Estratégica", 
        "🛒 Asistente de Compras", 
        "💀 Stock Muerto", 
        "📋 Auditoría Física"
    ])

    # -----------------------------------------------
    # TAB 1: DASHBOARD VISUAL
    # -----------------------------------------------
    with tab_dash:
        col_g1, col_g2 = st.columns([2, 1])
        
        with col_g1:
            st.subheader("Estado de Salud del Inventario")
            # Agrupar datos para gráfico
            df_status = df.groupby('Estado').size().reset_index(name='Cantidad')
            
            # Colores semánticos
            colors_map = {
                "✅ Saludable": "#22c55e",
                "🚨 AGOTADO (Perdiendo Ventas)": "#ef4444",
                "🔥 Crítico (< 1 semana)": "#f97316",
                "⚠️ Bajo (< 2 semanas)": "#eab308",
                "🧊 Sobre-Stock (> 3 meses)": "#3b82f6",
                "💀 Stock Muerto (0 ventas)": "#64748b",
                "⚪ Agotado (Sin Demanda)": "#cbd5e1"
            }
            
            fig_bar = px.bar(df_status, x='Cantidad', y='Estado', orientation='h', 
                             color='Estado', text='Cantidad',
                             color_discrete_map=colors_map,
                             title="Distribución de SKUs por Salud de Stock")
            fig_bar.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_g2:
            st.subheader("Top Revenue (30 días)")
            top_5 = df.nlargest(5, 'Revenue_30d')
            # SOLUCIÓN DEL ERROR PX.DONUT -> PX.PIE CON HOLE
            if not top_5.empty and top_5['Revenue_30d'].sum() > 0:
                fig_don = px.pie(top_5, values='Revenue_30d', names='Nombre', hole=0.5,
                                 title="Top 5 Productos Estrella")
                fig_don.update_traces(textposition='inside', textinfo='percent+label')
                fig_don.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig_don, use_container_width=True)
            else:
                st.info("No hay suficientes datos de ventas recientes para mostrar el Top 5.")

        # Segunda Fila: Categorías
        st.subheader("Rentabilidad por Categoría")
        if 'Categoria' in df.columns:
            df_cat = df.groupby('Categoria')[['Valor_Stock_Costo', 'Revenue_30d']].sum().reset_index()
            # Gráfico combinado
            fig_mix = go.Figure()
            fig_mix.add_trace(go.Bar(x=df_cat['Categoria'], y=df_cat['Valor_Stock_Costo'], name='Dinero Invertido', marker_color='#94a3b8'))
            fig_mix.add_trace(go.Scatter(x=df_cat['Categoria'], y=df_cat['Revenue_30d'], name='Ventas (30d)', yaxis='y2', line=dict(color='#2563eb', width=3)))
            
            fig_mix.update_layout(
                yaxis=dict(title="Inversión ($)"),
                yaxis2=dict(title="Ventas ($)", overlaying='y', side='right'),
                title="Correlación: Inversión vs Retorno por Categoría",
                hovermode="x unified"
            )
            st.plotly_chart(fig_mix, use_container_width=True)

    # -----------------------------------------------
    # TAB 2: MATRIZ ESTRATÉGICA (ABC & MÁRGENES)
    # -----------------------------------------------
    with tab_strat:
        c_str1, c_str2 = st.columns([1, 2])
        
        with c_str1:
            st.markdown("### 🧠 Análisis Pareto (ABC)")
            st.info("""
            **Regla 80/20:**
            * **Clase A:** Generan el 80% de tus ingresos. ¡Nunca deben agotarse!
            * **Clase B:** Importancia media.
            * **Clase C:** Generan poco ingreso. Candidatos a reducción.
            """)
            
            # Sunburst
            fig_sun = px.sunburst(df, path=['Clasificacion_ABC', 'Categoria'], values='Revenue_30d',
                                  color='Clasificacion_ABC', 
                                  color_discrete_map={'A (Estrellas)':'#22c55e', 'B (Regulares)':'#facc15', 'C (Lento Mov.)':'#94a3b8'},
                                  title="Estructura de Ingresos")
            st.plotly_chart(fig_sun, use_container_width=True)

        with c_str2:
            st.markdown("### 💎 Matriz de Rentabilidad: Margen vs Volumen")
            st.caption("Identifica tus 'Vacas Lecheras' (Alto Volumen, Bajo Margen) y 'Estrellas' (Alto Volumen, Alto Margen).")
            
            # Scatter Plot Avanzado
            # Filtramos outliers extremos para que el gráfico se vea bien
            df_scat = df[df['Revenue_30d'] > 0]
            
            fig_scat = px.scatter(df_scat, x='Revenue_30d', y='Margen_Porcentaje',
                                  size='Valor_Stock_Costo', color='Clasificacion_ABC',
                                  hover_name='Nombre', text='Nombre',
                                  labels={'Revenue_30d': 'Ventas Totales ($)', 'Margen_Porcentaje': 'Margen (%)'},
                                  title="Mapa de Posicionamiento de Producto")
            
            # Líneas cuadrantes
            avg_margen = df_scat['Margen_Porcentaje'].mean()
            avg_rev = df_scat['Revenue_30d'].mean()
            
            fig_scat.add_hline(y=avg_margen, line_dash="dash", line_color="gray", annotation_text="Margen Promedio")
            fig_scat.add_vline(x=avg_rev, line_dash="dash", line_color="gray", annotation_text="Venta Promedio")
            fig_scat.update_traces(textposition='top center')
            
            st.plotly_chart(fig_scat, use_container_width=True)

    # -----------------------------------------------
    # TAB 3: ASISTENTE DE COMPRAS (SOLUCIÓN COMPLETA)
    # -----------------------------------------------
    with tab_buy:
        st.header("🛒 Generador de Órdenes de Compra")
        st.markdown("El sistema calcula automáticamente cuánto pedir basándose en la velocidad de venta de los últimos 30 días.")
        
        col_ctrl, col_data = st.columns([1, 3])
        
        with col_ctrl:
            dias_obj = st.slider("Días de Stock Objetivo", min_value=7, max_value=60, value=21, step=1, help="¿Para cuántos días quieres tener inventario?")
            
            # Recalcular Stock Ideal Dinámicamente basado en el Slider
            df['Stock_Ideal_Din'] = np.ceil(df['Velocidad_Diaria'] * dias_obj)
            df['A_Comprar_Din'] = (df['Stock_Ideal_Din'] - df['Stock']).apply(lambda x: x if x > 0 else 0)
            df['Inversion_Din'] = df['A_Comprar_Din'] * df['Costo']
            
            # --- SOLUCIÓN AL ERROR DEL MULTISELECT ---
            # 1. Obtener opciones existentes en los datos
            opciones_existentes = sorted(df['Estado'].unique().tolist())
            
            # 2. Definir deseados
            deseados = ["🚨 AGOTADO (Perdiendo Ventas)", "🔥 Crítico (< 1 semana)", "⚠️ Bajo (< 2 semanas)"]
            
            # 3. Intersección segura
            default_validos = [x for x in deseados if x in opciones_existentes]
            
            filtro_urgencia = st.multiselect(
                "Filtrar por Urgencia:",
                options=opciones_existentes,
                default=default_validos
            )
        
        with col_data:
            # Filtrar Dataframe
            df_pedidos = df[df['Estado'].isin(filtro_urgencia) & (df['A_Comprar_Din'] > 0)].copy()
            
            if not df_pedidos.empty:
                total_inversion = df_pedidos['Inversion_Din'].sum()
                st.success(f"💰 Inversión total sugerida: **${total_inversion:,.2f}** para cubrir **{dias_obj} días**.")
                
                st.dataframe(
                    df_pedidos[['Nombre', 'Stock', 'Velocidad_Diaria', 'Stock_Ideal_Din', 'A_Comprar_Din', 'Costo', 'Inversion_Din', 'Proveedor'] if 'Proveedor' in df.columns else ['Nombre', 'Stock', 'Velocidad_Diaria', 'Stock_Ideal_Din', 'A_Comprar_Din', 'Costo', 'Inversion_Din']],
                    column_config={
                        "Velocidad_Diaria": st.column_config.NumberColumn("Venta Diaria", format="%.2f u"),
                        "Stock_Ideal_Din": st.column_config.NumberColumn("Nivel Óptimo"),
                        "A_Comprar_Din": st.column_config.NumberColumn("CANTIDAD A PEDIR", help="Sugerencia IA"),
                        "Inversion_Din": st.column_config.NumberColumn("Costo Total", format="$%.2f"),
                        "Costo": st.column_config.NumberColumn("Costo Unit", format="$%.2f"),
                    },
                    use_container_width=True,
                    height=500
                )
            else:
                st.balloons()
                st.success("🎉 ¡Excelente gestión! No se requieren compras para los estados seleccionados.")

    # -----------------------------------------------
    # TAB 4: STOCK MUERTO
    # -----------------------------------------------
    with tab_dead:
        st.header("💀 Análisis de Inventario Inmovilizado")
        st.warning("Estos productos ocupan espacio y capital, pero no generan flujo de caja. ¡Considera ofertas o liquidaciones!")
        
        # Filtro: Productos con Stock > 0 pero Ventas_30d = 0
        df_dead = df[(df['Stock'] > 0) & (df['Ventas_30d'] == 0)].copy()
        df_dead = df_dead.sort_values('Valor_Stock_Costo', ascending=False)
        
        c_d1, c_d2 = st.columns([1, 1])
        with c_d1:
            st.metric("Total Productos sin Movimiento (30d)", len(df_dead))
        with c_d2:
            st.metric("Capital Congelado", f"${df_dead['Valor_Stock_Costo'].sum():,.2f}")
            
        st.dataframe(
            df_dead[['Nombre', 'Categoria', 'Stock', 'Costo', 'Valor_Stock_Costo', 'Fecha_Ingreso'] if 'Fecha_Ingreso' in df.columns else ['Nombre', 'Categoria', 'Stock', 'Costo', 'Valor_Stock_Costo']],
            column_config={
                "Valor_Stock_Costo": st.column_config.ProgressColumn("Capital Atrapado", format="$%d", min_value=0, max_value=df_dead['Valor_Stock_Costo'].max())
            },
            use_container_width=True
        )

    # -----------------------------------------------
    # TAB 5: AUDITORÍA
    # -----------------------------------------------
    with tab_audit:
        st.header("📋 Centro de Auditoría Física")
        
        c_audit1, c_audit2 = st.columns([3, 1])
        with c_audit1:
            search_audit = st.text_input("🔍 Buscar producto para hoja de conteo:", placeholder="Ej: Shampoo...")
        with c_audit2:
            st.write("")
            st.write("")
            excel_bytes = generar_excel_auditoria(df, search_audit)
            st.download_button(
                label="📥 Descargar Hoja de Conteo (Excel)",
                data=excel_bytes,
                file_name=f"Auditoria_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
        st.markdown("### Vista Previa de Datos")
        st.dataframe(df[['Nombre', 'Stock', 'Categoria']].head(20), use_container_width=True)

if __name__ == "__main__":
    main()
