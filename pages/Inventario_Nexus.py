import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
import json
import uuid
import time
import io
from datetime import datetime, timedelta, date
from urllib.parse import quote
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from BigotesyPaticas import normalizar_id_producto

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================

st.set_page_config(
    page_title="Bigotes & Paticas | Nexus Pro WMS",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PERSONALIZADOS (CIAN #187f77 Y NARANJA #f5a641) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    
    :root {
        --primary-color: #187f77;
        --accent-color: #f5a641;
        --bg-light: #f0fdfc;
    }

    /* Títulos y Encabezados */
    h1, h2, h3 { color: #187f77 !important; }
    
    /* Métricas */
    div[data-testid="metric-container"] {
        background: #ffffff;
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #187f77;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div[data-testid="metric-container"] label { color: #187f77; font-weight: 600; }
    
    /* Botones */
    .stButton>button {
        border-radius: 8px;
        font-weight: 700;
        border: 2px solid #187f77;
        color: #187f77;
        background-color: white;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #187f77;
        color: white;
        border-color: #187f77;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #e0f2f1;
        border-radius: 8px 8px 0 0;
        padding: 0 20px;
        font-weight: 600;
        color: #187f77;
    }
    .stTabs [aria-selected="true"] {
        background-color: #187f77 !important;
        color: white !important;
    }
    
    /* Dataframe y Tablas */
    div[data-testid="stDataFrame"] { border: 1px solid #e0f2f1; }
    
    /* Input Fields */
    .stTextInput > div > div > input { border-radius: 8px; }
    
    /* Custom Box for Totals */
    .total-box {
        background-color: #e0f2f1;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #187f77;
        text-align: right;
        margin-bottom: 20px;
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

def get_worksheet_safe(sh, name, headers, retries=3, delay=2):
    for intento in range(retries):
        try:
            return sh.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=name, rows=1000, cols=max(len(headers), 20))
            ws.append_row(headers)
            return ws
        except gspread.exceptions.APIError:
            if intento == retries - 1:
                raise
            time.sleep(delay * (intento + 1))

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
    # Columnas exactas requeridas
    cols_inv = ['ID_Producto', 'SKU_Proveedor', 'Nombre', 'Stock', 'Precio', 'Costo', 'Categoria']
    cols_ven = ['ID_Venta','Fecha','Cedula_Cliente','Nombre_Cliente','Tipo_Entrega',
                'Direccion_Envio','Estado_Envio','Metodo_Pago','Banco_Destino',
                'Total','Items','Items_Detalle','Costo_Total','Mascota']
    cols_prov = ['ID_Proveedor', 'Nombre_Proveedor', 'SKU_Proveedor', 'SKU_Interno', 'Factor_Pack', 'Ultima_Actualizacion', 'Email', 'Costo_Proveedor']
    cols_ord = ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total_Dinero', 'Estado', 'Fecha_Recepcion', 'Lead_Time_Real', 'Calificacion']
    cols_recep = ['Fecha_Recepcion', 'Folio_Factura', 'Proveedor', 'Fecha_Emision_Factura', 'Dias_Entrega', 'Total_Items', 'Total_Costo']
    cols_ajustes = ['ID_Ajuste', 'Fecha', 'ID_Producto', 'Nombre', 'Stock_Anterior', 'Conteo_Fisico', 'Diferencia', 'Tipo_Movimiento', 'Usuario']

    # Obtener Hojas
    ws_inv = get_worksheet_safe(sh, "Inventario", cols_inv)
    ws_ven = get_worksheet_safe(sh, "Ventas", cols_ven)
    ws_prov = get_worksheet_safe(sh, "Maestro_Proveedores", cols_prov)
    ws_ord = get_worksheet_safe(sh, "Historial_Ordenes", cols_ord)
    ws_recep = get_worksheet_safe(sh, "Historial_Recepciones", cols_recep)
    ws_ajustes = get_worksheet_safe(sh, "Historial_Ajustes", cols_ajustes)

    # DataFrames
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    df_prov = pd.DataFrame(ws_prov.get_all_records())
    df_ord = pd.DataFrame(ws_ord.get_all_records())
    
    # --- LIMPIEZA Y NORMALIZACIÓN ---
    
    # 1. Inventario
    if not df_inv.empty:
        # Asegurar columnas
        for c in cols_inv: 
            if c not in df_inv.columns: df_inv[c] = ""
        
        df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
        df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
        df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
        df_inv['ID_Producto'] = df_inv['ID_Producto'].astype(str).str.strip()
        df_inv['ID_Producto_Norm'] = df_inv['ID_Producto'].apply(normalizar_id_producto)
        # Drop duplicates para la lógica, pero mantenemos referencia al WS
        df_inv.drop_duplicates(subset=['ID_Producto'], keep='first', inplace=True)
    else:
        df_inv = pd.DataFrame(columns=cols_inv)

    # 2. Proveedores
    if not df_prov.empty:
        for c in cols_prov:
            if c not in df_prov.columns: df_prov[c] = ""
        df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
        df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)
        df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str).str.strip()
        df_prov['Nombre_Proveedor'] = df_prov['Nombre_Proveedor'].astype(str).str.strip()
    else:
        df_prov = pd.DataFrame(columns=cols_prov)

    # 3. Ordenes
    if not df_ord.empty:
        for c in cols_ord:
            if c not in df_ord.columns: df_ord[c] = ""
        df_ord['Total_Dinero'] = df_ord['Total_Dinero'].apply(clean_currency)
    else:
        df_ord = pd.DataFrame(columns=cols_ord)

    # 4. Ventas
    if not df_ven.empty:
        for c in cols_ven:
            if c not in df_ven.columns: df_ven[c] = ""
        df_ven['Costo_Total'] = pd.to_numeric(df_ven['Costo_Total'], errors='coerce').fillna(0)
    else:
        df_ven = pd.DataFrame(columns=cols_ven)

    return {
        "df_inv": df_inv, "ws_inv": ws_inv,
        "df_ven": df_ven, "ws_ven": ws_ven,
        "df_prov": df_prov, "ws_prov": ws_prov,
        "df_ord": df_ord, "ws_ord": ws_ord,
        "ws_recep": ws_recep, "ws_ajustes": ws_ajustes
    }

# ==========================================
# 3. LÓGICA DE NEGOCIO Y EXCEL
# ==========================================

def procesar_inventario_avanzado(df_inv, df_ven, df_prov):
    # 1. Análisis de Ventas (90 días)
    if not df_ven.empty:
        df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
        cutoff = datetime.now() - timedelta(days=90)
        ven_recent = df_ven[df_ven['Fecha'] >= cutoff]
        
        stats = {}
        for _, row in ven_recent.iterrows():
            items_str = str(row.get('Items', ''))
            lista = items_str.split(',')
            for item in lista:
                nombre_clean = item.strip()
                # POS usa formato "2xNombreProducto"
                if 'x' in nombre_clean:
                    nombre_clean = nombre_clean.split('x', 1)[1].strip()
                if '(' in nombre_clean:
                    nombre_clean = nombre_clean.split('(')[0].strip()
                if nombre_clean:
                    stats[nombre_clean] = stats.get(nombre_clean, 0) + 1
        
        df_sales = pd.DataFrame(list(stats.items()), columns=['Nombre', 'Ventas_90d'])
    else:
        df_sales = pd.DataFrame(columns=['Nombre', 'Ventas_90d'])

    # 2. MERGE INVENTARIO + VENTAS
    if not df_inv.empty and 'Nombre' in df_inv.columns:
        master = pd.merge(df_inv, df_sales, on='Nombre', how='left').fillna({'Ventas_90d': 0})
    else:
        master = df_inv.copy()
        master['Ventas_90d'] = 0

    # 3. Cálculos de Stock
    master['Velocidad_Diaria'] = master['Ventas_90d'] / 90
    master['Dias_Cobertura'] = np.where(master['Velocidad_Diaria'] > 0, master['Stock'] / master['Velocidad_Diaria'], 999)
    
    master['Estado_Stock'] = np.select(
        [master['Stock'] == 0, master['Dias_Cobertura'] <= 20, master['Dias_Cobertura'] > 20],
        ['💀 AGOTADO', '🚨 Pedir', '✅ OK'], default='✅ OK'
    )

    master['Stock_Objetivo'] = master['Velocidad_Diaria'] * 45
    master['Faltante_Unidades'] = (master['Stock_Objetivo'] - master['Stock']).clip(lower=0)

    # 4. TRATAMIENTO DE PROVEEDORES
    if not df_prov.empty:
        df_prov_unico = df_prov.sort_values('Costo_Proveedor', ascending=True).drop_duplicates(subset=['SKU_Interno'], keep='first')
        master_unico = pd.merge(master, df_prov_unico, left_on='ID_Producto', right_on='SKU_Interno', how='left')
        master_buy = pd.merge(master, df_prov, left_on='ID_Producto', right_on='SKU_Interno', how='left')
    else:
        master_unico = master.copy()
        master_buy = master.copy()
        for df in [master_unico, master_buy]:
            df['Nombre_Proveedor'] = 'Genérico'
            df['Factor_Pack'] = 1
            df['Costo_Proveedor'] = df['Costo']
            df['Email'] = ''

    # Limpieza final
    for df in [master_unico, master_buy]:
        df['Nombre_Proveedor'] = df['Nombre_Proveedor'].fillna('Sin Asignar')
        df['Factor_Pack'] = df['Factor_Pack'].fillna(1).replace(0, 1)
        df['Costo_Proveedor'] = np.where(df['Costo_Proveedor'] > 0, df['Costo_Proveedor'], df['Costo'])
        df['Cajas_Sugeridas'] = np.ceil(df['Faltante_Unidades'] / df['Factor_Pack'])

    return master_unico, master_buy

def generar_excel_pro(df_data, nombre_hoja="Reporte"):
    """Genera un archivo Excel profesional con formatos y estilos."""
    output = io.BytesIO()
    
    # Crear el escritor de Pandas usando xlsxwriter
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_data.to_excel(writer, sheet_name=nombre_hoja, index=False)
        
        workbook = writer.book
        worksheet = writer.sheets[nombre_hoja]
        
        # Formatos
        header_fmt = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top', 
            'fg_color': '#187f77', 'font_color': '#FFFFFF', 'border': 1
        })
        currency_fmt = workbook.add_format({'num_format': '$#,##0', 'border': 1})
        num_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1})
        base_fmt = workbook.add_format({'border': 1})
        
        # Aplicar formato a headers
        for col_num, value in enumerate(df_data.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            
            # Anchos automáticos estimados
            col_width = max(len(str(value)) + 2, 12)
            worksheet.set_column(col_num, col_num, col_width)

        # Aplicar formato a columnas de Dinero
        money_cols = ['Precio', 'Costo', 'Total', 'Valor', 'Costo_Proveedor']
        for i, col in enumerate(df_data.columns):
            if col in money_cols or 'Precio' in col or 'Costo' in col or 'Valor' in col:
                worksheet.set_column(i, i, 15, currency_fmt)
            elif 'Stock' in col or 'Ventas' in col or 'Diferencia' in col or 'Conteo' in col:
                worksheet.set_column(i, i, 12, num_fmt)
            else:
                worksheet.set_column(i, i, 20, base_fmt)
                
    output.seek(0)
    return output

# ==========================================
# 4. UTILS: COMUNICACIÓN Y DB
# ==========================================

def enviar_correo(destinatario, proveedor, df_orden):
    if not destinatario or "@" not in destinatario: return False, "Correo inválido"
    try:
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]
        
        filas = ""
        total = 0
        for _, row in df_orden.iterrows():
            sub = row['Cajas_Sugeridas'] * row['Factor_Pack'] * row['Costo_Proveedor']
            total += sub
            filas += f"""<tr style="border-bottom:1px solid #ddd;">
                <td style="padding:8px;">{row['Nombre']}</td>
                <td style="padding:8px;text-align:center;">{int(row['Cajas_Sugeridas'])}</td>
                <td style="padding:8px;text-align:right;">${sub:,.0f}</td>
            </tr>"""
            
        html = f"""
        <div style="font-family:sans-serif; color:#333;">
            <h2 style="color:#187f77;">🐾 Bigotes y Paticas | Solicitud de Pedido</h2>
            <p>Hola <b>{proveedor}</b>, adjunto orden de compra:</p>
            <table style="width:100%; border-collapse:collapse; margin-top:10px;">
                <tr style="background:#187f77; color:white;">
                    <th style="padding:10px; text-align:left;">Producto</th>
                    <th style="padding:10px;">Cajas</th>
                    <th style="padding:10px; text-align:right;">Subtotal</th>
                </tr>
                {filas}
                <tr>
                    <td colspan="2" style="padding:10px; text-align:right;"><b>TOTAL ESTIMADO:</b></td>
                    <td style="padding:10px; text-align:right; color:#f5a641; font-size:18px;"><b>${total:,.0f}</b></td>
                </tr>
            </table>
        </div>
        """
        
        msg = MIMEMultipart()
        msg['Subject'] = f"Pedido Bigotes y Paticas ({date.today()})"
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
    txt = f"👋 Hola *{proveedor}*, pedido de *Bigotes y Paticas* 🐾:\n\n"
    for _, row in df_orden.iterrows():
        sub = row['Cajas_Sugeridas'] * row['Factor_Pack'] * row['Costo_Proveedor']
        total += sub
        txt += f"📦 {int(row['Cajas_Sugeridas'])} cj - {row['Nombre']}\n"
    txt += f"\n💰 *Total Aprox: ${total:,.0f}*\nQuedamos atentos. ¡Gracias!"
    return f"https://wa.me/{numero}?text={quote(txt)}"

# ==========================================
# 5. UI PRINCIPAL
# ==========================================

def main():
    sh = conectar_db()
    if not sh: return

    # Carga Inicial
    with st.spinner('🐾 Sincronizando sistema Nexus WMS...'):
        data = cargar_datos_completos(sh)
        master_unico, master_buy = procesar_inventario_avanzado(data['df_inv'], data['df_ven'], data['df_prov'])
        ventas_dict = ventas_por_producto(data['df_ven'], data['df_inv'])
        sugerencias = sugerencias_compra(data['df_inv'], ventas_dict)

    # HEADER
    st.title("🐾 Bigotes & Paticas | Nexus WMS")
    st.markdown(f"**Fecha Sistema:** {date.today()} | **Usuario:** Admin")

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    valor_inv = (master_unico['Stock'] * master_unico['Costo']).sum()
    agotados = master_unico[master_unico['Estado_Stock'] == '💀 AGOTADO'].shape[0]
    
    k1.metric("💰 Valor Inventario", f"${valor_inv:,.0f}")
    k2.metric("⚠️ Referencias Agotadas", agotados, delta="Atención" if agotados > 0 else "OK", delta_color="inverse")
    k3.metric("📦 Referencias Totales", len(master_unico))
    k4.metric("📉 Tasa Venta (90d)", f"{int(master_unico['Ventas_90d'].sum())} unds")

    # TABS
    tabs = st.tabs(["📊 Inventario y Auditoría", "🛒 Generar Pedidos", "📥 Recepción Bodega", "💾 Base de Datos Maestra"])

    # --- TAB 1: INVENTARIO CONTEO FÍSICO Y CREACIÓN ---
    with tabs[0]:
        st.subheader("📋 Control de Inventario & Auditoría")
        
        col_ctrl, col_act = st.columns([3, 1])
        
        # 1. Agregar Producto Nuevo
        with col_ctrl.expander("✨ Agregar Nuevo Producto (Alta en Sistema)"):
            with st.form("nuevo_prod_form"):
                c1, c2, c3 = st.columns(3)
                nuevo_nombre = c1.text_input("Nombre Producto")
                nuevo_sku = c2.text_input("ID/Código Barras")
                nuevo_cat = c3.selectbox("Categoría", ["Alimento Seco", "Húmedo", "Accesorios", "Farmacia", "Higiene"])
                
                c4, c5, c6 = st.columns(3)
                nuevo_costo = c4.number_input("Costo Unitario ($)", min_value=0.0)
                nuevo_precio = c5.number_input("Precio Venta ($)", min_value=0.0)
                nuevo_stock = c6.number_input("Stock Inicial", min_value=0, step=1)
                
                if st.form_submit_button("💾 Crear Producto"):
                    if nuevo_nombre and nuevo_sku:
                        # Verificar si existe
                        if nuevo_sku in data['df_inv']['ID_Producto'].values:
                            st.error("❌ El ID de Producto ya existe.")
                        else:
                            with st.spinner("Creando ficha de producto..."):
                                # Inventario
                                row_inv = [nuevo_sku, "", nuevo_nombre, nuevo_stock, nuevo_precio, nuevo_costo, nuevo_cat]
                                data['ws_inv'].append_row(row_inv)
                                # Si hay stock inicial, registrar ajuste inicial
                                if nuevo_stock > 0:
                                    row_ajuste = [str(uuid.uuid4())[:8], str(date.today()), nuevo_sku, nuevo_nombre, 0, nuevo_stock, nuevo_stock, "Alta Inicial", "Admin"]
                                    data['ws_ajustes'].append_row(row_ajuste)
                                
                                st.success("¡Producto creado exitosamente!")
                                time.sleep(1.5)
                                st.rerun()
                    else:
                        st.warning("Nombre y ID son obligatorios.")

        st.divider()

        # 2. Tabla de Auditoría (Edición Masiva)
        st.markdown("### 🕵️ Auditoría de Stock (Solo productos en Bodega)")
        st.info("Mostrando únicamente productos con **Stock > 0** para facilitar el conteo.")

        # Preparamos dataframe para edición
        df_audit = master_unico[['ID_Producto', 'Nombre', 'Categoria', 'Stock', 'Costo']].copy()
        
        # --- FILTRO SOLICITADO: SOLO STOCK POSITIVO ---
        df_audit = df_audit[df_audit['Stock'] > 0]
        # ----------------------------------------------

        df_audit.rename(columns={'Stock': 'Sistema'}, inplace=True)
        df_audit['Conteo_Fisico'] = df_audit['Sistema']
        df_audit['Diferencia'] = 0
        df_audit['Acción'] = "✅ OK"

        # Configuración del Editor
        edited_df = st.data_editor(
            df_audit,
            key="audit_editor",
            use_container_width=True,
            column_config={
                "ID_Producto": st.column_config.TextColumn("SKU", disabled=True),
                "Nombre": st.column_config.TextColumn("Producto", disabled=True, width="large"),
                "Sistema": st.column_config.NumberColumn("Stock Sistema", disabled=True),
                "Conteo_Fisico": st.column_config.NumberColumn("🔢 Conteo Físico", min_value=0, step=1, required=True),
                "Diferencia": st.column_config.NumberColumn("Diff", disabled=True),
                "Acción": st.column_config.TextColumn("Estado", disabled=True),
                "Costo": st.column_config.NumberColumn("Costo Unit", format="$%.2f", disabled=True)
            },
            hide_index=True
        )

        # Recalcular diferencias
        edited_df['Diferencia'] = edited_df['Conteo_Fisico'] - edited_df['Sistema']

        cambios = edited_df[edited_df['Conteo_Fisico'] != edited_df['Sistema']].copy()
        cambios['Diferencia'] = cambios['Conteo_Fisico'] - cambios['Sistema']
        
        if not cambios.empty:
            st.warning(f"⚠️ Se han detectado {len(cambios)} discrepancias en el inventario.")
            
            # Vista previa de cambios
            st.dataframe(cambios[['Nombre', 'Sistema', 'Conteo_Fisico', 'Diferencia']], hide_index=True)
            
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("✅ CONFIRMAR Y GUARDAR AJUSTES", type="primary", use_container_width=True):
                with st.spinner("Actualizando Inventario en la Nube..."):
                    logs = []
                    errores = 0
                    
                    for idx, row in cambios.iterrows():
                        try:
                            # 1. Actualizar Stock en Hoja Inventario
                            # Buscamos celda por ID
                            cell = data['ws_inv'].find(str(row['ID_Producto']))
                            if cell:
                                # Asumiendo columna 4 es Stock (Verificar indices en funcion carga)
                                # Cols: ID(1), SKU(2), Nombre(3), Stock(4)...
                                data['ws_inv'].update_cell(cell.row, 4, int(row['Conteo_Físico']))
                                
                                # 2. Registrar en Historial Ajustes
                                tipo = "Faltante" if row['Diferencia'] < 0 else "Sobrante"
                                log_row = [
                                    str(uuid.uuid4())[:8], 
                                    str(date.today()), 
                                    str(row['ID_Producto']), 
                                    row['Nombre'], 
                                    int(row['Sistema']), 
                                    int(row['Conteo_Fisico']), 
                                    int(row['Diferencia']), 
                                    tipo, 
                                    "Admin"
                                ]
                                data['ws_ajustes'].append_row(log_row)
                                logs.append(f"{row['Nombre']}: {row['Diferencia']}")
                            else:
                                errores += 1
                        except Exception as e:
                            st.error(f"Error actualizando {row['Nombre']}: {e}")
                            errores += 1
                    
                    if errores == 0:
                        st.balloons()
                        st.success("¡Inventario sincronizado perfectamente!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.warning(f"Proceso completado con {errores} errores.")

        # 4. Descarga Reporte Excel
        st.markdown("---")
        st.subheader("📂 Reportes Profesionales")
        
        excel_file = generar_excel_pro(master_unico, "Inventario_General")
        
        st.download_button(
            label="⬇️ Descargar Inventario Excel (.xlsx)",
            data=excel_file,
            file_name=f"Inventario_Bigotes_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # --- TAB 2: COMPRAS ---
    with tabs[1]:
        st.subheader("🛒 Sugerencias de Compra Global (Todos los Productos)")

        # Filtrar solo productos con faltante > 0
        df_sugerencias = master_buy[master_buy['Faltante_Unidades'] > 0].copy()
        df_sugerencias = df_sugerencias.sort_values(['Nombre_Proveedor', 'Nombre'])

        # Agrega columna para seleccionar productos
        df_sugerencias['Seleccionar'] = False

        # Editor para seleccionar productos
        edited = st.data_editor(
            df_sugerencias[['Seleccionar', 'ID_Producto_Norm', 'Nombre', 'Stock', 'Ventas_90d', 'Faltante_Unidades', 'Nombre_Proveedor', 'Costo_Proveedor']],
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
                "ID_Producto_Norm": st.column_config.TextColumn("SKU", disabled=True),
                "Nombre": st.column_config.TextColumn("Producto", disabled=True, width="large"),
                "Stock": st.column_config.NumberColumn("Stock", disabled=True),
                "Ventas_90d": st.column_config.NumberColumn("Ventas 90d", disabled=True),
                "Faltante_Unidades": st.column_config.NumberColumn("Faltante", disabled=True),
                "Nombre_Proveedor": st.column_config.TextColumn("Proveedor", disabled=True),
                "Costo_Proveedor": st.column_config.NumberColumn("Costo", format="$%.0f", disabled=True),
            },
            use_container_width=True,
            hide_index=True,
            key="editor_sugerencias"
        )

        # Filtra los seleccionados
        seleccionados = edited[edited['Seleccionar']]

        if not seleccionados.empty:
            st.success(f"{len(seleccionados)} productos seleccionados para orden de compra.")
            # Agrupa por proveedor y muestra botón para generar orden por proveedor
            for prov, df_prov in seleccionados.groupby('Nombre_Proveedor'):
                st.markdown(f"### Orden de compra para: {prov}")
                st.dataframe(df_prov[['ID_Producto_Norm', 'Nombre', 'Faltante_Unidades', 'Costo_Proveedor']], use_container_width=True)
                if st.button(f"Generar Orden para {prov}", key=f"orden_{prov}"):
                    total = (df_prov['Faltante_Unidades'] * df_prov['Costo_Proveedor']).sum()
                    guardar_orden(data['ws_ord'], prov, df_prov, total)
                    st.success(f"Orden de compra generada para {prov}")

    # --- TAB 3: RECEPCIÓN ---
    with tabs[2]:
        st.subheader("📥 Recepción de Mercancía")
        
        pendientes = data['df_ord'][data['df_ord']['Estado'] == 'Pendiente']
        
        if pendientes.empty:
            st.success("✅ Todo limpio. No hay mercancía pendiente por llegar.")
        else:
            opciones = pendientes['ID_Orden'] + " | " + pendientes['Proveedor'] + " | $" + pendientes['Total_Dinero'].astype(str)
            orden_selec = st.selectbox("Seleccionar Orden Pendiente:", opciones)
            
            if orden_selec:
                id_act = orden_selec.split(" | ")[0]
                row_orden = pendientes[pendientes['ID_Orden'] == id_act].iloc[0]
                
                try:
                    items = json.loads(row_orden['Items_JSON'])
                    st.table(pd.DataFrame(items)[['Nombre', 'Cajas_Sugeridas']])
                except:
                    st.error("Error leyendo detalles.")
                    items = []

                with st.form("form_recepcion"):
                    c_f1, c_f2 = st.columns(2)
                    folio = c_f1.text_input("Número de Factura Física")
                    fecha_fac = c_f2.date_input("Fecha de Factura")
                    
                    if st.form_submit_button("✅ INGRESAR AL INVENTARIO"):
                        with st.spinner("Actualizando stock..."):
                            log_txt = []
                            for it in items:
                                prod_info = master_unico[master_unico['ID_Producto'] == it['ID_Producto']]
                                factor = prod_info['Factor_Pack'].values[0] if not prod_info.empty else 1
                                cant_und = float(it['Cajas_Sugeridas']) * factor
                                
                                # Actualizar GSheet
                                actualizar_stock_gsheets(data['ws_inv'], it['ID_Producto'], cant_und)
                                log_txt.append(f"{it['Nombre']}: +{cant_und} unds")
                            
                            # Guardar Recepción
                            row_recep = [str(date.today()), folio, row_orden['Proveedor'], str(fecha_fac), 0, len(items), row_orden['Total_Dinero']]
                            data['ws_recep'].append_row(row_recep)
                            
                            # Cerrar Orden
                            cell = data['ws_ord'].find(id_act)
                            data['ws_ord'].update_cell(cell.row, 6, "Recibido")
                            data['ws_ord'].update_cell(cell.row, 7, str(date.today()))
                            

                            st.success("¡Inventario actualizado correctamente!")
                            st.write(log_txt)
                            time.sleep(3)
                            st.rerun()

    # --- TAB 4: BASE DE DATOS Y LOGS ---
    with tabs[3]:
        st.subheader("💾 Base de Datos & Logs")
        
        tab_bd1, tab_bd2 = st.tabs(["📦 Inventario Maestro", "🕵️ Historial Ajustes"])
        
        with tab_bd1:
            st.dataframe(
                master_unico[['ID_Producto', 'Nombre', 'Stock', 'Costo', 'Precio', 'Nombre_Proveedor', 'Estado_Stock']],
                use_container_width=True,
                hide_index=True
            )
            excel_bd = generar_excel_pro(master_unico, "Maestro_Completo")
            st.download_button("⬇️ Descargar Maestro", excel_bd, "Maestro.xlsx")
            
        with tab_bd2:
            st.markdown("##### Historial de Movimientos Manuales (Auditorías)")
            try:
                df_ajustes = pd.DataFrame(data['ws_ajustes'].get_all_records())
                if not df_ajustes.empty:
                    st.dataframe(df_ajustes, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay registros de ajustes manuales.")
            except:
                st.error("No se pudo leer la hoja de Ajustes. Verifica que exista la hoja 'Historial_Ajustes' en Google Sheets.")

def ventas_por_producto(df_ven, df_inv):
    # Extrae ventas de los últimos 30 días
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
    cutoff = datetime.now() - timedelta(days=30)
    ven_recent = df_ven[df_ven['Fecha'] >= cutoff]

    # Diccionario para sumar ventas por referencia normalizada
    ventas_dict = {}

    for _, row in ven_recent.iterrows():
        items_str = str(row.get('Items', ''))
        items_list = items_str.split(',')
        for item in items_list:
            item = item.strip()
            if 'x' in item:
                qty_str, nombre = item.split('x', 1)
                try:
                    qty = int(qty_str.strip())
                except:
                    qty = 1
                nombre = nombre.strip()
                # Buscar referencia normalizada en inventario
                match = df_inv[df_inv['Nombre'].str.upper().str.strip() == nombre.upper().strip()]
                if not match.empty:
                    ref_norm = match.iloc[0]['ID_Producto_Norm']
                    ventas_dict[ref_norm] = ventas_dict.get(ref_norm, 0) + qty
    return ventas_dict

def sugerencias_compra(df_inv, ventas_dict, dias_ventas=30, dias_stock=8, stock_seguridad=1):
    # Ventas en los últimos X días
    df_inv['Ventas_periodo'] = df_inv['ID_Producto_Norm'].map(ventas_dict).fillna(0)
    # Velocidad diaria
    df_inv['Velocidad_Diaria'] = df_inv['Ventas_periodo'] / dias_ventas
    # Stock objetivo para 8 días + stock de seguridad
    df_inv['Stock_Objetivo'] = np.ceil(df_inv['Velocidad_Diaria'] * dias_stock + stock_seguridad)
    # Faltante: lo que falta para llegar al stock objetivo
    df_inv['Faltante_Unidades'] = (df_inv['Stock_Objetivo'] - df_inv['Stock']).clip(lower=0).apply(np.ceil).astype(int)
    # Si el producto está en 0 y se ha vendido, sugerir al menos 1
    df_inv.loc[(df_inv['Stock'] == 0) & (df_inv['Ventas_periodo'] > 0), 'Faltante_Unidades'] = df_inv.loc[(df_inv['Stock'] == 0) & (df_inv['Ventas_periodo'] > 0), 'Stock_Objetivo'].astype(int)
    return df_inv[['ID_Producto', 'ID_Producto_Norm', 'Nombre', 'Stock', 'Ventas_periodo', 'Velocidad_Diaria', 'Stock_Objetivo', 'Faltante_Unidades']]

# ==========================================
# 6. FUNCIONES DE ESCRITURA
# ==========================================

def guardar_orden(ws_ord, proveedor, df_orden, total):
    items_list = df_orden[['ID_Producto', 'Nombre', 'Cajas_Sugeridas', 'Costo_Proveedor']].to_dict('records')
    id_unico = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    fila = [id_unico, proveedor, str(date.today()), json.dumps(items_list), total, "Pendiente", "", "", ""]
    ws_ord.append_row(fila)

def actualizar_stock_gsheets(ws_inv, id_producto, unidades_sumar):
    id_producto_norm = normalizar_id_producto(id_producto)
    all_rows = ws_inv.get_all_values()
    for idx, row in enumerate(all_rows):
        if idx == 0: continue  # Saltar encabezado
        if normalizar_id_producto(row[0]) == id_producto_norm:
            col_stock = 4  # Verifica que esta columna sea la correcta para tu hoja
            val_act = ws_inv.cell(idx+1, col_stock).value
            nuevo = float(val_act if val_act else 0) + unidades_sumar
            ws_inv.update_cell(idx+1, col_stock, nuevo)
            break

def normalizar_todas_las_referencias(ws_inv):
    import pandas as pd
    df = pd.DataFrame(ws_inv.get_all_records())
    if 'ID_Producto' not in df.columns:
        st.error("No se encontró la columna ID_Producto en Inventario.")
        return
    df['ID_Producto_Norm'] = df['ID_Producto'].apply(normalizar_id_producto)
    headers = ws_inv.row_values(1)
    if 'ID_Producto_Norm' not in headers:
        ws_inv.update_cell(1, len(headers)+1, 'ID_Producto_Norm')
        col_norm = len(headers)+1
    else:
        col_norm = headers.index('ID_Producto_Norm') + 1
    for i, val in enumerate(df['ID_Producto_Norm']):
        ws_inv.update_cell(i+2, col_norm, val)
    st.success("¡Referencias normalizadas en la hoja Inventario!")

@st.cache_data(ttl=60)  # o más, según tu necesidad
def leer_datos_cached(ws):
    raw = ws.get_all_values()
    # ...procesamiento igual que leer_datos...
    return df

if __name__ == "__main__":
    main()
