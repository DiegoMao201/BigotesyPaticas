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
import plotly.express as px
import plotly.graph_objects as go
import xlsxwriter  # Necesario para exportar a Excel

# --- 1. CONFIGURACIÓN Y ESTILOS ---

COLOR_PRIMARIO = "#2ecc71"  # Verde Éxito
COLOR_SECUNDARIO = "#27ae60" # Verde Oscuro
COLOR_FONDO = "#f4f6f9"
COLOR_TEXTO = "#2c3e50"
COLOR_GASTO = "#e74c3c"
COLOR_INVERSION = "#3498db"
COLOR_ALERTA = "#f39c12"

# Logo Verificado (Huella simple en PNG Base64)
LOGO_B64 = """
iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAHpElEQVRoge2ZbWxT1xXHf+f62Q87TgwJQ54hCQy0U
5oQ6iYU2q60q6pCX7aoq1CfqlO1U9V92EdTtVWbtqmfJlW7PlS1q9qqPqxSZ6uCQJuQMAJMKISQ8BIIcRw7sR37+t774IdJbJzYTuw4rern8917zrnn
/8/5P+fee17AC17wghf8P4R40g0QAuqALsABRICcSeYIsA/4LXBqMu2cdAMmQwjRDLwMrAeWAxVAWshsA74GfAT0CCFOTrR9E2YkCLwM/Ay432Q+
ArwCXBBCHJ/wOicamQf8CngAyDSZ3wWeBz4VQoybdEsmQgjRDHwfeAlIN5kPAz8RQlROtH1jZiQIrADeBBabzIeAHwFnhRCHJ9yCCcII8F3gH4DL
ZH4v8HMhRMVE2zchRgLAA8B7gM9kPgD8SAhxfcItmACMAE8BHwNuk/k9wDeEEJcm2r6JGakH3gXWmcyHgO8LIc5MuAUTgBHgceBfJvNu4MdCiCsT
bd+EGKkF3gU2mswHgO8IIU5NuAUTgBHgCeBvJvNu4EdCiB8n2r6JGakF3gM2m8wHgO8IIU5OuAUTgBHgSeAjJvNu4EdCiCsTbd+EGNkM/ADYajIf
AL4jhDg14RZMMEaAp4CPmMw7gR8JIa5MtH0TM7IZ+CGwzWQ+APyHEOLMhFswARgBngH+YTJvB34khLgy0fZNmL0eAF4E7jWZDwK/EEL8b8ItmCC
MAKuAD4AcMv8B8B0hRG2i7ZuQ2WsFsA3IMpkPAj8RQlROuAUTiBFgJbADyCOzf9K+TwhxbaLtmzAjQWAL8DqQaTIfAv5J+xMhRPVE2zchRgLAKu
AdIMdkPgT8SwhxdsItmACMAKuA94BcMv+X9v1CiGsTbd/EjASBFcC7QC6Z/0f7fiHEmQm3YIIwAqwC3gNyyfxA2/cLIS5PtH0TYmQFsB3IMZkPA
v8WQpybcAsmACPASuADIDvI/EDbDwghrk20fRNmJAhsA34O5JD5gbYfFEJUTLR9E2IkCKwC3gdyyPxA2w8KIc5OuAUTgBFgJfARkE3mB9p+WAhxf
aLtmzAjQWAb8Esgh8wPtP2IEOKMt2CCMQKsBD4CskzmB9p+VAhxbSJsJ8xIEFgH/BLIMZk/0PZjQoiK0bZ5QoyUAI3AaiDfzD4M/EwIcWykbSYA
I8BK4GMgy8w+DPxcCHF1JG0mZEQIsRb4BZBjZh8Gfi6EOObVNlJGehFCfAfIMbMPAz8XQoyY2Yz5P0wIsR74BZBjZh8GfiGEODrSNhM4ewmwc+c
uI7t27TKyt2zZzMjeunUrd999F3ffvYV169awfv06duzYxo4d29i8eRObN29m8+ZNfPe736GxsZGGhga2b99OQ0MD27ZtY+vWzTQ2NrJ16xZ8Ph
/19fV4PB68Xi+1tbXU1tZSW1tLbW0t27ZtY/v27TQ0NNDQ0EBDQwPbtm2joaGBHTt2sHnzZjZv3szmzZvZvHkzmzdvZs+e3YzsAwcOMrKPHj3Ky
D5+/DgA58+fZ2RfuXKFkX3t2jVG9vXr1xnZIyMjAGzZsoW1a9cCsHbtWtatW8f69etZv349GzZsYP369axbt4577rmHdevWsWbNGlauXMmKFS
tYsWIFd955J3feeaep/0c/+hEj+9ixY4zsEydOALL/EydOALL/U6dOAbL/M2fOALL/c+fOAfL/CxcuyP7L/i9dukR/fz/9/f309/fT399Pf38/
AwMDDAwMMDAwwIEDB4wb+f1+vF4vXq8Xr9eL1+vF6/Xi8Xjw+/3U19dTvF4vXq8Xr9eL1+vF4/Hg8/uN/v1+v9H/mjVriP1/9atfMbKPHDnCyD5
69Cgj+7e//S0A586dY2RfvnyZkf3b3/6WkX39+nVG9sjICAD33Xcfd955JwArVqxgxYoVrFixghUrVrBy5UpWrVrFqlWrWbNmDWvWrGHNmjWsWb
OGu+++mzVr1rBmzRrWrFnDmjVrWLNmjan/w8PDjOyRkRFG9vDwsJH9+9//HpD9Hx4eBmT/R0ZGATn/R0ZGADn/R0ZGGBoaYmhoiKGhIYaGhhgaG
mJoaIje3l56e3vp7e2lt7eX3t5eent72b9/P/v372f//v3s37+f/fv3s3//fuJG/H4/dXV11NXVUVdXR11dHXV1dfj9furq6qirq6Ouro66ujrq
6urw+/1G//F6/f8A7r0yHqfVv+oAAAAASUVORK5CYII=
"""

def configurar_pagina():
    st.set_page_config(
        page_title="Bigotes y Patitas ERP PRO",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {COLOR_FONDO}; }}
        h1, h2, h3 {{ color: {COLOR_TEXTO}; font-family: 'Helvetica Neue', sans-serif; }}
        
        /* Contenedores de métricas */
        div[data-testid="metric-container"] {{
            background-color: white;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-left: 5px solid {COLOR_PRIMARIO};
        }}
        
        /* Botones */
        .stButton button[type="primary"] {{
            background: linear-gradient(90deg, {COLOR_PRIMARIO}, {COLOR_SECUNDARIO});
            border: none;
            font-weight: bold;
            box-shadow: 0 4px 6px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
        }}
        .stButton button[type="primary"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.2);
        }}
        
        /* Inputs */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
            border-radius: 8px;
            border: 1px solid #ddd;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            white-space: pre-wrap;
            background-color: white;
            border-radius: 8px 8px 0 0;
            color: {COLOR_TEXTO};
            font-weight: 500;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {COLOR_PRIMARIO};
            color: white;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y UTILIDADES ---

@st.cache_resource(ttl=300)
def conectar_google_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account y SHEET_URL).")
            return None, None, None, None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        return (sh.worksheet("Inventario"), sh.worksheet("Clientes"), 
                sh.worksheet("Ventas"), sh.worksheet("Gastos"), sh.worksheet("Capital"))
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
        # Limpieza robusta de numéricos
        for col in ['Precio', 'Stock', 'Monto', 'Total', 'Cantidad', 'Subtotal']:
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

# --- 3. EXPORTADOR EXCEL Y PDF ---

def generar_excel_financiero(df_v, df_g, df_c):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # Formatos
    fmt_moneda = workbook.add_format({'num_format': '$#,##0', 'font_name': 'Arial', 'font_size': 10})
    fmt_fecha = workbook.add_format({'num_format': 'dd/mm/yyyy', 'font_name': 'Arial', 'font_size': 10})
    fmt_header = workbook.add_format({'bold': True, 'bg_color': '#2ecc71', 'font_color': 'white', 'border': 1})

    # Función auxiliar para escribir hojas
    def escribir_hoja(df, nombre_hoja):
        if df.empty: return
        worksheet = workbook.add_worksheet(nombre_hoja)
        # Headers
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, fmt_header)
        # Data
        for row_num, row in enumerate(df.values):
            for col_num, cell_value in enumerate(row):
                if isinstance(cell_value, (float, int)):
                    worksheet.write(row_num + 1, col_num, cell_value, fmt_moneda)
                else:
                    worksheet.write(row_num + 1, col_num, cell_value)
        worksheet.autofit()

    escribir_hoja(df_v, "Reporte_Ventas")
    escribir_hoja(df_g, "Reporte_Gastos")
    escribir_hoja(df_c, "Reporte_Capital")

    workbook.close()
    return output.getvalue()

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
            "items": items,
            "total": venta_data['Total']
        }
        template = jinja2.Template(template_str)
        html_renderizado = template.render(context)
        return HTML(string=html_renderizado).write_pdf()
    except: return None

# --- 4. MÓDULOS DE NEGOCIO ---

def tab_punto_venta(ws_inv, ws_cli, ws_ven):
    st.markdown("### 🛒 Punto de Venta (POS)")
    col_izq, col_der = st.columns([1.5, 1])

    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None

    with col_izq:
        # Selección Cliente
        with st.expander("👤 Cliente", expanded=not st.session_state.cliente_actual):
            col_b, col_crear = st.columns([3, 1])
            busqueda = col_b.text_input("Buscar Cédula")
            if col_b.button("Buscar"):
                df_c = leer_datos(ws_cli)
                if not df_c.empty:
                    df_c['Cedula'] = df_c['Cedula'].astype(str)
                    res = df_c[df_c['Cedula'] == busqueda.strip()]
                    if not res.empty:
                        st.session_state.cliente_actual = res.iloc[0].to_dict()
                        st.success("Cliente encontrado.")
                    else: st.warning("No encontrado.")
        
        if st.session_state.cliente_actual:
            st.info(f"Cliente: **{st.session_state.cliente_actual.get('Nombre')}**")

        # Selección Productos
        st.markdown("#### Productos")
        df_inv = leer_datos(ws_inv)
        if not df_inv.empty:
            df_stock = df_inv[df_inv['Stock'] > 0]
            prod_lista = df_stock.apply(lambda x: f"{x.get('Nombre')} | ${x.get('Precio'):,.0f} | ID:{x.get('ID_Producto')}", axis=1).tolist()
            sel_prod = st.selectbox("Buscar Item", [""] + prod_lista)
            col_cant, col_add = st.columns([1, 2])
            cantidad = col_cant.number_input("Cant", 1, 100, 1)
            
            if col_add.button("➕ Agregar", type="primary"):
                if sel_prod:
                    id_p = sel_prod.split("ID:")[1]
                    info_p = df_inv[df_inv['ID_Producto'].astype(str) == id_p].iloc[0]
                    if cantidad <= info_p['Stock']:
                        st.session_state.carrito.append({
                            "ID_Producto": info_p['ID_Producto'],
                            "Nombre_Producto": info_p['Nombre'],
                            "Precio": float(info_p['Precio']),
                            "Cantidad": int(cantidad),
                            "Subtotal": float(info_p['Precio'] * cantidad)
                        })
                    else: st.error("Stock insuficiente")

    with col_der:
        st.markdown("### 🧾 Resumen")
        if st.session_state.ultimo_pdf:
            st.success("✅ Venta Guardada")
            st.download_button("🖨️ Descargar Recibo", st.session_state.ultimo_pdf, "recibo.pdf", "application/pdf")
            if st.button("🔄 Nueva Venta"):
                st.session_state.carrito = []
                st.session_state.cliente_actual = None
                st.session_state.ultimo_pdf = None
                st.rerun()
        
        elif st.session_state.carrito:
            df_cart = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_cart[['Nombre_Producto', 'Cantidad', 'Subtotal']], hide_index=True)
            total = df_cart['Subtotal'].sum()
            st.metric("Total a Pagar", f"${total:,.0f}")
            
            with st.form("cobro"):
                metodo = st.selectbox("Método Pago", ["Efectivo", "Nequi", "DaviPlata", "Bancolombia", "Tarjeta"])
                # Lógica simplificada de destino
                destino_map = {"Efectivo": "Caja General", "Nequi": "Nequi", "DaviPlata": "DaviPlata", 
                               "Bancolombia": "Bancolombia Ahorros", "Tarjeta": "Bancolombia Ahorros"}
                
                if st.form_submit_button("✅ COBRAR", type="primary"):
                    if not st.session_state.cliente_actual:
                        st.error("Falta Cliente")
                    else:
                        id_venta = datetime.now().strftime("%Y%m%d%H%M%S")
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        items_str = ", ".join([f"{i['Nombre_Producto']} (x{i['Cantidad']})" for i in st.session_state.carrito])
                        
                        datos = [id_venta, fecha, str(st.session_state.cliente_actual['Cedula']), 
                                 st.session_state.cliente_actual['Nombre'], "Punto de Venta", "Local", "Entregado",
                                 metodo, destino_map[metodo], total, items_str]
                        
                        if escribir_fila(ws_ven, datos):
                            actualizar_stock(ws_inv, st.session_state.carrito)
                            st.session_state.ultimo_pdf = generar_pdf_html({
                                "ID": id_venta, "Fecha": fecha, "Total": total, "Cliente": st.session_state.cliente_actual['Nombre']
                            }, st.session_state.carrito)
                            st.rerun()

def tab_gestion_capital(ws_cap, ws_gas):
    st.markdown("### 💰 Gestión de Inversión y Gastos")
    t1, t2 = st.tabs(["📉 Registrar Gasto", "📈 Registrar Capital"])
    
    with t1:
        with st.form("form_gasto"):
            c1, c2 = st.columns(2)
            with c1:
                tipo = st.selectbox("Clasificación", ["Gasto Fijo", "Gasto Variable", "Costo de Venta (Mercancía)"])
                cat = st.selectbox("Concepto", ["Mercancía", "Arriendo", "Nómina", "Servicios", "Publicidad", "Mantenimiento", "Otros"])
                desc = st.text_input("Detalle")
            with c2:
                monto = st.number_input("Monto Salida ($)", min_value=0.0)
                origen = st.selectbox("Salió de:", ["Caja General", "Bancolombia Ahorros", "Nequi", "DaviPlata", "Caja Menor"])
                fecha = st.date_input("Fecha", date.today())
            
            if st.form_submit_button("🔴 Registrar Gasto"):
                if monto > 0:
                    datos = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(fecha), tipo, cat, desc, monto, "N/A", origen]
                    escribir_fila(ws_gas, datos)
                    st.success("Gasto registrado")

    with t2:
        with st.form("form_cap"):
            c1, c2 = st.columns(2)
            with c1:
                tipo_inv = st.selectbox("Tipo", ["Capital Inicial", "Inyección Adicional", "Préstamo"])
                monto_inv = st.number_input("Monto Ingreso ($)", min_value=0.0)
            with c2:
                destino = st.selectbox("Ingresó a:", ["Bancolombia Ahorros", "Caja General", "Nequi"])
                desc_inv = st.text_input("Socio/Detalle")
                fecha_inv = st.date_input("Fecha Inv", date.today())
            
            if st.form_submit_button("🔵 Registrar Inversión"):
                if monto_inv > 0:
                    escribir_fila(ws_cap, [datetime.now().strftime("%Y%m%d%H%M"), str(fecha_inv), tipo_inv, monto_inv, destino, desc_inv])
                    st.success("Capital registrado")

def tab_cuadre_diario_pro(ws_ven, ws_gas, ws_cap):
    st.markdown("### ⚖️ Cuadre de Caja Profesional")
    st.caption("Verificación contable de efectivo físico vs. registros digitales.")

    col_fecha, col_base = st.columns(2)
    fecha_analisis = col_fecha.date_input("📅 Fecha de Cierre", value=date.today())
    base_caja = col_base.number_input("💵 Base de Caja Inicial", value=200000.0, step=1000.0, help="Dinero con el que iniciaste el día en el cajón.")

    # 1. Cargar Data del Día
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)
    df_c = leer_datos(ws_cap)

    # Filtrar Fechas
    for df in [df_v, df_g, df_c]:
        if not df.empty and 'Fecha' in df.columns:
            df['Fecha_Dt'] = pd.to_datetime(df['Fecha']).dt.date
    
    v_dia = df_v[df_v['Fecha_Dt'] == fecha_analisis] if not df_v.empty else pd.DataFrame()
    g_dia = df_g[df_g['Fecha_Dt'] == fecha_analisis] if not df_g.empty else pd.DataFrame()
    c_dia = df_c[df_c['Fecha_Dt'] == fecha_analisis] if not df_c.empty else pd.DataFrame()

    st.markdown("---")
    
    # 2. Separar Flujos: EFECTIVO vs DIGITAL
    # Ventas
    ventas_efectivo = v_dia[v_dia['Metodo'] == 'Efectivo']['Total'].sum() if not v_dia.empty else 0
    ventas_digital = v_dia[v_dia['Metodo'] != 'Efectivo']['Total'].sum() if not v_dia.empty else 0
    
    # Gastos (Salidas de Caja vs Salidas de Banco)
    gastos_efectivo = g_dia[g_dia['Banco_Origen'].astype(str).str.contains('Caja', case=False)]['Monto'].sum() if not g_dia.empty else 0
    
    # Capital (Entradas a Caja)
    capital_efectivo = c_dia[c_dia['Destino_Fondos'].astype(str).str.contains('Caja', case=False)]['Monto'].sum() if not c_dia.empty else 0

    # 3. Cálculo Teórico (Lo que debe haber en el cajón)
    total_debe_haber = base_caja + ventas_efectivo + capital_efectivo - gastos_efectivo

    # 4. Interfaz de Conteo Real
    col_teorico, col_conteo = st.columns(2)
    
    with col_teorico:
        st.subheader("📊 Movimiento Teórico (Sistema)")
        st.markdown(f"""
        | Concepto | Monto |
        | :--- | :--- |
        | **(+) Base Inicial** | **${base_caja:,.0f}** |
        | (+) Ventas en Efectivo | ${ventas_efectivo:,.0f} |
        | (+) Entradas Capital Efectivo | ${capital_efectivo:,.0f} |
        | (-) Salidas/Gastos en Efectivo | -${gastos_efectivo:,.0f} |
        | **(=) DEBE HABER EN CAJÓN** | **${total_debe_haber:,.0f}** |
        """)
        
        st.info(f"💰 Ventas Digitales (Bancos/Nequi): ${ventas_digital:,.0f}")

    with col_conteo:
        st.subheader("🖐️ Conteo Físico (Realidad)")
        dinero_contado = st.number_input("¿Cuánto dinero contaste en el cajón?", min_value=0.0, step=100.0, format="%.2f")
        
        diferencia = dinero_contado - total_debe_haber
        
        st.markdown("---")
        if dinero_contado > 0:
            if abs(diferencia) < 100:
                st.success(f"✅ ¡CUADRE PERFECTO! Diferencia: ${diferencia:,.0f}")
            elif diferencia > 0:
                st.warning(f"⚠️ Sobrante de Caja: ${diferencia:,.0f} (Revisa si no registraste una venta)")
            else:
                st.error(f"🚨 Faltante de Caja: ${diferencia:,.0f} (Revisa si olvidaste anotar un gasto)")

def tab_finanzas_pro(ws_ven, ws_gas, ws_cap):
    st.markdown("## 🚀 Centro de Control Financiero (CEO Dashboard)")
    st.markdown("Análisis estratégico para la toma de decisiones sobre tu inversión.")

    # 1. Filtros y Descarga
    with st.container():
        c1, c2, c3 = st.columns([1, 1, 2])
        f_ini = c1.date_input("Desde", date.today().replace(day=1))
        f_fin = c2.date_input("Hasta", date.today())
        
        # Cargar Data Global
        df_v = leer_datos(ws_ven)
        df_g = leer_datos(ws_gas)
        df_c = leer_datos(ws_cap)
        
        # Procesar fechas
        for df in [df_v, df_g, df_c]:
            if not df.empty: df['Fecha_Dt'] = pd.to_datetime(df['Fecha']).dt.date
        
        # Filtrar Data
        v_ok = df_v[(df_v['Fecha_Dt'] >= f_ini) & (df_v['Fecha_Dt'] <= f_fin)] if not df_v.empty else pd.DataFrame()
        g_ok = df_g[(df_g['Fecha_Dt'] >= f_ini) & (df_g['Fecha_Dt'] <= f_fin)] if not df_g.empty else pd.DataFrame()
        c_ok = df_c[(df_c['Fecha_Dt'] >= f_ini) & (df_c['Fecha_Dt'] <= f_fin)] if not df_c.empty else pd.DataFrame()

        # Botón Excel
        excel_data = generar_excel_financiero(v_ok, g_ok, c_ok)
        c3.download_button(
            label="📥 Descargar Reporte Excel Completo",
            data=excel_data,
            file_name=f"Finanzas_Bigotes_{f_ini}_{f_fin}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

    st.markdown("---")

    # 2. KPIs Principales
    ingresos = v_ok['Total'].sum() if not v_ok.empty else 0
    gastos_totales = g_ok['Monto'].sum() if not g_ok.empty else 0
    utilidad_neta = ingresos - gastos_totales
    margen = (utilidad_neta / ingresos * 100) if ingresos > 0 else 0
    inversion_total_historica = df_c['Monto'].sum() if not df_c.empty else 1 # Evitar div/0
    roi = (utilidad_neta / inversion_total_historica * 100)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Ventas Totales", f"${ingresos:,.0f}", help="Ingreso Bruto en el periodo")
    k2.metric("Gastos Totales", f"${gastos_totales:,.0f}", delta_color="inverse", help="Salidas operativas y costos")
    k3.metric("Utilidad Neta", f"${utilidad_neta:,.0f}", delta=f"{margen:.1f}% Margen", help="Lo que realmente queda")
    k4.metric("Inversión Total", f"${inversion_total_historica:,.0f}", help="Capital histórico inyectado")
    k5.metric("ROI Periodo", f"{roi:.1f}%", help="Retorno sobre la inversión en este periodo")

    # 3. Gráficos Profesionales
    c_graf1, c_graf2 = st.columns([2, 1])

    with c_graf1:
        st.subheader("📈 Tendencia de Ingresos vs Gastos")
        if not v_ok.empty or not g_ok.empty:
            # Agrupar por día
            v_day = v_ok.groupby('Fecha_Dt')['Total'].sum().reset_index() if not v_ok.empty else pd.DataFrame(columns=['Fecha_Dt', 'Total'])
            g_day = g_ok.groupby('Fecha_Dt')['Monto'].sum().reset_index() if not g_ok.empty else pd.DataFrame(columns=['Fecha_Dt', 'Monto'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=v_day['Fecha_Dt'], y=v_day['Total'], mode='lines+markers', name='Ingresos', line=dict(color=COLOR_PRIMARIO, width=3)))
            fig.add_trace(go.Bar(x=g_day['Fecha_Dt'], y=g_day['Monto'], name='Gastos', marker_color=COLOR_GASTO, opacity=0.6))
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos suficientes para graficar.")

    with c_graf2:
        st.subheader("🍩 Desglose de Gastos")
        if not g_ok.empty:
            fig_pie = px.donut(g_ok, values='Monto', names='Categoria', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay gastos registrados.")

    # 4. Insights Detallados
    c_ins1, c_ins2 = st.columns(2)
    
    with c_ins1:
        st.subheader("🏆 Top Productos Vendidos")
        if not v_ok.empty:
            # Parsear items string simple
            all_items = []
            for idx, row in v_ok.iterrows():
                items_raw = row.get('Items', '')
                if items_raw:
                    # Logica simple de parseo string "Prod (xN)"
                    parts = items_raw.split(',')
                    for p in parts:
                        nombre = p.split('(')[0].strip()
                        all_items.append(nombre)
            
            if all_items:
                df_top = pd.DataFrame(all_items, columns=['Producto']).value_counts().reset_index(name='Ventas')
                st.dataframe(df_top.head(5), use_container_width=True, hide_index=True)
            else: st.info("No se pudieron parsear los items.")
            
            # Ticket Promedio
            num_ventas = len(v_ok)
            ticket_prom = ingresos / num_ventas if num_ventas > 0 else 0
            st.metric("Ticket Promedio de Venta", f"${ticket_prom:,.0f}")

    with c_ins2:
        st.subheader("💳 Preferencia de Pago")
        if not v_ok.empty:
            df_metodo = v_ok.groupby('Metodo')['Total'].sum().reset_index()
            fig_bar = px.bar(df_metodo, x='Metodo', y='Total', text_auto='.2s', color='Total', color_continuous_scale='Greens')
            fig_bar.update_layout(height=300)
            st.plotly_chart(fig_bar, use_container_width=True)


# --- MAIN ---

def main():
    configurar_pagina()
    
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2171/2171991.png", width=80)
        st.title("Bigotes PRO")
        opcion = st.radio("Menú", ["Punto de Venta", "Clientes", "Inversión y Gastos", "Cuadre de Caja", "Finanzas CEO"])
        st.markdown("---")
        st.info("Sistema v5.0 Ultimate")

    ws_inv, ws_cli, ws_ven, ws_gas, ws_cap = conectar_google_sheets()

    if not ws_inv: return

    if opcion == "Punto de Venta": tab_punto_venta(ws_inv, ws_cli, ws_ven)
    elif opcion == "Clientes": 
        st.dataframe(leer_datos(ws_cli), use_container_width=True) # Vista simple
    elif opcion == "Inversión y Gastos": tab_gestion_capital(ws_cap, ws_gas)
    elif opcion == "Cuadre de Caja": tab_cuadre_diario_pro(ws_ven, ws_gas, ws_cap)
    elif opcion == "Finanzas CEO": tab_finanzas_pro(ws_ven, ws_gas, ws_cap)

if __name__ == "__main__":
    main()
