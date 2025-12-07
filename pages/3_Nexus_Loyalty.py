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
    page_icon="🐾",
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
    
    # 5. Detección Inteligente de Cumpleaños (MEJORADO)
    # Buscamos columnas tipo 'Fecha', 'Nacimiento', 'Cumpleaños', 'Cumple'
    col_nac = next((c for c in master.columns if 'nacimiento' in c.lower() or 'cumple' in c.lower() or c == 'Fecha'), None)
    
    master['Cumpleaños_mascota'] = False
    master['Cumpleaños_mascota'] = "No encontrada" # Debug para el usuario
    
    if col_nac:
        master['Cumpleaños_mascota'] = col_nac
        # ⚠️ CORRECCIÓN CLAVE: Convertimos a string primero para manejar formatos mixtos de Google Sheets
        # Esto asegura que lea '2023-12-01' o '01/12/2023' correctamente
        master[col_nac] = master[col_nac].astype(str)
        
        fechas_temp = pd.to_datetime(master[col_nac], errors='coerce')
        
        # Extraer el mes de nacimiento
        meses_nac = fechas_temp.dt.month
        
        # Comparar estrictamente el mes de la fecha con el mes actual
        master['Cumpleaños_mascota'] = meses_nac == hoy.month
        
        # Guardar la fecha limpia
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
        
        hoy_str = datetime.now().strftime('%d/%m/%Y')
        st.success(f"📅 Hoy es: {hoy_str}")
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
    
    cumpleaneros = len(master[master['Cumpleaños_mascota'] == True])
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
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🥣</span> Alerta: Plato Vacío (30-60 días)", unsafe_allow_html=True)
        df_rebuy = master[master['Estado'] == "🟡 Recompra (Alerta)"].copy()
        
        if df_rebuy.empty:
            st.success("✅ Todo al día. No hay alertas de recompra urgentes.")
        else:
            st.dataframe(df_rebuy[['Nombre', 'Nombre_Mascota', 'Telefono', 'Ultimo_Producto', 'Dias_Sin_Compra']], use_container_width=True, hide_index=True)
            
            st.markdown("##### 🚀 Click para enviar Recordatorio Bonito:")
            for idx, row in df_rebuy.iterrows():
                nom = row.get('Nombre', 'Cliente')
                mascota = row.get('Nombre_Mascota', 'tu peludito')
                prod = str(row.get('Ultimo_Producto', 'su alimento')).split('(')[0]
                tel = row.get('Telefono', '')
                
                # Mensaje Rebuy Mejorado
                msg = f"¡Hola {nom}! 🐾 Soy el asistente virtual de Bigotes y Patitas 🤖❤. Mi radar me dice que a {mascota} se le podría estar acabando su {prod}. 🥣😟 ¡No queremos pancitas vacías! ¿Te enviamos su refil hoy mismo a casa? 🚚💨"
                link = link_whatsapp(tel, msg)
                
                if link:
                    st.markdown(f"🔸 **{mascota}** (Dueño: {nom}) → [Enviar WhatsApp Recordatorio]({link})")

    # 2. CUMPLEAÑOS (LÓGICA MEJORADA)
    with tabs[1]:
        mes_actual_nombre = datetime.now().strftime("%B") # Nombre del mes
        mes_num = datetime.now().month
        
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>🎂</span> Cumpleañeros del Mes ({mes_actual_nombre})", unsafe_allow_html=True)
        
        # Debug para el usuario si no sale nada
        col_detectada = master['Cumpleaños_mascota'].iloc[0] if not master.empty else "N/A"
        st.caption(f"ℹ️ Columna detectada en Excel: **{col_detectada}**. Buscando fechas del mes: **{mes_num}**.")
        
        df_cumple = master[master['Cumpleaños_mascota'] == True].copy()
        
        if df_cumple.empty:
            st.warning(f"⚠️ No hay cumpleañeros detectados para el mes {mes_num}. (Revisa que la fecha en el Excel sea de este mes para probar).")
        else:
            st.success(f"🎉 **¡SÍ! Tenemos {len(df_cumple)} cumpleañeros listos para celebrar:**")
            st.dataframe(df_cumple[['Nombre', 'Nombre_Mascota', 'Telefono']], use_container_width=True)
            
            st.markdown("---")
            st.markdown("##### 🎁 Configura tu Promo de Cumpleaños:")
            
            # Input libre para definir la promo
            promo_text = st.text_input("¿Qué regalo les daremos hoy?", "un 15% DE DESCUENTO en su snack favorito")
            
            st.markdown("##### 💌 Enviar Felicitación:")
            for idx, row in df_cumple.iterrows():
                nom = row.get('Nombre', 'Cliente')
                mascota = row.get('Nombre_Mascota', 'tu peludito')
                tel = row.get('Telefono', '')
                
                # Mensaje Cumpleaños Mejorado y Personalizable
                msg = f"¡🎉 GUAU! ¡MIAU! 🎈 ¡Sabemos que {mascota} cumple años este mes! 🎂👑 En Bigotes y Patitas queremos celebrarlo a lo grande. ✨ Regalo especial: Tienes {promo_text} para consentir al rey/reina de la casa. 🎁🥳 ¡Vengan pronto por su regalo!"
                link = link_whatsapp(tel, msg)
                
                if link:
                    st.markdown(f"🎉 **{mascota}** ({nom}): [Enviar Regalo WhatsApp]({link})")

    # 3. SERVICIOS (RECORDATORIO ÁNGELA - INACTIVOS)
    with tabs[2]:
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>💁‍♀️</span> Mensajes de Ángela (Recuperar Relación)", unsafe_allow_html=True)
        st.markdown("**Objetivo:** Contactar clientes inactivos con un mensaje cálido y humano.")
        
        # Filtro automático para clientes inactivos (Riesgo o Perdidos)
        df_angela = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido", "⚪ Nuevo"])].copy()
        
        st.write(f"**Lista de envío ({len(df_angela)} personas que extrañamos):**")
        
        with st.expander("Ver lista detallada"):
            st.dataframe(df_angela[['Nombre', 'Nombre_Mascota', 'Estado', 'Dias_Sin_Compra']], use_container_width=True)

        st.markdown("##### 💌 Enviar Saludo Cálido de Ángela:")
        
        for idx, row in df_angela.iterrows():
            nom = row.get('Nombre', 'Vecino')
            mascota = row.get('Nombre_Mascota', 'tu mascota')
            tel = row.get('Telefono', '')
            
            # Mensaje Bonito/Animalista solicitado
            msg_serv = f"¡Hola {nom}! 🌈 Hace tiempo no vemos la colita feliz de {mascota} y los extrañamos mucho en Bigotes y Patitas 🥺🐾. Soy Ángela 👋. Solo pasaba a saludarte y recordarte que aquí seguimos con el corazón abierto para lo que necesiten. ❤️ ¿Cómo han estado? ¡Nos encantaría saber de ustedes! ✨🚚"
            
            link = link_whatsapp(tel, msg_serv)
            if link:
                st.write(f"💕 **{nom} & {mascota}**: [Enviar Saludo Ángela]({link})")

    # 4. CAMPAÑAS AUTOMÁTICAS
    with tabs[3]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>📢</span> Creador de Campañas Bonitas", unsafe_allow_html=True)
        
        col_c1, col_c2 = st.columns([1, 2])
        
        with col_c1:
            st.markdown("**Configuración**")
            motivo = st.text_input("Motivo (Ej: llegaron juguetes)", placeholder="Ej: Nuevos collares luminosos")
            if not motivo: motivo = "contarte novedades increíbles"
            
            filtro_camp = st.selectbox("¿A quién le escribimos?", ["Todos mis Clientes", "Solo Activos (VIP)", "Clientes Inactivos"])
        
        # Lógica de filtrado
        if filtro_camp == "Solo Activos (VIP)":
            target = master[master['Estado'] == "🟢 Activo"]
        elif filtro_camp == "Clientes Inactivos":
            target = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido"])]
        else:
            target = master

        with col_c2:
            st.info(f"✨ El sistema redactará un mensaje lleno de amor sobre: **'{motivo}'** para {len(target)} personas.")
        
        st.markdown("---")
        
        # Generación automática de mensajes bonitos
        for idx, row in target.iterrows():
            nom = row.get('Nombre', 'Amigo')
            mascota = row.get('Nombre_Mascota', 'tu peludito')
            tel = row.get('Telefono', '')
            
            # Plantilla automática bonita
            msg_auto = f"¡Hola {nom}! 🐾 Esperamos que {mascota} esté moviendo la colita de felicidad hoy. 🌟 Pasamos por aquí desde Bigotes y Patitas para {motivo}. 😍✨ Recuerda que amamos consentir a {mascota}. ¡Cualquier duda estamos a un ladrido de distancia! 🐕❤️"
            
            link = link_whatsapp(tel, msg_auto)
            if link:
                st.markdown(f"💌 **{nom}**: [Enviar Campaña]({link})")

    # 5. RECUPERACIÓN (OFERTA DIRECTA)
    with tabs[4]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🚑</span> Rescate con Oferta (>60 días)", unsafe_allow_html=True)
        df_risk = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido"])].copy()
        
        if df_risk.empty:
            st.success("¡Excelente! No tienes clientes perdidos.")
        else:
            st.write(f"Detectamos {len(df_risk)} clientes que necesitan un empujoncito.")
            
            gancho = st.text_input("Oferta Gancho para que vuelvan:", "Envío Gratis + una Sorpresa 🎁")
            
            for idx, row in df_risk.iterrows():
                nom = row.get('Nombre', 'Cliente')
                mascota = row.get('Nombre_Mascota', 'tu mascota')
                tel = row.get('Telefono', '')
                
                # Mensaje de Recuperación Bonito pero Directo
                msg = f"¡Hola {nom}! 🐾 Notamos que hace mucho no consentimos a {mascota} 🥺 y nos duele el corazón. ¡Queremos que vuelvan a la familia Bigotes y Patitas! ❤ Solo por responder este mensaje hoy, tienen: {gancho}. 😲🐾 ¿Qué dices? ¿Se lo enviamos ya mismo? 🚚💨"
                link = link_whatsapp(tel, msg)
                
                if link:
                    st.markdown(f"🎣 **Recuperar a {nom}**: [Enviar Oferta Irresistible]({link})")

if __name__ == "__main__":
    main()
