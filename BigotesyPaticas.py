import streamlit as st
import pandas as pd
import gspread
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ImageRL, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime, date
import time
import numpy as np
import base64

# --- 1. CONFIGURACIÓN Y ESTILOS MODERNOS ---

COLOR_PRIMARIO = "#2ecc71"  # Verde Éxito
COLOR_SECUNDARIO = "#27ae60" # Verde Oscuro
COLOR_FONDO = "#f4f6f9"
COLOR_TEXTO = "#2c3e50"

# Logo de Huellita en Base64 (Para no depender de archivos externos)
LOGO_B64 = """
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
"""

def configurar_pagina():
    st.set_page_config(
        page_title="Bigotes y Patitas PRO",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {COLOR_FONDO}; }}
        h1, h2, h3 {{ color: {COLOR_TEXTO}; font-family: 'Helvetica Neue', sans-serif; }}
        div[data-testid="metric-container"] {{
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border: 1px solid #e0e0e0;
        }}
        .stButton button[type="primary"] {{
            background: linear-gradient(90deg, {COLOR_PRIMARIO}, {COLOR_SECUNDARIO});
            border: none;
            font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
            border-radius: 8px;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y UTILIDADES ---

@st.cache_resource(ttl=600)
def conectar_google_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account y SHEET_URL).")
            return None, None, None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        return sh.worksheet("Inventario"), sh.worksheet("Clientes"), sh.worksheet("Ventas"), sh.worksheet("Gastos")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None, None, None, None

def sanitizar_dato(dato):
    if isinstance(dato, (np.int64, np.int32, np.integer)): return int(dato)
    elif isinstance(dato, (np.float64, np.float32, np.floating)): return float(dato)
    return dato

def leer_datos(ws):
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        for col in ['Precio', 'Stock', 'Monto', 'Total']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def escribir_fila(ws, datos):
    try:
        datos_limpios = [sanitizar_dato(d) for d in datos]
        ws.append_row(datos_limpios)
        return True
    except Exception as e:
        st.error(f"Error guardando: {e}")
        return False

def actualizar_stock(ws_inv, items):
    try:
        records = ws_inv.get_all_records()
        df = pd.DataFrame(records)
        df['ID_Producto'] = df['ID_Producto'].astype(str)
        
        for item in items:
            id_p = str(item['ID_Producto'])
            idx = df.index[df['ID_Producto'] == id_p].tolist()
            if idx:
                fila = idx[0] + 2
                stock_act = int(df.iloc[idx[0]]['Stock'])
                nuevo = max(0, stock_act - item['Cantidad'])
                ws_inv.update_cell(fila, 5, nuevo) 
        return True
    except Exception as e:
        st.error(f"Error stock: {e}")
        return False

# --- 3. GENERADOR DE PDF "SUPER PRO" ---

def generar_pdf(venta_data, items):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    Story = []
    
    # --- ESTILOS PERSONALIZADOS ---
    styles = getSampleStyleSheet()
    
    # Estilo Título Tienda
    style_store_name = ParagraphStyle(
        'StoreName',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor(COLOR_SECUNDARIO),
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    # Estilo Info Contacto
    style_contact = ParagraphStyle(
        'ContactInfo',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.gray,
        alignment=TA_CENTER,
        leading=12
    )
    
    # Estilo Título de Sección
    style_section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor(COLOR_TEXTO),
        spaceBefore=10,
        spaceAfter=5
    )
    
    # Estilo Info Factura (Derecha)
    style_invoice_info = ParagraphStyle(
        'InvoiceInfo',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT,
        leading=14
    )

    # Estilo Info Cliente (Izquierda)
    style_client_info = ParagraphStyle(
        'ClientInfo',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        leading=14
    )

    # --- 1. CABECERA CON LOGO Y NOMBRE ---
    # Decodificar logo base64
    img_data = base64.b64decode(LOGO_B64.strip())
    im = ImageRL(BytesIO(img_data), width=0.8*inch, height=0.8*inch)
    im.hAlign = 'CENTER'
    Story.append(im)
    
    Story.append(Paragraph("BIGOTES Y PATITAS", style_store_name))
    Story.append(Paragraph("<b>Tu tienda de confianza para mascotas 🐾</b>", style_contact))
    Story.append(Paragraph("Tel: 320 504 6277 | Email: bigotesypaticasdosquebradas@gmail.com", style_contact))
    Story.append(Paragraph("Instagram: @bigotesypaticas", style_contact))
    Story.append(Spacer(1, 10))
    Story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(COLOR_PRIMARIO)))
    Story.append(Spacer(1, 20))

    # --- 2. INFORMACIÓN DEL TICKET Y CLIENTE (Grid de 2 columnas) ---
    
    # Datos Izquierda (Cliente)
    cliente_txt = f"""
    <b>FACTURAR A:</b><br/>
    {venta_data['Cliente']}<br/>
    ID: {venta_data.get('Cedula_Cliente', '---')}<br/>
    {venta_data.get('Direccion', 'Dirección no registrada')}
    """
    
    # Datos Derecha (Factura)
    factura_txt = f"""
    <b>RECIBO DE VENTA</b><br/>
    <font color={COLOR_SECUNDARIO}><b># {venta_data['ID']}</b></font><br/>
    Fecha: {venta_data['Fecha']}<br/>
    Método: {venta_data.get('Metodo', 'Efectivo')}
    """

    data_info = [[Paragraph(cliente_txt, style_client_info), Paragraph(factura_txt, style_invoice_info)]]
    t_info = Table(data_info, colWidths=[3.5*inch, 3*inch])
    t_info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    Story.append(t_info)
    Story.append(Spacer(1, 20))

    # --- 3. TABLA DE PRODUCTOS ---
    
    # Encabezados
    headers = ['PRODUCTO / DESCRIPCIÓN', 'CANT', 'PRECIO UNIT.', 'SUBTOTAL']
    table_data = [headers]
    
    # Filas
    for item in items:
        row = [
            Paragraph(item['Nombre_Producto'], styles['Normal']),
            str(item['Cantidad']),
            f"${item['Precio']:,.0f}",
            f"${item['Subtotal']:,.0f}"
        ]
        table_data.append(row)
    
    # Tabla
    t_prods = Table(table_data, colWidths=[3.5*inch, 0.8*inch, 1.2*inch, 1.3*inch])
    
    # Estilo de Tabla "Profesional"
    style_table = TableStyle([
        # Encabezado
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(COLOR_PRIMARIO)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('TOPPADDING', (0,0), (-1,0), 10),
        
        # Cuerpo
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'), # Cantidad centrada
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),  # Precio derecha
        ('ALIGN', (3,1), (-1,-1), 'RIGHT'),  # Subtotal derecha
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('BOTTOMPADDING', (0,1), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
    ])
    
    # Filas alternas (zebra)
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            bg_color = colors.HexColor("#f4f6f9")
            style_table.add('BACKGROUND', (0,i), (-1,i), bg_color)
            
    t_prods.setStyle(style_table)
    Story.append(t_prods)
    Story.append(Spacer(1, 10))

    # --- 4. TOTALES ---
    
    total_val = venta_data['Total']
    
    # Tabla simple para alinear totales a la derecha
    data_total = [
        ['', 'TOTAL A PAGAR:', f"${total_val:,.0f}"]
    ]
    t_total = Table(data_total, colWidths=[4*inch, 1.5*inch, 1.3*inch])
    t_total.setStyle(TableStyle([
        ('ALIGN', (1,0), (2,0), 'RIGHT'),
        ('FONTNAME', (1,0), (2,0), 'Helvetica-Bold'),
        ('FONTSIZE', (1,0), (2,0), 12),
        ('TEXTCOLOR', (2,0), (2,0), colors.HexColor(COLOR_SECUNDARIO)),
        ('LINEABOVE', (1,0), (2,0), 1, colors.black),
    ]))
    Story.append(t_total)
    
    # --- 5. PIE DE PÁGINA ---
    Story.append(Spacer(1, 40))
    Story.append(HRFlowable(width="80%", thickness=0.5, color=colors.lightgrey, spaceAfter=10))
    
    footer_text = """
    ¡Gracias por consentir a tu mascota con nosotros! 🐶🐱<br/>
    Guardar este recibo para cambios o garantías (5 días hábiles).
    """
    Story.append(Paragraph(footer_text, style_contact))

    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue()

# --- 4. PESTAÑA: PUNTO DE VENTA (MODIFICADA PARA NUEVO PDF) ---

def tab_punto_venta(ws_inv, ws_cli, ws_ven):
    st.markdown("### 🛒 Nueva Venta")
    col_izq, col_der = st.columns([1.5, 1])

    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None

    # --- IZQUIERDA ---
    with col_izq:
        # Cliente
        with st.expander("👤 Selección de Cliente", expanded=True if not st.session_state.cliente_actual else False):
            busqueda = st.text_input("Buscar Cédula", placeholder="Ingrese documento...")
            if st.button("Buscar Cliente"):
                df_c = leer_datos(ws_cli)
                if not df_c.empty:
                    df_c['Cedula'] = df_c['Cedula'].astype(str)
                    busqueda = busqueda.strip()
                    res = df_c[df_c['Cedula'] == busqueda]
                    if not res.empty:
                        st.session_state.cliente_actual = res.iloc[0].to_dict()
                        st.success(f"Cliente: {st.session_state.cliente_actual.get('Nombre', 'Sin Nombre')}")
                    else:
                        st.warning("No encontrado")
        
        if st.session_state.cliente_actual:
            nombre_cliente = st.session_state.cliente_actual.get('Nombre', 'Cliente')
            st.info(f"Cliente Activo: **{nombre_cliente}**")

        # Productos
        st.markdown("#### Agregar Productos")
        df_inv = leer_datos(ws_inv)
        if not df_inv.empty:
            df_stock = df_inv[df_inv['Stock'] > 0]
            prod_lista = df_stock.apply(lambda x: f"{x.get('Nombre', 'N/A')} | ${x.get('Precio', 0):,.0f} | ID:{x.get('ID_Producto', '')}", axis=1).tolist()
            
            sel_prod = st.selectbox("Buscar Producto", [""] + prod_lista)
            col_cant, col_add = st.columns([1, 2])
            cantidad = col_cant.number_input("Cant", min_value=1, value=1)
            
            if col_add.button("➕ Agregar", type="primary"):
                if sel_prod:
                    try:
                        id_p = sel_prod.split("ID:")[1]
                        info_p = df_inv[df_inv['ID_Producto'].astype(str) == id_p].iloc[0]
                        if cantidad <= info_p['Stock']:
                            item = {
                                "ID_Producto": info_p['ID_Producto'],
                                "Nombre_Producto": info_p['Nombre'],
                                "Precio": float(info_p['Precio']),
                                "Cantidad": int(cantidad),
                                "Subtotal": float(info_p['Precio'] * cantidad)
                            }
                            st.session_state.carrito.append(item)
                        else:
                            st.error("Stock insuficiente")
                    except Exception as e:
                        st.error(f"Error agregando: {e}")

    # --- DERECHA ---
    with col_der:
        st.markdown("### 🧾 Resumen")
        
        if st.session_state.ultimo_pdf:
            st.success("✅ ¡Venta Registrada!")
            st.markdown(f"**Ticket #{st.session_state.ultima_venta_id}**")
            
            st.download_button(
                label="🖨️ Descargar Recibo PDF",
                data=st.session_state.ultimo_pdf,
                file_name=f"Venta_{st.session_state.ultima_venta_id}.pdf",
                mime="application/pdf",
                type="primary"
            )
            
            if st.button("🔄 Nueva Venta / Limpiar"):
                st.session_state.carrito = []
                st.session_state.cliente_actual = None
                st.session_state.ultimo_pdf = None
                st.session_state.ultima_venta_id = None
                st.rerun()

        elif st.session_state.carrito:
            df_cart = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_cart[['Nombre_Producto', 'Cantidad', 'Subtotal']], hide_index=True, use_container_width=True)
            total = df_cart['Subtotal'].sum()
            st.metric("Total a Pagar", f"${total:,.0f}")
            
            st.markdown("---")
            
            with st.form("form_cobro"):
                st.markdown("#### 💳 Detalles de Pago")
                
                tipo_entrega = st.radio("Modalidad:", ["Punto de Venta", "Envío a Domicilio"], horizontal=True)
                
                dir_cliente = st.session_state.cliente_actual.get('Direccion', '') if st.session_state.cliente_actual else ""
                direccion_envio = "Local"
                if tipo_entrega == "Envío a Domicilio":
                    direccion_envio = st.text_input("Dirección de Entrega", value=str(dir_cliente))

                metodo = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "DaviPlata", "Bancolombia", "Davivienda", "Tarjeta Débito/Crédito"])
                
                banco_destino = "Caja General"
                if metodo in ["Nequi", "DaviPlata", "Bancolombia", "Davivienda", "Tarjeta Débito/Crédito"]:
                    banco_destino = st.selectbox("Banco Destino", ["Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata", "Caja Menor"])
                
                enviar = st.form_submit_button("✅ CONFIRMAR VENTA", type="primary", use_container_width=True)
            
            if enviar:
                if not st.session_state.cliente_actual:
                    st.error("⚠️ Falta seleccionar cliente")
                else:
                    try:
                        id_venta = datetime.now().strftime("%Y%m%d%H%M%S")
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        items_str = ", ".join([f"{i['Nombre_Producto']} (x{i['Cantidad']})" for i in st.session_state.carrito])
                        estado_envio = "Entregado" if tipo_entrega == "Punto de Venta" else "Pendiente"
                        
                        datos_venta = [
                            id_venta, fecha, 
                            str(st.session_state.cliente_actual.get('Cedula', '0')), 
                            st.session_state.cliente_actual.get('Nombre', 'Consumidor'),
                            tipo_entrega, direccion_envio, estado_envio,
                            metodo, banco_destino, 
                            total, items_str
                        ]
                        
                        if escribir_fila(ws_ven, datos_venta):
                            actualizar_stock(ws_inv, st.session_state.carrito)
                            
                            # GENERAR PDF PRO
                            cliente_data = {
                                "ID": id_venta,
                                "Fecha": fecha,
                                "Cliente": st.session_state.cliente_actual.get('Nombre', 'Consumidor'),
                                "Cedula_Cliente": str(st.session_state.cliente_actual.get('Cedula', '')),
                                "Direccion": direccion_envio,
                                "Total": total,
                                "Metodo": metodo
                            }
                            
                            pdf_bytes = generar_pdf(cliente_data, st.session_state.carrito)
                            
                            st.session_state.ultimo_pdf = pdf_bytes
                            st.session_state.ultima_venta_id = id_venta
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error procesando venta: {e}")

        else:
            st.info("El carrito está vacío.")

# --- 5. OTRAS PESTAÑAS (ENVÍOS, GASTOS, CIERRE) ---

def tab_envios(ws_ven):
    st.markdown("### 🚚 Control de Despachos")
    df = leer_datos(ws_ven)
    if not df.empty and 'Tipo_Entrega' in df.columns and 'Estado_Envio' in df.columns:
        pendientes = df[(df['Tipo_Entrega'] == 'Envío a Domicilio') & (df['Estado_Envio'] == 'Pendiente')]
        if pendientes.empty:
            st.success("🎉 ¡No hay envíos pendientes!")
        else:
            st.markdown(f"**Tienes {len(pendientes)} envíos por despachar.**")
            for index, row in pendientes.iterrows():
                with st.expander(f"📦 {row['Nombre_Cliente']} - {row['Direccion_Envio']}"):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**Items:** {row['Items']}")
                    c1.write(f"**Total:** ${row['Total']:,.0f}")
                    if c2.button("Marcar Enviado", key=f"btn_{row['ID_Venta']}"):
                        try:
                            cell = ws_ven.find(str(row['ID_Venta']))
                            ws_ven.update_cell(cell.row, 7, "Enviado")
                            st.toast("Estado actualizado a Enviado")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

def tab_gastos(ws_gas):
    st.markdown("### 💸 Registro de Egresos")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo_gasto = st.selectbox("Clasificación", ["Gasto Fijo", "Gasto Variable", "Costo de Venta"])
            categorias = []
            if tipo_gasto == "Gasto Fijo": categorias = ["Arriendo", "Nómina", "Servicios Públicos", "Internet/Software", "Seguros"]
            elif tipo_gasto == "Gasto Variable": categorias = ["Comisiones", "Mantenimiento", "Publicidad", "Transporte", "Papelería"]
            else: categorias = ["Compra de Mercancía", "Insumos Veterinarios", "Laboratorio"]
            categoria = st.selectbox("Concepto", categorias)
            descripcion = st.text_input("Descripción Detallada (Opcional)")
        with col2:
            monto = st.number_input("Monto", min_value=0.0, step=100.0)
            metodo_pago = st.selectbox("Medio de Pago", ["Transferencia", "Efectivo", "Tarjeta Crédito"])
            origen_fondos = st.selectbox("¿De dónde sale el dinero?", ["Caja General", "Bancolombia Ahorros", "Davivienda", "Caja Menor"])

        if st.button("Guardar Gasto", type="primary", use_container_width=True):
            if monto > 0:
                datos_gasto = [datetime.now().strftime("%Y%m%d%H%M%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tipo_gasto, categoria, descripcion, monto, metodo_pago, origen_fondos]
                if escribir_fila(ws_gas, datos_gasto):
                    st.success("Gasto registrado.")
                    time.sleep(1)
                    st.rerun()
            else: st.warning("Monto debe ser > 0")

def tab_cierre(ws_ven, ws_gas):
    st.markdown("### 💰 Cierre de Caja")
    hoy = date.today()
    fecha_filtro = st.date_input("Fecha de Análisis", hoy)
    
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)
    
    if not df_v.empty:
        df_v['Fecha_Dt'] = pd.to_datetime(df_v['Fecha']).dt.date
        datos_dia = df_v[df_v['Fecha_Dt'] == fecha_filtro]
        total_ventas = datos_dia['Total'].sum()
        num_ventas = len(datos_dia)
        
        total_gastos = 0
        if not df_g.empty:
            df_g['Fecha_Dt'] = pd.to_datetime(df_g['Fecha']).dt.date
            gastos_dia = df_g[df_g['Fecha_Dt'] == fecha_filtro]
            total_gastos = gastos_dia['Monto'].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ventas Totales", f"${total_ventas:,.0f}")
        m2.metric("Gastos Totales", f"${total_gastos:,.0f}", delta_color="inverse")
        m3.metric("Balance Neto", f"${(total_ventas - total_gastos):,.0f}")
        m4.metric("Transacciones", num_ventas)
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Entradas por Banco")
            if not datos_dia.empty:
                bancos = datos_dia.groupby('Banco_Destino')['Total'].sum().reset_index()
                st.dataframe(bancos, use_container_width=True)
        with c2:
            st.subheader("Salidas por Banco")
            if not df_g.empty and not gastos_dia.empty:
                salidas = gastos_dia.groupby('Banco_Origen')['Monto'].sum().reset_index()
                st.dataframe(salidas, use_container_width=True)

# --- MAIN ---

def main():
    configurar_pagina()
    st.sidebar.title("🐾 Menú Principal")
    opcion = st.sidebar.radio("Ir a:", ["Punto de Venta", "Despachos y Envíos", "Registro de Gastos", "Cierre y Finanzas"])
    st.sidebar.markdown("---")
    st.sidebar.caption("Bigotes y Patitas v3.0 Super App")
    
    ws_inv, ws_cli, ws_ven, ws_gas = conectar_google_sheets()
    
    if not ws_inv:
        st.warning("Esperando conexión a Google Sheets...")
        return

    if opcion == "Punto de Venta": tab_punto_venta(ws_inv, ws_cli, ws_ven)
    elif opcion == "Despachos y Envíos": tab_envios(ws_ven)
    elif opcion == "Registro de Gastos": tab_gastos(ws_gas)
    elif opcion == "Cierre y Finanzas": tab_cierre(ws_ven, ws_gas)

if __name__ == "__main__":
    main()
