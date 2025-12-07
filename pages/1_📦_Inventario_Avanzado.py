import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import json
import uuid
from urllib.parse import quote

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN (NEXUS PRO)
# ==========================================

st.set_page_config(
    page_title="NEXUS PRO | AI Supply Chain",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS "Glassmorphism"
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Fondo y Contenedores */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Métricas */
    div[data-testid="metric-container"] {
        background: white;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #6366f1;
    }
    
    /* Tablas */
    .stDataFrame { 
        border-radius: 12px; 
        overflow: hidden;
        border: 1px solid #e5e7eb;
    }
    
    /* Botones Principales */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    /* Títulos */
    h1, h2, h3 { color: #111827; }
    .highlight { color: #4f46e5; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE BASE DE DATOS (AUTO-REPARABLE)
# ==========================================

@st.cache_resource
def conectar_db():
    """Conexión persistente a Google Sheets."""
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta la configuración de 'google_service_account' en secrets.toml")
            return None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["general"]["SHEET_URL"])
        return sh
    except Exception as e:
        st.error(f"🔴 Error Crítico de Conexión: {e}")
        return None

def get_or_create_worksheet(sh, name, headers):
    """
    Intenta obtener una hoja. Si no existe, LA CREA automáticamente.
    Esto soluciona el error 'WorksheetNotFound'.
    """
    try:
        # Intenta encontrar la hoja (buscamos variaciones comunes de nombres)
        try:
            return sh.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            # Si es proveedores, intenta buscar con doble o (typo comun)
            if name == "Maestro_Proveedores":
                 try: return sh.worksheet("Maestro_Proveedores")
                 except: pass
            
            # Si no existe, la crea
            ws = sh.add_worksheet(title=name, rows=100, cols=20)
            ws.append_row(headers)
            return ws
    except Exception as e:
        st.error(f"Error gestionando hoja '{name}': {e}")
        return None

def cargar_datos_pro(sh):
    """Carga datos con validación de esquema."""
    
    # 1. Definir esquemas (Columnas esperadas)
    schema_inv = ['ID_Producto', 'Nombre', 'Categoria', 'Stock', 'Costo', 'Precio', 'SKU_Proveedor']
    schema_ven = ['ID_Venta', 'Fecha', 'Items', 'Total']
    schema_prov = ['Nombre_Proveedor', 'SKU_Interno', 'Costo', 'Factor_Pack', 'Email', 'Telefono']
    schema_hist = ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total', 'Estado', 'Fecha_Recepcion', 'Lead_Time_Real', 'Calificacion']

    # 2. Cargar o Crear Hojas
    ws_inv = get_or_create_worksheet(sh, "Inventario", schema_inv)
    ws_ven = get_or_create_worksheet(sh, "Ventas", schema_ven)
    ws_prov = get_or_create_worksheet(sh, "Maestro_Proveedores", schema_prov)
    ws_hist = get_or_create_worksheet(sh, "Historial_Ordenes", schema_hist)

    # 3. Convertir a DataFrames
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    df_prov = pd.DataFrame(ws_prov.get_all_records())
    df_hist = pd.DataFrame(ws_hist.get_all_records())

    # 4. Normalización Numérica (Crucial para cálculos)
    def clean_currency(x):
        if isinstance(x, str):
            return float(x.replace('$', '').replace(',', '').replace(' ', '') or 0)
        return float(x or 0)

    if not df_inv.empty:
        df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
        df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
        df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
    
    return df_inv, df_ven, df_prov, df_hist, ws_hist

# ==========================================
# 3. LÓGICA DE INTELIGENCIA DE NEGOCIO (BI)
# ==========================================

def analisis_abc(df):
    """Realiza clasificación Pareto (ABC) sobre el inventario."""
    if df.empty or 'Ventas_Valor' not in df.columns:
        df['Clasificacion_ABC'] = 'C'
        return df
    
    df = df.sort_values('Ventas_Valor', ascending=False)
    df['Acumulado'] = df['Ventas_Valor'].cumsum() / df['Ventas_Valor'].sum()
    
    def classify(x):
        if x <= 0.80: return 'A' # 80% del valor (Vitales)
        elif x <= 0.95: return 'B' # 15% del valor (Importantes)
        else: return 'C' # 5% del valor (Triviales)
        
    df['Clasificacion_ABC'] = df['Acumulado'].apply(classify)
    return df

def procesar_cerebro_nexus(df_inv, df_ven, df_prov):
    # 1. Analisis de Ventas
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
    
    # Rango: Últimos 90 días
    cutoff_90 = datetime.now() - timedelta(days=90)
    cutoff_30 = datetime.now() - timedelta(days=30)
    cutoff_60 = datetime.now() - timedelta(days=60)
    
    ven_recent = df_ven[df_ven['Fecha'] >= cutoff_90]
    
    stats_prod = {}
    
    # Desglosar items de ventas (formato: "ProdA, ProdB" o "ProdA (2)")
    # Este loop es simplificado, asume nombres separados por coma
    for _, row in ven_recent.iterrows():
        items = str(row['Items']).split(',')
        for item in items:
            nombre = item.split('(')[0].strip()
            # Contador simple (en PRO real, parsear cantidad)
            stats_prod[nombre] = stats_prod.get(nombre, 0) + 1

    df_metrics = pd.DataFrame(list(stats_prod.items()), columns=['Nombre', 'Unidades_Vendidas_90d'])
    
    # 2. Unificar con Inventario
    df_master = pd.merge(df_inv, df_metrics, on='Nombre', how='left').fillna({'Unidades_Vendidas_90d': 0})
    
    # 3. Unificar con Proveedores
    if not df_prov.empty and 'SKU_Interno' in df_prov.columns:
         # Asegurar tipos string
         df_master['ID_Producto'] = df_master['ID_Producto'].astype(str)
         df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str)
         # Merge
         df_master = pd.merge(df_master, df_prov, left_on='ID_Producto', right_on='SKU_Interno', how='left')
    else:
        df_master['Nombre_Proveedor'] = 'Genérico'
        df_master['Factor_Pack'] = 1
        df_master['Telefono'] = ''

    # 4. Cálculos Avanzados
    df_master['Ventas_Valor'] = df_master['Unidades_Vendidas_90d'] * df_master['Precio']
    df_master = analisis_abc(df_master) # Aplicar Pareto
    
    df_master['Velocidad_Diaria'] = df_master['Unidades_Vendidas_90d'] / 90
    
    # Dias de Inventario (DSI)
    df_master['Dias_Inventario'] = np.where(df_master['Velocidad_Diaria'] > 0, 
                                            df_master['Stock'] / df_master['Velocidad_Diaria'], 
                                            999) # 999 indica stock estancado
    
    # Reabastecimiento
    LEAD_TIME = 15
    SAFETY_STOCK_DAYS = {'A': 14, 'B': 7, 'C': 3} # Stock de seguridad dinámico por importancia
    
    df_master['Safety_Days'] = df_master['Clasificacion_ABC'].map(SAFETY_STOCK_DAYS).fillna(7)
    df_master['Punto_Reorden'] = df_master['Velocidad_Diaria'] * (LEAD_TIME + df_master['Safety_Days'])
    
    df_master['Estado_Stock'] = np.where(df_master['Stock'] <= df_master['Punto_Reorden'], '🚨 Pedir', '✅ OK')
    df_master['Faltante'] = (df_master['Punto_Reorden'] * 1.5 - df_master['Stock']).clip(lower=0)
    
    df_master['Factor_Pack'] = pd.to_numeric(df_master['Factor_Pack'], errors='coerce').fillna(1)
    df_master['Cajas_Sugeridas'] = np.ceil(df_master['Faltante'] / df_master['Factor_Pack'])
    df_master['Inversion_Sugerida'] = df_master['Cajas_Sugeridas'] * df_master['Factor_Pack'] * df_master['Costo']
    
    return df_master

# ==========================================
# 4. FUNCIONES DE EXPORTACIÓN Y MENSAJERÍA
# ==========================================

def generar_excel_po(df_orden):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_orden.to_excel(writer, index=False, sheet_name='Orden_Compra')
        workbook = writer.book
        worksheet = writer.sheets['Orden_Compra']
        header_fmt = workbook.add_format({'bold': True, 'fg_color': '#4f46e5', 'font_color': 'white'})
        money_fmt = workbook.add_format({'num_format': '$#,##0.00'})
        
        for col_num, value in enumerate(df_orden.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            
        worksheet.set_column('A:B', 20) # Ancho columnas
    return output.getvalue()

def generar_link_whatsapp(numero, proveedor, items_df):
    if not numero or str(numero) == 'nan' or str(numero) == '': return None
    
    numero = ''.join(filter(str.isdigit, str(numero)))
    
    resumen = ""
    for _, row in items_df.iterrows():
        resumen += f"📦 {row['Cajas_Sugeridas']:.0f} cajas de {row['Nombre']}\n"
    
    total = items_df['Inversion_Sugerida'].sum()
    
    msg = f"""*Hola {proveedor}, pedido de reposición:*
    
{resumen}
💰 *Total Estimado: ${total:,.0f}*

Quedamos atentos a confirmación. ¡Gracias!"""
    
    return f"https://wa.me/{numero}?text={quote(msg)}"

# ==========================================
# 5. UI PRINCIPAL (DASHBOARD)
# ==========================================

def main():
    sh = conectar_db()
    if not sh: return

    # Carga de Datos Resiliente
    df_inv, df_ven, df_prov, df_hist, ws_hist = cargar_datos_pro(sh)
    
    # Procesamiento
    master = procesar_cerebro_nexus(df_inv, df_ven, df_prov)

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("💠 NEXUS PRO")
        st.markdown("---")
        
        # Estado del Sistema
        alertas = master[master['Estado_Stock'] == '🚨 Pedir'].shape[0]
        if alertas > 0:
            st.error(f"⚠️ {alertas} Productos Críticos")
        else:
            st.success("✅ Inventario Saludable")
            
        st.markdown("---")
        st.caption("Sistema Inteligente v4.2")

    # --- HEADER ---
    st.markdown("## <span class='highlight'>Dashboard de Control</span>", unsafe_allow_html=True)
    
    # KPIs Top
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Valor Inventario", f"${(master['Stock']*master['Costo']).sum():,.0f}")
    k2.metric("Cashflow Requerido", f"${master['Inversion_Sugerida'].sum():,.0f}", delta="Para reabastecer", delta_color="inverse")
    
    # KPI Ventas 90d
    total_unidades = master['Unidades_Vendidas_90d'].sum()
    k3.metric("Velocidad Venta", f"{total_unidades/90:.1f} u/día")
    
    # KPI Proveedores
    pendientes = df_hist[df_hist['Estado'] == 'Pendiente'].shape[0] if not df_hist.empty else 0
    k4.metric("Órdenes Activas", pendientes)

    # --- TABS ---
    tabs = st.tabs(["📊 Análisis 360", "🚀 Centro de Compras", "📦 Recepción", "⚙️ Datos"])

    # TAB 1: ANÁLISIS 360
    with tabs[0]:
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("Distribución de Valor (Análisis ABC)")
            # Gráfico Sunburst: Categoria -> Clasificación ABC -> Producto
            if 'Categoria' in master.columns and not master.empty:
                fig = px.sunburst(master, path=['Clasificacion_ABC', 'Categoria', 'Nombre'], 
                                  values='Ventas_Valor', 
                                  color='Clasificacion_ABC',
                                  color_discrete_map={'A':'#ef4444', 'B':'#f59e0b', 'C':'#10b981'},
                                  title="¿Dónde está tu dinero? (Rojo = Productos Vitales)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Añade categorías a tus productos para ver el gráfico solar.")

        with c2:
            st.subheader("Top Agotados")
            agotados = master[master['Stock'] == 0].sort_values('Clasificacion_ABC')
            if not agotados.empty:
                st.dataframe(
                    agotados[['Nombre', 'Clasificacion_ABC', 'Velocidad_Diaria']],
                    hide_index=True,
                    column_config={
                        "Clasificacion_ABC": st.column_config.TextColumn("Importancia"),
                        "Velocidad_Diaria": st.column_config.ProgressColumn("Demanda", format="%.2f", min_value=0, max_value=master['Velocidad_Diaria'].max())
                    }
                )
            else:
                st.success("¡Sin quiebres de stock!")

    # TAB 2: COMPRAS
    with tabs[1]:
        st.subheader("🛒 Generador de Pedidos Inteligente")
        
        # Filtro de productos a pedir
        pedir_df = master[master['Cajas_Sugeridas'] > 0].copy()
        
        if pedir_df.empty:
            st.balloons()
            st.success("¡Nada que pedir hoy! Relájate.")
        else:
            col_prov, col_info = st.columns([1, 3])
            
            with col_prov:
                proveedores = pedir_df['Nombre_Proveedor'].unique()
                prov_sel = st.selectbox("Seleccionar Proveedor", proveedores)
                
                # Datos proveedor
                info_p = df_prov[df_prov['Nombre_Proveedor'] == prov_sel]
                email_p = info_p['Email'].values[0] if not info_p.empty else "N/A"
                tel_p = info_p['Telefono'].values[0] if not info_p.empty else None
                
                st.info(f"📧 {email_p}")
            
            with col_info:
                # Editor de Orden
                orden_base = pedir_df[pedir_df['Nombre_Proveedor'] == prov_sel]
                
                st.markdown(f"#### Editando Orden para **{prov_sel}**")
                
                orden_final = st.data_editor(
                    orden_base[['ID_Producto', 'Nombre', 'Stock', 'Cajas_Sugeridas', 'Costo', 'Factor_Pack']],
                    hide_index=True,
                    num_rows="dynamic",
                    column_config={
                        "Cajas_Sugeridas": st.column_config.NumberColumn("Cajas a Pedir", min_value=1, step=1),
                        "Costo": st.column_config.NumberColumn("Costo Unit", format="$%.2f"),
                        "Stock": st.column_config.NumberColumn("Stock Actual", disabled=True)
                    },
                    use_container_width=True
                )
                
                total_po = (orden_final['Cajas_Sugeridas'] * orden_final['Factor_Pack'] * orden_final['Costo']).sum()
                st.write(f"### Total Orden: :green[${total_po:,.2f}]")
                
                # ACCIONES
                st.markdown("---")
                ac1, ac2, ac3 = st.columns(3)
                
                excel_data = generar_excel_po(orden_final)
                nombre_archivo = f"PO_{prov_sel}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                
                # 1. Descargar
                ac1.download_button(
                    label="💾 Descargar Excel",
                    data=excel_data,
                    file_name=nombre_archivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
                # 2. WhatsApp
                link_wa = generar_link_whatsapp(tel_p, prov_sel, orden_final)
                if link_wa:
                    ac2.link_button("📲 Enviar WhatsApp", link_wa, type="secondary", use_container_width=True)
                else:
                    ac2.warning("Sin teléfono configurado")
                
                # 3. Confirmar (Guardar DB)
                if ac3.button("🚀 Registrar Orden", type="primary", use_container_width=True):
                    try:
                        nueva_orden = [
                            f"PO-{uuid.uuid4().hex[:6].upper()}",
                            prov_sel,
                            str(datetime.now().date()),
                            json.dumps(orden_final[['Nombre', 'Cajas_Sugeridas']].to_dict('records')),
                            total_po,
                            "Pendiente", "", "", ""
                        ]
                        ws_hist.append_row(nueva_orden)
                        st.toast("✅ Orden Registrada Exitosamente", icon="🎉")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

    # TAB 3: RECEPCIÓN
    with tabs[2]:
        st.subheader("📦 Recepción de Mercancía")
        
        if df_hist.empty:
            st.info("No hay historial de órdenes.")
        else:
            # Filtro visual
            filtro_estado = st.radio("Mostrar:", ["Pendientes", "Recibidos"], horizontal=True)
            estado_db = "Pendiente" if filtro_estado == "Pendientes" else "Recibido"
            
            view_orders = df_hist[df_hist['Estado'] == estado_db]
            
            if view_orders.empty:
                st.caption("No hay órdenes en esta categoría.")
            
            for idx, row in view_orders.iterrows():
                with st.expander(f"{row['Fecha_Orden']} | {row['Proveedor']} | ${row['Total']:,.0f}"):
                    c1, c2 = st.columns([2,1])
                    with c1:
                        st.write("**Items:**")
                        try:
                            items = json.loads(row['Items_JSON'])
                            st.table(pd.DataFrame(items))
                        except:
                            st.warning("Formato de items antiguo/inválido")
                            
                    with c2:
                        if estado_db == "Pendiente":
                            st.write("**Acciones de Recepción:**")
                            fecha_llega = st.date_input("Fecha Llegada", key=f"d_{row['ID_Orden']}")
                            calidad = st.slider("Calidad Entrega (1-5)", 1, 5, 5, key=f"s_{row['ID_Orden']}")
                            
                            if st.button("✅ Confirmar Ingreso", key=f"btn_{row['ID_Orden']}"):
                                cell = ws_hist.find(row['ID_Orden'])
                                r = cell.row
                                # Actualizar GSheets
                                ws_hist.update_cell(r, 6, "Recibido") # Estado
                                ws_hist.update_cell(r, 7, str(fecha_llega)) # Fecha
                                
                                # Calcular Lead Time
                                f_orden = datetime.strptime(str(row['Fecha_Orden']), '%Y-%m-%d').date()
                                days = (fecha_llega - f_orden).days
                                ws_hist.update_cell(r, 8, days) # Lead Time
                                ws_hist.update_cell(r, 9, calidad) # Calificacion
                                
                                st.success("Inventario actualizado (Simulado). Recarga la página.")
                        else:
                            st.write(f"🏁 Lead Time: **{row['Lead_Time_Real']} días**")
                            st.write(f"⭐ Calidad: **{row['Calificacion']}/5**")

    # TAB 4: DATOS CRUD
    with tabs[3]:
        st.info("Vista directa de la base de datos (Lectura)")
        st.dataframe(master)

if __name__ == "__main__":
    main()
