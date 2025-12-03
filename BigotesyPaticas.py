import streamlit as st
import pandas as pd
import gspread # Necesitarás configurarlo para Google Sheets
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import base64
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA Y LOGO (Visual Increíble) ---
def configurar_pagina():
    """Configura la apariencia inicial de la aplicación."""
    st.set_page_config(
        page_title="🐾 Bigotes y Patitas - POS",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Estilo CSS para mejor visual y el logo
    st.markdown("""
        <style>
        .css-1d391kg, .css-18e3th9 { padding-top: 2rem; } /* Ajuste de padding general */
        .big-title {
            font-size: 2.5em;
            color: #4CAF50; /* Un color verde que evoque naturaleza */
            text-align: center;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Título y Logo
    col1, col2 = st.columns([1, 4])
    try:
        col1.image("BigotesyPaticas.png", width=150) # Asegúrate de tener la imagen
    except:
        col1.write("Logo no encontrado.")
        
    col2.markdown('<div class="big-title">Sistema POS - Bigotes y Patitas 🐾</div>', unsafe_allow_html=True)

# --- CONEXIÓN A GOOGLE SHEETS (DEBES CONFIGURAR ESTO) ---
@st.cache_resource
def conectar_google_sheets():
    """Establece y cachea la conexión a Google Sheets."""
    # *******************************************************************
    # *** ESTO ES LO MÁS IMPORTANTE Y REQUERIRÁ CONFIGURACIÓN EXTERNA ***
    # *** 1. Habilitar la Google Sheets API.                          ***
    # *** 2. Crear una cuenta de servicio (service account).          ***
    # *** 3. Compartir tu hoja de cálculo con el email de la cuenta.  ***
    # *** 4. Guardar las credenciales JSON como 'google_service_account' en st.secrets  ***
    # *******************************************************************
    try:
        # Ejemplo usando st.secrets y gspread
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        # Abre las hojas por URL o por nombre
        SHEET_URL = "https://docs.google.com/spreadsheets/d/12ay8_vug1yYXoGhHCIjKy1_NL5oqz6QBQ537283iGEo/edit?pli=1&gid=0#gid=0"
        hoja = gc.open_by_url(SHEET_URL)
        
        return hoja.worksheet("Inventario"), hoja.worksheet("Clientes"), hoja.worksheet("Ventas")
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets. Revisa tu configuración. Error: {e}")
        return None, None, None

# --- FUNCIONES DE LECTURA Y ESCRITURA ---
def leer_inventario(ws_inventario):
    """Lee y retorna el inventario como un DataFrame de Pandas."""
    if ws_inventario:
        data = ws_inventario.get_all_records()
        df = pd.DataFrame(data)
        # Asegúrate de que las columnas críticas sean del tipo correcto
        df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce')
        df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce')
        return df.set_index('ID_Producto')
    return pd.DataFrame()

def escribir_nuevo_cliente(ws_clientes, datos_cliente):
    """Escribe los datos de un nuevo cliente en la hoja de Clientes."""
    if ws_clientes:
        try:
            ws_clientes.append_row(datos_cliente)
            st.success("✅ Cliente registrado exitosamente!")
            return True
        except Exception as e:
            st.error(f"Error al guardar el cliente: {e}")
            return False

def registrar_venta(ws_ventas, ws_inventario, datos_venta, items_venta):
    """Guarda la venta y actualiza el inventario."""
    if ws_ventas and ws_inventario:
        try:
            # 1. Registrar la venta en la hoja de Ventas
            ws_ventas.append_row(datos_venta)
            
            # 2. Actualizar el inventario
            inventario_df = leer_inventario(ws_inventario)
            for item in items_venta:
                prod_id = item['ID_Producto']
                cantidad_vendida = item['Cantidad']
                
                # Encontrar la fila del producto en Google Sheets (gspread usa índices 1-basados)
                # +2 porque la fila 1 es el header y el índice de gspread es 1-basado
                fila_a_actualizar = inventario_df.index.get_loc(prod_id) + 2
                
                # Nueva cantidad de stock
                nuevo_stock = inventario_df.loc[prod_id, 'Stock'] - cantidad_vendida
                
                # Actualizar el valor de la celda de Stock
                # Asumiendo que la columna 'Stock' es la columna D (4)
                ws_inventario.update_cell(fila_a_actualizar, 4, nuevo_stock) 
            
            st.success("✅ Venta registrada y inventario actualizado correctamente.")
            return True
        except Exception as e:
            st.error(f"Error al registrar la venta y actualizar inventario: {e}")
            return False
            
# --- GENERACIÓN DE PDF BONITO (ReportLab) ---
def generar_pdf_factura(datos_factura, items_venta):
    """Crea una factura PDF con ReportLab y retorna los bytes."""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    Story = []
    styles = getSampleStyleSheet()

    # --- Cabecera de la Factura (Logo y Datos de la Tienda) ---
    Story.append(Paragraph('<font size="16" color="#4CAF50">**FACTURA DE VENTA**</font>', styles['h1']))
    Story.append(Spacer(1, 0.2 * inch))

    # Información de la tienda (puedes añadir más)
    Story.append(Paragraph("<b>Bigotes y Patitas</b>", styles['Normal']))
    Story.append(Paragraph("Tienda de Mascotas - Tel: 555-PAW", styles['Normal']))
    Story.append(Paragraph(f"Fecha: {datos_factura['Fecha']}", styles['Normal']))
    Story.append(Paragraph(f"Factura #: {datos_factura['ID_Venta']}", styles['Normal']))
    Story.append(Spacer(1, 0.3 * inch))

    # --- Información del Cliente ---
    Story.append(Paragraph('<font size="12"><b>Datos del Cliente</b></font>', styles['h2']))
    Story.append(Paragraph(f"<b>Nombre:</b> {datos_factura['Nombre_Cliente']}", styles['Normal']))
    Story.append(Paragraph(f"<b>Cédula:</b> {datos_factura['Cedula_Cliente']}", styles['Normal']))
    Story.append(Paragraph(f"<b>Mascota:</b> {datos_factura['Nombre_Mascota']}", styles['Normal']))
    Story.append(Spacer(1, 0.3 * inch))
    
    # --- Tabla de Items (Formato Increíble) ---
    data_table = [['Código', 'Producto', 'Precio Unit.', 'Cantidad', 'Subtotal']]
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

    t = Table(data_table, colWidths=[1.0*inch, 2.5*inch, 1.0*inch, 0.8*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')), # Fila de encabezado verde
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    Story.append(t)
    Story.append(Spacer(1, 0.3 * inch))
    
    # --- Total General ---
    Story.append(Paragraph(f'<div align="right"><font size="14"><b>TOTAL: ${total_general:,.2f}</b></font></div>', styles['Normal']))
    Story.append(Spacer(1, 0.5 * inch))

    # --- Mensaje de Agradecimiento ---
    Story.append(Paragraph('<i>¡Gracias por preferir Bigotes y Patitas! Vuelve pronto.</i>', styles['Italic']))

    # Construir el PDF
    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue(), total_general

# --- INTERFAZ DE USUARIO CON STREAMLIT ---
def main():
    configurar_pagina()
    
    # Inicializar estado de sesión para el carrito si no existe
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    # Conectar a Google Sheets
    ws_inventario, ws_clientes, ws_ventas = conectar_google_sheets()

    if ws_inventario is None:
        st.warning("⚠️ No se pudo conectar a Google Sheets. La aplicación no funcionará correctamente.")
        return

    inventario_df = leer_inventario(ws_inventario)
    
    # --- Sidebar para Navegación ---
    st.sidebar.header("Menú Principal")
    opcion = st.sidebar.radio(
        "Selecciona una opción:",
        ('🛍️ Nueva Venta', '👤 Registrar Cliente', '📋 Ver Inventario')
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("Hecho con 💖 para Bigotes y Patitas")

    # --- 1. SECCIÓN DE NUEVA VENTA ---
    if opcion == '🛍️ Nueva Venta':
        st.header("🛍️ Nuevo Pedido")
        st.markdown("---")
        
        # 1.1 Selección/Creación de Cliente
        st.subheader("1. Datos del Cliente")
        cedula_cliente = st.text_input("Buscar Cliente por Cédula (o Cédula Nueva)", max_chars=15)
        
        # Simulación de búsqueda de cliente (en un entorno real buscarías en ws_clientes)
        # Por simplicidad, si no lo encuentra, asume que es nuevo para la venta
        cliente_encontrado = None # Simular la búsqueda en la base de clientes
        
        if st.button("🔍 Buscar"):
            # En un entorno real, buscarías en la hoja 'Clientes' y cargarías los datos
            # Aquí asumimos que si no lo encontramos, lo pedimos en el formulario de abajo
            st.info("Función de búsqueda de cliente real no implementada. Completa los datos si es nuevo.")


        with st.form("form_datos_cliente_venta"):
            c1, c2 = st.columns(2)
            c3, c4 = st.columns(2)
            
            nombre_cliente = c1.text_input("Nombre del Cliente", key="nc")
            telefono_cliente = c2.text_input("Teléfono", key="tc")
            direccion_cliente = c3.text_input("Dirección", key="dc")
            nombre_mascota = c4.text_input("Nombre de la Mascota", key="nm")
            
            st.form_submit_button("Guardar Datos de Venta (Temporal)")

        
        st.subheader("2. Carrito de Compras")
        
        if not inventario_df.empty:
            productos_disponibles = inventario_df['Nombre'].tolist()
            producto_seleccionado = st.selectbox("Seleccionar Producto:", [""] + productos_disponibles)
            
            if producto_seleccionado:
                # Obtener el ID y el precio del producto seleccionado
                producto_info = inventario_df[inventario_df['Nombre'] == producto_seleccionado].iloc[0]
                stock_disp = producto_info['Stock']
                
                c1, c2, c3 = st.columns([1, 1, 2])
                cantidad = c1.number_input(f"Cantidad (Max: {stock_disp})", min_value=1, max_value=int(stock_disp), value=1, step=1)
                precio_unitario = producto_info['Precio']
                c2.metric("Precio Unitario", f"${precio_unitario:,.2f}")

                if c3.button("➕ Agregar al Carrito"):
                    item_carrito = {
                        "ID_Producto": producto_info.name,
                        "Nombre_Producto": producto_seleccionado,
                        "Precio": precio_unitario,
                        "Cantidad": cantidad,
                        "Subtotal": precio_unitario * cantidad
                    }
                    st.session_state.carrito.append(item_carrito)
                    st.toast(f"Se ha añadido {cantidad} de {producto_seleccionado}")
        else:
             st.warning("⚠️ No se pudo cargar el inventario. Revisa la conexión a Google Sheets.")

        st.markdown("---")
        st.subheader("3. Resumen del Carrito")

        if st.session_state.carrito:
            carrito_df = pd.DataFrame(st.session_state.carrito)
            carrito_df_mostrar = carrito_df.rename(columns={
                'Nombre_Producto': 'Producto', 
                'Precio': 'Precio Unitario',
                'Cantidad': 'Cant.', 
                'Subtotal': 'Subtotal'
            })
            carrito_df_mostrar = carrito_df_mostrar[['Producto', 'Cant.', 'Precio Unitario', 'Subtotal']]
            
            st.dataframe(carrito_df_mostrar, use_container_width=True, hide_index=True)
            
            total_venta = carrito_df['Subtotal'].sum()
            st.markdown(f"**TOTAL A PAGAR: ${total_venta:,.2f}**")
            
            st.markdown("---")
            
            if st.button("💰 Finalizar Venta y Generar Factura PDF", type="primary"):
                if not all([cedula_cliente, nombre_cliente, nombre_mascota]):
                    st.error("🚨 Por favor, completa la Cédula, Nombre del Cliente y Nombre de la Mascota.")
                else:
                    # Datos de la Venta (para el PDF y la DB)
                    id_venta = datetime.now().strftime("%Y%m%d%H%M%S") # ID de venta único
                    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                    datos_factura = {
                        "ID_Venta": id_venta,
                        "Fecha": fecha_str,
                        "Nombre_Cliente": nombre_cliente,
                        "Cedula_Cliente": cedula_cliente,
                        "Nombre_Mascota": nombre_mascota,
                        # ... otros datos
                    }

                    # 1. Generar el PDF
                    pdf_bytes, total_venta = generar_pdf_factura(datos_factura, st.session_state.carrito)
                    
                    # 2. Registrar la Venta y Actualizar Inventario
                    datos_venta_db = [
                        id_venta,
                        fecha_str,
                        cedula_cliente,
                        nombre_cliente,
                        nombre_mascota,
                        total_venta,
                        # Añade los detalles del carrito en un formato string si es necesario
                        "; ".join([f"{i['Nombre_Producto']} ({i['Cantidad']})" for i in st.session_state.carrito]) 
                    ]
                    
                    if registrar_venta(ws_ventas, ws_inventario, datos_venta_db, st.session_state.carrito):
                        # 3. Mostrar el botón de descarga del PDF
                        st.download_button(
                            label="Descargar Factura PDF",
                            data=pdf_bytes,
                            file_name=f"Factura_{id_venta}.pdf",
                            mime="application/pdf"
                        )
                        st.balloons()
                        st.session_state.carrito = [] # Limpiar el carrito después de la venta
                        st.rerun()
                        
        else:
            st.info("El carrito está vacío. Agrega productos para continuar.")


    # --- 2. SECCIÓN DE REGISTRAR CLIENTE ---
    elif opcion == '👤 Registrar Cliente':
        st.header("👤 Nuevo Cliente")
        st.markdown("---")
        
        with st.form("form_registro_cliente"):
            st.subheader("Datos del Cliente y su Mascota")
            c1, c2 = st.columns(2)
            c3, c4 = st.columns(2)
            c5, c6 = st.columns(2)
            
            # Campos requeridos
            reg_cedula = c1.text_input("Cédula/ID", max_chars=15, key="rc")
            reg_nombre = c2.text_input("Nombre Completo", key="rn")
            reg_telefono = c3.text_input("Teléfono", key="rt")
            reg_direccion = c4.text_input("Dirección", key="rd")
            reg_mascota = c5.text_input("Nombre de la Mascota", key="rm")
            
            # Otros datos opcionales
            reg_tipo_mascota = c6.selectbox("Tipo de Mascota", ("Perro", "Gato", "Ave", "Otro"), key="rtm")
            
            submit_button = st.form_submit_button("💾 Guardar Cliente")
            
            if submit_button:
                if reg_cedula and reg_nombre and reg_mascota and ws_clientes:
                    datos_cliente = [reg_cedula, reg_nombre, reg_telefono, reg_direccion, reg_mascota, reg_tipo_mascota]
                    escribir_nuevo_cliente(ws_clientes, datos_cliente)
                else:
                    st.error("🚨 La Cédula, Nombre del Cliente y Nombre de la Mascota son obligatorios.")

    # --- 3. SECCIÓN DE INVENTARIO ---
    elif opcion == '📋 Ver Inventario':
        st.header("📋 Inventario Actual")
        st.markdown("---")
        
        if not inventario_df.empty:
            # Mostrar el inventario con un formato amigable
            st.dataframe(
                inventario_df[['Nombre', 'Precio', 'Stock']],
                use_container_width=True,
                column_config={
                    "Precio": st.column_config.NumberColumn("Precio ($)", format="$%.2f"),
                    "Stock": st.column_config.NumberColumn("Stock Disponible", format="%d unidades")
                }
            )
            
            # Alerta para bajo stock
            stock_bajo = inventario_df[inventario_df['Stock'] < 5] # Ejemplo: Menos de 5 unidades
            if not stock_bajo.empty:
                st.warning("🚨 Alerta de Bajo Stock en los siguientes productos:")
                st.table(stock_bajo[['Nombre', 'Stock']])
                
        else:
            st.warning("⚠️ El inventario está vacío o no se pudo cargar.")

if __name__ == "__main__":
    main()
