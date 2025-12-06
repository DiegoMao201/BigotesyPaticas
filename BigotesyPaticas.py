import streamlit as st
import pandas as pd
import gspread
from io import BytesIO
from datetime import datetime, date, timedelta
import time
import numpy as np
import base64
import jinja2
from weasyprint import HTML, CSS
import plotly.express as px  # Agregamos Plotly para gráficos financieros pro

# --- 1. CONFIGURACIÓN Y ESTILOS ---

COLOR_PRIMARIO = "#2ecc71"  # Verde Éxito
COLOR_SECUNDARIO = "#27ae60" # Verde Oscuro
COLOR_FONDO = "#f4f6f9"
COLOR_TEXTO = "#2c3e50"
COLOR_GASTO = "#e74c3c"
COLOR_INVERSION = "#3498db"

# Logo Verificado (Huella simple en PNG Base64)
LOGO_B64 = """
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
"""

def configurar_pagina():
    st.set_page_config(
        page_title="Bigotes y Patitas PRO",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="expanded"
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
        /* Tabs personalizados */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            white-space: pre-wrap;
            background-color: white;
            border-radius: 5px;
            color: {COLOR_TEXTO};
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {COLOR_PRIMARIO};
            color: white;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y UTILIDADES ---

@st.cache_resource(ttl=600)
def conectar_google_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account y SHEET_URL).")
            return None, None, None, None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        ws_inv = sh.worksheet("Inventario")
        ws_cli = sh.worksheet("Clientes")
        ws_ven = sh.worksheet("Ventas")
        ws_gas = sh.worksheet("Gastos")
        
        # Intentamos conectar la hoja de Capital, si no existe avisamos
        try:
            ws_cap = sh.worksheet("Capital")
        except:
            st.error("⚠️ Falta la hoja 'Capital' en Google Sheets. Por favor créala.")
            ws_cap = None
        
        return ws_inv, ws_cli, ws_ven, ws_gas, ws_cap
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None, None, None, None, None

def sanitizar_dato(dato):
    if isinstance(dato, (np.int64, np.int32, np.integer)): return int(dato)
    elif isinstance(dato, (np.float64, np.float32, np.floating)): return float(dato)
    return dato

def leer_datos(ws):
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        # Convertir columnas numéricas de forma segura
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
        st.error(f"Error guardando en Google Sheets: {e}")
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
        st.error(f"Error actualizando stock: {e}")
        return False

# --- 3. GENERADOR DE PDF ---

def generar_pdf_html(venta_data, items):
    try:
        with open("factura.html", "r", encoding="utf-8") as f:
            template_str = f.read()

        clean_b64 = LOGO_B64.replace('\n', '').replace(' ', '')
        
        context = {
            "logo_b64": clean_b64,
            "id_venta": venta_data['ID'],
            "fecha": venta_data['Fecha'],
            "cliente_nombre": venta_data.get('Cliente', 'Consumidor Final'),
            "cliente_cedula": venta_data.get('Cedula_Cliente', '---'),
            "cliente_direccion": venta_data.get('Direccion', 'Local'),
            "cliente_mascota": venta_data.get('Mascota', '---'),
            "metodo_pago": venta_data.get('Metodo', 'Efectivo'),
            "items": items,
            "total": venta_data['Total']
        }

        template = jinja2.Template(template_str)
        html_renderizado = template.render(context)
        pdf_file = HTML(string=html_renderizado).write_pdf()
        
        return pdf_file
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None

# --- 4. MÓDULOS DE NEGOCIO ---

def tab_punto_venta(ws_inv, ws_cli, ws_ven):
    st.markdown("### 🛒 Punto de Venta (POS)")
    col_izq, col_der = st.columns([1.5, 1])

    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None

    # --- IZQUIERDA ---
    with col_izq:
        # Selección de Cliente
        with st.expander("👤 Selección de Cliente", expanded=True if not st.session_state.cliente_actual else False):
            col_b, col_crear = st.columns([3, 1])
            busqueda = col_b.text_input("Buscar Cédula", placeholder="Ingrese documento...")
            
            if col_b.button("Buscar Cliente"):
                df_c = leer_datos(ws_cli)
                if not df_c.empty:
                    df_c['Cedula'] = df_c['Cedula'].astype(str)
                    busqueda = busqueda.strip()
                    res = df_c[df_c['Cedula'] == busqueda]
                    if not res.empty:
                        st.session_state.cliente_actual = res.iloc[0].to_dict()
                        st.success(f"Cliente: {st.session_state.cliente_actual.get('Nombre')}")
                    else:
                        st.warning("Cliente no encontrado.")
                else:
                    st.warning("Base de clientes vacía.")
            
        if st.session_state.cliente_actual:
            c = st.session_state.cliente_actual
            st.info(f"Cliente: **{c.get('Nombre')}** | Mascota: **{c.get('Mascota', 'N/A')}**")

        # Selección de Productos
        st.markdown("#### Agregar Productos")
        df_inv = leer_datos(ws_inv)
        if not df_inv.empty:
            df_stock = df_inv[df_inv['Stock'] > 0]
            prod_lista = df_stock.apply(lambda x: f"{x.get('Nombre', 'N/A')} | ${x.get('Precio', 0):,.0f} | ID:{x.get('ID_Producto', '')}", axis=1).tolist()
            
            sel_prod = st.selectbox("Buscar Producto", [""] + prod_lista)
            col_cant, col_add = st.columns([1, 2])
            cantidad = col_cant.number_input("Cant", min_value=1, value=1)
            
            if col_add.button("➕ Agregar al Carrito", type="primary"):
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
                            st.error(f"Stock insuficiente. Disponible: {info_p['Stock']}")
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
                st.markdown("#### 💳 Pago")
                tipo_entrega = st.radio("Entrega:", ["Punto de Venta", "Envío a Domicilio"], horizontal=True)
                
                dir_def = st.session_state.cliente_actual.get('Direccion', '') if st.session_state.cliente_actual else ""
                direccion_envio = "Local"
                if tipo_entrega == "Envío a Domicilio":
                    direccion_envio = st.text_input("Dirección de Entrega", value=str(dir_def))

                metodo = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "DaviPlata", "Bancolombia", "Davivienda", "Tarjeta D/C"])
                banco_destino = st.selectbox("Cuenta Destino (Interno)", ["Caja General", "Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata"])
                
                enviar = st.form_submit_button("✅ CONFIRMAR VENTA", type="primary", use_container_width=True)
            
            if enviar:
                if not st.session_state.cliente_actual:
                    st.error("⚠️ Selecciona un cliente primero.")
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
                            
                            # Datos para PDF
                            cliente_pdf_data = {
                                "ID": id_venta,
                                "Fecha": fecha,
                                "Cliente": st.session_state.cliente_actual.get('Nombre', 'Consumidor'),
                                "Cedula_Cliente": str(st.session_state.cliente_actual.get('Cedula', '')),
                                "Direccion": direccion_envio,
                                "Mascota": st.session_state.cliente_actual.get('Mascota', ''),
                                "Total": total,
                                "Metodo": metodo
                            }
                            
                            pdf_bytes = generar_pdf_html(cliente_pdf_data, st.session_state.carrito)
                            st.session_state.ultimo_pdf = pdf_bytes
                            st.session_state.ultima_venta_id = id_venta
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error procesando venta: {e}")
        else:
            st.info("🛒 El carrito está vacío.")

def tab_clientes(ws_cli):
    st.markdown("### 👥 Gestión de Clientes (CRM)")
    with st.container(border=True):
        st.markdown("#### ✨ Nuevo Cliente")
        with st.form("form_cliente"):
            col1, col2 = st.columns(2)
            with col1:
                cedula = st.text_input("Cédula / ID *")
                nombre = st.text_input("Nombre Completo *")
                telefono = st.text_input("Teléfono / WhatsApp *")
                email = st.text_input("Correo Electrónico")
            with col2:
                direccion = st.text_input("Dirección")
                nombre_mascota = st.text_input("Nombre Mascota *")
                tipo_mascota = st.selectbox("Tipo", ["Perro", "Gato", "Ave", "Roedor", "Otro"])
                fecha_nac = st.date_input("Cumpleaños Mascota", value=None)

            if st.form_submit_button("💾 Guardar Cliente", type="primary"):
                if cedula and nombre and nombre_mascota:
                    datos = [cedula, nombre, telefono, email, direccion, nombre_mascota, tipo_mascota, str(fecha_nac), str(date.today())]
                    if escribir_fila(ws_cli, datos):
                        st.success("Cliente guardado.")
                else:
                    st.warning("Completa los campos obligatorios (*).")
    
    st.markdown("#### Base de Datos")
    df = leer_datos(ws_cli)
    st.dataframe(df, use_container_width=True)

def tab_gestion_capital(ws_cap, ws_gas):
    st.markdown("### 💰 Gestión de Inversión y Gastos")
    st.info("Aquí registras el dinero que entra como INVERSIÓN (Capital) y el dinero que sale como GASTO.")

    tab1, tab2 = st.tabs(["📉 Registrar Gasto/Egreso", "📈 Registrar Inversión/Capital"])

    # --- TAB GASTOS ---
    with tab1:
        st.markdown("#### Salida de Dinero")
        with st.form("form_gasto"):
            col1, col2 = st.columns(2)
            with col1:
                tipo_gasto = st.selectbox("Clasificación", ["Gasto Fijo", "Gasto Variable", "Costo de Venta (Mercancía)"])
                categoria = st.selectbox("Concepto", ["Compra de Mercancía", "Arriendo", "Nómina", "Servicios", "Publicidad", "Mantenimiento", "Otros"])
                descripcion = st.text_input("Detalle")
            with col2:
                monto = st.number_input("Monto Salida ($)", min_value=0.0)
                origen = st.selectbox("¿De dónde salió el dinero?", ["Caja General", "Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata", "Caja Menor"])
                fecha_gasto = st.date_input("Fecha Gasto", value=date.today())

            if st.form_submit_button("🔴 Registrar Gasto"):
                if monto > 0:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    datos = [ts, str(fecha_gasto), tipo_gasto, categoria, descripcion, monto, "N/A", origen]
                    if escribir_fila(ws_gas, datos):
                        st.success("Gasto registrado correctamente.")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("El monto debe ser mayor a 0.")

    # --- TAB INVERSIONES ---
    with tab2:
        st.markdown("#### Entrada de Dinero (Inversión)")
        st.caption("Usa esto para la inversión inicial o inyecciones de dinero futuras.")
        
        if ws_cap is None:
            st.error("Error: No se encontró la hoja 'Capital'.")
        else:
            with st.form("form_capital"):
                c1, c2 = st.columns(2)
                with c1:
                    tipo_inv = st.selectbox("Tipo de Inversión", ["Capital Inicial", "Inyección Adicional", "Préstamo Socio"])
                    monto_inv = st.number_input("Monto a Ingresar ($)", min_value=0.0, step=10000.0)
                with c2:
                    destino = st.selectbox("¿A dónde entra el dinero?", ["Bancolombia Ahorros", "Davivienda", "Caja General", "Nequi"])
                    desc_inv = st.text_input("Descripción / Socio")
                    fecha_inv = st.date_input("Fecha Inversión", value=date.today())

                if st.form_submit_button("🔵 Registrar Inversión"):
                    if monto_inv > 0:
                        id_cap = datetime.now().strftime("%Y%m%d%H%M")
                        datos_cap = [id_cap, str(fecha_inv), tipo_inv, monto_inv, destino, desc_inv]
                        if escribir_fila(ws_cap, datos_cap):
                            st.success(f"Inversión de ${monto_inv:,.0f} registrada exitosamente.")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("El monto debe ser positivo.")

def tab_cuadre_diario(ws_ven, ws_gas, ws_cap):
    st.markdown("### ⚖️ Cuadre de Caja (Diario)")
    st.markdown("Utiliza esta herramienta al finalizar el día para verificar que el dinero físico y digital coincida.")

    fecha_analisis = st.date_input("📅 Seleccionar Fecha de Cuadre", value=date.today())
    
    # Cargar datos
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)
    df_c = leer_datos(ws_cap)

    # Convertir fechas
    for df in [df_v, df_g, df_c]:
        if not df.empty and 'Fecha' in df.columns:
            df['Fecha_Dt'] = pd.to_datetime(df['Fecha']).dt.date

    # Filtrar por día
    v_dia = df_v[df_v['Fecha_Dt'] == fecha_analisis] if not df_v.empty else pd.DataFrame()
    g_dia = df_g[df_g['Fecha_Dt'] == fecha_analisis] if not df_g.empty else pd.DataFrame()
    c_dia = df_c[df_c['Fecha_Dt'] == fecha_analisis] if not df_c.empty else pd.DataFrame()

    # Cálculos
    total_ventas = v_dia['Total'].sum() if not v_dia.empty else 0
    total_inversion = c_dia['Monto'].sum() if not c_dia.empty else 0
    total_gastos = g_dia['Monto'].sum() if not g_dia.empty else 0
    flujo_neto = (total_ventas + total_inversion) - total_gastos

    # Métricas Principales
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Ventas (Ingreso)", f"${total_ventas:,.0f}", delta="Operativo")
    m2.metric("Total Inversión (Entrada)", f"${total_inversion:,.0f}", delta="Capital")
    m3.metric("Total Gastos (Salida)", f"${total_gastos:,.0f}", delta="-Salidas", delta_color="inverse")
    m4.metric("💰 Flujo Neto del Día", f"${flujo_neto:,.0f}", delta_color="normal" if flujo_neto >= 0 else "inverse")
    st.markdown("---")

    # Detalle por Cuenta/Banco (La parte más importante para cuadrar)
    st.subheader("🔎 Detalle para Cuadre (Por Cuenta)")
    st.info("Compara estos montos con lo que tienes realmente en cada cuenta o cajón.")

    cuentas = ["Efectivo", "Caja General", "Nequi", "DaviPlata", "Bancolombia", "Bancolombia Ahorros", "Davivienda", "Tarjeta Débito/Crédito", "Caja Menor"]
    # Normalizamos nombres para el reporte
    resumen_cuentas = []

    for cta in cuentas:
        # Entradas por Ventas (Banco_Destino)
        v_cta = v_dia[v_dia['Banco_Destino'].astype(str).str.contains(cta, case=False, na=False)]['Total'].sum() if not v_dia.empty else 0
        # Entradas por Inversión (Destino_Fondos)
        i_cta = c_dia[c_dia['Destino_Fondos'].astype(str).str.contains(cta, case=False, na=False)]['Monto'].sum() if not c_dia.empty else 0
        # Salidas por Gastos (Banco_Origen)
        g_cta = g_dia[g_dia['Banco_Origen'].astype(str).str.contains(cta, case=False, na=False)]['Monto'].sum() if not g_dia.empty else 0
        
        neto = (v_cta + i_cta) - g_cta
        if v_cta > 0 or i_cta > 0 or g_cta > 0:
            resumen_cuentas.append({
                "Cuenta / Medio": cta,
                "Entrada (Ventas)": v_cta,
                "Entrada (Capital)": i_cta,
                "Salidas (Gastos)": g_cta,
                "DEBE HABER HOY": neto
            })
    
    if resumen_cuentas:
        df_resumen = pd.DataFrame(resumen_cuentas)
        st.dataframe(df_resumen.style.format({
            "Entrada (Ventas)": "${:,.0f}", 
            "Entrada (Capital)": "${:,.0f}", 
            "Salidas (Gastos)": "${:,.0f}", 
            "DEBE HABER HOY": "${:,.0f}"
        }), use_container_width=True)
    else:
        st.warning("No hubo movimientos registrados para esta fecha.")

def tab_finanzas_pro(ws_ven, ws_gas, ws_cap):
    st.markdown("### 📊 Estado de Resultados & Finanzas")
    st.markdown("Reporte financiero gerencial para toma de decisiones.")

    # Filtros de Fecha Globales
    col_d1, col_d2 = st.columns(2)
    f_inicio = col_d1.date_input("Desde", value=date.today().replace(day=1))
    f_fin = col_d2.date_input("Hasta", value=date.today())

    # Cargar Data
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)
    df_c = leer_datos(ws_cap)

    # Preprocesamiento Fechas
    if not df_v.empty: df_v['Fecha_Dt'] = pd.to_datetime(df_v['Fecha']).dt.date
    if not df_g.empty: df_g['Fecha_Dt'] = pd.to_datetime(df_g['Fecha']).dt.date
    if not df_c.empty: df_c['Fecha_Dt'] = pd.to_datetime(df_c['Fecha']).dt.date

    # Filtrar Rango
    v_rango = df_v[(df_v['Fecha_Dt'] >= f_inicio) & (df_v['Fecha_Dt'] <= f_fin)] if not df_v.empty else pd.DataFrame()
    g_rango = df_g[(df_g['Fecha_Dt'] >= f_inicio) & (df_g['Fecha_Dt'] <= f_fin)] if not df_g.empty else pd.DataFrame()
    
    # --- CÁLCULO ESTADO DE RESULTADOS (P&L) ---
    # 1. Ingresos Operacionales
    ingresos = v_rango['Total'].sum() if not v_rango.empty else 0

    # 2. Costo de Venta (Aproximación por Gasto 'Compra de Mercancía' o 'Costo de Venta')
    # Asumimos contabilidad de caja: Lo que gasté en mercancía en este periodo es el costo.
    costos = 0
    gastos_op = 0
    if not g_rango.empty:
        # Filtramos Costos Directos (Mercancía) vs Gastos Operativos (Arriendo, etc)
        mask_costo = g_rango['Categoria'].isin(['Costo de Venta', 'Costo de Venta (Mercancía)'])
        costos = g_rango[mask_costo]['Monto'].sum()
        gastos_op = g_rango[~mask_costo]['Monto'].sum()

    utilidad_bruta = ingresos - costos
    utilidad_neta = utilidad_bruta - gastos_op
    
    margen_neto = (utilidad_neta / ingresos * 100) if ingresos > 0 else 0

    # --- VISUALIZACIÓN ---
    st.markdown("#### 1. Estado de Pérdidas y Ganancias (P&L)")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Ingresos (Ventas)", f"${ingresos:,.0f}")
    kpi2.metric("Costos Directos", f"${costos:,.0f}")
    kpi3.metric("Gastos Operativos", f"${gastos_op:,.0f}")
    kpi4.metric("Utilidad Neta", f"${utilidad_neta:,.0f}", delta=f"{margen_neto:.1f}% Margen")

    # Gráfico de Cascada (Waterfall) simplificado con Bar Chart
    datos_pl = pd.DataFrame({
        "Concepto": ["(+) Ingresos", "(-) Costos", "(=) Utilidad Bruta", "(-) Gastos Ops", "(=) Utilidad Neta"],
        "Monto": [ingresos, -costos, utilidad_bruta, -gastos_op, utilidad_neta],
        "Color": ["Positivo", "Negativo", "Total", "Negativo", "Final"]
    })
    
    fig_pl = px.bar(datos_pl, x="Concepto", y="Monto", color="Color", 
                    color_discrete_map={"Positivo": COLOR_PRIMARIO, "Negativo": COLOR_GASTO, "Total": "#95a5a6", "Final": COLOR_INVERSION},
                    text_auto='.2s', title="Estructura Financiera del Periodo")
    st.plotly_chart(fig_pl, use_container_width=True)

    st.markdown("#### 2. Análisis de Retorno de Inversión (Histórico Total)")
    total_invertido = df_c['Monto'].sum() if not df_c.empty else 0
    
    # Calculamos la utilidad acumulada histórica (aproximada con todos los datos disponibles)
    historico_ventas = df_v['Total'].sum() if not df_v.empty else 0
    historico_gastos = df_g['Monto'].sum() if not df_g.empty else 0
    utilidad_acumulada = historico_ventas - historico_gastos
    
    col_inv1, col_inv2 = st.columns(2)
    with col_inv1:
        st.metric("Total Capital Invertido (Histórico)", f"${total_invertido:,.0f}")
        roi = (utilidad_acumulada / total_invertido * 100) if total_invertido > 0 else 0
        st.metric("ROI (Retorno sobre Inversión)", f"{roi:.1f}%", help="Mide cuánto has ganado respecto a lo que invertiste.")
    
    with col_inv2:
        st.info(f"""
        **Interpretación:**
        - Has invertido un total de **${total_invertido:,.0f}**.
        - Tu negocio ha generado una utilidad neta histórica de **${utilidad_acumulada:,.0f}**.
        - { "¡Excelente! Ya recuperaste tu inversión y estás ganando." if utilidad_acumulada > total_invertido else "Aún estás en proceso de recuperar la inversión inicial." }
        """)

# --- MAIN ---

def main():
    configurar_pagina()
    
    # Sidebar Estilizado
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2171/2171991.png", width=100)
        st.title("Bigotes y Patitas")
        st.caption("Sistema ERP v4.0")
        st.markdown("---")
        opcion = st.radio("Navegación", 
            ["Punto de Venta", "Gestión de Clientes", "Inversión y Gastos", "Cuadre Diario (Caja)", "Finanzas & Resultados"],
            index=0
        )
        st.markdown("---")
        st.info("💡 Tip: Realiza el cuadre diario al cerrar el local.")

    ws_inv, ws_cli, ws_ven, ws_gas, ws_cap = conectar_google_sheets()

    if not ws_inv:
        st.warning("🔄 Conectando a la base de datos...")
        return

    if opcion == "Punto de Venta":
        tab_punto_venta(ws_inv, ws_cli, ws_ven)
    elif opcion == "Gestión de Clientes":
        tab_clientes(ws_cli)
    elif opcion == "Inversión y Gastos":
        tab_gestion_capital(ws_cap, ws_gas)
    elif opcion == "Cuadre Diario (Caja)":
        tab_cuadre_diario(ws_ven, ws_gas, ws_cap)
    elif opcion == "Finanzas & Resultados":
        tab_finanzas_pro(ws_ven, ws_gas, ws_cap)

if __name__ == "__main__":
    main()
