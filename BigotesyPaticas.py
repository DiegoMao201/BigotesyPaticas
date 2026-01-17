import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date, timedelta
import json
import urllib.parse
import jinja2
from weasyprint import HTML
from io import BytesIO
import io
import pytz

TZ_CO = pytz.timezone("America/Bogota")
def now_co():
    return datetime.now(TZ_CO)

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
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        for col in ['Precio', 'Stock', 'Costo', 'Monto', 'Total', 'Costo_Total', 'Base_Inicial', 'Ventas_Efectivo', 'Gastos_Efectivo', 'Dinero_A_Bancos', 'Saldo_Teorico', 'Saldo_Real', 'Diferencia']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"🔴 Error leyendo datos de Google Sheets: {e}")
        return pd.DataFrame()

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
    # Normaliza todos los IDs del inventario una vez
    df_inv['ID_Producto_Norm'] = df_inv['ID_Producto'].apply(normalizar_id_producto)
    for item in carrito:
        id_prod_norm = normalizar_id_producto(item['ID_Producto'])
        cantidad = item['Cantidad']
        filtro = df_inv[df_inv['ID_Producto_Norm'] == id_prod_norm]
        if not filtro.empty:
            stock_actual = filtro['Stock'].values[0]
            # Busca la celda en Google Sheets usando el ID normalizado
            for idx, row in df_inv.iterrows():
                if row['ID_Producto_Norm'] == id_prod_norm:
                    cell = ws_inv.find(str(row['ID_Producto']))
                    if cell:
                        ws_inv.update_cell(cell.row, df_inv.columns.get_loc('Stock')+1, int(stock_actual) - int(cantidad))
                    break
        else:
            st.warning(f"Producto con ID {item['ID_Producto']} no encontrado en inventario. No se actualizó el stock.")

def normalizar_id_producto(id_prod):
    """Convierte cualquier ID_Producto a string, sin espacios, sin puntos, sin comas, sin ceros a la izquierda innecesarios."""
    if pd.isna(id_prod):
        return ""
    s = str(id_prod).strip()
    # Elimina espacios, puntos, comas, y ceros a la izquierda solo si es numérico puro
    s = s.replace(" ", "").replace(",", "").replace(".", "")
    return s.upper()

# --- PESTAÑAS ---

def tab_pos(ws_inv, ws_cli, ws_ven):
    st.markdown("""
        <style>
        .main-title { color: #187f77; font-size: 2.2rem; font-weight: 800; margin-bottom: 0.5rem; }
        .sub-title { color: #f5a641; font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem; }
        .mascota-box { background: #f8f9fa; border-radius: 12px; padding: 10px 18px; margin-bottom: 10px; border-left: 5px solid #f5a641; }
        .carrito-total { background: #f5a641; color: white; font-size: 1.5rem; font-weight: bold; border-radius: 10px; padding: 12px 24px; text-align: right; margin-top: 10px; }
        .btn-factura { background: linear-gradient(135deg, #187f77, #f5a641); color: white !important; font-weight: bold; border-radius: 10px; padding: 14px 28px; font-size: 1.1rem; border: none; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">🐾 Punto de Venta Bigotes y Patitas</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Venta rápida y profesional para consentir a tus peluditos</div>', unsafe_allow_html=True)

    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'mascota_seleccionada' not in st.session_state: st.session_state.mascota_seleccionada = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None
    if 'whatsapp_link' not in st.session_state: st.session_state.whatsapp_link = None

    # --- CLIENTE ---
    st.markdown("### 👤 Buscar Cliente")
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
        if st.button("Cargar Cliente", help="Carga el cliente y sus mascotas"):
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
    # --- Mascotas visuales ---
    if st.session_state.cliente_actual:
        st.markdown("#### 🐶 Mascotas registradas")
        info_mascotas = st.session_state.cliente_actual.get('Info_Mascotas', '')
        if info_mascotas:
            try:
                lista = json.loads(info_mascotas)
                for m in lista:
                    st.markdown(f'<div class="mascota-box">🐾 <b>{m["Nombre"]}</b> | Cumpleaños: {m["Cumpleaños"]} | Tipo: {m["Tipo"]}</div>', unsafe_allow_html=True)
            except:
                st.write("Mascotas: " + ", ".join(st.session_state.cliente_actual.get('Lista_Nombres_Mascotas', [])))
        else:
            st.write("Mascotas: " + ", ".join(st.session_state.cliente_actual.get('Lista_Nombres_Mascotas', [])))

    # --- PRODUCTOS ---
    st.markdown("### 🛒 Buscar y Agregar Producto")
    df_inv = leer_datos(ws_inv)
    if not df_inv.empty:
        if 'ID_Producto_Norm' not in df_inv.columns:
            df_inv['ID_Producto_Norm'] = df_inv['ID_Producto'].apply(normalizar_id_producto)
        opciones, id_map = [], {}
        for _, row in df_inv.iterrows():
            stock = int(row['Stock']); precio = int(row['Precio']); nombre = row['Nombre']
            display = f"{nombre} | Stock: {stock} | ${precio:,}"
            opciones.append(display); id_map[display] = row['ID_Producto_Norm']

        producto_sel = st.selectbox("Producto", opciones, help="Busca por nombre, stock o precio")
        id_prod_sel_norm = id_map[producto_sel]
        prod_row = df_inv[df_inv['ID_Producto_Norm'] == id_prod_sel_norm].iloc[0]

        st.caption(f"{prod_row['Nombre']} · Stock {int(prod_row['Stock'])} · ${int(prod_row['Precio']):,}")
        cantidad = st.number_input("Cantidad", min_value=1, value=1, max_value=max(int(prod_row['Stock']),1), key="cantidad_agregar")
        precio_mod = st.number_input("Precio Unitario", min_value=0, value=int(prod_row['Precio']), key="precio_agregar")
        descuento = st.number_input("Descuento", min_value=0, value=0, key="descuento_agregar")
        if st.button("Agregar al Carrito", help="Agrega el producto al carrito"):
            existe = False
            for item in st.session_state.carrito:
                if item["ID_Producto"] == prod_row['ID_Producto']:
                    item["Cantidad"] = cantidad
                    item["Precio"] = precio_mod
                    item["Descuento"] = descuento
                    item["Subtotal"] = (precio_mod - descuento) * item["Cantidad"]
                    existe = True; break
            if not existe:
                subtotal = (precio_mod - descuento) * cantidad
                st.session_state.carrito.append({
                    "ID_Producto": prod_row['ID_Producto'],
                    "Nombre_Producto": prod_row['Nombre'],
                    "Cantidad": cantidad,
                    "Precio": precio_mod,
                    "Descuento": descuento,
                    "Subtotal": subtotal
                })
            st.success(f"{prod_row['Nombre']} actualizado en el carrito.")

    # --- CARRITO VISUAL Y EDICIÓN ---
    if st.session_state.carrito:
        st.markdown("### 🧺 Carrito de Compra")
        df_carrito = pd.DataFrame(st.session_state.carrito)
        selected_row = st.selectbox(
            "Selecciona un producto para eliminar del carrito",
            df_carrito.index,
            format_func=lambda i: f"{df_carrito.loc[i, 'Nombre_Producto']} (x{df_carrito.loc[i, 'Cantidad']})"
        )
        if st.button("Eliminar Producto Seleccionado"):
            st.session_state.carrito.pop(selected_row)
            st.success("Producto eliminado del carrito.")
            st.rerun()

        edited = st.data_editor(
            df_carrito,
            key="carrito_editor",
            use_container_width=True,
            column_config={
                "Nombre_Producto": st.column_config.TextColumn("Producto", disabled=True),
                "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=1),
                "Precio": st.column_config.NumberColumn("Precio", min_value=0),
                "Descuento": st.column_config.NumberColumn("Descuento", min_value=0),
                "Subtotal": st.column_config.NumberColumn("Subtotal", disabled=True)
            },
            hide_index=True
        )
        for i, row in edited.iterrows():
            edited.at[i, "Subtotal"] = (row["Precio"] - row["Descuento"]) * row["Cantidad"]
        st.session_state.carrito = edited.to_dict("records")
        total = sum([item["Subtotal"] for item in st.session_state.carrito])
        st.markdown(f'<div class="carrito-total">TOTAL: ${total:,.0f}</div>', unsafe_allow_html=True)
        if st.button("Vaciar Carrito"):
            st.session_state.carrito = []
            st.rerun()

    # --- FACTURACIÓN Y PDF ---
    st.markdown("### 💳 Facturación")
    if st.session_state.carrito and st.session_state.cliente_actual:
        metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "Daviplata", "Tarjeta", "Transferencia"])
        tipo_entrega = st.selectbox("Tipo de Entrega", ["Local", "Envío a Domicilio"])
        direccion = st.text_input("Dirección de Entrega", value=st.session_state.cliente_actual.get('Direccion', ''))
        if st.button("Facturar y Guardar Venta", key="btn_factura", help="Genera la factura y guarda la venta"):
            id_venta = f"VEN-{int(now_co().timestamp())}"
            fecha = now_co().strftime("%Y-%m-%d %H:%M:%S")
            items_str = ", ".join([f"{x['Cantidad']}x{x['Nombre_Producto']}" for x in st.session_state.carrito])
            total = sum([x['Subtotal'] for x in st.session_state.carrito])
            ws_ven.append_row([
                id_venta, fecha,
                st.session_state.cliente_actual.get('Cedula', ''),
                st.session_state.cliente_actual.get('Nombre', ''),
                tipo_entrega, direccion, "Pendiente" if tipo_entrega != "Local" else "Entregado",
                metodo_pago, "", total, items_str, "", st.session_state.mascota_seleccionada
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
        st.markdown(f"""<a href="{st.session_state.whatsapp_link}" target="_blank" class="btn-factura">📲 Enviar Resumen por WhatsApp</a>""", unsafe_allow_html=True)

def tab_cuadre(ws_ven, ws_gas, ws_cie):
    st.header("💵 Cuadre de Caja Diario (Avanzado y Robusto)")

    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)
    df_cie = leer_datos(ws_cie)
    hoy = now_co().date()

    # --- Selector de fecha para cargar/editar cajas previas ---
    fecha_sel = st.date_input("Selecciona la fecha de la caja a revisar/editar", value=hoy)

    # Buscar si ya existe cierre para la fecha seleccionada
    cierre_existente = df_cie[df_cie['Fecha'].dt.date == fecha_sel] if not df_cie.empty else pd.DataFrame()
    row_cierre = cierre_existente.iloc[-1] if not cierre_existente.empty else None
    row_number = (cierre_existente.index[-1] + 2) if not cierre_existente.empty else None  # +2 por header en Sheets

    # --- Ventas del día seleccionado ---
    ventas_dia = df_v[df_v['Fecha'].dt.date == fecha_sel] if not df_v.empty else pd.DataFrame()
    ventas_pagadas = ventas_dia[ventas_dia['Estado_Envio'].isin(["Entregado", "Pagado"])]
    ventas_pendientes = ventas_dia[ventas_dia['Estado_Envio'].isin(["Pendiente", "En camino"])]

    # --- Gastos del día seleccionado (flujo único con pestaña Gastos) ---
    gastos_dia = df_g[df_g['Fecha'] == fecha_sel.strftime("%Y-%m-%d")] if not df_g.empty else pd.DataFrame()
    gastos_efectivo = gastos_dia[gastos_dia['Metodo_Pago'] == "Efectivo"]['Monto'].sum() if 'Metodo_Pago' in gastos_dia.columns else 0.0

    # --- Prefills: si hay cierre previo, cargamos sus valores; si no, base inicial es saldo real del día anterior ---
    saldo_real_prev = 0.0
    if not df_cie.empty:
        prev = df_cie[df_cie['Fecha'].dt.date == (fecha_sel - timedelta(days=1))]
        if not prev.empty:
            saldo_real_prev = prev.iloc[-1].get('Saldo_Real', 0.0)

    base_inicial_default = row_cierre['Base_Inicial'] if row_cierre is not None else saldo_real_prev
    ventas_efectivo = ventas_pagadas[ventas_pagadas['Metodo_Pago'] == "Efectivo"]['Total'].sum()
    ventas_electronico = ventas_pagadas[ventas_pagadas['Metodo_Pago'].isin(["Nequi", "Daviplata", "Transferencia", "Tarjeta"])]["Total"].sum()

    base_inicial = st.number_input("Base Inicial (Efectivo en caja al abrir)", min_value=0.0, value=float(base_inicial_default))
    dinero_a_bancos = st.number_input("Dinero a Bancos (consignaciones)", min_value=0.0, value=float(row_cierre['Dinero_A_Bancos']) if row_cierre is not None else 0.0)

    saldo_teorico = base_inicial + ventas_efectivo - gastos_efectivo - dinero_a_bancos
    saldo_real = st.number_input("Saldo Real contado en caja", min_value=0.0, value=float(row_cierre['Saldo_Real']) if row_cierre is not None else saldo_teorico)
    diferencia = saldo_real - saldo_teorico

    notas = st.text_area("Notas del cuadre", value=row_cierre['Notas'] if row_cierre is not None and 'Notas' in row_cierre else "")

    # --- Visualización de métricas ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ventas Efectivo", f"${ventas_efectivo:,.0f}")
    col2.metric("Ventas Electrónico", f"${ventas_electronico:,.0f}")
    col3.metric("Gastos Efectivo", f"${gastos_efectivo:,.0f}")
    col4.metric("Base Inicial", f"${base_inicial:,.0f}")

    col5, col6, col7 = st.columns(3)
    col5.metric("Saldo Teórico", f"${saldo_teorico:,.0f}")
    col6.metric("Saldo Real", f"${saldo_real:,.0f}")
    col7.metric("Diferencia", f"${diferencia:,.0f}")

    # --- Registro rápido de gastos desde el cuadre ---
    with st.expander("➕ Registrar Gasto Rápido"):
        with st.form("form_gasto_cuadre"):
            tipo = st.selectbox("Tipo de Gasto", ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"])
            categoria = st.text_input("Categoría", "General")
            descripcion = st.text_area("Descripción")
            monto = st.number_input("Monto", min_value=0.0)
            metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"])
            banco = st.text_input("Banco/Origen", "")
            if st.form_submit_button("Registrar Gasto"):
                ts = int(now_co().timestamp())
                ws_gas.append_row([
                    f"GAS-{ts}",
                    now_co().strftime("%Y-%m-%d"),
                    tipo,
                    categoria,
                    descripcion,
                    monto,
                    metodo_pago,   # Metodo_Pago
                    banco,         # Banco_Origen
                    "Módulo POS"   # Responsable
                ])
                st.success("Gasto registrado correctamente.")
                st.rerun()

    # --- Ventas pendientes del día ---
    st.markdown("### 🚩 Ventas Pendientes de Pago/Entrega")
    if ventas_pendientes.empty:
        st.success("No hay ventas pendientes hoy.")
    else:
        st.dataframe(ventas_pendientes[['ID_Venta', 'Fecha', 'Nombre_Cliente', 'Total', 'Metodo_Pago', 'Estado_Envio']], use_container_width=True)
        selected = st.selectbox("Selecciona una venta pendiente para marcar como pagada", ventas_pendientes['ID_Venta'])
        if st.button("Marcar como Pagada/Entregada"):
            actualizar_estado_envio(ws_ven, selected, "Entregado")
            st.success("Venta marcada como pagada/entregada.")
            st.rerun()

    # --- Notas y guardar cuadre ---
    notas = st.text_area("Notas del cuadre", "")
    if st.button("Guardar Cuadre en Google Sheets"):
        fila_valores = [
            fecha_sel.strftime("%Y-%m-%d"),
            now_co().strftime("%H:%M:%S"),
            base_inicial,
            ventas_efectivo,
            ventas_electronico,
            gastos_efectivo,
            dinero_a_bancos,
            saldo_teorico,
            saldo_real,
            diferencia,
            notas,
            0.0,  # costo_mercancia (ajusta si lo calculas)
            ventas_efectivo + ventas_electronico - gastos_efectivo  # margen_ganado aprox
        ]
        if row_number:
            ws_cie.update(f"A{row_number}:M{row_number}", [fila_valores])
            st.success("Cierre actualizado (sin crear fila nueva).")
        else:
            ws_cie.append_row(fila_valores)
            st.success("Cierre guardado como nuevo.")

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
    if not resultados.empty:
        # Mejora visual: Colores por estado
        def color_estado(val):
            if val == "Entregado" or val == "Pagado":
                return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == "Pendiente":
                return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
            elif val == "Cancelado":
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            return ''
        st.dataframe(
            resultados.style.applymap(color_estado, subset=['Estado_Envio']),
            use_container_width=True
        )
        # ...descarga Excel igual...
    else:
        st.info("No hay ventas para mostrar.")
    # ...resto igual...

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
    st.dataframe(resultados[['Cedula', 'Nombre', 'Telefono', 'Email', 'Direccion', 'Mascota', 'Tipo_Mascota', 'Cumpleaños_mascota', 'Registro']], use_container_width=True, hide_index=True)
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
        if 'cliente_guardado' not in st.session_state:
            st.session_state.cliente_guardado = False
        if 'last_welcome_link' not in st.session_state:
            st.session_state.last_welcome_link = None

        cedula = st.text_input("Cédula", key="cli_cedula")
        nombre = st.text_input("Nombre", key="cli_nombre")
        telefono = st.text_input("Teléfono", key="cli_telefono")
        email = st.text_input("Email", key="cli_email")
        direccion = st.text_input("Dirección", key="cli_direccion")
        registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        st.markdown("#### Mascotas del Cliente")
        num_mascotas = st.number_input("¿Cuántas mascotas tiene?", min_value=1, max_value=5, value=1, key="cli_num_mascotas")
        mascotas = []
        for i in range(num_mascotas):
            st.markdown(f"##### Mascota #{i+1}")
            nombre_mascota = st.text_input(f"Nombre Mascota #{i+1}", key=f"cli_mascota_nombre_{i}")
            tipo_mascota = st.selectbox(f"Tipo Mascota #{i+1}", ["Perro", "Gato", "Otro"], key=f"cli_mascota_tipo_{i}")
            cumple_mascota = st.date_input(f"Cumpleaños Mascota #{i+1}", key=f"cli_mascota_cumple_{i}")
            mascotas.append({
                "Nombre": nombre_mascota,
                "Tipo": tipo_mascota,
                "Cumpleaños": cumple_mascota.strftime("%Y-%m-%d")
            })

        if st.button("Guardar Cliente", type="primary", use_container_width=True):
            info_mascotas_json = json.dumps(mascotas)
            mascota_principal = mascotas[0]['Nombre'] if mascotas else ""
            tipo_principal = mascotas[0]['Tipo'] if mascotas else ""
            cumple_principal = mascotas[0]['Cumpleaños'] if mascotas else ""
            ws_cli.append_row([
                cedula, nombre, telefono, email, direccion,
                mascota_principal, tipo_principal, cumple_principal,
                registro, info_mascotas_json
            ])
            st.session_state.cliente_guardado = True
            # Generar link de bienvenida y guardarlo
            mensaje = f"""¡Hola {nombre}! 👋
Bienvenido/a a la familia Bigotes y Patitas 🐾.

Nos alegra mucho tenerte con nosotros y que confíes en nosotros para consentir a tus peluditos.

Recuerda que puedes contactarnos para cualquier cosa que necesite {mascota_principal} o sus amigos. ¡Estamos aquí para ayudarte!

¡Un abrazo y feliz día! 🐶🐱
"""
            telefono_clean = str(telefono).replace(" ", "").replace("+", "").replace("-", "")
            if len(telefono_clean) == 10 and not telefono_clean.startswith("57"):
                telefono_clean = "57" + telefono_clean
            st.session_state.last_welcome_link = f"https://wa.me/{telefono_clean}?text={urllib.parse.quote(mensaje)}"
            st.success("Cliente guardado correctamente con sus mascotas.")
            reset_form_cliente()

        if st.session_state.last_welcome_link:
            st.markdown(
                f"""<a href="{st.session_state.last_welcome_link}" target="_blank" style="display:inline-block; background:#25D366; color:white; padding:12px 20px; border-radius:8px; text-decoration:none; font-weight:bold; margin-top:10px;">📲 Enviar Bienvenida por WhatsApp</a>""",
                unsafe_allow_html=True
            )

def reset_form_cliente():
    for k in ["cli_cedula","cli_nombre","cli_telefono","cli_email","cli_direccion","cli_num_mascotas"]:
        st.session_state.pop(k, None)
    for i in range(5):
        st.session_state.pop(f"cli_mascota_nombre_{i}", None)
        st.session_state.pop(f"cli_mascota_tipo_{i}", None)
        st.session_state.pop(f"cli_mascota_cumple_{i}", None)
    st.session_state.cliente_guardado = False

def tab_despachos(ws_ven):
    st.header("🚚 Despachos y Ventas Pendientes")
    df_v = leer_datos(ws_ven)
    pendientes = df_v[df_v['Estado_Envio'].isin(["Pendiente", "En camino"])]
    if pendientes.empty:
        st.success("No hay despachos pendientes.")
    else:
        st.dataframe(pendientes[['ID_Venta', 'Fecha', 'Nombre_Cliente', 'Direccion_Envio', 'Total', 'Metodo_Pago', 'Estado_Envio']], use_container_width=True)
        selected = st.selectbox("Selecciona una venta para actualizar estado", pendientes['ID_Venta'])
        nuevo_estado = st.selectbox("Nuevo estado", ["Entregado", "Pagado", "Cancelado"])
        if st.button("Actualizar Estado"):
            actualizar_estado_envio(ws_ven, selected, nuevo_estado)
            st.success("Estado actualizado.")
            st.rerun()

def tab_gastos(ws_gas):
    st.header("💳 Registro y Consulta de Gastos")
    df_g = leer_datos(ws_gas)
    st.dataframe(df_g, use_container_width=True)
    with st.expander("➕ Registrar Nuevo Gasto"):
        with st.form("form_gasto"):
            fecha = st.date_input("Fecha", value=date.today())
            tipo = st.text_input("Tipo de Gasto")
            categoria = st.text_input("Categoría")
            descripcion = st.text_area("Descripción")
            monto = st.number_input("Monto", min_value=0.0)
            metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"])
            banco = st.text_input("Banco/Origen")
            if st.form_submit_button("Registrar Gasto"):
                ts = int(now_co().timestamp())
                ws_gas.append_row([
                    f"GAS-{ts}",
                    now_co().strftime("%Y-%m-%d"),
                    tipo,
                    categoria,
                    descripcion,
                    monto,
                    metodo_pago,   # Metodo_Pago
                    banco,         # Banco_Origen
                    "Módulo POS"   # Responsable
                ])
                st.success("Gasto registrado correctamente.")
                st.rerun()

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
    with tabs[4]:
        tab_cuadre(ws_ven, ws_gas, ws_cie)
    with tabs[5]:
        tab_resumen(ws_ven, ws_gas, ws_cie)
    with tabs[1]:
        tab_clientes(ws_cli, ws_ven)
    with tabs[2]:
        tab_despachos(ws_ven)
    with tabs[3]:
        tab_gastos(ws_gas)
    # ...agrega aquí tus otras pestañas como tab_gastos, etc...

if __name__ == "__main__":
    main()
