import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
import json
import uuid
import time
from datetime import datetime, timedelta, date
from urllib.parse import quote
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================

st.set_page_config(
    page_title="Bigotes & Paticas | Nexus System",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    
    /* Métricas */
    div[data-testid="metric-container"] {
        background: #ffffff;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Botones */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        height: 3rem;
    }
    
    /* Headers */
    h1, h2, h3 { color: #831843; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #fce7f3;
        border-radius: 8px;
        padding: 0 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #831843 !important;
        color: white !important;
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
            st.error("❌ Falta configuración en secrets.toml")
            return None
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        return sh
    except Exception as e:
        st.error(f"🔴 Error de Conexión: {e}")
        return None

def get_worksheet_safe(sh, name, headers):
    """Obtiene una hoja o la crea si no existe con las cabeceras exactas."""
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=100, cols=20)
        ws.append_row(headers)
        return ws

def clean_currency(x):
    """Limpia formatos de moneda ($1,200.00 -> 1200.00)."""
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        clean = x.replace('$', '').replace(',', '').replace(' ', '').strip()
        if not clean: return 0.0
        try: return float(clean)
        except: return 0.0
    return 0.0

def cargar_datos_completos(sh):
    # 1. Definir columnas exactas según tu requerimiento
    cols_inv = ['ID_Producto', 'SKU_Proveedor', 'Nombre', 'Stock', 'Precio', 'Costo', 'Categoria']
    cols_ven = ['ID_Venta', 'Fecha', 'Cedula_Cliente', 'Nombre_Cliente', 'Tipo_Entrega', 'Direccion_Envio', 'Estado_Envio', 'Metodo_Pago', 'Banco_Destino', 'Total', 'Items']
    cols_prov = ['ID_Proveedor', 'Nombre_Proveedor', 'SKU_Proveedor', 'SKU_Interno', 'Factor_Pack', 'Ultima_Actualizacion', 'Email', 'Costo_Proveedor']
    cols_ord = ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total_Dinero', 'Estado', 'Fecha_Recepcion', 'Lead_Time_Real', 'Calificacion']
    cols_recep = ['Fecha_Recepcion', 'Folio_Factura', 'Proveedor', 'Fecha_Emision_Factura', 'Dias_Entrega', 'Total_Items', 'Total_Costo']

    # 2. Obtener Hojas
    ws_inv = get_worksheet_safe(sh, "Inventario", cols_inv)
    ws_ven = get_worksheet_safe(sh, "Ventas", cols_ven)
    ws_prov = get_worksheet_safe(sh, "Maestro_Proveedores", cols_prov)
    ws_ord = get_worksheet_safe(sh, "Historial_Ordenes", cols_ord)
    ws_recep = get_worksheet_safe(sh, "Historial_Recepciones", cols_recep)

    # 3. Convertir a DataFrames
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    df_prov = pd.DataFrame(ws_prov.get_all_records())
    df_ord = pd.DataFrame(ws_ord.get_all_records())
    
    # 4. Normalización de Tipos de Datos (Limpieza)
    
    # Inventario
    if not df_inv.empty:
        # Asegurar columnas aunque estén vacías
        for c in cols_inv: 
            if c not in df_inv.columns: df_inv[c] = ""
        
        df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
        df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
        df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
        df_inv['ID_Producto'] = df_inv['ID_Producto'].astype(str).str.strip()
    else:
        df_inv = pd.DataFrame(columns=cols_inv)

    # Proveedores
    if not df_prov.empty:
        for c in cols_prov:
            if c not in df_prov.columns: df_prov[c] = ""
            
        df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
        df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)
        df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str).str.strip()
        df_prov['Nombre_Proveedor'] = df_prov['Nombre_Proveedor'].astype(str).str.strip()
    else:
        df_prov = pd.DataFrame(columns=cols_prov)

    # Ordenes
    if not df_ord.empty:
        for c in cols_ord:
            if c not in df_ord.columns: df_ord[c] = ""
        df_ord['Total_Dinero'] = df_ord['Total_Dinero'].apply(clean_currency)
    else:
        df_ord = pd.DataFrame(columns=cols_ord)

    return {
        "df_inv": df_inv, "ws_inv": ws_inv,
        "df_ven": df_ven, "ws_ven": ws_ven,
        "df_prov": df_prov, "ws_prov": ws_prov,
        "df_ord": df_ord, "ws_ord": ws_ord,
        "ws_recep": ws_recep
    }

# ==========================================
# 3. LÓGICA DE NEGOCIO (PROCESAMIENTO)
# ==========================================

def procesar_inventario_avanzado(df_inv, df_ven, df_prov):
    # 1. Calcular Velocidad de Ventas (Últimos 90 días)
    if not df_ven.empty:
        df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
        cutoff = datetime.now() - timedelta(days=90)
        ven_recent = df_ven[df_ven['Fecha'] >= cutoff]
        
        # Desglosar items (asumiendo formato "Producto A, Producto B")
        # Si tu formato Items es JSON en Ventas, habría que parsearlo. 
        # Asumiremos texto simple separado por comas para compatibilidad general.
        stats = {}
        for _, row in ven_recent.iterrows():
            items_str = str(row.get('Items', ''))
            lista = items_str.split(',')
            for item in lista:
                # Limpiar nombre (quitar cantidades entre paréntesis si las hay)
                nombre_clean = item.split('(')[0].strip()
                if nombre_clean:
                    stats[nombre_clean] = stats.get(nombre_clean, 0) + 1
        
        df_sales = pd.DataFrame(list(stats.items()), columns=['Nombre', 'Ventas_90d'])
    else:
        df_sales = pd.DataFrame(columns=['Nombre', 'Ventas_90d'])

    # 2. Merge Inventario con Ventas
    if not df_inv.empty and 'Nombre' in df_inv.columns:
        master = pd.merge(df_inv, df_sales, on='Nombre', how='left').fillna({'Ventas_90d': 0})
    else:
        master = df_inv.copy()
        master['Ventas_90d'] = 0

    # 3. Métricas de Stock
    master['Velocidad_Diaria'] = master['Ventas_90d'] / 90
    master['Dias_Cobertura'] = np.where(master['Velocidad_Diaria'] > 0, master['Stock'] / master['Velocidad_Diaria'], 999)
    
    # 4. Definir Estados
    conditions = [
        (master['Stock'] == 0),
        (master['Dias_Cobertura'] <= 20), # Reordenar si hay para menos de 20 días
        (master['Dias_Cobertura'] > 20)
    ]
    choices = ['💀 AGOTADO', '🚨 Pedir', '✅ OK']
    master['Estado_Stock'] = np.select(conditions, choices, default='✅ OK')

    # 5. Calcular Sugerido (Para cubrir 45 días)
    master['Stock_Objetivo'] = master['Velocidad_Diaria'] * 45
    master['Faltante_Unidades'] = (master['Stock_Objetivo'] - master['Stock']).clip(lower=0)

    # 6. Merge con Proveedores (Cruce por ID_Producto = SKU_Interno)
    if not df_prov.empty:
        # Left join para traer datos del proveedor principal
        master_buy = pd.merge(master, df_prov, left_on='ID_Producto', right_on='SKU_Interno', how='left')
        
        # Llenar nulos para productos sin proveedor asignado
        master_buy['Nombre_Proveedor'] = master_buy['Nombre_Proveedor'].fillna('Genérico')
        master_buy['Factor_Pack'] = master_buy['Factor_Pack'].fillna(1).replace(0, 1)
        master_buy['Costo_Proveedor'] = np.where(master_buy['Costo_Proveedor'] > 0, master_buy['Costo_Proveedor'], master_buy['Costo'])
    else:
        master_buy = master.copy()
        master_buy['Nombre_Proveedor'] = 'Genérico'
        master_buy['Factor_Pack'] = 1
        master_buy['Costo_Proveedor'] = master_buy['Costo']
        master_buy['Email'] = ''

    # 7. Calcular Cajas
    master_buy['Cajas_Sugeridas'] = np.ceil(master_buy['Faltante_Unidades'] / master_buy['Factor_Pack'])
    master_buy['Costo_Total_Sugerido'] = master_buy['Cajas_Sugeridas'] * master_buy['Factor_Pack'] * master_buy['Costo_Proveedor']

    return master, master_buy

# ==========================================
# 4. UTILS: CORREO Y WHATSAPP
# ==========================================

def enviar_correo(destinatario, proveedor, df_orden):
    if not destinatario or "@" not in destinatario: return False, "Correo inválido"
    try:
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]
        
        # Crear HTML
        filas = ""
        total = 0
        for _, row in df_orden.iterrows():
            subtotal = row['Cajas_Sugeridas'] * row['Factor_Pack'] * row['Costo_Proveedor']
            total += subtotal
            filas += f"<tr><td>{row['Nombre']}</td><td style='text-align:center'>{int(row['Cajas_Sugeridas'])}</td><td style='text-align:right'>${subtotal:,.0f}</td></tr>"
            
        html = f"""
        <h2>Pedido para {proveedor}</h2>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse; width:100%">
            <tr style="background:#f3f4f6"><th>Producto</th><th>Cajas</th><th>Subtotal</th></tr>
            {filas}
            <tr><td colspan="2"><b>TOTAL</b></td><td style='text-align:right'><b>${total:,.0f}</b></td></tr>
        </table>
        <p>Favor confirmar recibido y fecha de entrega. Gracias.</p>
        """
        
        msg = MIMEMultipart()
        msg['Subject'] = f"Pedido Bigotes y Paticas - {date.today()}"
        msg['From'] = sender_email
        msg['To'] = destinatario
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Enviado"
    except Exception as e:
        return False, str(e)

def link_whatsapp(numero, proveedor, df_orden):
    if not numero: return None
    total = 0
    txt = f"Hola *{proveedor}*, pedido de Bigotes:\n"
    for _, row in df_orden.iterrows():
        sub = row['Cajas_Sugeridas'] * row['Factor_Pack'] * row['Costo_Proveedor']
        total += sub
        txt += f"📦 {int(row['Cajas_Sugeridas'])}cj {row['Nombre']}\n"
    txt += f"\n💰 Total: ${total:,.0f}"
    return f"https://wa.me/{numero}?text={quote(txt)}"

# ==========================================
# 5. UI PRINCIPAL
# ==========================================

def main():
    sh = conectar_db()
    if not sh: return

    # Carga Inicial
    with st.spinner('🔄 Sincronizando datos con Google Sheets...'):
        data = cargar_datos_completos(sh)
        # Procesamiento
        master_stock, master_buy = procesar_inventario_avanzado(data['df_inv'], data['df_ven'], data['df_prov'])

    st.title("🐾 Bigotes & Paticas | Nexus Pro")

    # KPIs Principales
    k1, k2, k3, k4 = st.columns(4)
    valor_inv = (master_stock['Stock'] * master_stock['Costo']).sum()
    agotados = master_stock[master_stock['Estado_Stock'] == '💀 AGOTADO'].shape[0]
    
    k1.metric("Valor Inventario", f"${valor_inv:,.0f}")
    k2.metric("Referencias Agotadas", agotados, delta="Crítico" if agotados > 0 else "Todo Bien", delta_color="inverse")
    k3.metric("Total Referencias", len(master_stock))
    k4.metric("Fecha Sistema", str(date.today()))

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Inventario Visual", 
        "🛒 Generar Ordenes", 
        "📥 Bodega & Recepción", 
        "⚙️ Base de Datos"
    ])

    # --- TAB 1: VISUALIZACIÓN ---
    with tab1:
        st.subheader("Estado Actual del Inventario")
        col_graf, col_data = st.columns([2, 1])
        
        with col_graf:
            fig = px.treemap(master_stock, path=['Categoria', 'Estado_Stock', 'Nombre'], values='Stock',
                             color='Estado_Stock', color_discrete_map={'💀 AGOTADO':'red', '🚨 Pedir':'orange', '✅ OK':'green'},
                             title="Mapa de Calor de Stock por Categoría")
            st.plotly_chart(fig, use_container_width=True)
            
        with col_data:
            st.write("📋 **Productos Críticos**")
            criticos = master_stock[master_stock['Estado_Stock'] != '✅ OK'][['ID_Producto','Nombre', 'Stock', 'Estado_Stock']]
            st.dataframe(criticos, use_container_width=True, hide_index=True)

    # --- TAB 2: GENERAR ORDENES (FLUJO 1) ---
    with tab2:
        st.subheader("Generador de Pedidos Inteligente")
        
        # 1. Seleccionar Proveedor
        provs = sorted(master_buy['Nombre_Proveedor'].unique().tolist())
        sel_prov = st.selectbox("Seleccionar Proveedor:", provs)
        
        # 2. Datos Automáticos (Filtrados)
        df_prov_active = master_buy[master_buy['Nombre_Proveedor'] == sel_prov].copy()
        
        # 3. Selector Manual de Productos
        with st.expander("➕ Agregar producto manual (que no está sugerido)"):
            all_products = master_buy['Nombre'].unique().tolist()
            add_prods = st.multiselect("Buscar producto:", all_products)
            if add_prods:
                # Buscar filas de los manuales (priorizando el proveedor actual si existe, si no genérico)
                manual_rows = master_buy[master_buy['Nombre'].isin(add_prods)].copy()
                # Forzar que aparezcan con al menos 1 caja
                manual_rows['Cajas_Sugeridas'] = manual_rows['Cajas_Sugeridas'].replace(0, 1)
                # Combinar
                df_editor_source = pd.concat([df_prov_active[df_prov_active['Cajas_Sugeridas']>0], manual_rows]).drop_duplicates(subset=['ID_Producto'])
            else:
                df_editor_source = df_prov_active[df_prov_active['Cajas_Sugeridas'] > 0]

        # 4. Editor de Orden
        if df_editor_source.empty:
            st.info("No hay sugerencias automáticas para este proveedor. Agrega productos manualmente.")
            orden_final = pd.DataFrame()
        else:
            st.write("Verifica las cantidades antes de procesar:")
            orden_final = st.data_editor(
                df_editor_source[['ID_Producto', 'Nombre', 'Stock', 'Cajas_Sugeridas', 'Factor_Pack', 'Costo_Proveedor']],
                column_config={
                    "Cajas_Sugeridas": st.column_config.NumberColumn("Cajas a Pedir", min_value=1, step=1),
                    "Costo_Proveedor": st.column_config.NumberColumn("Costo Pack", format="$%.2f"),
                    "ID_Producto": st.column_config.TextColumn("ID", disabled=True),
                    "Nombre": st.column_config.TextColumn("Producto", disabled=True),
                },
                hide_index=True,
                use_container_width=True,
                key="editor_orden"
            )

        # 5. Acciones de Guardado
        if not orden_final.empty:
            total_orden = (orden_final['Cajas_Sugeridas'] * orden_final['Factor_Pack'] * orden_final['Costo_Proveedor']).sum()
            st.metric("Total Orden Estimada", f"${total_orden:,.0f}")
            
            c1, c2, c3 = st.columns(3)
            email_prov = df_prov_active['Email'].iloc[0] if not df_prov_active.empty else ""
            
            with c1:
                dest = st.text_input("Email Destino", value=email_prov)
                if st.button("📧 Enviar y Guardar"):
                    ok, msg = enviar_correo(dest, sel_prov, orden_final)
                    if ok:
                        guardar_orden(data['ws_ord'], sel_prov, orden_final, total_orden)
                        st.success("Orden enviada y guardada exitosamente.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")
            
            with c2:
                tel = st.text_input("WhatsApp (Solo números)", placeholder="57300...")
                if st.button("📱 Link WhatsApp + Guardar"):
                    link = link_whatsapp(tel, sel_prov, orden_final)
                    if link:
                        guardar_orden(data['ws_ord'], sel_prov, orden_final, total_orden)
                        st.markdown(f"[Haz click para abrir WhatsApp]({link})", unsafe_allow_html=True)
                        st.success("Orden guardada. Abre el link arriba.")
            
            with c3:
                st.write("")
                st.write("")
                if st.button("💾 Solo Guardar (Sin Enviar)"):
                    guardar_orden(data['ws_ord'], sel_prov, orden_final, total_orden)
                    st.success("Orden guardada en Historial.")
                    time.sleep(2)
                    st.rerun()

    # --- TAB 3: RECEPCIÓN (FLUJO 2) ---
    with tab3:
        st.subheader("Recepción de Mercancía (Bodega)")
        
        # Cargar Ordenes Pendientes
        pendientes = data['df_ord'][data['df_ord']['Estado'] == 'Pendiente']
        
        if pendientes.empty:
            st.success("¡Todo al día! No hay órdenes pendientes de recepción.")
        else:
            orden_selec = st.selectbox("Seleccionar Orden Pendiente:", 
                                       pendientes['ID_Orden'] + " | " + pendientes['Proveedor'] + " | $" + pendientes['Total_Dinero'].astype(str))
            
            if orden_selec:
                id_orden_act = orden_selec.split(" | ")[0]
                row_orden = pendientes[pendientes['ID_Orden'] == id_orden_act].iloc[0]
                
                st.info(f"Recibiendo Orden: **{id_orden_act}** del proveedor **{row_orden['Proveedor']}**")
                
                # Mostrar Items Esperados
                try:
                    items_dict = json.loads(row_orden['Items_JSON'])
                    df_items_esp = pd.DataFrame(items_dict)
                    st.table(df_items_esp[['ID_Producto', 'Nombre', 'Cajas_Sugeridas']])
                except:
                    st.error("Error al leer JSON de items.")
                    df_items_esp = pd.DataFrame()

                st.markdown("---")
                st.write("📝 **Datos de Factura Real**")
                
                col_r1, col_r2, col_r3 = st.columns(3)
                folio_factura = col_r1.text_input("Folio / Número Factura")
                fecha_emision = col_r2.date_input("Fecha Emisión Factura")
                costo_real = col_r3.number_input("Costo Total Factura", min_value=0.0)
                
                confirmar = st.checkbox("Confirmo que he contado la mercancía física y coincide (o ajustaré stock manual).")
                
                if st.button("✅ PROCESAR ENTRADA DE MERCANCÍA", type="primary", disabled=not confirmar):
                    with st.spinner("Actualizando Inventario y Cerrando Orden..."):
                        # 1. Calcular Lead Time
                        fecha_orden = pd.to_datetime(row_orden['Fecha_Orden']).date()
                        dias_entrega = (date.today() - fecha_orden).days
                        
                        # 2. Actualizar Inventario (Grave Loop)
                        logs = []
                        for item in items_dict:
                            prod_id = item['ID_Producto']
                            cajas = float(item['Cajas_Sugeridas'])
                            # Necesitamos saber el factor pack para sumar unidades
                            # Buscamos en el dataframe maestro cargado
                            info_prod = master_buy[master_buy['ID_Producto'] == prod_id]
                            if not info_prod.empty:
                                factor = float(info_prod['Factor_Pack'].values[0])
                                unidades_sumar = cajas * factor
                                
                                # Actualizar GSheets (Función Auxiliar)
                                exito_upd = actualizar_stock_gsheets(data['ws_inv'], prod_id, unidades_sumar)
                                if exito_upd:
                                    logs.append(f"✅ {prod_id}: +{unidades_sumar} unds")
                                else:
                                    logs.append(f"❌ {prod_id}: Error al buscar ID")
                        
                        # 3. Guardar en Historial Recepciones
                        nueva_recepcion = [
                            str(date.today()),          # Fecha_Recepcion
                            folio_factura,              # Folio_Factura
                            row_orden['Proveedor'],     # Proveedor
                            str(fecha_emision),         # Fecha_Emision
                            dias_entrega,               # Dias_Entrega
                            len(items_dict),            # Total_Items
                            costo_real                  # Total_Costo
                        ]
                        data['ws_recep'].append_row(nueva_recepcion)
                        
                        # 4. Actualizar Estado Orden a "Recibido"
                        # Buscar la celda del ID y actualizar fila
                        cell = data['ws_ord'].find(id_orden_act)
                        if cell:
                            # Asumiendo orden columnas: ID, Prov, Fecha, Items, Total, ESTADO(6), FECHA_RECEP(7), LEAD(8)
                            data['ws_ord'].update_cell(cell.row, 6, "Recibido")
                            data['ws_ord'].update_cell(cell.row, 7, str(date.today()))
                            data['ws_ord'].update_cell(cell.row, 8, dias_entrega)
                        
                        st.success("¡Recepción Completada!")
                        st.write("Log de Actualización:")
                        st.write(logs)
                        time.sleep(3)
                        st.rerun()

    # --- TAB 4: DATOS RAW ---
    with tab4:
        st.dataframe(master_buy)

# ==========================================
# 6. FUNCIONES AUXILIARES DE ESCRITURA
# ==========================================

def guardar_orden(ws_ord, proveedor, df_orden, total):
    """Guarda la orden generada en la hoja Historial_Ordenes"""
    # Preparar JSON para la columna Items_JSON
    items_list = df_orden[['ID_Producto', 'Nombre', 'Cajas_Sugeridas', 'Costo_Proveedor']].to_dict('records')
    items_json = json.dumps(items_list)
    
    id_unico = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    
    # Columnas: ID_Orden, Proveedor, Fecha_Orden, Items_JSON, Total_Dinero, Estado, Fecha_Recepcion, Lead_Time_Real, Calificacion
    fila = [
        id_unico,
        proveedor,
        str(date.today()),
        items_json,
        total,
        "Pendiente",
        "", # Fecha Recep vacía
        "", # Lead Time vacío
        ""  # Calificacion vacía
    ]
    ws_ord.append_row(fila)

def actualizar_stock_gsheets(ws_inv, id_producto, unidades_sumar):
    """Busca el ID en la hoja Inventario y suma las unidades a la columna Stock"""
    try:
        # Buscar la celda que contiene el ID
        cell = ws_inv.find(id_producto)
        if cell:
            # Asumimos que Stock es la columna 4 (D) según tu estructura:
            # ID(1), SKU(2), Nombre(3), Stock(4), ...
            col_stock = 4 
            stock_actual_val = ws_inv.cell(cell.row, col_stock).value
            
            # Limpiar valor actual
            try:
                stock_actual = float(stock_actual_val)
            except:
                stock_actual = 0.0
            
            nuevo_stock = stock_actual + unidades_sumar
            ws_inv.update_cell(cell.row, col_stock, nuevo_stock)
            return True
        else:
            return False
    except Exception as e:
        print(f"Error update gsheets: {e}")
        return False

if __name__ == "__main__":
    main()
