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

# --- 1. CONFIGURACIÓN Y ESTILOS (NEXUS PRO THEME) ---

# Paleta de Colores Solicitada
COLOR_PRIMARIO = "#187f77"      # Cian Oscuro (Teal)
COLOR_SECUNDARIO = "#125e58"    # Variante más oscura para degradados
COLOR_ACENTO = "#f5a641"        # Naranja (Alertas y Acentos)
COLOR_FONDO = "#f8f9fa"         # Fondo gris muy claro para contraste
COLOR_TEXTO = "#262730"
COLOR_BLANCO = "#ffffff"

# Logo Verificado (Huella simple en PNG Base64)
LOGO_B64 = """
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
"""

def configurar_pagina():
    st.set_page_config(
        page_title="Nexus Pro | Bigotes y Patitas",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS Personalizado para Nexus Pro
    st.markdown(f"""
        <style>
        /* Importar fuente moderna */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        .stApp {{
            background-color: {COLOR_FONDO};
            font-family: 'Inter', sans-serif;
        }}
        
        h1, h2, h3 {{
            color: {COLOR_PRIMARIO};
            font-weight: 700;
        }}
        
        h4, h5, h6 {{
            color: {COLOR_TEXTO};
            font-weight: 600;
        }}

        /* Estilo de Tarjetas (Metric Containers y otros divs) */
        div[data-testid="metric-container"] {{
            background-color: {COLOR_BLANCO};
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border-left: 5px solid {COLOR_ACENTO};
        }}
        
        div[data-testid="stExpander"] {{
            background-color: {COLOR_BLANCO};
            border-radius: 10px;
            border: 1px solid #e0e0e0;
        }}

        /* Botones Primarios (Cian) */
        .stButton button[type="primary"] {{
            background: linear-gradient(135deg, {COLOR_PRIMARIO}, {COLOR_SECUNDARIO});
            border: none;
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }}
        .stButton button[type="primary"]:hover {{
            box-shadow: 0 5px 15px rgba(24, 127, 119, 0.4);
            transform: translateY(-1px);
        }}

        /* Botones Secundarios */
        .stButton button[type="secondary"] {{
            border: 2px solid {COLOR_PRIMARIO};
            color: {COLOR_PRIMARIO};
            border-radius: 8px;
        }}

        /* Inputs y Selects */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
            border-radius: 8px;
            border-color: #e0e0e0;
        }}
        .stTextInput input:focus, .stNumberInput input:focus {{
            border-color: {COLOR_PRIMARIO};
            box-shadow: 0 0 0 1px {COLOR_PRIMARIO};
        }}

        /* Tabs Personalizados */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: transparent;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 45px;
            white-space: pre-wrap;
            background-color: {COLOR_BLANCO};
            border-radius: 8px 8px 0 0;
            color: {COLOR_TEXTO};
            font-weight: 600;
            border: 1px solid #eee;
            border-bottom: none;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {COLOR_PRIMARIO};
            color: white;
            border-color: {COLOR_PRIMARIO};
        }}

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {{
            background-color: {COLOR_BLANCO};
            border-right: 1px solid #eee;
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
        for col in ['Precio', 'Stock', 'Monto', 'Total']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Estandarizar fechas si existen
        if 'Fecha' in df.columns:
             df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')

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
                # Usamos la cantidad vendida
                nuevo = max(0, stock_act - int(item['Cantidad']))
                ws_inv.update_cell(fila, 5, nuevo) 
        return True
    except Exception as e:
        st.error(f"Error actualizando stock: {e}")
        return False

# --- 3. GENERADOR DE PDF Y EXCEL ---

def generar_pdf_html(venta_data, items):
    try:
        # Usamos una plantilla simple embebida si no existe el archivo
        try:
            with open("factura.html", "r", encoding="utf-8") as f:
                template_str = f.read()
        except:
             template_str = f"""
             <html>
             <head>
                <style>
                    body {{ font-family: sans-serif; color: #333; }}
                    h2 {{ color: {COLOR_PRIMARIO}; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    td, th {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                    .total {{ font-size: 18px; font-weight: bold; color: {COLOR_PRIMARIO}; }}
                </style>
             </head>
             <body>
             <center><img src="data:image/png;base64,{{{{ logo_b64 }}}}" width="60"></center>
             <center><h2>Nexus Pro</h2><p>Bigotes y Patitas</p></center>
             <p><strong>Ticket:</strong> {{{{ id_venta }}}}<br><strong>Fecha:</strong> {{{{ fecha }}}}</p>
             <hr>
             <p><strong>Cliente:</strong> {{{{ cliente_nombre }}}}</p>
             <p><strong>Mascota:</strong> {{{{ cliente_mascota }}}}</p>
             <table>
             <tr style="background-color: #f2f2f2;"><th>Producto</th><th align="right">Total</th></tr>
             {{% for item in items %}}
             <tr><td>{{{{ item.Nombre_Producto }}}} (x{{{{ item.Cantidad }}}})</td><td align="right">${{{{ item.Subtotal }}}}</td></tr>
             {{% endfor %}}
             </table>
             <br>
             <p class="total" align="right">TOTAL A PAGAR: ${{{{ total }}}}</p>
             <center><p style="font-size:10px; color:#777;">Gracias por su compra</p></center>
             </body></html>
             """

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

def generar_excel_financiero(df_v, df_g, df_c, f_inicio, f_fin):
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 1. Hoja Resumen
            resumen_data = {
                'Concepto': ['Ingresos (Ventas)', 'Gastos Totales', 'Inversión/Capital', 'Utilidad Neta', 'Rango Fechas'],
                'Monto': [
                    df_v['Total'].sum(), 
                    df_g['Monto'].sum(), 
                    df_c['Monto'].sum(), 
                    df_v['Total'].sum() - df_g['Monto'].sum(),
                    f"{f_inicio} a {f_fin}"
                ]
            }
            pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen Gerencial', index=False)
            
            # 2. Hojas de Datos
            if not df_v.empty:
                df_v.to_excel(writer, sheet_name='Ventas Detalle', index=False)
            if not df_g.empty:
                df_g.to_excel(writer, sheet_name='Gastos Detalle', index=False)
            if not df_c.empty:
                df_c.to_excel(writer, sheet_name='Inversiones Detalle', index=False)
                
        return output.getvalue()
    except Exception as e:
        st.error(f"Error generando Excel: {e}")
        return None

# --- 4. MÓDULOS DE NEGOCIO ---

def tab_punto_venta(ws_inv, ws_cli, ws_ven):
    st.markdown(f"### <span style='color:{COLOR_ACENTO}'>🛒</span> Nexus Pro POS", unsafe_allow_html=True)
    st.caption("Punto de Venta - Bigotes y Patitas")
    
    # Inicialización de Estados
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None

    col_izq, col_der = st.columns([1.6, 1])

    # --- COLUMNA IZQUIERDA: Búsqueda y Carrito ---
    with col_izq:
        # 1. Selección de Cliente
        with st.expander("👤 Datos del Cliente", expanded=not st.session_state.cliente_actual):
            c1, c2 = st.columns([3, 1])
            busqueda = c1.text_input("Buscar por Cédula", placeholder="Ingrese documento...")
            if c2.button("🔍 Buscar"):
                df_c = leer_datos(ws_cli)
                if not df_c.empty:
                    df_c['Cedula'] = df_c['Cedula'].astype(str)
                    res = df_c[df_c['Cedula'] == busqueda.strip()]
                    if not res.empty:
                        st.session_state.cliente_actual = res.iloc[0].to_dict()
                        st.toast(f"Cliente cargado: {st.session_state.cliente_actual.get('Nombre')}", icon="✅")
                    else:
                        st.warning("Cliente no encontrado.")
        
        if st.session_state.cliente_actual:
            st.info(f"🟢 **{st.session_state.cliente_actual.get('Nombre')}** | Mascota: **{st.session_state.cliente_actual.get('Mascota', 'N/A')}**")

        st.markdown("---")
        
        # 2. Buscador de Productos (Con Stock)
        st.markdown("#### 📦 Catálogo de Productos")
        df_inv = leer_datos(ws_inv)
        
        if not df_inv.empty:
            prod_lista = df_inv.apply(lambda x: f"{x.get('Nombre', 'N/A')} | Stock: {x.get('Stock', 0)} | ${x.get('Precio', 0):,.0f} | ID:{x.get('ID_Producto', '')}", axis=1).tolist()
            
            sel_prod_str = st.selectbox("Escriba para buscar producto...", [""] + prod_lista)
            
            col_add_btn, col_dummy = st.columns([1, 2])
            if col_add_btn.button("➕ Agregar al Carrito", type="primary", use_container_width=True):
                if sel_prod_str:
                    try:
                        id_p = sel_prod_str.split("ID:")[1]
                        info_p = df_inv[df_inv['ID_Producto'].astype(str) == id_p].iloc[0]
                        
                        # Verificar si ya existe en carrito para sumar
                        existe = False
                        for item in st.session_state.carrito:
                            if str(item['ID_Producto']) == str(info_p['ID_Producto']):
                                item['Cantidad'] += 1
                                item['Subtotal'] = item['Cantidad'] * item['Precio']
                                existe = True
                                break
                        
                        if not existe:
                            nuevo_item = {
                                "ID_Producto": info_p['ID_Producto'],
                                "Nombre_Producto": info_p['Nombre'],
                                "Precio": float(info_p['Precio']),
                                "Cantidad": 1,
                                "Subtotal": float(info_p['Precio']),
                                "Eliminar": False 
                            }
                            st.session_state.carrito.append(nuevo_item)
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Error al agregar: {e}")

        # 3. TABLA EDITABLE (Carrito)
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>🛒</span> Detalle de Venta", unsafe_allow_html=True)
        
        if st.session_state.carrito:
            df_carrito = pd.DataFrame(st.session_state.carrito)
            
            column_config = {
                "Nombre_Producto": st.column_config.TextColumn("Producto", disabled=True, width="medium"),
                "Cantidad": st.column_config.NumberColumn("Cant.", min_value=1, step=1),
                "Precio": st.column_config.NumberColumn("Precio Unit.", format="$%d", min_value=0),
                "Subtotal": st.column_config.NumberColumn("Subtotal", format="$%d", disabled=True),
                "Eliminar": st.column_config.CheckboxColumn("Quitar")
            }

            edited_df = st.data_editor(
                df_carrito,
                column_config=column_config,
                column_order=["Nombre_Producto", "Cantidad", "Precio", "Subtotal", "Eliminar"],
                hide_index=True,
                use_container_width=True,
                key="editor_carrito",
                num_rows="dynamic"
            )

            # LÓGICA DE ACTUALIZACIÓN DEL CARRITO
            edited_df['Subtotal'] = edited_df['Cantidad'] * edited_df['Precio']
            items_finales = edited_df[~edited_df['Eliminar']].copy()
            nuevos_datos = items_finales.to_dict('records')
            
            for d in nuevos_datos:
                if 'Eliminar' in d: del d['Eliminar']
                d['Eliminar'] = False

            st.session_state.carrito = nuevos_datos
            
            total_general = sum(item['Subtotal'] for item in st.session_state.carrito)

        else:
            st.info("El carrito está vacío. Agrega productos arriba.")
            total_general = 0

    # --- COLUMNA DERECHA: Resumen y Pago ---
    with col_der:
        with st.container(border=True):
            st.markdown(f"### <span style='color:{COLOR_ACENTO}'>🧾</span> Resumen", unsafe_allow_html=True)
            
            # Mostrar Total Grande
            st.markdown(f"<h1 style='text-align: center; color: {COLOR_PRIMARIO}; font-size: 3em;'>${total_general:,.0f}</h1>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Si hay venta procesada, mostrar PDF y Botón Limpiar
            if st.session_state.ultimo_pdf:
                st.success("✅ ¡Venta Exitosa!")
                st.markdown(f"**Ticket #{st.session_state.ultima_venta_id}**")
                
                c_pdf, c_new = st.columns(2)
                c_pdf.download_button(
                    "🖨️ PDF",
                    data=st.session_state.ultimo_pdf,
                    file_name=f"Venta_{st.session_state.ultima_venta_id}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                if c_new.button("🔄 Nueva", use_container_width=True):
                    st.session_state.carrito = []
                    st.session_state.cliente_actual = None
                    st.session_state.ultimo_pdf = None
                    st.session_state.ultima_venta_id = None
                    st.rerun()
            
            # Formulario de Pago
            elif st.session_state.carrito:
                with st.form("form_cobro"):
                    st.markdown("#### 💳 Detalles de Pago")
                    
                    tipo_entrega = st.radio("Entrega:", ["Punto de Venta", "Envío a Domicilio"], horizontal=True)
                    
                    direccion_envio = "Local"
                    if st.session_state.cliente_actual:
                         direccion_envio = st.session_state.cliente_actual.get('Direccion', 'Local')
                    
                    if tipo_entrega == "Envío a Domicilio":
                        direccion_envio = st.text_input("Dirección de Entrega", value=str(direccion_envio))

                    metodo = st.selectbox("Método de Pago", ["Efectivo", "Nequi", "DaviPlata", "Bancolombia", "Davivienda", "Tarjeta D/C"])
                    banco_destino = st.selectbox("Cuenta Destino (Interno)", ["Caja General", "Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata"])
                    
                    st.markdown("---")
                    enviar = st.form_submit_button(f"✅ CONFIRMAR Y FACTURAR", type="primary", use_container_width=True)
                
                if enviar:
                    if not st.session_state.cliente_actual:
                        st.error("⚠️ Por favor selecciona un cliente antes de facturar.", icon="⚠️")
                    else:
                        try:
                            # Preparar datos
                            id_venta = datetime.now().strftime("%Y%m%d%H%M%S")
                            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            items_str_list = []
                            for i in st.session_state.carrito:
                                items_str_list.append(f"{i['Nombre_Producto']} (x{i['Cantidad']})")
                            items_str = ", ".join(items_str_list)
                            
                            estado_envio = "Entregado" if tipo_entrega == "Punto de Venta" else "Pendiente"
                            
                            # Guardar en Sheet Ventas
                            datos_venta = [
                                id_venta, fecha, 
                                str(st.session_state.cliente_actual.get('Cedula', '0')), 
                                st.session_state.cliente_actual.get('Nombre', 'Consumidor'),
                                tipo_entrega, direccion_envio, estado_envio,
                                metodo, banco_destino, 
                                total_general, items_str
                            ]
                            
                            if escribir_fila(ws_ven, datos_venta):
                                # Descontar Inventario
                                actualizar_stock(ws_inv, st.session_state.carrito)
                                
                                # Generar PDF
                                cliente_pdf_data = {
                                    "ID": id_venta,
                                    "Fecha": fecha,
                                    "Cliente": st.session_state.cliente_actual.get('Nombre', 'Consumidor'),
                                    "Cedula_Cliente": str(st.session_state.cliente_actual.get('Cedula', '')),
                                    "Direccion": direccion_envio,
                                    "Mascota": st.session_state.cliente_actual.get('Mascota', ''),
                                    "Total": total_general,
                                    "Metodo": metodo
                                }
                                
                                pdf_bytes = generar_pdf_html(cliente_pdf_data, st.session_state.carrito)
                                st.session_state.ultimo_pdf = pdf_bytes
                                st.session_state.ultima_venta_id = id_venta
                                st.rerun()
                            else:
                                st.error("Error al guardar la venta en la base de datos.")
                        except Exception as e:
                            st.error(f"Error procesando la venta: {e}")

def tab_clientes(ws_cli):
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>👥</span> Gestión de Clientes (CRM)", unsafe_allow_html=True)
    
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
    
    st.markdown("---")
    st.markdown("#### Base de Datos de Clientes")
    df = leer_datos(ws_cli)
    st.dataframe(df, use_container_width=True)

def tab_gestion_capital(ws_cap, ws_gas):
    st.markdown(f"### <span style='color:{COLOR_ACENTO}'>💰</span> Inversión y Gastos (Nexus Pro)", unsafe_allow_html=True)

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

            if st.form_submit_button("🔴 Registrar Gasto", type="primary"):
                if monto > 0:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    datos = [ts, str(fecha_gasto), tipo_gasto, categoria, descripcion, monto, "N/A", origen]
                    if escribir_fila(ws_gas, datos):
                        st.toast("Gasto registrado correctamente.", icon="📉")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("El monto debe ser mayor a 0.")

    # --- TAB INVERSIONES ---
    with tab2:
        st.markdown("#### Entrada de Dinero (Inversión)")
        st.caption("Capital inicial o inyecciones de socios.")
        
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

                if st.form_submit_button("🔵 Registrar Inversión", type="primary"):
                    if monto_inv > 0:
                        id_cap = datetime.now().strftime("%Y%m%d%H%M")
                        datos_cap = [id_cap, str(fecha_inv), tipo_inv, monto_inv, destino, desc_inv]
                        if escribir_fila(ws_cap, datos_cap):
                            st.toast(f"Inversión de ${monto_inv:,.0f} registrada.", icon="📈")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("El monto debe ser positivo.")

def tab_cuadre_diario(ws_ven, ws_gas, ws_cap):
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>⚖️</span> Cuadre de Caja Diario", unsafe_allow_html=True)

    col_fecha, col_base = st.columns(2)
    fecha_analisis = col_fecha.date_input("📅 Fecha de Cuadre", value=date.today())
    base_caja = col_base.number_input("🏦 Base de Caja (Dinero inicial)", value=200000.0, step=1000.0)
    
    # Cargar datos y filtrar
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)
    
    # Convertir fechas
    if not df_v.empty: df_v['Fecha_Dt'] = df_v['Fecha'].dt.date
    if not df_g.empty: df_g['Fecha_Dt'] = df_g['Fecha'].dt.date

    v_dia = df_v[df_v['Fecha_Dt'] == fecha_analisis] if not df_v.empty else pd.DataFrame(columns=['Total', 'Metodo', 'Banco_Destino'])
    g_dia = df_g[df_g['Fecha_Dt'] == fecha_analisis] if not df_g.empty else pd.DataFrame(columns=['Monto', 'Banco_Origen'])

    st.markdown("---")

    # --- SECCIÓN 1: CUADRE DE CAJA FÍSICA (EFECTIVO) ---
    st.subheader("1. Cuadre de Efectivo")
    
    # Cálculos Efectivo
    ventas_efectivo = v_dia[v_dia['Metodo_Pago'] == 'Efectivo']['Total'].sum()
    gastos_efectivo = g_dia[g_dia['Banco_Origen'].isin(['Caja General', 'Caja Menor', 'Efectivo'])]['Monto'].sum()
    teorico_caja = base_caja + ventas_efectivo - gastos_efectivo

    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("Base Inicial", f"${base_caja:,.0f}")
    col_res2.metric("Ventas Efectivo", f"${ventas_efectivo:,.0f}")
    col_res3.metric("Gastos Efectivo", f"${gastos_efectivo:,.0f}")

    st.markdown(f"<h3 style='text-align:center; color:{COLOR_PRIMARIO}'>💰 DEBE HABER EN CAJÓN: ${teorico_caja:,.0f}</h3>", unsafe_allow_html=True)
    
    # Auditoría
    with st.container(border=True):
        st.markdown("**Auditoría de Cierre:**")
        real_caja = st.number_input("Dinero contado real:", min_value=0.0, step=100.0, format="%.0f")
        
        diferencia = real_caja - teorico_caja
        
        if real_caja > 0:
            if abs(diferencia) < 100:
                st.success(f"✅ ¡CUADRE PERFECTO! Diferencia: ${diferencia:,.0f}")
            elif diferencia > 0:
                st.warning(f"⚠️ Sobra dinero: ${diferencia:,.0f}")
            else:
                st.error(f"🚨 Faltante de dinero: ${diferencia:,.0f}")

    st.markdown("---")

    # --- SECCIÓN 2: CUADRE DIGITAL (BANCOS) ---
    st.subheader("2. Cuadre Digital (Apps/Bancos)")

    medios_digitales = ["Nequi", "DaviPlata", "Bancolombia", "Davivienda", "Tarjeta D/C"]
    
    datos_digitales = []
    total_digital = 0
    
    for medio in medios_digitales:
        mask = v_dia['Metodo_Pago'].astype(str).str.contains(medio, case=False) | v_dia['Banco_Destino'].astype(str).str.contains(medio, case=False)
        total_medio = v_dia[mask]['Total'].sum()
        
        if total_medio > 0:
            datos_digitales.append({"Medio": medio, "Total Venta": total_medio})
            total_digital += total_medio
            
    if datos_digitales:
        col_graf, col_tabla = st.columns([1, 1])
        with col_tabla:
            st.dataframe(pd.DataFrame(datos_digitales), hide_index=True, use_container_width=True)
            st.metric("Total Digital Esperado", f"${total_digital:,.0f}")
        with col_graf:
            fig = px.pie(datos_digitales, names='Medio', values='Total Venta', title='Ingresos Digitales', hole=0.5,
                         color_discrete_sequence=[COLOR_PRIMARIO, COLOR_ACENTO, COLOR_SECUNDARIO, "#2c3e50"])
            fig.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hubo ventas digitales hoy.")

def tab_finanzas_pro(ws_ven, ws_gas, ws_cap):
    st.markdown(f"## <span style='color:{COLOR_PRIMARIO}'>📊</span> Dashboard Financiero Nexus Pro", unsafe_allow_html=True)
    st.caption("Análisis de resultados y métricas clave.")

    # --- FILTROS GLOBALES ---
    with st.container(border=True):
        col_f1, col_f2, col_btn = st.columns([1, 1, 1])
        f_inicio = col_f1.date_input("Desde", value=date.today().replace(day=1))
        f_fin = col_f2.date_input("Hasta", value=date.today())
        
        # Cargar Data
        df_v = leer_datos(ws_ven)
        df_g = leer_datos(ws_gas)
        df_c = leer_datos(ws_cap)

        # Botón Exportar Excel
        with col_btn:
            st.write("") 
            st.write("") 
            if st.button("📥 Descargar Reporte Excel", type="primary"):
                excel_file = generar_excel_financiero(df_v, df_g, df_c, f_inicio, f_fin)
                if excel_file:
                    st.download_button(
                        label="📄 Guardar Excel",
                        data=excel_file,
                        file_name=f"NexusPro_Finanzas_{f_inicio}_{f_fin}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    # Procesar Fechas
    if not df_v.empty: df_v['Fecha_Dt'] = df_v['Fecha'].dt.date
    if not df_g.empty: df_g['Fecha_Dt'] = df_g['Fecha'].dt.date
    if not df_c.empty: df_c['Fecha_Dt'] = df_c['Fecha'].dt.date

    # Filtrar Rango Actual
    v_rango = df_v[(df_v['Fecha_Dt'] >= f_inicio) & (df_v['Fecha_Dt'] <= f_fin)] if not df_v.empty else pd.DataFrame()
    g_rango = df_g[(df_g['Fecha_Dt'] >= f_inicio) & (df_g['Fecha_Dt'] <= f_fin)] if not df_g.empty else pd.DataFrame()

    # --- CÁLCULOS KPI AVANZADOS ---
    ingresos = v_rango['Total'].sum() if not v_rango.empty else 0
    transacciones = len(v_rango)
    ticket_promedio = (ingresos / transacciones) if transacciones > 0 else 0
    
    costos_directos = 0 
    gastos_operativos = 0 
    
    if not g_rango.empty:
        mask_costo = g_rango['Categoria'].isin(['Compra de Mercancía', 'Costo de Venta'])
        costos_directos = g_rango[mask_costo]['Monto'].sum()
        gastos_operativos = g_rango[~mask_costo]['Monto'].sum()

    utilidad_bruta = ingresos - costos_directos
    utilidad_neta = utilidad_bruta - gastos_operativos
    margen_neto = (utilidad_neta / ingresos * 100) if ingresos > 0 else 0

    # Punto de Equilibrio (Simplified)
    punto_equilibrio = gastos_operativos * 1.5 

    # --- VISUALIZACIÓN DE KPIs ---
    st.markdown("### 1. Indicadores Clave (KPIs)")
    k1, k2, k3, k4, k5 = st.columns(5)
    
    k1.metric("Ventas Totales", f"${ingresos:,.0f}", help="Ingreso bruto")
    k2.metric("Utilidad Neta", f"${utilidad_neta:,.0f}", delta=f"{margen_neto:.1f}% Margen")
    k3.metric("Ticket Promedio", f"${ticket_promedio:,.0f}")
    k4.metric("Costos Mercancía", f"${costos_directos:,.0f}", delta="-Costo", delta_color="inverse")
    k5.metric("Gastos Operativos", f"${gastos_operativos:,.0f}", delta="-Gasto", delta_color="inverse")

    st.markdown("---")

    # --- GRÁFICOS INTERACTIVOS (PLOTLY - NUEVOS COLORES) ---
    col_g1, col_g2 = st.columns([2, 1])

    # Gráfico 1: Evolución de Ventas Diarias
    with col_g1:
        st.subheader("📈 Tendencia de Ventas")
        if not v_rango.empty:
            v_diaria = v_rango.groupby('Fecha_Dt')['Total'].sum().reset_index()
            fig_line = px.line(v_diaria, x='Fecha_Dt', y='Total', markers=True, 
                               line_shape='spline', render_mode='svg')
            fig_line.update_traces(line_color=COLOR_PRIMARIO, line_width=4, marker_color=COLOR_ACENTO)
            fig_line.update_layout(xaxis_title="Fecha", yaxis_title="Venta ($)", height=350)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Sin datos para graficar.")

    # Gráfico 2: Estructura de Gastos (Sunburst o Donut)
    with col_g2:
        st.subheader("💸 Gastos")
        if not g_rango.empty:
            fig_pie = px.pie(g_rango, values='Monto', names='Categoria', hole=0.4,
                             color_discrete_sequence=[COLOR_ACENTO, COLOR_PRIMARIO, COLOR_SECUNDARIO, "#95a5a6"])
            fig_pie.update_layout(height=350, showlegend=False)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sin gastos registrados.")

    col_g3, col_g4 = st.columns(2)
    
    # Gráfico 3: Top Productos Vendidos
    with col_g3:
        st.subheader("🏆 Top Productos")
        if not v_rango.empty:
            items_list = []
            for idx, row in v_rango.iterrows():
                try:
                    items_str = row['Items'] 
                    parts = items_str.split(", ")
                    for p in parts:
                        nombre = p.split(" (x")[0]
                        items_list.append(nombre)
                except: pass
            
            if items_list:
                df_top = pd.DataFrame(items_list, columns=['Producto']).value_counts().reset_index(name='Cantidad').head(7)
                fig_bar = px.bar(df_top, x='Cantidad', y='Producto', orientation='h', text='Cantidad')
                fig_bar.update_traces(marker_color=COLOR_PRIMARIO, textposition='outside')
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=300)
                st.plotly_chart(fig_bar, use_container_width=True)

    # Gráfico 4: Análisis de Punto de Equilibrio
    with col_g4:
        st.subheader("⚖️ Salud Financiera")
        st.markdown(f"""
        **Punto de Equilibrio Estimado:** :blue[${punto_equilibrio:,.0f}]
        """)
        
        delta_pe = ingresos - punto_equilibrio
        pct_cubierto = (ingresos / punto_equilibrio * 100) if punto_equilibrio > 0 else 100
        
        st.progress(min(int(pct_cubierto), 100))
        if delta_pe > 0:
            st.success(f"¡Zona de GANANCIA! Superávit: ${delta_pe:,.0f}")
        else:
            st.warning(f"Zona de RIESGO. Faltan ${abs(delta_pe):,.0f}")

    # --- ANÁLISIS ROI ---
    st.markdown("---")
    st.subheader("🏦 Estado de Inversión (Histórico)")
    
    total_invertido = df_c['Monto'].sum() if not df_c.empty else 0
    h_ventas = df_v['Total'].sum() if not df_v.empty else 0
    h_gastos = df_g['Monto'].sum() if not df_g.empty else 0
    utilidad_historica = h_ventas - h_gastos
    
    roi = (utilidad_historica / total_invertido * 100) if total_invertido > 0 else 0
    
    c_roi1, c_roi2 = st.columns([1, 2])
    with c_roi1:
        st.metric("Total Capital Invertido", f"${total_invertido:,.0f}")
        st.metric("ROI (Retorno)", f"{roi:.1f}%")
    
    with c_roi2:
        fig_waterfall = go.Figure(go.Waterfall(
            name = "Flujo", orientation = "v",
            measure = ["relative", "relative", "total"],
            x = ["Inversión", "Utilidad Acumulada", "Valor Actual"],
            textposition = "outside",
            text = [f"${total_invertido/1e6:.1f}M", f"${utilidad_historica/1e6:.1f}M", f"${(total_invertido+utilidad_historica)/1e6:.1f}M"],
            y = [total_invertido, utilidad_historica, 0],
            connector = {"line":{"color":"#333"}},
            decreasing = {"marker":{"color":COLOR_ACENTO}},
            increasing = {"marker":{"color":COLOR_PRIMARIO}},
            totals = {"marker":{"color":COLOR_SECUNDARIO}}
        ))
        fig_waterfall.update_layout(title = "Evolución del Capital", height=300)
        st.plotly_chart(fig_waterfall, use_container_width=True)


# --- MAIN ---

def main():
    configurar_pagina()
    
    # Sidebar Estilizado Nexus Pro
    with st.sidebar:
        # Título y Branding
        st.markdown(f"<h1 style='color:{COLOR_PRIMARIO}; text-align: center;'>Nexus Pro</h1>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='color:{COLOR_TEXTO}; text-align: center; margin-top: -20px;'>Bigotes y Patitas</h4>", unsafe_allow_html=True)
        st.markdown(f"<center><span style='background-color:{COLOR_ACENTO}; color:white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;'>v5.0 PRO</span></center>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        opcion = st.radio("Menú Principal", 
            ["Punto de Venta", "Gestión de Clientes", "Inversión y Gastos", "Cuadre Diario (Caja)", "Finanzas & Resultados"],
            index=0
        )
        st.markdown("---")
        with st.container(border=True):
            st.caption("💡 Tip: Realiza el cuadre diario al cerrar el local.")

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
