import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime, date
import time
import numpy as np
from jinja2 import Template
from weasyprint import HTML, CSS

# --- 1. CONFIGURACIÓN Y ESTILOS GLOBALES ---

COLOR_PRIMARIO = "#667eea"  # Color principal de tu factura
COLOR_SECUNDARIO = "#764ba2" # Color secundario de tu factura
COLOR_FONDO = "#f4f7fe"
COLOR_TEXTO = "#2c3e50"

st.set_page_config(
    page_title="Bigotes y Patitas ERP",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_FONDO}; }}
    div.stButton > button:first-child {{
        background: linear-gradient(135deg, {COLOR_PRIMARIO} 0%, {COLOR_SECUNDARIO} 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: transform 0.2s;
    }}
    div.stButton > button:hover {{
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }}
    .metric-card {{
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid {COLOR_PRIMARIO};
    }}
    </style>
""", unsafe_allow_html=True)

# --- 2. PLANTILLA HTML JINJA2 (Tu diseño integrado) ---

HTML_TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Factura - {{ business_name }}</title>
    <style>
        @page { size: A4; margin: 0; }
        body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; -webkit-print-color-adjust: exact; }
        .invoice-container { width: 100%; background: white; }
        .invoice-header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; padding: 40px; display: flex; justify-content: space-between; 
        }
        .business-info h1 { margin: 0; font-size: 28px; font-weight: 700; }
        .business-info p { margin: 2px 0; font-size: 13px; opacity: 0.95; }
        .invoice-number { text-align: right; }
        .invoice-number h2 { margin: 0; font-size: 32px; font-weight: 700; }
        .client-section { padding: 30px 40px; display: flex; justify-content: space-between; gap: 30px; }
        .section-title { font-size: 12px; font-weight: 700; text-transform: uppercase; color: #667eea; margin-bottom: 10px; letter-spacing: 1px;}
        .client-info p, .invoice-details p { margin: 5px 0; color: #333; font-size: 14px; }
        .items-table { width: 100%; border-collapse: collapse; margin: 20px 0; padding: 0 40px; }
        .items-table th { background: #f8f9fa; padding: 15px 40px; text-align: left; font-size: 12px; font-weight: 700; text-transform: uppercase; color: #667eea; border-bottom: 2px solid #667eea; }
        .items-table td { padding: 15px 40px; border-bottom: 1px solid #e9ecef; color: #333; font-size: 14px; }
        .items-table th:last-child, .items-table td:last-child { text-align: right; }
        .totals-section { padding: 0 40px 30px; display: flex; justify-content: flex-end; }
        .totals-table { width: 300px; }
        .total-row { display: flex; justify-content: space-between; padding: 8px 0; font-size: 14px; color: #666; }
        .grand-total { font-size: 20px; font-weight: 700; color: #667eea; border-top: 1px solid #ddd; padding-top: 15px; margin-top: 5px; }
        .invoice-footer { background: #f8f9fa; padding: 30px 40px; text-align: center; border-top: 3px solid #667eea; font-size: 14px; color: #666; }
        .thank-you { font-size: 18px; font-weight: 600; color: #667eea; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="invoice-container">
        <div class="invoice-header">
            <div class="business-info">
                <h1>🐾 {{ business_name }}</h1>
                <p>Dirección: Calle Principal #123</p>
                <p>Tel: 320 504 6277</p>
                <p>Email: bigotesypaticasdosquebradas@gmail.com</p>
            </div>
            <div class="invoice-number">
                <h2>FACTURA</h2>
                <p><strong>No:</strong> {{ invoice_id }}</p>
                <p><strong>Fecha:</strong> {{ date }}</p>
            </div>
        </div>

        <div class="client-section">
            <div class="client-info">
                <div class="section-title">Facturado a:</div>
                <p><strong>{{ client_name }}</strong></p>
                <p>ID: {{ client_id }}</p>
                <p>{{ client_address }}</p>
                <p>Mascota: {{ pet_name }}</p>
            </div>
            <div class="invoice-details">
                <div class="section-title">Detalles de Pago:</div>
                <p><strong>Método:</strong> {{ payment_method }}</p>
                <p><strong>Estado:</strong> Pagado / {{ delivery_status }}</p>
            </div>
        </div>

        <table class="items-table">
            <thead>
                <tr>
                    <th>Descripción</th>
                    <th style="text-align: center;">Cant.</th>
                    <th style="text-align: right;">Precio Unit.</th>
                    <th style="text-align: right;">Total</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td>{{ item.Nombre_Producto }}</td>
                    <td style="text-align: center;">{{ item.Cantidad }}</td>
                    <td style="text-align: right;">${{ "{:,.0f}".format(item.Precio) }}</td>
                    <td style="text-align: right;">${{ "{:,.0f}".format(item.Subtotal) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="totals-section">
            <div class="totals-table">
                <div class="total-row"><span>Subtotal:</span> <span>${{ "{:,.0f}".format(total) }}</span></div>
                <div class="total-row"><span>Descuento:</span> <span>$0</span></div>
                <div class="total-row grand-total">
                    <span>TOTAL:</span> 
                    <span>${{ "{:,.0f}".format(total) }}</span>
                </div>
            </div>
        </div>

        <div class="invoice-footer">
            <p class="thank-you">🐕 ¡Gracias por confiar en nosotros! 🐈</p>
            <p>Esta factura es válida como comprobante de pago.</p>
            <p>Guarda este recibo para cambios o garantías (5 días hábiles).</p>
        </div>
    </div>
</body>
</html>
"""

# --- 3. FUNCIONES DE CONEXIÓN Y UTILIDADES ---

@st.cache_resource(ttl=600)
def conectar_google_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account y SHEET_URL).")
            return None, None, None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        ws_inv = sh.worksheet("Inventario")
        ws_cli = sh.worksheet("Clientes")
        ws_ven = sh.worksheet("Ventas")
        ws_gas = sh.worksheet("Gastos")
        
        return ws_inv, ws_cli, ws_ven, ws_gas
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
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
        for col in ['Precio', 'Stock', 'Monto', 'Total', 'Cantidad']:
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

# --- 4. MOTORES DE GENERACIÓN (PDF Y EXCEL) ---

def generar_pdf_html(contexto):
    """Genera PDF usando WeasyPrint + Jinja2"""
    try:
        template = Template(HTML_TEMPLATE)
        html_content = template.render(contexto)
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except Exception as e:
        st.error(f"Error al generar PDF: {e}")
        return None

def generar_excel_profesional(df_ventas, df_gastos, f_inicio, f_fin):
    """Genera Excel con reporte financiero avanzado"""
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book

    # Estilos
    fmt_header = workbook.add_format({'bold': True, 'bg_color': COLOR_PRIMARIO, 'font_color': 'white', 'border': 1})
    fmt_money = workbook.add_format({'num_format': '$ #,##0', 'border': 1})
    fmt_base = workbook.add_format({'border': 1})

    # 1. Hoja Resumen
    ws_res = workbook.add_worksheet("Resumen Ejecutivo")
    ws_res.merge_range('A1:D1', f"Reporte Financiero: {f_inicio} al {f_fin}", fmt_header)
    
    total_v = df_ventas['Total'].sum()
    total_g = df_gastos['Monto'].sum()
    neto = total_v - total_g

    ws_res.write('A3', "Ingresos Totales", fmt_base)
    ws_res.write('B3', total_v, fmt_money)
    ws_res.write('A4', "Gastos Totales", fmt_base)
    ws_res.write('B4', total_g, fmt_money)
    ws_res.write('A5', "Utilidad Neta", fmt_header)
    ws_res.write('B5', neto, fmt_money)

    # 2. Hoja Ventas
    if not df_ventas.empty:
        df_ventas.to_excel(writer, sheet_name="Detalle Ventas", index=False, startrow=1, header=False)
        ws_v = writer.sheets["Detalle Ventas"]
        for col, val in enumerate(df_ventas.columns):
            ws_v.write(0, col, val, fmt_header)
        ws_v.set_column('A:Z', 18)

    # 3. Hoja Gastos
    if not df_gastos.empty:
        df_gastos.to_excel(writer, sheet_name="Detalle Gastos", index=False, startrow=1, header=False)
        ws_g = writer.sheets["Detalle Gastos"]
        for col, val in enumerate(df_gastos.columns):
            ws_g.write(0, col, val, fmt_header)
        ws_g.set_column('A:Z', 18)

    writer.close()
    output.seek(0)
    return output

# --- 5. PESTAÑAS Y MÓDULOS DE LA APLICACIÓN ---

def tab_punto_venta(ws_inv, ws_cli, ws_ven):
    st.markdown("### 🛒 Terminal de Venta (POS)")
    col_izq, col_der = st.columns([1.5, 1])

    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None

    with col_izq:
        # Selección Cliente
        with st.expander("👤 Selección de Cliente", expanded=not st.session_state.cliente_actual):
            col_b, col_btn = st.columns([3, 1])
            busqueda = col_b.text_input("Buscar Cédula", placeholder="Ingrese documento...")
            if col_btn.button("🔍 Buscar"):
                df_c = leer_datos(ws_cli)
                if not df_c.empty:
                    res = df_c[df_c['Cedula'].astype(str) == busqueda.strip()]
                    if not res.empty:
                        st.session_state.cliente_actual = res.iloc[0].to_dict()
                        st.success(f"Cliente: {st.session_state.cliente_actual.get('Nombre')}")
                    else:
                        st.warning("No encontrado.")
                else: st.warning("Base de datos vacía.")

        if st.session_state.cliente_actual:
            c = st.session_state.cliente_actual
            st.info(f"Cliente: **{c.get('Nombre')}** | Mascota: **{c.get('Mascota','-')}**")

        # Selección Productos
        st.markdown("#### Agregar Productos")
        df_inv = leer_datos(ws_inv)
        if not df_inv.empty:
            df_stock = df_inv[df_inv['Stock'] > 0]
            prod_lista = df_stock.apply(lambda x: f"{x['Nombre']} | ${x['Precio']:,.0f} | ID:{x['ID_Producto']}", axis=1).tolist()
            sel_prod = st.selectbox("Producto", [""] + prod_lista)
            col_c, col_a = st.columns([1, 2])
            cantidad = col_c.number_input("Cant", 1, 100, 1)
            
            if col_a.button("➕ Agregar al Carrito", type="primary"):
                if sel_prod:
                    id_p = sel_prod.split("ID:")[1]
                    info = df_inv[df_inv['ID_Producto'].astype(str) == id_p].iloc[0]
                    if cantidad <= info['Stock']:
                        item = {
                            "ID_Producto": info['ID_Producto'],
                            "Nombre_Producto": info['Nombre'],
                            "Precio": float(info['Precio']),
                            "Cantidad": int(cantidad),
                            "Subtotal": float(info['Precio'] * cantidad)
                        }
                        st.session_state.carrito.append(item)
                    else: st.error("Stock insuficiente")

    with col_der:
        st.markdown("### 🧾 Resumen")
        if st.session_state.ultimo_pdf:
            st.success("✅ Venta Exitosa")
            st.download_button("📄 Descargar PDF", st.session_state.ultimo_pdf, file_name=f"Venta_{st.session_state.ultima_venta_id}.pdf", mime="application/pdf", type="primary")
            if st.button("🔄 Nueva Venta"):
                st.session_state.carrito = []
                st.session_state.cliente_actual = None
                st.session_state.ultimo_pdf = None
                st.rerun()

        elif st.session_state.carrito:
            df_cart = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_cart[['Nombre_Producto', 'Cantidad', 'Subtotal']], hide_index=True, use_container_width=True)
            total = df_cart['Subtotal'].sum()
            st.metric("Total a Pagar", f"${total:,.0f}")
            
            with st.form("cobro"):
                entrega = st.radio("Entrega:", ["Punto de Venta", "Envío a Domicilio"], horizontal=True)
                dir_envio = st.text_input("Dirección", value=st.session_state.cliente_actual.get('Direccion', '') if st.session_state.cliente_actual else "") if entrega == "Envío a Domicilio" else "Local"
                metodo = st.selectbox("Pago", ["Efectivo", "Nequi", "DaviPlata", "Bancolombia", "Tarjeta"])
                
                if st.form_submit_button("✅ FACTURAR", type="primary", use_container_width=True):
                    if not st.session_state.cliente_actual:
                        st.error("Seleccione cliente")
                    else:
                        id_venta = datetime.now().strftime("%Y%m%d%H%M%S")
                        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        items_str = ", ".join([f"{i['Nombre_Producto']} (x{i['Cantidad']})" for i in st.session_state.carrito])
                        
                        # Guardar Venta
                        row = [id_venta, fecha, str(st.session_state.cliente_actual['Cedula']), 
                               st.session_state.cliente_actual['Nombre'], entrega, dir_envio, 
                               "Entregado" if entrega == "Punto de Venta" else "Pendiente", 
                               metodo, metodo if metodo != "Efectivo" else "Caja General", total, items_str]
                        
                        if escribir_fila(ws_ven, row):
                            actualizar_stock(ws_inv, st.session_state.carrito)
                            
                            # Generar PDF
                            ctx = {
                                "business_name": "Bigotes y Patitas",
                                "invoice_id": id_venta,
                                "date": datetime.now().strftime("%d/%m/%Y"),
                                "client_name": st.session_state.cliente_actual['Nombre'],
                                "client_id": st.session_state.cliente_actual['Cedula'],
                                "client_address": dir_envio,
                                "pet_name": st.session_state.cliente_actual.get('Mascota', ''),
                                "payment_method": metodo,
                                "delivery_status": entrega,
                                "items": st.session_state.carrito,
                                "total": total
                            }
                            st.session_state.ultimo_pdf = generar_pdf_html(ctx)
                            st.session_state.ultima_venta_id = id_venta
                            st.rerun()

def tab_clientes(ws_cli):
    st.markdown("### 👥 Gestión de Clientes")
    with st.container(border=True):
        st.markdown("#### Nuevo Cliente")
        with st.form("new_client"):
            c1, c2 = st.columns(2)
            cedula = c1.text_input("Cédula *")
            nombre = c1.text_input("Nombre *")
            tel = c1.text_input("Teléfono *")
            email = c1.text_input("Email")
            dir = c2.text_input("Dirección")
            mascota = c2.text_input("Mascota *")
            tipo = c2.selectbox("Tipo", ["Perro", "Gato", "Otro"])
            cumple = c2.date_input("Cumpleaños Mascota", value=None)
            
            if st.form_submit_button("Guardar"):
                if cedula and nombre and mascota:
                    row = [cedula, nombre, tel, email, dir, mascota, tipo, str(cumple), str(date.today())]
                    escribir_fila(ws_cli, row)
                    st.success("Guardado")
                else: st.warning("Faltan datos obligatorios")
    
    st.markdown("#### Base de Datos")
    st.dataframe(leer_datos(ws_cli), use_container_width=True)

def tab_envios(ws_ven):
    st.markdown("### 🚚 Control de Despachos")
    df = leer_datos(ws_ven)
    if not df.empty:
        pendientes = df[(df['Tipo_Entrega'] == 'Envío a Domicilio') & (df['Estado_Envio'] == 'Pendiente')]
        if pendientes.empty:
            st.success("🎉 Todo despachado")
        else:
            st.info(f"Pendientes: {len(pendientes)}")
            for idx, row in pendientes.iterrows():
                with st.expander(f"📦 {row['Nombre_Cliente']} - {row['Direccion_Envio']}"):
                    st.write(f"Items: {row['Items']}")
                    if st.button("Marcar Enviado", key=row['ID_Venta']):
                        cell = ws_ven.find(str(row['ID_Venta']))
                        ws_ven.update_cell(cell.row, 7, "Enviado")
                        st.rerun()

def tab_gastos(ws_gas):
    st.markdown("### 💸 Registro de Gastos")
    with st.form("gastos"):
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Clasificación", ["Fijo", "Variable", "Costo Venta"])
        cat = c1.selectbox("Categoría", ["Arriendo", "Servicios", "Nómina", "Proveedores", "Mantenimiento", "Publicidad"])
        desc = c1.text_input("Descripción")
        monto = c2.number_input("Monto", min_value=0.0)
        metodo = c2.selectbox("Medio Pago", ["Efectivo", "Transferencia"])
        origen = c2.selectbox("Origen Fondos", ["Caja General", "Bancolombia", "Nequi"])
        
        if st.form_submit_button("Registrar Gasto"):
            row = [datetime.now().strftime("%Y%m%d%H%M"), datetime.now().strftime("%Y-%m-%d"), tipo, cat, desc, monto, metodo, origen]
            escribir_fila(ws_gas, row)
            st.success("Registrado")

def tab_finanzas(ws_ven, ws_gas):
    st.markdown("### 📊 Centro de Control Financiero")
    st.info("Visualiza el rendimiento de tu negocio, controla la caja y exporta reportes.")

    col_ctrl, col_chart = st.columns([1, 3])

    with col_ctrl:
        with st.container(border=True):
            st.markdown("**📅 Filtros de Fecha**")
            hoy = date.today()
            f_inicio = st.date_input("Desde", hoy.replace(day=1))
            f_fin = st.date_input("Hasta", hoy)
            aplicar = st.button("Analizar Datos", use_container_width=True)

    if aplicar:
        df_v = leer_datos(ws_ven)
        df_g = leer_datos(ws_gas)

        # Filtros de fecha
        if not df_v.empty:
            df_v['Fecha_DT'] = pd.to_datetime(df_v['Fecha']).dt.date
            df_v = df_v[(df_v['Fecha_DT'] >= f_inicio) & (df_v['Fecha_DT'] <= f_fin)]
        
        if not df_g.empty:
            df_g['Fecha_DT'] = pd.to_datetime(df_g['Fecha']).dt.date
            df_g = df_g[(df_g['Fecha_DT'] >= f_inicio) & (df_g['Fecha_DT'] <= f_fin)]

        # KPIs
        total_ventas = df_v['Total'].sum() if not df_v.empty else 0
        total_gastos = df_g['Monto'].sum() if not df_g.empty else 0
        utilidad = total_ventas - total_gastos
        margen = (utilidad / total_ventas * 100) if total_ventas > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Ventas Totales", f"${total_ventas:,.0f}", delta="Ingresos")
        k2.metric("Gastos Totales", f"${total_gastos:,.0f}", delta="- Egresos", delta_color="inverse")
        k3.metric("Utilidad Neta", f"${utilidad:,.0f}", delta=f"{margen:.1f}% Margen")
        k4.metric("Transacciones", len(df_v))

        st.markdown("---")
        
        tabs = st.tabs(["📈 Gráficos", "💵 Flujo de Caja", "📥 Reportes"])

        with tabs[0]:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Métodos de Pago")
                if not df_v.empty:
                    fig = px.pie(df_v, values='Total', names='Metodo_Pago', hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.subheader("Ingresos vs Gastos Diarios")
                if not df_v.empty:
                    daily_v = df_v.groupby('Fecha_DT')['Total'].sum().reset_index()
                    daily_v['Tipo'] = 'Ingreso'
                    daily_v.rename(columns={'Total': 'Monto'}, inplace=True)
                else: daily_v = pd.DataFrame()

                if not df_g.empty:
                    daily_g = df_g.groupby('Fecha_DT')['Monto'].sum().reset_index()
                    daily_g['Tipo'] = 'Gasto'
                else: daily_g = pd.DataFrame()

                df_chart = pd.concat([daily_v, daily_g])
                if not df_chart.empty:
                    fig2 = px.bar(df_chart, x='Fecha_DT', y='Monto', color='Tipo', barmode='group',
                                  color_discrete_map={'Ingreso': COLOR_PRIMARIO, 'Gasto': '#ff6b6b'})
                    st.plotly_chart(fig2, use_container_width=True)

        with tabs[1]:
            st.subheader("Cuadre de Caja (Por Banco)")
            if not df_v.empty:
                bancos = df_v.groupby('Banco_Destino')['Total'].sum().reset_index()
                st.dataframe(bancos.style.format({'Total': '${:,.0f}'}), use_container_width=True)

        with tabs[2]:
            st.subheader("Descargar Información")
            excel_file = generar_excel_profesional(df_v, df_g, f_inicio, f_fin)
            st.download_button(
                label="📥 Descargar Reporte Financiero Completo (Excel)",
                data=excel_file,
                file_name=f"Reporte_Financiero_{f_inicio}_{f_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

# --- 6. MAIN ORCHESTRATOR ---

def main():
    ws_inv, ws_cli, ws_ven, ws_gas = conectar_google_sheets()
    if not ws_inv: return

    with st.sidebar:
        st.title("🐾 MENU")
        opcion = st.radio("Navegación", [
            "Punto de Venta", 
            "Gestión de Clientes", 
            "Despachos y Envíos",
            "Registro de Gastos", 
            "Centro Financiero"
        ])
        st.caption("v4.0 Pro | Bigotes y Patitas")

    if opcion == "Punto de Venta": tab_punto_venta(ws_inv, ws_cli, ws_ven)
    elif opcion == "Gestión de Clientes": tab_clientes(ws_cli)
    elif opcion == "Despachos y Envíos": tab_envios(ws_ven)
    elif opcion == "Registro de Gastos": tab_gastos(ws_gas)
    elif opcion == "Centro Financiero": tab_finanzas(ws_ven, ws_gas)

if __name__ == "__main__":
    main()
