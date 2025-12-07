import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import time
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

# CSS IDÉNTICO AL CÓDIGO 1 PARA CONSISTENCIA VISUAL
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

    /* Estilo de Tarjetas (Metric Containers) */
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

    /* Botones Primarios */
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

    /* Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
        border-radius: 8px;
        border-color: #e0e0e0;
    }}

    /* Tabs Personalizados */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 45px;
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
# 2. CONEXIÓN Y PROCESAMIENTO ROBUSTO
# ==========================================

@st.cache_resource(ttl=600)
def conectar_crm():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos.")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Intentar cargar hojas, crear si no existen (lectura segura)
        try: ws_cli = sh.worksheet("Clientes")
        except: ws_cli = None
        
        try: ws_ven = sh.worksheet("Ventas")
        except: ws_ven = None
            
        return ws_cli, ws_ven
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None, None

def limpiar_columnas(df):
    """Elimina espacios en blanco de los nombres de columnas para evitar KeyError"""
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

def procesar_inteligencia(ws_cli, ws_ven):
    # 1. Cargar Datos Crudos
    data_cli = ws_cli.get_all_records() if ws_cli else []
    data_ven = ws_ven.get_all_records() if ws_ven else []
    
    df_cli = pd.DataFrame(data_cli)
    df_ven = pd.DataFrame(data_ven)
    
    # 2. Limpieza de Columnas (FIX DEL ERROR KEYERROR)
    df_cli = limpiar_columnas(df_cli)
    df_ven = limpiar_columnas(df_ven)
    
    # 3. Validación de Datos Mínimos
    if df_cli.empty:
        return pd.DataFrame(), pd.DataFrame(), "Sin clientes"
    
    # Asegurar columnas críticas en Clientes
    if 'Cedula' not in df_cli.columns: df_cli['Cedula'] = ''
    df_cli['Cedula'] = df_cli['Cedula'].astype(str).str.replace(r'\.0$', '', regex=True)
    
    # Asegurar columnas críticas en Ventas
    if df_ven.empty or 'Fecha' not in df_ven.columns or 'Cedula_Cliente' not in df_ven.columns:
        # Si no hay ventas, devolvemos clientes sin métricas de compra
        df_cli['Estado'] = "⚪ Nuevo"
        df_cli['Dias_Sin_Compra'] = 999
        df_cli['Ultima_Compra_Dt'] = pd.NaT
        return df_cli, df_ven, "OK (Sin Ventas)"

    # 4. Procesamiento de Fechas y Métricas
    df_ven['Cedula_Cliente'] = df_ven['Cedula_Cliente'].astype(str).str.replace(r'\.0$', '', regex=True)
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
    
    # Agrupar ventas por cliente para sacar la última fecha
    # Usamos groupby y agg para evitar sort_values sobre columna inexistente si falla conversión
    resumen_ventas = df_ven.groupby('Cedula_Cliente').agg({
        'Fecha': 'max',
        'Total': 'sum',
        'Items': 'last' # Último item comprado (aproximado)
    }).reset_index()
    
    resumen_ventas.columns = ['Cedula', 'Ultima_Compra_Dt', 'Total_Gastado', 'Ultimo_Producto']
    
    # 5. Merge (Unir Clientes con su Historial)
    master = pd.merge(df_cli, resumen_ventas, on='Cedula', how='left')
    
    # 6. Lógica de Negocio (El Cerebro)
    hoy = pd.Timestamp.now()
    master['Dias_Sin_Compra'] = (hoy - master['Ultima_Compra_Dt']).dt.days.fillna(999)
    
    def clasificar(dias):
        if dias <= 30: return "🟢 Activo"
        elif 31 <= dias <= 60: return "🟡 Recompra (Alerta)"
        elif 61 <= dias <= 90: return "🟠 Riesgo"
        elif dias > 90 and dias != 999: return "🔴 Perdido"
        else: return "⚪ Nuevo"
        
    master['Estado'] = master['Dias_Sin_Compra'].apply(clasificar)
    
    # Detectar Cumpleaños
    if 'Fecha' in master.columns: # A veces se guarda como 'Fecha' en vez de 'Fecha_Nacimiento'
        col_nac = 'Fecha'
    elif 'Cumpleaños Mascota' in master.columns:
         col_nac = 'Cumpleaños Mascota'
    else:
        col_nac = None

    master['Es_Cumple'] = False
    if col_nac and col_nac in master.columns:
        master[col_nac] = pd.to_datetime(master[col_nac], errors='coerce')
        master['Mes_Cumple'] = master[col_nac].dt.month
        master['Es_Cumple'] = master['Mes_Cumple'] == hoy.month

    return master, df_ven, "OK"

# ==========================================
# 3. GENERADORES DE MENSAJES
# ==========================================

def link_whatsapp(telefono, mensaje):
    if not telefono: return None
    # Limpieza básica Colombia
    tel = str(telefono).replace(" ", "").replace("+", "").replace("-", "").replace(".", "")
    if len(tel) == 10: tel = "57" + tel
    return f"https://wa.me/{tel}?text={quote(mensaje)}"

# ==========================================
# 4. UI PRINCIPAL
# ==========================================

def main():
    # Sidebar Estilizado Nexus Pro
    with st.sidebar:
        st.markdown(f"<h1 style='color:{COLOR_PRIMARIO}; text-align: center;'>Nexus Loyalty</h1>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='color:{COLOR_TEXTO}; text-align: center; margin-top: -20px;'>Bigotes y Patitas</h4>", unsafe_allow_html=True)
        st.markdown("---")
        st.info("💡 Este módulo analiza tus ventas y clientes para decirte a quién contactar hoy para vender más.")

    # Conexión
    ws_cli, ws_ven = conectar_crm()
    if not ws_cli: return

    # Carga de Datos
    master, df_ven, status = procesar_inteligencia(ws_cli, ws_ven)

    if master.empty:
        st.warning("⚠️ No hay clientes registrados en la base de datos.")
        return

    # --- KPI DASHBOARD ---
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>❤️</span> Centro de Fidelización", unsafe_allow_html=True)
    
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    
    total_cli = len(master)
    activos = len(master[master['Estado'] == "🟢 Activo"])
    alerta_recompra = len(master[master['Estado'] == "🟡 Recompra (Alerta)"])
    riesgo = len(master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido"])])
    
    col_k1.metric("Total Clientes", total_cli)
    col_k2.metric("Clientes Activos", activos, delta="Compraron < 30 días")
    col_k3.metric("🔥 Oportunidad Venta", alerta_recompra, delta="Llamar YA", delta_color="inverse")
    col_k4.metric("En Riesgo / Perdidos", riesgo, delta="Recuperar", delta_color="inverse")

    st.markdown("---")

    # --- TABS DE ACCIÓN ---
    tabs = st.tabs(["🔄 Smart Rebuy (Recompra)", "🎂 Cumpleaños Mascota", "🚑 Recuperación", "📢 Campañas"])

    # --- TAB 1: RECOMPRA INTELIGENTE ---
    with tabs[0]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🥣</span> Alerta de Reabastecimiento", unsafe_allow_html=True)
        st.caption("Clientes que compraron hace 30-60 días. Probablemente se les acabó la comida.")
        
        df_rebuy = master[master['Estado'] == "🟡 Recompra (Alerta)"].copy()
        
        if df_rebuy.empty:
            st.success("✅ ¡Excelente! No hay clientes pendientes de recompra urgente.")
        else:
            # Seleccionar columnas visibles
            cols_show = ['Nombre', 'Nombre_Mascota', 'Telefono', 'Ultimo_Producto', 'Dias_Sin_Compra']
            # Asegurar que existan
            cols_show = [c for c in cols_show if c in df_rebuy.columns]
            
            st.dataframe(df_rebuy[cols_show], use_container_width=True, hide_index=True)
            
            st.markdown("##### 🚀 Acciones Rápidas")
            
            # Generador de Links
            for idx, row in df_rebuy.iterrows():
                prod = str(row.get('Ultimo_Producto', 'su alimento')).split('(')[0]
                mascota = row.get('Nombre_Mascota', 'tu peludito')
                cliente = row.get('Nombre', 'Cliente')
                tel = row.get('Telefono', '')
                
                msg = f"Hola {cliente}! 🐾 Esperamos que {mascota} esté genial. Notamos que ya casi es hora de refilar su {prod}. 🥣 ¿Te enviamos el domicilio hoy sin costo?"
                link = link_whatsapp(tel, msg)
                
                if link:
                    with st.expander(f"📱 Contactar a {cliente} ({mascota})"):
                        st.markdown(f"**Mensaje sugerido:** _{msg}_")
                        st.markdown(f"<a href='{link}' target='_blank' style='background-color:{COLOR_PRIMARIO}; color:white; padding:8px 16px; border-radius:5px; text-decoration:none; font-weight:bold;'>👉 Enviar WhatsApp</a>", unsafe_allow_html=True)

    # --- TAB 2: CUMPLEAÑOS ---
    with tabs[1]:
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>🎂</span> Club de Cumpleaños ({datetime.now().strftime('%B')})", unsafe_allow_html=True)
        
        df_cumple = master[master['Es_Cumple'] == True].copy()
        
        if df_cumple.empty:
            st.info("No hay cumpleaños registrados este mes. ¡Recuerda pedir la fecha de nacimiento al registrar clientes!")
        else:
            st.dataframe(df_cumple[['Nombre', 'Nombre_Mascota', 'Telefono']], use_container_width=True)
            
            col_msg, col_promo = st.columns(2)
            descuento = col_promo.number_input("Descuento Regalo (%)", value=10, step=5)
            
            st.markdown("##### 🎁 Enviar Regalos")
            for idx, row in df_cumple.iterrows():
                mascota = row.get('Nombre_Mascota', 'tu peludito')
                cliente = row.get('Nombre', 'Cliente')
                tel = row.get('Telefono', '')
                
                msg = f"¡Feliz Cumpleaños a {mascota}! 🎂🐶 En Bigotes y Patitas queremos celebrarlo. Tienes un {descuento}% DE DESCUENTO en su torta o snacks favoritos todo este mes. 🎁 ¡Ven por su regalo!"
                link = link_whatsapp(tel, msg)
                
                if link:
                    st.markdown(f"🎉 **{mascota} ({cliente}):** [Enviar Regalo WhatsApp]({link})")

    # --- TAB 3: RECUPERACIÓN ---
    with tabs[2]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🚑</span> Estrategia de Retorno", unsafe_allow_html=True)
        st.caption("Clientes que no compran hace más de 60 días.")
        
        df_riesgo = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido"])].copy()
        
        if df_riesgo.empty:
            st.success("¡Base de datos saludable! Poca deserción.")
        else:
            st.dataframe(df_riesgo[['Nombre', 'Telefono', 'Dias_Sin_Compra', 'Ultimo_Producto']], use_container_width=True)
            
            st.markdown("##### 📢 Oferta de Reactivación")
            oferta = st.text_input("Define el gancho:", "Envío Gratis + Snack de Regalo")
            
            if st.button("Generar Campaña de Recuperación", type="primary"):
                st.markdown("---")
                for idx, row in df_riesgo.head(20).iterrows(): # Limitado a 20 para no saturar
                    cliente = row.get('Nombre', 'Cliente')
                    mascota = row.get('Nombre_Mascota', 'tu mascota')
                    tel = row.get('Telefono', '')
                    
                    msg = f"¡Hola {cliente}! Hace tiempo no vemos a {mascota} 🥺. ¡Los extrañamos en Bigotes y Patitas! Solo por volver, hoy tienen: {oferta}. 🐾 ¿Qué dices, se lo enviamos?"
                    link = link_whatsapp(tel, msg)
                    if link:
                        st.markdown(f"🔸 **{cliente}:** [Recuperar Cliente]({link})")

    # --- TAB 4: CAMPAÑAS ---
    with tabs[3]:
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>📢</span> Difusión General", unsafe_allow_html=True)
        
        with st.form("form_campaign"):
            st.markdown("**Crear Mensaje Masivo**")
            titulo = st.text_input("Motivo", "Nuevos Juguetes / Promo Fin de Mes")
            cuerpo = st.text_area("Mensaje", "Hola! Te cuento que llegaron collares hermosos...")
            
            filtro = st.radio("Enviar a:", ["Todos los Clientes", "Solo Activos (VIP)"])
            
            if st.form_submit_button("🚀 Preparar Envíos"):
                if filtro == "Solo Activos (VIP)":
                    target = master[master['Estado'] == "🟢 Activo"]
                else:
                    target = master
                
                st.success(f"Campaña preparada para {len(target)} clientes.")
                st.info("Haz clic en los enlaces abajo para abrir WhatsApp Web:")
                
                with st.expander("Ver lista de envío"):
                    for idx, row in target.iterrows():
                        tel = row.get('Telefono', '')
                        nom = row.get('Nombre', '')
                        if tel:
                            full_msg = f"Hola {nom}! 🐾 {cuerpo} - Equipo Bigotes y Patitas"
                            link = link_whatsapp(tel, full_msg)
                            st.write(f"👉 {nom}: [Enviar]({link})")

if __name__ == "__main__":
    main()
