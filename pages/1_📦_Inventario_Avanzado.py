import streamlit as st
import pandas as pd
import gspread
from io import BytesIO
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS "ULTIMATE"
# ==========================================

st.set_page_config(
    page_title="Nexus: Master Inventory Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS inyectados para UI/UX de alto nivel
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f1f5f9; }
    
    /* Headers */
    h1, h2, h3 { color: #1e293b; font-weight: 700; letter-spacing: -0.5px; }
    
    /* KPI Cards Avanzadas */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-left: 4px solid #3b82f6;
    }
    
    /* Tablas */
    .stDataFrame { 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); 
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 0.9rem;
        border: 1px solid #cbd5e1;
        color: #64748b;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0f172a !important;
        color: white !important;
        border-color: #0f172a;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: white; border-right: 1px solid #e2e8f0; }
    
    /* Custom Alerts */
    .nexus-alert { padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid transparent; }
    .nexus-alert-danger { background-color: #fee2e2; color: #991b1b; border-color: #fca5a5; }
    .nexus-alert-success { background-color: #dcfce7; color: #166534; border-color: #86efac; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SISTEMA DE CONEXIÓN Y BLINDAJE DE DATOS
# ==========================================

@st.cache_resource(ttl=600)
def conectar_db():
    """Conexión robusta con manejo de secretos."""
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 CRÍTICO: No se encontraron los secretos de Google Sheets.")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Intentar conectar a hojas específicas
        try: ws_inv = sh.worksheet("Inventario")
        except: ws_inv = None
        
        try: ws_ven = sh.worksheet("Ventas")
        except: ws_ven = None
            
        return ws_inv, ws_ven
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None, None

def normalizar_columnas(df, tipo="inventario"):
    """
    Inteligencia Artificial Simbólica para corregir nombres de columnas mal escritos
    y garantizar estructura mínima para evitar crashes.
    """
    if df.empty: return df
    
    # 1. Limpieza inicial
    df.columns = df.columns.str.strip().str.lower()
    
    # 2. Mapa de sinónimos (Thesaurus)
    mapa = {
        'fecha': 'Fecha', 'date': 'Fecha', 'dia': 'Fecha', 'time': 'Fecha',
        'items': 'Items', 'producto': 'Items', 'products': 'Items', 'sku': 'Items',
        'precio': 'Precio', 'price': 'Precio', 'pvp': 'Precio', 'venta': 'Precio',
        'costo': 'Costo', 'cost': 'Costo', 'compra': 'Costo',
        'stock': 'Stock', 'cantidad': 'Stock', 'qty': 'Stock', 'existencia': 'Stock',
        'nombre': 'Nombre', 'name': 'Nombre', 'item': 'Nombre', 'descripcion': 'Nombre',
        'categoria': 'Categoria', 'cat': 'Categoria', 'familia': 'Categoria',
        'proveedor': 'Proveedor', 'supplier': 'Proveedor'
    }
    
    new_cols = {}
    for col in df.columns:
        match_found = False
        # Búsqueda exacta
        if col in mapa:
            new_cols[col] = mapa[col]
            match_found = True
        else:
            # Búsqueda difusa (contiene la palabra)
            for key, val in mapa.items():
                if key in col:
                    new_cols[col] = val
                    match_found = True
                    break
        
        # Si no se encuentra, mantener capitalizado
        if not match_found:
            new_cols[col] = col.title()
            
    df = df.rename(columns=new_cols)
    
    # 3. GARANTÍA DE ESTRUCTURA (Anti-Crash)
    # Si falta una columna crítica, la creamos con valores por defecto.
    columnas_criticas = []
    if tipo == "inventario":
        columnas_criticas = [('Nombre', 'Producto Desconocido'), ('Stock', 0), ('Precio', 0.0), ('Costo', 0.0)]
    elif tipo == "ventas":
        columnas_criticas = [('Fecha', datetime.now()), ('Items', '')]
        
    for col, default_val in columnas_criticas:
        if col not in df.columns:
            df[col] = default_val
            # Solo avisar si es debug, para no molestar al usuario final
            # st.toast(f"⚠️ Columna '{col}' regenerada automáticamente.", icon="🔧")

    return df

def clean_currency(val):
    """Sanitizador de números agresivo."""
    if isinstance(val, (int, float, np.number)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace('€', '').replace(' ', '').strip()
        if not val: return 0.0
        try:
            val = val.replace(',', '') 
            return float(val)
        except: return 0.0
    return 0.0

@st.cache_data(ttl=300)
def leer_data(_ws, tipo):
    """ETL Pipeline: Extracción y Transformación segura."""
    if _ws is None: return pd.DataFrame()
    try:
        data = _ws.get_all_records()
        if not data: return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # PASO 1: Normalización Inteligente
        df = normalizar_columnas(df, tipo)
        
        # PASO 2: Tipado de Datos
        cols_num = ['Precio', 'Stock', 'Costo', 'Total', 'Cantidad']
        for c in cols_num:
            if c in df.columns:
                df[c] = df[c].apply(clean_currency)
                
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
            # Eliminar fechas nulas si es tabla de ventas
            if tipo == "ventas":
                df = df.dropna(subset=['Fecha'])
            
        return df
    except Exception as e:
        st.error(f"Error en ETL ({tipo}): {e}")
        return pd.DataFrame()

# ==========================================
# 3. MOTOR DE INTELIGENCIA DE NEGOCIOS (BI)
# ==========================================

def motor_analisis_master(df_inv, df_ven, growth_scenario=0.0):
    """
    Cerebro analítico que incluye:
    - Análisis de Series de Tiempo
    - Stock de Seguridad (Z-Score)
    - GMROI
    - Simulador de Crecimiento
    """
    if df_inv.empty: return pd.DataFrame(), pd.DataFrame()

    # --- A. PROCESAMIENTO DE VENTAS ---
    ventas_por_producto = {}
    ventas_historicas = [] # Lista para serie de tiempo global
    
    if not df_ven.empty:
        # 1. Filtro de fecha (Últimos 90 días para mejor tendencia, no solo 30)
        cutoff_date = datetime.now() - timedelta(days=90)
        df_ven_recent = df_ven[df_ven['Fecha'] >= cutoff_date].copy()
        
        # 2. Desglose de Items
        for idx, row in df_ven_recent.iterrows():
            items_str = str(row.get('Items', ''))
            fecha_venta = row['Fecha']
            
            if items_str:
                parts = items_str.split(", ")
                for p in parts:
                    try:
                        cant = 1
                        nombre = p.strip()
                        if "(x" in p:
                            nombre_parts = p.split(" (x")
                            nombre = nombre_parts[0].strip()
                            cant = int(nombre_parts[1].replace(")", ""))
                        
                        # Acumuladores
                        ventas_por_producto[nombre] = ventas_por_producto.get(nombre, 0) + cant
                        
                        # Guardar para serie de tiempo
                        ventas_historicas.append({
                            'Fecha': fecha_venta,
                            'Nombre': nombre,
                            'Cantidad': cant
                        })
                    except: continue

    # Dataframe de Historial Detallado (para gráficos de línea)
    df_history = pd.DataFrame(ventas_historicas)
    
    # --- B. CÁLCULO DE VELOCIDAD Y VARIABILIDAD ---
    # Convertimos el diccionario a DF
    df_metrics = pd.DataFrame(list(ventas_por_producto.items()), columns=['Nombre', 'Ventas_90d'])
    
    # Cálculo de métricas avanzadas
    # Velocidad Diaria (Run Rate) - Promedio simple
    df_metrics['Velocidad_Diaria'] = df_metrics['Ventas_90d'] / 90
    
    # APLICAR SIMULADOR DE CRECIMIENTO
    if growth_scenario != 0:
        df_metrics['Velocidad_Diaria'] = df_metrics['Velocidad_Diaria'] * (1 + (growth_scenario/100))

    # --- C. FUSIÓN MAESTRA (MERGE) ---
    df_full = pd.merge(df_inv, df_metrics, on='Nombre', how='left')
    
    # Limpieza post-merge
    df_full['Ventas_90d'] = df_full['Ventas_90d'].fillna(0)
    df_full['Velocidad_Diaria'] = df_full['Velocidad_Diaria'].fillna(0)
    
    # --- D. MATEMÁTICA FINANCIERA ---
    # Fallback inteligente para costo
    if 'Costo' not in df_full.columns: df_full['Costo'] = 0.0
    if 'Precio' not in df_full.columns: df_full['Precio'] = 0.0
    
    # Rellenar costos cero con heurística (60% del precio)
    mask_no_cost = (df_full['Costo'] <= 0) & (df_full['Precio'] > 0)
    df_full.loc[mask_no_cost, 'Costo'] = df_full.loc[mask_no_cost, 'Precio'] * 0.6
    
    # Métricas Base
    df_full['Margen_Unitario'] = df_full['Precio'] - df_full['Costo']
    df_full['Margen_Pct'] = (df_full['Margen_Unitario'] / df_full['Precio'].replace(0, 1)).fillna(0) * 100
    df_full['Valor_Inv_Costo'] = df_full['Stock'] * df_full['Costo']
    
    # --- E. GMROI (Gross Margin Return on Inventory) ---
    # GMROI = (Margen Bruto Anualizado) / (Costo Inventario Promedio)
    # Es la métrica reina del retail. Cuánto gano por cada $1 invertido en stock.
    df_full['GMROI'] = np.where(
        df_full['Valor_Inv_Costo'] > 0,
        (df_full['Margen_Unitario'] * df_full['Velocidad_Diaria'] * 365) / df_full['Valor_Inv_Costo'],
        0
    )

    # --- F. STOCK DE SEGURIDAD Y REORDEN (Nivel Enterprise) ---
    # Asumimos Lead Time (Tiempo de proveedor) de 7 días por defecto, con desviación.
    LEAD_TIME_DIAS = 7 
    Z_SCORE_95 = 1.65 # Para 95% de nivel de servicio
    
    # Stock de Seguridad = Z * raiz(LeadTime) * DesviacionVenta (Simplificada aquí como 20% de la media para no complejizar sin datos diarios exactos por SKU)
    df_full['Safety_Stock'] = np.ceil(Z_SCORE_95 * np.sqrt(LEAD_TIME_DIAS) * (df_full['Velocidad_Diaria'] * 0.5))
    
    # Punto de Reorden = (Velocidad * LeadTime) + Safety Stock
    df_full['Punto_Reorden'] = (df_full['Velocidad_Diaria'] * LEAD_TIME_DIAS) + df_full['Safety_Stock']
    
    # Sugerencia de Compra (Target 30 días)
    TARGET_DIAS = 30
    df_full['Stock_Maximo'] = (df_full['Velocidad_Diaria'] * TARGET_DIAS) + df_full['Safety_Stock']
    
    df_full['A_Comprar'] = (df_full['Stock_Maximo'] - df_full['Stock']).clip(lower=0)
    df_full['Inversion_Compra'] = df_full['A_Comprar'] * df_full['Costo']

    # --- G. ESTADOS Y ALARMAS ---
    df_full['Dias_Cobertura'] = np.where(df_full['Velocidad_Diaria'] > 0, df_full['Stock'] / df_full['Velocidad_Diaria'], 999)
    
    def clasificar_estado(row):
        if row['Stock'] <= 0 and row['Velocidad_Diaria'] > 0: return "🚨 AGOTADO (Perdida Venta)"
        if row['Stock'] <= row['Safety_Stock']: return "🔥 Crítico (Bajo Seguridad)"
        if row['Stock'] <= row['Punto_Reorden']: return "⚠️ Reorden (Pedir ya)"
        if row['Dias_Cobertura'] > 120: return "🧊 Obsoleto (> 4 meses)"
        if row['Velocidad_Diaria'] == 0 and row['Stock'] > 0: return "💀 Stock Muerto"
        return "✅ Saludable"
        
    df_full['Estado'] = df_full.apply(clasificar_estado, axis=1)
    
    # --- H. CLASIFICACIÓN ABC (PARETO) ---
    df_full['Revenue_Proyectado'] = df_full['Velocidad_Diaria'] * 30 * df_full['Precio']
    df_full = df_full.sort_values('Revenue_Proyectado', ascending=False)
    
    total_rev = df_full['Revenue_Proyectado'].sum()
    if total_rev > 0:
        df_full['Acumulado_Pct'] = df_full['Revenue_Proyectado'].cumsum() / total_rev
        conditions = [
            (df_full['Acumulado_Pct'] <= 0.8),
            (df_full['Acumulado_Pct'] <= 0.95)
        ]
        choices = ['A (Premium)', 'B (Estándar)']
        df_full['Clasificacion_ABC'] = np.select(conditions, choices, default='C (Cola Larga)')
    else:
        df_full['Clasificacion_ABC'] = 'C (Cola Larga)'

    return df_full, df_history

# ==========================================
# 4. REPORTING AUTOMATIZADO (XLSX)
# ==========================================

def generar_reporte_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Hoja 1: Resumen Ejecutivo
    df_resumen = df[['Nombre', 'Categoria', 'Stock', 'Estado', 'A_Comprar', 'Inversion_Compra', 'Dias_Cobertura', 'GMROI']].copy()
    df_resumen.to_excel(writer, sheet_name='Dashboard', index=False)
    
    # Hoja 2: Conteo Físico (Formateada)
    df_auditoria = df[['Nombre', 'Categoria', 'Stock']].copy()
    df_auditoria['Conteo_Fisico'] = ""
    df_auditoria['Diferencia'] = ""
    df_auditoria.to_excel(writer, sheet_name='Auditoria_Fisica', index=False)
    
    # Formateo
    wb = writer.book
    ws = writer.sheets['Auditoria_Fisica']
    fmt_header = wb.add_format({'bold': True, 'bg_color': '#1e293b', 'font_color': 'white'})
    ws.set_column('A:B', 25)
    ws.write(0, 0, "Nombre", fmt_header) # Re-escribir cabecera con estilo
    
    writer.close()
    return output.getvalue()

# ==========================================
# 5. UI: INTERFAZ DE USUARIO MAESTRA
# ==========================================

def main():
    st.title("Nexus Inventory™")
    st.caption("Sistema de Inteligencia Logística & Financiera v2.0")

    # --- CARGA ---
    ws_inv, ws_ven = conectar_db()
    if not ws_inv: return # Stop si no hay conexión

    with st.spinner("🔄 Procesando Algoritmos Predictivos..."):
        df_inv_raw = leer_data(ws_inv, "inventario")
        df_ven_raw = leer_data(ws_ven, "ventas")
        
        if df_inv_raw.empty:
            st.error("❌ El inventario está vacío o no se pudo leer.")
            return

    # --- SIDEBAR DE CONTROL ---
    with st.sidebar:
        st.header("🎛️ Centro de Mando")
        
        # Simulador
        st.subheader("🔮 Simulador de Futuro")
        growth = st.slider("Crecimiento Esperado (%)", -50, 100, 0, help="Ajusta esto para ver cómo cambia la necesidad de compra si vendes más o menos.")
        if growth != 0:
            st.info(f"Simulando escenario: {growth:+}% ventas")
            
        # Filtros
        st.subheader("🔍 Filtros Globales")
        cats = sorted(df_inv_raw['Categoria'].unique()) if 'Categoria' in df_inv_raw.columns else []
        sel_cat = st.multiselect("Categoría", cats)
        
        # Ejecución del Motor
        df, df_hist = motor_analisis_master(df_inv_raw, df_ven_raw, growth)
        
        # Aplicar filtro visual
        if sel_cat:
            df = df[df['Categoria'].isin(sel_cat)]
            if not df_hist.empty:
                # Filtrar historial requiere cruzar nombres
                nombres_filtrados = df['Nombre'].unique()
                df_hist = df_hist[df_hist['Nombre'].isin(nombres_filtrados)]

        st.markdown("---")
        st.download_button(
            "📥 Descargar Informe Completo",
            data=generar_reporte_excel(df),
            file_name="Reporte_Nexus.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --- KPI HEADER ---
    col1, col2, col3, col4 = st.columns(4)
    
    inv_val = df['Valor_Inv_Costo'].sum()
    sales_potential = (df['Velocidad_Diaria'] * 30 * df['Precio']).sum()
    stockout_loss = df[df['Estado'].str.contains("AGOTADO")]['Velocidad_Diaria'] * df['Precio']
    stockout_loss_total = stockout_loss.sum()
    gmroi_avg = df[df['Valor_Inv_Costo'] > 0]['GMROI'].mean()

    col1.metric("Valor Inventario", f"${inv_val:,.0f}", help="Dinero actual en bodega (Costo)")
    col2.metric("Ventas Proyectadas (Mes)", f"${sales_potential:,.0f}", delta=f"{growth}% Escenario")
    col3.metric("Pérdida Diaria (Stockout)", f"${stockout_loss_total:,.0f}", delta="Acción Inmediata", delta_color="inverse")
    col4.metric("GMROI Promedio", f"{gmroi_avg:.2f}x", help="Por cada $1 invertido, recuperas esto en margen bruto anual.")

    # --- TABS DE NAVEGACIÓN ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard 360", 
        "📈 Tendencias y Tiempo", 
        "🛒 Planificador de Compras", 
        "💀 Cementerio de Stock",
        "💎 Estrategia ABC"
    ])

    # 1. DASHBOARD
    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Salud del Ecosistema")
            df_status = df['Estado'].value_counts().reset_index()
            df_status.columns = ['Estado', 'Count']
            
            fig = px.bar(df_status, x='Count', y='Estado', orientation='h', 
                         color='Estado', text='Count',
                         color_discrete_map={
                             "✅ Saludable": "#10b981",
                             "🚨 AGOTADO (Perdida Venta)": "#ef4444",
                             "🔥 Crítico (Bajo Seguridad)": "#f97316",
                             "⚠️ Reorden (Pedir ya)": "#eab308",
                             "🧊 Obsoleto (> 4 meses)": "#3b82f6",
                             "💀 Stock Muerto": "#64748b"
                         })
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("Top Rentabilidad")
            # Treemap de Margen
            if 'Categoria' in df.columns:
                fig_tree = px.treemap(df, path=['Categoria', 'Nombre'], values='Valor_Inv_Costo',
                                      color='GMROI', color_continuous_scale='RdYlGn',
                                      title="Inventario por Valor y Retorno (GMROI)")
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.info("Necesitas categorizar productos para ver el mapa de calor.")

    # 2. TENDENCIAS (NUEVO)
    with tab2:
        st.subheader("⏳ Máquina del Tiempo de Ventas")
        if not df_hist.empty:
            # Agrupar por semana
            df_hist['Fecha'] = pd.to_datetime(df_hist['Fecha'])
            ventas_tiempo = df_hist.groupby([pd.Grouper(key='Fecha', freq='W-MON'), 'Nombre'])['Cantidad'].sum().reset_index()
            
            # Selector de productos para limpiar el gráfico
            top_products = df.nlargest(5, 'Revenue_Proyectado')['Nombre'].tolist()
            selected_prods = st.multiselect("Comparar Productos:", df['Nombre'].unique(), default=top_products)
            
            df_chart = ventas_tiempo[ventas_tiempo['Nombre'].isin(selected_prods)]
            
            fig_line = px.line(df_chart, x='Fecha', y='Cantidad', color='Nombre', markers=True,
                               title="Evolución Semanal de Ventas")
            fig_line.update_xaxes(dtick="M1", tickformat="%b %d")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("No hay suficientes datos históricos de ventas con fechas válidas.")

    # 3. PLANIFICADOR DE COMPRAS
    with tab3:
        st.subheader("🧠 Motor de Reabastecimiento Inteligente")
        st.markdown("""
        Este módulo calcula cuánto comprar basándose en:
        1. **Stock de Seguridad:** Para cubrir imprevistos.
        2. **Punto de Reorden:** Cuándo hacer el pedido.
        3. **Simulador:** El % de crecimiento seleccionado en el menú lateral.
        """)
        
        # Filtro rápido
        urgentes = df[df['A_Comprar'] > 0].sort_values('Estado')
        
        if not urgentes.empty:
            costo_total_compra = urgentes['Inversion_Compra'].sum()
            st.success(f"💰 Presupuesto Recomendado: **${costo_total_compra:,.2f}**")
            
            st.dataframe(
                urgentes[['Nombre', 'Stock', 'Safety_Stock', 'Punto_Reorden', 'A_Comprar', 'Inversion_Compra', 'Estado', 'Proveedor'] if 'Proveedor' in df.columns else ['Nombre', 'Stock', 'Safety_Stock', 'Punto_Reorden', 'A_Comprar', 'Inversion_Compra', 'Estado']],
                column_config={
                    "Safety_Stock": st.column_config.NumberColumn("Colchón Seguridad", help="Stock mínimo intocable"),
                    "Punto_Reorden": st.column_config.NumberColumn("Gatillo Pedido", help="Si baja de aquí, pide"),
                    "A_Comprar": st.column_config.NumberColumn("CANTIDAD PEDIR", format="%.0f 📦"),
                    "Inversion_Compra": st.column_config.NumberColumn("Costo Estimado", format="$%.2f"),
                },
                use_container_width=True
            )
        else:
            st.balloons()
            st.info("Todo perfecto. Niveles de inventario óptimos según la demanda actual.")

    # 4. STOCK MUERTO
    with tab4:
        st.subheader("⚰️ Análisis de Obsolescencia")
        col_dead1, col_dead2 = st.columns(2)
        
        muertos = df[df['Estado'].str.contains("Muerto|Obsoleto")].copy()
        
        if not muertos.empty:
            capital_preso = muertos['Valor_Inv_Costo'].sum()
            with col_dead1:
                st.error(f"Capital Congelado: ${capital_preso:,.2f}")
                st.caption("Dinero que podrías usar para comprar productos 'Clase A'.")
            
            with col_dead2:
                st.markdown("#### 💡 Estrategias de Liquidación")
                st.markdown("""
                - **Combos:** Agrúpalos con productos estrella.
                - **Flash Sale:** Descuento del 30-50%.
                - **Donación:** Beneficio fiscal si aplica.
                """)
            
            st.dataframe(muertos[['Nombre', 'Stock', 'Dias_Cobertura', 'Costo', 'Valor_Inv_Costo']], use_container_width=True)
        else:
            st.success("¡Increíble! No tienes stock obsoleto.")

    # 5. ABC STRATEGY
    with tab5:
        st.subheader("📐 Matriz Estratégica ABC (Pareto)")
        c_abc1, c_abc2 = st.columns([2,1])
        
        with c_abc1:
            fig_scat = px.scatter(df, x='Revenue_Proyectado', y='Margen_Pct', 
                                  size='Valor_Inv_Costo', color='Clasificacion_ABC',
                                  hover_name='Nombre',
                                  labels={'Revenue_Proyectado': 'Ventas Proyectadas ($)', 'Margen_Pct': 'Margen %'},
                                  title="Mapa de Estrellas vs Vacas Lecheras")
            st.plotly_chart(fig_scat, use_container_width=True)
            
        with c_abc2:
            st.markdown("#### Resumen por Clase")
            resumen_abc = df.groupby('Clasificacion_ABC').agg({
                'Nombre': 'count',
                'Valor_Inv_Costo': 'sum',
                'Revenue_Proyectado': 'sum'
            }).reset_index()
            st.dataframe(resumen_abc, hide_index=True)

if __name__ == "__main__":
    main()
