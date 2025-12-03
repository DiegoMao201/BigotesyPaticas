import streamlit as st
import pandas as pd
import gspread 
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import base64
from datetime import datetime
import json 
import os

# --- CONFIGURACIÓN Y ESTILOS (Visual Impactante) ---
def configurar_pagina():
    """Configura la apariencia inicial de la aplicación con CSS personalizado."""
    st.set_page_config(
        page_title="🐾 Bigotes y Patitas - POS",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
        <style>
        /* Título Principal */
        .big-title {
            font-size: 2.8em;
            color: #4CAF50; /* Verde Pet-Friendly */
            text-align: left;
            margin-bottom: 5px;
            font-weight: 800;
        }
        /* Botones Principales (Finalizar Venta) */
        div.stButton > button:first-child[data-testid="stFormSubmitButton"] {
            background-color: #FF5733; /* Naranja vibrante para acciones */
            color: white;
            font-weight: bold;
            border-radius: 10px;
            border: 2px solid #D94429;
            padding: 10px 20px;
        }
        /* Botón de Descarga */
        .stDownloadButton > button {
            background-color: #007BFF;
            color: white;
            border-radius: 10px;
        }
        /* Sidebar Mejorado */
        .css-1d391kg {
            background-color: #F8F8F8; /* Gris claro para el sidebar */
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Título y Logo
    col1, col2 = st.columns([1, 4])
    # NOTA: Asegúrate de tener la imagen "BigotesyPaticas.png"
    try:
        col1.image("BigotesyPaticas.png", width=150)
    except:
        col1.markdown("## 🐾") 
            
    col2.markdown('<div class="big-title">Sistema POS - Bigotes y Patitas</div>', unsafe_allow_html=True)
    st.markdown("---")

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_google_sheets():
    """Establece y cachea la conexión a Google Sheets."""
    try:
        # Se asume que st.secrets está configurado correctamente
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        SHEET_URL = st.secrets.get("gsheets_url", "TU_URL_DE_HOJA_DE_CÁLCULO") # Reemplaza con tu URL
        hoja = gc.open_by_url(SHEET_URL)
        
        # Se incluyen las 5 hojas para la funcionalidad completa
        ws_inventario = hoja.worksheet("Inventario")
        ws_clientes = hoja.worksheet("Clientes")
        ws_ventas = hoja.worksheet("Ventas")
        ws_costos = hoja.worksheet("Costos")
        ws_cuadres = hoja.worksheet("Cuadres")
        
        return ws_inventario, ws_clientes, ws_ventas, ws_costos, ws_cuadres
    except Exception as e:
        st.error(f"❌ Error al conectar con Google Sheets. Revisa tus credenciales y URL. Error: {e}")
        return None, None, None, None, None

# --- FUNCIONES DE LECTURA DE DATOS (Cacheable) ---
@st.cache_data(ttl=60) 
def leer_inventario(ws_inventario):
    """Lee y retorna el inventario como un DataFrame de Pandas."""
    if ws_inventario:
        try:
            data = ws_inventario.get_all_records()
            df = pd.DataFrame(data)
            # Asegura las columnas clave (Costo es nueva para rentabilidad)
            df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce')
            df['Costo'] = pd.to_numeric(df['Costo'], errors='coerce')
            df['Stock'] = pd.to_numeric(df['Stock'], errors='coerce')
            # Manejar el índice
            if 'ID_Producto' in df.columns:
                return df.set_index('ID_Producto')
            else:
                 st.error("Columna 'ID_Producto' no encontrada en Inventario.")
                 return pd.DataFrame()
        except Exception as e:
            st.error(f"Error al leer inventario: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def leer_clientes(ws_clientes):
    """Lee y retorna la lista de clientes."""
    if ws_clientes:
        try:
            data = ws_clientes.get_all_records()
            df = pd.DataFrame(data)
            if 'Cedula/ID' in df.columns:
                return df.set_index('Cedula/ID')
            else:
                 st.error("Columna 'Cedula/ID' no encontrada en Clientes.")
                 return pd.DataFrame()
        except Exception as e:
            st.error(f"Error al leer clientes: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- FUNCIONES DE ESCRITURA DE DATOS ---
def escribir_nuevo_cliente(ws_clientes, datos_cliente):
    """Escribe los datos de un nuevo cliente."""
    if ws_clientes:
        try:
            # Orden: Cedula/ID, Nombre, Telefono, Direccion, Nombre_Mascota, Tipo_Mascota
            ws_clientes.append_row(datos_cliente)
            leer_clientes.clear() # Limpia la caché para recargar la lista
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
            
            # 2. Actualizar el inventario (se usa batch_update para eficiencia)
            inventario_df = leer_inventario(ws_inventario)
            updates = []

            for item in items_venta:
                prod_id = item['ID_Producto']
                cantidad_vendida = item['Cantidad']
                
                # Ubicación de la columna 'Stock' (asumimos que es la D o la columna 4 en sheets)
                # NOTA: En un sistema robusto, buscarías el índice de la columna por nombre. Aquí asumimos D (4)
                columna_stock = 4 
                fila_a_actualizar = inventario_df.index.get_loc(prod_id) + 2
                
                nuevo_stock = inventario_df.loc[prod_id, 'Stock'] - cantidad_vendida
                
                updates.append({
                    'range': f'D{fila_a_actualizar}',
                    'values': [[nuevo_stock]]
                })
            
            if updates:
                ws_inventario.batch_update(updates)
                leer_inventario.clear() # Limpia la caché del inventario
            
            return True
        except Exception as e:
            st.error(f"Error al registrar la venta y actualizar inventario: {e}")
            return False

def registrar_costos_y_cuadre(ws_costos, ws_cuadres, datos_cuadre, gastos_fijos, gastos_variables):
    """Registra los gastos y el resumen del cuadre diario."""
    if ws_costos and ws_cuadres:
        try:
            # 1. Registrar Gastos Fijos y Variables (en hoja Costos)
            gastos = []
            fecha_str = datos_cuadre['Fecha']
            for g in gastos_fijos:
                # Columnas de Costos: Fecha, Tipo, Concepto, Monto
                gastos.append([fecha_str, 'Fijo', g['Concepto'], g['Monto']])
            for g in gastos_variables:
                gastos.append([fecha_str, 'Variable', g['Concepto'], g['Monto']])
            
            if gastos:
                ws_costos.append_rows(gastos)

            # 2. Registrar Cuadre Diario (en hoja Cuadres)
            # Columnas de Cuadres: Fecha, Ventas_Totales, Costo_Mercancia_Vendida, Gasto_Fijo_Total, Gasto_Variable_Total, Utilidad_Neta
            ws_cuadres.append_row([
                fecha_str,
                datos_cuadre['Ventas_Totales'],
                datos_cuadre['Costo_Mercancia_Vendida'],
                datos_cuadre['Gasto_Fijo_Total'],
                datos_cuadre['Gasto_Variable_Total'],
                datos_cuadre['Utilidad_Neta']
            ])
            
            return True
        except Exception as e:
            st.error(f"Error al registrar cuadre y costos: {e}")
            return False

# --- GENERACIÓN DE PDF BONITO (ReportLab) ---
def generar_pdf_factura(datos_factura, items_venta, total_general):
    """Crea una factura PDF con ReportLab y retorna los bytes."""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)
    Story = []
    styles = getSampleStyleSheet()

    # Estilo de título (Verde PET)
    style_titulo = styles['h1']
    style_titulo.alignment = 1 
    style_titulo.textColor = colors.HexColor('#4CAF50')
    style_titulo.fontSize = 18
    
    # --- Cabecera de la Factura ---
    Story.append(Paragraph('<b><font size="16">🐾 BIGOTES Y PATITAS</font></b>', style_titulo))
    Story.append(Paragraph('<i>¡Tu mejor aliado en cuidado de mascotas!</i>', styles['Italic']))
    Story.append(Paragraph("<b>FACTURA DE VENTA</b>", styles['h2']))
    Story.append(Spacer(1, 0.1 * inch))
    
    # Información de la tienda y la factura
    info_tienda = [
        ['Tienda de Mascotas', f"Fecha: {datos_factura['Fecha']}"],
        ['Tel: 555-PAW | Dir: Calle Falsa 123', f"Factura #: {datos_factura['ID_Venta']}"]
    ]
    t_info_tienda = Table(info_tienda, colWidths=[3.0*inch, 2.5*inch])
    t_info_tienda.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
    ]))
    Story.append(t_info_tienda)
    Story.append(Spacer(1, 0.2 * inch))

    # --- Información del Cliente ---
    Story.append(Paragraph('<font size="12" color="#4CAF50"><b>DATOS DEL CLIENTE</b></font>', styles['Normal']))
    info_cliente = [
        [Paragraph(f"<b>Nombre:</b> {datos_factura['Nombre_Cliente']}", styles['Normal']),
         Paragraph(f"<b>Cédula:</b> {datos_factura['Cedula_Cliente']}", styles['Normal'])],
        [Paragraph(f"<b>Mascota:</b> {datos_factura['Nombre_Mascota']}", styles['Normal']),
         Paragraph(f"<b>Teléfono:</b> {datos_factura.get('Telefono_Cliente', 'N/A')}", styles['Normal'])]
    ]
    t_info_cliente = Table(info_cliente, colWidths=[3.0*inch, 2.5*inch])
    Story.append(t_info_cliente)
    Story.append(Spacer(1, 0.3 * inch))
    
    # --- Tabla de Items ---
    data_table = [['CÓDIGO', 'PRODUCTO', 'PRECIO UNIT.', 'CANT.', 'SUBTOTAL']]
    for item in items_venta:
        data_table.append([
            item['ID_Producto'],
            item['Nombre_Producto'],
            f"${item['Precio']:,.2f}",
            str(item['Cantidad']),
            f"${item['Subtotal']:,.2f}"
        ])

    t = Table(data_table, colWidths=[0.8*inch, 2.5*inch, 1.0*inch, 0.8*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E8F5E9')), 
    ]))
    Story.append(t)
    Story.append(Spacer(1, 0.1 * inch))
    
    # --- Total General ---
    total_data = [
        ['', '', '', Paragraph('<font size="12"><b>TOTAL:</b></font>', styles['Normal']), Paragraph(f'<div align="right"><font size="12"><b>${total_general:,.2f}</b></font></div>', styles['Normal'])]
    ]
    t_total = Table(total_data, colWidths=[0.8*inch, 2.5*inch, 1.0*inch, 0.8*inch, 1.2*inch])
    t_total.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#FF5733')),
        ('ALIGN', (-2, 0), (-1, 0), 'RIGHT'),
        ('FONTNAME', (-2, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    Story.append(t_total)
    Story.append(Spacer(1, 0.5 * inch))

    # --- Mensaje de Agradecimiento ---
    Story.append(Paragraph('<div align="center"><i>¡Gracias por preferir Bigotes y Patitas! Vuelve pronto 💖.</i></div>', styles['Italic']))

    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue()

# --- FORMULARIO DE REGISTRO DE CLIENTE (Usado en el modal/popover) ---
def formulario_registro_cliente(ws_clientes):
    """Muestra el formulario para registrar un nuevo cliente en un popover."""
    st.subheader("📝 Registro de Cliente Nuevo")
    
    with st.form("form_registro_cliente_modal", clear_on_submit=True):
        col_c_1, col_c_2 = st.columns(2)
        col_c_3, col_c_4 = st.columns(2)
        col_c_5, col_c_6 = st.columns(2)
        
        # Campos requeridos
        reg_cedula = col_c_1.text_input("Cédula/ID (*)", max_chars=15, key="rc_modal")
        reg_nombre = col_c_2.text_input("Nombre Completo (*)", key="rn_modal")
        reg_telefono = col_c_3.text_input("Teléfono", key="rt_modal")
        reg_direccion = col_c_4.text_input("Dirección", key="rd_modal")
        reg_mascota = col_c_5.text_input("Nombre de la Mascota (*)", key="rm_modal")
        
        # Otros datos opcionales
        reg_tipo_mascota = col_c_6.selectbox("Tipo de Mascota", ("Perro", "Gato", "Ave", "Otro"), key="rtm_modal")
        
        submit_button = st.form_submit_button("💾 Guardar Cliente y Continuar")
        
        if submit_button:
            if reg_cedula and reg_nombre and reg_mascota and ws_clientes:
                datos_cliente = [reg_cedula, reg_nombre, reg_telefono, reg_direccion, reg_mascota, reg_tipo_mascota]
                
                if escribir_nuevo_cliente(ws_clientes, datos_cliente):
                    st.success("✅ Cliente registrado exitosamente!")
                    # Carga el nuevo cliente inmediatamente en la sesión de venta
                    st.session_state.cedula_cliente = reg_cedula
                    st.session_state.nombre_cliente = reg_nombre
                    st.session_state.telefono_cliente = reg_telefono
                    st.session_state.direccion_cliente = reg_direccion
                    st.session_state.nombre_mascota = reg_mascota
                    st.session_state.cliente_cargado = True
                    st.toast("Datos cargados para la venta.")
                    st.rerun() 
            else:
                st.error("🚨 Los campos marcados con (*) son obligatorios.")

# --- INTERFAZ DE USUARIO CON STREAMLIT (FUNCIÓN PRINCIPAL) ---
def main():
    configurar_pagina()
    
    # 0. Inicializar estado de sesión
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cedula_cliente' not in st.session_state: st.session_state.cedula_cliente = ""
    if 'nombre_cliente' not in st.session_state: st.session_state.nombre_cliente = ""
    if 'telefono_cliente' not in st.session_state: st.session_state.telefono_cliente = ""
    if 'direccion_cliente' not in st.session_state: st.session_state.direccion_cliente = ""
    if 'nombre_mascota' not in st.session_state: st.session_state.nombre_mascota = ""
    if 'cliente_cargado' not in st.session_state: st.session_state.cliente_cargado = False
    if 'inventario_cargado' not in st.session_state: st.session_state.inventario_cargado = False
    if 'gastos_fijos' not in st.session_state: st.session_state.gastos_fijos = []
    if 'gastos_variables' not in st.session_state: st.session_state.gastos_variables = []


    # Conectar a Google Sheets
    ws_inventario, ws_clientes, ws_ventas, ws_costos, ws_cuadres = conectar_google_sheets()

    if ws_inventario is None:
        return

    inventario_df = leer_inventario(ws_inventario)
    clientes_df = leer_clientes(ws_clientes)

    if not inventario_df.empty:
        st.session_state.inventario_cargado = True
    
    # --- Sidebar para Navegación ---
    st.sidebar.header("Menú Principal 🎯")
    # Se eliminó "Ver Inventario" de la barra lateral, según solicitud
    opcion = st.sidebar.radio(
        "Selecciona una opción:",
        ('🛍️ Nueva Venta', '💰 Cuadre de Caja & Rentabilidad', '📋 Ver Inventario Completo')
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("Hecho con 💖 para Bigotes y Patitas")
    
    # --- 1. SECCIÓN DE NUEVA VENTA ---
    if opcion == '🛍️ Nueva Venta':
        st.header("🛍️ Nuevo Pedido")
        st.markdown("---")
        
        # 1.1 Sección de Cliente (Búsqueda y Registro en Popover)
        st.subheader("1. Datos del Cliente")
        
        c_search, c_register = st.columns([3, 1])
        
        # Input de búsqueda de Cédula (usa el valor de sesión como default)
        cedula_input = c_search.text_input("Buscar Cliente por Cédula/ID (Requerido)", value=st.session_state.cedula_cliente, max_chars=15, key="cedula_venta_input")
        
        # Botón para registrar nuevo cliente (Popover)
        with c_register.popover("👤 Registrar Nuevo"):
            formulario_registro_cliente(ws_clientes)

        # Lógica de Carga de Cliente
        if cedula_input != st.session_state.cedula_cliente or (cedula_input and not st.session_state.cliente_cargado):
            st.session_state.cedula_cliente = cedula_input
            
            if cedula_input and not clientes_df.empty and cedula_input in clientes_df.index:
                # Cliente ENCONTRADO
                cliente_encontrado = clientes_df.loc[cedula_input]
                st.session_state.nombre_cliente = cliente_encontrado['Nombre']
                st.session_state.telefono_cliente = cliente_encontrado['Telefono']
                st.session_state.direccion_cliente = cliente_encontrado['Direccion']
                st.session_state.nombre_mascota = cliente_encontrado['Nombre_Mascota']
                st.session_state.cliente_cargado = True
                st.success(f"Cliente **{st.session_state.nombre_cliente}** (Mascota: {st.session_state.nombre_mascota}) cargado exitosamente.")
            elif st.session_state.cedula_cliente:
                # Cliente NO ENCONTRADO/NUEVO (resetea los campos)
                st.session_state.cliente_cargado = False
                st.session_state.nombre_cliente = ""
                st.session_state.telefono_cliente = ""
                st.session_state.direccion_cliente = ""
                st.session_state.nombre_mascota = ""
                st.warning("Cliente no encontrado. Completa los datos para esta venta.")

        # Mostrar campos del cliente (usa los datos de sesión para mantenerlos)
        if st.session_state.cedula_cliente:
            c1, c2 = st.columns(2)
            c3, c4 = st.columns(2)
            
            # Los inputs actualizan directamente el st.session_state
            st.session_state.nombre_cliente = c1.text_input("Nombre del Cliente (*)", value=st.session_state.nombre_cliente, key="nc_v")
            st.session_state.telefono_cliente = c2.text_input("Teléfono", value=st.session_state.telefono_cliente, key="tc_v")
            st.session_state.direccion_cliente = c3.text_input("Dirección", value=st.session_state.direccion_cliente, key="dc_v")
            st.session_state.nombre_mascota = c4.text_input("Nombre de la Mascota (*)", value=st.session_state.nombre_mascota, key="nm_v")
        
        st.markdown("---")
        
        # 1.2 Carrito de Compras
        st.subheader("2. Carrito de Compras 🛒")
        
        if st.session_state.inventario_cargado:
            col_prod, col_cant, col_btn = st.columns([3, 1, 1])
            
            productos_disponibles = inventario_df['Nombre'].tolist()
            producto_seleccionado = col_prod.selectbox("Seleccionar Producto:", [""] + productos_disponibles)
            
            if producto_seleccionado:
                producto_info = inventario_df[inventario_df['Nombre'] == producto_seleccionado].iloc[0]
                stock_disp = producto_info['Stock']
                precio_unitario = producto_info['Precio']
                
                # Input de cantidad
                cantidad = col_cant.number_input(f"Cantidad (Max: {int(stock_disp)})", min_value=1, max_value=int(stock_disp), value=1, step=1, key="cant_prod")
                col_cant.metric("Precio Unitario", f"${precio_unitario:,.2f}")

                if col_btn.button("➕ Agregar", use_container_width=True):
                    item_carrito = {
                        "ID_Producto": producto_info.name,
                        "Nombre_Producto": producto_seleccionado,
                        "Precio": precio_unitario,
                        "Costo": producto_info['Costo'], 
                        "Cantidad": cantidad,
                        "Subtotal": precio_unitario * cantidad
                    }
                    st.session_state.carrito.append(item_carrito)
                    st.toast(f"Se añadió {cantidad} de {producto_seleccionado}")
        else:
            st.warning("⚠️ No se pudo cargar el inventario. Revisa la conexión a Google Sheets.")

        st.markdown("---")
        
        # 1.3 Resumen y Finalización
        st.subheader("3. Resumen y Total")

        if st.session_state.carrito:
            carrito_df = pd.DataFrame(st.session_state.carrito)
            carrito_df_mostrar = carrito_df.rename(columns={
                'Nombre_Producto': 'Producto', 'Precio': 'Precio Unitario',
                'Cantidad': 'Cant.', 'Subtotal': 'Subtotal'
            })[['Producto', 'Cant.', 'Precio Unitario', 'Subtotal']]
            
            st.dataframe(carrito_df_mostrar, use_container_width=True, hide_index=True)
            
            total_venta = carrito_df['Subtotal'].sum()
            st.markdown(f"## **TOTAL A PAGAR: ${total_venta:,.2f}**")
            
            with st.form("form_finalizar_venta"):
                st.markdown("---")
                
                # Botón de Finalizar Venta
                submit_venta = st.form_submit_button("💰 FINALIZAR VENTA y Generar Factura PDF", type="primary", use_container_width=True)
                
                if submit_venta:
                    if not all([st.session_state.cedula_cliente, st.session_state.nombre_cliente, st.session_state.nombre_mascota]):
                        st.error("🚨 Por favor, completa la Cédula/ID, Nombre del Cliente y Nombre de la Mascota.")
                    else:
                        # Cálculo de Costo de Mercancía Vendida (CMV)
                        cmv = (carrito_df['Costo'] * carrito_df['Cantidad']).sum()
                        
                        id_venta = datetime.now().strftime("%Y%m%d%H%M%S")
                        fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                        datos_factura = {
                            "ID_Venta": id_venta,
                            "Fecha": fecha_str,
                            "Nombre_Cliente": st.session_state.nombre_cliente,
                            "Cedula_Cliente": st.session_state.cedula_cliente,
                            "Nombre_Mascota": st.session_state.nombre_mascota,
                            "Telefono_Cliente": st.session_state.telefono_cliente
                        }
                        
                        # 1. Generar el PDF
                        pdf_bytes = generar_pdf_factura(datos_factura, st.session_state.carrito, total_venta)
                        
                        # 2. Registrar la Venta y Actualizar Inventario
                        datos_venta_db = [
                            id_venta, fecha_str, st.session_state.cedula_cliente, st.session_state.nombre_cliente,
                            st.session_state.nombre_mascota, total_venta, cmv,
                            json.dumps([{'ID': i['ID_Producto'], 'C': i['Cantidad'], 'P': i['Precio']} for i in st.session_state.carrito])
                        ]
                        
                        if registrar_venta(ws_ventas, ws_inventario, datos_venta_db, st.session_state.carrito):
                            st.balloons()
                            st.success("¡Venta completada y registrada!")
                            
                            # 3. Mostrar el botón de descarga del PDF
                            st.download_button(
                                label="📥 Descargar Factura PDF",
                                data=pdf_bytes,
                                file_name=f"Factura_{id_venta}.pdf",
                                mime="application/pdf"
                            )
                            # Limpiar estado después de la venta exitosa
                            st.session_state.carrito = [] 
                            st.session_state.cliente_cargado = False 
                            st.session_state.cedula_cliente = ""
                            # st.rerun() # Puedes comentar esto si quieres que el botón de descarga quede visible
                            
            
        else:
            st.info("El carrito está vacío. Agrega productos para continuar.")

    # --- 2. SECCIÓN DE CUADRE DE CAJA & RENTABILIDAD ---
    elif opcion == '💰 Cuadre de Caja & Rentabilidad':
        st.header("💰 Gestión Financiera Diaria y Rentabilidad")
        st.markdown("---")
        
        # 2.1 Pestañas de Navegación
        tab1, tab2 = st.tabs(["📊 Cuadre de Caja Diario", "📈 Análisis de Rentabilidad"])

        # --- 2.1.1 Cuadre de Caja Diario ---
        with tab1:
            st.subheader("Registro de Cierre de Día")
            
            fecha_cuadre = st.date_input("Fecha del Cuadre", datetime.today().date())
            
            # --- 2.1.1.1 Registro de Gastos Fijos ---
            st.markdown("#### 1. Gastos Fijos 🏠 (Alquiler, Nómina, Servicios)")
            col_f_1, col_f_2, col_f_3 = st.columns([3, 1, 1])
            gasto_fijo_concepto = col_f_1.text_input("Concepto Fijo", key="gf_conc")
            gasto_fijo_monto = col_f_2.number_input("Monto ($)", min_value=0.0, format="%.2f", key="gf_mont")
            if col_f_3.button("➕ Añadir Fijo", use_container_width=True):
                if gasto_fijo_concepto and gasto_fijo_monto > 0:
                    st.session_state.gastos_fijos.append({'Concepto': gasto_fijo_concepto, 'Monto': gasto_fijo_monto})
                    st.toast("Gasto fijo añadido.")

            if st.session_state.gastos_fijos:
                gf_df = pd.DataFrame(st.session_state.gastos_fijos)
                st.dataframe(gf_df, hide_index=True)
                gasto_fijo_total = gf_df['Monto'].sum()
                st.markdown(f"**Total Gastos Fijos: ${gasto_fijo_total:,.2f}**")
            else:
                gasto_fijo_total = 0.0
                st.info("No hay gastos fijos temporales registrados.")

            st.markdown("---")
            
            # --- 2.1.1.2 Registro de Gastos Variables ---
            st.markdown("#### 2. Gastos Variables 🚗 (Comisiones, Mantenimiento, Publicidad)")
            col_v_1, col_v_2, col_v_3 = st.columns([3, 1, 1])
            gasto_var_concepto = col_v_1.text_input("Concepto Variable", key="gv_conc")
            gasto_var_monto = col_v_2.number_input("Monto ($)", min_value=0.0, format="%.2f", key="gv_mont")
            if col_v_3.button("➕ Añadir Variable", use_container_width=True):
                if gasto_var_concepto and gasto_var_monto > 0:
                    st.session_state.gastos_variables.append({'Concepto': gasto_var_concepto, 'Monto': gasto_var_monto})
                    st.toast("Gasto variable añadido.")
            
            if st.session_state.gastos_variables:
                gv_df = pd.DataFrame(st.session_state.gastos_variables)
                st.dataframe(gv_df, hide_index=True)
                gasto_variable_total = gv_df['Monto'].sum()
                st.markdown(f"**Total Gastos Variables: ${gasto_variable_total:,.2f}**")
            else:
                gasto_variable_total = 0.0
                st.info("No hay gastos variables temporales registrados.")

            st.markdown("---")
            
            # --- 2.1.1.3 Resumen y Registro Final ---
            st.markdown("#### 3. Resumen y Cierre de Caja")
            
            # NOTA: En un sistema real, harías una consulta a la hoja 'Ventas' para obtener estos valores del día.
            ventas_dia = st.number_input("Ventas Totales del Día (Manual/Consulta)", min_value=0.0, value=0.0, format="%.2f")
            cmv_dia = st.number_input("Costo de Mercancía Vendida (CMV) del Día (Manual/Consulta)", min_value=0.0, value=0.0, format="%.2f")
            
            utilidad_bruta = ventas_dia - cmv_dia
            utilidad_neta = utilidad_bruta - (gasto_fijo_total + gasto_variable_total)
            
            col_u_1, col_u_2, col_u_3 = st.columns(3)
            col_u_1.metric("Utilidad Bruta", f"${utilidad_bruta:,.2f}", "Ventas - CMV")
            col_u_2.metric("Gastos Totales", f"${gasto_fijo_total + gasto_variable_total:,.2f}", "Fijos + Variables")
            col_u_3.metric("UTILIDAD NETA DIARIA", f"${utilidad_neta:,.2f}", "Bruta - Gastos", delta_color="normal")
            
            if st.button("✅ Registrar Cuadre de Caja Final", type="primary"):
                datos_cuadre = {
                    "Fecha": fecha_cuadre.strftime("%d/%m/%Y"),
                    "Ventas_Totales": ventas_dia,
                    "Costo_Mercancia_Vendida": cmv_dia,
                    "Gasto_Fijo_Total": gasto_fijo_total,
                    "Gasto_Variable_Total": gasto_variable_total,
                    "Utilidad_Neta": utilidad_neta
                }
                
                if registrar_costos_y_cuadre(ws_costos, ws_cuadres, datos_cuadre, st.session_state.gastos_fijos, st.session_state.gastos_variables):
                    st.balloons()
                    # Limpiar gastos temporales después del registro
                    st.session_state.gastos_fijos = []
                    st.session_state.gastos_variables = []
                    st.rerun()

        # --- 2.1.2 Análisis de Rentabilidad ---
        with tab2:
            st.subheader("Análisis de Rentabilidad y Gastos")
            st.info("Para implementar un análisis real, necesitarías leer las hojas 'Ventas', 'Costos' y 'Cuadres' y calcular los márgenes históricos.")
            
            # Métricas Clave (Simulación de datos)
            col_r_1, col_r_2, col_r_3 = st.columns(3)
            col_r_1.metric("Margen Bruto Promedio", "42%", "⬆️ 2% vs Mes Pasado")
            col_r_2.metric("Ratio Gastos/Ventas", "30%", "Objetivo: < 25%")
            col_r_3.metric("Utilidad Neta Acumulada (Mes)", "$12,500.00", "Rentabilidad Sólida", delta_color="normal")
            
            st.markdown("#### Distribución de Gastos (Gráfico de ejemplo)")
            gastos_ejemplo = pd.DataFrame({
                'Gasto': ['Alquiler', 'Nómina', 'Inventario', 'Marketing'],
                'Monto': [2000, 3000, 500, 1000]
            })
            st.bar_chart(gastos_ejemplo.set_index('Gasto'))

    # --- 3. SECCIÓN DE INVENTARIO COMPLETO ---
    elif opcion == '📋 Ver Inventario Completo':
        st.header("📋 Inventario, Costos y Alertas")
        st.markdown("---")
        
        if st.session_state.inventario_cargado:
            # Calcular margen bruto unitario (Precio - Costo)
            inventario_df['Margen Unitario'] = inventario_df['Precio'] - inventario_df['Costo']
            
            # Mostrar columnas clave
            inventario_mostrar = inventario_df[['Nombre', 'Precio', 'Costo', 'Margen Unitario', 'Stock', 'Proveedor', 'Categoría']]
            
            st.dataframe(
                inventario_mostrar,
                use_container_width=True,
                column_config={
                    "Precio": st.column_config.NumberColumn("Precio Venta ($)", format="$%.2f"),
                    "Costo": st.column_config.NumberColumn("Costo ($)", format="$%.2f"),
                    "Margen Unitario": st.column_config.NumberColumn("Margen ($)", format="$%.2f"),
                    "Stock": st.column_config.NumberColumn("Stock Disponible", format="%d unidades")
                }
            )
            
            # Alerta para bajo stock
            stock_bajo = inventario_df[inventario_df['Stock'] < 5] 
            if not stock_bajo.empty:
                st.error("🚨 **ALERTA DE STOCK CRÍTICO** (Menos de 5 unidades):")
                st.table(stock_bajo[['Nombre', 'Stock', 'Proveedor']])
                
        else:
            st.warning("⚠️ El inventario está vacío o no se pudo cargar. Revisa la hoja de Google Sheets.")

if __name__ == "__main__":
    main()
