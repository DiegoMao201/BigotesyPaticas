import streamlit as st
import pandas as pd
import gspread
from io import BytesIO
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS "NEXUS GOLD"
# ==========================================

st.set_page_config(
    page_title="Nexus: Master Inventory Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS de Alta Gama
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; }
    
    /* KPI Cards */
    div[data-testid="metric-container"] {
        background: white;
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
    
    /* Tablas */
    .stDataFrame { 
        border-radius: 12px;
        border: 1px solid #f1f5f9;
        overflow: hidden;
    }
    
    /* Headers */
    h1, h2, h3 { color: #0f172a; font-weight: 700; letter-spacing: -0.5px; }
    
    /* Custom Alerts */
    .nexus-alert { padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y ESTRUCTURA DE DATOS (EXACTA)
# ==========================================

@st.cache_resource(ttl=600)
def conectar_db():
    """Conexión robusta a Google Sheets."""
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 CRÍTICO: Faltan los secretos 'google_service_account'.")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Intentamos conectar a las hojas con tus nombres exactos
        try: ws_inv = sh.worksheet("Inventario")
        except: ws_inv = None
        
        try: ws_ven = sh.worksheet("Ventas")
        except: ws_ven = None
            
        return ws_inv, ws_ven
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None, None

def garantizar_unicidad_columnas(df):
    """
    🛡️ ESCUDO ANTI-CRASH:
    Renombra columnas duplicadas (ej: Costo, Costo) a (Costo, Costo_1)
    para evitar que Plotly/Narwhals colapsen.
    """
    df = df.copy()
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique(): 
        cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols
    return df

def normalizar_datos(df, tipo):
    """
    Mapeo EXACTO basado en tus columnas.
    """
    if df.empty: return df
    
    # Estandarizamos nombres de columnas para manipulación interna
    # TUS COLUMNAS -> COLUMNAS DEL SISTEMA
    mapa_inventario = {
        'ID_Producto': 'ID',
        'SKU_Proveedor': 'SKU',
        'Nombre': 'Nombre',
        'Stock': 'Stock',
        'Precio': 'Precio',
        'Costo': 'Costo',
        'Categoria': 'Categoria'
    }
    
    mapa_ventas = {
        'ID_Venta': 'ID_Venta',
        'Fecha': 'Fecha',
        'Items': 'Items',
        'Total': 'Total_Venta'
    }
    
    # Renombrar solo las columnas que existen
    if tipo == "inventario":
        df = df.rename(columns=mapa_inventario)
    elif tipo == "ventas":
        df = df.rename(columns=mapa_ventas)
        
    # Limpieza de duplicados post-renombramiento
    df = garantizar_unicidad_columnas(df)
    
    # Garantía de columnas críticas (Si faltan, se crean vacías para no romper el código)
    if tipo == "inventario":
        required = ['Nombre', 'Stock', 'Precio', 'Costo', 'Categoria']
        for col in required:
            if col not in df.columns:
                df[col] = 0 if col != 'Nombre' and col != 'Categoria' else 'General'
                
    elif tipo == "ventas":
        if 'Fecha' not in df.columns: df['Fecha'] = datetime.now()
        if 'Items' not in df.columns: df['Items'] = ''

    return df

def clean_currency(val):
    """Limpia símbolos de moneda y convierte a float."""
    if isinstance(val, (int, float, np.number)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace('€', '').replace('COP', '').replace(' ', '').strip()
        val = val.replace('.', '').replace(',', '.') # Asume formato latino (1.000,00) o US (1,000.00) según configuración. Ajustado a estándar float.
        # Intento robusto: eliminar todo menos números y punto
        import re
        try:
            # Eliminar comas si se usan como separador de miles
            val_clean = val.replace(',', '') 
            return float(val_clean)
        except: return 0.0
    return 0.0

@st.cache_data(ttl=300)
def leer_data(_ws, tipo):
    if _ws is None: return pd.DataFrame()
    try:
        data = _ws.get_all_records()
        if not data: return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # 1. Normalización basada en tus columnas
        df = normalizar_datos(df, tipo)
        
        # 2. Conversión Numérica
        cols_num = ['Precio', 'Stock', 'Costo', 'Total_Venta']
        for c in cols_num:
            if c in df.columns:
                df[c] = df[c].apply(clean_currency)
                
        # 3. Conversión de Fechas
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
            if tipo == "ventas":
                df = df.dropna(subset=['Fecha'])
            
        return df
    except Exception as e:
        st.error(f"Error procesando datos de {tipo}: {e}")
        return pd.DataFrame()

# ==========================================
# 3. MOTOR DE INTELIGENCIA DE NEGOCIOS (BI)
# ==========================================

def motor_analisis_master(df_inv, df_ven, growth_scenario=0.0):
    if df_inv.empty: return pd.DataFrame(), pd.DataFrame()

    # --- A. PARSEO DE VENTAS (TUS ITEMS) ---
    ventas_por_producto = {}
    ventas_historicas = []
    
    if not df_ven.empty:
        # Filtro: Últimos 90 días
        cutoff_date = datetime.now() - timedelta(days=90)
        df_ven_recent = df_ven[df_ven['Fecha'] >= cutoff_date].copy()
        
        for idx, row in df_ven_recent.iterrows():
            items_str = str(row.get('Items', ''))
            fecha_venta = row['Fecha']
            
            # Lógica de Parseo: Asumimos formato "Producto A, Producto B (x2)"
            if items_str and items_str.lower() != "nan":
                parts = items_str.split(",") # Separar items por coma
                for p in parts:
                    try:
                        p = p.strip()
                        cant = 1
                        nombre = p
                        
                        # Detectar cantidad "(x3)"
                        if "(x" in p:
                            nombre_parts = p.split("(x")
                            nombre = nombre_parts[0].strip()
                            cant_str = nombre_parts[1].replace(")", "").strip()
                            if cant_str.isdigit():
                                cant = int(cant_str)
                        
                        # Acumular
                        ventas_por_producto[nombre] = ventas_por_producto.get(nombre, 0) + cant
                        
                        # Historial para gráfica
                        ventas_historicas.append({
                            'Fecha': fecha_venta,
                            'Nombre': nombre,
                            'Cantidad': cant
                        })
                    except: continue

    df_history = pd.DataFrame(ventas_historicas)
    
    # --- B. CÁLCULO DE VELOCIDAD ---
    df_metrics = pd.DataFrame(list(ventas_por_producto.items()), columns=['Nombre', 'Ventas_90d'])
    
    if df_metrics.empty:
        df_metrics = pd.DataFrame(columns=['Nombre', 'Ventas_90d'])
        df_metrics['Velocidad_Diaria'] = 0.0
    else:
        df_metrics['Velocidad_Diaria'] = df_metrics['Ventas_90d'] / 90
    
    # Simulador de Crecimiento
    if growth_scenario != 0:
        df_metrics['Velocidad_Diaria'] = df_metrics['Velocidad_Diaria'] * (1 + (growth_scenario/100))

    # --- C. MERGE INTELIGENTE ---
    # Unimos Inventario con Métricas de Venta
    df_full = pd.merge(df_inv, df_metrics, on='Nombre', how='left')
    
    # 🔥 ESCUDO: Volver a limpiar duplicados tras el merge por si acaso
    df_full = garantizar_unicidad_columnas(df_full)
    
    df_full['Ventas_90d'] = df_full['Ventas_90d'].fillna(0)
    df_full['Velocidad_Diaria'] = df_full['Velocidad_Diaria'].fillna(0)
    
    # --- D. MATEMÁTICA FINANCIERA ---
    # Relleno de seguridad para costos/precios cero
    mask_no_cost = (df_full['Costo'] <= 0) & (df_full['Precio'] > 0)
    df_full.loc[mask_no_cost, 'Costo'] = df_full.loc[mask_no_cost, 'Precio'] * 0.6
    
    df_full['Margen_Unitario'] = df_full['Precio'] - df_full['Costo']
    df_full['Margen_Pct'] = (df_full['Margen_Unitario'] / df_full['Precio'].replace(0, 1)).fillna(0) * 100
    df_full['Valor_Inv_Costo'] = df_full['Stock'] * df_full['Costo']
    
    # GMROI (Rentabilidad del inventario)
    df_full['GMROI'] = np.where(
        df_full['Valor_Inv_Costo'] > 0,
        (df_full['Margen_Unitario'] * df_full['Velocidad_Diaria'] * 365) / df_full['Valor_Inv_Costo'],
        0
    )

    # --- E. LOGÍSTICA PREDICTIVA ---
    LEAD_TIME_DIAS = 7  # Tiempo estimado de proveedor
    Z_SCORE = 1.65      # Nivel de servicio 95%
    
    df_full['Safety_Stock'] = np.ceil(Z_SCORE * np.sqrt(LEAD_TIME_DIAS) * (df_full['Velocidad_Diaria'] * 0.5))
    df_full['Punto_Reorden'] = (df_full['Velocidad_Diaria'] * LEAD_TIME_DIAS) + df_full['Safety_Stock']
    
    TARGET_DIAS = 30
    df_full['Stock_Maximo'] = (df_full['Velocidad_Diaria'] * TARGET_DIAS) + df_full['Safety_Stock']
    
    # Cálculo de Compra
    df_full['A_Comprar'] = (df_full['Stock_Maximo'] - df_full['Stock']).clip(lower=0)
    df_full['Inversion_Compra'] = df_full['A_Comprar'] * df_full['Costo']

    # --- F. ESTADOS ---
    df_full['Dias_Cobertura'] = np.where(df_full['Velocidad_Diaria'] > 0, df_full['Stock'] / df_full['Velocidad_Diaria'], 999)
    
    def clasificar_estado(row):
        if row['Stock'] <= 0 and row['Velocidad_Diaria'] > 0: return "🚨 AGOTADO"
        if row['Stock'] <= row['Safety_Stock']: return "🔥 Crítico"
        if row['Stock'] <= row['Punto_Reorden']: return "⚠️ Reorden"
        if row['Dias_Cobertura'] > 120: return "🧊 Obsoleto"
        if row['Velocidad_Diaria'] == 0 and row['Stock'] > 0: return "💀 Stock Muerto"
        return "✅ Saludable"
        
    df_full['Estado'] = df_full.apply(clasificar_estado, axis=1)
    
    # --- G. CLASIFICACIÓN ABC ---
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
# 4. EXPORTACIÓN A EXCEL (BLINDADA)
# ==========================================

def generar_reporte_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # 1. Definir columnas finales deseadas
    # Usamos .get() para evitar KeyError si algo faltara
    cols_export = ['ID', 'SKU', 'Nombre', 'Categoria', 'Stock', 'Estado', 
                   'A_Comprar', 'Inversion_Compra', 'GMROI', 'Dias_Cobertura']
    
    # Crear un DF limpio solo con lo que existe
    df_clean = df.copy()
    existing_cols = [c for c in cols_export if c in df_clean.columns]
    
    df_resumen = df_clean[existing_cols]
    df_resumen.to_excel(writer, sheet_name='Dashboard', index=False)
    
    # 2. Hoja de Auditoría
    cols_audit = ['ID', 'Nombre', 'Stock']
    existing_audit = [c for c in cols_audit if c in df_clean.columns]
    df_audit = df_clean[existing_audit].copy()
    df_audit['Conteo_Fisico'] = ""
    df_audit['Diferencia'] = ""
    df_audit.to_excel(writer, sheet_name='Auditoria_Fisica', index=False)
    
    # 3. Formato
    wb = writer.book
    ws = writer.sheets['Dashboard']
    fmt_currency = wb.add_format({'num_format': '$#,##0.00'})
    
    # Intentar aplicar formato moneda a columnas de dinero
    try:
        if 'Inversion_Compra' in df_resumen.columns:
            idx = df_resumen.columns.get_loc('Inversion_Compra')
            ws.set_column(idx, idx, 18, fmt_currency)
    except: pass
    
    ws.set_column(0, 3, 20) # Ancho columnas texto
    
    writer.close()
    return output.getvalue()

# ==========================================
# 5. UI: INTERFAZ DE USUARIO MAESTRA
# ==========================================

def main():
    st.title("Nexus Inventory™ Gold")
    st.caption("Sistema de Inteligencia Logística v5.0 (Custom Schema)")

    # --- CARGA ---
    ws_inv, ws_ven = conectar_db()
    if not ws_inv: return 

    with st.spinner("🔄 Conectando a Matriz de Datos..."):
        df_inv_raw = leer_data(ws_inv, "inventario")
        df_ven_raw = leer_data(ws_ven, "ventas")
        
        if df_inv_raw.empty:
            st.error("❌ El inventario está vacío o no coincide con las columnas especificadas.")
            st.info("Columnas esperadas: ID_Producto, SKU_Proveedor, Nombre, Stock, Precio, Costo, Categoria")
            return

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🎛️ Centro de Mando")
        
        # Simulador
        st.subheader("🔮 Simulador")
        growth = st.slider("Crecimiento Esperado (%)", -50, 100, 0)
        
        # Filtros
        st.subheader("🔍 Filtros")
        cats = sorted(df_inv_raw['Categoria'].unique()) if 'Categoria' in df_inv_raw.columns else []
        sel_cat = st.multiselect("Categoría", cats)
        
        # MOTOR PRINCIPAL
        df, df_hist = motor_analisis_master(df_inv_raw, df_ven_raw, growth)
        
        # Aplicar Filtros Visuales
        if sel_cat:
            df = df[df['Categoria'].isin(sel_cat)]
            if not df_hist.empty:
                nombres_filtro = df['Nombre'].unique()
                df_hist = df_hist[df_hist['Nombre'].isin(nombres_filtro)]

        st.markdown("---")
        
        # Botón Descarga
        excel_data = generar_reporte_excel(df)
        st.download_button(
            "📥 Descargar Informe Maestro",
            data=excel_data,
            file_name=f"Nexus_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --- KPI HEADER ---
    col1, col2, col3, col4 = st.columns(4)
    
    # Cálculos seguros (usando .get o suma directa si columna existe)
    inv_val = df['Valor_Inv_Costo'].sum() if 'Valor_Inv_Costo' in df.columns else 0
    sales_proj = df['Revenue_Proyectado'].sum() if 'Revenue_Proyectado' in df.columns else 0
    
    lost_val = 0
    if 'Estado' in df.columns:
        lost_df = df[df['Estado'].str.contains("AGOTADO")]
        if not lost_df.empty:
            lost_val = (lost_df['Velocidad_Diaria'] * lost_df['Precio']).sum()

    gmroi_avg = df[df['Valor_Inv_Costo'] > 0]['GMROI'].mean() if 'GMROI' in df.columns else 0

    col1.metric("Valor Inventario (Costo)", f"${inv_val:,.0f}")
    col2.metric("Ventas Proyectadas (Mes)", f"${sales_proj:,.0f}", delta=f"{growth}% Escenario")
    col3.metric("Pérdida Diaria (Stockout)", f"${lost_val:,.0f}", delta="Crítico", delta_color="inverse")
    col4.metric("GMROI Promedio", f"{gmroi_avg:.2f}x")

    # --- TABS ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard 360", "📈 Tendencias", "🛒 Compras", "💀 Obsolescencia", "💎 Estrategia ABC"
    ])

    # 1. DASHBOARD
    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Salud del Ecosistema")
            if 'Estado' in df.columns:
                df_status = df['Estado'].value_counts().reset_index()
                df_status.columns = ['Estado', 'Count']
                
                fig = px.bar(df_status, x='Count', y='Estado', orientation='h', 
                             color='Estado', text='Count',
                             color_discrete_map={
                                 "✅ Saludable": "#10b981",
                                 "🚨 AGOTADO": "#ef4444",
                                 "🔥 Crítico": "#f97316",
                                 "⚠️ Reorden": "#eab308",
                                 "🧊 Obsoleto": "#3b82f6",
                                 "💀 Stock Muerto": "#64748b"
                             })
                st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("Mapa de Rentabilidad")
            # IMPORTANTE: Aquí aplicamos la corrección final para evitar DuplicateError
            if 'Categoria' in df.columns and not df.empty:
                df_plot = garantizar_unicidad_columnas(df) # Limpieza final antes de plot
                try:
                    fig_tree = px.treemap(df_plot, path=['Categoria', 'Nombre'], values='Valor_Inv_Costo',
                                          color='GMROI', color_continuous_scale='RdYlGn')
                    st.plotly_chart(fig_tree, use_container_width=True)
                except Exception as e:
                    st.warning(f"No se pudo generar mapa de calor: {e}")

    # 2. TENDENCIAS
    with tab2:
        if not df_hist.empty:
            df_hist['Fecha'] = pd.to_datetime(df_hist['Fecha'])
            ventas_tiempo = df_hist.groupby([pd.Grouper(key='Fecha', freq='W-MON'), 'Nombre'])['Cantidad'].sum().reset_index()
            
            top_list = df.nlargest(5, 'Revenue_Proyectado')['Nombre'].tolist() if 'Revenue_Proyectado' in df.columns else []
            selected = st.multiselect("Comparar productos:", df['Nombre'].unique(), default=top_list)
            
            df_chart = ventas_tiempo[ventas_tiempo['Nombre'].isin(selected)]
            fig_line = px.line(df_chart, x='Fecha', y='Cantidad', color='Nombre', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No hay suficientes datos de ventas históricos.")

    # 3. COMPRAS
    with tab3:
        if 'A_Comprar' in df.columns:
            urgentes = df[df['A_Comprar'] > 0].sort_values('Estado')
            if not urgentes.empty:
                total_req = urgentes['Inversion_Compra'].sum()
                st.success(f"💰 Inversión Sugerida: **${total_req:,.2f}**")
                
                cols_show = ['ID', 'Nombre', 'Stock', 'Punto_Reorden', 'A_Comprar', 'Inversion_Compra', 'Estado']
                # Filtrar solo columnas que existen
                cols_final = [c for c in cols_show if c in urgentes.columns]
                
                st.dataframe(
                    urgentes[cols_final],
                    column_config={
                        "A_Comprar": st.column_config.NumberColumn("PEDIR 📦", format="%.0f"),
                        "Inversion_Compra": st.column_config.NumberColumn("Costo Estimado", format="$%.2f")
                    },
                    use_container_width=True
                )
            else:
                st.balloons()
                st.info("Inventario Optimizado. No se requiere compra.")

    # 4. OBSOLESCENCIA
    with tab4:
        if 'Estado' in df.columns:
            muertos = df[df['Estado'].str.contains("Muerto|Obsoleto")].copy()
            if not muertos.empty:
                val_muerto = muertos['Valor_Inv_Costo'].sum()
                st.error(f"Capital Estancado: ${val_muerto:,.2f}")
                st.dataframe(muertos[['ID', 'Nombre', 'Stock', 'Dias_Cobertura', 'Valor_Inv_Costo']], use_container_width=True)
            else:
                st.success("Inventario fresco. No hay obsolescencia.")

    # 5. ABC
    with tab5:
        if 'Clasificacion_ABC' in df.columns:
            c_abc1, c_abc2 = st.columns([2,1])
            with c_abc1:
                fig_scat = px.scatter(df, x='Revenue_Proyectado', y='Margen_Pct', 
                                      size='Valor_Inv_Costo', color='Clasificacion_ABC',
                                      hover_name='Nombre', title="Matriz Estratégica")
                st.plotly_chart(fig_scat, use_container_width=True)
            
            with c_abc2:
                resumen = df.groupby('Clasificacion_ABC').agg({
                    'Nombre': 'count', 
                    'Valor_Inv_Costo': 'sum',
                    'Revenue_Proyectado': 'sum'
                }).reset_index()
                st.dataframe(resumen, hide_index=True)

if __name__ == "__main__":
    main()
