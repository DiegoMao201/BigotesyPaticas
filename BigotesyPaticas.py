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
import calendar # Para el Cuadre de Caja

# --- CONFIGURACIÓN DE PÁGINA Y ESTILOS GLOBALES ---

# Color principal para Bigotes y Patitas (Verde amigable)
COLOR_PRIMARIO = "#4CAF50" 
COLOR_SECUNDARIO = "#FF9800" # Naranja para alertas/mascotas

def configurar_pagina():
    """Configura la apariencia inicial de la aplicación."""
    st.set_page_config(
        page_title="🐾 Bigotes y Patitas - POS y Gestión",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Estilo CSS para mejor visual (más limpio y moderno)
    st.markdown(f"""
        <style>
        /* Título Principal más impactante */
        .big-title {{
            font-size: 3em;
            color: {COLOR_PRIMARIO}; 
            text-align: center;
            margin-bottom: 20px;
            font-weight: 700;
            text-shadow: 1px 1px 2px #ccc;
        }}
        /* Estilo para los subtítulos de las pestañas */
        h2 {{
            color: {COLOR_PRIMARIO};
            border-bottom: 2px solid {COLOR_PRIMARIO};
            padding-bottom: 5px;
        }}
        /* Mejorar la apariencia del botón primario */
        .stButton button[data-testid="stFormSubmitButton"], 
        .stButton button:focus:not([data-testid="baseButton-secondary"]) {{
            background-color: {COLOR_PRIMARIO} !important;
            border-color: {COLOR_PRIMARIO} !important;
            color: white !important;
            font-weight: bold;
        }}
        /* Estilo para las métricas (Key Performance Indicators) */
        [data-testid="stMetricValue"] {{
            font-size: 2.5rem;
            color: {COLOR_PRIMARIO};
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # Título y Logo
    col1, col2 = st.columns([1, 6])
    # Intentar cargar el logo (asumiendo que 'BigotesyPaticas.png' existe)
    try:
        col1.image("BigotesyPaticas.png", width=120) 
    except:
        # Si no lo encuentra, mostrar un ícono grande
        col1.markdown(f'<p style="font-size: 70px; text-align: center;">🐾</p>', unsafe_allow_html=True)

    col2.markdown('<div class="big-title">Bigotes y Patitas - Sistema de Gestión Premium</div>', unsafe_allow_html=True)
    st.markdown("---")


# --- CONEXIÓN A GOOGLE SHEETS Y LECTURA/ESCRITURA BÁSICA ---

@st.cache_resource
def conectar_google_sheets():
    """Establece y cachea la conexión a Google Sheets. Retorna los Worksheets."""
    try:
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        SHEET_URL = st.secrets["SHEET_URL"] # Mejor usar un secreto para la URL
        hoja = gc.open_by_url(SHEET_URL)
        
        # Se asumen los nombres de las hojas (crea las que no existan en tu archivo)
        ws_inventario = hoja.worksheet("Inventario")
        ws_clientes = hoja.worksheet("Clientes")
        ws_ventas = hoja.worksheet("Ventas")
        ws_gastos = hoja.worksheet("Gastos") # Nueva hoja
        
        return ws_inventario, ws_clientes, ws_ventas, ws_gastos
    except Exception as e:
        st.error(f"🚨 Error crítico al conectar con Google Sheets. Revisa la URL y tus credenciales 'google_service_account'. Detalle: {e}")
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
        st.error(f"Error al leer la hoja '{ws.title}': {e}")
        return pd.DataFrame()

# --- FUNCIONES DE ESCRITURA ESPECÍFICAS ---

def escribir_nuevo_cliente(ws_clientes, datos_cliente):
    """Escribe los datos de un nuevo cliente."""
    if ws_clientes:
        try:
            # Asegúrate que el orden de datos_cliente coincida con las columnas en Google Sheets
            ws_clientes.append_row(datos_cliente)
            st.success("✅ Cliente registrado exitosamente!")
            return True
        except Exception as e:
            st.error(f"Error al guardar el cliente: {e}")
            return False

def registrar_venta_y_actualizar_inventario(ws_ventas, ws_inventario, datos_venta, items_venta):
    """Guarda la venta y actualiza el inventario."""
    if ws_ventas and ws_inventario:
        try:
            # 1. Registrar la venta en la hoja de Ventas
            ws_ventas.append_row(datos_venta)
            
            # 2. Actualizar el inventario
            # Lee el inventario (se asume que 'ID_Producto' es el índice)
            inventario_df = leer_datos(ws_inventario, index_col='ID_Producto')
            
            for item in items_venta:
                prod_id = item['ID_Producto']
                cantidad_vendida = item['Cantidad']
                
                # Obtener la posición de la fila en el DataFrame (+2 para gspread, que es 1-basado y tiene header)
                # Esta es una forma más robusta de encontrar la fila para la actualización
                fila_idx_df = inventario_df.index.get_loc(prod_id)
                fila_a_actualizar = fila_idx_df + 2 
                
                # Nueva cantidad de stock
                nuevo_stock = inventario_df.loc[prod_id, 'Stock'] - cantidad_vendida
                
                # Columna 'Stock' se asume que es la columna D (4)
                ws_inventario.update_cell(fila_a_actualizar, 4, nuevo_stock) 
            
            st.success("✅ Venta registrada y inventario actualizado correctamente.")
            return True
        except Exception as e:
            st.error(f"🚨 Error al registrar la venta y actualizar inventario: {e}")
            return False

# --- COMPONENTES DE INTERFAZ DE USUARIO (UX/UI MEJORADO) ---

def buscar_cliente_ui(clientes_df, cedula_buscada):
    """Busca un cliente por cédula y retorna sus datos o None."""
    if not clientes_df.empty and cedula_buscada:
        cliente_encontrado = clientes_df[clientes_df['Cedula'] == cedula_buscada]
        if not cliente_encontrado.empty:
            st.success(f"Cliente '{cliente_encontrado['Nombre'].iloc[0]}' encontrado.")
            # Retorna el primer resultado como un diccionario/Serie de Pandas
            return cliente_encontrado.iloc[0].to_dict()
    return None

def registrar_cliente_modal(ws_clientes):
    """Despliega un formulario de registro de cliente dentro de un `st.expander`."""
    with st.expander("➕ Registrar Cliente Nuevo (Si no existe)", expanded=False):
        st.subheader("Datos de Cliente y Mascota")
        with st.form("form_registro_cliente_venta"):
            c1, c2 = st.columns(2)
            c3, c4 = st.columns(2)
            c5, c6 = st.columns(2)
            
            # Campos obligatorios para la DB
            reg_cedula = c1.text_input("Cédula/ID (*)", max_chars=15, key="rc_venta")
            reg_nombre = c2.text_input("Nombre Completo (*)", key="rn_venta")
            reg_mascota = c5.text_input("Nombre de la Mascota (*)", key="rm_venta")
            
            # Campos opcionales
            reg_telefono = c3.text_input("Teléfono", key="rt_venta")
            reg_direccion = c4.text_input("Dirección", key="rd_venta")
            reg_tipo_mascota = c6.selectbox("Tipo de Mascota", ("Perro", "Gato", "Ave", "Otro"), key="rtm_venta")
            
            submit_button = st.form_submit_button("💾 Guardar y Usar Cliente")
            
            if submit_button:
                if reg_cedula and reg_nombre and reg_mascota:
                    datos_cliente = [reg_cedula, reg_nombre, reg_telefono, reg_direccion, reg_mascota, reg_tipo_mascota]
                    if escribir_nuevo_cliente(ws_clientes, datos_cliente):
                        # Simular la carga del cliente recién creado al estado de sesión
                        st.session_state.cliente_actual = {
                            "Cedula": reg_cedula,
                            "Nombre": reg_nombre,
                            "Mascota": reg_mascota,
                            "Telefono": reg_telefono,
                            "Direccion": reg_direccion
                        }
                        st.toast("Cliente nuevo listo para la venta!", icon="🎉")
                        st.rerun() # Refrescar para usar el cliente
                else:
                    st.error("🚨 La Cédula, Nombre del Cliente y Nombre de la Mascota son obligatorios.")

# --- GENERACIÓN DE PDF (ReportLab Mejorado) ---

def generar_pdf_factura(datos_factura, items_venta):
    """Crea una factura PDF bonita con ReportLab y retorna los bytes y el total."""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)
    Story = []
    styles = getSampleStyleSheet()

    # Estilos personalizados
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
            Paragraph(f"<b>Fecha:</b> {datos_factura['Fecha']}", styles['FacturaBody'])
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
        subtotal = item['Precio'] * item['Cantidad']
        total_general += subtotal
        data_table.append([
            item['ID_Producto'],
            item['Nombre_Producto'],
            f"${item['Precio']:,.2f}",
            str(item['Cantidad']),
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
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F5F5F5')), # Franja de fondo
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
    Story.append(Paragraph('<i>¡Gracias por preferir Bigotes y Patitas! Vuelve pronto. Cuidamos a tu mejor amigo.</i>', styles['Italic']))

    # Construir el PDF
    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue(), total_general


# --- MANEJO DE GASTOS Y CIERRES (NUEVAS FUNCIONES) ---

def registrar_gasto(ws_gastos, datos_gasto):
    """Registra un gasto en la hoja de Gastos."""
    if ws_gastos:
        try:
            ws_gastos.append_row(datos_gasto)
            st.success("✅ Gasto registrado exitosamente.")
            return True
        except Exception as e:
            st.error(f"Error al guardar el gasto: {e}")
            return False

def generar_cuadre_caja_pdf(ventas_df, gastos_df, fecha_cuadre, total_caja):
    """Crea un resumen de Cuadre de Caja en PDF."""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    Story = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CuadreTitle', fontSize=18, fontName='Helvetica-Bold', alignment=1, spaceAfter=20, textColor=blue))
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=14, fontName='Helvetica-Bold', spaceAfter=10, textColor=black))
    styles.add(ParagraphStyle(name='Metric', fontSize=16, fontName='Helvetica-Bold', alignment=2, textColor=HexColor(COLOR_PRIMARIO)))

    # Título
    Story.append(Paragraph(f'📊 CIERRE DE CAJA DIARIO - {fecha_cuadre}', styles['CuadreTitle']))
    Story.append(Spacer(1, 0.2 * inch))

    # Resumen de totales
    Story.append(Paragraph(f"Total Ingresos (Ventas): ${ventas_df['Total_Venta'].sum():,.2f}", styles['Metric']))
    Story.append(Paragraph(f"Total Egresos (Gastos): -${gastos_df['Monto'].sum():,.2f}", styles['Metric']))
    Story.append(Paragraph(f"Total Neto de Caja: ${total_caja:,.2f}", styles['Metric']))
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
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#D9EAD3')), # Fondo suave
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
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#FEE3CC')), # Fondo suave (Naranja)
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
    ]))
    Story.append(t_gastos)

    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue()


# --- PÁGINAS PRINCIPALES DEL FLUJO DE TRABAJO ---

def page_nueva_venta(ws_inventario, ws_clientes, ws_ventas):
    """Página principal de Venta con carrito de compras."""
    st.header("🛍️ Punto de Venta (POS)")
    st.markdown("---")

    # Inicializar el carrito y el cliente si no existen
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state:
        st.session_state.cliente_actual = None

    inventario_df = leer_datos(ws_inventario, index_col='ID_Producto')
    clientes_df = leer_datos(ws_clientes, index_col=None) # Los clientes se indexan por 'Cedula' si es la primera col.

    # 1. Búsqueda y Carga de Cliente
    col_cedula, col_buscar = st.columns([3, 1])
    cedula_input = col_cedula.text_input("Cédula del Cliente", key="cedula_venta_input", value=st.session_state.cliente_actual['Cedula'] if st.session_state.cliente_actual else "")

    if col_buscar.button("🔍 Cargar Cliente", use_container_width=True, disabled=not cedula_input):
        cliente_cargado = buscar_cliente_ui(clientes_df, cedula_input)
        if cliente_cargado:
            st.session_state.cliente_actual = {
                "Cedula": cliente_cargado.get('Cedula', ''),
                "Nombre": cliente_cargado.get('Nombre_Completo', cliente_cargado.get('Nombre', '')), # Adaptar al nombre de tu columna
                "Mascota": cliente_cargado.get('Nombre_Mascota', ''),
                "Telefono": cliente_cargado.get('Telefono', '')
            }
            st.toast(f"Cliente {st.session_state.cliente_actual['Nombre']} cargado.")
        else:
            st.session_state.cliente_actual = None
            st.warning("Cliente no encontrado. Puedes registrarlo o continuar con los datos de venta.")
    
    # Mostrar datos del cliente cargado
    if st.session_state.cliente_actual:
        st.info(f"👤 **Cliente:** {st.session_state.cliente_actual.get('Nombre')} | **Mascota:** {st.session_state.cliente_actual.get('Mascota')}")
    else:
        st.warning("⚠️ Sin cliente cargado. Completa la Cédula/Nombre de Mascota al finalizar.")
        
    # Opción para registrar nuevo cliente
    registrar_cliente_modal(ws_clientes)
    st.markdown("---")

    # 2. Carrito de Compras
    st.subheader("🛒 Agregar Productos")

    if not inventario_df.empty:
        # Crea una lista de opciones con el nombre y el stock
        productos_disponibles = inventario_df.apply(lambda row: f"{row['Nombre']} (Stock: {row['Stock']})", axis=1).tolist()
        
        col_select, col_cant, col_add = st.columns([4, 1, 1])
        
        producto_seleccionado_str = col_select.selectbox("Seleccionar Producto:", [""] + productos_disponibles)
        
        if producto_seleccionado_str:
            # Extraer el nombre real (antes del " (Stock:...")
            nombre_producto_real = producto_seleccionado_str.split(" (Stock:")[0]
            
            producto_info = inventario_df[inventario_df['Nombre'] == nombre_producto_real].iloc[0]
            stock_disp = producto_info['Stock']
            
            cantidad = col_cant.number_input(f"Cant.", min_value=1, max_value=int(stock_disp), value=1, step=1, key="cantidad_item")
            
            precio_unitario = producto_info['Precio']
            col_cant.markdown(f"**Precio:** ${precio_unitario:,.2f}")

            if col_add.button("➕ Añadir", use_container_width=True):
                if cantidad > 0 and cantidad <= stock_disp:
                    item_carrito = {
                        "ID_Producto": producto_info.name,
                        "Nombre_Producto": nombre_producto_real,
                        "Precio": precio_unitario,
                        "Cantidad": cantidad,
                        "Subtotal": precio_unitario * cantidad
                    }
                    st.session_state.carrito.append(item_carrito)
                    st.toast(f"Se añadió {cantidad} de {nombre_producto_real}")
                    st.rerun() # Recargar para limpiar el selectbox y actualizar el stock
                else:
                    st.error("Cantidad inválida o superior al stock disponible.")
    else:
        st.warning("⚠️ No se pudo cargar el inventario. Revisa la conexión a Google Sheets.")

    st.markdown("---")
    
    # 3. Resumen y Finalización
    st.subheader("🧾 Resumen de la Venta")

    if st.session_state.carrito:
        carrito_df = pd.DataFrame(st.session_state.carrito)
        
        # Opciones para modificar el carrito
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
            st.markdown(f"### **TOTAL A PAGAR: ${total_venta:,.2f}**")
        
        with col_actions:
            if st.button("🗑️ Vaciar Carrito", type="secondary", use_container_width=True):
                st.session_state.carrito = []
                st.toast("Carrito vaciado.", icon="🧹")
                st.rerun()

            if st.button("💰 Finalizar Venta y Facturar", type="primary", use_container_width=True):
                # Validar datos mínimos de cliente
                if not st.session_state.cliente_actual:
                    st.error("🚨 Debes cargar o registrar un cliente antes de finalizar.")
                else:
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
                    # Asegúrate que el orden coincida con el encabezado de tu hoja 'Ventas'
                    datos_venta_db = [
                        id_venta,
                        fecha_str,
                        datos_factura['Cedula_Cliente'],
                        datos_factura['Nombre_Cliente'],
                        datos_factura['Nombre_Mascota'],
                        total_venta_final,
                        "; ".join([f"{i['Nombre_Producto']} ({i['Cantidad']})" for i in st.session_state.carrito])
                    ]
                    
                    if registrar_venta_y_actualizar_inventario(ws_ventas, ws_inventario, datos_venta_db, st.session_state.carrito):
                        # 3. Mostrar el botón de descarga del PDF
                        st.balloons()
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
        st.info("El carrito está vacío. Agrega productos para continuar.")


def page_gestion_gastos(ws_gastos):
    """Página para registrar y visualizar gastos."""
    st.header("💸 Gestión de Gastos")
    st.markdown("---")

    # 1. Formulario de Registro de Gasto
    st.subheader("➕ Registrar Nuevo Gasto")
    with st.form("form_registro_gasto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)
        
        fecha_gasto = c1.date_input("Fecha del Gasto", value=datetime.now().date())
        monto = c2.number_input("Monto ($)", min_value=0.0, format="%.2f")
        
        concepto = c3.text_input("Concepto (Ej: Alquiler, Sueldo, Compras)")
        tipo_gasto = c4.selectbox("Tipo de Gasto", ["Fijo", "Variable", "Inversión"])
        
        submit_button = st.form_submit_button("💾 Guardar Gasto")
        
        if submit_button:
            if monto > 0 and concepto:
                datos_gasto = [
                    fecha_gasto.strftime("%d/%m/%Y"), 
                    concepto, 
                    tipo_gasto, 
                    monto
                    # Agrega más campos si tu hoja 'Gastos' los tiene (Ej: ID de Transacción)
                ]
                registrar_gasto(ws_gastos, datos_gasto)
            else:
                st.error("🚨 Monto debe ser mayor a 0 y el Concepto es obligatorio.")

    st.markdown("---")

    # 2. Visualización de Gastos
    st.subheader("Historial de Gastos")
    gastos_df = leer_datos(ws_gastos, index_col=None)
    
    if not gastos_df.empty:
        # Convertir 'Monto' a numérico
        gastos_df['Monto'] = pd.to_numeric(gastos_df['Monto'], errors='coerce').fillna(0)
        
        # Filtro por mes
        meses_disponibles = sorted(list(set(gastos_df['Fecha_Gasto'].apply(lambda x: x[-7:])))) # Asume formato dd/mm/yyyy
        mes_seleccionado = st.selectbox("Filtrar por Mes (mm/yyyy)", ["Todos"] + meses_disponibles)
        
        if mes_seleccionado != "Todos":
            gastos_filtrados_df = gastos_df[gastos_df['Fecha_Gasto'].str.endswith(mes_seleccionado)]
        else:
            gastos_filtrados_df = gastos_df

        st.dataframe(gastos_filtrados_df, use_container_width=True, hide_index=True)
        st.metric("Total de Gastos en el periodo", f"${gastos_filtrados_df['Monto'].sum():,.2f}")
    else:
        st.info("No hay gastos registrados.")


def page_cuadre_caja_y_rentabilidad(ws_ventas, ws_gastos):
    """Página para el cierre de caja y análisis de rentabilidad simple."""
    st.header("💰 Cuadre de Caja y Rentabilidad Diaria")
    st.markdown("---")

    ventas_df = leer_datos(ws_ventas, index_col=None)
    gastos_df = leer_datos(ws_gastos, index_col=None)

    # Preparar datos
    if ventas_df.empty or 'Total_Venta' not in ventas_df.columns:
        ventas_df = pd.DataFrame(columns=['Fecha', 'Total_Venta'])
    else:
        ventas_df['Total_Venta'] = pd.to_numeric(ventas_df['Total_Venta'], errors='coerce').fillna(0)
        ventas_df['Fecha_Corta'] = ventas_df['Fecha'].apply(lambda x: x.split(' ')[0])

    if gastos_df.empty or 'Monto' not in gastos_df.columns:
        gastos_df = pd.DataFrame(columns=['Fecha_Gasto', 'Monto'])
    else:
        gastos_df['Monto'] = pd.to_numeric(gastos_df['Monto'], errors='coerce').fillna(0)
        
    # Selector de fecha para el cierre
    fecha_cierre = st.date_input("Selecciona la Fecha para el Cuadre de Caja", value=datetime.now().date())
    fecha_cierre_str = fecha_cierre.strftime("%d/%m/%Y")

    st.markdown("---")
    
    # 1. Filtrado para el día seleccionado
    ventas_del_dia_df = ventas_df[ventas_df['Fecha_Corta'] == fecha_cierre_str]
    gastos_del_dia_df = gastos_df[gastos_df['Fecha_Gasto'] == fecha_cierre_str]
    
    total_ingresos = ventas_del_dia_df['Total_Venta'].sum()
    total_egresos = gastos_del_dia_df['Monto'].sum()
    total_caja_neto = total_ingresos - total_egresos

    # 2. Indicadores Clave del Día
    col_v, col_g, col_neto = st.columns(3)
    col_v.metric("💵 Ingresos por Ventas", f"${total_ingresos:,.2f}")
    col_g.metric("📉 Gastos/Egresos", f"${total_egresos:,.2f}")
    col_neto.metric("💰 Caja Neta del Día", f"${total_caja_neto:,.2f}", delta=f"Rentab. Simple")

    st.markdown("---")

    # 3. Generar el Cuadre y PDF
    col_pdf, col_desc = st.columns(2)
    
    if col_pdf.button("📄 Generar Cuadre de Caja (PDF)"):
        if total_caja_neto != 0:
            pdf_cuadre_bytes = generar_cuadre_caja_pdf(ventas_del_dia_df, gastos_del_dia_df, fecha_cierre_str, total_caja_neto)
            col_desc.download_button(
                label="⬇️ Descargar Cuadre de Caja PDF",
                data=pdf_cuadre_bytes,
                file_name=f"Cuadre_Caja_{fecha_cierre_str.replace('/', '-')}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("No hay movimientos (ingresos/egresos) para generar un cuadre en este día.")


# --- FUNCIÓN PRINCIPAL ---

def main():
    configurar_pagina()
    
    # Conectar a Google Sheets y obtener los Worksheets
    ws_inventario, ws_clientes, ws_ventas, ws_gastos = conectar_google_sheets()

    # Si la conexión falla, solo muestra el error y termina
    if ws_inventario is None:
        return

    # --- Sidebar para Navegación Administrativa ---
    st.sidebar.header("Menú de Gestión ⚙️")
    
    opcion_gestion = st.sidebar.radio(
        "Reportes y Control:",
        ('📋 Inventario', '💸 Gastos', '💰 Cuadre de Caja')
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("Hecho con 💖 para Bigotes y Patitas")


    # --- CONTENIDO PRINCIPAL (Navegación por Pestañas para el POS) ---
    tab_venta, tab_admin = st.tabs(["🛍️ Nueva Venta", "Panel Administrativo"])

    with tab_venta:
        # Llamar a la función de la página de venta
        page_nueva_venta(ws_inventario, ws_clientes, ws_ventas)

    with tab_admin:
        if opcion_gestion == '📋 Inventario':
            # La antigua sección de inventario, ahora en un tab
            st.header("📋 Inventario Actual")
            st.markdown("---")
            inventario_df = leer_datos(ws_inventario, index_col='ID_Producto')
            if not inventario_df.empty:
                st.dataframe(
                    inventario_df[['Nombre', 'Precio', 'Stock', 'Costo']], # Se añade la columna Costo para futura rentabilidad
                    use_container_width=True,
                    column_config={
                        "Precio": st.column_config.NumberColumn("Precio Venta ($)", format="$%.2f"),
                        "Costo": st.column_config.NumberColumn("Costo de Compra ($)", format="$%.2f"),
                        "Stock": st.column_config.NumberColumn("Stock Disponible", format="%d unidades")
                    }
                )
                
                # Alerta para bajo stock
                stock_bajo = inventario_df[inventario_df['Stock'] < 5] 
                if not stock_bajo.empty:
                    st.warning("🚨 Alerta de Bajo Stock en los siguientes productos:")
                    st.table(stock_bajo[['Nombre', 'Stock']])
            else:
                st.warning("⚠️ El inventario está vacío o no se pudo cargar.")

        elif opcion_gestion == '💸 Gastos':
            # Página de gestión de gastos
            page_gestion_gastos(ws_gastos)
            
        elif opcion_gestion == '💰 Cuadre de Caja':
            # Página de cuadre de caja
            page_cuadre_caja_y_rentabilidad(ws_ventas, ws_gastos)


if __name__ == "__main__":
    main()
