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

# ==========================================
# 0. FUNCIONES CORE (DEFINIDAS AL INICIO)
# ==========================================

def normalizar_id_producto(id_prod):
    """
    Normaliza SKUs para asegurar cruces perfectos entre tablas.
    Convierte a string, mayúsculas, quita espacios y caracteres raros.
    """
    if pd.isna(id_prod) or id_prod == "":
        return "SIN_ID"
    val = str(id_prod).strip().upper()
    val = val.replace(".", "").replace(",", "").replace("\t", "").replace("\n", "")
    # Quitar ceros a la izquierda si es numérico puro
    val = val.lstrip("0")
    if not val:
        return "SIN_ID"
    return val

def clean_currency(x):
    """Limpia formatos de moneda ($1,200.00 -> 1200.00)."""
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        clean = x.replace('$', '').replace(',', '').replace(' ', '').strip()
        if not clean: return 0.0
        try: return float(clean)
        except: return 0.0
    return 0.0

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================

st.set_page_config(
    page_title="Bigotes & Paticas | Nexus Pro AI",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    :root { --primary-color: #187f77; --accent-color: #f5a641; }
    h1, h2, h3 { color: #187f77 !important; }
    div[data-testid="metric-container"] {
        background: #ffffff; padding: 15px; border-radius: 12px;
        border-left: 5px solid #187f77; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stButton>button {
        border-radius: 8px; font-weight: 700; border: 2px solid #187f77;
        color: #187f77; background-color: white; transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #187f77; color: white; }
    div[data-testid="stDataFrame"] { border: 1px solid #e0f2f1; }
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
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=max(len(headers), 20))
        ws.append_row(headers)
        return ws

def cargar_datos_completos(sh):
    # --- DEFINICIÓN DE COLUMNAS OBLIGATORIAS ---
    # Esto evita el KeyError si la hoja está vacía
    cols_inv = ['ID_Producto', 'SKU_Proveedor', 'Nombre', 'Stock', 'Precio', 'Costo', 'Categoria']
    cols_ven = ['ID_Venta','Fecha','Cedula_Cliente','Nombre_Cliente','Items','Total','Costo_Total']
    cols_prov = ['ID_Proveedor', 'Nombre_Proveedor', 'SKU_Interno', 'Factor_Pack', 'Costo_Proveedor', 'Email']
    cols_ord = ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total_Dinero', 'Estado']
    
    # Obtener Hojas
    ws_inv = get_worksheet_safe(sh, "Inventario", cols_inv)
    ws_ven = get_worksheet_safe(sh, "Ventas", cols_ven)
    ws_prov = get_worksheet_safe(sh, "Maestro_Proveedores", cols_prov)
    ws_ord = get_worksheet_safe(sh, "Historial_Ordenes", cols_ord)
    ws_recep = get_worksheet_safe(sh, "Historial_Recepciones", ['Fecha', 'Folio'])
    ws_ajustes = get_worksheet_safe(sh, "Historial_Ajustes", ['Fecha', 'ID_Producto'])

    # Cargar DataFrames
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    df_prov = pd.DataFrame(ws_prov.get_all_records())
    df_ord = pd.DataFrame(ws_ord.get_all_records())

    # --- BLINDAJE DE COLUMNAS (Fix KeyError) ---
    
    # 1. Inventario
    if df_inv.empty:
        df_inv = pd.DataFrame(columns=cols_inv)
    else:
        for c in cols_inv:
            if c not in df_inv.columns: df_inv[c] = ""
    
    # 2. Proveedores
    if df_prov.empty:
        df_prov = pd.DataFrame(columns=cols_prov)
    else:
        for c in cols_prov:
            if c not in df_prov.columns: df_prov[c] = ""

    # 3. Órdenes
    if df_ord.empty:
        df_ord = pd.DataFrame(columns=cols_ord)
    else:
        for c in cols_ord:
            if c not in df_ord.columns: df_ord[c] = "" 

    # 4. Ventas
    if df_ven.empty:
        df_ven = pd.DataFrame(columns=cols_ven)

    # --- LIMPIEZA Y TIPOS DE DATOS ---
    
    # Inventario
    df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
    df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
    df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
    df_inv['ID_Producto_Norm'] = df_inv['ID_Producto'].apply(normalizar_id_producto)

    # Proveedores
    df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
    df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)
    df_prov['SKU_Interno_Norm'] = df_prov['SKU_Interno'].apply(normalizar_id_producto)
    
    # Ventas
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')

    return {
        "df_inv": df_inv, "ws_inv": ws_inv,
        "df_ven": df_ven, "ws_ven": ws_ven,
        "df_prov": df_prov, "ws_prov": ws_prov,
        "df_ord": df_ord, "ws_ord": ws_ord,
        "ws_recep": ws_recep, "ws_ajustes": ws_ajustes
    }

# ==========================================
# 3. LÓGICA DE NEGOCIO "SUPER PODEROSA"
# ==========================================

def analizar_ventas_inteligente(df_ven, df_inv):
    """Calcula ventas históricas y detecta tendencias."""
    if df_ven.empty:
        return {}

    # Filtrar últimos 90 días
    cutoff_90 = datetime.now() - timedelta(days=90)
    cutoff_30 = datetime.now() - timedelta(days=30)
    
    ven_recent = df_ven[df_ven['Fecha'] >= cutoff_90]
    
    stats = {} # { 'ID_NORM': {'v90': x, 'v30': y} }

    # Mapeo de Nombre a ID Normalizado para velocidad
    mapa_nombre_id = dict(zip(df_inv['Nombre'].str.strip().str.upper(), df_inv['ID_Producto_Norm']))

    for _, row in ven_recent.iterrows():
        items_str = str(row.get('Items', ''))
        fecha_venta = row['Fecha']
        lista = items_str.split(',')
        
        for item in lista:
            # Lógica para parsear "2xNombre" o "Nombre"
            item = item.strip()
            qty = 1
            nombre_clean = item
            
            if 'x' in item:
                parts = item.split('x', 1)
                if parts[0].strip().isdigit():
                    qty = int(parts[0].strip())
                    nombre_clean = parts[1].strip()
            
            nombre_upper = nombre_clean.upper()
            
            # Buscar ID
            id_norm = mapa_nombre_id.get(nombre_upper)
            
            if id_norm:
                if id_norm not in stats:
                    stats[id_norm] = {'v90': 0, 'v30': 0}
                
                stats[id_norm]['v90'] += qty
                if fecha_venta >= cutoff_30:
                    stats[id_norm]['v30'] += qty

    return stats

def procesar_inventario_power_logic(df_inv, df_prov, stats_ventas):
    """
    Fusiona datos y aplica lógica de reabastecimiento avanzada.
    Usa numpy.where para evitar ValueError y merge con normalización.
    """
    # 1. PREPARAR DATOS PROVEEDOR
    if not df_prov.empty:
        df_prov_clean = df_prov.sort_values('Costo_Proveedor', ascending=True).drop_duplicates(subset=['SKU_Interno_Norm'], keep='first')
        
        # MERGE BLINDADO
        master = pd.merge(
            df_inv, 
            df_prov_clean[['SKU_Interno_Norm', 'Nombre_Proveedor', 'Costo_Proveedor', 'Factor_Pack']], 
            left_on='ID_Producto_Norm', 
            right_on='SKU_Interno_Norm', 
            how='left'
        )
    else:
        master = df_inv.copy()
        master['Nombre_Proveedor'] = None
        master['Costo_Proveedor'] = None
        master['Factor_Pack'] = 1

    # 2. LIMPIEZA POST-MERGE Y RELLENO
    cols_check = ['Nombre_Proveedor', 'Costo_Proveedor', 'Factor_Pack']
    for col in cols_check:
        if col not in master.columns:
            master[col] = np.nan

    # A. Nombre Proveedor
    master['Nombre_Proveedor'] = master['Nombre_Proveedor'].fillna('Generico / Sin Asignar')

    # B. Costo Proveedor (CORREGIDO CON NP.WHERE)
    master['Costo_Proveedor'] = master['Costo_Proveedor'].fillna(master['Costo'])
    master['Costo_Proveedor'] = np.where(master['Costo_Proveedor'] <= 0, master['Costo'], master['Costo_Proveedor'])

    # C. Factor Pack (CORREGIDO)
    master['Factor_Pack'] = master['Factor_Pack'].fillna(1)
    master['Factor_Pack'] = np.where(master['Factor_Pack'] <= 0, 1, master['Factor_Pack'])

    # 3. CÁLCULOS DE INTELIGENCIA DE NEGOCIO
    resultados = []
    
    for idx, row in master.iterrows():
        id_norm = row['ID_Producto_Norm']
        stock_actual = row['Stock']
        
        # Obtener stats de venta
        data_vta = stats_ventas.get(id_norm, {'v90': 0, 'v30': 0})
        v90 = data_vta['v90']
        v30 = data_vta['v30']
        
        # Velocidad Diaria
        diario_90 = v90 / 90
        diario_30 = v30 / 30
        velocidad_diaria = max(diario_90, diario_30) # Enfoque conservador
        
        # Días de Cobertura
        dias_cobertura = stock_actual / velocidad_diaria if velocidad_diaria > 0 else 999
        
        # Estado del Stock
        if stock_actual <= 0:
            estado = "💀 AGOTADO"
        elif dias_cobertura <= 15:
            estado = "🚨 CRÍTICO"
        elif dias_cobertura <= 30:
            estado = "⚠️ Bajo"
        else:
            estado = "✅ OK"
            
        # LÓGICA DE SUGERENCIA DE COMPRA
        dias_objetivo = 45 
        stock_seguridad = velocidad_diaria * 5
        
        stock_ideal = (velocidad_diaria * dias_objetivo) + stock_seguridad
        faltante_unidades = max(0, stock_ideal - stock_actual)
        
        # Ajuste a Pack
        pack = row['Factor_Pack']
        if faltante_unidades > 0:
            cajas_sugeridas = np.ceil(faltante_unidades / pack)
        else:
            cajas_sugeridas = 0
            
        unidades_a_pedir_real = cajas_sugeridas * pack
        costo_estimado = unidades_a_pedir_real * row['Costo_Proveedor']

        resultados.append({
            'ID_Producto': row['ID_Producto'],
            'ID_Producto_Norm': id_norm,   # <--- CORRECCIÓN AQUÍ: Clave unificada
            'Nombre': row['Nombre'],
            'Categoria': row['Categoria'],
            'Stock': stock_actual,
            'Costo': row['Costo'],
            'Precio': row['Precio'],
            'Proveedor': row['Nombre_Proveedor'],
            'Costo_Prov': row['Costo_Proveedor'],
            'Pack': pack,
            'Venta_90d': v90,
            'Velocidad_Diaria': round(velocidad_diaria, 2),
            'Dias_Cobertura': round(dias_cobertura, 1),
            'Estado': estado,
            'Sugerencia_Cajas': int(cajas_sugeridas),
            'Unidades_Pedir': int(unidades_a_pedir_real),
            'Inversion_Est': costo_estimado
        })
        
    return pd.DataFrame(resultados)

def generar_excel_pro(df_data, nombre_hoja="Reporte"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_data.to_excel(writer, sheet_name=nombre_hoja, index=False)
        workbook = writer.book
        worksheet = writer.sheets[nombre_hoja]
        header_fmt = workbook.add_format({'bold': True, 'fg_color': '#187f77', 'font_color': 'white', 'border': 1})
        for col_num, value in enumerate(df_data.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            worksheet.set_column(col_num, col_num, 20)
    output.seek(0)
    return output

# ==========================================
# 4. UTILS: COMUNICACIÓN Y ESCRITURA
# ==========================================

def guardar_orden_compra(ws_ord, proveedor, items_df):
    """Guarda la orden en la base de datos."""
    id_orden = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    fecha = str(date.today())
    
    # Preparar JSON ligero
    detalles = items_df[['ID_Producto', 'Nombre', 'Sugerencia_Cajas', 'Unidades_Pedir', 'Costo_Prov']].to_dict('records')
    total_dinero = items_df['Inversion_Est'].sum()
    
    # Cols: ID_Orden, Proveedor, Fecha_Orden, Items_JSON, Total_Dinero, Estado
    row = [id_orden, proveedor, fecha, json.dumps(detalles), total_dinero, "Pendiente"]
    ws_ord.append_row(row)
    return id_orden

def link_whatsapp(proveedor, df_orden):
    total = df_orden['Inversion_Est'].sum()
    txt = f"👋 Hola *{proveedor}*, pedido de *Bigotes y Paticas*:\n\n"
    for _, row in df_orden.iterrows():
        txt += f"📦 {row['Sugerencia_Cajas']} packs - {row['Nombre']}\n"
    txt += f"\n💰 Total Est: ${total:,.0f}"
    return f"https://wa.me/?text={quote(txt)}"

# ==========================================
# 5. UI PRINCIPAL
# ==========================================

def main():
    sh = conectar_db()
    if not sh: return

    # --- CARGA DE DATOS ---
    with st.spinner('🐾 Potencializando Nexus AI...'):
        data = cargar_datos_completos(sh)
        stats = analizar_ventas_inteligente(data['df_ven'], data['df_inv'])
        master_df = procesar_inventario_power_logic(data['df_inv'], data['df_prov'], stats)

    # --- DASHBOARD HEADER ---
    st.title("🐾 Bigotes & Paticas | Nexus WMS")
    
    # Métricas Globales
    c1, c2, c3, c4 = st.columns(4)
    valor_inv = (master_df['Stock'] * master_df['Costo']).sum()
    agotados = master_df[master_df['Stock'] <= 0].shape[0]
    criticos = master_df[master_df['Estado'] == '🚨 CRÍTICO'].shape[0]
    venta_proyectada = master_df['Venta_90d'].sum() / 3 # Mensual aprox
    
    c1.metric("💰 Valor Inventario", f"${valor_inv:,.0f}")
    c2.metric("💀 Agotados", agotados, delta_color="inverse")
    c3.metric("🚨 Stock Crítico", criticos, delta="Pedir Urgente" if criticos > 0 else "OK", delta_color="inverse")
    c4.metric("📈 Venta Mensual Est.", f"{int(venta_proyectada)} unds")

    tabs = st.tabs(["📊 Control & Auditoría", "🧠 Sugerencias de Compra (AI)", "📥 Recepción", "⚙️ Base de Datos"])

    # --- TAB 1: CONTROL ---
    with tabs[0]:
        st.subheader("🕵️ Auditoría de Inventario (Solo productos con stock)")
        col_op, col_filt = st.columns([2,1])
        filtro = col_filt.text_input("🔍 Buscar Producto...")

        # Filtra solo productos con stock > 0
        df_show = master_df[master_df['Stock'] > 0].copy()

        if filtro:
            df_show = df_show[
                df_show['Nombre'].str.contains(filtro, case=False, na=False) |
                df_show['ID_Producto_Norm'].str.contains(filtro, case=False, na=False)
            ]

        # Editor mostrando la referencia normalizada como SKU
        edited = st.data_editor(
            df_show[['ID_Producto_Norm', 'Nombre', 'Stock', 'Estado', 'Costo']],
            column_config={
                "ID_Producto_Norm": st.column_config.TextColumn("SKU (Norm)", disabled=True),
                "Nombre": st.column_config.TextColumn("Producto", disabled=True),
                "Stock": st.column_config.NumberColumn("Stock Real", step=1),
                "Estado": st.column_config.TextColumn("Status", disabled=True),
                "Costo": st.column_config.NumberColumn("Costo", format="$%.0f", disabled=True)
            },
            use_container_width=True,
            key="editor_inv",
            hide_index=True
        )
        if st.button("💾 Guardar Ajustes de Inventario"):
            st.info("Funcionalidad de escritura lista para configurar según tu lógica de auditoría.")

    # --- TAB 2: COMPRAS INTELIGENTES ---
    with tabs[1]:
        st.subheader("🧠 Sugerencias de Reabastecimiento (Power Logic)")
        st.info("Cálculo basado en: (Ventas 30d/90d) + (Stock Seguridad) - Stock Actual.")
        
        df_compras = master_df[master_df['Unidades_Pedir'] > 0].copy()
        df_compras = df_compras.sort_values(['Proveedor', 'Estado'])
        
        if df_compras.empty:
            st.success("✅ ¡Inventario saludable! No se requieren compras urgentes.")
        else:
            df_compras['Seleccionar'] = True
            
            compra_final = st.data_editor(
                df_compras[['Seleccionar', 'Proveedor', 'Nombre', 'Stock', 'Dias_Cobertura', 'Sugerencia_Cajas', 'Pack', 'Inversion_Est']],
                column_config={
                    "Sugerencia_Cajas": st.column_config.NumberColumn("📦 Cajas a Pedir", step=1),
                    "Inversion_Est": st.column_config.NumberColumn("Total $", format="$%.0f", disabled=True),
                    "Dias_Cobertura": st.column_config.NumberColumn("Cobertura (Días)", format="%.1f")
                },
                hide_index=True,
                use_container_width=True
            )
            
            seleccionados = compra_final[compra_final['Seleccionar'] == True]
            
            st.divider()
            st.subheader("🚀 Generar Órdenes")
            total_global = seleccionados['Inversion_Est'].sum()
            st.markdown(f"**Total a Invertir:** :green[${total_global:,.0f}]")
            
            proveedores_unicos = seleccionados['Proveedor'].unique()
            cols = st.columns(len(proveedores_unicos)) if len(proveedores_unicos) < 4 and len(proveedores_unicos) > 0 else st.columns(3)
            
            for i, prov in enumerate(proveedores_unicos):
                items_prov = seleccionados[seleccionados['Proveedor'] == prov]
                total_prov = items_prov['Inversion_Est'].sum()
                
                with cols[i % 3]:
                    with st.expander(f"🛒 {prov} (${total_prov:,.0f})", expanded=True):
                        st.dataframe(items_prov[['Nombre', 'Sugerencia_Cajas']], hide_index=True)
                        
                        c_btn1, c_btn2 = st.columns(2)
                        if c_btn1.button(f"Confirmar {prov}", key=f"btn_{prov}"):
                            id_new = guardar_orden_compra(data['ws_ord'], prov, items_prov)
                            st.success(f"Orden {id_new} creada.")
                            time.sleep(1)
                            st.rerun()
                            
                        link = link_whatsapp(prov, items_prov)
                        c_btn2.markdown(f"[📲 WhatsApp]({link})", unsafe_allow_html=True)

    # --- TAB 3: RECEPCIÓN ---
    with tabs[2]:
        st.subheader("📦 Recepción de Mercancía")
        
        if data['df_ord'].empty:
            st.info("📭 No hay historial de órdenes.")
        else:
            pendientes = data['df_ord'][data['df_ord']['Estado'] == 'Pendiente']
            
            if pendientes.empty:
                st.write("✅ No hay órdenes pendientes por recibir.")
            else:
                orden = st.selectbox("Seleccionar Orden", pendientes['ID_Orden'] + " - " + pendientes['Proveedor'])
                st.info(f"Orden seleccionada: {orden}. Sistema listo para el ingreso.")

    # --- TAB 4: DATA ---
    with tabs[3]:
        st.dataframe(master_df)
        excel = generar_excel_pro(master_df)
        st.download_button("⬇️ Descargar Maestro Completo", excel, "Bigotes_Master.xlsx")

if __name__ == "__main__":
    main()