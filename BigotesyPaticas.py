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
    for item in carrito:
        id_prod = item['ID_Producto']
        cantidad = item['Cantidad']
        filtro = df_inv[df_inv['ID_Producto'] == id_prod]
        if not filtro.empty:
            stock_actual = filtro['Stock'].values[0]
            cell = ws_inv.find(str(id_prod))
            if cell:
                ws_inv.update_cell(cell.row, df_inv.columns.get_loc('Stock')+1, int(stock_actual) - int(cantidad))
        else:
            st.warning(f"Producto con ID {id_prod} no encontrado en inventario. No se actualizó el stock.")

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
        opciones = []
        id_map = {}
        for _, row in df_inv.iterrows():
            stock = int(row['Stock'])
            precio = int(row['Precio'])
            nombre = row['Nombre']
            icon = "🔴" if stock == 0 else "🟡" if stock <= 5 else "🟢"
            display = f"{icon} {nombre} | Stock: {stock} | ${precio:,}"
            opciones.append(display)
            id_map[display] = row['ID_Producto']

        producto_sel = st.selectbox("Producto", opciones, help="Busca por nombre, stock o precio")
        id_prod_sel = id_map[producto_sel]
        prod_row = df_inv[df_inv['ID_Producto'] == id_prod_sel].iloc[0]
        st.info(f"{icon} Stock disponible: {prod_row['Stock']} | Precio: ${prod_row['Precio']:,.0f}")
        cantidad = st.number_input("Cantidad", min_value=1, value=1, max_value=int(prod_row['Stock']) if int(prod_row['Stock']) > 0 else 1, key="cantidad_agregar")
        precio_mod = st.number_input("Precio Unitario", min_value=0, value=int(prod_row['Precio']), key="precio_agregar")
        descuento = st.number_input("Descuento", min_value=0, value=0, key="descuento_agregar")
        if st.button("Agregar al Carrito", help="Agrega el producto al carrito"):
            existe = False
            for item in st.session_state.carrito:
                if item["ID_Producto"] == prod_row['ID_Producto']:
                    item["Cantidad"] += cantidad
                    item["Precio"] = precio_mod
                    item["Descuento"] = descuento
                    item["Subtotal"] = (precio_mod - descuento) * item["Cantidad"]
                    existe = True
                    break
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
            st.success(f"{cantidad} x {prod_row['Nombre']} agregado/modificado en el carrito.")

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
            id_venta = f"VEN-{int(datetime.now().timestamp())}"
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
