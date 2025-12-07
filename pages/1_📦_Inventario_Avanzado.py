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
from twilio.rest import Client
import json
import uuid

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================

st.set_page_config(
    page_title="Nexus Ultra: AI Procurement & SRM",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS Premium
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; color: #1e293b; }
    
    /* KPI Cards Mejoradas */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
        padding: 15px;
        border-radius: 15px;
        border-left: 6px solid #4f46e5;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); }
    
    /* Botones Personalizados */
    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Tablas */
    .stDataFrame { border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SISTEMA DE COMUNICACIÓN (Email & WhatsApp)
# ==========================================

def enviar_correo_proveedor(proveedor, email_destino, archivo_excel, nombre_archivo):
    """Envía la PO por correo usando SMTP."""
    try:
        if not email_destino or "@" not in str(email_destino):
            return False, "Email de proveedor inválido."

        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["sender_email"]
        msg['To'] = email_destino
        msg['Subject'] = f"Nueva Orden de Compra - {proveedor} - {datetime.now().strftime('%d/%m/%Y')}"

        body = f"""
        Estimado equipo de {proveedor},
        
        Adjunto encontrarán una nueva orden de compra generada por nuestro sistema Nexus AI.
        
        Por favor confirmar recepción y fecha estimada de entrega.
        
        Cordialmente,
        Dpto. Compras.
        """
        msg.attach(MIMEText(body, 'plain'))

        part = MIMEApplication(archivo_excel, Name=nombre_archivo)
        part['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        msg.attach(part)

        server = smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"])
        server.starttls()
        server.login(st.secrets["email"]["sender_email"], st.secrets["email"]["sender_password"])
        server.send_message(msg)
        server.quit()
        return True, "Correo enviado exitosamente."
    except Exception as e:
        return False, f"Error SMTP: {str(e)}"

def enviar_whatsapp_tierno(tipo_mensaje, datos_extra=None):
    """
    Envía notificaciones WhatsApp con personalidad 'Bigotes y Paticas'.
    Tipos: 'nueva_orden', 'alerta_stock', 'recepcion_ok'
    """
    try:
        client = Client(st.secrets["twilio"]["account_sid"], st.secrets["twilio"]["auth_token"])
        
        emojis = "🐱🐾📦✨🌱"
        mensaje = ""
        
        if tipo_mensaje == 'nueva_orden':
            mensaje = f"""
            *¡Miau! 🐱 Hola Humano Favorito.*
            
            El Agente Bigotes informa: ¡Hemos enviado una nueva orden de compra! 🐾
            
            *Proveedor:* {datos_extra.get('proveedor')}
            *Valor:* ${datos_extra.get('monto'):,.0f}
            
            ¡Espero mis sobres de comida premium! 🐟
            """
        elif tipo_mensaje == 'recepcion_ok':
            mensaje = f"""
            *¡Ronroneos de Felicidad! 😻*
            
            ¡Llegó mercancía a la bodega!
            
            *Orden:* {datos_extra.get('id_orden')}
            *Proveedor:* {datos_extra.get('proveedor')}
            *Lead Time:* {datos_extra.get('dias')} días
            
            Inventario actualizado. A amasar panecitos. 🍞🐈
            """
            
        message = client.messages.create(
            from_=st.secrets["twilio"]["whatsapp_from"],
            body=mensaje,
            to=st.secrets["twilio"]["whatsapp_to"]
        )
        return True, message.sid
    except Exception as e:
        return False, str(e)

# ==========================================
# 3. CONEXIÓN Y DATOS (CON CAPACIDAD DE ESCRITURA)
# ==========================================

@st.cache_resource
def conectar_db():
    try:
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["general"]["SHEET_URL"])
        return sh
    except Exception as e:
        st.error(f"Error Database: {e}")
        return None

def cargar_datos(sh):
    ws_inv = sh.worksheet("Inventario")
    ws_ven = sh.worksheet("Ventas")
    ws_prov = sh.worksheet("Maestro_Proovedores")
    
    # Manejo de errores si no existe la hoja de historial
    try: ws_hist_ordenes = sh.worksheet("Historial_Ordenes")
    except: ws_hist_ordenes = None

    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    df_prov = pd.DataFrame(ws_prov.get_all_records())
    
    df_ordenes = pd.DataFrame()
    if ws_hist_ordenes:
        df_ordenes = pd.DataFrame(ws_hist_ordenes.get_all_records())

    # Limpieza básica
    cols_inv = {'ID_Producto': 'ID', 'Stock': 'Stock', 'Costo': 'Costo', 'Precio': 'Precio', 'Nombre': 'Nombre'}
    df_inv = df_inv.rename(columns={k:v for k,v in cols_inv.items() if k in df_inv.columns})
    
    # Conversión numérica segura
    for df in [df_inv, df_ordenes]:
        if 'Stock' in df.columns: 
             df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce').fillna(0)
        if 'Costo' in df.columns:
             df['Costo'] = pd.to_numeric(df['Costo'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
    
    return df_inv, df_ven, df_prov, df_ordenes, ws_hist_ordenes

def guardar_orden_historial(ws, orden_data):
    """Guarda una nueva orden en Google Sheets para 'aprender'."""
    if ws:
        # Fila: ID, Proveedor, Fecha, JSON, Total, Estado, Fecha_Recepcion, Lead_Time, Calificacion
        row = [
            orden_data['id'],
            orden_data['proveedor'],
            str(datetime.now().date()),
            json.dumps(orden_data['items']), # Guardamos items como string
            orden_data['total'],
            "Pendiente",
            "", # Fecha recepción vacía
            "", # Lead Time vacío
            ""  # Calificacion vacía
        ]
        ws.append_row(row)

# ==========================================
# 4. LÓGICA DE NEGOCIO AVANZADA (SRM & FORECAST)
# ==========================================

def analizar_rendimiento_proveedores(df_ordenes):
    """Analiza los datos históricos para calificar proveedores."""
    if df_ordenes.empty: return pd.DataFrame()
    
    # Filtramos solo las completadas
    df_compl = df_ordenes[df_ordenes['Estado'] == 'Recibido'].copy()
    
    if df_compl.empty: return pd.DataFrame()
    
    df_compl['Lead_Time_Real'] = pd.to_numeric(df_compl['Lead_Time_Real'], errors='coerce')
    df_compl['Calificacion'] = pd.to_numeric(df_compl['Calificacion'], errors='coerce')
    
    stats = df_compl.groupby('Proveedor').agg({
        'Lead_Time_Real': 'mean',
        'Calificacion': 'mean',
        'ID_Orden': 'count'
    }).reset_index()
    
    stats.columns = ['Proveedor', 'Tiempo_Entrega_Promedio', 'Score_Calidad', 'Ordenes_Totales']
    return stats

def procesar_datos(df_inv, df_ven, df_prov):
    # Lógica de forecast simple (promedio 90 días)
    # [Aquí iría la lógica detallada del ejemplo anterior, simplificada para caber]
    # Asumimos que df_inv ya tiene Stock y Costo limpios
    
    # 1. Ventas
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
    cutoff = datetime.now() - timedelta(days=90)
    df_recent = df_ven[df_ven['Fecha'] >= cutoff]
    
    ventas_dict = {}
    for items in df_recent['Items'].dropna():
        # Parsing muy básico, adaptar a tu formato real de strings
        for item in str(items).split(','):
            nombre = item.split('(')[0].strip()
            ventas_dict[nombre] = ventas_dict.get(nombre, 0) + 1
            
    df_metrics = pd.DataFrame(list(ventas_dict.items()), columns=['Nombre', 'Ventas_90d'])
    
    # 2. Merge Maestro
    df_master = pd.merge(df_inv, df_metrics, on='Nombre', how='left').fillna({'Ventas_90d': 0})
    
    # 3. Merge Proveedores
    if not df_prov.empty:
        # Asegurarse tipos de datos para merge
        df_master['SKU'] = df_master['SKU_Proveedor'].astype(str)
        df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str)
        df_master = pd.merge(df_master, df_prov, left_on='SKU', right_on='SKU_Interno', how='left')
    else:
        df_master['Nombre_Proveedor'] = 'Genérico'
        df_master['Factor_Pack'] = 1
        df_master['Email_Contacto'] = ''

    # 4. Cálculos Reabastecimiento
    df_master['Velocidad_Diaria'] = df_master['Ventas_90d'] / 90
    df_master['Stock_Dias'] = df_master['Stock'] / df_master['Velocidad_Diaria'].replace(0, 0.01)
    
    LEAD_TIME_STD = 15
    SAFETY_STOCK = 7
    df_master['Punto_Reorden'] = df_master['Velocidad_Diaria'] * (LEAD_TIME_STD + SAFETY_STOCK)
    df_master['Unidades_Faltantes'] = (df_master['Punto_Reorden']*2 - df_master['Stock']).clip(lower=0)
    
    # Ajuste por caja/pack
    df_master['Factor_Pack'] = pd.to_numeric(df_master['Factor_Pack'], errors='coerce').fillna(1)
    df_master['Packs_Pedir'] = np.ceil(df_master['Unidades_Faltantes'] / df_master['Factor_Pack'])
    df_master['Costo_Total_Sugerido'] = df_master['Unidades_Faltantes'] * df_master['Costo']

    return df_master

# ==========================================
# 5. UI PRINCIPAL
# ==========================================

def main():
    sh = conectar_db()
    if not sh: return
    
    df_inv, df_ven, df_prov, df_ordenes, ws_hist = cargar_datos(sh)
    df_master = procesar_datos(df_inv, df_ven, df_prov)
    
    # Análisis de Proveedores (Learning)
    df_srm = analizar_rendimiento_proveedores(df_ordenes)

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🧬 NEXUS ULTRA")
        st.info(f"Conectado a: {sh.title}")
        st.write("---")
        
        # Mini KPI
        if not df_srm.empty:
            best_prov = df_srm.sort_values('Score_Calidad', ascending=False).iloc[0]
            st.success(f"🏆 Mejor Proveedor:\n**{best_prov['Proveedor']}**")
        
        st.caption("v2.5 - AI Enabled")

    # --- HEADER ---
    st.markdown("## 🧠 Panel de Control Inteligente")
    
    k1, k2, k3, k4 = st.columns(4)
    inv_val = (df_master['Stock'] * df_master['Costo']).sum()
    por_pedir = df_master['Costo_Total_Sugerido'].sum()
    
    k1.metric("Valor Inventario", f"${inv_val:,.0f}")
    k2.metric("Necesidad de Compra", f"${por_pedir:,.0f}", "Cashflow requerido", delta_color="inverse")
    
    # KPI de Proveedores
    avg_lead = df_srm['Tiempo_Entrega_Promedio'].mean() if not df_srm.empty else 0
    k3.metric("Lead Time Real Promedio", f"{avg_lead:.1f} días", "Aprendido de historial")
    k4.metric("Órdenes Pendientes", len(df_ordenes[df_ordenes['Estado']=='Pendiente']) if not df_ordenes.empty else 0)

    st.markdown("---")
    
    # --- TABS PRINCIPALES ---
    tabs = st.tabs(["📊 Dashboard & SRM", "🛒 Centro de Compras AI", "📦 Recepción (Learning)", "📂 Datos Maestros"])

    # ------------------------------------------------------------------
    # TAB 1: DASHBOARD & SRM (Supplier Relationship Management)
    # ------------------------------------------------------------------
    with tabs[0]:
        c1, c2 = st.columns([2,1])
        
        with c1:
            st.subheader("Evaluación de Proveedores (Scorecard)")
            if not df_srm.empty:
                fig = px.scatter(df_srm, x='Tiempo_Entrega_Promedio', y='Score_Calidad', 
                                 size='Ordenes_Totales', color='Proveedor',
                                 title="Matriz Eficiencia vs Calidad",
                                 labels={'Tiempo_Entrega_Promedio': 'Días de Retraso (Menos es mejor)', 'Score_Calidad': 'Calidad (1-5)'})
                # Invertir eje X para que "menos días" sea mejor (hacia la derecha)
                fig.update_xaxes(autorange="reversed") 
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ℹ️ El sistema necesita recibir pedidos en la pestaña 'Recepción' para generar gráficos de proveedores.")

        with c2:
            st.subheader("Top Productos a Pedir")
            top_pedir = df_master.sort_values('Costo_Total_Sugerido', ascending=False).head(5)
            st.dataframe(top_pedir[['Nombre', 'Packs_Pedir', 'Costo_Total_Sugerido']], hide_index=True)

    # ------------------------------------------------------------------
    # TAB 2: CENTRO DE COMPRAS (GENERACIÓN & ENVÍO)
    # ------------------------------------------------------------------
    with tabs[1]:
        st.header("Gestión de Compras Automatizada")
        
        df_buy = df_master[df_master['Unidades_Faltantes'] > 0].copy()
        
        if df_buy.empty:
            st.success("✅ Inventario Saludable. No se requieren acciones.")
        else:
            proveedores_list = df_buy['Nombre_Proveedor'].unique()
            prov_sel = st.selectbox("Seleccionar Proveedor para Ordenar:", proveedores_list)
            
            # Detalle de la orden
            orden_actual = df_buy[df_buy['Nombre_Proveedor'] == prov_sel]
            
            st.markdown(f"### 📋 Orden Sugerida para: **{prov_sel}**")
            
            # Editor de datos (permite ajustar cantidades manualmente antes de pedir)
            orden_editada = st.data_editor(
                orden_actual[['SKU', 'Nombre', 'Stock', 'Packs_Pedir', 'Costo', 'Factor_Pack']],
                num_rows="dynamic",
                column_config={
                    "Packs_Pedir": st.column_config.NumberColumn("Cajas a Pedir", min_value=1, step=1),
                    "Costo": st.column_config.NumberColumn("Costo Unit", format="$%.2f")
                },
                use_container_width=True
            )
            
            # Calcular totales finales
            total_orden = (orden_editada['Packs_Pedir'] * orden_editada['Factor_Pack'] * orden_editada['Costo']).sum()
            st.metric("Total Orden Estimada", f"${total_orden:,.2f}")
            
            # --- ACCIONES ---
            c_act1, c_act2, c_act3 = st.columns(3)
            
            # Generar Excel en memoria
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                orden_editada.to_excel(writer, index=False, sheet_name='Orden_Compra')
            excel_data = output.getvalue()
            
            with c_act1:
                st.download_button("📥 Descargar Excel", data=excel_data, file_name=f"OC_{prov_sel}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            with c_act2:
                # Botón con confirmación usando session state es complejo, lo hacemos directo
                if st.button("📧 Enviar por Correo + Registrar"):
                    # 1. Obtener email
                    email_prov = df_prov[df_prov['Nombre_Proveedor'] == prov_sel]['Email'].values
                    email_dest = email_prov[0] if len(email_prov) > 0 else None
                    
                    if not email_dest:
                        st.error("❌ El proveedor no tiene email configurado en la hoja 'Maestro_Proovedores'.")
                    else:
                        with st.spinner("Enviando correos..."):
                            # Enviar
                            ok, msg = enviar_correo_proveedor(prov_sel, email_dest, excel_data, f"OC_{prov_sel}.xlsx")
                            if ok:
                                st.success(f"✅ {msg}")
                                # Registrar en DB
                                id_orden = f"PO-{uuid.uuid4().hex[:6].upper()}"
                                items_dict = orden_editada[['Nombre', 'Packs_Pedir']].to_dict('records')
                                
                                guardar_orden_historial(ws_hist, {
                                    'id': id_orden, 'proveedor': prov_sel, 
                                    'items': items_dict, 'total': total_orden
                                })
                                st.toast("Orden registrada en historial.")
                            else:
                                st.error(f"❌ {msg}")

            with c_act3:
                if st.button("🐱 Notificar por WhatsApp"):
                    with st.spinner("Contactando al Agente Bigotes..."):
                        ok, sid = enviar_whatsapp_tierno('nueva_orden', {'proveedor': prov_sel, 'monto': total_orden})
                        if ok:
                            st.balloons()
                            st.success("✅ Mensaje enviado! ID: " + sid)
                        else:
                            st.error("Error Twilio: " + sid)

    # ------------------------------------------------------------------
    # TAB 3: RECEPCIÓN Y APRENDIZAJE (EL CEREBRO)
    # ------------------------------------------------------------------
    with tabs[2]:
        st.header("📦 Muelle de Recepción (Feedback Loop)")
        st.info("Aquí registras cuando llega la mercancía. Esto entrena al sistema sobre Lead Times reales.")
        
        if df_ordenes.empty:
            st.write("No hay historial de órdenes.")
        else:
            # Filtro pendientes
            pendientes = df_ordenes[df_ordenes['Estado'] == 'Pendiente']
            
            if pendientes.empty:
                st.success("🎉 No hay órdenes pendientes de llegada.")
            else:
                st.write("### Órdenes en Tránsito")
                
                for idx, row in pendientes.iterrows():
                    with st.expander(f"🚛 {row['Proveedor']} - Enviada: {row['Fecha_Orden']} (ID: {row['ID_Orden']})"):
                        c_rec1, c_rec2 = st.columns(2)
                        
                        with c_rec1:
                            st.json(row['Items_JSON'])
                        
                        with c_rec2:
                            fecha_recepcion = st.date_input("Fecha Real de Llegada", key=f"d_{idx}")
                            calificacion = st.slider("Calificación del Servicio (1=Malo, 5=Excelente)", 1, 5, 5, key=f"s_{idx}")
                            
                            if st.button("✅ Confirmar Recepción", key=f"b_{idx}"):
                                # Calcular Lead Time
                                fecha_orden = pd.to_datetime(row['Fecha_Orden']).date()
                                lead_time = (fecha_recepcion - fecha_orden).days
                                
                                # Actualizar Google Sheets
                                # Encontrar la fila (idx + 2 porque sheet headers es 1 y index empieza en 0)
                                # IMPORTANTE: Esto asume que el orden no cambia. Mejor buscar por ID.
                                cell = ws_hist.find(row['ID_Orden'])
                                if cell:
                                    r = cell.row
                                    # Actualizar columnas Estado(6), Fecha_Recepcion(7), Lead_Time(8), Calificacion(9)
                                    ws_hist.update_cell(r, 6, "Recibido")
                                    ws_hist.update_cell(r, 7, str(fecha_recepcion))
                                    ws_hist.update_cell(r, 8, lead_time)
                                    ws_hist.update_cell(r, 9, calificacion)
                                    
                                    st.success("Inventario Recibido. Sistema Actualizado.")
                                    
                                    # Notificar WhatsApp
                                    enviar_whatsapp_tierno('recepcion_ok', {
                                        'id_orden': row['ID_Orden'], 
                                        'proveedor': row['Proveedor'],
                                        'dias': lead_time
                                    })
                                    st.rerun()

    # ------------------------------------------------------------------
    # TAB 4: DATOS MAESTROS
    # ------------------------------------------------------------------
    with tabs[3]:
        st.dataframe(df_master)

if __name__ == "__main__":
    main()
