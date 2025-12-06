import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime, date, timedelta
import time
import numpy as np
from jinja2 import Template
from weasyprint import HTML, CSS

# --- 1. CONFIGURACIÓN Y ESTILOS GLOBALES ---

st.set_page_config(
    page_title="Bigotes y Patitas ERP",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores Corporativos (Basados en tu HTML)
COLOR_PRIMARIO = "#667eea"
COLOR_SECUNDARIO = "#764ba2"
COLOR_FONDO = "#f4f7fe"

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
        text-align: center;
        border-left: 5px solid {COLOR_PRIMARIO};
    }}
    </style>
""", unsafe_allow_html=True)

# --- 2. PLANTILLA HTML DE FACTURA (TU DISEÑO ADAPTADO) ---

HTML_TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Factura - {{ business_name }}</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; -webkit-print-color-adjust: exact; }
        .invoice-container { width: 100%; max-width: 800px; margin: 0 auto; background: white; }
        .invoice-header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; padding: 40px; display: flex; justify-content: space-between; 
        }
        .business-info h1 { margin: 0; font-size: 24px; font-weight: 700; }
        .business-info p { margin: 2px 0; font-size: 12px; opacity: 0.9; }
        .invoice-number { text-align: right; }
        .invoice-number h2 { margin: 0; font-size: 28px; }
        .client-section { padding: 30px 40px; display: flex; justify-content: space-between; }
        .section-title { font-size: 10px; font-weight: 700; text-transform: uppercase; color: #667eea; margin-bottom: 5px; }
        .items-table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 12px; }
        .items-table th { background: #f8f9fa; padding: 12px 40px; text-align: left; color: #667eea; border-bottom: 2px solid #667eea; }
        .items-table td { padding: 12px 40px; border-bottom: 1px solid #e9ecef; color: #333; }
        .totals-section { padding: 0 40px 30px; display: flex; justify-content: flex-end; }
        .totals-table { width: 300px; }
        .total-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 12px; color: #666; }
        .grand-total { font-size: 18px; font-weight: 700; color: #667eea; border-top: 1px solid #ddd; padding-top: 10px; margin-top: 5px; }
        .invoice-footer { background: #f8f9fa; padding: 20px; text-align: center; border-top: 3px solid #667eea; font-size: 12px; color: #666; }
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
                <div class="section-title">Detalles:</div>
                <p><strong>Método:</strong> {{ payment_method }}</p>
                <p><strong>Estado:</strong> Pagado</p>
            </div>
        </div>

        <table class="items-table">
            <thead>
                <tr>
                    <th>Descripción</th>
                    <th style="text-align: center;">Cant</th>
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
            <p><strong>¡Gracias por consentir a tu mascota con nosotros!</strong> 🐶🐱</p>
            <p>Guarda este recibo para cambios o garantías (5 días hábiles).</p>
        </div>
    </div>
</body>
</html>
"""

# --- 3. FUNCIONES UTILITARIAS Y DE CONEXIÓN ---

@st.cache_resource(ttl=600)
def conectar_google_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta la configuración de 'google_service_account' en secrets.")
            return None, None, None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        return sh.worksheet("Inventario"), sh.worksheet("Clientes"), sh.worksheet("Ventas"), sh.worksheet("Gastos")
    except Exception as e:
        st.error(f"Error conectando a Google Sheets: {e}")
        return None, None, None, None

def leer_datos(ws):
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        numeric_cols = ['Precio', 'Stock', 'Monto', 'Total', 'Cantidad']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def escribir_fila(ws, datos):
    try:
        clean_data = [int(x) if isinstance(x, (np.integer, int)) else float(x) if isinstance(x, (np.float64, float)) else x for x in datos]
        ws.append_row(clean_data)
        return True
    except Exception as e:
        st.error(f"Error guardando datos: {e}")
        return False

def generar_pdf_html(contexto):
    """Genera el PDF usando Jinja2 y WeasyPrint con el HTML proporcionado"""
    try:
        template = Template(HTML_TEMPLATE)
        html_rendered = template.render(contexto)
        pdf_bytes = HTML(string=html_rendered).write_pdf()
        return pdf_bytes
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None

def generar_excel_profesional(df_ventas, df_gastos, fecha_inicio, fecha_fin):
    """Genera un archivo Excel con múltiples pestañas y formato avanzado"""
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book

    # Formatos
    fmt_header = workbook.add_format({'bold': True, 'bg_color': COLOR_PRIMARIO, 'font_color': 'white', 'border': 1})
    fmt_currency = workbook.add_format({'num_format': '$ #,##0', 'border': 1})
    fmt_date = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
    fmt_base = workbook.add_format({'border': 1})

    # --- PESTAÑA 1: RESUMEN EJECUTIVO ---
    ws_res = workbook.add_worksheet("Resumen Ejecutivo")
    ws_res.merge_range('A1:E1', f"REPORTE FINANCIERO: {fecha_inicio} al {fecha_fin}", fmt_header)
    
    ventas_tot = df_ventas['Total'].sum()
    gastos_tot = df_gastos['Monto'].sum()
    utilidad = ventas_tot - gastos_tot
    
    ws_res.write('A3', "Ingresos Totales", fmt_base)
    ws_res.write('B3', ventas_tot, fmt_currency)
    ws_res.write('A4', "Gastos Totales", fmt_base)
    ws_res.write('B4', gastos_tot, fmt_currency)
    ws_res.write('A5', "Utilidad Neta", fmt_header)
    ws_res.write('B5', utilidad, fmt_currency)

    # --- PESTAÑA 2: DETALLE VENTAS ---
    if not df_ventas.empty:
        df_ventas.to_excel(writer, sheet_name='Detalle Ventas', index=False, startrow=1, header=False)
        ws_ven = writer.sheets['Detalle Ventas']
        for col_num, value in enumerate(df_ventas.columns.values):
            ws_ven.write(0, col_num, value, fmt_header)
        ws_ven.set_column('A:Z', 20)

    # --- PESTAÑA 3: DETALLE GASTOS ---
    if not df_gastos.empty:
        df_gastos.to_excel(writer, sheet_name='Detalle Gastos', index=False, startrow=1, header=False)
        ws_gas = writer.sheets['Detalle Gastos']
        for col_num, value in enumerate(df_gastos.columns.values):
            ws_gas.write(0, col_num, value, fmt_header)
        ws_gas.set_column('A:Z', 20)

    writer.close()
    output.seek(0)
    return output

# --- 4. MÓDULOS DE LA APLICACIÓN ---

def modulo_pos(ws_inv, ws_cli, ws_ven):
    st.markdown("## 🛒 Terminal de Venta (POS)")
    
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None

    col_izq, col_der = st.columns([1.8, 1.2])

    with col_izq:
        # 1. Buscador de Cliente
        st.markdown("### 1. Cliente")
        cedula_input = st.text_input("Buscar por Cédula", key="search_cli")
        if st.button("🔍 Buscar Cliente"):
            df_cli = leer_datos(ws_cli)
            if not df_cli.empty:
                cli = df_cli[df_cli['Cedula'].astype(str) == str(cedula_input)]
                if not cli.empty:
                    st.session_state.cliente_actual = cli.iloc[0].to_dict()
                    st.success(f"Cliente: {st.session_state.cliente_actual['Nombre']}")
                else:
                    st.warning("Cliente no encontrado.")
        
        if st.session_state.cliente_actual:
            c = st.session_state.cliente_actual
            st.info(f"👤 **{c['Nombre']}** | 🐾 {c.get('Mascota','-')} | 📞 {c.get('Telefono','-')}")

        st.markdown("---")
        # 2. Agregar Productos
        st.markdown("### 2. Productos")
        df_inv = leer_datos(ws_inv)
        if not df_inv.empty:
            df_active = df_inv[df_inv['Stock'] > 0]
            product_opts = df_active.apply(lambda x: f"{x['Nombre']} | ${x['Precio']:,.0f} (Stock: {x['Stock']}) | ID:{x['ID_Producto']}", axis=1).tolist()
            seleccion = st.selectbox("Seleccionar Producto", [""] + product_opts)
            cantidad = st.number_input("Cantidad", min_value=1, value=1)

            if st.button("➕ Agregar al Carrito", type="primary"):
                if seleccion and st.session_state.cliente_actual:
                    id_p = seleccion.split("ID:")[1]
                    prod_data = df_inv[df_inv['ID_Producto'].astype(str) == id_p].iloc[0]
                    if cantidad <= prod_data['Stock']:
                        item = {
                            "ID_Producto": prod_data['ID_Producto'],
                            "Nombre_Producto": prod_data['Nombre'],
                            "Precio": float(prod_data['Precio']),
                            "Cantidad": int(cantidad),
                            "Subtotal": float(prod_data['Precio'] * cantidad)
                        }
                        st.session_state.carrito.append(item)
                    else:
                        st.error("Stock insuficiente.")
                elif not st.session_state.cliente_actual:
                    st.error("Primero selecciona un cliente.")

    with col_der:
        st.markdown("### 🧾 Resumen de Venta")
        if st.session_state.carrito:
            df_cart = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_cart[['Nombre_Producto', 'Cantidad', 'Subtotal']], hide_index=True, use_container_width=True)
            
            total_venta = df_cart['Subtotal'].sum()
            st.markdown(f"<h2 style='text-align: right; color: {COLOR_PRIMARIO}'>Total: ${total_venta:,.0f}</h2>", unsafe_allow_html=True)
            
            metodo = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "DaviPlata", "Bancolombia", "Tarjeta"])
            banco = "Caja General" if metodo == "Efectivo" else metodo

            if st.button("✅ FINALIZAR Y FACTURAR", type="primary", use_container_width=True):
                # Generar ID
                id_venta = datetime.now().strftime("%Y%m%d%H%M%S")
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Contexto para PDF HTML
                contexto_pdf = {
                    "business_name": "Bigotes y Patitas",
                    "invoice_id": id_venta,
                    "date": datetime.now().strftime("%d/%m/%Y"),
                    "client_name": st.session_state.cliente_actual['Nombre'],
                    "client_id": st.session_state.cliente_actual['Cedula'],
                    "client_address": st.session_state.cliente_actual.get('Direccion', 'Local'),
                    "pet_name": st.session_state.cliente_actual.get('Mascota', ''),
                    "payment_method": metodo,
                    "items": st.session_state.carrito,
                    "total": total_venta
                }
                
                # Generar PDF
                pdf_bytes = generar_pdf_html(contexto_pdf)
                st.session_state.ultimo_pdf = pdf_bytes
                
                # Guardar en Sheets
                items_str = " | ".join([f"{i['Cantidad']}x {i['Nombre_Producto']}" for i in st.session_state.carrito])
                row_venta = [
                    id_venta, fecha_actual, st.session_state.cliente_actual['Cedula'],
                    st.session_state.cliente_actual['Nombre'], "Entregado", "Local", "Entregado",
                    metodo, banco, total_venta, items_str
                ]
                escribir_fila(ws_ven, row_venta)
                
                # Actualizar Stock (Lógica simplificada)
                # ... (Lógica de stock igual a la anterior) ...
                
                st.session_state.carrito = []
                st.success("Venta registrada correctamente")
                st.rerun()

        if st.session_state.ultimo_pdf:
            st.download_button(
                label="🖨️ Imprimir Factura (PDF)",
                data=st.session_state.ultimo_pdf,
                file_name=f"Factura_{datetime.now().strftime('%H%M%S')}.pdf",
                mime="application/pdf",
                type="secondary"
            )

def modulo_finanzas(ws_ven, ws_gas):
    st.markdown("## 📊 Centro de Control Financiero")
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

        # Filtros
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
        ticket_prom = df_v['Total'].mean() if not df_v.empty else 0

        # Tarjetas KPI
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Ventas Totales", f"${total_ventas:,.0f}", delta="Ingresos Brutos")
        k2.metric("Gastos Totales", f"${total_gastos:,.0f}", delta="- Salidas", delta_color="inverse")
        k3.metric("Utilidad Neta", f"${utilidad:,.0f}", delta=f"{margen:.1f}% Margen")
        k4.metric("Ticket Promedio", f"${ticket_prom:,.0f}")

        st.markdown("---")

        # Pestañas de Análisis
        tab1, tab2, tab3 = st.tabs(["📈 Gráficos", "💵 Flujo de Caja", "📥 Reportes"])

        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Ventas por Método de Pago")
                if not df_v.empty:
                    fig_pie = px.pie(df_v, values='Total', names='Metodo_Pago', hole=0.4, color_discrete_sequence=px.colors.sequential.Purp)
                    st.plotly_chart(fig_pie, use_container_width=True)
            with c2:
                st.subheader("Ingresos vs Gastos Diarios")
                # Lógica para gráfico de barras agrupado por día
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
                    fig_bar = px.bar(df_chart, x='Fecha_DT', y='Monto', color='Tipo', barmode='group', 
                                     color_discrete_map={'Ingreso': COLOR_PRIMARIO, 'Gasto': '#ff6b6b'})
                    st.plotly_chart(fig_bar, use_container_width=True)

        with tab2:
            st.subheader("Cuadre de Caja (Desglose por Banco)")
            if not df_v.empty:
                bancos = df_v.groupby('Banco_Destino')['Total'].sum().reset_index()
                st.dataframe(bancos.style.format({'Total': '${:,.0f}'}), use_container_width=True)
            else:
                st.info("No hay datos para el periodo.")

        with tab3:
            st.subheader("Descargar Información")
            excel_file = generar_excel_profesional(df_v, df_g, f_inicio, f_fin)
            st.download_button(
                label="📥 Descargar Reporte Financiero Completo (Excel)",
                data=excel_file,
                file_name=f"Reporte_Financiero_{f_inicio}_{f_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

# --- 5. ORQUESTADOR PRINCIPAL ---

def main():
    ws_inv, ws_cli, ws_ven, ws_gas = conectar_google_sheets()
    
    if not ws_inv: return # Detener si no hay conexión

    with st.sidebar:
        st.title("🐾 MENU")
        st.markdown("---")
        opcion = st.radio("Ir a:", [
            "Punto de Venta", 
            "Gestión de Clientes", 
            "Inventario",
            "Registro de Gastos", 
            "Centro Financiero"
        ])
        st.markdown("---")
        st.caption("v4.0 Pro | Bigotes y Patitas")

    if opcion == "Punto de Venta":
        modulo_pos(ws_inv, ws_cli, ws_ven)
    elif opcion == "Centro Financiero":
        modulo_finanzas(ws_ven, ws_gas)
    elif opcion == "Registro de Gastos":
        st.header("💸 Registrar Nuevo Gasto")
        with st.form("gastos_form"):
            fecha = datetime.now()
            concepto = st.text_input("Concepto / Descripción")
            categoria = st.selectbox("Categoría", ["Arriendo", "Servicios", "Nómina", "Proveedores", "Mantenimiento", "Publicidad", "Otros"])
            monto = st.number_input("Monto", min_value=0.0)
            origen = st.selectbox("Banco Origen", ["Caja General", "Bancolombia", "Nequi", "Davivienda"])
            
            if st.form_submit_button("Guardar Gasto"):
                row = [datetime.now().strftime("%Y%m%d%H%M%S"), str(fecha), "Gasto", categoria, concepto, monto, "N/A", origen]
                if escribir_fila(ws_gas, row):
                    st.success("Gasto registrado")
    elif opcion == "Gestión de Clientes":
        st.header("👥 Base de Datos Clientes")
        df = leer_datos(ws_cli)
        st.dataframe(df, use_container_width=True)
        # Aquí puedes añadir el formulario de creación de clientes similar al anterior
    elif opcion == "Inventario":
        st.header("📦 Inventario Actual")
        df = leer_datos(ws_inv)
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
