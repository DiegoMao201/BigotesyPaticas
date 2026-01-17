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

# Estilos CSS
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

    /* CLASE ESPECIAL PARA LA ALERTA DE CUMPLEAÑOS */
    .cumple-hoy {{
        background-color: #ffead0;
        border: 2px solid {COLOR_ACENTO};
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        color: #8a4b00;
        font-weight: bold;
        text-align: center;
        font-size: 1.2rem;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y PROCESAMIENTO
# ==========================================

@st.cache_resource(ttl=600)
def conectar_crm():
    try:
        # Verifica que existan los secretos configurados en Streamlit Cloud
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
    """Elimina espacios en blanco al inicio y final de los nombres de columnas"""
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
    
    # Asegurar nombre de columna Mascota
    if 'Mascota' not in df_cli.columns: 
        df_cli['Mascota'] = 'Tu Peludito'

    # 3. Procesamiento de Ventas (Calculo de RFM básico)
    if df_ven.empty or 'Fecha' not in df_ven.columns or 'Cedula_Cliente' not in df_ven.columns:
        df_cli['Estado'] = "⚪ Nuevo"
        df_cli['Dias_Sin_Compra'] = 999
        df_cli['Ultima_Compra_Dt'] = pd.NaT
        df_cli['Ultimo_Producto'] = "N/A"
    else:
        df_ven['Cedula_Cliente'] = df_ven['Cedula_Cliente'].astype(str).str.replace(r'\.0$', '', regex=True)
        df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
        
        resumen_ventas = df_ven.groupby('Cedula_Cliente').agg({
            'Fecha': 'max',
            'Total': 'sum',
            'Items': 'last'
        }).reset_index()
        
        resumen_ventas.columns = ['Cedula', 'Ultima_Compra_Dt', 'Total_Gastado', 'Ultimo_Producto']
        
        # Merge y Lógica de Negocio
        df_cli = pd.merge(df_cli, resumen_ventas, on='Cedula', how='left')
        
        hoy = pd.Timestamp.now()
        df_cli['Dias_Sin_Compra'] = (hoy - df_cli['Ultima_Compra_Dt']).dt.days.fillna(999)
        
        def clasificar(dias):
            if dias <= 30: return "🟢 Activo"
            elif 31 <= dias <= 60: return "🟡 Recompra (Alerta)"
            elif 61 <= dias <= 90: return "🟠 Riesgo"
            elif dias > 90 and dias != 999: return "🔴 Perdido"
            else: return "⚪ Nuevo"
            
        df_cli['Estado'] = df_cli['Dias_Sin_Compra'].apply(clasificar)
    
    # 4. DETECCIÓN DE CUMPLEAÑOS (CORREGIDO PARA TU FORMATO)
    # Nombre exacto de la columna según tu foto: 'Cumpleaños_mascota'
    col_nac = 'Cumpleaños_mascota'
    
    df_cli['Es_Cumple_Mes'] = False
    df_cli['Es_Cumple_Hoy'] = False
    
    if col_nac in df_cli.columns:
        # A) Convertimos a string y limpiamos
        df_cli[col_nac] = df_cli[col_nac].astype(str).str.strip()
        
        # B) Convertimos a FECHA
        # Como tu foto muestra '2023-12-07' (Año-Mes-Dia), Pandas lo detecta mejor sin 'dayfirst=True'
        # errors='coerce' transformará fechas inválidas o vacías en NaT (Not a Time)
        df_cli['Fecha_Nac_DT'] = pd.to_datetime(df_cli[col_nac], errors='coerce')
        
        hoy_dt = datetime.now()
        
        # C) Lógica de Comparación
        # Extraemos el MES y el DÍA de la fecha de nacimiento de la mascota
        df_cli['Mes_Nac'] = df_cli['Fecha_Nac_DT'].dt.month
        df_cli['Dia_Nac'] = df_cli['Fecha_Nac_DT'].dt.day
        
        # Validamos dónde hay fechas reales (no vacías)
        mask_valid = df_cli['Fecha_Nac_DT'].notna()
        
        # LÓGICA DE MES: ¿El mes de nacimiento es igual al mes actual?
        df_cli.loc[mask_valid, 'Es_Cumple_Mes'] = df_cli.loc[mask_valid, 'Mes_Nac'] == hoy_dt.month
        
        # LÓGICA DE HOY: ¿El mes es igual AL ACTUAL Y el día es igual AL ACTUAL?
        df_cli.loc[mask_valid, 'Es_Cumple_Hoy'] = (
            (df_cli.loc[mask_valid, 'Mes_Nac'] == hoy_dt.month) & 
            (df_cli.loc[mask_valid, 'Dia_Nac'] == hoy_dt.day)
        )

    return df_cli, df_ven, "OK"

# ==========================================
# 3. GENERADOR DE LINKS WHATSAPP
# ==========================================

def link_whatsapp(telefono, mensaje):
    if not telefono: return None
    # Limpieza agresiva del teléfono
    tel = str(telefono).replace(" ", "").replace("+", "").replace("-", "").replace(".", "").replace("(", "").replace(")", "").strip()
    
    if len(tel) < 7: return None
    # Asumimos código país 57 (Colombia) si es un número de 10 dígitos, ajústalo si estás en otro país
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
        
        hoy_dt = datetime.now()
        hoy_str = hoy_dt.strftime('%d/%m/%Y')
        
        # Diccionario de meses para mostrar nombre en español
        meses_es = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        mes_actual_nombre = meses_es[hoy_dt.month]

        st.success(f"📅 Hoy es: {hoy_str}")
        st.info(f"🎂 Mes de: **{mes_actual_nombre}**")

    # Carga de datos
    ws_cli, ws_ven = conectar_crm()
    if not ws_cli: return
    
    with st.spinner('Conectando con la base de datos de peluditos...'):
        master, df_ven, status = procesar_inteligencia(ws_cli, ws_ven)

    if master.empty:
        st.warning("⚠️ No se encontraron datos en la hoja de Clientes.")
        return

    # --- KPI HEADER ---
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>📊</span> Tablero de Control", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    activos = len(master[master['Estado'] == "🟢 Activo"]) if 'Estado' in master.columns else 0
    alertas = len(master[master['Estado'] == "🟡 Recompra (Alerta)"]) if 'Estado' in master.columns else 0
    
    # Contadores de Cumpleaños
    cumple_hoy_count = len(master[master['Es_Cumple_Hoy'] == True]) if 'Es_Cumple_Hoy' in master.columns else 0
    # Cumple mes (excluyendo los de hoy para no duplicar en lógica visual, aunque el filtro de abajo lo maneja)
    cumple_mes_total = len(master[master['Es_Cumple_Mes'] == True]) if 'Es_Cumple_Mes' in master.columns else 0

    col1.metric("Clientes Totales", len(master))
    col2.metric("Activos (Mes)", activos)
    col3.metric("🔥 Recompra Urgente", alertas, delta="Prioridad Alta", delta_color="inverse")
    col4.metric("🎂 Cumpleaños HOY", cumple_hoy_count, delta=f"Total Mes: {cumple_mes_total}")

    st.markdown("---")

    # --- TABS DE GESTIÓN ---
    tabs = st.tabs([
        "🎂 Cumpleaños", 
        "🔄 Smart Rebuy", 
        "💁‍♀️ Servicios (Ángela)", 
        "📢 Campañas Auto", 
        "🚑 Recuperación"
    ])

    # ==========================================
    # TAB 1: CUMPLEAÑOS (CORREGIDO)
    # ==========================================
    with tabs[0]:
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>🎂</span> Centro de Celebraciones - {mes_actual_nombre}", unsafe_allow_html=True)
        
        if 'Es_Cumple_Hoy' not in master.columns:
            st.error("No se pudo procesar la columna 'Cumpleaños_mascota'. Verifica que el nombre sea exacto en Google Sheets.")
        else:
            # Separar los de HOY de los del resto del MES
            df_hoy = master[master['Es_Cumple_Hoy'] == True].copy()
            # El resto del mes son los que son del Mes == True PERO Hoy == False
            df_mes = master[(master['Es_Cumple_Mes'] == True) & (master['Es_Cumple_Hoy'] == False)].copy()

            # --- SECCIÓN A: CUMPLE HOY ---
            if not df_hoy.empty:
                st.markdown(f"""
                <div class="cumple-hoy">
                    🎉 ¡ATENCIÓN! ¡HOY CUMPLEN AÑOS {len(df_hoy)} PELUDITOS! 🎂🎈
                </div>
                """, unsafe_allow_html=True)
                
                st.write("**Lista de Cumpleañeros de HOY:**")
                # Mostrar solo columnas relevantes
                cols_hoy = ['Nombre', 'Mascota', 'Telefono', 'Cumpleaños_mascota', 'Tipo_Mascota']
                st.dataframe(df_hoy[[c for c in cols_hoy if c in df_hoy.columns]], use_container_width=True)

                col_gift1, col_gift2 = st.columns([1, 2])
                with col_gift1:
                     regalo_hoy = st.text_input("🎁 Regalo Especial HOY:", "Postre de cortesía + 20% OFF", key="gift_hoy")
                
                with col_gift2:
                    st.info("👇 Haz click abajo para enviar la felicitación.")

                for idx, row in df_hoy.iterrows():
                    nom = row.get('Nombre', 'Amigo')
                    mascota = row.get('Mascota', 'tu bebé')
                    tel = row.get('Telefono', '')
                    
                    msg = msg_cumple(mascota, regalo_hoy)  # o regalo_mes
                    link = link_whatsapp(tel, msg)
                    if link:
                        st.markdown(f"🎈 **{mascota}** (Dueño: {nom}) → [📲 Enviar WhatsApp de Cumpleaños]({link})")
                
                st.markdown("---")
            else:
                st.info(f"📅 Hoy ({hoy_str}) no hay cumpleaños exactos registrados. ¡Revisemos los del mes!")

            # --- SECCIÓN B: RESTO DEL MES ---
            st.subheader(f"📅 Resto de cumpleañeros de {mes_actual_nombre} ({len(df_mes)})")
            st.caption("Aprovecha para enviarles una promo adelantada o invitarlos a celebrar este mes.")
            
            if not df_mes.empty:
                cols_mes = ['Nombre', 'Mascota', 'Cumpleaños_mascota', 'Telefono']
                st.dataframe(df_mes[[c for c in cols_mes if c in df_mes.columns]], use_container_width=True)
                
                regalo_mes = st.text_input("🎟 Promo general del mes:", "10% de descuento en snacks todo el mes", key="gift_mes")
                
                st.write("##### 💌 Enviar Mensaje de 'Mes de Cumpleaños':")
                
                # Expandible para no llenar la pantalla si son muchos
                with st.expander("Ver lista de envío para el Mes"):
                    for idx, row in df_mes.iterrows():
                        nom = row.get('Nombre', 'Cliente')
                        mascota = row.get('Mascota', 'tu peludito')
                        tel = row.get('Telefono', '')
                        fecha_txt = str(row.get('Cumpleaños_mascota', 'este mes'))
                        
                        msg = f"¡Hola {nom}! 🐾 Vimos en nuestro calendario que es el mes de cumpleaños de {mascota} ({fecha_txt})! 🎂🎈 Queremos adelantarnos: Tienen **{regalo_mes}** para que celebremos juntos. 🎁 ¡Los esperamos! ✨ *Bigotes y Paticas*"
                        
                        link = link_whatsapp(tel, msg)
                        if link:
                            st.markdown(f"🗓 **{mascota}** (Fecha: {fecha_txt}) → [📲 Enviar Promo Mes]({link})")
            else:
                st.write("No hay más cumpleañeros este mes.")

    # ==========================================
    # TAB 2: RECOMPRA INTELIGENTE
    # ==========================================
    with tabs[1]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🥣</span> Alerta: Plato Vacío (30-60 días)", unsafe_allow_html=True)
        
        if 'Estado' in master.columns:
            df_rebuy = master[master['Estado'] == "🟡 Recompra (Alerta)"].copy()
        else:
            df_rebuy = pd.DataFrame()

        if df_rebuy.empty:
            st.success("✅ Todo al día. No hay alertas de recompra urgentes.")
        else:
            cols_mostrar = ['Nombre', 'Mascota', 'Telefono', 'Ultimo_Producto', 'Dias_Sin_Compra']
            cols_existentes = [c for c in cols_mostrar if c in df_rebuy.columns]
            st.dataframe(df_rebuy[cols_existentes], use_container_width=True, hide_index=True)
            
            st.markdown("##### 🚀 Click para enviar Recordatorio Bonito:")
            for idx, row in df_rebuy.iterrows():
                nom = row.get('Nombre', 'Cliente')
                mascota = row.get('Mascota', 'tu peludito')
                prod = str(row.get('Ultimo_Producto', 'su alimento')).split('(')[0]
                tel = row.get('Telefono', '')
                
                msg = msg_recompra(nom, mascota, prod)
                link = link_whatsapp(tel, msg)
                
                if link:
                    st.markdown(f"🔸 **{mascota}** (Dueño: {nom}) → [📲 WhatsApp Recompra]({link})")

    # ==========================================
    # TAB 3: SERVICIOS (ÁNGELA)
    # ==========================================
    with tabs[2]:
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>💁‍♀️</span> Mensajes de Ángela", unsafe_allow_html=True)
        
        if 'Estado' in master.columns:
            df_angela = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido", "⚪ Nuevo"])].copy()
        else:
            df_angela = master.copy()
        
        st.write(f"**Lista de envío ({len(df_angela)} clientes inactivos o nuevos):**")
        
        with st.expander("Ver lista detallada"):
            cols_angela = ['Nombre', 'Mascota', 'Telefono', 'Email']
            st.dataframe(df_angela[[c for c in cols_angela if c in df_angela.columns]], use_container_width=True)

        st.markdown("##### 💌 Enviar Saludo:")
        for idx, row in df_angela.iterrows():
            nom = row.get('Nombre', 'Vecino')
            mascota = row.get('Mascota', 'tu mascota')
            tel = row.get('Telefono', '')
            
            msg_serv = f"¡Hola {nom}! 🌈 Hace tiempo no vemos la colita feliz de {mascota} y los extrañamos mucho en Bigotes y Patitas 🥺🐾. Soy Ángela 👋. Solo pasaba a saludarte y recordarte que aquí seguimos con el corazón abierto. ❤️ ¿Cómo han estado? ¡Nos encantaría saber de ustedes! ✨🚚"
            
            link = link_whatsapp(tel, msg_serv)
            if link:
                st.write(f"💕 **{nom} & {mascota}**: [Enviar Saludo]({link})")

    # ==========================================
    # TAB 4: CAMPAÑAS AUTO
    # ==========================================
    with tabs[3]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>📢</span> Creador de Campañas", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns([1, 2])
        
        with col_c1:
            motivo = st.text_input("Motivo de la campaña", placeholder="Ej: Llegaron juguetes nuevos")
            if not motivo: motivo = "contarte novedades increíbles"
            filtro_camp = st.selectbox("Destinatarios", ["Todos mis Clientes", "Solo Activos (VIP)", "Clientes Inactivos"])
        
        target = master
        if 'Estado' in master.columns:
            if filtro_camp == "Solo Activos (VIP)":
                target = master[master['Estado'] == "🟢 Activo"]
            elif filtro_camp == "Clientes Inactivos":
                target = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido"])]

        with col_c2:
            st.info(f"✨ Mensaje sobre: **'{motivo}'** para {len(target)} personas.")
        
        st.markdown("---")
        with st.expander("Ver lista de envío de campaña"):
            for idx, row in target.iterrows():
                nom = row.get('Nombre', 'Amigo')
                mascota = row.get('Mascota', 'tu peludito')
                tel = row.get('Telefono', '')
                
                msg_auto = f"¡Hola {nom}! 🐾 Esperamos que {mascota} esté súper bien. 🌟 Pasamos por aquí desde Bigotes y Patitas para {motivo}. 😍✨ Recuerda que amamos consentir a {mascota}. ¡Cualquier duda estamos a un ladrido de distancia! 🐕❤️"
                
                link = link_whatsapp(tel, msg_auto)
                if link:
                    st.markdown(f"💌 **{nom}**: [Enviar Campaña]({link})")

    # ==========================================
    # TAB 5: RECUPERACIÓN
    # ==========================================
    with tabs[4]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🚑</span> Rescate con Oferta", unsafe_allow_html=True)
        
        if 'Estado' in master.columns:
            df_risk = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido"])].copy()
        else:
            df_risk = pd.DataFrame()
        
        if df_risk.empty:
            st.success("¡Excelente! No tienes clientes perdidos.")
        else:
            st.write(f"Detectamos {len(df_risk)} clientes para recuperar.")
            gancho = st.text_input("Oferta Gancho:", "Envío Gratis + una Sorpresa 🎁")
            
            with st.expander("Ver lista de recuperación"):
                for idx, row in df_risk.iterrows():
                    nom = row.get('Nombre', 'Cliente')
                    mascota = row.get('Mascota', 'tu mascota')
                    tel = row.get('Telefono', '')
                    
                    msg = msg_inactivo(nom, mascota, gancho)
                    link = link_whatsapp(tel, msg)
                    
                    if link:
                        st.markdown(f"🎣 **Recuperar a {nom}**: [Enviar Oferta]({link})")

if __name__ == "__main__":
    main()
