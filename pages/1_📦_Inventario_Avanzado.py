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
# 1. CONFIGURACIÓN E INICIALIZACIÓN (NEXUS PRO - VERSIÓN ANIMALISTA)
# ==========================================

st.set_page_config(
    page_title="Bigotes & Paticas | Nexus System",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS (Diseño Limpio y Amigable)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    
    :root {
        --primary: #8b5cf6;
        --secondary: #ec4899;
        --success: #10b981;
        --background: #fff1f2; /* Fondo rosado muy suave */
    }

    /* Tarjetas de Métricas */
    div[data-testid="metric-container"] {
        background: #ffffff;
        padding: 20px;
        border-radius: 20px;
        border: 2px solid #fce7f3;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }

    /* Botones Bonitos */
    .stButton>button {
        border-radius: 15px;
        font-weight: 700;
        border: none;
        transition: transform 0.2s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
    }
    
    h1, h2, h3 { color: #831843; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN A DATOS (GOOGLE SHEETS)
# ==========================================

@st.cache_resource
def conectar_db():
    try:
        # Verifica conexión a Google Sheets
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
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        clean = x.replace('$', '').replace(',', '').replace(' ', '').replace('%', '').strip()
        if not clean: return 0.0
        try: return float(clean)
        except: return 0.0
    return 0.0

def normalizar_columnas(df, target_cols, aliases):
    cols_actuales = [c.lower().strip() for c in df.columns]
    renames = {}
    
    for target in target_cols:
        target_lower = target.lower()
        if target_lower in cols_actuales:
            continue
        
        # Buscar en alias
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
            df[target] = 0 if any(x in target for x in ['Precio', 'Costo', 'Stock']) else ""

    if renames:
        df.rename(columns=renames, inplace=True)
    return df

def cargar_datos_pro(sh):
    # Alias para encontrar columnas aunque tengan nombres distintos
    alias_inv = {
        'ID_Producto': ['ID', 'SKU', 'Codigo'],
        'Nombre': ['Producto', 'Descripcion', 'Item'],
        'Stock': ['Cantidad', 'Existencia', 'Unidades'],
        'Costo': ['Costo Unitario', 'Valor Compra'],
        'Precio': ['Precio Venta', 'PVP'],
        'ID_Proveedor': ['Proveedor_ID', 'Nit']
    }
    
    alias_prov = {
        'Nombre_Proveedor': ['Proveedor', 'Empresa', 'Nombre'],
        'SKU_Interno': ['ID_Producto', 'SKU'],
        'Costo_Proveedor': ['Costo', 'Precio', 'Valor'],
        'Factor_Pack': ['Pack', 'Unidades_Caja'],
        'Telefono': ['Celular', 'Movil', 'Whatsapp'],
        'Email': ['Correo', 'Mail', 'Email_Contacto']
    }

    # Columnas fijas para historial para evitar KeyError
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

    # Normalización Inventario
    if not df_inv.empty:
        df_inv = normalizar_columnas(df_inv, alias_inv.keys(), alias_inv)
        df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
        df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
        df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
        df_inv['ID_Producto'] = df_inv['ID_Producto'].astype(str).str.strip()
        df_inv.drop_duplicates(subset=['ID_Producto'], keep='first', inplace=True)

    # Normalización Proveedores
    if not df_prov.empty:
        df_prov = normalizar_columnas(df_prov, alias_prov.keys(), alias_prov)
        df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
        df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)
        if 'ID_Producto' in df_prov.columns and 'SKU_Interno' not in df_prov.columns:
             df_prov['SKU_Interno'] = df_prov['ID_Producto']
        df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str).str.strip()

    # Normalización Historial (Evitar Error Key)
    if df_hist.empty:
        df_hist = pd.DataFrame(columns=cols_hist)
    else:
        for col in cols_hist:
            if col not in df_hist.columns:
                df_hist[col] = ""

    return df_inv, df_ven, df_prov, df_hist, ws_hist

# ==========================================
# 3. LÓGICA DE NEGOCIO (PREDICCIÓN IA)
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
    
    # Días para quiebre
    master_inv['Dias_Para_Quiebre'] = np.where(
        master_inv['Velocidad_Diaria'] > 0,
        master_inv['Stock'] / master_inv['Velocidad_Diaria'],
        999
    )

    # Estado del Stock
    LEAD_TIME = 15
    master_inv['Punto_Reorden'] = master_inv['Velocidad_Diaria'] * (LEAD_TIME + 10) # +10 dias seguridad
    
    conditions = [
        (master_inv['Stock'] == 0),
        (master_inv['Stock'] <= master_inv['Punto_Reorden']),
        (master_inv['Stock'] > master_inv['Punto_Reorden'])
    ]
    choices = ['💀 AGOTADO', '🚨 Pedir', '✅ OK']
    master_inv['Estado'] = np.select(conditions, choices, default='✅ OK')
    
    # Calcular pedido
    master_inv['Stock_Objetivo'] = master_inv['Velocidad_Diaria'] * 45 # Quiero stock para 45 días
    master_inv['Faltante'] = master_inv['Stock_Objetivo'] - master_inv['Stock']
    master_inv['Faltante'] = master_inv['Faltante'].clip(lower=0)

    # Merge Proveedores
    if not df_prov.empty:
        master_buy = pd.merge(master_inv, df_prov, left_on='ID_Producto', right_on='SKU_Interno', how='left')
        master_buy['Costo_Proveedor'] = np.where(master_buy['Costo_Proveedor'] > 0, master_buy['Costo_Proveedor'], master_buy['Costo'])
        master_buy['Factor_Pack'] = master_buy['Factor_Pack'].fillna(1)
        master_buy['Nombre_Proveedor'] = master_buy['Nombre_Proveedor'].fillna('Genérico')
    else:
        master_buy = master_inv.copy()
        master_buy['Nombre_Proveedor'] = 'Proveedor Genérico'
        master_buy['Costo_Proveedor'] = master_buy['Costo']
        master_buy['Factor_Pack'] = 1
        master_buy['Email'] = ''
        master_buy['Telefono'] = ''

    master_buy['Cajas_Sugeridas'] = np.ceil(master_buy['Faltante'] / master_buy['Factor_Pack'])
    master_buy['Inversion_Requerida'] = master_buy['Cajas_Sugeridas'] * master_buy['Factor_Pack'] * master_buy['Costo_Proveedor']

    return master_inv, master_buy

# ==========================================
# 4. SISTEMA DE CORREO (AUTOMÁTICO Y BONITO)
# ==========================================

def enviar_correo_animalista(destinatario, proveedor_nombre, df_orden):
    """
    Envía un correo con diseño HTML profesional y tierno.
    Usa las credenciales 'sender_email' y 'sender_password' del TOML.
    """
    try:
        # 1. Obtener Credenciales (Aquí estaba el error, ahora corregido)
        if "email" not in st.secrets:
            return False, "Falta sección [email] en secrets.toml"
            
        smtp_server = st.secrets["email"].get("smtp_server", "smtp.gmail.com")
        smtp_port = st.secrets["email"].get("smtp_port", 587)
        # CORRECCIÓN: Usamos las claves exactas que tienes en tu secrets
        sender_email = st.secrets["email"]["sender_email"] 
        sender_password = st.secrets["email"]["sender_password"]
        
        # 2. Construir el HTML del Correo (Diseño Bigotes y Paticas)
        filas_html = ""
        total_orden = 0
        
        for _, row in df_orden.iterrows():
            subtotal = row['Cajas_Sugeridas'] * row['Factor_Pack'] * row['Costo_Proveedor']
            total_orden += subtotal
            filas_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px;">{row['Nombre']}</td>
                <td style="padding: 10px; text-align: center;">{int(row['Cajas_Sugeridas'])}</td>
                <td style="padding: 10px; text-align: right;">${subtotal:,.0f}</td>
            </tr>
            """

        cuerpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden;">
                <div style="background-color: #8b5cf6; padding: 20px; text-align: center; color: white;">
                    <h1 style="margin: 0;">🐾 Bigotes y Paticas</h1>
                    <p style="margin: 5px 0 0;">Solicitud de Pedido</p>
                </div>
                
                <div style="padding: 20px;">
                    <p>Hola <strong>{proveedor_nombre}</strong>,</p>
                    <p>Esperamos que estén teniendo un día excelente llenito de buena energía. 🐶🐱</p>
                    <p>Quisiéramos solicitar los siguientes productos para reabastecer nuestro inventario:</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                        <thead>
                            <tr style="background-color: #f3f4f6;">
                                <th style="padding: 10px; text-align: left;">Producto</th>
                                <th style="padding: 10px; text-align: center;">Cajas</th>
                                <th style="padding: 10px; text-align: right;">Subtotal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_html}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td colspan="2" style="padding: 15px; text-align: right; font-weight: bold;">TOTAL ESTIMADO:</td>
                                <td style="padding: 15px; text-align: right; font-weight: bold; color: #8b5cf6;">${total_orden:,.0f}</td>
                            </tr>
                        </tfoot>
                    </table>
                    
                    <p style="margin-top: 30px;">Quedamos atentos a la confirmación y la factura.</p>
                    <p>¡Muchas gracias!</p>
                </div>
                
                <div style="background-color: #fdf2f8; padding: 15px; text-align: center; font-size: 12px; color: #888;">
                    Enviado con amor desde <strong>Bigotes y Paticas System 🐾</strong>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 3. Configurar el Mensaje
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = destinatario
        msg['Subject'] = f"🐾 Pedido Nuevo - Bigotes y Paticas ({datetime.now().strftime('%d/%m')})"
        msg.attach(MIMEText(cuerpo_html, 'html'))
        
        # 4. Enviar
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Correo enviado exitosamente"
        
    except Exception as e:
        return False, str(e)

def generar_link_whatsapp(numero, proveedor, df_orden):
    """Genera link de WhatsApp con mensaje formateado."""
    if not numero or len(str(numero)) < 5:
        return None
        
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
        
        # Alertas
        agotados = master_inv[master_inv['Estado'] == '💀 AGOTADO'].shape[0]
        criticos = master_inv[master_inv['Estado'] == '🚨 Pedir'].shape[0]
        
        if agotados > 0:
            st.error(f"💀 {agotados} Agotados")
        if criticos > 0:
            st.warning(f"🚨 {criticos} Por pedir")
        if agotados == 0 and criticos == 0:
            st.success("✅ Todo perfecto")
            
        st.divider()
        st.info("💡 Tip: Revisa tu correo en 'Enviados' para confirmar que salieron los pedidos.")

    # --- HEADER ---
    st.title("🐾 Bigotes y Paticas | Nexus Pro")
    st.markdown("### Centro de Control de Inventario")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Valor Inventario", f"${master_inv['Valor_Stock'].sum():,.0f}")
    k2.metric("Necesidad Compra", f"${master_buy[master_buy['Cajas_Sugeridas']>0]['Inversion_Requerida'].sum():,.0f}")
    k3.metric("Productos Activos", len(master_inv))
    k4.metric("Venta Proyectada Mes", f"${master_inv['Ventas_90d'].sum()/3 * master_inv['Precio'].mean():,.0f}")

    # --- TABS ---
    tabs = st.tabs(["📊 Análisis", "🛒 Generar Pedidos", "📥 Recepción", "💾 Datos"])

    # TAB 1: ANÁLISIS
    with tabs[0]:
        st.subheader("🔍 ¿Qué está pasando con el stock?")
        
        if agotados > 0:
            st.warning(f"⚠️ Atención: Tienes {agotados} productos en CERO. Ve a la pestaña de Pedidos.")
            
        col1, col2 = st.columns([2,1])
        with col1:
            # Grafico Bonito
            fig = px.scatter(
                master_inv[master_inv['Stock']>0],
                x='Dias_Para_Quiebre',
                y='Margen_Unit',
                size='Valor_Stock',
                color='Estado',
                color_discrete_map={'💀 AGOTADO':'red', '🚨 Pedir':'orange', '✅ OK':'green'},
                hover_name='Nombre',
                title="Mapa de Salud del Inventario"
            )
            fig.add_vline(x=15, line_dash="dash", annotation_text="Punto Crítico")
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.write("🔥 **Top Más Vendidos**")
            st.dataframe(
                master_inv.sort_values('Ventas_90d', ascending=False).head(5)[['Nombre', 'Stock']],
                hide_index=True
            )

    # TAB 2: PEDIDOS (AQUÍ ESTÁ LA MAGIA DEL CORREO)
    with tabs[1]:
        st.subheader("🛒 Crear Órdenes de Compra")
        
        df_pedir = master_buy[master_buy['Cajas_Sugeridas'] > 0].copy()
        
        if df_pedir.empty:
            st.balloons()
            st.success("🎉 ¡Maravilloso! No hace falta pedir nada hoy.")
        else:
            c_izq, c_der = st.columns([1, 3])
            
            with c_izq:
                proveedores = df_pedir['Nombre_Proveedor'].unique()
                prov_sel = st.selectbox("Seleccionar Proveedor", proveedores)
                
                # Datos del proveedor
                info_p = df_prov[df_prov['Nombre_Proveedor'] == prov_sel]
                email_db = info_p['Email'].values[0] if not info_p.empty and 'Email' in info_p.columns else ""
                tel_db = info_p['Telefono'].values[0] if not info_p.empty else ""
                
                st.info(f"📧 Email: {email_db}\n📱 Tel: {tel_db}")
                
            with c_der:
                orden_borrador = df_pedir[df_pedir['Nombre_Proveedor'] == prov_sel].copy()
                
                st.markdown(f"**Editando pedido para: {prov_sel}**")
                
                orden_final = st.data_editor(
                    orden_borrador[['ID_Producto', 'Nombre', 'Stock', 'Cajas_Sugeridas', 'Costo_Proveedor', 'Factor_Pack']],
                    num_rows="dynamic",
                    hide_index=True,
                    column_config={
                        "Cajas_Sugeridas": st.column_config.NumberColumn("Cajas", min_value=1),
                        "Costo_Proveedor": st.column_config.NumberColumn("Costo", format="$%.0f"),
                        "Nombre": st.column_config.TextColumn("Producto", disabled=True),
                        "Stock": st.column_config.NumberColumn("Stock", disabled=True)
                    },
                    use_container_width=True,
                    key="editor_orden"
                )
                
                total_po = (orden_final['Cajas_Sugeridas'] * orden_final['Factor_Pack'] * orden_final['Costo_Proveedor']).sum()
                st.write(f"### Total Orden: :violet[${total_po:,.0f}]")
                
                st.divider()
                
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                # BOTÓN 1: ENVIAR CORREO AUTOMÁTICO
                with col_btn1:
                    email_dest = st.text_input("Confirmar Correo", value=str(email_db))
                    if st.button("📧 Enviar Correo Ahora", type="primary", use_container_width=True):
                        if not email_dest or "@" not in email_dest:
                            st.error("Correo inválido")
                        else:
                            with st.spinner("Enviando correo animalista... 🐾"):
                                exito, msg = enviar_correo_animalista(email_dest, prov_sel, orden_final)
                                if exito:
                                    st.success("¡Correo enviado exitosamente! 📨")
                                    st.balloons()
                                else:
                                    st.error(f"Error: {msg}")

                # BOTÓN 2: WHATSAPP
                with col_btn2:
                    tel_dest = st.text_input("Confirmar WhatsApp", value=str(tel_db))
                    link_wa = generar_link_whatsapp(tel_dest, prov_sel, orden_final)
                    if link_wa:
                        st.link_button("📲 Abrir WhatsApp", link_wa, use_container_width=True)
                    else:
                        st.warning("Falta número")

                # BOTÓN 3: GUARDAR
                with col_btn3:
                    st.write("") # Espacio
                    st.write("") 
                    if st.button("💾 Solo Guardar (Sin enviar)", use_container_width=True):
                        try:
                            items_guardar = orden_final[['Nombre', 'Cajas_Sugeridas']].to_dict('records')
                            nueva = [
                                f"ORD-{uuid.uuid4().hex[:6].upper()}",
                                prov_sel,
                                str(datetime.now().date()),
                                json.dumps(items_guardar),
                                total_po,
                                "Pendiente", ""
                            ]
                            ws_hist.append_row(nueva)
                            st.toast("Orden guardada en historial")
                        except Exception as e:
                            st.error(f"Error guardando: {e}")

    # TAB 3: RECEPCIÓN
    with tabs[2]:
        st.subheader("📦 Mercancía en Camino")
        pendientes = df_hist[df_hist['Estado'] == 'Pendiente']
        
        if pendientes.empty:
            st.info("No esperas paquetes por ahora.")
        else:
            for i, row in pendientes.iterrows():
                with st.expander(f"🚛 {row['Proveedor']} - ${float(row['Total']):,.0f}"):
                    st.write("Productos:")
                    try:
                        st.table(pd.DataFrame(json.loads(row['Items_JSON'])))
                    except:
                        st.write("Error visualizando items")
                        
                    if st.button("✅ Confirmar Llegada", key=row['ID_Orden']):
                        cell = ws_hist.find(row['ID_Orden'])
                        ws_hist.update_cell(cell.row, 6, "Recibido")
                        ws_hist.update_cell(cell.row, 7, str(datetime.now().date()))
                        st.success("¡Stock actualizado! (Simulado)")
                        st.rerun()

    # TAB 4: DATOS RAW
    with tabs[3]:
        st.dataframe(master_inv)

if __name__ == "__main__":
    main()
