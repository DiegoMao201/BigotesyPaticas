import streamlit as st
import pandas as pd
import gspread
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime
import time

# --- 1. CONFIGURACIÓN Y ESTILOS ---

# Colores de marca
COLOR_PRIMARIO = "#28a745"  # Verde Éxito
COLOR_SECUNDARIO = "#ffc107" # Amarillo Alerta/Acento
COLOR_FONDO_CLARO = "#f0fff4"
COLOR_TEXTO = "#333333"

def configurar_pagina():
    """Configuración inicial de la página."""
    st.set_page_config(
        page_title="🐾 Bigotes y Patitas POS",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="collapsed" # Colapsado para dar protagonismo al contenido
    )
    
    st.markdown(f"""
        <style>
        .main {{ background-color: {COLOR_FONDO_CLARO}; }}
        
        /* Título Principal */
        .big-title {{
            font-size: 3em;
            color: {COLOR_PRIMARIO};
            font-weight: 900;
            text-shadow: 1px 1px 2px #ccc;
            margin-bottom: 0px;
        }}
        
        /* Estilo de las Pestañas (Tabs) */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            white-space: pre-wrap;
            background-color: white;
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
            border: 1px solid #ddd;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {COLOR_PRIMARIO} !important;
            color: white !important;
            font-weight: bold;
        }}
        
        /* Botones Primarios */
        .stButton button[type="primary"] {{
            background-color: {COLOR_PRIMARIO} !important;
            border: none;
            color: white;
            font-weight: bold;
            transition: transform 0.2s;
        }}
        .stButton button[type="primary"]:hover {{
            transform: scale(1.02);
        }}
        
        /* Métricas */
        [data-testid="stMetricValue"] {{
            font-size: 2.2rem;
            color: {COLOR_PRIMARIO};
        }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE DATOS (GOOGLE SHEETS) ---

@st.cache_resource(ttl=600)
def conectar_google_sheets():
    """Conecta a Google Sheets y maneja errores de credenciales."""
    try:
        # Asegúrate de que st.secrets["google_service_account"] y st.secrets["SHEET_URL"] existan
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta la configuración de 'google_service_account' en secrets.toml")
            return None, None, None, None

        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        hoja = gc.open_by_url(st.secrets["SHEET_URL"])
        
        # Obtener worksheets, si no existen, el código podría fallar aquí si la hoja es nueva
        # Se asume que las hojas existen con estos nombres exactos.
        ws_inv = hoja.worksheet("Inventario")
        ws_cli = hoja.worksheet("Clientes")
        ws_ven = hoja.worksheet("Ventas")
        ws_gas = hoja.worksheet("Gastos")
        
        return ws_inv, ws_cli, ws_ven, ws_gas
    except Exception as e:
        st.error(f"🚨 Error crítico de conexión: {e}")
        return None, None, None, None

def leer_datos(ws, index_col=None):
    """
    Lee datos de una hoja y retorna un DataFrame seguro.
    Si la hoja está vacía, devuelve un DataFrame con las columnas correctas pero vacío.
    """
    if ws is None: 
        return pd.DataFrame()

    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # Definición de columnas esperadas para robustez
        columnas_esperadas = []
        if ws.title == "Inventario":
            columnas_esperadas = ['ID_Producto', 'Nombre', 'Precio', 'Stock', 'Costo']
        elif ws.title == "Clientes":
            columnas_esperadas = ['Cedula', 'Nombre', 'Telefono', 'Direccion', 'Mascota', 'Tipo_Mascota']
        elif ws.title == "Ventas":
            columnas_esperadas = ['ID_Venta', 'Fecha', 'Cedula_Cliente', 'Nombre_Cliente', 'Nombre_Mascota', 'Total_Venta', 'Items_Vendidos']
        elif ws.title == "Gastos":
            columnas_esperadas = ['Fecha_Gasto', 'Concepto', 'Tipo_Gasto', 'Monto']

        # Si el DF está vacío o faltan columnas, reestructurar
        if df.empty:
            df = pd.DataFrame(columns=columnas_esperadas)
        else:
            # Asegurar que existan todas las columnas esperadas, rellenar con NaN si faltan
            for col in columnas_esperadas:
                if col not in df.columns:
                    df[col] = ""

        if index_col and not df.empty and index_col in df.columns:
            df = df.set_index(index_col)
            
        return df
    except Exception as e:
        st.warning(f"Advertencia leyendo {ws.title}: {e}")
        return pd.DataFrame()

def escribir_fila(ws, datos):
    """Agrega una fila al final de la hoja."""
    try:
        ws.append_row(datos)
        return True
    except Exception as e:
        st.error(f"Error escribiendo datos: {e}")
        return False

def actualizar_inventario_batch(ws_inventario, items_venta):
    """Actualiza el stock restando la cantidad vendida."""
    try:
        # Obtener todos los datos para buscar coordenadas
        records = ws_inventario.get_all_records()
        df = pd.DataFrame(records)
        df['ID_Producto'] = df['ID_Producto'].astype(str) # Asegurar string para búsqueda
        
        updates = []
        
        for item in items_venta:
            id_prod = str(item['ID_Producto'])
            cantidad = item['Cantidad']
            
            # Buscar índice en el DF (fila + 2 porque gspread es base-1 y tiene header)
            fila_idx = df.index[df['ID_Producto'] == id_prod].tolist()
            
            if fila_idx:
                fila_real = fila_idx[0] + 2 
                col_stock = 4 # Asumiendo que 'Stock' es la columna 4 (D)
                
                stock_actual = int(df.iloc[fila_idx[0]]['Stock'])
                nuevo_stock = max(0, stock_actual - cantidad)
                
                # Preparar actualización celda por celda (un poco lento pero seguro)
                # Para optimizar usar batch_update en apps grandes
                ws_inventario.update_cell(fila_real, col_stock, nuevo_stock)
                
        return True
    except Exception as e:
        st.error(f"Error actualizando inventario: {e}")
        return False

# --- 3. GENERACIÓN DE REPORTES PDF ---

def generar_factura_pdf(datos, items):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    Story = []

    # Estilos
    style_titulo = ParagraphStyle('Header', parent=styles['Heading1'], alignment=1, textColor=HexColor(COLOR_PRIMARIO))
    style_normal = styles['BodyText']

    Story.append(Paragraph("🐾 Bigotes y Patitas - Factura de Venta", style_titulo))
    Story.append(Spacer(1, 12))
    Story.append(Paragraph(f"<b>Fecha:</b> {datos['Fecha']} | <b>ID Venta:</b> {datos['ID_Venta']}", style_normal))
    Story.append(Paragraph(f"<b>Cliente:</b> {datos['Nombre_Cliente']} (ID: {datos['Cedula_Cliente']})", style_normal))
    Story.append(Spacer(1, 12))

    # Tabla Items
    data_tabla = [['Producto', 'Cant', 'Precio', 'Subtotal']]
    for i in items:
        data_tabla.append([
            i['Nombre_Producto'], 
            i['Cantidad'], 
            f"${i['Precio']:,.0f}", 
            f"${i['Subtotal']:,.0f}"
        ])
    
    # Agregar Total
    data_tabla.append(['', '', 'TOTAL', f"${datos['Total_Venta']:,.0f}"])

    t = Table(data_tabla, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor(COLOR_PRIMARIO)),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-2), 1, black),
        ('FONTWEIGHT', (0,0), (-1,0), 'BOLD'),
        ('FONTWEIGHT', (-2,-1), (-1,-1), 'BOLD'), # Total bold
    ]))
    Story.append(t)
    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue()

def generar_cierre_caja_pdf(ventas, gastos, fecha, balance):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    Story = []

    Story.append(Paragraph(f"💰 Cierre de Caja - {fecha}", styles['Heading1']))
    Story.append(Spacer(1, 12))
    
    # Resumen
    Story.append(Paragraph(f"Total Ingresos: ${ventas['Total_Venta'].sum():,.0f}", styles['Normal']))
    Story.append(Paragraph(f"Total Gastos: ${gastos['Monto'].sum():,.0f}", styles['Normal']))
    Story.append(Paragraph(f"<b>BALANCE NETO: ${balance:,.0f}</b>", styles['Heading2']))
    Story.append(Spacer(1, 20))

    # Tabla Ventas
    if not ventas.empty:
        Story.append(Paragraph("Detalle de Ventas", styles['Heading3']))
        data_v = [['ID', 'Cliente', 'Total']] + ventas[['ID_Venta', 'Nombre_Cliente', 'Total_Venta']].values.tolist()
        t_v = Table(data_v)
        t_v.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, black)]))
        Story.append(t_v)

    # Tabla Gastos
    if not gastos.empty:
        Story.append(Spacer(1, 12))
        Story.append(Paragraph("Detalle de Gastos", styles['Heading3']))
        data_g = [['Concepto', 'Monto']] + gastos[['Concepto', 'Monto']].values.tolist()
        t_g = Table(data_g)
        t_g.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, black)]))
        Story.append(t_g)

    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue()

# --- 4. INTERFAZ DE USUARIO (COMPONENTES) ---

def seccion_nueva_venta(ws_inv, ws_cli, ws_ven):
    st.markdown("### 🛍️ Terminal de Punto de Venta (POS)")
    
    # Inicializar Session State para POS
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente' not in st.session_state: st.session_state.cliente = None

    col_izq, col_der = st.columns([1.5, 1])

    with col_izq:
        st.markdown("#### 1. Datos del Cliente")
        df_clientes = leer_datos(ws_cli)
        
        c1, c2 = st.columns([3, 1])
        cedula_buscar = c1.text_input("Buscar Cédula Cliente", placeholder="Ej: 1088...")
        
        if c2.button("🔎 Buscar"):
            if not df_clientes.empty:
                # Convertir a string para comparar
                df_clientes['Cedula'] = df_clientes['Cedula'].astype(str)
                cliente = df_clientes[df_clientes['Cedula'] == str(cedula_buscar)]
                if not cliente.empty:
                    st.session_state.cliente = cliente.iloc[0].to_dict()
                    st.success("Cliente cargado")
                else:
                    st.warning("No encontrado")
            else:
                st.error("Base de datos de clientes vacía")

        # Mostrar cliente activo o Formulario de registro rápido
        if st.session_state.cliente:
            st.info(f"👤 **Cliente:** {st.session_state.cliente.get('Nombre', 'N/A')} | 🐾 **Mascota:** {st.session_state.cliente.get('Mascota', 'N/A')}")
            if st.button("❌ Quitar Cliente"):
                st.session_state.cliente = None
                st.rerun()
        else:
            with st.expander("➕ Nuevo Cliente Rápido"):
                with st.form("form_nuevo_cliente"):
                    nc_ced = st.text_input("Cédula*")
                    nc_nom = st.text_input("Nombre*")
                    nc_mas = st.text_input("Mascota")
                    if st.form_submit_button("Guardar"):
                        if nc_ced and nc_nom:
                            escribir_fila(ws_cli, [nc_ced, nc_nom, "", "", nc_mas, ""])
                            st.session_state.cliente = {"Cedula": nc_ced, "Nombre": nc_nom, "Mascota": nc_mas}
                            st.toast("Cliente registrado y seleccionado")
                            st.rerun()

        st.markdown("---")
        st.markdown("#### 2. Agregar Productos")
        df_inv = leer_datos(ws_inv)
        
        if not df_inv.empty:
            # Limpieza de datos
            df_inv['Precio'] = pd.to_numeric(df_inv['Precio'], errors='coerce').fillna(0)
            df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
            
            # Filtro solo con stock
            df_stock = df_inv[df_inv['Stock'] > 0]
            opciones = [f"{row['Nombre']} (${row['Precio']:,.0f}) | ID: {row['ID_Producto']}" for i, row in df_stock.iterrows()]
            
            seleccion = st.selectbox("Buscar Producto", [""] + opciones)
            col_cant, col_add = st.columns([1, 2])
            cantidad = col_cant.number_input("Cant", min_value=1, value=1)
            
            if col_add.button("Añadir al Carrito", type="primary") and seleccion:
                id_prod_sel = seleccion.split("| ID: ")[1]
                prod_data = df_inv[df_inv['ID_Producto'].astype(str) == id_prod_sel].iloc[0]
                
                if cantidad <= prod_data['Stock']:
                    item = {
                        "ID_Producto": prod_data['ID_Producto'],
                        "Nombre_Producto": prod_data['Nombre'],
                        "Precio": prod_data['Precio'],
                        "Cantidad": cantidad,
                        "Subtotal": prod_data['Precio'] * cantidad
                    }
                    st.session_state.carrito.append(item)
                    st.toast("Producto Agregado")
                else:
                    st.error(f"Stock insuficiente. Solo hay {prod_data['Stock']}")
        else:
            st.warning("Inventario vacío")

    with col_der:
        st.markdown("#### 🛒 Carrito de Compras")
        if st.session_state.carrito:
            df_cart = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_cart[['Nombre_Producto', 'Cantidad', 'Subtotal']], hide_index=True, use_container_width=True)
            
            total = df_cart['Subtotal'].sum()
            st.metric("Total a Pagar", f"${total:,.0f}")
            
            col_vac, col_fin = st.columns(2)
            if col_vac.button("🗑️ Vaciar"):
                st.session_state.carrito = []
                st.rerun()
            
            if col_fin.button("✅ FINALIZAR VENTA", type="primary", use_container_width=True):
                if not st.session_state.cliente:
                    st.error("⚠️ Falta seleccionar un cliente")
                else:
                    # Procesar Venta
                    id_venta = datetime.now().strftime("%Y%m%d%H%M%S")
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    items_str = ", ".join([f"{i['Nombre_Producto']} (x{i['Cantidad']})" for i in st.session_state.carrito])
                    
                    datos_venta = [
                        id_venta, fecha, 
                        st.session_state.cliente['Cedula'], 
                        st.session_state.cliente['Nombre'], 
                        st.session_state.cliente.get('Mascota', ''), 
                        total, items_str
                    ]
                    
                    # 1. Guardar en Ventas
                    if escribir_fila(ws_ven, datos_venta):
                        # 2. Actualizar Stock
                        actualizar_inventario_batch(ws_inv, st.session_state.carrito)
                        
                        # 3. Generar PDF
                        datos_pdf = {
                            "ID_Venta": id_venta, "Fecha": fecha, 
                            "Nombre_Cliente": st.session_state.cliente['Nombre'],
                            "Cedula_Cliente": st.session_state.cliente['Cedula'],
                            "Total_Venta": total
                        }
                        pdf_bytes = generar_factura_pdf(datos_pdf, st.session_state.carrito)
                        
                        st.success("¡Venta Registrada con Éxito!")
                        st.balloons()
                        
                        # Botón Descarga
                        st.download_button("📄 Descargar Factura", pdf_bytes, file_name=f"Factura_{id_venta}.pdf", mime="application/pdf")
                        
                        # Reset
                        st.session_state.carrito = []
                        st.session_state.cliente = None
                        time.sleep(5) # Dar tiempo para descargar antes de borrar UI
                        st.rerun()
        else:
            st.info("El carrito está vacío")

def seccion_inventario(ws_inv):
    st.markdown("### 📋 Gestión de Inventario")
    
    # Formulario Agregar
    with st.expander("➕ Agregar Nuevo Producto al Inventario"):
        with st.form("nuevo_prod"):
            c1, c2, c3, c4 = st.columns(4)
            n_id = c1.text_input("ID / Código Barras")
            n_nom = c2.text_input("Nombre Producto")
            n_pre = c3.number_input("Precio Venta", min_value=0.0)
            n_sto = c4.number_input("Stock Inicial", min_value=0, step=1)
            n_cos = st.number_input("Costo (Opcional)", min_value=0.0)
            
            if st.form_submit_button("Guardar Producto"):
                if n_id and n_nom:
                    escribir_fila(ws_inv, [n_id, n_nom, n_pre, int(n_sto), n_cos])
                    st.success("Producto guardado")
                    st.rerun()
                else:
                    st.error("ID y Nombre son obligatorios")

    # Tabla Visualización
    df = leer_datos(ws_inv)
    if not df.empty:
        # Formato numérico seguro
        df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce')
        df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce')
        
        st.dataframe(df, use_container_width=True)
        
        # Alerta Stock Bajo
        bajo_stock = df[df['Stock'] <= 5]
        if not bajo_stock.empty:
            st.error(f"⚠️ Hay {len(bajo_stock)} productos con stock crítico (5 o menos).")
            st.dataframe(bajo_stock[['Nombre', 'Stock']])
    else:
        st.info("Inventario vacío.")

def seccion_gastos(ws_gas):
    st.markdown("### 💸 Control de Gastos")
    
    c1, c2 = st.columns([1, 2])
    
    with c1:
        with st.container(border=True):
            st.subheader("Registrar Gasto")
            g_fecha = st.date_input("Fecha", value=datetime.now())
            g_con = st.text_input("Concepto (Ej: Luz, Agua)")
            g_tipo = st.selectbox("Tipo", ["Operativo", "Nomina", "Insumos", "Otros"])
            g_monto = st.number_input("Monto ($)", min_value=0.0)
            
            if st.button("💾 Guardar Gasto", type="primary"):
                if g_con and g_monto > 0:
                    escribir_fila(ws_gas, [str(g_fecha), g_con, g_tipo, g_monto])
                    st.success("Gasto registrado")
                    st.rerun()
                else:
                    st.error("Faltan datos")

    with c2:
        df = leer_datos(ws_gas)
        if not df.empty:
            df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
            st.metric("Total Gastos Histórico", f"${df['Monto'].sum():,.0f}")
        else:
            st.info("No hay gastos registrados.")

def seccion_cierre_caja(ws_ven, ws_gas):
    st.markdown("### 💰 Cierre de Caja Diario")
    
    fecha_cierre = st.date_input("Seleccionar Fecha de Cierre", value=datetime.now())
    fecha_str_match = fecha_cierre.strftime("%Y-%m-%d") # Formato para comparar (ajusta según cómo guarda GSheet)
    
    if st.button("📊 Generar Reporte"):
        df_v = leer_datos(ws_ven)
        df_g = leer_datos(ws_gas)
        
        # Filtrar por fecha (asumiendo formato YYYY-MM-DD en la primera parte del string)
        # Nota: Ajusta el slice .str[:10] según tu formato de fecha en GSheets
        ventas_dia = pd.DataFrame()
        gastos_dia = pd.DataFrame()
        
        if not df_v.empty:
            # Asegurar tipo string y limpieza
            df_v['FechaStr'] = df_v['Fecha'].astype(str).str[:10] 
            ventas_dia = df_v[df_v['FechaStr'] == fecha_str_match].copy()
            ventas_dia['Total_Venta'] = pd.to_numeric(ventas_dia['Total_Venta'], errors='coerce').fillna(0)
            
        if not df_g.empty:
            df_g['FechaStr'] = df_g['Fecha_Gasto'].astype(str)
            gastos_dia = df_g[df_g['FechaStr'] == fecha_str_match].copy()
            gastos_dia['Monto'] = pd.to_numeric(gastos_dia['Monto'], errors='coerce').fillna(0)
            
        total_ingresos = ventas_dia['Total_Venta'].sum() if not ventas_dia.empty else 0
        total_egresos = gastos_dia['Monto'].sum() if not gastos_dia.empty else 0
        balance = total_ingresos - total_egresos
        
        # Mostrar Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos (Ventas)", f"${total_ingresos:,.0f}")
        c2.metric("Egresos (Gastos)", f"${total_egresos:,.0f}")
        c3.metric("Balance Neto", f"${balance:,.0f}", delta_color="normal")
        
        # Generar PDF Cierre
        pdf_cierre = generar_cierre_caja_pdf(ventas_dia, gastos_dia, fecha_str_match, balance)
        st.download_button("⬇️ Descargar Reporte de Cierre (PDF)", pdf_cierre, file_name=f"Cierre_{fecha_str_match}.pdf")

# --- 5. FUNCIÓN PRINCIPAL (MAIN) ---

def main():
    configurar_pagina()
    
    # Encabezado
    col_logo, col_tit = st.columns([1, 6])
    with col_logo:
        st.markdown("<h1>🐱</h1>", unsafe_allow_html=True) # Placeholder emoji si no hay logo
    with col_tit:
        st.markdown('<p class="big-title">Bigotes y Patitas</p>', unsafe_allow_html=True)
        st.markdown("**Sistema Integral de Gestión Veterinaria y Pet Shop**")

    # Conexión Backend
    ws_inv, ws_cli, ws_ven, ws_gas = conectar_google_sheets()

    if not ws_inv:
        st.warning("⚠️ Esperando conexión con Google Sheets...")
        st.stop()

    # --- NAVEGACIÓN POR TABS (Reemplaza el Sidebar) ---
    # Esto soluciona tu conflicto con la carpeta 'pages/'
    tab_pos, tab_inv, tab_gas, tab_cierre = st.tabs([
        "🛒 VENDER (POS)", 
        "📋 INVENTARIO", 
        "💸 GASTOS", 
        "💰 CIERRE DE CAJA"
    ])

    with tab_pos:
        seccion_nueva_venta(ws_inv, ws_cli, ws_ven)
    
    with tab_inv:
        seccion_inventario(ws_inv)
        
    with tab_gas:
        seccion_gastos(ws_gas)
        
    with tab_cierre:
        seccion_cierre_caja(ws_ven, ws_gas)

if __name__ == "__main__":
    main()
