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
    .stApp { background-color: #f8fafc; }
    
    /* Headers */
    h1, h2, h3 { color: #0f172a; font-weight: 700; letter-spacing: -0.5px; }
    
    /* KPI Cards Avanzadas */
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
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05); 
        border-radius: 12px;
        border: 1px solid #f1f5f9;
        overflow: hidden;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        font-size: 0.9rem;
        border: 1px solid transparent;
        color: #64748b;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: white; border-right: 1px solid #e2e8f0; }
    
    /* Custom Alerts */
    .nexus-alert { padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid transparent; }
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
    Inteligencia Artificial Simbólica para corregir nombres de columnas mal escritos.
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
        'categoria': 'Categoria', 'cat': 'Categoria', 'familia': 'Categoria', 'category': 'Categoria',
        'proveedor': 'Proveedor', 'supplier': 'Proveedor'
    }
    
    new_cols = {}
    for col in df.columns:
        match_found = False
        if col in mapa:
            new_cols[col] = mapa[col]
            match_found = True
        else:
            for key, val in mapa.items():
                if key in col:
                    new_cols[col] = val
                    match_found = True
                    break
        if not match_found:
            new_cols[col] = col.title()
            
    df = df.rename(columns=new_cols)
    
    # 3. GARANTÍA DE ESTRUCTURA (Anti-Crash)
    if tipo == "inventario":
        # Aseguramos columnas críticas
        if 'Nombre' not in df.columns: df['Nombre'] = 'Desconocido'
        if 'Stock' not in df.columns: df['Stock'] = 0
        if 'Precio' not in df.columns: df['Precio'] = 0.0
        if 'Costo' not in df.columns: df['Costo'] = 0.0
        if 'Categoria' not in df.columns: df['Categoria'] = 'General' # Fix para KeyError
    
    elif tipo == "ventas":
        if 'Fecha' not in df.columns: df['Fecha'] = datetime.now()
        if 'Items' not in df.columns: df['Items'] = ''
        
    return df

def clean_currency(val):
    """Sanitizador de números."""
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
    """ETL Pipeline."""
    if _ws is None: return pd.DataFrame()
    try:
        data = _ws.get_all_records()
        if not data: return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df = normalizar_columnas(df, tipo)
        
        cols_num = ['Precio', 'Stock', 'Costo', 'Total', 'Cantidad']
        for c in cols_num:
            if c in df.columns:
                df[c] = df[c].apply(clean_currency)
                
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
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
    if df_inv.empty: return pd.DataFrame(), pd.DataFrame()

    # --- A. PROCESAMIENTO DE VENTAS ---
    ventas_por_producto = {}
    ventas_historicas = []
    
    if not df_ven.empty:
        cutoff_date = datetime.now() - timedelta(days=90)
        df_ven_recent = df_ven[df_ven['Fecha'] >= cutoff_date].copy()
        
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
                        
                        ventas_por_producto[nombre] = ventas_por_producto.get(nombre, 0) + cant
                        ventas_historicas.append({
                            'Fecha': fecha_venta, 'Nombre': nombre, 'Cantidad': cant
                        })
                    except: continue

    df_history = pd.DataFrame(ventas_historicas)
    
    # --- B. CÁLCULO DE VELOCIDAD ---
    df_metrics = pd.DataFrame(list(ventas_por_producto.items()), columns=['Nombre', 'Ventas_90d'])
    
    # Prevenir error si df_metrics está vacío
    if df_metrics.empty:
        df_metrics = pd.DataFrame(columns=['Nombre', 'Ventas_90d', 'Velocidad_Diaria'])
    else:
        df_metrics['Velocidad_Diaria'] = df_metrics['Ventas_90d'] / 90
    
    if growth_scenario != 0:
        df_metrics['Velocidad_Diaria'] = df_metrics['Velocidad_Diaria'] * (1 + (growth_scenario/100))

    # --- C. FUSIÓN ---
    df_full = pd.merge(df_inv, df_metrics, on='Nombre', how='left')
    df_full['Ventas_90d'] = df_full['Ventas_90d'].fillna(0)
    df_full['Velocidad_Diaria'] = df_full['Velocidad_Diaria'].fillna(0)
    
    # --- D. MATEMÁTICA FINANCIERA ---
    if 'Costo' not in df_full.columns: df_full['Costo'] = 0.0
    if 'Precio' not in df_full.columns: df_full['Precio'] = 0.0
    
    mask_no_cost = (df_full['Costo'] <= 0) & (df_full['Precio'] > 0)
    df_full.loc[mask_no_cost, 'Costo'] = df_full.loc[mask_no_cost, 'Precio'] * 0.6
    
    df_full['Margen_Unitario'] = df_full['Precio'] - df_full['Costo']
    df_full['Margen_Pct'] = (df_full['Margen_Unitario'] / df_full['Precio'].replace(0, 1)).fillna(0) * 100
    df_full['Valor_Inv_Costo'] = df_full['Stock'] * df_full['Costo']
    
    # GMROI
    df_full['GMROI'] = np.where(
        df_full['Valor_Inv_Costo'] > 0,
        (df_full['Margen_Unitario'] * df_full['Velocidad_Diaria'] * 365) / df_full['Valor_Inv_Costo'],
        0
    )

    # --- E. STOCK DE SEGURIDAD ---
    LEAD_TIME_DIAS = 7 
    Z_SCORE_95 = 1.65
    
    df_full['Safety_Stock'] = np.ceil(Z_SCORE_95 * np.sqrt(LEAD_TIME_DIAS) * (df_full['Velocidad_Diaria'] * 0.5))
    df_full['Punto_Reorden'] = (df_full['Velocidad_Diaria'] * LEAD_TIME_DIAS) + df_full['Safety_Stock']
    
    TARGET_DIAS = 30
    df_full['Stock_Maximo'] = (df_full['Velocidad_Diaria'] * TARGET_DIAS) + df_full['Safety_Stock']
    df_full['A_Comprar'] = (df_full['Stock_Maximo'] - df_full['Stock']).clip(lower=0)
    df_full['Inversion_Compra'] = df_full['A_Comprar'] * df_full['Costo']

    # --- F. ESTADOS ---
    df_full['Dias_Cobertura'] = np.where(df_full['Velocidad_Diaria'] > 0, df_full['Stock'] / df_full['Velocidad_Diaria'], 999)
    
    def clasificar_estado(row):
        if row['Stock'] <= 0 and row['Velocidad_Diaria'] > 0: return "🚨 AGOTADO (Perdida Venta)"
        if row['Stock'] <= row['Safety_Stock']: return "🔥 Crítico (Bajo Seguridad)"
        if row['Stock'] <= row['Punto_Reorden']: return "⚠️ Reorden (Pedir ya)"
        if row['Dias_Cobertura'] > 120: return "🧊 Obsoleto (> 4 meses)"
        if row['Velocidad_Diaria'] == 0 and row['Stock'] > 0: return "💀 Stock Muerto"
        return "✅ Saludable"
        
    df_full['Estado'] = df_full.apply(clasificar_estado, axis=1)
    
    # --- G. ABC ---
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
# 4. REPORTING AUTOMATIZADO (FIXED)
# ==========================================

def generar_reporte_excel(df):
    """
    Genera un Excel robusto, creando columnas faltantes para evitar KeyErrors.
    """
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # 1. Definir columnas deseadas y asegurar su existencia
    cols_deseadas = ['Nombre', 'Categoria', 'Stock', 'Estado', 'A_Comprar', 'Inversion_Compra', 'Dias_Cobertura', 'GMROI']
    
    df_export = df.copy()
    
    # Ciclo de seguridad anti-error
    for col in cols_deseadas:
        if col not in df_export.columns:
            if col == 'Categoria':
                df_export[col] = "General"
            elif col == 'Estado':
                df_export[col] = "Desconocido"
            else:
                df_export[col] = 0
                
    # Selección segura
    df_resumen = df_export[cols_deseadas]
    df_resumen.to_excel(writer, sheet_name='Dashboard', index=False)
    
    # 2. Hoja de Auditoría
    cols_audit = ['Nombre', 'Categoria', 'Stock']
    # Asegurar cols para auditoria
    for col in cols_audit:
        if col not in df_export.columns:
            df_export[col] = 0 if col == 'Stock' else ""
            
    df_auditoria = df_export[cols_audit].copy()
    df_auditoria['Conteo_Fisico'] = ""
    df_auditoria['Diferencia'] = ""
    df_auditoria.to_excel(writer, sheet_name='Auditoria_Fisica', index=False)
    
    # 3. Formateo Visual
    workbook = writer.book
    worksheet = writer.sheets['Dashboard']
    
    # Formatos
    fmt_currency = workbook.add_format({'num_format': '$#,##0.00'})
    fmt_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    fmt_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
    
    # Aplicar formato moneda a columnas financieras
    # (Asumiendo que Inversion_Compra es la columna F, índice 5)
    worksheet.set_column('F:F', 15, fmt_currency)
    worksheet.set_column('A:A', 30) # Nombre ancho
    
    # Formato condicional básico para Estado (Columna D)
    worksheet.conditional_format('D2:D1000', {'type': 'text',
                                              'criteria': 'containing',
                                              'value': 'AGOTADO',
                                              'format': fmt_red})
                                              
    writer.close()
    return output.getvalue()

# ==========================================
# 5. UI: INTERFAZ DE USUARIO MAESTRA
# ==========================================

def main():
    st.title("Nexus Inventory™")
    st.caption("Sistema de Inteligencia Logística & Financiera v3.0 (Pro Edition)")

    # --- CARGA ---
    ws_inv, ws_ven = conectar_db()
    if not ws_inv: return 

    with st.spinner("🔄 Procesando Algoritmos Predictivos..."):
        df_inv_raw = leer_data(ws_inv, "inventario")
        df_ven_raw = leer_data(ws_ven, "ventas")
        
        if df_inv_raw.empty:
            st.error("❌ El inventario está vacío. Revisa la hoja de Google Sheets.")
            return

    # --- SIDEBAR DE CONTROL ---
    with st.sidebar:
        st.header("🎛️ Centro de Mando")
        
        st.subheader("🔮 Simulador")
        growth = st.slider("Crecimiento Esperado (%)", -50, 100, 0)
        
        st.subheader("🔍 Filtros")
        cats = sorted(df_inv_raw['Categoria'].unique()) if 'Categoria' in df_inv_raw.columns else []
        sel_cat = st.multiselect("Categoría", cats)
        
        # Ejecución del Motor
        df, df_hist = motor_analisis_master(df_inv_raw, df_ven_raw, growth)
        
        if sel_cat:
            df = df[df['Categoria'].isin(sel_cat)]
            if not df_hist.empty:
                nombres = df['Nombre'].unique()
                df_hist = df_hist[df_hist['Nombre'].isin(nombres)]

        st.markdown("---")
        
        # Botón de Descarga Blindado
        try:
            excel_data = generar_reporte_excel(df)
            st.download_button(
                "📥 Descargar Informe",
                data=excel_data,
                file_name=f"Nexus_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error generando Excel: {e}")

    # --- KPI HEADER ---
    col1, col2, col3, col4 = st.columns(4)
    
    inv_val = df['Valor_Inv_Costo'].sum() if 'Valor_Inv_Costo' in df.columns else 0
    sales_potential = df['Revenue_Proyectado'].sum() if 'Revenue_Proyectado' in df.columns else 0
    
    # Manejo seguro de filtros
    if 'Estado' in df.columns:
        lost_sales = df[df['Estado'].str.contains("AGOTADO")]['Velocidad_Diaria'] * df['Precio']
        stockout_loss_total = lost_sales.sum()
    else:
        stockout_loss_total = 0

    gmroi_avg = df[df['Valor_Inv_Costo'] > 0]['GMROI'].mean() if 'GMROI' in df.columns else 0

    col1.metric("Valor Inventario", f"${inv_val:,.0f}")
    col2.metric("Ventas Proyectadas", f"${sales_potential:,.0f}", delta=f"{growth}%")
    col3.metric("Pérdida (Stockout)", f"${stockout_loss_total:,.0f}", delta_color="inverse")
    col4.metric("GMROI Promedio", f"{gmroi_avg:.2f}x")

    # --- TABS ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", "📈 Tendencias", "🛒 Compras", "💀 Muerto", "💎 ABC"
    ])

    # 1. DASHBOARD
    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("Estado del Inventario")
            if 'Estado' in df.columns:
                df_status = df['Estado'].value_counts().reset_index()
                df_status.columns = ['Estado', 'Count']
                fig = px.bar(df_status, x='Count', y='Estado', orientation='h', 
                             color='Estado', text='Count', 
                             color_discrete_sequence=px.colors.qualitative.Bold)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No se pudo calcular el estado del inventario.")
                
        with c2:
            st.subheader("Mapa de Calor")
            if 'Categoria' in df.columns and 'GMROI' in df.columns:
                fig_tree = px.treemap(df, path=['Categoria', 'Nombre'], values='Valor_Inv_Costo',
                                      color='GMROI', color_continuous_scale='RdYlGn')
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.warning("Faltan datos de Categoría o GMROI.")

    # 2. TENDENCIAS
    with tab2:
        if not df_hist.empty:
            df_hist['Fecha'] = pd.to_datetime(df_hist['Fecha'])
            ventas_tiempo = df_hist.groupby([pd.Grouper(key='Fecha', freq='W-MON'), 'Nombre'])['Cantidad'].sum().reset_index()
            
            top_prods = df.nlargest(5, 'Revenue_Proyectado')['Nombre'].tolist() if 'Revenue_Proyectado' in df.columns else []
            sel_prods = st.multiselect("Comparar:", df['Nombre'].unique(), default=top_prods)
            
            chart_data = ventas_tiempo[ventas_tiempo['Nombre'].isin(sel_prods)]
            fig_line = px.line(chart_data, x='Fecha', y='Cantidad', color='Nombre', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No hay histórico de ventas suficiente.")

    # 3. COMPRAS
    with tab3:
        if 'A_Comprar' in df.columns:
            urgentes = df[df['A_Comprar'] > 0].sort_values('Estado')
            if not urgentes.empty:
                total_buy = urgentes['Inversion_Compra'].sum()
                st.success(f"💰 Presupuesto Sugerido: **${total_buy:,.2f}**")
                
                cols_show = ['Nombre', 'Stock', 'Safety_Stock', 'A_Comprar', 'Inversion_Compra', 'Estado']
                if 'Proveedor' in df.columns: cols_show.append('Proveedor')
                
                st.dataframe(
                    urgentes[cols_show],
                    column_config={
                        "A_Comprar": st.column_config.NumberColumn("PEDIR 📦", format="%.0f"),
                        "Inversion_Compra": st.column_config.NumberColumn("Costo $", format="$%.2f")
                    },
                    use_container_width=True
                )
            else:
                st.balloons()
                st.info("Inventario optimizado. No se requieren compras.")

    # 4. MUERTO
    with tab4:
        if 'Estado' in df.columns:
            muertos = df[df['Estado'].str.contains("Muerto|Obsoleto")].copy()
            if not muertos.empty:
                val_muerto = muertos['Valor_Inv_Costo'].sum()
                st.error(f"Capital Estancado: ${val_muerto:,.2f}")
                st.dataframe(muertos[['Nombre', 'Stock', 'Dias_Cobertura', 'Valor_Inv_Costo']], use_container_width=True)
            else:
                st.success("No hay stock obsoleto.")

    # 5. ABC
    with tab5:
        if 'Clasificacion_ABC' in df.columns:
            c_abc1, c_abc2 = st.columns([2,1])
            with c_abc1:
                fig_scat = px.scatter(df, x='Revenue_Proyectado', y='Margen_Pct', 
                                      size='Valor_Inv_Costo', color='Clasificacion_ABC',
                                      hover_name='Nombre')
                st.plotly_chart(fig_scat, use_container_width=True)
            
            with c_abc2:
                resumen = df.groupby('Clasificacion_ABC').agg({
                    'Nombre': 'count', 'Valor_Inv_Costo': 'sum'
                }).reset_index()
                st.dataframe(resumen, hide_index=True)

if __name__ == "__main__":
    main()
