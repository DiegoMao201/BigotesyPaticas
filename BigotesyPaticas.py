import streamlit as st
import pandas as pd
import gspread
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.colors import black
from io import BytesIO
from datetime import datetime, date
import time
import numpy as np

# --- 1. CONFIGURACIÓN Y ESTILOS MODERNOS ---

COLOR_PRIMARIO = "#2ecc71"  # Verde Éxito
COLOR_SECUNDARIO = "#3498db" # Azul Corporativo
COLOR_FONDO = "#f4f6f9"
COLOR_TEXTO = "#2c3e50"

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
        
        /* Títulos */
        h1, h2, h3 {{ color: {COLOR_TEXTO}; font-family: 'Helvetica Neue', sans-serif; }}
        
        /* Tarjetas de Métricas */
        div[data-testid="metric-container"] {{
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border: 1px solid #e0e0e0;
        }}
        
        /* Botones Personalizados */
        .stButton button[type="primary"] {{
            background: linear-gradient(90deg, {COLOR_PRIMARIO}, #27ae60);
            border: none;
            font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        /* Inputs estilizados */
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
            st.error("🚨 Falta configuración de secretos.")
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
        # Limpieza numérica básica
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
                ws_inv.update_cell(fila, 5, nuevo) # Asumiendo Col 5 es Stock
        return True
    except Exception as e:
        st.error(f"Error stock: {e}")
        return False

def generar_pdf(venta_data, items):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    Story = []
    styles = getSampleStyleSheet()
    
    Story.append(Paragraph(f"<b>BIGOTES Y PATITAS</b>", styles['Title']))
    Story.append(Paragraph(f"Ticket: {venta_data['ID']}", styles['Normal']))
    Story.append(Paragraph(f"Fecha: {venta_data['Fecha']}", styles['Normal']))
    Story.append(Paragraph(f"Cliente: {venta_data['Cliente']}", styles['Normal']))
    Story.append(Spacer(1, 12))
    
    data = [['Producto', 'Cant', 'Total']]
    for i in items:
        data.append([i['Nombre_Producto'][:25], i['Cantidad'], f"${i['Subtotal']:,.0f}"])
    
    data.append(['', 'TOTAL:', f"${venta_data['Total']:,.0f}"])
    t = Table(data)
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, black)]))
    Story.append(t)
    
    doc.build(Story)
    buffer.seek(0)
    return buffer.getvalue()

# --- 3. PESTAÑA: PUNTO DE VENTA (SOLUCIÓN ERROR DOWNLOAD) ---

def tab_punto_venta(ws_inv, ws_cli, ws_ven):
    st.markdown("### 🛒 Nueva Venta")
    col_izq, col_der = st.columns([1.5, 1])

    # Inicializar Session State para el carrito y el PDF temporal
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    
    # NUEVO: Estado para guardar la última venta y mostrar el recibo fuera del form
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None

    # --- IZQUIERDA: Selección ---
    with col_izq:
        # 1. CLIENTE
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
            nombre_mascota = st.session_state.cliente_actual.get('Mascota', 'No registrada')
            st.info(f"Cliente Activo: **{nombre_cliente}** - Mascota: {nombre_mascota}")

        # 2. PRODUCTOS
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

    # --- DERECHA: Checkout y Pago ---
    with col_der:
        st.markdown("### 🧾 Resumen")
        
        # Si ya se hizo la venta, mostramos SOLO el resultado y el botón de descarga
        if st.session_state.ultimo_pdf:
            st.success("✅ ¡Venta Registrada!")
            st.markdown(f"**Ticket #{st.session_state.ultima_venta_id}**")
            
            # 1. BOTÓN DE DESCARGA (Ahora está fuera del form)
            st.download_button(
                label="🖨️ Descargar Recibo PDF",
                data=st.session_state.ultimo_pdf,
                file_name=f"Venta_{st.session_state.ultima_venta_id}.pdf",
                mime="application/pdf",
                type="primary"
            )
            
            # 2. BOTÓN PARA NUEVA VENTA (Limpia todo)
            if st.button("🔄 Nueva Venta / Limpiar"):
                st.session_state.carrito = []
                st.session_state.cliente_actual = None
                st.session_state.ultimo_pdf = None
                st.session_state.ultima_venta_id = None
                st.rerun()

        # Si NO hay venta finalizada, mostramos el carrito y el formulario
        elif st.session_state.carrito:
            df_cart = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_cart[['Nombre_Producto', 'Cantidad', 'Subtotal']], hide_index=True, use_container_width=True)
            total = df_cart['Subtotal'].sum()
            st.metric("Total a Pagar", f"${total:,.0f}")
            
            st.markdown("---")
            
            # --- FORMULARIO DE COBRO ---
            with st.form("form_cobro"):
                st.markdown("#### 💳 Detalles de Pago")
                
                # A. TIPO DE ENTREGA
                tipo_entrega = st.radio("Modalidad:", ["Punto de Venta", "Envío a Domicilio"], horizontal=True)
                
                dir_cliente = st.session_state.cliente_actual.get('Direccion', '') if st.session_state.cliente_actual else ""
                direccion_envio = "Local"
                if tipo_entrega == "Envío a Domicilio":
                    direccion_envio = st.text_input("Dirección de Entrega", value=str(dir_cliente))

                # B. FORMA DE PAGO
                metodo = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "DaviPlata", "Bancolombia", "Davivienda", "Tarjeta Débito/Crédito"])
                
                # C. DESTINO
                banco_destino = "Caja General"
                if metodo in ["Nequi", "DaviPlata", "Bancolombia", "Davivienda", "Tarjeta Débito/Crédito"]:
                    banco_destino = st.selectbox("Banco Destino", ["Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata", "Caja Menor"])
                
                # BOTÓN DE ENVÍO DEL FORMULARIO
                enviar = st.form_submit_button("✅ CONFIRMAR VENTA", type="primary", use_container_width=True)
            
            # --- LÓGICA AL PRESIONAR EL BOTÓN (FUERA DEL FORM PARA EVITAR ERRORES) ---
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
                        
                        # Guardar en Google Sheets
                        if escribir_fila(ws_ven, datos_venta):
                            actualizar_stock(ws_inv, st.session_state.carrito)
                            
                            # Generar PDF y guardarlo en Session State
                            cliente_pdf = st.session_state.cliente_actual.get('Nombre', 'Cliente')
                            pdf_bytes = generar_pdf({"ID": id_venta, "Fecha": fecha, "Cliente": cliente_pdf, "Total": total}, st.session_state.carrito)
                            
                            # AQUÍ ESTÁ EL TRUCO: Guardamos en variables de estado
                            st.session_state.ultimo_pdf = pdf_bytes
                            st.session_state.ultima_venta_id = id_venta
                            
                            # Recargamos la página para que aparezca el botón de descarga (arriba en el if)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error procesando venta: {e}")

        else:
            st.info("El carrito está vacío.")

# --- 4. PESTAÑA: GESTIÓN DE ENVÍOS ---

def tab_envios(ws_ven):
    st.markdown("### 🚚 Control de Despachos")
    df = leer_datos(ws_ven)
    
    if not df.empty:
        # Filtrar solo envíos pendientes
        if 'Tipo_Entrega' in df.columns and 'Estado_Envio' in df.columns:
            pendientes = df[(df['Tipo_Entrega'] == 'Envío a Domicilio') & (df['Estado_Envio'] == 'Pendiente')]
            
            if pendientes.empty:
                st.success("🎉 ¡No hay envíos pendientes!")
            else:
                st.markdown(f"**Tienes {len(pendientes)} envíos por despachar.**")
                
                for index, row in pendientes.iterrows():
                    with st.expander(f"📦 {row['Nombre_Cliente']} - {row['Direccion_Envio']} ({row['Fecha']})"):
                        c1, c2 = st.columns([3, 1])
                        c1.write(f"**Items:** {row['Items']}")
                        c1.write(f"**Total:** ${row['Total']:,.0f}")
                        
                        if c2.button("Marcar Enviado", key=f"btn_{row['ID_Venta']}"):
                            # Actualizar Google Sheets
                            # Buscamos la fila exacta (Ojo: esto es lento con muchos datos, idealmente usar cell lookup)
                            try:
                                cell = ws_ven.find(str(row['ID_Venta']))
                                ws_ven.update_cell(cell.row, 7, "Enviado") # Col 7 es Estado_Envio
                                st.toast("Estado actualizado a Enviado")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error actualizando: {e}")
        else:
            st.error("Faltan columnas en la hoja de Ventas para gestionar envíos.")

# --- 5. PESTAÑA: GASTOS DETALLADOS ---

def tab_gastos(ws_gas):
    st.markdown("### 💸 Registro de Egresos")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            tipo_gasto = st.selectbox("Clasificación", ["Gasto Fijo", "Gasto Variable", "Costo de Venta"])
            
            # Subcategorías inteligentes
            categorias = []
            if tipo_gasto == "Gasto Fijo":
                categorias = ["Arriendo", "Nómina", "Servicios Públicos", "Internet/Software", "Seguros"]
            elif tipo_gasto == "Gasto Variable":
                categorias = ["Comisiones", "Mantenimiento", "Publicidad", "Transporte", "Papelería"]
            else:
                categorias = ["Compra de Mercancía", "Insumos Veterinarios", "Laboratorio"]
                
            categoria = st.selectbox("Concepto", categorias)
            descripcion = st.text_input("Descripción Detallada (Opcional)")

        with col2:
            monto = st.number_input("Monto del Gasto", min_value=0.0, step=100.0)
            metodo_pago = st.selectbox("Medio de Pago", ["Transferencia", "Efectivo", "Tarjeta Crédito"])
            
            origen_fondos = st.selectbox("¿De dónde sale el dinero?", ["Caja General", "Bancolombia Ahorros", "Davivienda", "Caja Menor"])

        if st.button("Guardar Gasto", type="primary", use_container_width=True):
            if monto > 0:
                datos_gasto = [
                    datetime.now().strftime("%Y%m%d%H%M%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    tipo_gasto, categoria, descripcion, monto, metodo_pago, origen_fondos
                ]
                if escribir_fila(ws_gas, datos_gasto):
                    st.success("Gasto registrado correctamente.")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("El monto debe ser mayor a 0")

# --- 6. PESTAÑA: CIERRE Y ESTADÍSTICAS (DASHBOARD) ---

def tab_cierre(ws_ven, ws_gas):
    st.markdown("### 💰 Cierre de Caja y Estadísticas")
    
    # Filtros de Fecha
    hoy = date.today()
    col_date, col_banco = st.columns(2)
    fecha_filtro = col_date.date_input("Fecha de Análisis", hoy)
    
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)
    
    if not df_v.empty:
        # Convertir fechas
        df_v['Fecha_Dt'] = pd.to_datetime(df_v['Fecha']).dt.date
        datos_dia = df_v[df_v['Fecha_Dt'] == fecha_filtro]
        
        # --- MÉTRICAS GENERALES DEL DÍA ---
        total_ventas = datos_dia['Total'].sum()
        num_ventas = len(datos_dia)
        
        # Gastos del día
        total_gastos = 0
        if not df_g.empty:
            df_g['Fecha_Dt'] = pd.to_datetime(df_g['Fecha']).dt.date
            gastos_dia = df_g[df_g['Fecha_Dt'] == fecha_filtro]
            total_gastos = gastos_dia['Monto'].sum()
        
        balance = total_ventas - total_gastos
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ventas Totales", f"${total_ventas:,.0f}")
        m2.metric("Gastos Totales", f"${total_gastos:,.0f}", delta_color="inverse")
        m3.metric("Balance Neto", f"${balance:,.0f}")
        m4.metric("Transacciones", num_ventas)
        
        st.markdown("---")
        
        # --- DESGLOSE POR BANCO/CAJA (EL CUADRE) ---
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("🏦 Dinero por Banco/Destino (Entradas)")
            if not datos_dia.empty:
                # Agrupamos por 'Banco_Destino'
                bancos = datos_dia.groupby('Banco_Destino')['Total'].sum().reset_index()
                st.dataframe(
                    bancos, 
                    column_config={
                        "Total": st.column_config.NumberColumn("Ingreso Total", format="$%.0f"),
                        "Banco_Destino": "Cuenta"
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Sin ventas hoy.")

        with c2:
            st.subheader("📉 Salidas por Origen (Gastos)")
            if not df_g.empty and not gastos_dia.empty:
                salidas = gastos_dia.groupby('Banco_Origen')['Monto'].sum().reset_index()
                st.dataframe(
                    salidas,
                    column_config={
                        "Monto": st.column_config.NumberColumn("Gasto Total", format="$%.0f"),
                        "Banco_Origen": "Cuenta Origen"
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Sin gastos hoy.")

        st.markdown("---")
        st.subheader("📊 Métodos de Pago Usados")
        if not datos_dia.empty:
            chart_data = datos_dia.groupby('Metodo_Pago')['Total'].sum()
            st.bar_chart(chart_data)

# --- MAIN ---

def main():
    configurar_pagina()
    
    # Sidebar Navigation
    st.sidebar.title("🐾 Menú Principal")
    opcion = st.sidebar.radio("Ir a:", ["Punto de Venta", "Despachos y Envíos", "Registro de Gastos", "Cierre y Finanzas"])
    st.sidebar.markdown("---")
    st.sidebar.caption("Bigotes y Patitas v3.0 Super App")
    
    ws_inv, ws_cli, ws_ven, ws_gas = conectar_google_sheets()
    
    if not ws_inv:
        st.warning("Esperando conexión a Google Sheets...")
        return

    if opcion == "Punto de Venta":
        tab_punto_venta(ws_inv, ws_cli, ws_ven)
    
    elif opcion == "Despachos y Envíos":
        tab_envios(ws_ven)
        
    elif opcion == "Registro de Gastos":
        tab_gastos(ws_gas)
        
    elif opcion == "Cierre y Finanzas":
        tab_cierre(ws_ven, ws_gas)

if __name__ == "__main__":
    main()
