import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta
import json
import uuid
from urllib.parse import quote

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN (NEXUS ULTRA)
# ==========================================

st.set_page_config(
    page_title="NEXUS PRO | Supply Chain AI",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS Avanzados (Modo Oscuro/Glassmorphism Híbrido)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    
    :root {
        --primary: #6366f1;
        --secondary: #8b5cf6;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --background: #f8fafc;
        --card-bg: #ffffff;
    }

    .stApp { background-color: var(--background); }

    /* Tarjetas de Métricas */
    div[data-testid="metric-container"] {
        background: var(--card-bg);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.2);
        border-color: var(--primary);
    }

    /* Tablas Profesionales */
    .stDataFrame { 
        border-radius: 12px; 
        overflow: hidden; 
        border: 1px solid #e2e8f0; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Botones */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        height: 3em;
        transition: all 0.2s;
    }
    
    /* Headers */
    h1, h2, h3 { color: #1e293b; letter-spacing: -0.5px; }
    .highlight { color: var(--primary); background: #e0e7ff; padding: 0 8px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE BASE DE DATOS (AUTO-ADAPTABLE)
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
        st.error(f"🔴 Error Crítico de Conexión: {e}")
        return None

def get_worksheet_safe(sh, name, headers):
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        # Intenta buscar hojas con nombres parecidos
        for ws in sh.worksheets():
            if name.lower() in ws.title.lower():
                return ws
        # Si no existe, la crea
        ws = sh.add_worksheet(title=name, rows=100, cols=20)
        ws.append_row(headers)
        return ws

def clean_currency(x):
    """Limpia cualquier formato de moneda a float."""
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        clean = x.replace('$', '').replace(',', '').replace(' ', '').replace('%', '').strip()
        if not clean: return 0.0
        try: return float(clean)
        except: return 0.0
    return 0.0

def normalizar_columnas(df, target_cols, aliases):
    """
    Esta función es CLAVE. Si tus columnas se llaman diferente,
    esto intenta arreglarlo automáticamente buscando sinónimos.
    """
    cols_actuales = [c.lower().strip() for c in df.columns]
    renames = {}
    
    for target in target_cols:
        target_lower = target.lower()
        if target_lower in cols_actuales:
            continue # La columna ya existe, todo bien
            
        # Buscar en alias
        found = False
        possible_names = aliases.get(target, [])
        for alias in possible_names:
            alias_lower = alias.lower()
            # Buscar coincidencia exacta en las columnas del usuario
            match = next((c for c in df.columns if c.lower().strip() == alias_lower), None)
            if match:
                renames[match] = target
                found = True
                break
        
        if not found:
            # Si no se encuentra, se crea vacía para evitar CRASH
            df[target] = 0 if 'Precio' in target or 'Costo' in target or 'Stock' in target else ""

    if renames:
        df.rename(columns=renames, inplace=True)
    return df

def cargar_datos_pro(sh):
    # Definición de esquemas y ALIAS (Sinónimos posibles en tus hojas)
    
    # 1. INVENTARIO
    alias_inv = {
        'ID_Producto': ['ID', 'SKU', 'Codigo', 'Referencia'],
        'Nombre': ['Producto', 'Descripcion', 'Item'],
        'Stock': ['Cantidad', 'Existencia', 'Unidades'],
        'Costo': ['Costo Unitario', 'Valor Compra', 'P.Costo'],
        'Precio': ['Precio Venta', 'PVP', 'Valor Venta'],
        'Categoria': ['Linea', 'Grupo', 'Familia'],
        'ID_Proveedor': ['Proveedor_ID', 'Nit_Proveedor']
    }
    
    # 2. PROVEEDORES (Aquí estaba tu error, ahora buscamos variaciones)
    alias_prov = {
        'Nombre_Proveedor': ['Proveedor', 'Empresa', 'Nombre'],
        'SKU_Interno': ['ID_Producto', 'SKU', 'Producto_Relacionado'],
        'Costo_Proveedor': ['Costo', 'Precio', 'Valor', 'Costo_Unitario', 'Precio_Lista'], # <--- AQUÍ BUSCAMOS EL COSTO
        'Factor_Pack': ['Pack', 'Unidades_Caja', 'Factor'],
        'Telefono': ['Celular', 'Movil', 'Tel', 'Whatsapp'],
        'Email': ['Correo', 'Mail']
    }

    # Cargar Hojas
    ws_inv = get_worksheet_safe(sh, "Inventario", list(alias_inv.keys()))
    ws_prov = get_worksheet_safe(sh, "Maestro_Proveedores", list(alias_prov.keys()))
    ws_ven = get_worksheet_safe(sh, "Ventas", ['ID_Venta', 'Fecha', 'Items', 'Total'])
    ws_hist = get_worksheet_safe(sh, "Historial_Ordenes", ['ID_Orden'])

    # DataFrames
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_prov = pd.DataFrame(ws_prov.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    df_hist = pd.DataFrame(ws_hist.get_all_records())

    # --- NORMALIZACIÓN Y LIMPIEZA INTELIGENTE ---
    
    # 1. Normalizar Inventario
    if not df_inv.empty:
        df_inv = normalizar_columnas(df_inv, alias_inv.keys(), alias_inv)
        # Limpieza de tipos
        df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
        df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
        df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
        df_inv['ID_Producto'] = df_inv['ID_Producto'].astype(str).str.strip()
        # Eliminar duplicados para evitar error de inventario x4
        df_inv = df_inv.drop_duplicates(subset=['ID_Producto'], keep='first')

    # 2. Normalizar Proveedores
    if not df_prov.empty:
        df_prov = normalizar_columnas(df_prov, alias_prov.keys(), alias_prov)
        df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
        df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)
        # Si SKU_Interno está vacío, intentamos usar ID_Producto si existe en el df original
        if 'ID_Producto' in df_prov.columns and 'SKU_Interno' not in df_prov.columns:
             df_prov['SKU_Interno'] = df_prov['ID_Producto']
        df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str).str.strip()

    return df_inv, df_ven, df_prov, df_hist, ws_hist

# ==========================================
# 3. CEREBRO DE NEGOCIO (ANALYTICS ENGINE)
# ==========================================

def procesar_inteligencia(df_inv, df_ven, df_prov):
    # 1. Análisis de Ventas (Velocidad)
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
    cutoff_90 = datetime.now() - timedelta(days=90)
    ven_recent = df_ven[df_ven['Fecha'] >= cutoff_90]
    
    stats = {}
    if not ven_recent.empty:
        for _, row in ven_recent.iterrows():
            items = str(row.get('Items', '')).split(',')
            for item in items:
                nombre = item.split('(')[0].strip() # Limpiar nombre "Producto (2)" -> "Producto"
                stats[nombre] = stats.get(nombre, 0) + 1

    df_sales = pd.DataFrame(list(stats.items()), columns=['Nombre', 'Ventas_90d'])
    
    # 2. Master Inventario (Base Única)
    # Hacemos Left Join por Nombre para pegar las ventas
    if 'Nombre' in df_inv.columns:
        master_inv = pd.merge(df_inv, df_sales, on='Nombre', how='left').fillna({'Ventas_90d': 0})
    else:
        master_inv = df_inv.copy()
        master_inv['Ventas_90d'] = 0

    # 3. Métricas Financieras y de Stock
    master_inv['Velocidad_Diaria'] = master_inv['Ventas_90d'] / 90
    master_inv['Valor_Stock'] = master_inv['Stock'] * master_inv['Costo']
    master_inv['Margen_Unit'] = master_inv['Precio'] - master_inv['Costo']
    master_inv['Margen_Total_Potencial'] = master_inv['Stock'] * master_inv['Margen_Unit']
    
    # Días de Inventario (DSI)
    master_inv['Dias_Inventario'] = np.where(
        master_inv['Velocidad_Diaria'] > 0, 
        master_inv['Stock'] / master_inv['Velocidad_Diaria'], 
        999 # Infinito/Estancado
    )

    # Lógica de Reabastecimiento (Punto de Reorden)
    LEAD_TIME = 15 # Días promedio entrega proveedor
    STOCK_SEGURIDAD = 7 # Días de colchón
    
    master_inv['Punto_Reorden'] = master_inv['Velocidad_Diaria'] * (LEAD_TIME + STOCK_SEGURIDAD)
    master_inv['Estado'] = np.where(master_inv['Stock'] <= master_inv['Punto_Reorden'], '🚨 Pedir', '✅ OK')
    
    # Calcular Cantidad Faltante
    master_inv['Faltante'] = (master_inv['Punto_Reorden'] * 1.5) - master_inv['Stock'] # Objetivo: tener 1.5 veces el punto de reorden
    master_inv['Faltante'] = master_inv['Faltante'].clip(lower=0)

    # 4. Master Compras (Relación Producto -> Proveedor)
    # Aquí unimos con la tabla de proveedores para saber a quién pedirle
    if not df_prov.empty:
        # Prioridad: Join por ID/SKU
        master_buy = pd.merge(master_inv, df_prov, left_on='ID_Producto', right_on='SKU_Interno', how='inner')
        # Si cost_proveedor es 0, usar costo del inventario
        master_buy['Costo_Proveedor'] = np.where(master_buy['Costo_Proveedor'] > 0, master_buy['Costo_Proveedor'], master_buy['Costo'])
    else:
        # Fallback si no hay proveedores configurados
        master_buy = master_inv.copy()
        master_buy['Nombre_Proveedor'] = 'Proveedor Genérico'
        master_buy['Costo_Proveedor'] = master_buy['Costo']
        master_buy['Factor_Pack'] = 1
        master_buy['Telefono'] = ''

    # Cálculos de Compra
    master_buy['Cajas_Sugeridas'] = np.ceil(master_buy['Faltante'] / master_buy['Factor_Pack'])
    master_buy['Inversion_Requerida'] = master_buy['Cajas_Sugeridas'] * master_buy['Factor_Pack'] * master_buy['Costo_Proveedor']

    return master_inv, master_buy

# ==========================================
# 4. HERRAMIENTAS DE EXPORTACIÓN
# ==========================================

def generar_link_whatsapp(numero_manual, numero_db, proveedor, df_orden):
    """
    Genera link inteligente. Prioriza el número manual si el usuario lo escribe.
    """
    telefono = numero_manual if numero_manual else numero_db
    
    if not telefono or str(telefono) in ['nan', '0', '']:
        return None
        
    clean_phone = ''.join(filter(str.isdigit, str(telefono)))
    
    msg = f"👋 Hola *{proveedor}*, favor gestionar el siguiente pedido:\n\n"
    total = 0
    for _, row in df_orden.iterrows():
        subtotal = row['Cajas_Sugeridas'] * row['Factor_Pack'] * row['Costo_Proveedor']
        total += subtotal
        msg += f"📦 *{int(row['Cajas_Sugeridas'])} un/cajas* - {row['Nombre']}\n"
    
    msg += f"\n💰 *Total Estimado: ${total:,.0f}*\nGracias."
    return f"https://wa.me/{clean_phone}?text={quote(msg)}"

def descargar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Orden_Compra')
        # Formato básico
        workbook = writer.book
        worksheet = writer.sheets['Orden_Compra']
        format1 = workbook.add_format({'num_format': '$#,##0'})
        worksheet.set_column('E:F', 18, format1)
    return output.getvalue()

# ==========================================
# 5. UI PRINCIPAL (DASHBOARD)
# ==========================================

def main():
    sh = conectar_db()
    if not sh: return

    # 1. Carga Resiliente (No se rompe si faltan columnas)
    df_inv, df_ven, df_prov, df_hist, ws_hist = cargar_datos_pro(sh)
    
    # 2. Procesamiento
    master_inv, master_buy = procesar_inteligencia(df_inv, df_ven, df_prov)

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("💠 NEXUS ULTRA")
        st.markdown("### Inteligencia de Inventario")
        
        # Alertas Rápidas
        criticos = master_inv[master_inv['Estado'] == '🚨 Pedir'].shape[0]
        if criticos > 0:
            st.error(f"⚠️ {criticos} Productos en nivel CRÍTICO")
        else:
            st.success("✅ Inventario Saludable")
        
        st.divider()
        st.info("El sistema ahora detecta automáticamente tus columnas. Si los costos salen en $0, revisa que la columna en Sheets se llame 'Costo', 'Precio Compra' o similar.")

    # --- HEADER KPI ---
    st.markdown("## 🚀 Centro de Comando")
    
    k1, k2, k3, k4 = st.columns(4)
    
    # Valor Real del Inventario (Suma de Stock * Costo)
    valor_inv = master_inv['Valor_Stock'].sum()
    k1.metric("Valor Inventario", f"${valor_inv:,.0f}", delta="Activos Líquidos")
    
    # Ganancia Potencial (Margen total si se vende todo)
    margen_potencial = master_inv['Margen_Total_Potencial'].sum()
    k2.metric("Ganancia Potencial", f"${margen_potencial:,.0f}", delta=f"{(margen_potencial/valor_inv)*100:.1f}% ROI", delta_color="normal")
    
    # Presupuesto para Reabastecer (Solo lo urgente)
    dinero_necesario = master_buy[master_buy['Estado'] == '🚨 Pedir']['Inversion_Requerida'].sum()
    k3.metric("Capital Requerido", f"${dinero_necesario:,.0f}", delta="Para reponer stock bajo", delta_color="inverse")
    
    # Ventas Promedio
    k4.metric("Velocidad Venta", f"{master_inv['Velocidad_Diaria'].sum():.1f} u/día")

    # --- TABS ---
    tabs = st.tabs(["📊 Análisis 360", "🛒 Compras Inteligentes", "📥 Recepción", "💾 Base de Datos"])

    # TAB 1: ANALYTICS
    with tabs[0]:
        c1, c2 = st.columns([2,1])
        with c1:
            st.subheader("Salud del Inventario (Días de Stock)")
            # Gráfico de dispersión: Stock vs Velocidad
            fig = px.scatter(
                master_inv[master_inv['Stock'] > 0],
                x='Dias_Inventario',
                y='Margen_Unit',
                size='Valor_Stock',
                color='Estado',
                hover_name='Nombre',
                color_discrete_map={'🚨 Pedir': '#ef4444', '✅ OK': '#10b981'},
                title="Mapa de Riesgo: Tamaño = Valor invertido"
            )
            # Línea de referencia de 30 días
            fig.add_vline(x=30, line_dash="dash", annotation_text="30 Días Stock")
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("Top Rentabilidad")
            top_margen = master_inv.sort_values('Margen_Unit', ascending=False).head(5)
            st.dataframe(
                top_margen[['Nombre', 'Precio', 'Costo', 'Margen_Unit']],
                hide_index=True,
                column_config={
                    "Margen_Unit": st.column_config.ProgressColumn("Margen $", format="$%.0f", min_value=0, max_value=master_inv['Margen_Unit'].max())
                }
            )

    # TAB 2: COMPRAS (SOLUCIÓN WHATSAPP + ERROR KEYERROR)
    with tabs[1]:
        st.subheader("Generador de Pedidos IA")
        
        # Filtro: Solo lo que necesitamos pedir
        df_pedir = master_buy[master_buy['Cajas_Sugeridas'] > 0].copy()
        
        if df_pedir.empty:
            st.success("🎉 ¡Todo está abastecido! No se requieren compras hoy.")
        else:
            col_sel, col_act = st.columns([1, 3])
            
            with col_sel:
                proveedores = df_pedir['Nombre_Proveedor'].unique()
                prov_sel = st.selectbox("Seleccionar Proveedor", proveedores)
                
                # Datos del proveedor seleccionado
                info_p = df_prov[df_prov['Nombre_Proveedor'] == prov_sel]
                tel_db = info_p['Telefono'].values[0] if not info_p.empty else ""
                
                st.info(f"📞 Tel en base de datos: {tel_db}")
            
            with col_act:
                # Filtrar orden para ese proveedor
                orden_borrador = df_pedir[df_pedir['Nombre_Proveedor'] == prov_sel].copy()
                
                st.markdown(f"#### 📝 Editando pedido para: **{prov_sel}**")
                
                # EDITOR DE DATOS
                orden_final = st.data_editor(
                    orden_borrador[['ID_Producto', 'Nombre', 'Stock', 'Cajas_Sugeridas', 'Costo_Proveedor', 'Factor_Pack']],
                    num_rows="dynamic",
                    hide_index=True,
                    column_config={
                        "Cajas_Sugeridas": st.column_config.NumberColumn("Cajas a Pedir", min_value=1, step=1),
                        "Costo_Proveedor": st.column_config.NumberColumn("Costo Pactado", format="$%.0f"),
                        "Stock": st.column_config.NumberColumn("Stock Actual", disabled=True),
                        "Nombre": st.column_config.TextColumn("Producto", disabled=True)
                    },
                    use_container_width=True
                )
                
                total_po = (orden_final['Cajas_Sugeridas'] * orden_final['Factor_Pack'] * orden_final['Costo_Proveedor']).sum()
                st.write(f"### Total Orden: :green[${total_po:,.0f}]")
                
                st.divider()
                
                # ACCIONES FINALES
                c_wa, c_ex, c_sa = st.columns(3)
                
                # 1. WHATSAPP MANUAL/AUTO
                with c_wa:
                    tel_manual = st.text_input("Confirmar Celular (WhatsApp)", value=str(tel_db))
                    link_wa = generar_link_whatsapp(tel_manual, tel_db, prov_sel, orden_final)
                    
                    if link_wa:
                        st.link_button("📲 Enviar WhatsApp", link_wa, type="primary", use_container_width=True)
                    else:
                        st.warning("Ingresa un número para enviar.")

                # 2. EXCEL
                with c_ex:
                    data_excel = descargar_excel(orden_final)
                    st.download_button("💾 Descargar Excel", data_excel, file_name=f"Pedido_{prov_sel}.xlsx", use_container_width=True)
                
                # 3. GUARDAR
                with c_sa:
                    if st.button("🚀 Registrar Orden", type="secondary", use_container_width=True):
                        try:
                            # Preparar JSON para guardar
                            items_guardar = orden_final[['Nombre', 'Cajas_Sugeridas']].to_dict('records')
                            nueva_fila = [
                                f"ORD-{uuid.uuid4().hex[:6].upper()}",
                                prov_sel,
                                str(datetime.now().date()),
                                json.dumps(items_guardar),
                                total_po,
                                "Pendiente", "", "", ""
                            ]
                            ws_hist.append_row(nueva_fila)
                            st.toast("Orden guardada exitosamente!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error guardando: {e}")

    # TAB 3: RECEPCIÓN (SIMPLIFICADA)
    with tabs[2]:
        st.subheader("Control de Llegadas")
        pendientes = df_hist[df_hist['Estado'] == 'Pendiente']
        
        if pendientes.empty:
            st.info("No hay órdenes pendientes de llegada.")
        else:
            for i, row in pendientes.iterrows():
                with st.expander(f"📦 {row['Proveedor']} - ${row['Total']:,.0f} ({row['Fecha_Orden']})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.json(json.loads(row['Items_JSON']))
                    with col2:
                        if st.button("✅ Confirmar Recepción Completa", key=row['ID_Orden']):
                            cell = ws_hist.find(row['ID_Orden'])
                            ws_hist.update_cell(cell.row, 6, "Recibido")
                            ws_hist.update_cell(cell.row, 7, str(datetime.now().date()))
                            st.success("Stock actualizado (Lógica simulada)")
                            st.rerun()

    # TAB 4: VISOR DE DATOS
    with tabs[3]:
        st.info("Vista Raw de Datos Normalizados")
        st.dataframe(master_inv)

if __name__ == "__main__":
    main()
