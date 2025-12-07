import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS NEXUS PRO
# ==========================================

st.set_page_config(
    page_title="Nexus Loyalty | Fidelización",
    page_icon="❤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores Corporativos
COLOR_PRIMARIO = "#187f77"      # Cian Oscuro
COLOR_SECUNDARIO = "#125e58"    # Variante Oscura
COLOR_ACENTO = "#f5a641"        # Naranja (Alertas)
COLOR_FONDO = "#f8f9fa"         # Gris Claro

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp {{ background-color: {COLOR_FONDO}; font-family: 'Inter', sans-serif; }}
    
    h1, h2, h3 {{ color: {COLOR_PRIMARIO}; font-weight: 700; }}
    
    /* Métricas tipo Tarjeta */
    div[data-testid="metric-container"] {{
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid {COLOR_ACENTO};
        transition: transform 0.2s;
    }}
    div[data-testid="metric-container"]:hover {{ transform: translateY(-5px); }}

    /* Botones */
    .stButton button[type="primary"] {{
        background: linear-gradient(135deg, {COLOR_PRIMARIO}, {COLOR_SECUNDARIO});
        border: none;
        color: white;
        font-weight: bold;
        border-radius: 8px;
    }}
    
    /* Tabs Estilizados */
    .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: white;
        border-radius: 8px 8px 0 0;
        color: {COLOR_PRIMARIO};
        font-weight: 600;
        padding: 10px 20px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COLOR_PRIMARIO} !important;
        color: white !important;
    }}
    
    /* Alertas personalizadas */
    .success-box {{
        padding: 15px;
        background-color: #d1fae5;
        color: #065f46;
        border-radius: 8px;
        border: 1px solid #34d399;
        margin-bottom: 10px;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN DE DATOS E INTELIGENCIA
# ==========================================

@st.cache_resource(ttl=600)
def conectar_datos():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración de secretos.")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Cargar Hojas Clave
        try:
            ws_cli = sh.worksheet("Clientes")
            ws_ven = sh.worksheet("Ventas")
        except:
            st.error("⚠️ Faltan las hojas 'Clientes' o 'Ventas'.")
            return None, None
            
        return ws_cli, ws_ven
    except Exception as e:
        st.error(f"Error conexión: {e}")
        return None, None

def cargar_inteligencia(ws_cli, ws_ven):
    # 1. Cargar DataFrames
    df_cli = pd.DataFrame(ws_cli.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    
    # 2. Limpieza Básica
    if not df_cli.empty:
        # Convertir Cédula a string limpio
        df_cli['Cedula'] = df_cli['Cedula'].astype(str).str.replace(r'\.0$', '', regex=True)
        # Convertir fechas
        if 'Fecha_Nacimiento' in df_cli.columns:
            df_cli['Fecha_Nacimiento'] = pd.to_datetime(df_cli['Fecha_Nacimiento'], errors='coerce')
    
    if not df_ven.empty:
        df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
        df_ven['Cedula_Cliente'] = df_ven['Cedula_Cliente'].astype(str).str.replace(r'\.0$', '', regex=True)

    # 3. CRUCE DE INTELIGENCIA (EL CEREBRO DEL SISTEMA)
    # Obtenemos la última compra de cada cliente
    last_purchase = df_ven.sort_values('Fecha').groupby('Cedula_Cliente').last().reset_index()
    last_purchase = last_purchase[['Cedula_Cliente', 'Fecha', 'Items', 'Total']]
    last_purchase.columns = ['Cedula', 'Ultima_Compra', 'Ultimo_Producto', 'Ultimo_Monto']
    
    # Unimos con datos del cliente
    master = pd.merge(df_cli, last_purchase, on='Cedula', how='left')
    
    # Cálculos de Tiempo
    hoy = pd.Timestamp.now()
    master['Dias_Sin_Compra'] = (hoy - master['Ultima_Compra']).dt.days.fillna(999)
    
    # SEGMENTACIÓN INTELIGENTE
    def clasificar_estado(dias):
        if dias <= 30: return "🟢 Activo (Reciente)"
        elif 31 <= dias <= 60: return "🟡 Oportunidad Recompra" # Momento ideal para comida
        elif 61 <= dias <= 90: return "🟠 En Riesgo"
        elif dias > 90 and dias != 999: return "🔴 Perdido"
        else: return "⚪ Nuevo / Sin Datos"
        
    master['Estado_Cliente'] = master['Dias_Sin_Compra'].apply(clasificar_estado)
    
    # DETECCIÓN DE CUMPLEAÑOS
    mes_actual = hoy.month
    master['Mes_Cumple'] = master['Fecha_Nacimiento'].dt.month
    master['Es_Cumpleanos'] = master['Mes_Cumple'] == mes_actual
    
    return master

# ==========================================
# 3. MOTORES DE ENVÍO (EMAIL & WHATSAPP)
# ==========================================

def generar_link_whatsapp(telefono, mensaje):
    if not telefono: return None
    # Limpieza de teléfono para Colombia (Asumimos +57 si no lo tiene)
    tel_str = str(telefono).replace(' ', '').replace('-', '').replace('+', '')
    if len(tel_str) == 10: tel_str = "57" + tel_str
    
    base_url = "https://wa.me/"
    encoded_msg = quote(mensaje)
    return f"{base_url}{tel_str}?text={encoded_msg}"

def enviar_email_marketing(destinatario, asunto, cuerpo_html):
    if not destinatario or "@" not in str(destinatario): 
        return False, "Correo inválido"
    
    try:
        # Credenciales desde Secrets
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]
        
        msg = MIMEMultipart()
        msg['From'] = f"Bigotes y Patitas <{sender_email}>"
        msg['To'] = destinatario
        msg['Subject'] = asunto
        
        msg.attach(MIMEText(cuerpo_html, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Enviado"
    except Exception as e:
        return False, str(e)

# ==========================================
# 4. INTERFAZ DE USUARIO
# ==========================================

def main():
    # --- HEADER ---
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("Nexus Loyalty ❤️")
        st.markdown("**Sistema de Fidelización y Recompra Inteligente**")
    with col_h2:
        st.image("https://cdn-icons-png.flaticon.com/512/2589/2589175.png", width=80) # Icono Corazón

    ws_cli, ws_ven = conectar_datos()
    if not ws_cli: return

    with st.spinner("🧠 Analizando patrones de compra..."):
        df_master = cargar_inteligencia(ws_cli, ws_ven)

    # --- KPI DASHBOARD ---
    st.markdown("### 📊 Salud de la Base de Clientes")
    k1, k2, k3, k4 = st.columns(4)
    
    total_cli = len(df_master)
    activos = len(df_master[df_master['Estado_Cliente'].str.contains("Activo")])
    recompra = len(df_master[df_master['Estado_Cliente'].str.contains("Oportunidad")])
    cumples = len(df_master[df_master['Es_Cumpleanos'] == True])
    
    k1.metric("Total Clientes", total_cli)
    k2.metric("Clientes Activos", activos, delta="Compraron < 30 días")
    k3.metric("🔥 Oportunidad Recompra", recompra, delta="Se les acaba la comida", delta_color="inverse")
    k4.metric("🎂 Cumpleaños Mes", cumples, delta="¡Enviar Regalo!")

    st.markdown("---")

    # --- PESTAÑAS DE ACCIÓN ---
    tabs = st.tabs([
        "🔄 Smart Rebuy (Recompra)", 
        "🎂 Club de Cumpleaños", 
        "🚑 Recuperación (Riesgo)", 
        "📢 Difusión General"
    ])

    # ---------------------------------------------------------
    # TAB 1: SMART REBUY (Clientes que probablemente necesitan comida)
    # ---------------------------------------------------------
    with tabs[0]:
        st.subheader("Detectamos que estos clientes necesitan comida pronto")
        st.info("💡 Estrategia: Recordatorio amable + Domicilio Gratis.")
        
        # Filtro: Clientes entre 30 y 60 días sin compra (Ciclo habitual de concentrado)
        df_rebuy = df_master[df_master['Estado_Cliente'] == "🟡 Oportunidad Recompra"].copy()
        
        if df_rebuy.empty:
            st.success("✅ ¡Todo al día! No hay clientes en ventana de recompra urgente.")
        else:
            # Selector de clientes
            df_rebuy['Seleccionar'] = False
            column_config = {
                "Nombre": st.column_config.TextColumn("Cliente", width="medium"),
                "Nombre_Mascota": st.column_config.TextColumn("Mascota", width="small"),
                "Ultimo_Producto": st.column_config.TextColumn("Última Compra", width="large"),
                "Dias_Sin_Compra": st.column_config.NumberColumn("Días sin venir", format="%d días"),
                "Seleccionar": st.column_config.CheckboxColumn("Contactar")
            }
            
            edited_rebuy = st.data_editor(
                df_rebuy[['Seleccionar', 'Nombre', 'Telefono', 'Email', 'Nombre_Mascota', 'Ultimo_Producto', 'Dias_Sin_Compra']],
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                key="editor_rebuy"
            )
            
            # Acciones Masivas
            seleccionados = edited_rebuy[edited_rebuy['Seleccionar']]
            
            if not seleccionados.empty:
                st.markdown("#### 🚀 Acciones para seleccionados")
                c_wa, c_em = st.columns(2)
                
                with c_wa:
                    if st.button("📱 Generar Links WhatsApp (Recompra)", type="primary", use_container_width=True):
                        st.markdown("##### 👇 Dale clic para abrir chat:")
                        for idx, row in seleccionados.iterrows():
                            # Mensaje Personalizado
                            prod_corto = str(row['Ultimo_Producto']).split('(')[0]
                            msg = f"Hola {row['Nombre']}! 🐾 Esperamos que {row['Nombre_Mascota']} esté genial. Notamos que ya casi es hora de refilar su {prod_corto}. 🥣 ¿Te enviamos el domicilio hoy sin costo adicional?"
                            link = generar_link_whatsapp(row['Telefono'], msg)
                            if link:
                                st.markdown(f"👉 **{row['Nombre']}:** [Enviar Mensaje]({link})")
                
                with c_em:
                    if st.button("📧 Enviar Email Recordatorio", use_container_width=True):
                        progres_bar = st.progress(0)
                        for i, (idx, row) in enumerate(seleccionados.iterrows()):
                            prod_corto = str(row['Ultimo_Producto']).split('(')[0]
                            asunto = f"🥣 ¡Hora de comer para {row['Nombre_Mascota']}!"
                            html = f"""
                            <div style='font-family: sans-serif; color: #333;'>
                                <h2 style='color: {COLOR_PRIMARIO};'>¡Hola {row['Nombre']}! 🐾</h2>
                                <p>En <b>Bigotes y Patitas</b> sabemos que lo más importante es la barriguita de {row['Nombre_Mascota']}.</p>
                                <p>Según nuestros registros, es posible que se esté acabando su: <b>{prod_corto}</b>.</p>
                                <hr>
                                <p style='font-size: 18px;'>🚚 <b>¡Pide hoy y el domicilio es GRATIS!</b></p>
                                <p>Solo responde a este correo o escríbenos al WhatsApp.</p>
                                <br>
                                <p style='font-size: 12px; color: #777;'>Con amor, el equipo de Bigotes y Patitas.</p>
                            </div>
                            """
                            if row['Email']:
                                enviar_email_marketing(row['Email'], asunto, html)
                            progres_bar.progress((i + 1) / len(seleccionados))
                        st.success("✅ Correos enviados exitosamente.")

    # ---------------------------------------------------------
    # TAB 2: CUMPLEAÑOS
    # ---------------------------------------------------------
    with tabs[1]:
        st.subheader(f"🎂 Mascotas cumpliendo años este mes ({datetime.now().strftime('%B')})")
        st.info("💡 Estrategia: Regalo emocional + Descuento exclusivo por el mes.")
        
        df_cumple = df_master[df_master['Es_Cumpleanos']].copy()
        
        if df_cumple.empty:
            st.warning("No hay cumpleañeros registrados este mes. ¡Pide las fechas de nacimiento a tus clientes!")
        else:
            df_cumple['Seleccionar'] = False
            edited_cumple = st.data_editor(
                df_cumple[['Seleccionar', 'Nombre', 'Nombre_Mascota', 'Fecha_Nacimiento', 'Telefono', 'Email']],
                hide_index=True,
                use_container_width=True,
                key="editor_cumple"
            )
            
            sel_cumple = edited_cumple[edited_cumple['Seleccionar']]
            
            if not sel_cumple.empty:
                col_btn_bd, col_dummy = st.columns([1, 2])
                if col_btn_bd.button("🎁 Enviar Felicitación + Regalo", type="primary"):
                    st.markdown("##### 🥳 Links Generados:")
                    for idx, row in sel_cumple.iterrows():
                        msg = f"¡Feliz Cumpleaños a {row['Nombre_Mascota']}! 🎂🐶🐱 En Bigotes y Patitas queremos celebrarlo. Tienes un 10% DE DESCUENTO en su torta o snacks favoritos durante todo este mes. 🎁 ¡Ven por su regalo!"
                        link = generar_link_whatsapp(row['Telefono'], msg)
                        st.markdown(f"🎉 **{row['Nombre_Mascota']} ({row['Nombre']}):** [Enviar Regalo WhatsApp]({link})")
                        
                        # Email también
                        if row['Email']:
                            html_bd = f"""
                            <div style='text-align: center; font-family: sans-serif;'>
                                <h1 style='color: {COLOR_ACENTO};'>¡Feliz Cumpleaños {row['Nombre_Mascota']}! 🎂</h1>
                                <p>Sabemos que es un mes especial.</p>
                                <div style='background-color: {COLOR_FONDO}; padding: 20px; border-radius: 10px; margin: 20px;'>
                                    <h2 style='color: {COLOR_PRIMARIO};'>🎁 TU REGALO: 10% OFF</h2>
                                    <p>Válido en snacks, juguetes y accesorios todo este mes.</p>
                                </div>
                                <p>Te esperamos en Bigotes y Patitas.</p>
                            </div>
                            """
                            enviar_email_marketing(row['Email'], f"🎁 Regalo para {row['Nombre_Mascota']}", html_bd)

    # ---------------------------------------------------------
    # TAB 3: RECUPERACIÓN (CHURN)
    # ---------------------------------------------------------
    with tabs[2]:
        st.subheader("🚑 Clientes en Riesgo (> 60 días sin compra)")
        st.error("💡 Estrategia: 'Te extrañamos' + Oferta agresiva para reactivarlos.")
        
        df_riesgo = df_master[(df_master['Estado_Cliente'] == "🟠 En Riesgo") | (df_master['Estado_Cliente'] == "🔴 Perdido")].copy()
        
        st.dataframe(df_riesgo[['Nombre', 'Telefono', 'Nombre_Mascota', 'Ultimo_Producto', 'Dias_Sin_Compra']], use_container_width=True)
        
        if not df_riesgo.empty:
            c_rec1, c_rec2 = st.columns(2)
            promo_reactivacion = c_rec1.text_input("Oferta de Reactivación", "Envío Gratis + 5% OFF")
            
            if c_rec2.button("📢 Generar Campaña de Reactivación"):
                st.markdown("##### 🥺 Mensajes de Recuperación:")
                for idx, row in df_riesgo.head(10).iterrows(): # Limitado a 10 para demo
                    msg = f"¡Hola {row['Nombre']}! Hace tiempo no vemos a {row['Nombre_Mascota']} 🥺. ¡Los extrañamos! Solo por volver, hoy tienen: {promo_reactivacion} en su pedido. 🐾 ¿Qué dices?"
                    link = generar_link_whatsapp(row['Telefono'], msg)
                    st.markdown(f"🔸 **{row['Nombre']}:** [Recuperar Cliente]({link})")

    # ---------------------------------------------------------
    # TAB 4: DIFUSIÓN GENERAL
    # ---------------------------------------------------------
    with tabs[3]:
        st.subheader("📢 Difusión a toda la base")
        st.info("Para promociones generales, nuevos productos o avisos de horario.")
        
        with st.form("form_difusion"):
            titulo_campana = st.text_input("Título de la Campaña", "¡Llegaron nuevos juguetes!")
            mensaje_wa = st.text_area("Mensaje para WhatsApp", "Hola! Pasaba a contarte que llegaron juguetes increíbles para tu peludito...")
            mensaje_email = st.text_area("Cuerpo del Correo (HTML opcional)", "<h1>Nuevos Juguetes</h1><p>Ven a conocerlos...</p>")
            
            segmento = st.selectbox("Enviar a:", ["Toda la Base de Datos", "Solo Clientes Activos"])
            
            if st.form_submit_button("🚀 Preparar Envío"):
                if segmento == "Solo Clientes Activos":
                    target = df_master[df_master['Estado_Cliente'].str.contains("Activo")]
                else:
                    target = df_master
                
                st.success(f"Objetivo: {len(target)} clientes.")
                st.warning("⚠️ El envío masivo de correos puede tomar tiempo. WhatsApp requiere clic manual por política de spam.")
                
                # Ejemplo de visualización de links
                with st.expander("Ver lista de envíos"):
                    for idx, row in target.head(20).iterrows():
                        msg_final = f"Hola {row['Nombre']}! 🐾 {mensaje_wa}"
                        link = generar_link_whatsapp(row['Telefono'], msg_final)
                        st.write(f"👉 {row['Nombre']}: [WhatsApp]({link})")

if __name__ == "__main__":
    main()
