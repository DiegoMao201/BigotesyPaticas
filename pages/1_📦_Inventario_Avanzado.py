import streamlit as st
import pandas as pd
import gspread
from io import BytesIO
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Inventario Avanzado & Compras",
    page_icon="📦",
    layout="wide"
)

# Estilos CSS idénticos al main para consistencia
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3 { color: #2c3e50; font-family: 'Helvetica Neue', sans-serif; }
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
    }
    .stButton button[type="primary"] {
        background: linear-gradient(90deg, #2ecc71, #27ae60);
        border: none;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN (Reutilizamos lógica para autonomía de la página) ---
@st.cache_resource(ttl=600)
def conectar_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos.")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        return sh.worksheet("Inventario"), sh.worksheet("Ventas")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None, None

def leer_df(ws):
    if ws is None: return pd.DataFrame()
    try:
        df = pd.DataFrame(ws.get_all_records())
        # Convertir numéricos
        cols_num = ['Precio', 'Stock', 'Costo'] 
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

# --- 3. LÓGICA DE NEGOCIO AVANZADA ---

def analizar_inventario_completo(df_inv, df_ven):
    """
    Realiza el cruce entre inventario y ventas históricas para determinar
    velocidad de venta y necesidades de compra.
    """
    if df_inv.empty:
        return pd.DataFrame()

    # 1. Procesar Ventas para obtener Velocidad por Producto
    # Asumimos que la columna 'Items' tiene formato "Producto A (x2), Producto B (x1)"
    ventas_detalle = []
    
    if not df_ven.empty:
        # Filtramos ventas de los últimos 30 días para calcular rotación mensual reciente
        fecha_limite = datetime.now() - timedelta(days=30)
        df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'])
        df_ven_30 = df_ven[df_ven['Fecha'] >= fecha_limite]

        for _, row in df_ven_30.iterrows():
            try:
                items_str = row['Items']
                if not items_str: continue
                
                # Separar productos
                partes = items_str.split(", ")
                for p in partes:
                    # p suele ser "Nombre (xCant)"
                    if "(x" in p:
                        nombre = p.split(" (x")[0]
                        cant_str = p.split(" (x")[1].replace(")", "")
                        cantidad = int(cant_str)
                    else:
                        nombre = p
                        cantidad = 1
                    
                    ventas_detalle.append({'Nombre': nombre, 'Cantidad_Vendida': cantidad})
            except:
                continue

    df_rotacion = pd.DataFrame(ventas_detalle)
    
    if not df_rotacion.empty:
        # Agrupar por nombre y sumar cantidad
        rotacion_total = df_rotacion.groupby('Nombre')['Cantidad_Vendida'].sum().reset_index()
        # Calcular velocidad diaria (Total vendido en 30 días / 30)
        rotacion_total['Velocidad_Diaria'] = rotacion_total['Cantidad_Vendida'] / 30
    else:
        rotacion_total = pd.DataFrame(columns=['Nombre', 'Cantidad_Vendida', 'Velocidad_Diaria'])

    # 2. Merge con Inventario
    # Hacemos merge por Nombre (Idealmente sería por ID, pero el string de items usa Nombre)
    df_full = pd.merge(df_inv, rotacion_total, on='Nombre', how='left')
    
    # Llenar valores nulos para productos sin ventas
    df_full['Velocidad_Diaria'] = df_full['Velocidad_Diaria'].fillna(0)
    df_full['Cantidad_Vendida'] = df_full['Cantidad_Vendida'].fillna(0)

    # 3. Cálculos Estratégicos
    
    # Valor del Inventario (Si no hay costo, estimamos Costo = 70% del Precio)
    if 'Costo' not in df_full.columns:
        df_full['Costo'] = df_full['Precio'] * 0.7
    
    df_full['Valor_Total_Stock'] = df_full['Stock'] * df_full['Precio']
    df_full['Costo_Total_Stock'] = df_full['Stock'] * df_full['Costo']
    
    # Días de Inventario (Cuántos días me dura lo que tengo)
    # Evitamos división por cero
    df_full['Dias_Cobertura'] = df_full.apply(
        lambda x: x['Stock'] / x['Velocidad_Diaria'] if x['Velocidad_Diaria'] > 0 else 999, axis=1
    )
    
    # Sugerencia de Compra (Target: 15 Días)
    DIAS_OBJETIVO = 15
    df_full['Stock_Necesario_15dias'] = np.ceil(df_full['Velocidad_Diaria'] * DIAS_OBJETIVO)
    
    df_full['Sugerencia_Compra'] = df_full['Stock_Necesario_15dias'] - df_full['Stock']
    df_full['Sugerencia_Compra'] = df_full['Sugerencia_Compra'].apply(lambda x: x if x > 0 else 0)
    
    # Clasificación de Urgencia
    def clasificar_urgencia(row):
        if row['Stock'] == 0 and row['Velocidad_Diaria'] > 0: return "🚨 AGOTADO (Urgente)"
        if row['Dias_Cobertura'] < 5: return "🔴 Crítico (< 5 días)"
        if row['Dias_Cobertura'] < 10: return "🟡 Bajo (< 10 días)"
        if row['Dias_Cobertura'] > 60: return "🔵 Exceso de Stock"
        return "🟢 Saludable"
        
    df_full['Estado'] = df_full.apply(clasificar_urgencia, axis=1)

    return df_full

def generar_excel_conteo(df, filtro_texto=""):
    """
    Genera un Excel profesional para auditoría física con filtros aplicados.
    """
    output = BytesIO()
    workbook = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Filtrar datos si hay texto
    if filtro_texto:
        df = df[df['Nombre'].str.contains(filtro_texto, case=False, na=False)]
    
    # Seleccionar columnas para la hoja de conteo
    cols_export = ['ID_Producto', 'Nombre', 'Categoria', 'Stock_Sistema']
    if 'Stock' in df.columns:
        df = df.rename(columns={'Stock': 'Stock_Sistema'})
    
    df_export = df[cols_export].copy() if not df.empty else pd.DataFrame(columns=cols_export)
    df_export['Conteo_Fisico'] = "" # Columna vacía para escribir
    df_export['Diferencia'] = ""
    df_export['Notas'] = ""
    
    # Escribir Excel
    sheet_name = 'Hoja de Conteo'
    df_export.to_excel(workbook, sheet_name=sheet_name, index=False)
    
    # Formateo Profesional con XlsxWriter
    worksheet = workbook.sheets[sheet_name]
    workbook_obj = workbook.book
    
    # Formatos
    header_fmt = workbook_obj.add_format({'bold': True, 'bg_color': '#2c3e50', 'font_color': 'white', 'border': 1})
    border_fmt = workbook_obj.add_format({'border': 1})
    conteo_fmt = workbook_obj.add_format({'border': 1, 'bg_color': '#fef9e7'}) # Color crema para donde se escribe
    
    # Aplicar anchos y formatos
    worksheet.set_column('A:A', 15) # ID
    worksheet.set_column('B:B', 40) # Nombre
    worksheet.set_column('C:C', 20) # Categoria
    worksheet.set_column('D:D', 15) # Stock Sistema
    worksheet.set_column('E:E', 15, conteo_fmt) # Conteo (Celda para escribir)
    worksheet.set_column('F:G', 20)
    
    # Escribir cabeceras con formato
    for col_num, value in enumerate(df_export.columns.values):
        worksheet.write(0, col_num, value, header_fmt)
        
    workbook.close()
    return output.getvalue()

# --- 4. INTERFAZ DE USUARIO ---

def main():
    st.title("📦 Centro de Control de Inventario")
    st.markdown("Análisis estratégico de stock, rotación y previsión de compras.")

    ws_inv, ws_ven = conectar_sheets()
    
    if not ws_inv:
        return

    # Cargar datos crudos
    df_inv_raw = leer_df(ws_inv)
    df_ven_raw = leer_df(ws_ven)
    
    if df_inv_raw.empty:
        st.warning("El inventario está vacío.")
        return

    # Procesar Inteligencia de Negocio
    df_analisis = analizar_inventario_completo(df_inv_raw, df_ven_raw)

    # --- TOP KPI's ---
    col1, col2, col3, col4 = st.columns(4)
    
    valor_total = df_analisis['Valor_Total_Stock'].sum()
    total_items = df_analisis['Stock'].sum()
    items_agotados = len(df_analisis[df_analisis['Stock'] <= 0])
    items_compra = len(df_analisis[df_analisis['Sugerencia_Compra'] > 0])
    
    col1.metric("Valor Inventario (PVP)", f"${valor_total:,.0f}", help="Valor total a precio de venta")
    col2.metric("Unidades en Stock", f"{total_items:,.0f}")
    col3.metric("Agotados", items_agotados, delta_color="inverse")
    col4.metric("Requieren Compra", items_compra, delta="Urgente", delta_color="inverse")

    st.markdown("---")

    # --- TABS DE NAVEGACIÓN ---
    tab_dashboard, tab_compras, tab_auditoria = st.tabs([
        "📊 Análisis de Rotación & Valor", 
        "🛒 Sugerencias de Compra (IA)", 
        "📝 Auditoría & Excel"
    ])

    # --- TAB 1: DASHBOARD ---
    with tab_dashboard:
        c_chart1, c_chart2 = st.columns([2, 1])
        
        with c_chart1:
            st.subheader("🔥 Top Productos: Mayor Rotación (30 días)")
            top_rotacion = df_analisis.sort_values(by='Cantidad_Vendida', ascending=False).head(10)
            
            fig_bar = px.bar(
                top_rotacion, 
                x='Cantidad_Vendida', 
                y='Nombre', 
                orientation='h',
                text='Cantidad_Vendida',
                color='Cantidad_Vendida',
                color_continuous_scale='Bluered'
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with c_chart2:
            st.subheader("💰 Pareto: Valor de Inventario")
            # Treemap para ver dónde está el dinero parqueado
            fig_tree = px.treemap(
                df_analisis, 
                path=['Categoria', 'Nombre'] if 'Categoria' in df_analisis.columns else ['Nombre'], 
                values='Valor_Total_Stock',
                color='Valor_Total_Stock',
                color_continuous_scale='Greens'
            )
            fig_tree.update_layout(height=400)
            st.plotly_chart(fig_tree, use_container_width=True)

    # --- TAB 2: COMPRAS SUGERIDAS ---
    with tab_compras:
        st.subheader("📅 Planificación de Compras (Cobertura 15 días)")
        st.info("Este módulo calcula cuánto necesitas comprar basándose en la velocidad de venta de los últimos 30 días para cubrir los próximos 15.")
        
        # Filtros
        filtro_estado = st.multiselect(
            "Filtrar por Estado:", 
            options=df_analisis['Estado'].unique(),
            default=["🚨 AGOTADO (Urgente)", "🔴 Crítico (< 5 días)", "🟡 Bajo (< 10 días)"]
        )
        
        df_compras = df_analisis[df_analisis['Estado'].isin(filtro_estado)].copy()
        
        # Tabla coloreada
        def color_urgencia(val):
            color = 'black'
            if "AGOTADO" in val: color = 'red'
            elif "Crítico" in val: color = 'orange'
            elif "Exceso" in val: color = 'blue'
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            df_compras[[
                'Nombre', 'Stock', 'Velocidad_Diaria', 
                'Dias_Cobertura', 'Sugerencia_Compra', 'Estado'
            ]].style.map(color_urgencia, subset=['Estado'])
              .format({
                  'Velocidad_Diaria': '{:.2f}', 
                  'Dias_Cobertura': '{:.1f} días',
                  'Sugerencia_Compra': '{:.0f} u.'
              }),
            use_container_width=True,
            height=500
        )

    # --- TAB 3: AUDITORÍA (EXCEL) ---
    with tab_auditoria:
        st.subheader("📋 Generador de Hojas de Conteo Físico")
        st.markdown("Descarga un Excel formateado para realizar inventarios físicos en bodega.")
        
        col_search, col_action = st.columns([3, 1])
        
        with col_search:
            filtro_palabra = st.text_input("🔍 Filtrar productos para el Excel (Opcional)", placeholder="Ej: Correa, Alimento, Gato...")
            
            # Previsualización
            df_preview = df_analisis.copy()
            if filtro_palabra:
                df_preview = df_preview[df_preview['Nombre'].str.contains(filtro_palabra, case=False, na=False)]
            
            st.caption(f"Se exportarán {len(df_preview)} productos.")
        
        with col_action:
            st.write("") # Espaciador
            st.write("")
            excel_data = generar_excel_conteo(df_analisis, filtro_texto=filtro_palabra)
            
            fecha_str = datetime.now().strftime("%Y-%m-%d")
            st.download_button(
                label="📥 DESCARGAR EXCEL",
                data=excel_data,
                file_name=f"Conteo_Fisico_{fecha_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
            
        with st.expander("Ver Previsualización de Datos a Exportar"):
            st.dataframe(df_preview[['ID_Producto', 'Nombre', 'Categoria', 'Stock']])

if __name__ == "__main__":
    main()
