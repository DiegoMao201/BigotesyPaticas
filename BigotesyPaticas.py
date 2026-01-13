import streamlit as st
import pandas as pd
import gspread
from io import BytesIO
from datetime import datetime, date, timedelta
import time
import numpy as np
import jinja2
from weasyprint import HTML
import urllib.parse
import json

# --- 1. CONFIGURACIÓN Y ESTILOS (NEXUS PRO THEME) ---

COLOR_PRIMARIO = "#187f77"
COLOR_SECUNDARIO = "#125e58"
COLOR_ACENTO = "#f5a641"
COLOR_FONDO = "#f8f9fa"
COLOR_TEXTO = "#262730"
COLOR_BLANCO = "#ffffff"
COLOR_WHATSAPP = "#25D366"

def configurar_pagina():
    st.set_page_config(
        page_title="Nexus Pro | Bigotes y Patitas",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        .stApp {{ background-color: {COLOR_FONDO}; font-family: 'Inter', sans-serif; }}
        h1, h2, h3 {{ color: {COLOR_PRIMARIO}; font-weight: 700; }}
        h4, h5, h6 {{ color: {COLOR_TEXTO}; font-weight: 600; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 8px; background-color: transparent; }}
        .stTabs [data-baseweb="tab"] {{
            height: 45px; white-space: pre-wrap; background-color: {COLOR_BLANCO};
            border-radius: 8px 8px 0 0; color: {COLOR_TEXTO}; font-weight: 600;
            border: 1px solid #eee; border-bottom: none;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {COLOR_PRIMARIO}; color: white; border-color: {COLOR_PRIMARIO};
        }}
        .whatsapp-btn {{
            display: inline-block; background-color: {COLOR_WHATSAPP}; color: white !important;
            padding: 12px 20px; border-radius: 8px; text-decoration: none; font-weight: bold;
            text-align: center; border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: background-color 0.3s; width: 100%; margin-top: 10px; margin-bottom: 20px;
        }}
        .whatsapp-btn:hover {{ background-color: #1ebc57; text-decoration: none; }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y UTILIDADES ---

@st.cache_resource(ttl=600)
def conectar_google_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account y SHEET_URL).")
            return None, None, None, None, None, None
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        ws_inv = sh.worksheet("Inventario")
        ws_cli = sh.worksheet("Clientes")
        ws_ven = sh.worksheet("Ventas")
        ws_gas = sh.worksheet("Gastos")
        try: ws_cap = sh.worksheet("Capital")
        except: ws_cap = None
        try:
            ws_cie = sh.worksheet("Cierres")
            if not ws_cie.get_all_values():
                ws_cie.append_row(["Fecha", "Hora", "Base_Inicial", "Ventas_Efectivo", "Gastos_Efectivo", "Consignaciones", "Saldo_Teorico", "Saldo_Real", "Diferencia", "Notas"])
        except:
            ws_cie = None
        return ws_inv, ws_cli, ws_ven, ws_gas, ws_cap, ws_cie
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None, None, None, None, None, None

def leer_datos(ws):
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        for col in ['Precio', 'Stock', 'Monto', 'Total', 'Costo', 'Costo_Total', 'Base_Inicial', 'Ventas_Efectivo', 'Gastos_Efectivo', 'Consignaciones', 'Saldo_Teorico', 'Saldo_Real', 'Diferencia']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        return df
    except: return pd.DataFrame()

def actualizar_estado_envio(ws_ven, id_venta, nuevo_estado):
    try:
        cell = ws_ven.find(str(id_venta))
        if cell:
            headers = ws_ven.row_values(1)
            try: col_index = headers.index("Estado_Envio") + 1
            except ValueError: col_index = 7
            ws_ven.update_cell(cell.row, col_index, nuevo_estado)
            return True
        else:
            st.error(f"No se encontró la venta ID: {id_venta}")
            return False
    except Exception as e:
        st.error(f"Error actualizando estado del envío: {e}")
        return False

def generar_mensaje_whatsapp(nombre_cliente, mascota, tipo_cliente, items_str, total):
    saludo = ""
    cuerpo = ""
    despedida = "¡Muchas gracias y feliz día! 🐾"
    if tipo_cliente == "NUEVO":
        saludo = f"¡Hola {nombre_cliente}! 👋 Bienvenido/a a la familia *Bigotes y Patitas*."
        cuerpo = f"Nos emociona mucho que nos hayas elegido para consentir a *{mascota}*. 🥰"
    elif tipo_cliente == "REACTIVADO":
        saludo = f"¡Hola {nombre_cliente}! 👋 ¡Qué alegría inmensa tenerte de vuelta!"
        cuerpo = f"Te habíamos extrañado a ti y a *{mascota}* ❤️."
    else:
        saludo = f"¡Hola de nuevo {nombre_cliente}! 👋"
        cuerpo = f"Qué gusto verte otra vez. 🌟"
    resumen = f"\n\n🧾 *Resumen de tu compra:*\n{items_str}\n\n💰 *Total:* ${total:,.0f}"
    mensaje_completo = f"{saludo}\n{cuerpo}{resumen}\n\n{despedida}"
    return urllib.parse.quote(mensaje_completo)

def generar_pdf_html(venta_data, items):
    try:
        with open("factura.html", "r", encoding="utf-8") as f:
            template_str = f.read()
        context = {
            "id_venta": venta_data['ID'],
            "fecha": venta_data['Fecha'],
            "cliente_nombre": venta_data.get('Cliente', 'Consumidor Final'),
            "cliente_cedula": venta_data.get('Cedula_Cliente', '---'),
            "cliente_direccion": venta_data.get('Direccion', 'Local'),
            "cliente_mascota": venta_data.get('Mascota', '---'),
            "metodo_pago": venta_data.get('Metodo_Pago', 'Efectivo'),
            "tipo_entrega": venta_data.get('Tipo_Entrega', 'Local'),
            "estado": "Pendiente" if venta_data.get('Tipo_Entrega') == "Envío a Domicilio" else "Entregado",
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

# --- 3. PESTAÑAS DE LA APP ---

def tab_pos(ws_inv, ws_cli, ws_ven):
    st.header("🛒 Punto de Venta (POS)")
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'mascota_seleccionada' not in st.session_state: st.session_state.mascota_seleccionada = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None
    if 'whatsapp_link' not in st.session_state: st.session_state.whatsapp_link = None

    col_izq, col_der = st.columns([1.6, 1])
    with col_izq:
        st.markdown("#### 👤 Buscar Cliente")
        df_c = leer_datos(ws_cli)
        if not df_c.empty:
            search = st.text_input("Buscar por nombre, cédula, mascota o teléfono", key="busca_cli_pos")
            mask = (
                df_c['Nombre'].str.contains(search, case=False, na=False) |
                df_c['Cedula'].astype(str).str.contains(search, case=False, na=False) |
                df_c['Mascota'].str.contains(search, case=False, na=False) |
                df_c['Telefono'].astype(str).str.contains(search, case=False, na=False)
            ) if search else [True]*len(df_c)
            resultados = df_c[mask]
            st.dataframe(resultados[['Cedula', 'Nombre', 'Mascota', 'Telefono']], use_container_width=True, hide_index=True)
            selected_idx = st.selectbox("Selecciona un cliente", resultados.index, format_func=lambda i: f"{resultados.loc[i, 'Nombre']} ({resultados.loc[i, 'Cedula']})")
            if st.button("Cargar Cliente"):
                cliente_data = resultados.loc[selected_idx].to_dict()
                mascotas_para_dropdown = []
                json_raw = cliente_data.get('Info_Mascotas', '')
                try:
                    if json_raw and str(json_raw).strip():
                        parsed_list = json.loads(str(json_raw))
                        if isinstance(parsed_list, list):
                            mascotas_para_dropdown = [m.get('Nombre') for m in parsed_list if m.get('Nombre')]
                except:
                    pass
                if not mascotas_para_dropdown:
                    nombre_old = cliente_data.get('Mascota', '')
                    if nombre_old:
                        mascotas_para_dropdown = [nombre_old]
                if not mascotas_para_dropdown:
                    mascotas_para_dropdown = ["Varios"]
                cliente_data['Lista_Nombres_Mascotas'] = mascotas_para_dropdown
                st.session_state.cliente_actual = cliente_data
                st.session_state.mascota_seleccionada = mascotas_para_dropdown[0] if mascotas_para_dropdown else None
                st.toast(f"Cliente cargado: {st.session_state.cliente_actual.get('Nombre')}", icon="✅")
                st.rerun()
        st.markdown("#### 🛒 Agregar Productos")
        df_inv = leer_datos(ws_inv)
        if not df_inv.empty:
            productos = df_inv['Nombre'].tolist()
            producto_sel = st.selectbox("Producto", productos)
            cantidad = st.number_input("Cantidad", min_value=1, value=1)
            if st.button("Agregar al Carrito"):
                prod_row = df_inv[df_inv['Nombre'] == producto_sel].iloc[0]
                st.session_state.carrito.append({
                    "ID_Producto": prod_row['ID_Producto'],
                    "Nombre_Producto": prod_row['Nombre'],
                    "Cantidad": cantidad,
                    "Precio": prod_row['Precio'],
                    "Subtotal": cantidad * prod_row['Precio']
                })
                st.success(f"{cantidad} x {producto_sel} agregado al carrito.")
        if st.session_state.carrito:
            st.markdown("#### 🧺 Carrito de Compra")
            df_carrito = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_carrito[['Nombre_Producto', 'Cantidad', 'Precio', 'Subtotal']], use_container_width=True, hide_index=True)
            total = df_carrito['Subtotal'].sum()
            st.markdown(f"### Total: ${total:,.0f}")
            if st.button("Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
    with col_der:
        st.markdown("#### 💳 Facturación")
        if st.session_state.carrito and st.session_state.cliente_actual:
            metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "Daviplata", "Tarjeta", "Transferencia"])
            tipo_entrega = st.selectbox("Tipo de Entrega", ["Local", "Envío a Domicilio"])
            direccion = st.text_input("Dirección de Entrega", value=st.session_state.cliente_actual.get('Direccion', ''))
            if st.button("Facturar y Guardar Venta", type="primary"):
                id_venta = f"VEN-{int(time.time())}"
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                items_str = ", ".join([f"{x['Cantidad']}x{x['Nombre_Producto']}" for x in st.session_state.carrito])
                total = sum([x['Subtotal'] for x in st.session_state.carrito])
                ws_ven.append_row([
                    id_venta, fecha,
                    st.session_state.cliente_actual.get('Cedula', ''),
                    st.session_state.cliente_actual.get('Nombre', ''),
                    tipo_entrega, direccion, "Pendiente",
                    metodo_pago, "", total, items_str
                ])
                # Actualizar stock
                # (puedes agregar tu función de stock aquí)
                venta_data = {
                    'ID': id_venta,
                    'Fecha': fecha,
                    'Cliente': st.session_state.cliente_actual.get('Nombre', ''),
                    'Cedula_Cliente': st.session_state.cliente_actual.get('Cedula', ''),
                    'Direccion': direccion,
                    'Mascota': st.session_state.mascota_seleccionada,
                    'Metodo_Pago': metodo_pago,
                    'Tipo_Entrega': tipo_entrega,
                    'Total': total
                }
                pdf_bytes = generar_pdf_html(venta_data, st.session_state.carrito)
                st.session_state.ultimo_pdf = pdf_bytes
                st.session_state.ultima_venta_id = id_venta
                mensaje = generar_mensaje_whatsapp(
                    venta_data['Cliente'],
                    venta_data['Mascota'],
                    "NUEVO",
                    items_str,
                    total
                )
                telefono = st.session_state.cliente_actual.get('Telefono', '')
                if telefono and len(telefono) >= 7:
                    if not telefono.startswith('57') and len(telefono) == 10:
                        telefono = '57' + telefono
                    link_wa = f"https://wa.me/{telefono}?text={mensaje}"
                    st.session_state.whatsapp_link = link_wa
                st.success("¡Venta registrada y factura generada!")
                st.session_state.carrito = []
        if st.session_state.ultimo_pdf:
            st.download_button(
                label="⬇️ Descargar Factura PDF",
                data=st.session_state.ultimo_pdf,
                file_name=f"Factura_{st.session_state.ultima_venta_id}.pdf",
                mime="application/pdf"
            )
        if st.session_state.whatsapp_link:
            st.markdown(f"""<a href="{st.session_state.whatsapp_link}" target="_blank" class="whatsapp-btn">📲 Enviar Resumen por WhatsApp</a>""", unsafe_allow_html=True)

def tab_clientes(ws_cli, ws_ven):
    st.header("👤 Gestión de Clientes")
    df_c = leer_datos(ws_cli)
    search = st.text_input("Buscar cliente por nombre, cédula, mascota o teléfono", key="busca_cli")
    mask = (
        df_c['Nombre'].str.contains(search, case=False, na=False) |
        df_c['Cedula'].astype(str).str.contains(search, case=False, na=False) |
        df_c['Mascota'].str.contains(search, case=False, na=False) |
        df_c['Telefono'].astype(str).str.contains(search, case=False, na=False)
    ) if search else [True]*len(df_c)
    resultados = df_c[mask]
    st.dataframe(resultados[['Cedula', 'Nombre', 'Mascota', 'Telefono']], use_container_width=True, hide_index=True)
    st.markdown("---")
    st.subheader("Historial de Ventas del Cliente")
    selected_idx = st.selectbox("Selecciona un cliente para ver historial", resultados.index, format_func=lambda i: f"{resultados.loc[i, 'Nombre']} ({resultados.loc[i, 'Cedula']})", key="cli_hist")
    df_v = leer_datos(ws_ven)
    if not df_v.empty:
        df_v['Cedula_Cliente'] = df_v['Cedula_Cliente'].astype(str)
        historial = df_v[df_v['Cedula_Cliente'] == resultados.loc[selected_idx, 'Cedula']]
        if not historial.empty:
            st.dataframe(historial[['Fecha', 'Total', 'Items', 'Metodo_Pago', 'Tipo_Entrega']], use_container_width=True, hide_index=True)
        else:
            st.info("No hay ventas registradas para este cliente.")
    telefono = resultados.loc[selected_idx, 'Telefono']
    nombre = resultados.loc[selected_idx, 'Nombre']
    if st.button("Enviar WhatsApp de Bienvenida"):
        mensaje = f"¡Hola {nombre}! 👋 Bienvenido/a a la familia Bigotes y Patitas. Nos alegra mucho tenerte con nosotros. 🐾"
        if telefono and len(str(telefono)) >= 7:
            tel = str(telefono)
            if not tel.startswith('57') and len(tel) == 10:
                tel = '57' + tel
            link_wa = f"https://wa.me/{tel}?text={urllib.parse.quote(mensaje)}"
            st.markdown(f"""<a href="{link_wa}" target="_blank" class="whatsapp-btn">📲 Enviar WhatsApp de Bienvenida</a>""", unsafe_allow_html=True)

def tab_despachos(ws_ven):
    st.header("🚚 Pedidos Pendientes")
    df_v = leer_datos(ws_ven)
    pendientes = df_v[df_v['Estado_Envio'].isin(["Pendiente", "En camino"])]
    if pendientes.empty:
        st.success("No hay pedidos pendientes de entrega.")
    else:
        st.dataframe(pendientes[['ID_Venta', 'Fecha', 'Nombre_Cliente', 'Direccion_Envio', 'Metodo_Pago', 'Total', 'Estado_Envio']], use_container_width=True)
        selected = st.selectbox("Selecciona un pedido para marcar como entregado", pendientes['ID_Venta'])
        if st.button("Marcar como Entregado"):
            actualizar_estado_envio(ws_ven, selected, "Entregado")
            st.success("Pedido marcado como entregado.")
            st.rerun()

def tab_gastos(ws_gas):
    st.header("💳 Registrar y Buscar Gastos")
    with st.form("form_gasto"):
        tipo = st.selectbox("Tipo de Gasto", ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"])
        categoria = st.text_input("Categoría", "General")
        descripcion = st.text_area("Descripción")
        monto = st.number_input("Monto", min_value=0.0)
        responsable = st.text_input("Responsable", "Admin")
        banco = st.text_input("Banco/Origen", "")
        if st.form_submit_button("Registrar Gasto"):
            ws_gas.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                datetime.now().strftime("%Y-%m-%d"),
                tipo,
                categoria,
                descripcion,
                monto,
                responsable,
                banco
            ])
            st.success("Gasto registrado correctamente.")
            st.rerun()
    st.subheader("Buscar Gastos")
    df_g = leer_datos(ws_gas)
    search = st.text_input("Buscar por descripción, responsable, banco, categoría", key="busca_gasto")
    mask = (
        df_g['Descripcion'].str.contains(search, case=False, na=False) |
        df_g['Responsable'].str.contains(search, case=False, na=False) |
        df_g['Banco'].str.contains(search, case=False, na=False) |
        df_g['Categoria'].str.contains(search, case=False, na=False)
    ) if search else [True]*len(df_g)
    resultados = df_g[mask]
    st.dataframe(resultados, use_container_width=True)

def tab_cuadre(ws_ven, ws_gas, ws_cie):
    st.header("💵 Cuadre de Caja Diario (Avanzado)")
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)
    df_cie = leer_datos(ws_cie)
    hoy = datetime.now().date()
    ventas_hoy = df_v[df_v['Fecha'].dt.date == hoy] if not df_v.empty else pd.DataFrame()
    gastos_hoy = df_g[df_g['Fecha'] == hoy.strftime("%Y-%m-%d")] if not df_g.empty else pd.DataFrame()
    base_inicial = st.number_input("Base Inicial (Efectivo en caja al abrir)", min_value=0.0, value=float(df_cie['Saldo_Real'].iloc[-1]) if not df_cie.empty else 0.0)
    ventas_efectivo = ventas_hoy[ventas_hoy['Metodo_Pago'] == "Efectivo"]['Total'].sum()
    ventas_electronico = ventas_hoy[ventas_hoy['Metodo_Pago'].isin(["Nequi", "Daviplata", "Transferencia", "Tarjeta"])]["Total"].sum()
    gastos_efectivo = gastos_hoy[gastos_hoy['Tipo'] == "Efectivo"]['Monto'].sum()
    consignaciones = st.number_input("Consignaciones del día (a bancos)", min_value=0.0, value=0.0)
    saldo_teorico = base_inicial + ventas_efectivo - gastos_efectivo - consignaciones
    saldo_real = st.number_input("Saldo Real contado en caja", min_value=0.0, value=saldo_teorico)
    diferencia = saldo_real - saldo_teorico
    notas = st.text_area("Notas del cuadre", "")
    st.metric("Ventas Efectivo", f"${ventas_efectivo:,.0f}")
    st.metric("Ventas Electrónico", f"${ventas_electronico:,.0f}")
    st.metric("Gastos Efectivo", f"${gastos_efectivo:,.0f}")
    st.metric("Saldo Teórico", f"${saldo_teorico:,.0f}")
    st.metric("Saldo Real", f"${saldo_real:,.0f}")
    st.metric("Diferencia", f"${diferencia:,.0f}")
    if st.button("Guardar Cuadre en Google Sheets"):
        ws_cie.append_row([
            hoy.strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            base_inicial,
            ventas_efectivo,
            gastos_efectivo,
            consignaciones,
            saldo_teorico,
            saldo_real,
            diferencia,
            notas
        ])
        st.success("Cuadre guardado en Google Sheets.")

def tab_resumen(ws_ven, ws_gas, ws_cie):
    st.header("📊 Resumen y Búsquedas")
    st.subheader("Buscar Ventas")
    df_v = leer_datos(ws_ven)
    search_v = st.text_input("Buscar ventas por cliente, producto, método de pago", key="busca_ven")
    mask = (
        df_v['Nombre_Cliente'].str.contains(search_v, case=False, na=False) |
        df_v['Items'].str.contains(search_v, case=False, na=False) |
        df_v['Metodo_Pago'].str.contains(search_v, case=False, na=False)
    ) if search_v else [True]*len(df_v)
    resultados = df_v[mask]
    st.dataframe(resultados, use_container_width=True)
    st.subheader("Buscar Cuadres de Caja")
    df_c = leer_datos(ws_cie)
    search_c = st.text_input("Buscar cuadre por fecha o notas", key="busca_cie")
    mask = (
        df_c['Fecha'].astype(str).str.contains(search_c, case=False, na=False) |
        df_c['Notas'].str.contains(search_c, case=False, na=False)
    ) if search_c else [True]*len(df_c)
    resultados = df_c[mask]
    st.dataframe(resultados, use_container_width=True)

# --- 4. MAIN APP ---

def main():
    configurar_pagina()
    ws_inv, ws_cli, ws_ven, ws_gas, ws_cap, ws_cie = conectar_google_sheets()
    st.title("🐾 Nexus Pro | Bigotes y Patitas")
    tabs = st.tabs([
        "🛒 POS",
        "👤 Clientes",
        "🚚 Despachos",
        "💳 Gastos",
        "💵 Cuadre de Caja",
        "📊 Resumen"
    ])
    with tabs[0]:
        tab_pos(ws_inv, ws_cli, ws_ven)
    with tabs[1]:
        tab_clientes(ws_cli, ws_ven)
    with tabs[2]:
        tab_despachos(ws_ven)
    with tabs[3]:
        tab_gastos(ws_gas)
    with tabs[4]:
        tab_cuadre(ws_ven, ws_gas, ws_cie)
    with tabs[5]:
        tab_resumen(ws_ven, ws_gas, ws_cie)

if __name__ == "__main__":
    main()
