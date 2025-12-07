import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta
import json
import uuid
from urllib.parse import quote
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN (NEXUS PRO)
# ==========================================

st.set_page_config(
    page_title="Bigotes & Paticas | Nexus System",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS (Diseño Limpio, Amigable y Robusto)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    
    :root {
        --primary: #8b5cf6;
        --secondary: #ec4899;
        --success: #10b981;
        --background: #fff1f2;
    }

    /* Tarjetas de Métricas */
    div[data-testid="metric-container"] {
        background: #ffffff;
        padding: 20px;
        border-radius: 20px;
        border: 2px solid #fce7f3;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(139, 92, 246, 0.1);
        border-color: #8b5cf6;
    }

    /* Botones Bonitos */
    .stButton>button {
        border-radius: 12px;
        font-weight: 700;
        border: none;
        height: 3rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Headers */
    h1, h2, h3 { color: #831843; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #fff;
        border-radius: 10px;
        padding: 0 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #fdf2f8 !important;
        color: #831843 !important;
        border: 2px solid #831843 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN A DATOS (GOOGLE SHEETS)
# ==========================================

@st.cache_resource
def conectar_db():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración de Google Sheets en secrets.toml")
            return None
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        return sh
    except Exception as e:
        st.error(f"🔴 Error de Conexión: {e}")
        return None

def get_worksheet_safe(sh, name, headers):
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=100, cols=20)
        ws.append_row(headers)
        return ws

def clean_currency(x):
    """Limpia strings de moneda y retorna float seguro."""
    if isinstance(x, (int, float)): 
        return float(x)
    if isinstance(x, str):
        # Eliminar símbolos y espacios
        clean = x.replace('$', '').replace(',', '').replace(' ', '').replace('%', '').strip()
        if not clean: 
            return 0.0
        try: 
            return float(clean)
        except: 
            return 0.0
    return 0.0

def normalizar_columnas(df, target_cols, aliases):
    cols_actuales = [c.lower().strip() for c in df.columns]
    renames = {}
    
    for target in target_cols:
        target_lower = target.lower()
        if target_lower in cols_actuales:
            continue
        
        found = False
        possible_names = aliases.get(target, [])
        for alias in possible_names:
            alias_lower = alias.lower()
            match = next((c for c in df.columns if c.lower().strip() == alias_lower), None)
            if match:
                renames[match] = target
                found = True
                break
        
        if not found:
            # Si no existe la columna, la creamos vacía o con ceros
            df[target] = 0.0 if any(x in target for x in ['Precio', 'Costo', 'Stock', 'Factor']) else ""

    if renames:
        df.rename(columns=renames, inplace=True)
    return df

def cargar_datos_pro(sh):
    # Definición exacta de alias basada en tu solicitud
    alias_inv = {
        'ID_Producto': ['ID', 'SKU', 'Codigo', 'Item Code'],
        'Nombre': ['Producto', 'Descripcion', 'Item', 'Nombre_Producto'],
        'Stock': ['Cantidad', 'Existencia', 'Unidades', 'Stock_Actual'],
        'Costo': ['Costo Unitario', 'Valor Compra', 'Costo_Promedio'],
        'Precio': ['Precio Venta', 'PVP', 'Precio_Publico'],
        'ID_Proveedor': ['Proveedor_ID', 'Nit', 'ID_Prov']
    }
    
    # Columnas exactas de Maestro_Proveedores según tu solicitud
    alias_prov = {
        'ID_Proveedor': ['ID', 'NIT', 'Identificacion'],
        'Nombre_Proveedor': ['Proveedor', 'Empresa', 'Nombre'],
        'SKU_Proveedor': ['SKU_Prov', 'Codigo_Proveedor'],
        'SKU_Interno': ['ID_Producto', 'SKU', 'Codigo_Interno'],
        'Factor_Pack': ['Pack', 'Unidades_Caja', 'Factor'],
        'Ultima_Actualizacion': ['Fecha_Act', 'Update'],
        'Email': ['Correo', 'Mail', 'Email_Contacto'],
        'Costo_Proveedor': ['Costo', 'Precio_Lista', 'Valor']
    }

    # Columnas Historial
    cols_hist = ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total', 'Estado', 'Fecha_Recepcion']

    # Cargar Hojas
    ws_inv = get_worksheet_safe(sh, "Inventario", list(alias_inv.keys()))
    ws_prov = get_worksheet_safe(sh, "Maestro_Proveedores", list(alias_prov.keys()))
    ws_ven = get_worksheet_safe(sh, "Ventas", ['ID_Venta', 'Fecha', 'Items', 'Total'])
    ws_hist = get_worksheet_safe(sh, "Historial_Ordenes", cols_hist)

    # Convertir a DataFrames
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_prov = pd.DataFrame(ws_prov.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    df_hist = pd.DataFrame(ws_hist.get_all_records())

    # --- NORMALIZACIÓN INVENTARIO ---
    if not df_inv.empty:
        df_inv = normalizar_columnas(df_inv, alias_inv.keys(), alias_inv)
        df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
        df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
        df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
        df_inv['ID_Producto'] = df_inv['ID_Producto'].astype(str).str.strip()
        df_inv.drop_duplicates(subset=['ID_Producto'], keep='first', inplace=True)

    # --- NORMALIZACIÓN PROVEEDORES ---
    if not df_prov.empty:
        df_prov = normalizar_columnas(df_prov, alias_prov.keys(), alias_prov)
        df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
        df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)
        # Asegurar enlace por SKU_Interno
        df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str).str.strip()
        df_prov['Nombre_Proveedor'] = df_prov['Nombre_Proveedor'].astype(str).str.strip()

    # --- NORMALIZACIÓN HISTORIAL (CORRECCIÓN CRÍTICA DE ERROR) ---
    if df_hist.empty:
        df_hist = pd.DataFrame(columns=cols_hist)
    else:
        # Asegurar que existan todas las columnas
        for col in cols_hist:
            if col not in df_hist.columns:
                df_hist[col] = ""
        # Limpiar la columna Total para evitar ValueError
        df_hist['Total'] = df_hist['Total'].apply(clean_currency)

    return df_inv, df_ven, df_prov, df_hist, ws_hist

# ==========================================
# 3. LÓGICA DE NEGOCIO (NEXUS AI)
# ==========================================

def procesar_inteligencia(df_inv, df_ven, df_prov):
    # Análisis Ventas (90 días)
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
    cutoff = datetime.now() - timedelta(days=90)
    ven_recent = df_ven[df_ven['Fecha'] >= cutoff]
    
    stats = {}
    if not ven_recent.empty:
        for _, row in ven_recent.iterrows():
            items = str(row.get('Items', '')).split(',')
            for item in items:
                nombre = item.split('(')[0].strip()
                stats[nombre] = stats.get(nombre, 0) + 1

    df_sales = pd.DataFrame(list(stats.items()), columns=['Nombre', 'Ventas_90d'])
    
    # Merge Inventario + Ventas
    if 'Nombre' in df_inv.columns:
        master_inv = pd.merge(df_inv, df_sales, on='Nombre', how='left').fillna({'Ventas_90d': 0})
    else:
        master_inv = df_inv.copy()
        master_inv['Ventas_90d'] = 0

    # Métricas
    master_inv['Velocidad_Diaria'] = master_inv['Ventas_90d'] / 90
    master_inv['Valor_Stock'] = master_inv['Stock'] * master_inv['Costo']
    master_inv['Margen_Unit'] = master_inv['Precio'] - master_inv['Costo']
    
    # Estado del Stock
    LEAD_TIME = 15 # Días que tarda en llegar
    master_inv['Punto_Reorden'] = master_inv['Velocidad_Diaria'] * (LEAD_TIME + 7) 
    master_inv['Dias_Para_Quiebre'] = np.where(
        master_inv['Velocidad_Diaria'] > 0,
        master_inv['Stock'] / master_inv['Velocidad_Diaria'],
        999
    )
    
    conditions = [
        (master_inv['Stock'] == 0),
        (master_inv['Stock'] <= master_inv['Punto_Reorden']),
        (master_inv['Stock'] > master_inv['Punto_Reorden'])
    ]
    choices = ['💀 AGOTADO', '🚨 Pedir', '✅ OK']
    master_inv['Estado'] = np.select(conditions, choices, default='✅ OK')
    
    # Calcular sugerencia
    master_inv['Stock_Objetivo'] = master_inv['Velocidad_Diaria'] * 45 
    master_inv['Faltante'] = master_inv['Stock_Objetivo'] - master_inv['Stock']
    master_inv['Faltante'] = master_inv['Faltante'].clip(lower=0)

    # Merge Proveedores (Cruce Avanzado con SKU_Interno)
    if not df_prov.empty:
        # Hacemos merge usando SKU_Interno de la tabla de proveedores y ID_Producto del inventario
        master_buy = pd.merge(master_inv, df_prov, left_on='ID_Producto', right_on='SKU_Interno', how='left')
        
        # Priorizar datos del proveedor si existen, sino usar los genéricos
        master_buy['Costo_Proveedor'] = np.where(master_buy['Costo_Proveedor'] > 0, master_buy['Costo_Proveedor'], master_buy['Costo'])
        master_buy['Factor_Pack'] = master_buy['Factor_Pack'].fillna(1).replace(0, 1)
        master_buy['Nombre_Proveedor'] = master_buy['Nombre_Proveedor'].fillna('Genérico')
    else:
        master_buy = master_inv.copy()
        master_buy['Nombre_Proveedor'] = 'Genérico'
        master_buy['Costo_Proveedor'] = master_buy['Costo']
        master_buy['Factor_Pack'] = 1
        master_buy['Email'] = ''
        master_buy['ID_Proveedor'] = ''

    master_buy['Cajas_Sugeridas'] = np.ceil(master_buy['Faltante'] / master_buy['Factor_Pack'])
    master_buy['Inversion_Requerida'] = master_buy['Cajas_Sugeridas'] * master_buy['Factor_Pack'] * master_buy['Costo_Proveedor']

    return master_inv, master_buy

# ==========================================
# 4. SISTEMA DE CORREO Y WHATSAPP
# ==========================================

def enviar_correo_animalista(destinatario, proveedor_nombre, df_orden):
    try:
        if "email" not in st.secrets:
            return False, "Falta sección [email] en secrets.toml"
            
        smtp_server = st.secrets["email"].get("smtp_server", "smtp.gmail.com")
        smtp_port = st.secrets["email"].get("smtp_port", 587)
        sender_email = st.secrets["email"]["sender_email"] 
        sender_password = st.secrets["email"]["sender_password"]
        
        # Construir tabla HTML
        filas_html = ""
        total_orden = 0
        
        for _, row in df_orden.iterrows():
            subtotal = row['Cajas_Sugeridas'] * row['Factor_Pack'] * row['Costo_Proveedor']
            total_orden += subtotal
            filas_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px;">{row['Nombre']} (SKU: {row['ID_Producto']})</td>
                <td style="padding: 10px; text-align: center;">{int(row['Cajas_Sugeridas'])}</td>
                <td style="padding: 10px; text-align: right;">${subtotal:,.0f}</td>
            </tr>
            """

        cuerpo_html = f"""
        <html>
        <body style="font-family: 'Helvetica', sans-serif; color: #444;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden;">
                <div style="background-color: #8b5cf6; padding: 25px; text-align: center; color: white;">
                    <h1 style="margin: 0; font-size: 24px;">🐾 Bigotes y Paticas</h1>
                    <p style="margin: 5px 0 0; opacity: 0.9;">Orden de Compra Generada</p>
                </div>
                
                <div style="padding: 30px;">
                    <p style="font-size: 16px;">Hola <strong>{proveedor_nombre}</strong>,</p>
                    <p>Esperamos que estén teniendo un día excelente. 🐶🐱</p>
                    <p>Adjunto detallamos nuestra solicitud de pedido para reabastecimiento:</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 25px; font-size: 14px;">
                        <thead>
                            <tr style="background-color: #f3f4f6; color: #666;">
                                <th style="padding: 12px; text-align: left;">Producto</th>
                                <th style="padding: 12px; text-align: center;">Cajas</th>
                                <th style="padding: 12px; text-align: right;">Subtotal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_html}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td colspan="2" style="padding: 15px; text-align: right; font-weight: bold;">TOTAL ESTIMADO:</td>
                                <td style="padding: 15px; text-align: right; font-weight: bold; color: #8b5cf6; font-size: 16px;">${total_orden:,.0f}</td>
                            </tr>
                        </tfoot>
                    </table>
                    
                    <p style="margin-top: 30px; font-size: 14px; color: #666;">Por favor confirmar disponibilidad y fecha de entrega. Quedamos atentos a la factura.</p>
                </div>
                
                <div style="background-color: #fdf2f8; padding: 15px; text-align: center; font-size: 12px; color: #db2777;">
                    Enviado desde <strong>NEXUS PRO SYSTEM 🐾</strong>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = destinatario
        msg['Subject'] = f"🐾 Pedido Nuevo - Bigotes y Paticas ({datetime.now().strftime('%d/%m')})"
        msg.attach(MIMEText(cuerpo_html, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Correo enviado exitosamente"
        
    except Exception as e:
        return False, str(e)

def generar_link_whatsapp(numero, proveedor, df_orden):
    if not numero or len(str(numero)) < 5:
        return None
    
    # Limpiar numero (quitar espacios, guiones, letras)
    clean_phone = ''.join(filter(str.isdigit, str(numero)))
    
    msg = f"👋 Hola *{proveedor}*, espero estés super bien.\n"
    msg += f"Desde *Bigotes y Paticas* 🐾 queremos hacerte el siguiente pedido:\n\n"
    
    total = 0
    for _, row in df_orden.iterrows():
        sub = row['Cajas_Sugeridas'] * row['Factor_Pack'] * row['Costo_Proveedor']
        total += sub
        msg += f"📦 {int(row['Cajas_Sugeridas'])} cj - {row['Nombre']}\n"
    
    msg += f"\n💰 *Total Aprox: ${total:,.0f}*\n"
    msg += "Quedo atento/a. ¡Gracias! 🐶"
    
    return f"https://wa.me/{clean_phone}?text={quote(msg)}"

# ==========================================
# 5. UI PRINCIPAL
# ==========================================

def main():
    sh = conectar_db()
    if not sh: return

    # Carga de Datos
    with st.spinner('🐾 Olfateando datos recientes...'):
        df_inv, df_ven, df_prov, df_hist, ws_hist = cargar_datos_pro(sh)
        master_inv, master_buy = procesar_inteligencia(df_inv, df_ven, df_prov)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🐾 Menú Bigotes")
        
        # Alertas Inteligentes
        agotados = master_inv[master_inv['Estado'] == '💀 AGOTADO'].shape[0]
        criticos = master_inv[master_inv['Estado'] == '🚨 Pedir'].shape[0]
        
        col_s1, col_s2 = st.columns(2)
        col_s1.metric("Agotados", agotados, delta_color="inverse")
        col_s2.metric("Críticos", criticos, delta_color="inverse")
        
        if agotados > 0:
            st.error("¡Atención! Hay productos en CERO.")
            
        st.divider()
        st.info("💡 **Nexus Pro Tip:**\nAhora puedes agregar productos manualmente a las órdenes aunque el sistema no los sugiera.")

    # --- HEADER ---
    st.title("🐾 Bigotes y Paticas | Nexus Pro")
    st.markdown("### Centro de Control de Inventario")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Valor Inventario", f"${master_inv['Valor_Stock'].sum():,.0f}", delta="Costo Total")
    k2.metric("Inversión Sugerida", f"${master_buy[master_buy['Cajas_Sugeridas']>0]['Inversion_Requerida'].sum():,.0f}", delta="Para estar al día", delta_color="inverse")
    k3.metric("Referencias Activas", len(master_inv), "Productos")
    k4.metric("Tasa de Venta (90d)", f"{master_inv['Ventas_90d'].sum():,.0f}", "Unidades")

    # --- TABS ---
    tabs = st.tabs(["📊 Análisis Visual", "🛒 Generar Pedidos (Nexus)", "📥 Recepción & Bodega", "💾 Base de Datos"])

    # TAB 1: ANÁLISIS
    with tabs[0]:
        st.subheader("🔍 ¿Qué está pasando con el stock?")
        
        col1, col2 = st.columns([2,1])
        with col1:
            # Grafico Dispersión Avanzado
            fig = px.scatter(
                master_inv[master_inv['Stock']>0],
                x='Dias_Para_Quiebre',
                y='Margen_Unit',
                size='Valor_Stock',
                color='Estado',
                color_discrete_map={'💀 AGOTADO':'#ef4444', '🚨 Pedir':'#f97316', '✅ OK':'#10b981'},
                hover_name='Nombre',
                hover_data=['Stock', 'Ventas_90d'],
                title="Mapa de Salud del Inventario (Días vs Margen)",
                template="plotly_white"
            )
            fig.add_vline(x=15, line_dash="dash", line_color="gray", annotation_text="Punto Crítico (15 días)")
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.write("🔥 **Top 5 Más Vendidos**")
            top_sales = master_inv.sort_values('Ventas_90d', ascending=False).head(5)
            st.dataframe(
                top_sales[['Nombre', 'Stock', 'Estado']],
                hide_index=True,
                use_container_width=True
            )
            
            st.write("🐢 **Top 5 Lento Movimiento (Con Stock)**")
            low_sales = master_inv[(master_inv['Ventas_90d'] == 0) & (master_inv['Stock'] > 5)].head(5)
            if not low_sales.empty:
                st.dataframe(low_sales[['Nombre', 'Stock']], hide_index=True)
            else:
                st.success("¡Todo se mueve!")

    # TAB 2: PEDIDOS (CORE CON MANUAL ADD)
    with tabs[1]:
        st.subheader("🛒 Crear Órdenes de Compra Inteligentes")
        
        # 1. Selección de Proveedor
        proveedores_list = sorted(df_prov['Nombre_Proveedor'].unique().tolist())
        if 'Genérico' not in proveedores_list: proveedores_list.append('Genérico')
        
        c_sel1, c_sel2 = st.columns([1, 2])
        with c_sel1:
            prov_sel = st.selectbox("👉 Selecciona un Proveedor para trabajar", proveedores_list)
        
        # 2. Filtrar Datos
        # Sugeridos Automáticos para este proveedor
        df_auto = master_buy[
            (master_buy['Cajas_Sugeridas'] > 0) & 
            (master_buy['Nombre_Proveedor'] == prov_sel)
        ].copy()
        
        # 3. Sección Manual (NUEVA CARACTERÍSTICA)
        with st.expander(f"➕ Agregar Productos Manualmente a la orden de {prov_sel}", expanded=False):
            # Buscar productos que NO estén ya en la sugerencia automática para no duplicar
            ids_auto = df_auto['ID_Producto'].tolist()
            
            # Filtramos productos asociados al proveedor O genéricos, que no estén ya en la lista auto
            # O permitimos buscar TODO el inventario si es un pedido especial
            opciones_manuales = master_buy[~master_buy['ID_Producto'].isin(ids_auto)]
            
            # Crear lista formateada para el buscador
            opciones_manuales['Label'] = opciones_manuales['Nombre'] + " | Stock: " + opciones_manuales['Stock'].astype(str)
            
            productos_manuales_sel = st.multiselect(
                "Busca productos adicionales:",
                options=opciones_manuales['ID_Producto'],
                format_func=lambda x: opciones_manuales[opciones_manuales['ID_Producto'] == x]['Label'].values[0]
            )
            
            if productos_manuales_sel:
                # Crear dataframe de manuales
                df_manual = master_buy[master_buy['ID_Producto'].isin(productos_manuales_sel)].copy()
                df_manual['Cajas_Sugeridas'] = 1 # Empezar con 1 caja por defecto
                
                # Unir Automático + Manual
                df_final_editor = pd.concat([df_auto, df_manual], ignore_index=True)
                st.info(f"Se han añadido {len(df_manual)} productos manuales a la lista.")
            else:
                df_final_editor = df_auto

        # 4. Editor de Orden
        if df_final_editor.empty:
            st.info(f"No hay sugerencias automáticas para {prov_sel} y no has seleccionado manuales.")
        else:
            # Obtener datos de contacto del proveedor seleccionado
            info_p = df_prov[df_prov['Nombre_Proveedor'] == prov_sel]
            email_db = info_p['Email'].values[0] if not info_p.empty and 'Email' in info_p.columns else ""
            tel_db = "" # Podrías mapearlo si tienes columna Telefono
            
            # Mostrar tabla editable
            st.markdown("##### 📝 Detalle de la Orden")
            orden_final = st.data_editor(
                df_final_editor[['ID_Producto', 'Nombre', 'Stock', 'Cajas_Sugeridas', 'Costo_Proveedor', 'Factor_Pack']],
                num_rows="dynamic",
                hide_index=True,
                column_config={
                    "Cajas_Sugeridas": st.column_config.NumberColumn("Cajas a Pedir", min_value=1, step=1),
                    "Costo_Proveedor": st.column_config.NumberColumn("Costo Pack", format="$%.0f"),
                    "Factor_Pack": st.column_config.NumberColumn("Und x Caja", disabled=True),
                    "Nombre": st.column_config.TextColumn("Producto", disabled=True, width="large"),
                    "Stock": st.column_config.NumberColumn("Stock Actual", disabled=True)
                },
                use_container_width=True,
                key=f"editor_{prov_sel}"
            )
            
            total_po = (orden_final['Cajas_Sugeridas'] * orden_final['Factor_Pack'] * orden_final['Costo_Proveedor']).sum()
            
            # Footer de Totales
            col_tot1, col_tot2 = st.columns([3, 1])
            with col_tot2:
                st.metric("Total Orden", f"${total_po:,.0f}")
            
            st.divider()
            
            # 5. Acciones
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                email_dest = st.text_input("📧 Correo Proveedor", value=str(email_db))
                if st.button("🚀 Enviar Pedido por Correo", type="primary", use_container_width=True):
                    if not email_dest or "@" not in email_dest:
                        st.error("Correo inválido")
                    else:
                        with st.spinner("Enviando correo NEXUS... 🐾"):
                            exito, msg = enviar_correo_animalista(email_dest, prov_sel, orden_final)
                            if exito:
                                st.success("¡Correo enviado! 📨")
                                st.balloons()
                            else:
                                st.error(f"Error: {msg}")

            with col_btn2:
                tel_dest = st.text_input("📱 WhatsApp (Opcional)", placeholder="Ej: 573001234567")
                link_wa = generar_link_whatsapp(tel_dest, prov_sel, orden_final)
                st.write("") # Spacer
                if link_wa:
                    st.link_button("💬 Abrir WhatsApp Web", link_wa, use_container_width=True)
                else:
                    st.button("💬 WhatsApp (Ingresa número)", disabled=True, use_container_width=True)

            with col_btn3:
                st.write("") 
                st.write("") 
                if st.button("💾 Guardar en Historial (Sin enviar)", use_container_width=True):
                    try:
                        # Preparar JSON ligero
                        items_guardar = orden_final[['Nombre', 'Cajas_Sugeridas', 'ID_Producto']].to_dict('records')
                        
                        nueva_fila = [
                            f"ORD-{uuid.uuid4().hex[:6].upper()}", # ID Orden
                            prov_sel,                              # Proveedor
                            str(datetime.now().date()),            # Fecha
                            json.dumps(items_guardar),             # Items
                            total_po,                              # Total
                            "Pendiente",                           # Estado
                            ""                                     # Fecha Recepcion
                        ]
                        ws_hist.append_row(nueva_fila)
                        st.success("✅ Orden guardada en Historial")
                        st.cache_data.clear() # Limpiar cache para recargar historial
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

    # TAB 3: RECEPCIÓN (CORREGIDO ERROR VALUEERROR)
    with tabs[2]:
        st.subheader("📦 Bodega: Mercancía en Camino")
        
        # Filtrar pendientes
        pendientes = df_hist[df_hist['Estado'] == 'Pendiente'].copy()
        
        if pendientes.empty:
            st.info("🌈 No hay pedidos pendientes de llegada. ¡Buen trabajo!")
        else:
            st.write(f"Tienes **{len(pendientes)}** ordenes esperando ingreso.")
            
            for index, row in pendientes.iterrows():
                # Cálculo seguro del total para mostrar en el título
                try:
                    total_show = float(row['Total'])
                except:
                    total_show = 0.0

                with st.expander(f"🚛 {row['Proveedor']} | Fecha: {row['Fecha_Orden']} | Total: ${total_show:,.0f}"):
                    c1, c2 = st.columns([3, 1])
                    
                    with c1:
                        try:
                            items_data = json.loads(row['Items_JSON'])
                            df_items_orden = pd.DataFrame(items_data)
                            st.table(df_items_orden)
                        except:
                            st.error("Error leyendo detalles de los items (JSON corrupto)")
                    
                    with c2:
                        st.write("**Acciones:**")
                        if st.button("✅ Recibir Mercancía", key=f"recibir_{row['ID_Orden']}", type="primary"):
                            try:
                                # Buscar la celda exacta en Google Sheets
                                cell = ws_hist.find(str(row['ID_Orden']))
                                if cell:
                                    # Columna 6 es Estado, Columna 7 es Fecha Recepcion
                                    ws_hist.update_cell(cell.row, 6, "Recibido")
                                    ws_hist.update_cell(cell.row, 7, str(datetime.now().date()))
                                    st.success(f"Orden {row['ID_Orden']} marcada como Recibida.")
                                    st.rerun()
                                else:
                                    st.error("No se encontró el ID en la hoja.")
                            except Exception as e:
                                st.error(f"Error actualizando hoja: {e}")

    # TAB 4: DATOS RAW
    with tabs[3]:
        st.subheader("💾 Base de Datos Maestra")
        st.markdown("Vista cruda de los datos combinados para auditoría.")
        st.dataframe(master_buy)

if __name__ == "__main__":
    main()
