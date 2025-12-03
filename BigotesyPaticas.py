import streamlit as st
import pandas as pd
import gspread
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime
import time
import numpy as np # Importante para detectar tipos de datos numéricos

# --- 1. CONFIGURACIÓN Y ESTILOS MODERNOS ---

COLOR_PRIMARIO = "#2ecc71"  # Verde Esmeralda (Más moderno)
COLOR_SECUNDARIO = "#e67e22" # Naranja Zanahoria (Acento)
COLOR_FONDO = "#f4f6f9"     # Gris azulado muy suave (Fondo técnico)
COLOR_CARD = "#ffffff"      # Blanco puro para tarjetas

def configurar_pagina():
    st.set_page_config(
        page_title="Bigotes y Patitas POS",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="expanded" # IMPORTANTE: Expandido para que se vean tus otras páginas (pages/)
    )
    
    st.markdown(f"""
        <style>
        /* Fondo General */
        .stApp {{
            background-color: {COLOR_FONDO};
        }}
        
        /* Estilo de Tarjetas (Contenedores) */
        .css-1r6slb0, .stVerticalBlock {{
            gap: 1rem;
        }}
        
        /* Título Principal */
        .big-title {{
            font-family: 'Helvetica Neue', sans-serif;
            font-size: 2.5em;
            color: #2c3e50;
            font-weight: 800;
            margin-bottom: 0px;
        }}
        .subtitle {{
            color: #7f8c8d;
            font-size: 1.1em;
            margin-bottom: 20px;
        }}

        /* Inputs y Selects más bonitos */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
            border-radius: 10px;
            border: 1px solid #dfe6e9;
            padding: 10px;
        }}
        
        /* Botones */
        .stButton button[type="primary"] {{
            background: linear-gradient(45deg, {COLOR_PRIMARIO}, #27ae60);
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            color: white;
            font-weight: bold;
            padding: 0.5rem 1rem;
            border-radius: 12px;
            transition: all 0.3s ease;
        }}
        .stButton button[type="primary"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.15);
        }}
        
        /* Métricas (Total a Pagar) */
        [data-testid="stMetricValue"] {{
            font-size: 3rem !important;
            color: {COLOR_PRIMARIO};
            font-weight: 900;
        }}
        
        /* Tabs personalizados */
        .stTabs [data-baseweb="tab-list"] button {{
            font-weight: bold;
            font-size: 1.1em;
            border-radius: 8px 8px 0 0;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: white !important;
            border-top: 3px solid {COLOR_PRIMARIO} !important;
            color: {COLOR_PRIMARIO} !important;
        }}
        
        /* Contenedores visuales "Cards" simulados con columnas y fondo blanco nativo de Streamlit widgets */
        div[data-testid="stVerticalBlock"] > div {{
            background-color: transparent;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE DATOS Y LIMPIEZA (FIX JSON ERROR) ---

@st.cache_resource(ttl=600)
def conectar_google_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos.")
            return None, None, None, None

        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        hoja = gc.open_by_url(st.secrets["SHEET_URL"])
        
        return hoja.worksheet("Inventario"), hoja.worksheet("Clientes"), hoja.worksheet("Ventas"), hoja.worksheet("Gastos")
    except Exception as e:
        st.error(f"Error conexión: {e}")
        return None, None, None, None

def sanitizar_dato(dato):
    """Convierte tipos de Numpy (int64, float64) a tipos nativos de Python (int, float) para JSON."""
    if isinstance(dato, (np.int64, np.int32, np.integer)):
        return int(dato)
    elif isinstance(dato, (np.float64, np.float32, np.floating)):
        return float(dato)
    elif isinstance(dato, list):
        return [sanitizar_dato(x) for x in dato]
    return dato

def leer_datos(ws, index_col=None):
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame() # Retorno seguro
        
        # Limpieza automática de columnas numéricas clave
        for col in ['Precio', 'Stock', 'Monto', 'Total_Venta']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        if index_col and index_col in df.columns:
            df = df.set_index(index_col)
        return df
    except Exception:
        return pd.DataFrame()

def escribir_fila(ws, datos):
    try:
        # AQUÍ ESTÁ LA SOLUCIÓN AL ERROR JSON: Limpiamos los datos antes de enviar
        datos_limpios = [sanitizar_dato(d) for d in datos]
        ws.append_row(datos_limpios)
        return True
    except Exception as e:
        st.error(f"Error escribiendo datos: {e}")
        return False

def actualizar_inventario_batch(ws_inventario, items_venta):
    try:
        records = ws_inventario.get_all_records()
        df = pd.DataFrame(records)
        df['ID_Producto'] = df['ID_Producto'].astype(str)
        
        for item in items_venta:
            id_prod = str(item['ID_Producto'])
            cantidad = item['Cantidad']
            fila_idx = df.index[df['ID_Producto'] == id_prod].tolist()
            
            if fila_idx:
                fila_real = fila_idx[0] + 2 
                col_stock = 4 
                stock_actual = int(df.iloc[fila_idx[0]]['Stock'])
                nuevo_stock = max(0, stock_actual - cantidad)
                ws_inventario.update_cell(fila_real, col_stock, int(nuevo_stock))
        return True
    except Exception as e:
        st.error(f"Error inv: {e}")
        return False

# --- 3. GENERACIÓN PDF ---
# (Mantenemos la función igual, funciona bien)
def generar_factura_pdf(datos, items):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    Story = []
    
    # Estilos simples
    Story.append(Paragraph(f"🐾 Bigotes y Patitas", styles['Title']))
    Story.append(Paragraph(f"Ticket de Venta #{datos['ID_Venta']}", styles['Normal']))
    Story.append(Spacer(1, 12))
    Story.append(Paragraph(f"Cliente: {datos['Nombre_Cliente']}", styles['Normal']))
    
    data = [['Prod', 'Cant', 'Total']]
    for i in items:
        data.append([i['Nombre_Producto'][:20], i['Cantidad'], f"${i['Subtotal']:,.0f}"])
    
    data.append(['', 'TOTAL:', f"${datos['Total_Venta']:,.0f}"])
    t = Table(data)
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, black)]))
    Story.append(t)
    
    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue()

# --- 4. INTERFAZ (UI) MEJORADA ---

def seccion_nueva_venta(ws_inv, ws_cli, ws_ven):
    # Layout de 2 columnas principales: Izquierda (Operación) 65% - Derecha (Resumen) 35%
    col_operacion, col_resumen = st.columns([1.8, 1])
    
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente' not in st.session_state: st.session_state.cliente = None

    # --- COLUMNA IZQUIERDA: Búsquedas y Selección ---
    with col_operacion:
        st.markdown("### 👤 Cliente")
        with st.container(border=True): # "Card" visual
            df_clientes = leer_datos(ws_cli)
            c1, c2 = st.columns([3, 1])
            cedula_buscar = c1.text_input("Buscar por Cédula", placeholder="Escribe la cédula...")
            if c2.button("🔍 Buscar", use_container_width=True):
                if not df_clientes.empty:
                    df_clientes['Cedula'] = df_clientes['Cedula'].astype(str)
                    cliente = df_clientes[df_clientes['Cedula'] == str(cedula_buscar)]
                    if not cliente.empty:
                        st.session_state.cliente = cliente.iloc[0].to_dict()
                        st.toast("Cliente encontrado", icon="✅")
                    else:
                        st.warning("No encontrado")

            if st.session_state.cliente:
                st.success(f"**Cliente Activo:** {st.session_state.cliente.get('Nombre')} ({st.session_state.cliente.get('Mascota')})")
            else:
                st.info("Selecciona un cliente o registra uno nuevo rápido.")
                with st.expander("➕ Registro Rápido"):
                    with st.form("reg_rapido"):
                        rc_ced = st.text_input("Cédula")
                        rc_nom = st.text_input("Nombre")
                        if st.form_submit_button("Guardar"):
                            escribir_fila(ws_cli, [rc_ced, rc_nom, "", "", "Mascota", ""])
                            st.session_state.cliente = {"Cedula": rc_ced, "Nombre": rc_nom}
                            st.rerun()

        st.markdown("### 📦 Productos")
        with st.container(border=True):
            df_inv = leer_datos(ws_inv)
            if not df_inv.empty:
                df_stock = df_inv[df_inv['Stock'] > 0]
                # Crear una lista de opciones más limpia
                opciones = df_stock.apply(lambda x: f"{x['Nombre']} | ${x['Precio']:,.0f}", axis=1).tolist()
                
                prod_seleccionado = st.selectbox("Seleccionar Producto", [""] + opciones, placeholder="Escribe para buscar...")
                
                c_cant, c_btn = st.columns([1, 2])
                cantidad = c_cant.number_input("Cantidad", min_value=1, value=1)
                
                if c_btn.button("➕ Agregar al Carrito", type="primary", use_container_width=True):
                    if prod_seleccionado:
                        nombre_real = prod_seleccionado.split(" | $")[0]
                        datos_prod = df_inv[df_inv['Nombre'] == nombre_real].iloc[0]
                        
                        if cantidad <= datos_prod['Stock']:
                            item = {
                                "ID_Producto": datos_prod['ID_Producto'],
                                "Nombre_Producto": datos_prod['Nombre'],
                                "Precio": float(datos_prod['Precio']), # Convertir explícitamente
                                "Cantidad": int(cantidad),             # Convertir explícitamente
                                "Subtotal": float(datos_prod['Precio'] * cantidad)
                            }
                            st.session_state.carrito.append(item)
                            st.toast("Producto Agregado", icon="🛒")
                        else:
                            st.error(f"Stock insuficiente ({datos_prod['Stock']})")

    # --- COLUMNA DERECHA: Carrito y Totales (Estilo Ticket) ---
    with col_resumen:
        with st.container(border=True):
            st.markdown("### 🛒 Ticket de Venta")
            
            if st.session_state.carrito:
                df_cart = pd.DataFrame(st.session_state.carrito)
                # Mostrar tabla limpia
                st.dataframe(
                    df_cart[['Nombre_Producto', 'Cantidad', 'Subtotal']], 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Subtotal": st.column_config.NumberColumn(format="$%.0f")
                    }
                )
                
                total_venta = df_cart['Subtotal'].sum()
                st.markdown("---")
                st.markdown("<p style='text-align: center; font-size: 1.2rem;'>Total a Pagar</p>", unsafe_allow_html=True)
                st.metric(label="", value=f"${total_venta:,.0f}")
                
                col_pay, col_clear = st.columns([2, 1])
                
                if col_clear.button("🗑️", help="Borrar todo"):
                    st.session_state.carrito = []
                    st.rerun()
                
                if col_pay.button("✅ COBRAR", type="primary", use_container_width=True):
                    if not st.session_state.cliente:
                        st.error("⚠️ Falta Cliente")
                    else:
                        # PROCESO DE COBRO
                        id_venta = datetime.now().strftime("%Y%m%d%H%M%S")
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Construir string de items
                        desc_items = ", ".join([f"{i['Nombre_Producto']} (x{i['Cantidad']})" for i in st.session_state.carrito])
                        
                        # Datos limpios y seguros
                        datos_venta = [
                            id_venta, 
                            fecha, 
                            str(st.session_state.cliente['Cedula']), 
                            st.session_state.cliente['Nombre'], 
                            st.session_state.cliente.get('Mascota', ''), 
                            float(total_venta), # Asegurar float python
                            desc_items
                        ]
                        
                        if escribir_fila(ws_ven, datos_venta):
                            actualizar_inventario_batch(ws_inv, st.session_state.carrito)
                            
                            st.balloons()
                            st.success("¡Venta Exitosa!")
                            
                            # Generar PDF
                            datos_pdf = {
                                "ID_Venta": id_venta, "Nombre_Cliente": st.session_state.cliente['Nombre'],
                                "Total_Venta": total_venta
                            }
                            pdf = generar_factura_pdf(datos_pdf, st.session_state.carrito)
                            st.download_button("Imprimir Recibo", pdf, file_name=f"Ticket_{id_venta}.pdf", mime="application/pdf")
                            
                            # Limpiar
                            st.session_state.carrito = []
                            st.session_state.cliente = None
                            time.sleep(3)
                            st.rerun()
            else:
                st.info("Carrito vacío 🛒")
                st.markdown("<br>"*5, unsafe_allow_html=True) # Espacio vacío visual

# --- FUNCIONES AUXILIARES DE LAS OTRAS PESTAÑAS (Simplificadas para el ejemplo) ---
def seccion_inventario(ws):
    st.markdown("### 📋 Inventario")
    with st.container(border=True):
        df = leer_datos(ws)
        st.dataframe(df, use_container_width=True)

def seccion_gastos(ws):
    st.markdown("### 💸 Gastos")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.text_input("Concepto")
        c2.number_input("Monto")
        st.button("Guardar Gasto")

def seccion_cierre(ws_v, ws_g):
    st.markdown("### 💰 Cierre de Caja")
    st.info("Selecciona fecha para calcular balance")

# --- MAIN ---

def main():
    configurar_pagina()
    
    # Header minimalista con logo
    c1, c2 = st.columns([0.5, 4])
    with c1:
        st.markdown("<h1>🐱</h1>", unsafe_allow_html=True)
    with c2:
        st.markdown('<p class="big-title">Bigotes y Patitas</p>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Sistema de Gestión Veterinaria Inteligente</p>', unsafe_allow_html=True)
        
    st.markdown("---")

    ws_inv, ws_cli, ws_ven, ws_gas = conectar_google_sheets()

    if not ws_inv:
        st.warning("Conectando con la nube...")
        return

    # Tabs modernos
    tab1, tab2, tab3, tab4 = st.tabs(["🛒 PUNTO DE VENTA", "📋 INVENTARIO", "💸 GASTOS", "💰 CIERRE"])

    with tab1:
        seccion_nueva_venta(ws_inv, ws_cli, ws_ven)
    with tab2:
        seccion_inventario(ws_inv)
    with tab3:
        seccion_gastos(ws_gas)
    with tab4:
        seccion_cierre(ws_ven, ws_gas)

    # Sidebar informativo (Ya no colapsado, aquí aparecerán tus Pages automáticamente)
    st.sidebar.markdown("### 🐾 Navegación")
    st.sidebar.info("Selecciona arriba las páginas adicionales como 'Compras'.")
    st.sidebar.markdown("---")
    st.sidebar.caption("v2.1 - Sistema Optimizado")

if __name__ == "__main__":
    main()
