import streamlit as st
import pandas as pd
import gspread # Necesitarás configurarlo para Google Sheets
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, green, blue
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from io import BytesIO
import base64
from datetime import datetime
import calendar

# --- CONFIGURACIÓN DE PÁGINA Y ESTILOS GLOBALES ---

# Color principal para Bigotes y Patitas (Verde vibrante premium)
COLOR_PRIMARIO = "#28a745" # Un verde más brillante y amigable
COLOR_SECUNDARIO = "#ffc107" # Dorado/Amarillo para acentos y alertas
COLOR_FONDO_CLARO = "#f0fff4" # Fondo muy suave

def configurar_pagina():
    """Configura la apariencia inicial de la aplicación (MÁS IMPACTANTE)."""
    st.set_page_config(
        page_title="🐾 Bigotes y Patitas - POS y Gestión Premium",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Estilo CSS para un aspecto Premium
    st.markdown(f"""
        <style>
        /* Contenedor principal con fondo suave */
        .main {{
            background-color: {COLOR_FONDO_CLARO};
        }}
        /* Título Principal más impactante */
        .big-title {{
            font-size: 3.5em; /* Más grande */
            color: {COLOR_PRIMARIO}; 
            text-align: left; /* Alineado a la izquierda */
            margin-bottom: 20px;
            font-weight: 900; /* Extra bold */
            text-shadow: 2px 2px 5px #ccc; /* Sombra más pronunciada */
            padding-left: 20px;
        }}
        /* Subtítulos de pestañas */
        h2 {{
            color: #333333; /* Color oscuro para contraste */
            border-bottom: 3px solid {COLOR_PRIMARIO};
            padding-bottom: 8px;
            font-weight: 700;
        }}
        /* Mejorar la apariencia del botón primario (Verde) */
        .stButton button[data-testid="stFormSubmitButton"], 
        .stButton button:focus:not([data-testid="baseButton-secondary"]) {{
            background-color: {COLOR_PRIMARIO} !important;
            border-color: {COLOR_PRIMARIO} !important;
            color: white !important;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 8px; /* Bordes más suaves */
            transition: all 0.3s ease;
        }}
        /* Estilo para las métricas (Key Performance Indicators) */
        [data-testid="stMetricValue"] {{
            font-size: 2.8rem; /* Más grande */
            color: {COLOR_PRIMARIO};
            font-weight: 800;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 1.1rem;
            color: #555;
            font-weight: 600;
        }}
        [data-testid="stAlert"] {{
            border-left: 5px solid {COLOR_SECUNDARIO};
            border-radius: 8px;
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # Título y Logo
    col1, col2 = st.columns([1, 6])
    # Intentar cargar el logo
    try:
        # Asumiendo que el logo es un ícono de la tienda de mascotas
        col1.image("BigotesyPaticas_logo.png", width=120) 
    except:
        col1.markdown(f'<p style="font-size: 70px; text-align: center;">😻</p>', unsafe_allow_html=True)

    col2.markdown('<div class="big-title">Bigotes y Patitas - Gestión Smart </div>', unsafe_allow_html=True)
    st.markdown("---")


# --- CONEXIÓN A GOOGLE SHEETS Y LECTURA/ESCRITURA BÁSICA ---

@st.cache_resource(ttl=3600) # Cacheo más agresivo para menos llamadas a gspread
def conectar_google_sheets():
    """Establece y cachea la conexión a Google Sheets. Retorna los Worksheets."""
    try:
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        SHEET_URL = st.secrets["SHEET_URL"] 
        hoja = gc.open_by_url(SHEET_URL)
        return hoja.worksheet("Inventario"), hoja.worksheet("Clientes"), hoja.worksheet("Ventas"), hoja.worksheet("Gastos")
    except Exception as e:
        st.error(f"🚨 Error crítico al conectar con Google Sheets. Revisa la URL y tus credenciales. Detalle: {e}")
        return None, None, None, None

def leer_datos(ws, index_col=None):
    """Función genérica para leer cualquier hoja como DataFrame."""
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if index_col and not df.empty:
            df = df.set_index(index_col)
        return df
    except Exception as e:
        # Silenciar errores por si la hoja está vacía pero mostrar un warning al dev
        # st.warning(f"Error al leer la hoja '{ws.title}'. Puede estar vacía: {e}")
        # Retorna un DF vacío pero con las columnas esperadas para evitar KeyErrors posteriores
        if ws.title == "Inventario":
            return pd.DataFrame(columns=['ID_Producto', 'Nombre', 'Precio', 'Stock', 'Costo']).set_index('ID_Producto')
        elif ws.title == "Clientes":
            return pd.DataFrame(columns=['Cedula', 'Nombre', 'Telefono', 'Direccion', 'Mascota', 'Tipo_Mascota'])
        elif ws.title == "Ventas":
            # 🟢 CLAVE PARA LA CORRECCIÓN: Definir las columnas necesarias
            return pd.DataFrame(columns=['ID_Venta', 'Fecha', 'Cedula_Cliente', 'Nombre_Cliente', 'Nombre_Mascota', 'Total_Venta', 'Items_Vendidos'])
        elif ws.title == "Gastos":
            # 🟢 CLAVE PARA LA CORRECCIÓN: Definir las columnas necesarias
            return pd.DataFrame(columns=['Fecha_Gasto', 'Concepto', 'Tipo_Gasto', 'Monto'])
        return pd.DataFrame()

# --- FUNCIONES DE ESCRITURA ESPECÍFICAS ---

def escribir_nuevo_cliente(ws_clientes, datos_cliente):
    """Escribe los datos de un nuevo cliente."""
    if ws_clientes:
        try:
            ws_clientes.append_row(datos_cliente)
            return True
        except Exception as e:
            st.error(f"Error al guardar el cliente: {e}")
            return False
    return False

def registrar_venta_y_actualizar_inventario(ws_ventas, ws_inventario, datos_venta, items_venta):
    """Guarda la venta y actualiza el inventario."""
    if ws_ventas and ws_inventario:
        try:
            # 1. Registrar la venta en la hoja de Ventas
            ws_ventas.append_row(datos_venta)
            
            # 2. Actualizar el inventario
            inventario_df = leer_datos(ws_inventario, index_col='ID_Producto')
            
            for item in items_venta:
                prod_id = item['ID_Producto']
                cantidad_vendida = item['Cantidad']
                
                # Buscar la fila por el ID_Producto (asume que está en la primera columna del Sheet)
                # Esta búsqueda es más lenta pero más segura que basarse en el index del DF local
                cell = ws_inventario.find(str(prod_id))
                if cell:
                    fila_a_actualizar = cell.row 
                    
                    # Columna 'Stock' (asume que es la columna D, que es 4)
                    # Debe coincidir con la columna real en Google Sheets
                    COLUMNA_STOCK = 4 

                    # Cargar el stock actual directamente de la celda
                    stock_actual_str = ws_inventario.cell(fila_a_actualizar, COLUMNA_STOCK).value
                    stock_actual = int(stock_actual_str) if stock_actual_str.isdigit() else 0
                    
                    nuevo_stock = stock_actual - cantidad_vendida
                    
                    if nuevo_stock >= 0:
                        ws_inventario.update_cell(fila_a_actualizar, COLUMNA_STOCK, nuevo_stock) 
                    else:
                         # Esto no debería pasar si la validación de stock es correcta en el POS,
                         # pero es un seguro
                        st.warning(f"Stock negativo detectado para {prod_id}. Revisar.")
            
            return True
        except Exception as e:
            st.error(f"🚨 Error al registrar la venta y actualizar inventario: {e}")
            return False
    return False

def registrar_gasto(ws_gastos, datos_gasto):
    """Registra un gasto en la hoja de Gastos."""
    if ws_gastos:
        try:
            ws_gastos.append_row(datos_gasto)
            return True
        except Exception as e:
            st.error(f"Error al guardar el gasto: {e}")
            return False
    return False

# --- COMPONENTES DE INTERFAZ DE USUARIO (UX/UI MEJORADO) ---

def buscar_cliente_ui(clientes_df, cedula_buscada):
    """Busca un cliente por cédula y retorna sus datos o None."""
    if not clientes_df.empty and cedula_buscada:
        cliente_encontrado = clientes_df[clientes_df['Cedula'].astype(str) == str(cedula_buscada)]
        if not cliente_encontrado.empty:
            return cliente_encontrado.iloc[0].to_dict()
    return None

def display_cliente_actual(cliente_info):
    """Muestra la información del cliente cargado con un estilo visual atractivo."""
    if cliente_info:
        nombre = cliente_info.get("Nombre", "Cliente Anónimo")
        mascota = cliente_info.get("Mascota", "Sin Mascota")
        cedula = cliente_info.get("Cedula", "N/A")
        st.markdown(f"""
            <div style="padding: 15px; border-radius: 10px; background-color: {COLOR_PRIMARIO}; color: white; margin-bottom: 20px;">
                <h4 style="margin: 0; color: white;">Cliente Activo: <b>{nombre.upper()}</b></h4>
                <p style="margin: 5px 0 0 0; font-size: 0.9em;">Cédula: {cedula} | Mascota: 🐾 {mascota}</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Sin cliente cargado. Usa la búsqueda o el registro para asociar la venta.")

def registrar_cliente_modal(ws_clientes):
    """Despliega un formulario de registro de cliente dentro de un `st.expander`."""
    with st.expander("➕ REGISTRO RÁPIDO DE CLIENTE NUEVO", expanded=False):
        st.subheader("Datos de Cliente y Mascota")
        with st.form("form_registro_cliente_venta"):
            c1, c2, c3 = st.columns(3)
            
            reg_cedula = c1.text_input("Cédula/ID (*)", max_chars=15, key="rc_venta")
            reg_nombre = c2.text_input("Nombre Completo (*)", key="rn_venta")
            reg_telefono = c3.text_input("Teléfono", key="rt_venta")
            
            c4, c5, c6 = st.columns(3)
            reg_mascota = c4.text_input("Nombre de la Mascota (*)", key="rm_venta")
            reg_tipo_mascota = c5.selectbox("Tipo de Mascota", ("Perro", "Gato", "Ave", "Otro"), key="rtm_venta")
            reg_direccion = c6.text_input("Dirección", key="rd_venta")
            
            submit_button = st.form_submit_button("💾 Guardar y Usar Cliente", type="primary")
            
            if submit_button:
                if reg_cedula and reg_nombre and reg_mascota:
                    datos_cliente = [reg_cedula, reg_nombre, reg_telefono, reg_direccion, reg_mascota, reg_tipo_mascota]
                    if escribir_nuevo_cliente(ws_clientes, datos_cliente):
                        st.session_state.cliente_actual = {
                            "Cedula": reg_cedula,
                            "Nombre": reg_nombre,
                            "Mascota": reg_mascota,
                            "Telefono": reg_telefono,
                            "Direccion": reg_direccion
                        }
                        st.toast("Cliente nuevo listo para la venta! 🎉", icon="🎉")
                        st.rerun() 
                else:
                    st.error("🚨 La Cédula, Nombre del Cliente y Nombre de la Mascota son obligatorios.")


# --- GENERACIÓN DE PDF (ReportLab Mejorado) ---
# ... Las funciones de PDF (generar_pdf_factura, generar_cuadre_caja_pdf) se mantienen igual 
# ya que ReportLab no depende de Streamlit y son correctas, solo ajustando los colores.

def generar_pdf_factura(datos_factura, items_venta):
    """Crea una factura PDF bonita con ReportLab y retorna los bytes y el total."""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)
    Story = []
    styles = getSampleStyleSheet()

    # Estilos personalizados (usando los nuevos colores)
    styles.add(ParagraphStyle(name='FacturaTitle', fontSize=20, fontName='Helvetica-Bold', alignment=1, spaceAfter=20, textColor=HexColor(COLOR_PRIMARIO)))
    styles.add(ParagraphStyle(name='FacturaHeader', fontSize=10, fontName='Helvetica-Bold', spaceAfter=2))
    styles.add(ParagraphStyle(name='FacturaBody', fontSize=10, fontName='Helvetica', spaceAfter=2))
    styles.add(ParagraphStyle(name='TotalStyle', fontSize=14, fontName='Helvetica-Bold', alignment=2, spaceBefore=10, textColor=HexColor(COLOR_PRIMARIO)))
    
    # --- Cabecera de la Factura ---
    Story.append(Paragraph('🐾 FACTURA DE VENTA - BIGOTES Y PATITAS 🐾', styles['FacturaTitle']))

    # Información de la tienda (en 2 columnas)
    header_data = [
        [
            Paragraph("<b>Bigotes y Patitas</b>", styles['FacturaHeader']), 
            Paragraph(f"<b>Factura #:</b> {datos_factura['ID_Venta']}", styles['FacturaHeader'])
        ],
        [
            Paragraph("Tienda de Mascotas - Tel: 555-PAW", styles['FacturaBody']), 
            Paragraph(f"<b>Fecha:</b> {datos_factura['Fecha'].split(' ')[0]}", styles['FacturaBody']) # Solo la fecha corta
        ]
    ]
    t_header = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
    t_header.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    Story.append(t_header)
    Story.append(Spacer(1, 0.2 * inch))

    # --- Información del Cliente ---
    Story.append(Paragraph(f'<font size="12" color="{COLOR_PRIMARIO}"><b>DATOS DEL CLIENTE</b></font>', styles['FacturaHeader']))
    cliente_data = [
        [
            Paragraph(f"<b>Nombre:</b> {datos_factura['Nombre_Cliente']}", styles['FacturaBody']),
            Paragraph(f"<b>Cédula:</b> {datos_factura['Cedula_Cliente']}", styles['FacturaBody'])
        ],
        [
            Paragraph(f"<b>Mascota:</b> {datos_factura['Nombre_Mascota']}", styles['FacturaBody']),
            Paragraph(f"<b>Teléfono:</b> {datos_factura.get('Telefono_Cliente', 'N/A')}", styles['FacturaBody'])
        ]
    ]
    t_cliente = Table(cliente_data, colWidths=[3.5*inch, 3.5*inch])
    t_cliente.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    Story.append(t_cliente)
    Story.append(Spacer(1, 0.3 * inch))
    
    # --- Tabla de Items ---
    data_table = [['ID', 'Producto', 'Precio Unit.', 'Cantidad', 'Subtotal']]
    total_general = 0
    for item in items_venta:
        # Asegurar que el precio sea numérico para el cálculo
        precio = item['Precio'] if isinstance(item['Precio'], (int, float)) else float(item['Precio'])
        cantidad = item['Cantidad']
        subtotal = precio * cantidad
        total_general += subtotal
        data_table.append([
            item['ID_Producto'],
            item['Nombre_Producto'],
            f"${precio:,.2f}",
            str(cantidad),
            f"${subtotal:,.2f}"
        ])

    t = Table(data_table, colWidths=[0.8*inch, 3.0*inch, 1.2*inch, 1.0*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor(COLOR_PRIMARIO)), 
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'), # Precios y Subtotal a la derecha
        ('ALIGN', (3, 1), (3, -1), 'CENTER'), # Cantidad al centro
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F0FFF4')), # Fondo más suave
        ('GRID', (0, 0), (-1, -1), 0.5, black),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6)
    ]))
    Story.append(t)
    Story.append(Spacer(1, 0.1 * inch))
    
    # --- Total General ---
    Story.append(Paragraph(f'TOTAL A PAGAR: ${total_general:,.2f}', styles['TotalStyle']))
    Story.append(Spacer(1, 0.5 * inch))

    # --- Mensaje de Agradecimiento y Pie de página ---
    styles.add(ParagraphStyle(name='Italic', fontSize=9, fontName='Helvetica-Oblique', textColor=HexColor('#666666')))
    Story.append(Paragraph('<i>¡Gracias por preferir Bigotes y Patitas! Vuelve pronto. Cuidamos a tu mejor amigo.</i>', styles['Italic']))

    # Construir el PDF
    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue(), total_general

def generar_cuadre_caja_pdf(ventas_df, gastos_df, fecha_cuadre, total_caja):
    """Crea un resumen de Cuadre de Caja en PDF."""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    Story = []
    styles = getSampleStyleSheet()
    # Usar los nuevos colores para más impacto
    styles.add(ParagraphStyle(name='CuadreTitle', fontSize=18, fontName='Helvetica-Bold', alignment=1, spaceAfter=20, textColor=HexColor(COLOR_PRIMARIO)))
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=14, fontName='Helvetica-Bold', spaceAfter=10, textColor=black))
    styles.add(ParagraphStyle(name='Metric', fontSize=16, fontName='Helvetica-Bold', alignment=2, textColor=HexColor('#333333')))

    # Título
    Story.append(Paragraph(f'📊 CIERRE DE CAJA DIARIO - {fecha_cuadre}', styles['CuadreTitle']))
    Story.append(Spacer(1, 0.2 * inch))

    # Resumen de totales
    Story.append(Paragraph(f"Total Ingresos (Ventas): <font color='{COLOR_PRIMARIO}'><b>${ventas_df['Total_Venta'].sum():,.2f}</b></font>", styles['Metric']))
    Story.append(Paragraph(f"Total Egresos (Gastos): <font color='#dc3545'><b>-${gastos_df['Monto'].sum():,.2f}</b></font>", styles['Metric']))
    Story.append(Paragraph(f"Total Neto de Caja: <font color='{COLOR_PRIMARIO if total_caja >= 0 else '#dc3545'}'><b>${total_caja:,.2f}</b></font>", styles['Metric']))
    Story.append(Spacer(1, 0.3 * inch))

    # Tabla de Ventas (detallada)
    Story.append(Paragraph("Detalle de Ventas:", styles['SectionHeader']))
    ventas_data = [['ID_Venta', 'Cliente', 'Total Venta']]
    for _, row in ventas_df.iterrows():
        ventas_data.append([
            row['ID_Venta'],
            row['Nombre_Cliente'],
            f"${row['Total_Venta']:,.2f}"
        ])
    t_ventas = Table(ventas_data, colWidths=[1.5*inch, 3.5*inch, 1.5*inch])
    t_ventas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor(COLOR_PRIMARIO)), 
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
    ]))
    Story.append(t_ventas)
    Story.append(PageBreak())

    # Tabla de Gastos (detallada)
    Story.append(Paragraph("Detalle de Gastos:", styles['SectionHeader']))
    gastos_data = [['Fecha', 'Concepto', 'Tipo', 'Monto']]
    for _, row in gastos_df.iterrows():
        gastos_data.append([
            row['Fecha_Gasto'],
            row['Concepto'],
            row['Tipo_Gasto'],
            f"${row['Monto']:,.2f}"
        ])
    t_gastos = Table(gastos_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 1.5*inch])
    t_gastos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor(COLOR_SECUNDARIO)), # Fondo suave (Dorado)
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
    ]))
    Story.append(t_gastos)

    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue()


# --- PÁGINAS PRINCIPALES DEL FLUJO DE TRABAJO ---

def page_nueva_venta(ws_inventario, ws_clientes, ws_ventas):
    """Página principal de Venta (POS) con UX/UI mejorado."""
    st.header("🛍️ Punto de Venta Premium")
    st.markdown("---")

    # Inicializar el carrito y el cliente si no existen
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state:
        st.session_state.cliente_actual = None

    inventario_df = leer_datos(ws_inventario, index_col='ID_Producto')
    clientes_df = leer_datos(ws_clientes, index_col=None) 

    # 1. Búsqueda y Carga de Cliente
    st.subheader("👤 Cliente de la Transacción")
    col_cedula, col_buscar, col_info = st.columns([3, 1, 3])

    cedula_input = col_cedula.text_input("Ingresa Cédula/ID:", key="cedula_venta_input", 
        value=st.session_state.cliente_actual['Cedula'] if st.session_state.cliente_actual else "")
    
    # 💥 Botón para Cargar Cliente
    if col_buscar.button("🔍 Cargar Cliente", type="secondary", use_container_width=True, disabled=not cedula_input):
        cliente_cargado = buscar_cliente_ui(clientes_df, cedula_input)
        if cliente_cargado:
            # Asegurar el mapeo de columnas si difiere (ej: Nombre_Completo vs Nombre)
            st.session_state.cliente_actual = {
                "Cedula": cliente_cargado.get('Cedula', ''),
                "Nombre": cliente_cargado.get('Nombre_Completo', cliente_cargado.get('Nombre', '')),
                "Mascota": cliente_cargado.get('Mascota', ''),
                "Telefono": cliente_cargado.get('Telefono', '')
            }
            st.toast(f"Cliente {st.session_state.cliente_actual['Nombre']} cargado con éxito. ✅")
        else:
            st.session_state.cliente_actual = None
            st.warning("Cliente no encontrado.")
            
    # Muestra los datos del cliente activo
    with col_info:
        display_cliente_actual(st.session_state.cliente_actual)
            
    # Opción para registrar nuevo cliente
    registrar_cliente_modal(ws_clientes)
    st.markdown("---")

    # 2. Carrito de Compras
    st.subheader("🛒 Agregar Productos")
    
    # Asegurar la conversión de tipos
    if not inventario_df.empty:
        inventario_df['Stock'] = pd.to_numeric(inventario_df['Stock'], errors='coerce').fillna(0).astype(int)
        inventario_df['Precio'] = pd.to_numeric(inventario_df['Precio'], errors='coerce').fillna(0.0)

        productos_disponibles = inventario_df[inventario_df['Stock'] > 0].apply(
            lambda row: f"{row['Nombre']} (Stock: {row['Stock']})", axis=1
        ).tolist()
        
        col_select, col_cant, col_precio, col_add = st.columns([4, 1, 1, 1])
        
        producto_seleccionado_str = col_select.selectbox("Seleccionar Producto:", [""] + productos_disponibles, key="prod_select")
        
        if producto_seleccionado_str:
            nombre_producto_real = producto_seleccionado_str.split(" (Stock:")[0]
            
            # Usar .name para obtener el índice/ID_Producto
            producto_info = inventario_df[inventario_df['Nombre'] == nombre_producto_real].iloc[0]
            stock_disp = producto_info['Stock']
            precio_unitario = producto_info['Precio']
            
            # Controles de cantidad y precio
            cantidad = col_cant.number_input(f"Cant.", min_value=1, max_value=int(stock_disp), value=1, step=1, key="cantidad_item")
            col_precio.metric("P. Unitario", f"${precio_unitario:,.2f}")

            # 💥 Botón para añadir
            if col_add.button("➕ Añadir", type="primary", use_container_width=True):
                if cantidad > 0 and cantidad <= stock_disp:
                    item_carrito = {
                        "ID_Producto": producto_info.name,
                        "Nombre_Producto": nombre_producto_real,
                        "Precio": precio_unitario,
                        "Cantidad": cantidad,
                        "Subtotal": precio_unitario * cantidad
                    }
                    st.session_state.carrito.append(item_carrito)
                    st.toast(f"Se añadió {cantidad} de {nombre_producto_real}", icon="🛒")
                    st.rerun() 
                else:
                    st.error("Cantidad inválida o superior al stock disponible.")
    else:
        st.warning("⚠️ Inventario no disponible o vacío.")

    st.markdown("---")
    
    # 3. Resumen y Finalización
    st.subheader("🧾 Resumen de la Venta")

    if st.session_state.carrito:
        carrito_df = pd.DataFrame(st.session_state.carrito)
        
        col_data, col_actions = st.columns([5, 1])
        
        with col_data:
            carrito_df_mostrar = carrito_df[['Nombre_Producto', 'Cantidad', 'Precio', 'Subtotal']]
            carrito_df_mostrar.columns = ['Producto', 'Cant.', 'P. Unitario', 'Subtotal']
            
            # Formateo visual
            st.dataframe(
                carrito_df_mostrar,
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "P. Unitario": st.column_config.NumberColumn(format="$%.2f"),
                    "Subtotal": st.column_config.NumberColumn(format="$%.2f")
                }
            )
            
            total_venta = carrito_df['Subtotal'].sum()
            st.markdown(f'<div style="text-align: right; font-size: 2em; color: {COLOR_PRIMARIO}; font-weight: 900;">TOTAL: ${total_venta:,.2f}</div>', unsafe_allow_html=True)

        with col_actions:
            if st.button("🗑️ Vaciar", type="secondary", use_container_width=True):
                st.session_state.carrito = []
                st.toast("Carrito vaciado.", icon="🧹")
                st.rerun()

            if st.button("💰 Finalizar Venta", type="primary", use_container_width=True, disabled=st.session_state.cliente_actual is None):
                
                if st.session_state.cliente_actual is None or not st.session_state.cliente_actual.get("Cedula"):
                    st.error("🚨 Debes cargar o registrar un cliente antes de finalizar.")
                    return # Salir si el cliente no está bien cargado

                # Datos para la Venta (para el PDF y la DB)
                id_venta = datetime.now().strftime("%Y%m%d%H%M%S") # ID de venta único
                fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                datos_factura = {
                    "ID_Venta": id_venta,
                    "Fecha": fecha_str,
                    "Nombre_Cliente": st.session_state.cliente_actual.get("Nombre", "Cliente Anónimo"),
                    "Cedula_Cliente": st.session_state.cliente_actual.get("Cedula", "SIN_ID"),
                    "Nombre_Mascota": st.session_state.cliente_actual.get("Mascota", "SIN_MASCOTA"),
                    "Telefono_Cliente": st.session_state.cliente_actual.get("Telefono")
                }

                # 1. Generar el PDF
                pdf_bytes, total_venta_final = generar_pdf_factura(datos_factura, st.session_state.carrito)
                
                # 2. Registrar la Venta y Actualizar Inventario
                datos_venta_db = [
                    id_venta,
                    fecha_str,
                    datos_factura['Cedula_Cliente'],
                    datos_factura['Nombre_Cliente'],
                    datos_factura['Nombre_Mascota'],
                    total_venta_final, # Asegúrate de que Google Sheets acepte el número sin formato
                    "; ".join([f"{i['Nombre_Producto']} ({i['Cantidad']})" for i in st.session_state.carrito])
                ]
                
                if registrar_venta_y_actualizar_inventario(ws_ventas, ws_inventario, datos_venta_db, st.session_state.carrito):
                    # 3. Mostrar el botón de descarga del PDF
                    st.balloons()
                    st.success("🎉 ¡Venta y registro de inventario completados!")
                    st.download_button(
                        label="⬇️ Descargar Factura PDF",
                        data=pdf_bytes,
                        file_name=f"Factura_{id_venta}.pdf",
                        mime="application/pdf"
                    )
                    st.session_state.carrito = [] # Limpiar el carrito
                    st.session_state.cliente_actual = None # Limpiar cliente
                    st.rerun() # Refrescar la página

    else:
        st.info("El carrito está vacío. ¡Comencemos a vender!")


def page_gestion_gastos(ws_gastos):
    """Página para registrar y visualizar gastos."""
    st.header("💸 Gestión de Gastos y Egresos")
    st.markdown("---")

    # 1. Formulario de Registro de Gasto
    with st.container(border=True):
        st.subheader("➕ Registro Express")
        with st.form("form_registro_gasto", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.5, 2, 1.5])
            
            fecha_gasto = c1.date_input("Fecha del Gasto", value=datetime.now().date())
            monto = c2.number_input("Monto ($)", min_value=0.0, format="%.2f", key="monto_gasto")
            tipo_gasto = c3.selectbox("Tipo de Gasto", ["Fijo", "Variable", "Inversión", "Operativo"], key="tipo_gasto_select")
            
            concepto = st.text_input("Concepto (Ej: Pago de Luz, Compra de Arena para Gato, Salario Empleado)", key="concepto_gasto")
            
            submit_button = st.form_submit_button("💾 Guardar Gasto", type="primary")
            
            if submit_button:
                if monto > 0 and concepto:
                    datos_gasto = [
                        fecha_gasto.strftime("%d/%m/%Y"), 
                        concepto, 
                        tipo_gasto, 
                        monto
                    ]
                    if registrar_gasto(ws_gastos, datos_gasto):
                         st.toast("Gasto guardado. 👍", icon="✅")
                         st.rerun()
                else:
                    st.error("🚨 Monto debe ser mayor a 0 y el Concepto es obligatorio.")

    st.markdown("---")

    # 2. Visualización de Gastos
    st.subheader("Historial y Análisis de Egresos")
    gastos_df = leer_datos(ws_gastos, index_col=None)
    
    if not gastos_df.empty:
        # Convertir 'Monto' a numérico (asegurar robustez)
        gastos_df['Monto'] = pd.to_numeric(gastos_df['Monto'], errors='coerce').fillna(0)
        
        # Filtro por mes/año
        # Asume que 'Fecha_Gasto' está en formato dd/mm/yyyy
        gastos_df['Mes_Año'] = gastos_df['Fecha_Gasto'].str[-7:]
        meses_disponibles = sorted(list(set(gastos_df['Mes_Año'])), reverse=True) 
        mes_seleccionado = st.selectbox("Filtrar por Mes (mm/yyyy)", ["Todos"] + meses_disponibles)
        
        if mes_seleccionado != "Todos":
            gastos_filtrados_df = gastos_df[gastos_df['Mes_Año'] == mes_seleccionado].drop(columns=['Mes_Año'])
        else:
            gastos_filtrados_df = gastos_df.drop(columns=['Mes_Año'])

        col_total, col_tipo = st.columns(2)
        
        # Métrica Total
        col_total.metric("Total de Gastos en el periodo", f"${gastos_filtrados_df['Monto'].sum():,.2f}", delta_color="inverse")
        
        # Visualización de gastos por tipo (Gráfico de barras)
        if not gastos_filtrados_df.empty:
             Image of a bar chart showing spending by Type of Expense with a vibrant green and orange color scheme
            gasto_por_tipo = gastos_filtrados_df.groupby('Tipo_Gasto')['Monto'].sum().sort_values(ascending=False)
            
            # Gráfico de barras (Streamlit usa Plotly o Altair, este es un ejemplo conceptual)
            col_tipo.bar_chart(gasto_por_tipo, color=COLOR_PRIMARIO)
            
            st.dataframe(gastos_filtrados_df.sort_values(by='Fecha_Gasto', ascending=False), use_container_width=True, hide_index=True)
            
    else:
        st.info("No hay gastos registrados. Usa el formulario de arriba para empezar.")


def page_gestion_gastos(ws_gastos):
    """Página para registrar y visualizar gastos."""
    st.header("💸 Gestión de Gastos y Egresos")
    st.markdown("---")

    # 1. Formulario de Registro de Gasto
    with st.container(border=True):
        st.subheader("➕ Registro Express")
        with st.form("form_registro_gasto", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.5, 2, 1.5])
            
            fecha_gasto = c1.date_input("Fecha del Gasto", value=datetime.now().date())
            monto = c2.number_input("Monto ($)", min_value=0.0, format="%.2f", key="monto_gasto")
            tipo_gasto = c3.selectbox("Tipo de Gasto", ["Fijo", "Variable", "Inversión", "Operativo"], key="tipo_gasto_select")
            
            concepto = st.text_input("Concepto (Ej: Pago de Luz, Compra de Arena para Gato, Salario Empleado)", key="concepto_gasto")
            
            submit_button = st.form_submit_button("💾 Guardar Gasto", type="primary")
            
            if submit_button:
                if monto > 0 and concepto:
                    datos_gasto = [
                        fecha_gasto.strftime("%d/%m/%Y"), 
                        concepto, 
                        tipo_gasto, 
                        monto
                    ]
                    if registrar_gasto(ws_gastos, datos_gasto):
                         st.toast("Gasto guardado. 👍", icon="✅")
                         st.rerun()
                else:
                    st.error("🚨 Monto debe ser mayor a 0 y el Concepto es obligatorio.")

    st.markdown("---")

    # 2. Visualización de Gastos
    st.subheader("Historial y Análisis de Egresos")
    gastos_df = leer_datos(ws_gastos, index_col=None)
    
    if not gastos_df.empty:
        # Convertir 'Monto' a numérico (asegurar robustez)
        gastos_df['Monto'] = pd.to_numeric(gastos_df['Monto'], errors='coerce').fillna(0)
        
        # Filtro por mes/año
        # Asume que 'Fecha_Gasto' está en formato dd/mm/yyyy
        gastos_df['Mes_Año'] = gastos_df['Fecha_Gasto'].str[-7:]
        meses_disponibles = sorted(list(set(gastos_df['Mes_Año'])), reverse=True) 
        mes_seleccionado = st.selectbox("Filtrar por Mes (mm/yyyy)", ["Todos"] + meses_disponibles)
        
        if mes_seleccionado != "Todos":
            gastos_filtrados_df = gastos_df[gastos_df['Mes_Año'] == mes_seleccionado].drop(columns=['Mes_Año'])
        else:
            gastos_filtrados_df = gastos_df.drop(columns=['Mes_Año'])

        col_total, col_tipo = st.columns(2)
        
        # Métrica Total
        col_total.metric("Total de Gastos en el periodo", f"${gastos_filtrados_df['Monto'].sum():,.2f}", delta_color="inverse")
        
        # Visualización de gastos por tipo (Gráfico de barras)
        if not gastos_filtrados_df.empty:
            # CORRECCIÓN: Esta línea ahora es un comentario real
            # 
            gasto_por_tipo = gastos_filtrados_df.groupby('Tipo_Gasto')['Monto'].sum().sort_values(ascending=False)
            
            # Gráfico de barras
            col_tipo.bar_chart(gasto_por_tipo, color=COLOR_PRIMARIO)
            
            st.dataframe(gastos_filtrados_df.sort_values(by='Fecha_Gasto', ascending=False), use_container_width=True, hide_index=True)
            
    else:
        st.info("No hay gastos registrados. Usa el formulario de arriba para empezar.")

    st.markdown("---")
    
    # 4. Botón de Descarga
    col_pdf, col_desc = st.columns(2)
    
    if col_pdf.button("📄 Generar Cuadre de Caja (PDF)", use_container_width=True, type="secondary"):
        if total_ingresos != 0 or total_egresos != 0:
            pdf_cuadre_bytes = generar_cuadre_caja_pdf(ventas_del_dia_df, gastos_del_dia_df, fecha_cierre_str, total_caja_neto)
            col_desc.download_button(
                label="⬇️ Descargar Cuadre de Caja PDF",
                data=pdf_cuadre_bytes,
                file_name=f"Cuadre_Caja_{fecha_cierre_str.replace('/', '-')}.pdf",
                mime="application/pdf"
            )
            st.toast("PDF Generado.", icon="📄")
        else:
            st.warning("No hay movimientos (ingresos/egresos) para generar un cuadre en este día.")


# --- FUNCIÓN PRINCIPAL ---

def main():
    # 1. Configuración y Conexión
    configurar_pagina()
    ws_inventario, ws_clientes, ws_ventas, ws_gastos = conectar_google_sheets()

    if ws_inventario is None:
        st.stop() # Detiene la ejecución si la conexión falla

    # 2. Sidebar para Navegación Administrativa
    st.sidebar.header("Menú de Gestión ⚙️")
    
    opcion_gestion = st.sidebar.radio(
        "Reportes y Control:",
        ('📋 Inventario', '💸 Gastos', '💰 Cuadre de Caja'),
        key="sidebar_management"
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("Hecho con 💖 para Bigotes y Patitas")

    # 3. CONTENIDO PRINCIPAL (Navegación por Pestañas para el POS)
    tab_venta, tab_admin = st.tabs(["🛍️ NUEVA VENTA (POS)", "PANEL ADMINISTRATIVO"])

    with tab_venta:
        page_nueva_venta(ws_inventario, ws_clientes, ws_ventas)

    with tab_admin:
        if opcion_gestion == '📋 Inventario':
            st.header("📋 Inventario Actual")
            st.markdown("---")
            inventario_df = leer_datos(ws_inventario, index_col='ID_Producto')
            
            if not inventario_df.empty:
                # Asegurar que las columnas existan y sean numéricas para el formato
                inventario_df['Precio'] = pd.to_numeric(inventario_df['Precio'], errors='coerce').fillna(0.0)
                inventario_df['Costo'] = pd.to_numeric(inventario_df['Costo'], errors='coerce').fillna(0.0)
                inventario_df['Stock'] = pd.to_numeric(inventario_df['Stock'], errors='coerce').fillna(0)

                st.dataframe(
                    inventario_df[['Nombre', 'Precio', 'Stock', 'Costo']],
                    use_container_width=True,
                    column_config={
                        "Precio": st.column_config.NumberColumn("Precio Venta ($)", format="$%.2f"),
                        "Costo": st.column_config.NumberColumn("Costo Compra ($)", format="$%.2f"),
                        "Stock": st.column_config.NumberColumn("Stock Disponible", format="%d unidades")
                    }
                )
                
                # Alerta para bajo stock
                stock_bajo = inventario_df[inventario_df['Stock'] < 5] 
                if not stock_bajo.empty:
                    st.error("🚨 Alerta Crítica: Bajo Stock en los siguientes productos. ¡Pide reposición ya!")
                    st.table(stock_bajo[['Nombre', 'Stock']])
                else:
                    st.success("Inventario en buen estado. ¡Sigue vendiendo!")
            else:
                st.warning("⚠️ El inventario está vacío o no se pudo cargar correctamente.")

        elif opcion_gestion == '💸 Gastos':
            page_gestion_gastos(ws_gastos)
            
        elif opcion_gestion == '💰 Cuadre de Caja':
            page_cuadre_caja_y_rentabilidad(ws_ventas, ws_gastos)


if __name__ == "__main__":
    main()
