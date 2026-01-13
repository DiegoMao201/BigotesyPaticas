import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
import json
import urllib.parse
import jinja2
from weasyprint import HTML
from io import BytesIO
import io

# --- CONFIGURACIÓN Y CONEXIÓN ---
def configurar_pagina():
    st.set_page_config(page_title="Nexus Pro | Bigotes y Patitas", page_icon="🐾", layout="wide")

@st.cache_resource(ttl=600)
def conectar_google_sheets():
    gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
    sh = gc.open_by_url(st.secrets["SHEET_URL"])
    ws_inv = sh.worksheet("Inventario")
    ws_cli = sh.worksheet("Clientes")
    ws_ven = sh.worksheet("Ventas")
    ws_gas = sh.worksheet("Gastos")
    ws_cie = sh.worksheet("Cierres")
    ws_cap = sh.worksheet("Capital")
    ws_prov = sh.worksheet("Maestro_Proveedores")
    ws_ord = sh.worksheet("Historial_Ordenes")
    ws_rec = sh.worksheet("Historial_Recepciones")
    return ws_inv, ws_cli, ws_ven, ws_gas, ws_cie, ws_cap, ws_prov, ws_ord, ws_rec

def leer_datos(ws):
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    for col in ['Precio', 'Stock', 'Costo', 'Monto', 'Total', 'Costo_Total', 'Base_Inicial', 'Ventas_Efectivo', 'Gastos_Efectivo', 'Dinero_A_Bancos', 'Saldo_Teorico', 'Saldo_Real', 'Diferencia']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    return df

# --- FUNCIONES DE NEGOCIO (puedes expandirlas según tu lógica actual) ---

def actualizar_estado_envio(ws_ven, id_venta, nuevo_estado):
    cell = ws_ven.find(str(id_venta))
    if cell:
        headers = ws_ven.row_values(1)
        col_index = headers.index("Estado_Envio") + 1
        ws_ven.update_cell(cell.row, col_index, nuevo_estado)
        return True
    return False

def generar_mensaje_whatsapp(nombre_cliente, mascota, tipo_cliente, items_str, total):
    saludo = f"¡Hola {nombre_cliente}! 👋 Bienvenido/a a la familia Bigotes y Patitas." if tipo_cliente == "NUEVO" else f"¡Hola de nuevo {nombre_cliente}! 👋"
    cuerpo = f"Nos emociona mucho que nos hayas elegido para consentir a {mascota}." if tipo_cliente == "NUEVO" else ""
    resumen = f"\n\n🧾 Resumen de tu compra:\n{items_str}\n\n💰 Total: ${total:,.0f}"
    despedida = "\n\n¡Muchas gracias y feliz día! 🐾"
    return urllib.parse.quote(f"{saludo}\n{cuerpo}{resumen}{despedida}")

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

def actualizar_stock(ws_inv, carrito):
    df_inv = leer_datos(ws_inv)
    for item in carrito:
        id_prod = item['ID_Producto']
        cantidad = item['Cantidad']
        cell = ws_inv.find(str(id_prod))
        if cell:
            stock_actual = df_inv[df_inv['ID_Producto'] == id_prod]['Stock'].values[0]
            ws_inv.update_cell(cell.row, df_inv.columns.get_loc('Stock')+1, int(stock_actual) - int(cantidad))

# --- PESTAÑAS ---

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
            st.dataframe(df_inv[['Nombre', 'Stock', 'Precio']], use_container_width=True, hide_index=True)
            productos = df_inv['Nombre'].tolist()
            producto_sel = st.selectbox("Producto", productos)
            prod_row = df_inv[df_inv['Nombre'] == producto_sel].iloc[0]
            st.info(f"Stock disponible: {prod_row['Stock']} | Precio: ${prod_row['Precio']:,.0f}")
            cantidad = st.number_input("Cantidad", min_value=1, value=1, max_value=int(prod_row['Stock']))
            if st.button("Agregar al Carrito"):
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
                id_venta = f"VEN-{int(datetime.now().timestamp())}"
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                items_str = ", ".join([f"{x['Cantidad']}x{x['Nombre_Producto']}" for x in st.session_state.carrito])
                total = sum([x['Subtotal'] for x in st.session_state.carrito])
                ws_ven.append_row([
                    id_venta, fecha,
                    st.session_state.cliente_actual.get('Cedula', ''),
                    st.session_state.cliente_actual.get('Nombre', ''),
                    tipo_entrega, direccion, "Pendiente" if tipo_entrega != "Local" else "Entregado",
                    metodo_pago, "", total, items_str, "", # Costo_Total vacío por ahora
                ])
                actualizar_stock(ws_inv, st.session_state.carrito)
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
                if telefono and len(str(telefono)) >= 7:
                    tel = str(telefono)
                    if not tel.startswith('57') and len(tel) == 10:
                        tel = '57' + tel
                    link_wa = f"https://wa.me/{tel}?text={mensaje}"
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
        if st.session_state.cliente_actual:
            st.markdown("#### Mascotas registradas")
            mascotas = st.session_state.cliente_actual.get('Lista_Nombres_Mascotas', [])
            info_mascotas = st.session_state.cliente_actual.get('Info_Mascotas', '')
            if info_mascotas:
                try:
                    lista = json.loads(info_mascotas)
                    for m in lista:
                        st.info(f"🐾 {m['Nombre']} | Cumpleaños: {m['Cumpleaños']} | Tipo: {m['Tipo']}")
                except:
                    st.write("Mascotas: " + ", ".join(mascotas))
            else:
                st.write("Mascotas: " + ", ".join(mascotas))

def tab_clientes(ws_cli, ws_ven):
    st.header("👤 Gestión de Clientes")
    df_c = leer_datos(ws_cli)
    search = st.text_input("Buscar cliente", key="busca_cli")
    mask = (
        df_c['Nombre'].str.contains(search, case=False, na=False) |
        df_c['Cedula'].astype(str).str.contains(search, case=False, na=False) |
        df_c['Mascota'].str.contains(search, case=False, na=False) |
        df_c['Telefono'].astype(str).str.contains(search, case=False, na=False)
    ) if search else [True]*len(df_c)
    resultados = df_c[mask]
    st.dataframe(resultados[['Cedula', 'Nombre', 'Mascota', 'Telefono', 'Direccion', 'Email']], use_container_width=True, hide_index=True)
    st.markdown("---")
    st.subheader("Historial de Ventas del Cliente")
    selected_idx = st.selectbox("Selecciona un cliente para ver historial", resultados.index, format_func=lambda i: f"{resultados.loc[i, 'Nombre']} ({resultados.loc[i, 'Cedula']})", key="cli_hist")
    cliente = resultados.loc[selected_idx]
    st.markdown("#### Mascotas registradas")
    info_mascotas = cliente.get('Info_Mascotas', '')
    if info_mascotas:
        try:
            lista = json.loads(info_mascotas)
            for m in lista:
                st.info(f"🐾 {m['Nombre']} | Cumpleaños: {m['Cumpleaños']} | Tipo: {m['Tipo']}")
        except:
            st.write("Mascotas: " + str(cliente.get('Mascota', '')))
    else:
        st.write("Mascotas: " + str(cliente.get('Mascota', '')))
    with st.expander("➕ Crear/Editar Cliente"):
        with st.form("form_cliente"):
            cedula = st.text_input("Cédula")
            nombre = st.text_input("Nombre")
            telefono = st.text_input("Teléfono")
            direccion = st.text_input("Dirección")
            email = st.text_input("Email")

            st.markdown("#### Mascotas del Cliente")
            num_mascotas = st.number_input("¿Cuántas mascotas tiene?", min_value=1, max_value=5, value=1)
            mascotas = []
            for i in range(num_mascotas):
                st.markdown(f"##### Mascota #{i+1}")
                nombre_mascota = st.text_input(f"Nombre Mascota #{i+1}", key=f"mascota_nombre_{i}")
                cumple_mascota = st.date_input(f"Cumpleaños Mascota #{i+1}", key=f"mascota_cumple_{i}")
                tipo_mascota = st.selectbox(f"Tipo Mascota #{i+1}", ["Perro", "Gato", "Otro"], key=f"mascota_tipo_{i}")
                mascotas.append({
                    "Nombre": nombre_mascota,
                    "Cumpleaños": cumple_mascota.strftime("%Y-%m-%d"),
                    "Tipo": tipo_mascota
                })

            if st.form_submit_button("Guardar Cliente"):
                info_mascotas_json = json.dumps(mascotas)
                ws_cli.append_row([cedula, nombre, "", telefono, direccion, email, info_mascotas_json])
                st.success("Cliente guardado correctamente con sus mascotas.")
                st.rerun()

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
        metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"])
        banco = st.text_input("Banco/Origen", "")
        if st.form_submit_button("Registrar Gasto"):
            ws_gas.append_row([
                f"GAS-{int(datetime.now().timestamp())}",
                datetime.now().strftime("%Y-%m-%d"),
                tipo,
                categoria,
                descripcion,
                monto,
                metodo_pago,
                banco
            ])
            st.success("Gasto registrado correctamente.")
            st.rerun()
    st.subheader("Buscar Gastos")
    df_g = leer_datos(ws_gas)
    search = st.text_input("Buscar gasto", key="busca_gasto")
    mask = (
        df_g['Descripcion'].str.contains(search, case=False, na=False) |
        df_g['Categoria'].str.contains(search, case=False, na=False) |
        df_g['Banco_Origen'].str.contains(search, case=False, na=False)
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
    gastos_efectivo = gastos_hoy[gastos_hoy['Metodo_Pago'] == "Efectivo"]['Monto'].sum() if 'Metodo_Pago' in gastos_hoy.columns else 0.0
    dinero_a_bancos = st.number_input("Dinero a Bancos (consignaciones)", min_value=0.0, value=0.0)
    saldo_teorico = base_inicial + ventas_efectivo - gastos_efectivo - dinero_a_bancos
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
            dinero_a_bancos,
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
    search_v = st.text_input("Buscar ventas", key="busca_ven")
    mask = (
        df_v['Nombre_Cliente'].str.contains(search_v, case=False, na=False) |
        df_v['Items'].str.contains(search_v, case=False, na=False) |
        df_v['Metodo_Pago'].str.contains(search_v, case=False, na=False)
    ) if search_v else [True]*len(df_v)
    resultados = df_v[mask]
    st.dataframe(resultados, use_container_width=True)
    if not resultados.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            resultados.to_excel(writer, index=False)
        output.seek(0)
        st.download_button("⬇️ Descargar Ventas en Excel", output, "Ventas.xlsx")
    st.subheader("Buscar Gastos")
    df_g = leer_datos(ws_gas)
    search_g = st.text_input("Buscar gastos", key="busca_gas")
    mask_g = (
        df_g['Descripcion'].str.contains(search_g, case=False, na=False) |
        df_g['Categoria'].str.contains(search_g, case=False, na=False) |
        df_g['Banco_Origen'].str.contains(search_g, case=False, na=False)
    ) if search_g else [True]*len(df_g)
    resultados_g = df_g[mask_g]
    st.dataframe(resultados_g, use_container_width=True)
    if not resultados_g.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            resultados_g.to_excel(writer, index=False)
        output.seek(0)
        st.download_button("⬇️ Descargar Gastos en Excel", output, "Gastos.xlsx")
    st.subheader("Buscar Cuadres de Caja")
    df_c = leer_datos(ws_cie)
    search_c = st.text_input("Buscar cuadre", key="busca_cie")
    mask_c = (
        df_c['Fecha'].astype(str).str.contains(search_c, case=False, na=False) |
        df_c['Notas'].str.contains(search_c, case=False, na=False)
    ) if search_c else [True]*len(df_c)
    resultados_c = df_c[mask_c]
    st.dataframe(resultados_c, use_container_width=True)
    if not resultados_c.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            resultados_c.to_excel(writer, index=False)
        output.seek(0)
        st.download_button("⬇️ Descargar Cuadres en Excel", output, "Cuadres.xlsx")

def main():
    configurar_pagina()
    ws_inv, ws_cli, ws_ven, ws_gas, ws_cie, ws_cap, ws_prov, ws_ord, ws_rec = conectar_google_sheets()
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
