import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from datetime import datetime
from urllib.parse import quote

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS (NEXUS PRO THEME)
# ==========================================

COLOR_PRIMARIO = "#187f77"      # Cian Oscuro (Teal)
COLOR_SECUNDARIO = "#125e58"    # Variante más oscura
COLOR_ACENTO = "#f5a641"        # Naranja (Alertas)
COLOR_FONDO = "#f8f9fa"         # Gris claro
COLOR_BLANCO = "#ffffff"
COLOR_TEXTO = "#262730"

st.set_page_config(
    page_title="Nexus Loyalty | Bigotes y Patitas",
    page_icon="❤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ESTILOS CSS
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    .stApp {{
        background-color: {COLOR_FONDO};
        font-family: 'Inter', sans-serif;
    }}
    
    h1, h2, h3 {{
        color: {COLOR_PRIMARIO};
        font-weight: 700;
    }}
    
    h4, h5, h6 {{
        color: {COLOR_TEXTO};
        font-weight: 600;
    }}

    /* Tarjetas Métricas */
    div[data-testid="metric-container"] {{
        background-color: {COLOR_BLANCO};
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid {COLOR_ACENTO};
    }}
    
    div[data-testid="stExpander"] {{
        background-color: {COLOR_BLANCO};
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }}

    /* Botones */
    .stButton button[type="primary"] {{
        background: linear-gradient(135deg, {COLOR_PRIMARIO}, {COLOR_SECUNDARIO});
        border: none;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }}
    .stButton button[type="primary"]:hover {{
        box-shadow: 0 5px 15px rgba(24, 127, 119, 0.4);
        transform: translateY(-1px);
    }}

    /* Inputs y Tabs */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
        border-radius: 8px;
        border-color: #e0e0e0;
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        white-space: pre-wrap;
        background-color: {COLOR_BLANCO};
        border-radius: 8px 8px 0 0;
        color: {COLOR_TEXTO};
        font-weight: 600;
        border: 1px solid #eee;
        border-bottom: none;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COLOR_PRIMARIO};
        color: white;
        border-color: {COLOR_PRIMARIO};
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y PROCESAMIENTO
# ==========================================

@st.cache_resource(ttl=600)
def conectar_crm():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account).")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        try: ws_cli = sh.worksheet("Clientes")
        except: ws_cli = None
        
        try: ws_ven = sh.worksheet("Ventas")
        except: ws_ven = None
            
        return ws_cli, ws_ven
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None, None

def limpiar_columnas(df):
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

def procesar_inteligencia(ws_cli, ws_ven):
    # 1. Cargar Datos
    data_cli = ws_cli.get_all_records() if ws_cli else []
    data_ven = ws_ven.get_all_records() if ws_ven else []
    
    df_cli = pd.DataFrame(data_cli)
    df_ven = pd.DataFrame(data_ven)
    
    df_cli = limpiar_columnas(df_cli)
    df_ven = limpiar_columnas(df_ven)
    
    if df_cli.empty:
        return pd.DataFrame(), pd.DataFrame(), "Sin clientes"
    
    # 2. Normalización de Clientes
    if 'Cedula' not in df_cli.columns: df_cli['Cedula'] = ''
    df_cli['Cedula'] = df_cli['Cedula'].astype(str).str.replace(r'\.0$', '', regex=True)
    
    # Asegurar nombres de columnas críticas
    # Buscamos columnas que contengan 'Mascota' para normalizar
    col_mascota = next((c for c in df_cli.columns if 'mascota' in c.lower()), 'Nombre_Mascota')
    df_cli.rename(columns={col_mascota: 'Nombre_Mascota'}, inplace=True)
    if 'Nombre_Mascota' not in df_cli.columns: df_cli['Nombre_Mascota'] = 'Tu Peludito'

    # 3. Procesamiento de Ventas
    if df_ven.empty or 'Fecha' not in df_ven.columns or 'Cedula_Cliente' not in df_ven.columns:
        df_cli['Estado'] = "⚪ Nuevo"
        df_cli['Dias_Sin_Compra'] = 999
        df_cli['Ultima_Compra_Dt'] = pd.NaT
        df_cli['Ultimo_Producto'] = "N/A"
        return df_cli, df_ven, "OK (Sin Ventas)"

    df_ven['Cedula_Cliente'] = df_ven['Cedula_Cliente'].astype(str).str.replace(r'\.0$', '', regex=True)
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
    
    resumen_ventas = df_ven.groupby('Cedula_Cliente').agg({
        'Fecha': 'max',
        'Total': 'sum',
        'Items': 'last'
    }).reset_index()
    
    resumen_ventas.columns = ['Cedula', 'Ultima_Compra_Dt', 'Total_Gastado', 'Ultimo_Producto']
    
    # 4. Merge y Lógica de Negocio
    master = pd.merge(df_cli, resumen_ventas, on='Cedula', how='left')
    
    hoy = pd.Timestamp.now()
    master['Dias_Sin_Compra'] = (hoy - master['Ultima_Compra_Dt']).dt.days.fillna(999)
    
    def clasificar(dias):
        if dias <= 30: return "🟢 Activo"
        elif 31 <= dias <= 60: return "🟡 Recompra (Alerta)"
        elif 61 <= dias <= 90: return "🟠 Riesgo"
        elif dias > 90 and dias != 999: return "🔴 Perdido"
        else: return "⚪ Nuevo"
        
    master['Estado'] = master['Dias_Sin_Compra'].apply(clasificar)
    
    # 5. Detección Inteligente de Cumpleaños (Mes Actual)
    # Buscamos columnas tipo 'Fecha', 'Nacimiento', 'Cumpleaños'
    col_nac = next((c for c in master.columns if 'nacimiento' in c.lower() or 'cumple' in c.lower() or c == 'Fecha'), None)
    
    master['Cumpleaños_Mes_Actual'] = False
    
    if col_nac:
        # Convertir a datetime forzando errores a NaT
        fechas_temp = pd.to_datetime(master[col_nac], errors='coerce')
        # Extraer el mes de nacimiento
        meses_nac = fechas_temp.dt.month
        # Comparar con mes actual
        master['Cumpleaños_Mes_Actual'] = meses_nac == hoy.month
        # Guardar la fecha limpia para uso futuro
        master['Fecha_Nacimiento_Clean'] = fechas_temp

    return master, df_ven, "OK"

# ==========================================
# 3. GENERADOR DE LINKS WHATSAPP
# ==========================================

def link_whatsapp(telefono, mensaje):
    if not telefono: return None
    tel = str(telefono).replace(" ", "").replace("+", "").replace("-", "").replace(".", "").replace("(", "").replace(")", "")
    if len(tel) == 10: tel = "57" + tel
    return f"https://wa.me/{tel}?text={quote(mensaje)}"

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================

def main():
    # Sidebar
    with st.sidebar:
        st.markdown(f"<h1 style='color:{COLOR_PRIMARIO}; text-align: center;'>Nexus Loyalty</h1>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='color:{COLOR_TEXTO}; text-align: center; margin-top: -20px;'>Bigotes y Patitas 🐾</h4>", unsafe_allow_html=True)
        st.markdown("---")
        st.success(f"📅 Hoy es: {datetime.now().strftime('%d/%m/%Y')}")
        st.info("💡 Usa las pestañas para gestionar tus contactos del día.")

    # Carga
    ws_cli, ws_ven = conectar_crm()
    if not ws_cli: return
    master, df_ven, status = procesar_inteligencia(ws_cli, ws_ven)

    if master.empty:
        st.warning("⚠️ No se encontraron datos.")
        return

    # --- KPI HEADER ---
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>📊</span> Tablero de Control", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Clientes Totales", len(master))
    col2.metric("Activos (Mes)", len(master[master['Estado'] == "🟢 Activo"]))
    col3.metric("🔥 Recompra Urgente", len(master[master['Estado'] == "🟡 Recompra (Alerta)"]), delta="Prioridad Alta", delta_color="inverse")
    
    cumpleaneros = len(master[master['Cumpleaños_Mes_Actual'] == True])
    col4.metric("🎂 Cumpleaños Mes", cumpleaneros, delta="Felicitar hoy")

    st.markdown("---")

    # --- TABS DE GESTIÓN ---
    tabs = st.tabs([
        "🔄 Smart Rebuy", 
        "🎂 Cumpleaños", 
        "💁‍♀️ Servicios (Ángela)", 
        "📢 Campañas Auto", 
        "🚑 Recuperación"
    ])

    # 1. RECOMPRA INTELIGENTE
    with tabs[0]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🥣</span> Se les acabó la comida (30-60 días)", unsafe_allow_html=True)
        df_rebuy = master[master['Estado'] == "🟡 Recompra (Alerta)"].copy()
        
        if df_rebuy.empty:
            st.success("✅ Todo al día. No hay alertas de recompra.")
        else:
            # Mostrar tabla informativa
            st.dataframe(df_rebuy[['Nombre', 'Nombre_Mascota', 'Telefono', 'Ultimo_Producto', 'Dias_Sin_Compra']], use_container_width=True, hide_index=True)
            
            st.markdown("##### 🚀 Click para contactar:")
            for idx, row in df_rebuy.iterrows():
                nom = row.get('Nombre', 'Cliente')
                mascota = row.get('Nombre_Mascota', 'tu peludito')
                prod = str(row.get('Ultimo_Producto', 'su alimento')).split('(')[0]
                tel = row.get('Telefono', '')
                
                msg = f"Hola {nom}! 🐾 Esperamos que {mascota} esté genial. Notamos que ya casi es hora de refilar su {prod}. 🥣 ¿Te enviamos el domicilio hoy? Recuerda que estamos para servirte."
                link = link_whatsapp(tel, msg)
                
                if link:
                    st.markdown(f"🔸 **{mascota}** (Dueño: {nom}) → [Enviar Recordatorio]({link})")

    # 2. CUMPLEAÑOS
    with tabs[1]:
        mes_actual = datetime.now().strftime("%B")
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>🎂</span> Cumpleañeros de {mes_actual}", unsafe_allow_html=True)
        st.caption("El sistema detecta el mes de nacimiento, sin importar el año.")
        
        df_cumple = master[master['Cumpleaños_Mes_Actual'] == True].copy()
        
        if df_cumple.empty:
            st.info(f"No hay cumpleaños detectados en la base de datos para este mes.")
        else:
            st.dataframe(df_cumple[['Nombre', 'Nombre_Mascota', 'Telefono']], use_container_width=True)
            
            st.markdown("##### 🎁 Enviar Felicitación")
            descuento = st.number_input("Descuento regalo (%)", 10, 50, 10)
            
            for idx, row in df_cumple.iterrows():
                nom = row.get('Nombre', 'Cliente')
                mascota = row.get('Nombre_Mascota', 'tu peludito')
                tel = row.get('Telefono', '')
                
                msg = f"¡Feliz Cumpleaños a {mascota}! 🎂🐶 En Bigotes y Patitas queremos celebrarlo. Tienes un {descuento}% DE DESCUENTO en su regalo favorito durante todo este mes. 🎁 ¡Ven a consentirlo!"
                link = link_whatsapp(tel, msg)
                
                if link:
                    st.markdown(f"🎉 **{mascota}** ({nom}): [Enviar Regalo WhatsApp]({link})")

    # 3. SERVICIOS (RECORDATORIO ÁNGELA)
    with tabs[2]:
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>💁‍♀️</span> Recordatorio de Servicios (Soy Ángela)", unsafe_allow_html=True)
        st.caption("Mensaje institucional cálido para recordar que estamos presentes.")
        
        # Filtro opcional
        opcion_envio = st.radio("¿A quién enviar?", ["Solo Clientes Activos (VIP)", "Todos los Clientes"], horizontal=True)
        
        if opcion_envio == "Solo Clientes Activos (VIP)":
            df_serv = master[master['Estado'] == "🟢 Activo"].copy()
        else:
            df_serv = master.copy()
            
        st.write(f"**Lista de envío ({len(df_serv)} personas):**")
        
        # Iterar y generar links con el mensaje ESPECÍFICO solicitado
        with st.expander("Ver lista y enviar mensajes"):
            for idx, row in df_serv.iterrows():
                nom = row.get('Nombre', 'Vecino')
                mascota = row.get('Nombre_Mascota', 'tu mascota')
                tel = row.get('Telefono', '')
                
                # Mensaje exacto solicitado
                msg_serv = f"Hola {nom}, te saludamos de Bigotes y Patitas 🐾. Recuerda que aquí te acompañamos con el alimento de {mascota}. 🚚 Tenemos servicio a domicilio. Soy Ángela, solo escríbeme y ahí estaremos. ❤️ Bigotes y Patitas."
                
                link = link_whatsapp(tel, msg_serv)
                if link:
                    st.write(f"🚚 **{nom} & {mascota}**: [Enviar Saludo Ángela]({link})")

    # 4. CAMPAÑAS AUTOMÁTICAS
    with tabs[3]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>📢</span> Generador de Campañas Bonitas", unsafe_allow_html=True)
        
        col_c1, col_c2 = st.columns([1, 2])
        
        with col_c1:
            st.markdown("**Configuración**")
            motivo = st.text_input("Motivo de la campaña", placeholder="Ej: Llegaron Juguetes Nuevos")
            if not motivo: motivo = "saludarte y contarte novedades"
            
            filtro_camp = st.selectbox("Segmento", ["Todos", "Solo Activos", "En Riesgo"])
        
        # Lógica de filtrado
        if filtro_camp == "Solo Activos":
            target = master[master['Estado'] == "🟢 Activo"]
        elif filtro_camp == "En Riesgo":
            target = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido"])]
        else:
            target = master

        with col_c2:
            st.info(f"✨ El sistema redactará automáticamente un mensaje bonito sobre: **'{motivo}'**")
        
        st.markdown("---")
        st.markdown(f"**Destinatarios ({len(target)}):**")
        
        # Mostrar tabla simple
        st.dataframe(target[['Nombre', 'Nombre_Mascota', 'Telefono']], use_container_width=True, height=150)
        
        st.markdown("##### 🚀 Enviar Campaña Ahora:")
        
        # Generación automática de mensajes bonitos
        for idx, row in target.iterrows():
            nom = row.get('Nombre', 'Amigo')
            mascota = row.get('Nombre_Mascota', 'tu peludito')
            tel = row.get('Telefono', '')
            
            # Plantilla automática bonita
            msg_auto = f"¡Hola {nom}! 🐾 Esperamos que {mascota} esté de maravilla hoy. 🌟 Pasamos por aquí desde Bigotes y Patitas para {motivo}. ❤️ Recuerda que te queremos mucho a ti y a {mascota}. ¡Cualquier cosita estamos a un mensaje de distancia!"
            
            link = link_whatsapp(tel, msg_auto)
            if link:
                st.markdown(f"💌 **{nom}** (para {mascota}): [Enviar WhatsApp Automático]({link})")

    # 5. RECUPERACIÓN
    with tabs[4]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🚑</span> Rescate de Clientes (>60 días sin compra)", unsafe_allow_html=True)
        df_risk = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido"])].copy()
        
        if df_risk.empty:
            st.success("¡Excelente retención! No hay clientes perdidos.")
        else:
            st.dataframe(df_risk[['Nombre', 'Nombre_Mascota', 'Dias_Sin_Compra']], use_container_width=True)
            
            gancho = st.text_input("Oferta Gancho", "Envío Gratis + Snack")
            
            for idx, row in df_risk.iterrows():
                nom = row.get('Nombre', 'Cliente')
                mascota = row.get('Nombre_Mascota', 'tu mascota')
                tel = row.get('Telefono', '')
                
                msg = f"¡Hola {nom}! Hace mucho no vemos a {mascota} 🥺. ¡Los extrañamos en Bigotes y Patitas! Solo por volver, hoy tienen: {gancho}. 🐾 ¿Qué dices, se lo enviamos?"
                link = link_whatsapp(tel, msg)
                if link:
                    st.markdown(f"🎣 **Recuperar a {nom}**: [Enviar Oferta]({link})")

if __name__ == "__main__":
    main()
