import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURACIÓN "NEXUS PLATINUM"
# ==========================================

st.set_page_config(
    page_title="Nexus AI: Executive Inventory Command",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS DE NIVEL EJECUTIVO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; color: #1e293b; }
    .stApp { background-color: #f1f5f9; }
    
    /* KPI Cards Premium */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #ffffff, #f8fafc);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Tablas Elegantes */
    .stDataFrame { 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-radius: 10px;
    }
    
    /* Títulos */
    h1 { color: #0f172a; font-weight: 800; letter-spacing: -1px; }
    h2, h3 { color: #334155; font-weight: 600; }
    
    /* Alertas IA */
    .ai-insight {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e40af;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        font-size: 0.95rem;
    }
    .ai-urgent {
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        color: #991b1b;
        padding: 15px;
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LIMPIEZA DE DATOS (SISTEMA LATINO)
# ==========================================

def clean_currency_latam(val):
    """
    CORRECCIÓN CRÍTICA DE FORMATO:
    Maneja el formato latino: 1.500,00 (mil quinientos con cero centavos).
    Si recibe 1.500 lo convierte a 1500.0.
    Si recibe 1,500.00 (formato US) intenta detectarlo, pero prioriza la coma como decimal.
    """
    if isinstance(val, (int, float, np.number)):
        return float(val)
    
    if isinstance(val, str):
        # 1. Limpiar símbolos y espacios
        val = val.replace('$', '').replace('€', '').replace('COP', '').replace(' ', '').strip()
        if not val: return 0.0
        
        # 2. Lógica heurística para determinar formato
        # Si hay puntos y comas:
        if '.' in val and ',' in val:
            if val.find('.') < val.find(','): 
                # Formato Latino: 1.000,50 -> Quitar punto, reemplazar coma
                val = val.replace('.', '').replace(',', '.')
            else:
                # Formato US: 1,000.50 -> Quitar coma
                val = val.replace(',', '')
        elif ',' in val:
            # Solo comas. Ej: "50,5" o "1,000"
            # Si tiene más de 3 dígitos después de la coma, es separador de miles (ej: 1,000)
            parts = val.split(',')
            if len(parts[-1]) == 2: # Asumimos decimal (,00 o ,50)
                val = val.replace(',', '.')
            elif len(parts[-1]) == 1: # Decimal (,5)
                val = val.replace(',', '.')
            else: # Probablemente miles (1,000) -> quitar coma
                # PELIGRO: Si es formato latino "1,000" (mil) y pandas leyó string
                # Asumiremos que si el usuario dijo ",00", la coma es decimal.
                val = val.replace(',', '.')
        elif '.' in val:
            # Solo puntos. Ej: "1.000" (mil) o "10.5" (diez y medio)
            # Contar puntos. Si hay más de uno, son miles.
            if val.count('.') > 1:
                val = val.replace('.', '')
            else:
                # Difícil distinción. Asumiremos que punto es miles si son 3 digitos exactos al final y contexto de precios altos,
                # pero por seguridad estándar de Python, punto suele ser decimal.
                # PERO, en LATAM "1.500" es mil quinientos.
                # Si la longitud post punto es 3, asumimos miles y lo quitamos.
                parts = val.split('.')
                if len(parts[-1]) == 3:
                    val = val.replace('.', '')
        
        try:
            return float(val)
        except:
            return 0.0
    return 0.0

# ==========================================
# 3. CONEXIÓN Y CARGA
# ==========================================

@st.cache_resource
def conectar_db():
    try:
        if "google_service_account" not in st.secrets:
            st.error("Faltan secretos de Google Sheets.")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Intentar conectar
        try: ws_inv = sh.worksheet("Inventario")
        except: ws_inv = None
        try: ws_ven = sh.worksheet("Ventas")
        except: ws_ven = None
            
        return ws_inv, ws_ven
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None, None

def normalizar_columnas(df):
    # Forzar nombres únicos para evitar errores de Plotly
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique(): 
        cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols
    return df

@st.cache_data(ttl=300)
def obtener_datos(_ws_inv, _ws_ven):
    if not _ws_inv: return pd.DataFrame(), pd.DataFrame()
    
    # --- INVENTARIO ---
    inv_data = _ws_inv.get_all_records()
    df_inv = pd.DataFrame(inv_data)
    
    # Mapeo y Normalización
    mapa_cols = {
        'ID_Producto': 'ID', 'SKU_Proveedor': 'SKU', 'Nombre': 'Nombre',
        'Stock': 'Stock', 'Precio': 'Precio', 'Costo': 'Costo', 'Categoria': 'Categoria'
    }
    df_inv = df_inv.rename(columns=mapa_cols)
    df_inv = normalizar_columnas(df_inv)
    
    # Limpieza Numérica ROBUSTA
    for col in ['Stock', 'Precio', 'Costo']:
        if col in df_inv.columns:
            df_inv[col] = df_inv[col].apply(clean_currency_latam)
    
    # Rellenar nulos
    if 'Stock' in df_inv.columns: df_inv['Stock'] = df_inv['Stock'].fillna(0)
    
    # --- VENTAS ---
    df_ven = pd.DataFrame()
    if _ws_ven:
        ven_data = _ws_ven.get_all_records()
        df_ven = pd.DataFrame(ven_data)
        if not df_ven.empty:
            df_ven = df_ven.rename(columns={'Fecha': 'Fecha', 'Items': 'Items', 'Total': 'Total'})
            df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
            df_ven = df_ven.dropna(subset=['Fecha'])

    return df_inv, df_ven

# ==========================================
# 4. MOTOR INTELIGENTE (BI + AI PREDICTIVA)
# ==========================================

def procesar_cerebro_negocio(df_inv, df_ven):
    # 1. Parseo de Ventas (Historial detallado)
    historial_ventas = []
    ventas_90d = {}
    
    if not df_ven.empty:
        # Solo últimos 90 días para velocidad real
        fecha_corte = datetime.now() - timedelta(days=90)
        df_ven_act = df_ven[df_ven['Fecha'] >= fecha_corte]
        
        for _, row in df_ven_act.iterrows():
            items = str(row.get('Items', ''))
            fecha = row['Fecha']
            
            if items and items.lower() != 'nan':
                lista_items = items.split(',')
                for prod_str in lista_items:
                    try:
                        prod_str = prod_str.strip()
                        cant = 1
                        nombre = prod_str
                        # Detectar (x3)
                        if "(x" in prod_str:
                            parts = prod_str.split("(x")
                            nombre = parts[0].strip()
                            cant = int(parts[1].replace(")", ""))
                        
                        ventas_90d[nombre] = ventas_90d.get(nombre, 0) + cant
                        historial_ventas.append({'Fecha': fecha, 'Nombre': nombre, 'Cantidad': cant})
                    except: continue

    df_historial = pd.DataFrame(historial_ventas)
    
    # 2. Merge con Inventario
    df_metrics = pd.DataFrame(list(ventas_90d.items()), columns=['Nombre', 'Ventas_90d'])
    df_full = pd.merge(df_inv, df_metrics, on='Nombre', how='left')
    df_full = normalizar_columnas(df_full) # Seguridad
    
    # 3. Métricas Financieras y Logísticas
    df_full['Ventas_90d'] = df_full['Ventas_90d'].fillna(0)
    df_full['Velocidad_Diaria'] = df_full['Ventas_90d'] / 90
    
    # Validaciones anti-error división por cero
    df_full['Costo'] = df_full['Costo'].replace(0, 0.01) 
    df_full['Precio'] = df_full['Precio'].replace(0, 0.01)
    
    df_full['Margen_Unitario'] = df_full['Precio'] - df_full['Costo']
    df_full['Margen_Pct'] = (df_full['Margen_Unitario'] / df_full['Precio']) * 100
    df_full['Valor_Inv_Costo'] = df_full['Stock'] * df_full['Costo']
    
    # GMROI (Retorno de Inversión del Margen Bruto)
    # (Margen Anualizado) / (Inversión Promedio)
    df_full['GMROI'] = np.where(
        df_full['Valor_Inv_Costo'] > 1,
        (df_full['Margen_Unitario'] * df_full['Velocidad_Diaria'] * 365) / df_full['Valor_Inv_Costo'],
        0
    )
    
    # Cobertura
    df_full['Dias_Cobertura'] = np.where(
        df_full['Velocidad_Diaria'] > 0, 
        df_full['Stock'] / df_full['Velocidad_Diaria'], 
        999
    )

    # 4. Estado y Reorden
    LEAD_TIME = 15 # Días promedio
    SAFETY_FACTOR = 0.5 # 50% extra de seguridad
    
    df_full['Punto_Reorden'] = (df_full['Velocidad_Diaria'] * LEAD_TIME) * (1 + SAFETY_FACTOR)
    df_full['Estado'] = "✅ OK"
    
    df_full.loc[df_full['Stock'] == 0, 'Estado'] = "🚨 AGOTADO"
    df_full.loc[(df_full['Stock'] > 0) & (df_full['Stock'] <= df_full['Punto_Reorden']), 'Estado'] = "⚠️ Reordenar"
    df_full.loc[df_full['Dias_Cobertura'] > 180, 'Estado'] = "🧊 Exceso/Obsoleto"
    
    return df_full, df_historial

# ==========================================
# 5. IA SIMBÓLICA: ANÁLISIS DE TENDENCIAS
# ==========================================

def motor_ia_tendencias(df_historial, df_master):
    """
    Analiza la pendiente de ventas recientes para determinar tendencias
    y genera sugerencias en lenguaje natural.
    """
    if df_historial.empty: return pd.DataFrame()

    # Agrupar ventas por semana para suavizar
    df_historial['Semana'] = df_historial['Fecha'] - pd.to_timedelta(df_historial['Fecha'].dt.dayofweek, unit='D')
    ventas_sem = df_historial.groupby(['Nombre', 'Semana'])['Cantidad'].sum().reset_index()
    
    insights = []
    
    prod_unicos = ventas_sem['Nombre'].unique()
    
    for prod in prod_unicos:
        data_prod = ventas_sem[ventas_sem['Nombre'] == prod].sort_values('Semana')
        
        # Necesitamos al menos 3 puntos de datos (3 semanas) para una tendencia
        if len(data_prod) >= 3:
            # Regresión Lineal Manual (NumPy) para evitar deps pesadas
            y = data_prod['Cantidad'].values
            x = np.arange(len(y))
            
            # Pendiente (m)
            m, b = np.polyfit(x, y, 1)
            
            # Datos maestros actuales
            info_actual = df_master[df_master['Nombre'] == prod]
            if info_actual.empty: continue
            stock_actual = info_actual.iloc[0]['Stock']
            dias_cob = info_actual.iloc[0]['Dias_Cobertura']
            
            trend_label = "Estable"
            consejo = ""
            accion = "Monitorear"
            
            # Lógica Experta (Decision Tree)
            if m > 0.5:
                trend_label = "🔥 EN AUGE"
                if dias_cob < 15:
                    consejo = f"La demanda se acelera rápidamente y tienes solo {dias_cob:.1f} días de stock. ¡Riesgo inminente de quiebre!"
                    accion = "COMPRA URGENTE"
                else:
                    consejo = "Ventas creciendo consistentemente. Buen momento para aumentar precios ligeramente o asegurar reposición."
                    accion = "Optimizar Margen"
            
            elif m < -0.5:
                trend_label = "❄️ ENFRIANDO"
                if dias_cob > 60:
                    consejo = f"Las ventas caen y tienes {dias_cob:.0f} días de stock acumulado. Considera una promoción para liberar capital."
                    accion = "Liquidar"
                else:
                    consejo = "Desaceleración normal. No recompres agresivamente hasta estabilizar."
                    accion = "Frenar Compra"
            else:
                trend_label = "➡️ ESTABLE"
                if dias_cob < 10:
                    consejo = "Demanda constante pero inventario bajo."
                    accion = "Reponer Normal"
            
            insights.append({
                'Producto': prod,
                'Tendencia': trend_label,
                'Pendiente_Score': round(m, 2),
                'IA_Advice': consejo,
                'Accion_Recomendada': accion,
                'Stock_Actual': stock_actual
            })
            
    return pd.DataFrame(insights)

# ==========================================
# 6. UI / UX PRINCIPAL
# ==========================================

def main():
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("Nexus Control")
        st.write("v.Platinum Edition")
        st.divider()
        st.info("💡 Este sistema utiliza limpieza heurística latinoamericana para corregir cifras.")
    
    # --- CARGA ---
    ws_inv, ws_ven = conectar_db()
    if not ws_inv: return

    df_inv_raw, df_ven_raw = obtener_datos(ws_inv, ws_ven)
    
    if df_inv_raw.empty:
        st.error("Error cargando inventario. Verifica las columnas en Google Sheets.")
        return

    # --- PROCESAMIENTO ---
    df_master, df_historial = procesar_cerebro_negocio(df_inv_raw, df_ven_raw)
    
    # --- HEADER: KPIS GERENCIALES ---
    st.title("Tablero de Mando Ejecutivo")
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    total_val = df_master['Valor_Inv_Costo'].sum()
    ventas_30d_proj = df_master['Velocidad_Diaria'].sum() * 30 * df_master['Precio'].mean() # Estimado grosero pero rápido
    prod_agotados = df_master[df_master['Estado'] == "🚨 AGOTADO"].shape[0]
    gmroi_global = df_master[df_master['Valor_Inv_Costo'] > 0]['GMROI'].median() # Mediana para evitar outliers
    
    kpi1.metric("Valor Inventario (Costo)", f"${total_val:,.0f}", delta="Capital Inmovilizado", delta_color="off")
    kpi2.metric("Proyección Ventas (Mes)", f"${ventas_30d_proj:,.0f}", delta="Estimado Actual")
    kpi3.metric("Productos Agotados", f"{prod_agotados}", delta="Requiere Atención", delta_color="inverse")
    kpi4.metric("Eficiencia GMROI", f"{gmroi_global:.2f}x", help="Por cada $1 invertido, recuperas X$ anualmente")

    st.markdown("---")

    # --- PESTAÑAS ---
    tab_dash, tab_trend, tab_data = st.tabs(["📊 Dashboard Estratégico", "🤖 IA Tendencias & Alertas", "📂 Datos & Auditoría"])

    # 1. DASHBOARD ESTRATÉGICO
    with tab_dash:
        col_main_1, col_main_2 = st.columns([2, 1])
        
        with col_main_1:
            st.subheader("Salud del Inventario por Categoría")
            if 'Categoria' in df_master.columns:
                fig_sun = px.sunburst(
                    df_master, 
                    path=['Categoria', 'Estado', 'Nombre'], 
                    values='Valor_Inv_Costo',
                    color='GMROI',
                    color_continuous_scale='RdYlGn',
                    midpoint=1.5,
                    title="Distribución de Capital y Rentabilidad"
                )
                fig_sun.update_layout(height=500)
                st.plotly_chart(fig_sun, use_container_width=True)
        
        with col_main_2:
            st.subheader("Top Riesgos (Exceso/Faltante)")
            riesgos = df_master[df_master['Estado'].isin(["🚨 AGOTADO", "🧊 Exceso/Obsoleto"])]
            if not riesgos.empty:
                st.dataframe(
                    riesgos[['Nombre', 'Estado', 'Stock', 'Dias_Cobertura']].sort_values('Estado'),
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.success("Inventario balanceado. Sin riesgos críticos.")
                
            st.divider()
            st.subheader("Análisis Pareto (80/20)")
            # Productos que generan el 80% del valor
            df_pareto = df_master.sort_values('Valor_Inv_Costo', ascending=False)
            df_pareto['Acumulado'] = df_pareto['Valor_Inv_Costo'].cumsum()
            df_pareto['Pct_Acumulado'] = df_pareto['Acumulado'] / total_val
            
            fig_pareto = px.line(df_pareto, x='Nombre', y='Pct_Acumulado', markers=True)
            fig_pareto.add_hline(y=0.8, line_dash="dash", line_color="red", annotation_text="Límite 80%")
            fig_pareto.update_layout(showlegend=False, xaxis_title="", yaxis_title="% Valor Acumulado")
            st.plotly_chart(fig_pareto, use_container_width=True)

    # 2. IA TENDENCIAS (LA JOYA DE LA CORONA)
    with tab_trend:
        st.subheader("🧠 Nexus AI Insights")
        st.caption("Análisis algorítmico basado en la pendiente de ventas de las últimas semanas.")
        
        if not df_historial.empty:
            df_insights = motor_ia_tendencias(df_historial, df_master)
            
            if not df_insights.empty:
                # Filtros
                filtro_accion = st.multiselect("Filtrar por Acción Recomendada:", df_insights['Accion_Recomendada'].unique())
                if filtro_accion:
                    df_insights = df_insights[df_insights['Accion_Recomendada'].isin(filtro_accion)]
                
                # Visualización de Tarjetas de Insight
                for index, row in df_insights.iterrows():
                    color_border = "#3b82f6" # Azul default
                    if "URGENTE" in row['Accion_Recomendada']: color_border = "#ef4444" # Rojo
                    elif "Liquidar" in row['Accion_Recomendada']: color_border = "#f59e0b" # Naranja
                    
                    col_a, col_b = st.columns([1, 4])
                    with col_a:
                        st.metric("Pendiente", f"{row['Pendiente_Score']}", delta=row['Tendencia'])
                    with col_b:
                        st.markdown(f"""
                        <div style="border-left: 4px solid {color_border}; padding-left: 10px;">
                            <h4 style="margin:0;">{row['Producto']}</h4>
                            <p style="font-weight:bold; color: {color_border}; margin:0;">{row['Accion_Recomendada'].upper()}</p>
                            <p style="margin-top:5px; font-style: italic;">"{row['IA_Advice']}"</p>
                            <small>Stock Actual: {row['Stock_Actual']}</small>
                        </div>
                        <hr style="margin: 10px 0;">
                        """, unsafe_allow_html=True)
                
                st.subheader("Visualización de Tendencias")
                prod_select = st.selectbox("Seleccionar Producto para ver Gráfica:", df_insights['Producto'].unique())
                
                # Gráfica avanzada con línea de tendencia
                data_prod = df_historial[df_historial['Nombre'] == prod_select].copy()
                data_prod = data_prod.sort_values('Fecha')
                
                fig_trend = px.scatter(data_prod, x='Fecha', y='Cantidad', title=f"Evolución: {prod_select}")
                # Agregar linea de tendencia
                fig_trend.update_traces(mode='lines+markers')
                st.plotly_chart(fig_trend, use_container_width=True)
                
            else:
                st.info("No hay suficientes datos históricos (mínimo 3 semanas) para generar predicciones fiables.")
        else:
            st.warning("No hay historial de ventas disponible para analizar tendencias.")

    # 3. DATOS CRUDOS Y EXPORTACIÓN
    with tab_data:
        st.subheader("Base de Datos Maestra")
        
        # Opciones de descarga
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_master.to_excel(writer, sheet_name='Master_Inventory', index=False)
            if not df_insights.empty:
                df_insights.to_excel(writer, sheet_name='IA_Insights', index=False)
            
        st.download_button(
            label="📥 Descargar Reporte Completo (Excel)",
            data=output.getvalue(),
            file_name="Nexus_Platinum_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.dataframe(df_master, use_container_width=True)

if __name__ == "__main__":
    main()
