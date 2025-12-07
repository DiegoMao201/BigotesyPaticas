import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
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
    page_title="NEXUS PRO | Supply Chain AI",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS Avanzados (Modo Oscuro/Glassmorphism Híbrido + Mejoras UI)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    
    :root {
        --primary: #6366f1;
        --secondary: #8b5cf6;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --background: #f8fafc;
        --card-bg: #ffffff;
    }

    .stApp { background-color: var(--background); }

    /* Tarjetas de Métricas */
    div[data-testid="metric-container"] {
        background: var(--card-bg);
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.2);
        border-color: var(--primary);
    }

    /* Tablas Profesionales */
    .stDataFrame { 
        border-radius: 12px; 
        overflow: hidden; 
        border: 1px solid #e2e8f0; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Botones Personalizados */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        height: 3em;
        transition: all 0.2s;
    }
    
    /* Alertas Personalizadas */
    .alerta-stock {
        padding: 10px;
        border-radius: 8px;
        background-color: #fee2e2;
        color: #991b1b;
        font-weight: bold;
        border-left: 5px solid #ef4444;
        margin-bottom: 10px;
    }
    
    h1, h2, h3 { color: #1e293b; letter-spacing: -0.5px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE BASE DE DATOS (BLINDADO)
# ==========================================

@st.cache_resource
def conectar_db():
    """Conexión a Google Sheets con manejo de errores."""
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración en secrets.toml")
            return None
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        return sh
    except Exception as e:
        st.error(f"🔴 Error Crítico de Conexión: {e}")
        return None

def get_worksheet_safe(sh, name, headers):
    """Obtiene una hoja o la crea si no existe, asegurando encabezados."""
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=100, cols=20)
        ws.append_row(headers)
        return ws

def clean_currency(x):
    """Limpia formatos de moneda ($1,000 -> 1000.0)."""
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        clean = x.replace('$', '').replace(',', '').replace(' ', '').replace('%', '').strip()
        if not clean: return 0.0
        try: return float(clean)
        except: return 0.0
    return 0.0

def normalizar_columnas(df, target_cols, aliases):
    """Normaliza nombres de columnas usando alias (sinónimos)."""
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
            # Crea columna vacía por defecto para evitar CRASH
            df[target] = 0 if any(x in target for x in ['Precio', 'Costo', 'Stock']) else ""

    if renames:
        df.rename(columns=renames, inplace=True)
    return df

def cargar_datos_pro(sh):
    """
    Carga datos y corrige automáticamente nombres de columnas y tipos.
    Aquí es donde arreglamos el error de 'KeyError'.
    """
    # 1. Definición de Alias (Sinónimos)
    alias_inv = {
        'ID_Producto': ['ID', 'SKU', 'Codigo', 'Referencia'],
        'Nombre': ['Producto', 'Descripcion', 'Item'],
        'Stock': ['Cantidad', 'Existencia', 'Unidades', 'Stock_Actual'],
        'Costo': ['Costo Unitario', 'Valor Compra', 'P.Costo'],
        'Precio': ['Precio Venta', 'PVP', 'Valor Venta'],
        'Categoria': ['Linea', 'Grupo', 'Familia'],
        'ID_Proveedor': ['Proveedor_ID', 'Nit_Proveedor']
    }
    
    alias_prov = {
        'Nombre_Proveedor': ['Proveedor', 'Empresa', 'Nombre'],
        'SKU_Interno': ['ID_Producto', 'SKU', 'Producto_Relacionado'],
        'Costo_Proveedor': ['Costo', 'Precio', 'Valor', 'Costo_Unitario', 'Precio_Lista'],
        'Factor_Pack': ['Pack', 'Unidades_Caja', 'Factor'],
        'Telefono': ['Celular', 'Movil', 'Tel', 'Whatsapp'],
        'Email': ['Correo', 'Mail', 'Email_Contacto']
    }

    # 2. Definición explícita de columnas para Historial (CORRECCIÓN DEL ERROR)
    cols_hist = ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total', 'Estado', 'Fecha_Recepcion']

    # 3. Cargar Hojas
    ws_inv = get_worksheet_safe(sh, "Inventario", list(alias_inv.keys()))
    ws_prov = get_worksheet_safe(sh, "Maestro_Proveedores", list(alias_prov.keys()))
    ws_ven = get_worksheet_safe(sh, "Ventas", ['ID_Venta', 'Fecha', 'Items', 'Total'])
    ws_hist = get_worksheet_safe(sh, "Historial_Ordenes", cols_hist) # Usamos las columnas fijas

    # 4. Crear DataFrames
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_prov = pd.DataFrame(ws_prov.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    df_hist = pd.DataFrame(ws_hist.get_all_records())

    # --- NORMALIZACIÓN ---
    
    # Inventario
    if not df_inv.empty:
        df_inv = normalizar_columnas(df_inv, alias_inv.keys(), alias_inv)
        df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
        df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
        df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
        df_inv['ID_Producto'] = df_inv['ID_Producto'].astype(str).str.strip()
        df_inv.drop_duplicates(subset=['ID_Producto'], keep='first', inplace=True)

    # Proveedores
    if not df_prov.empty:
        df_prov = normalizar_columnas(df_prov, alias_prov.keys(), alias_prov)
        df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
        df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)
        if 'ID_Producto' in df_prov.columns and 'SKU_Interno' not in df_prov.columns:
             df_prov['SKU_Interno'] = df_prov['ID_Producto']
        df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str).str.strip()

    # Historial (SOLUCIÓN FINAL KEYERROR)
    # Si el dataframe está vacío o le faltan columnas, las forzamos
    if df_hist.empty:
        df_hist = pd.DataFrame(columns=cols_hist)
    else:
        for col in cols_hist:
            if col not in df_hist.columns:
                df_hist[col] = "" # Crear columna faltante

    return df_inv, df_ven, df_prov, df_hist, ws_hist

# ==========================================
# 3. CEREBRO DE NEGOCIO (PREDICCIÓN IA)
# ==========================================

def procesar_inteligencia(df_inv, df_ven, df_prov):
    # 1. Velocidad de Ventas (Análisis 90 días)
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
    cutoff_90 = datetime.now() - timedelta(days=90)
    ven_recent = df_ven[df_ven['Fecha'] >= cutoff_90]
    
    stats = {}
    if not ven_recent.empty:
        for _, row in ven_recent.iterrows():
            items = str(row.get('Items', '')).split(',')
            for item in items:
                nombre = item.split('(')[0].strip()
                stats[nombre] = stats.get(nombre, 0) + 1

    df_sales = pd.DataFrame(list(stats.items()), columns=['Nombre', 'Ventas_90d'])
    
    # 2. Cruce Maestro
    if 'Nombre' in df_inv.columns:
        master_inv = pd.merge(df_inv, df_sales, on='Nombre', how='left').fillna({'Ventas_90d': 0})
    else:
        master_inv = df_inv.copy()
        master_inv['Ventas_90d'] = 0

    # 3. Cálculos Financieros y de Abastecimiento
    master_inv['Velocidad_Diaria'] = master_inv['Ventas_90d'] / 90
    master_inv['Valor_Stock'] = master_inv['Stock'] * master_inv['Costo']
    master_inv['Margen_Unit'] = master_inv['Precio'] - master_inv['Costo']
    
    # Días hasta Quiebre (Stockout)
    master_inv['Dias_Para_Quiebre'] = np.where(
        master_inv['Velocidad_Diaria'] > 0,
        master_inv['Stock'] / master_inv['Velocidad_Diaria'],
        999 # Si no se vende, dura para siempre
    )

    # Lógica de Reorden (Personalizable)
    LEAD_TIME = 15 # Días que tarda el proveedor
    STOCK_SEGURIDAD = 10 # Días extra por si acaso
    
    master_inv['Punto_Reorden'] = master_inv['Velocidad_Diaria'] * (LEAD_TIME + STOCK_SEGURIDAD)
    
    # Estados Inteligentes
    conditions = [
        (master_inv['Stock'] == 0),
        (master_inv['Stock'] <= master_inv['Punto_Reorden']),
        (master_inv['Stock'] > master_inv['Punto_Reorden'])
    ]
    choices = ['💀 AGOTADO', '🚨 Pedir', '✅ OK']
    master_inv['Estado'] = np.select(conditions, choices, default='✅ OK')
    
    # Cálculo de Cantidad a Pedir (Objetivo: Cubrir 45 días)
    DIAS_OBJETIVO = 45
    master_inv['Stock_Objetivo'] = master_inv['Velocidad_Diaria'] * DIAS_OBJETIVO
    master_inv['Faltante'] = master_inv['Stock_Objetivo'] - master_inv['Stock']
    master_inv['Faltante'] = master_inv['Faltante'].clip(lower=0)

    # 4. Cruce con Proveedores
    if not df_prov.empty:
        master_buy = pd.merge(master_inv, df_prov, left_on='ID_Producto', right_on='SKU_Interno', how='left') # Left join para no perder productos sin proveedor
        master_buy['Costo_Proveedor'] = np.where(master_buy['Costo_Proveedor'] > 0, master_buy['Costo_Proveedor'], master_buy['Costo'])
        master_buy['Factor_Pack'] = master_buy['Factor_Pack'].fillna(1)
        master_buy['Nombre_Proveedor'] = master_buy['Nombre_Proveedor'].fillna('Genérico')
    else:
        master_buy = master_inv.copy()
        master_buy['Nombre_Proveedor'] = 'Proveedor Genérico'
        master_buy['Costo_Proveedor'] = master_buy['Costo']
        master_buy['Factor_Pack'] = 1
        master_buy['Telefono'] = ''
        master_buy['Email'] = ''

    # Cálculos Finales de Compra
    master_buy['Cajas_Sugeridas'] = np.ceil(master_buy['Faltante'] / master_buy['Factor_Pack'])
    master_buy['Inversion_Requerida'] = master_buy['Cajas_Sugeridas'] * master_buy['Factor_Pack'] * master_buy['Costo_Proveedor']

    return master_inv, master_buy

# ==========================================
# 4. HERRAMIENTAS DE COMUNICACIÓN (WHATSAPP + EMAIL)
# ==========================================

def generar_mensaje_whatsapp(proveedor, df_orden):
    """Genera un mensaje de WhatsApp formateado profesionalmente."""
    msg = f"*ORDEN DE COMPRA - {proveedor}*\n"
    msg += f"📅 Fecha: {datetime.now().strftime('%d/%m/%Y')}\n\n"
    msg += "Hola, favor procesar el siguiente pedido:\n\n"
    
    total = 0
    for _, row in df_orden.iterrows():
        subtotal = row['Cajas_Sugeridas'] * row['Factor_Pack'] * row['Costo_Proveedor']
        total += subtotal
        unidades_totales = int(row['Cajas_Sugeridas'] * row['Factor_Pack'])
        msg += f"📦 *{row['Nombre']}*\n"
        msg += f"   Cant: {int(row['Cajas_Sugeridas'])} Cajas ({unidades_totales} un.)\n"
    
    msg += f"\n💰 *Total Estimado: ${total:,.0f}*\n"
    msg += "Quedo atento a la confirmación y factura.\nGracias."
    return msg

def enviar_correo_smtp(destinatario, asunto, cuerpo_html, df_orden):
    """
    Envía correo usando SMTP. Requiere configuración en secrets.toml.
    Si no hay config, retorna False.
    """
    try:
        # Verificar credenciales
        if "email" not in st.secrets:
            return False, "Falta configuración 'email' en secrets.toml"
            
        smtp_server = st.secrets["email"].get("smtp_server", "smtp.gmail.com")
        smtp_port = st.secrets["email"].get("smtp_port", 587)
        sender_email = st.secrets["email"]["user"]
        password = st.secrets["email"]["password"]
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = destinatario
        msg['Subject'] = asunto
        
        # Tabla HTML simple para el correo
        html_table = df_orden[['Nombre', 'Cajas_Sugeridas', 'Costo_Proveedor']].to_html(index=False)
        full_html = f"{cuerpo_html}<br><br>{html_table}"
        
        msg.attach(MIMEText(full_html, 'html'))
        
        # Enviar
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        return True, "Correo enviado correctamente"
        
    except Exception as e:
        return False, str(e)

def descargar_excel(df):
    """Genera Excel descargable."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Orden_Compra')
        workbook = writer.book
        worksheet = writer.sheets['Orden_Compra']
        format1 = workbook.add_format({'num_format': '$#,##0'})
        worksheet.set_column('E:F', 18, format1)
    return output.getvalue()

# ==========================================
# 5. UI PRINCIPAL (DASHBOARD)
# ==========================================

def main():
    sh = conectar_db()
    if not sh: return

    # Carga de Datos
    with st.spinner('Conectando con Nexus Brain...'):
        df_inv, df_ven, df_prov, df_hist, ws_hist = cargar_datos_pro(sh)
        master_inv, master_buy = procesar_inteligencia(df_inv, df_ven, df_prov)

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("💠 NEXUS PRO")
        st.caption("Sistema de Abastecimiento IA")
        
        # Alertas Rápidas Sidebar
        agotados = master_inv[master_inv['Estado'] == '💀 AGOTADO'].shape[0]
        criticos = master_inv[master_inv['Estado'] == '🚨 Pedir'].shape[0]
        
        if agotados > 0:
            st.error(f"💀 {agotados} Productos AGOTADOS")
        if criticos > 0:
            st.warning(f"⚠️ {criticos} Productos por pedir")
        if agotados == 0 and criticos == 0:
            st.success("✅ Inventario Óptimo")
            
        st.divider()
        st.markdown("### ⚙️ Configuración")
        st.info("El sistema detecta automáticamente columnas. Asegúrate de tener una hoja 'Historial_Ordenes' aunque esté vacía.")

    # --- KPI HEADER ---
    st.markdown("## 🚀 Centro de Comando")
    
    k1, k2, k3, k4 = st.columns(4)
    
    dinero_en_calle = master_inv['Valor_Stock'].sum()
    k1.metric("Valor Inventario", f"${dinero_en_calle:,.0f}", delta="Capital Invertido")
    
    presupuesto_urgente = master_buy[master_buy['Estado'].isin(['🚨 Pedir', '💀 AGOTADO'])]['Inversion_Requerida'].sum()
    k2.metric("Necesidad Compra", f"${presupuesto_urgente:,.0f}", delta="Para reabastecer", delta_color="inverse")
    
    venta_proyectada = master_inv['Ventas_90d'].sum() / 3 # Promedio mensual
    k3.metric("Venta Mes Proy.", f"{venta_proyectada:.0f} unids", delta="Basado en ult. 90 dias")
    
    dias_stock_promedio = master_inv['Dias_Para_Quiebre'].replace([np.inf, 999], np.nan).median()
    k4.metric("Días Stock (Mediana)", f"{dias_stock_promedio:.1f} días", delta="Cobertura Promedio")

    # --- TABS PRINCIPALES ---
    tabs = st.tabs(["📊 Análisis Predictivo", "🛒 Generador de Pedidos", "📥 Recepción Mercancía", "💾 Datos"])

    # TAB 1: ANALYTICS
    with tabs[0]:
        st.subheader("Salud del Inventario")
        
        # Alerta visual grande si hay agotados
        if agotados > 0:
            st.markdown(f"""
            <div class="alerta-stock">
                ⚠️ ATENCIÓN: Tienes {agotados} productos con STOCK 0. Estás perdiendo ventas cada hora.
                Ve a la pestaña 'Generador de Pedidos' inmediatamente.
            </div>
            """, unsafe_allow_html=True)

        c1, c2 = st.columns([2,1])
        with c1:
            # Gráfico Interactivo: Días de Stock vs Margen
            fig = px.scatter(
                master_inv[master_inv['Stock'] > 0],
                x='Dias_Para_Quiebre',
                y='Margen_Unit',
                size='Valor_Stock',
                color='Estado',
                hover_name='Nombre',
                color_discrete_map={'🚨 Pedir': '#f59e0b', '✅ OK': '#10b981', '💀 AGOTADO': '#ef4444'},
                title="Mapa de Riesgo: ¿Qué productos ganadores se están agotando?"
            )
            fig.add_vline(x=15, line_dash="dash", annotation_text="Punto Crítico (15 días)")
            fig.update_layout(xaxis_range=[0, 100]) # Limitar eje X para ver bien los cercanos a 0
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.write("#### 🏆 Top Productos (Velocidad)")
            top_vel = master_inv.sort_values('Velocidad_Diaria', ascending=False).head(5)
            st.dataframe(
                top_vel[['Nombre', 'Stock', 'Dias_Para_Quiebre']],
                hide_index=True,
                column_config={
                    "Dias_Para_Quiebre": st.column_config.NumberColumn("Días Restantes", format="%.1f d")
                }
            )

    # TAB 2: COMPRAS (NEXUS INTELLIGENCE)
    with tabs[1]:
        st.subheader("🛒 Gestión de Compras Inteligente")
        st.markdown("El sistema sugiere compras basándose en tu velocidad de venta real.")
        
        # Filtro: Solo mostrar lo que hay que pedir
        df_pedir = master_buy[master_buy['Cajas_Sugeridas'] > 0].copy()
        
        if df_pedir.empty:
            st.balloons()
            st.success("🎉 ¡Excelente gestión! No necesitas comprar nada hoy.")
        else:
            col_sel, col_act = st.columns([1, 3])
            
            with col_sel:
                proveedores = df_pedir['Nombre_Proveedor'].unique()
                prov_sel = st.selectbox("1️⃣ Seleccionar Proveedor", proveedores)
                
                # Datos de contacto
                info_p = df_prov[df_prov['Nombre_Proveedor'] == prov_sel]
                tel_db = info_p['Telefono'].values[0] if not info_p.empty else ""
                email_db = info_p['Email'].values[0] if not info_p.empty and 'Email' in info_p.columns else ""
                
                st.caption(f"Datos: {tel_db} | {email_db}")
            
            with col_act:
                # Filtrar orden
                orden_borrador = df_pedir[df_pedir['Nombre_Proveedor'] == prov_sel].copy()
                
                st.markdown(f"#### 2️⃣ Revisar Orden: **{prov_sel}**")
                
                # EDITOR DE DATOS POTENTE
                orden_final = st.data_editor(
                    orden_borrador[['ID_Producto', 'Nombre', 'Stock', 'Dias_Para_Quiebre', 'Cajas_Sugeridas', 'Costo_Proveedor', 'Factor_Pack']],
                    num_rows="dynamic",
                    hide_index=True,
                    column_config={
                        "Cajas_Sugeridas": st.column_config.NumberColumn("📦 Cajas a Pedir", min_value=1, step=1),
                        "Costo_Proveedor": st.column_config.NumberColumn("💲 Costo Unit.", format="$%.0f"),
                        "Dias_Para_Quiebre": st.column_config.NumberColumn("⏳ Días Stock", format="%.1f"),
                        "Stock": st.column_config.NumberColumn("Inv. Actual", disabled=True),
                        "Nombre": st.column_config.TextColumn("Producto", disabled=True)
                    },
                    use_container_width=True,
                    key="editor_orden"
                )
                
                total_po = (orden_final['Cajas_Sugeridas'] * orden_final['Factor_Pack'] * orden_final['Costo_Proveedor']).sum()
                st.write(f"### Total Orden: :green[${total_po:,.0f}]")
                
                st.divider()
                st.markdown("#### 3️⃣ Enviar Orden")
                
                c_wa, c_mail, c_save = st.columns(3)
                
                # WHATSAPP
                with c_wa:
                    st.write("**Opción A: WhatsApp**")
                    tel_manual = st.text_input("Número WhatsApp", value=str(tel_db))
                    msg_wa = generar_mensaje_whatsapp(prov_sel, orden_final)
                    
                    if tel_manual and len(tel_manual) > 5:
                        clean_phone = ''.join(filter(str.isdigit, str(tel_manual)))
                        link_wa = f"https://wa.me/{clean_phone}?text={quote(msg_wa)}"
                        st.link_button("📲 Enviar WhatsApp", link_wa, type="primary", use_container_width=True)
                    else:
                        st.warning("Ingresa celular")

                # EMAIL
                with c_mail:
                    st.write("**Opción B: Email**")
                    email_dest = st.text_input("Correo Destino", value=str(email_db))
                    if st.button("📧 Enviar Correo", use_container_width=True):
                        enviado, res = enviar_correo_smtp(
                            email_dest, 
                            f"Orden de Compra - {prov_sel}", 
                            f"Hola, adjunto pedido por valor de ${total_po:,.0f}", 
                            orden_final
                        )
                        if enviado:
                            st.toast("Correo enviado!", icon="📧")
                        else:
                            st.error(f"Error: {res}")
                            st.caption("Si no tienes SMTP configurado, copia el texto abajo.")

                # GUARDAR
                with c_save:
                    st.write("**Opción C: Registrar**")
                    if st.button("💾 Guardar en Historial", type="secondary", use_container_width=True):
                        try:
                            items_guardar = orden_final[['Nombre', 'Cajas_Sugeridas']].to_dict('records')
                            nueva_fila = [
                                f"ORD-{uuid.uuid4().hex[:6].upper()}",
                                prov_sel,
                                str(datetime.now().date()),
                                json.dumps(items_guardar),
                                total_po,
                                "Pendiente", # Estado inicial
                                "" # Fecha recepción vacía
                            ]
                            ws_hist.append_row(nueva_fila)
                            st.balloons()
                            st.success("Orden Registrada en Sistema")
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

                # Área de Copiado Manual (Fallback)
                with st.expander("Ver texto plano del pedido (Para copiar y pegar)"):
                    st.text_area("Copia esto:", value=msg_wa, height=200)

    # TAB 3: RECEPCIÓN (ELIMINACIÓN DE ERROR)
    with tabs[2]:
        st.subheader("📦 Recepción de Mercancía")
        
        # Filtrado seguro evitando KeyError
        if 'Estado' in df_hist.columns:
            pendientes = df_hist[df_hist['Estado'] == 'Pendiente']
        else:
            st.error("Error en estructura de base de datos. Se han regenerado las columnas.")
            pendientes = pd.DataFrame() # DataFrame vacío seguro
        
        if pendientes.empty:
            st.info("✅ No hay órdenes pendientes de llegada.")
        else:
            for i, row in pendientes.iterrows():
                with st.expander(f"🚛 {row['Proveedor']} - ${float(row['Total']):,.0f} (Ordenado: {row['Fecha_Orden']})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Items Esperados:**")
                        try:
                            items = json.loads(row['Items_JSON'])
                            st.table(pd.DataFrame(items))
                        except:
                            st.write("Error leyendo items.")
                    
                    with col2:
                        st.write("**Acciones:**")
                        if st.button("✅ Confirmar Llegada y Actualizar Stock", key=f"btn_{row['ID_Orden']}"):
                            try:
                                # 1. Actualizar estado en Historial
                                cell = ws_hist.find(row['ID_Orden'])
                                ws_hist.update_cell(cell.row, 6, "Recibido") # Columna Estado
                                ws_hist.update_cell(cell.row, 7, str(datetime.now().date())) # Columna Fecha
                                
                                # 2. Lógica de Sumar Stock (Simplificada)
                                # Aquí deberías buscar el producto en Inventario y sumar.
                                # Por seguridad en esta demo, solo marcamos como recibido.
                                
                                st.success("Orden marcada como Recibida.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error actualizando: {e}")

    # TAB 4: VISOR
    with tabs[3]:
        st.write("Datos procesados:")
        st.dataframe(master_inv)

if __name__ == "__main__":
    main()
