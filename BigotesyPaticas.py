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
import xlsxwriter
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTILOS (NEXUS PRO THEME) ---

# Paleta de Colores
COLOR_PRIMARIO = "#187f77"      # Cian Oscuro (Teal)
COLOR_SECUNDARIO = "#125e58"    # Variante más oscura
COLOR_ACENTO = "#f5a641"        # Naranja (Alertas)
COLOR_FONDO = "#f8f9fa"         # Fondo gris muy claro
COLOR_TEXTO = "#262730"
COLOR_BLANCO = "#ffffff"
COLOR_WHATSAPP = "#25D366"      # Verde oficial WhatsApp

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

        /* Tarjetas */
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

        /* Botones */
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

        .stButton button[type="secondary"] {{
            border: 2px solid {COLOR_PRIMARIO};
            color: {COLOR_PRIMARIO};
            border-radius: 8px;
        }}

        /* Botón WhatsApp */
        .whatsapp-btn {{
            display: inline-block;
            background-color: {COLOR_WHATSAPP};
            color: white !important;
            padding: 12px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            text-align: center;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: background-color 0.3s;
            width: 100%;
            margin-top: 10px;
            margin-bottom: 20px;
        }}
        .whatsapp-btn:hover {{
            background-color: #1ebc57;
            text-decoration: none;
            box-shadow: 0 6px 8px rgba(0,0,0,0.15);
        }}

        /* Inputs */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
            border-radius: 8px;
            border-color: #e0e0e0;
        }}
        .stTextInput input:focus, .stNumberInput input:focus {{
            border-color: {COLOR_PRIMARIO};
            box-shadow: 0 0 0 1px {COLOR_PRIMARIO};
        }}

        /* Tabs */
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

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: {COLOR_BLANCO};
            border-right: 1px solid #eee;
        }}
        
        /* Tarjetas Logística */
        .delivery-card {{
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #eee;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 15px;
        }}
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
        
        try:
            ws_cap = sh.worksheet("Capital")
        except:
            st.error("⚠️ Falta la hoja 'Capital'. Créala para gestionar inversiones.")
            ws_cap = None

        try:
            ws_cie = sh.worksheet("Cierres")
        except:
            st.error("⚠️ CRÍTICO: Falta la hoja 'Cierres'. Créala con columnas: Fecha, Hora, Base_Inicial, Ventas_Efectivo, Gastos_Efectivo, Retiros_Bancos, Total_Teorico, Total_Real, Diferencia, Notas")
            ws_cie = None
        
        return ws_inv, ws_cli, ws_ven, ws_gas, ws_cap, ws_cie
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None, None, None, None, None, None

def sanitizar_dato(dato):
    if isinstance(dato, (np.int64, np.int32, np.integer)): return int(dato)
    elif isinstance(dato, (np.float64, np.float32, np.floating)): return float(dato)
    return dato

def leer_datos(ws):
    if ws is None: return pd.DataFrame()
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # Limpieza de columnas numéricas clave
        # 'Costo' es nuevo, 'Costo_Total' es nuevo para calcular márgenes
        cols_numericas = ['Precio', 'Stock', 'Monto', 'Total', 'Costo', 'Costo_Total', 'Base_Inicial', 'Ventas_Efectivo', 'Gastos_Efectivo', 'Total_Real']
        
        for col in cols_numericas:
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
        all_values = ws_inv.get_all_values()
        id_a_fila = {}
        for idx, row in enumerate(all_values):
            if idx == 0: continue 
            p_id = str(row[0]).strip() 
            id_a_fila[p_id] = idx + 1 
            
        for item in items:
            id_buscado = str(item['ID_Producto']).strip()
            if id_buscado in id_a_fila:
                fila_num = id_a_fila[id_buscado]
                stock_actual_val = ws_inv.cell(fila_num, 4).value # Leer columna 4 (Stock)
                try:
                    stock_actual = int(float(stock_actual_val)) if stock_actual_val else 0
                except:
                    stock_actual = 0
                
                nuevo_stock = max(0, stock_actual - int(item['Cantidad']))
                ws_inv.update_cell(fila_num, 4, nuevo_stock) 
                
        return True
    except Exception as e:
        st.error(f"Error actualizando stock: {e}")
        return False

def actualizar_estado_envio(ws_ven, id_venta, nuevo_estado):
    try:
        cell = ws_ven.find(str(id_venta))
        if cell:
            headers = ws_ven.row_values(1)
            try:
                col_index = headers.index("Estado_Envio") + 1
            except ValueError:
                col_index = 7
            
            ws_ven.update_cell(cell.row, col_index, nuevo_estado)
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error actualizando estado del envío: {e}")
        return False

# --- FUNCIÓN PARA GENERAR MENSAJE DE WHATSAPP ---
def generar_mensaje_whatsapp(nombre_cliente, mascota, tipo_cliente, items_str, total):
    saludo = ""
    cuerpo = ""
    despedida = "¡Muchas gracias y feliz día! 🐾"
    
    if tipo_cliente == "NUEVO":
        saludo = f"¡Hola {nombre_cliente}! 👋 Bienvenido/a a la familia *Bigotes y Patitas*."
        cuerpo = f"Nos emociona mucho que nos hayas elegido para consentir a *{mascota}*. 🥰 Estamos seguros de que le encantará lo que llevas."
    elif tipo_cliente == "REACTIVADO":
        saludo = f"¡Hola {nombre_cliente}! 👋 ¡Qué alegría inmensa tenerte de vuelta!"
        cuerpo = f"Te habíamos extrañado a ti y a *{mascota}* ❤️. Nos hace muy felices que confíes nuevamente en nosotros."
    else: 
        saludo = f"¡Hola de nuevo {nombre_cliente}! 👋"
        cuerpo = f"Qué gusto verte otra vez. 🌟 Gracias por ser un cliente tan especial y seguir eligiendo lo mejor para *{mascota}*."

    resumen = f"\n\n🧾 *Resumen de tu compra:*\n{items_str}\n\n💰 *Total:* ${total:,.0f}"
    mensaje_completo = f"{saludo}\n{cuerpo}{resumen}\n\n{despedida}"
    return urllib.parse.quote(mensaje_completo)

# --- 3. GENERADOR DE PDF Y EXCEL ---

def generar_pdf_html(venta_data, items):
    try:
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
             <p><strong>Entrega:</strong> {{{{ tipo_entrega }}}} ({{{{ estado }}}})</p>
             <p><strong>Dirección:</strong> {{{{ cliente_direccion }}}}</p>
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

def generar_excel_financiero(df_v, df_g, df_c, f_inicio, f_fin):
    output = BytesIO()
    try:
        # Cálculos de Ganancia Real
        total_ingresos = df_v['Total'].sum() if not df_v.empty else 0
        total_costo_venta = df_v['Costo_Total'].sum() if not df_v.empty and 'Costo_Total' in df_v.columns else 0
        
        utilidad_bruta = total_ingresos - total_costo_venta
        
        total_gastos_op = df_g['Monto'].sum() if not df_g.empty else 0
        
        utilidad_neta = utilidad_bruta - total_gastos_op
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            fmt_header = workbook.add_format({
                'bold': True, 'font_color': 'white', 'bg_color': COLOR_PRIMARIO, 
                'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            fmt_title = workbook.add_format({
                'bold': True, 'font_size': 14, 'font_color': COLOR_PRIMARIO, 'bottom': 2
            })
            fmt_kpi_label = workbook.add_format({'bold': True, 'bg_color': '#f2f2f2', 'border': 1})
            fmt_kpi_val = workbook.add_format({'num_format': '$#,##0', 'bold': True, 'font_size': 12, 'border': 1})

            # --- HOJA 1: RESUMEN EJECUTIVO ---
            ws_resumen = workbook.add_worksheet("Resultados")
            ws_resumen.set_column('B:C', 25)
            ws_resumen.write('B2', f"Reporte Financiero Nexus Pro", fmt_title)
            ws_resumen.write('B3', f"Periodo: {f_inicio} al {f_fin}")

            ws_resumen.write('B5', "Concepto", fmt_header)
            ws_resumen.write('C5', "Valor", fmt_header)

            kpis = [
                ("Ventas Totales", total_ingresos),
                ("(-) Costo de Mercancía (COGS)", total_costo_venta),
                ("(=) Utilidad Bruta", utilidad_bruta),
                ("(-) Gastos Operativos", total_gastos_op),
                ("(=) Utilidad Neta Real", utilidad_neta)
            ]

            row = 5
            for label, value in kpis:
                ws_resumen.write(row, 1, label, fmt_kpi_label)
                ws_resumen.write(row, 2, value, fmt_kpi_val)
                row += 1

            # --- HOJA 2: VENTAS CON COSTO ---
            if not df_v.empty:
                df_v_export = df_v.copy()
                if 'Fecha' in df_v_export.columns:
                    df_v_export['Fecha'] = df_v_export['Fecha'].astype(str)
                df_v_export.to_excel(writer, sheet_name='Detalle Ventas', index=False)

            # --- HOJA 3: GASTOS ---
            if not df_g.empty:
                df_g_export = df_g.copy()
                if 'Fecha' in df_g_export.columns:
                    df_g_export['Fecha'] = df_g_export['Fecha'].astype(str)
                df_g_export.to_excel(writer, sheet_name='Detalle Gastos', index=False)

        return output.getvalue()
    except Exception as e:
        st.error(f"Error generando Excel: {e}")
        return None

# --- 4. MÓDULOS DE NEGOCIO ---

def tab_punto_venta(ws_inv, ws_cli, ws_ven):
    st.markdown(f"### <span style='color:{COLOR_ACENTO}'>🛒</span> Nexus Pro POS", unsafe_allow_html=True)
    st.caption("Punto de Venta - Bigotes y Patitas")
    
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None
    if 'whatsapp_link' not in st.session_state: st.session_state.whatsapp_link = None

    col_izq, col_der = st.columns([1.6, 1])

    with col_izq:
        # Selección de Cliente
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
        
        # Buscador de Productos
        st.markdown("#### 📦 Catálogo")
        df_inv = leer_datos(ws_inv)
        
        if not df_inv.empty:
            df_inv['ID_Producto'] = df_inv['ID_Producto'].astype(str)
            prod_lista = df_inv.apply(lambda x: f"{x.get('Nombre', 'N/A')} | Stock: {x.get('Stock', 0)} | ${x.get('Precio', 0):,.0f} | ID:{x.get('ID_Producto', '')}", axis=1).tolist()
            
            sel_prod_str = st.selectbox("Escriba para buscar producto...", [""] + prod_lista)
            
            col_add_btn, col_dummy = st.columns([1, 2])
            if col_add_btn.button("➕ Agregar al Carrito", type="primary", use_container_width=True):
                if sel_prod_str:
                    try:
                        id_p = sel_prod_str.split("ID:")[1]
                        info_p = df_inv[df_inv['ID_Producto'] == id_p].iloc[0]
                        
                        # Manejo de Costo (Si no existe columna Costo, asume 0)
                        costo_unitario = float(info_p.get('Costo', 0))
                        
                        existe = False
                        for item in st.session_state.carrito:
                            if str(item['ID_Producto']) == str(info_p['ID_Producto']):
                                item['Cantidad'] += 1
                                item['Subtotal'] = item['Cantidad'] * item['Precio']
                                item['Costo_Total_Item'] = item['Cantidad'] * costo_unitario # Recalcular costo total item
                                existe = True
                                item['Eliminar'] = False
                                break
                        
                        if not existe:
                            nuevo_item = {
                                "ID_Producto": str(info_p['ID_Producto']),
                                "Nombre_Producto": info_p['Nombre'],
                                "Precio": float(info_p['Precio']),
                                "Costo_Unitario": costo_unitario,
                                "Cantidad": 1,
                                "Subtotal": float(info_p['Precio']),
                                "Costo_Total_Item": costo_unitario, # Inicial
                                "Eliminar": False 
                            }
                            st.session_state.carrito.append(nuevo_item)
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Error al agregar: {e}")

        # TABLA CARRITO
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
            # Ocultamos columnas de costos al usuario, son internas
            cols_visibles = ["Nombre_Producto", "Cantidad", "Precio", "Subtotal", "Eliminar"]

            edited_df = st.data_editor(
                df_carrito[cols_visibles], # Solo mostrar visibles
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                key="editor_carrito",
                num_rows="dynamic"
            )

            # Sincronizar cambios y recálculos ocultos
            items_actualizados = []
            for index, row in edited_df.iterrows():
                if not row['Eliminar']:
                    # Recuperar datos ocultos del estado original (como el Costo Unitario)
                    original_item = st.session_state.carrito[index]
                    
                    nuevo_subtotal = row['Cantidad'] * row['Precio']
                    nuevo_costo_total = row['Cantidad'] * original_item['Costo_Unitario']
                    
                    item_dict = row.to_dict()
                    item_dict['ID_Producto'] = original_item['ID_Producto']
                    item_dict['Costo_Unitario'] = original_item['Costo_Unitario']
                    item_dict['Costo_Total_Item'] = nuevo_costo_total
                    item_dict['Subtotal'] = nuevo_subtotal
                    item_dict['Eliminar'] = False
                    items_actualizados.append(item_dict)

            st.session_state.carrito = items_actualizados
            
            total_general = sum(item['Subtotal'] for item in st.session_state.carrito)
            total_costo_venta = sum(item['Costo_Total_Item'] for item in st.session_state.carrito)

        else:
            st.info("El carrito está vacío.")
            total_general = 0
            total_costo_venta = 0

    # COLUMNA DERECHA: PAGO
    with col_der:
        with st.container(border=True):
            st.markdown(f"### <span style='color:{COLOR_ACENTO}'>🧾</span> Total", unsafe_allow_html=True)
            st.markdown(f"<h1 style='text-align: center; color: {COLOR_PRIMARIO}; font-size: 3em;'>${total_general:,.0f}</h1>", unsafe_allow_html=True)
            st.markdown("---")
            
            if st.session_state.ultimo_pdf:
                st.success("✅ ¡Venta Exitosa!")
                st.markdown(f"**Ticket #{st.session_state.ultima_venta_id}**")
                
                if st.session_state.whatsapp_link:
                    link_wa = f"https://wa.me/{st.session_state.whatsapp_link['telefono']}?text={st.session_state.whatsapp_link['mensaje']}"
                    st.markdown(f"""<a href="{link_wa}" target="_blank" class="whatsapp-btn">📲 WhatsApp</a>""", unsafe_allow_html=True)

                c_pdf, c_new = st.columns(2)
                c_pdf.download_button("🖨️ PDF", data=st.session_state.ultimo_pdf, file_name=f"Venta_{st.session_state.ultima_venta_id}.pdf", mime="application/pdf", type="primary", use_container_width=True)
                if c_new.button("🔄 Nueva", use_container_width=True):
                    st.session_state.carrito = []
                    st.session_state.cliente_actual = None
                    st.session_state.ultimo_pdf = None
                    st.session_state.ultima_venta_id = None
                    st.session_state.whatsapp_link = None
                    st.rerun()
            
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
                    
                    enviar = st.form_submit_button(f"✅ CONFIRMAR Y FACTURAR", type="primary", use_container_width=True)
                
                if enviar:
                    if not st.session_state.cliente_actual:
                        st.error("⚠️ Por favor selecciona un cliente antes de facturar.", icon="⚠️")
                    else:
                        try:
                            id_venta = datetime.now().strftime("%Y%m%d%H%M%S")
                            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            items_str_list = [f"{i['Nombre_Producto']} (x{i['Cantidad']})" for i in st.session_state.carrito]
                            items_str = ", ".join(items_str_list)
                            estado_envio = "Entregado" if tipo_entrega == "Punto de Venta" else "Pendiente"
                            
                            # Guardar en Sheet Ventas (AHORA INCLUYE COSTO_TOTAL AL FINAL)
                            datos_venta = [
                                id_venta, fecha, 
                                str(st.session_state.cliente_actual.get('Cedula', '0')), 
                                st.session_state.cliente_actual.get('Nombre', 'Consumidor'),
                                tipo_entrega, direccion_envio, estado_envio,
                                metodo, banco_destino, 
                                total_general, items_str,
                                total_costo_venta # <--- NUEVO CAMPO IMPORTANTE
                            ]
                            
                            # Generar Link WhatsApp
                            telefono = str(st.session_state.cliente_actual.get('Telefono', ''))
                            telefono = ''.join(filter(str.isdigit, telefono))
                            if telefono and not telefono.startswith('57') and len(telefono) == 10: telefono = '57' + telefono
                            
                            items_wa = "\n".join([f"• {i['Nombre_Producto']} x{i['Cantidad']}" for i in st.session_state.carrito])
                            
                            mensaje_wa = generar_mensaje_whatsapp(
                                st.session_state.cliente_actual.get('Nombre', 'Cliente'),
                                st.session_state.cliente_actual.get('Mascota', 'tu peludito'),
                                "RECURRENTE", items_wa, total_general
                            )
                            st.session_state.whatsapp_link = {"telefono": telefono, "mensaje": mensaje_wa}

                            if escribir_fila(ws_ven, datos_venta):
                                actualizar_stock(ws_inv, st.session_state.carrito)
                                
                                cliente_pdf_data = {
                                    "ID": id_venta, "Fecha": fecha,
                                    "Cliente": st.session_state.cliente_actual.get('Nombre', 'Consumidor'),
                                    "Cedula_Cliente": str(st.session_state.cliente_actual.get('Cedula', '')),
                                    "Direccion": direccion_envio, "Mascota": st.session_state.cliente_actual.get('Mascota', ''),
                                    "Total": total_general, "Metodo": metodo, "Tipo_Entrega": tipo_entrega
                                }
                                pdf_bytes = generar_pdf_html(cliente_pdf_data, st.session_state.carrito)
                                st.session_state.ultimo_pdf = pdf_bytes
                                st.session_state.ultima_venta_id = id_venta
                                if estado_envio == "Pendiente": st.toast("Pedido enviado a Domicilios", icon="🛵")
                                st.rerun()
                            else:
                                st.error("Error al guardar venta.")
                        except Exception as e:
                            st.error(f"Error procesando venta: {e}")

def tab_logistica(ws_ven):
    st.markdown(f"### <span style='color:{COLOR_ACENTO}'>🛵</span> Gestión de Despachos", unsafe_allow_html=True)
    df = leer_datos(ws_ven)
    if df.empty: return

    if 'Tipo_Entrega' in df.columns and 'Estado_Envio' in df.columns:
        mask_pendientes = (df['Tipo_Entrega'] == 'Envío a Domicilio') & (df['Estado_Envio'] == 'Pendiente')
        pendientes = df[mask_pendientes].copy()
    else: return

    if pendientes.empty:
        st.success("✅ No hay domicilios pendientes.")
    else:
        for index, row in pendientes.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="delivery-card">
                    <h4 style="margin:0; color:{COLOR_PRIMARIO};">Pedido #{row.get('ID', 'N/A')}</h4>
                    <p>{row.get('Cliente', 'N/A')} - {row.get('Direccion', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"🚀 Enviado #{row.get('ID')}", key=f"btn_{index}"):
                    actualizar_estado_envio(ws_ven, row.get('ID', ''), "Enviado")
                    st.rerun()

def tab_clientes(ws_cli):
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>👥</span> Gestión de Clientes", unsafe_allow_html=True)
    with st.form("form_cliente"):
        col1, col2 = st.columns(2)
        with col1:
            cedula = st.text_input("Cédula / ID *")
            nombre = st.text_input("Nombre Completo *")
            telefono = st.text_input("Teléfono *")
            email = st.text_input("Correo")
        with col2:
            direccion = st.text_input("Dirección")
            nombre_mascota = st.text_input("Nombre Mascota *")
            tipo_mascota = st.selectbox("Tipo", ["Perro", "Gato", "Otro"])
            fecha_nac = st.date_input("Cumpleaños Mascota", value=None)

        if st.form_submit_button("💾 Guardar Cliente", type="primary"):
            if cedula and nombre and nombre_mascota:
                datos = [cedula, nombre, telefono, email, direccion, nombre_mascota, tipo_mascota, str(fecha_nac), str(date.today())]
                if escribir_fila(ws_cli, datos):
                    st.success("Cliente guardado.")
                    
                    # Link de bienvenida Angela
                    msg_bienvenida = f"¡Hola {nombre}! 👋\nBienvenido a *Bigotes y Patitas* 🐾. Soy Angela, guardame como contacto para tus domicilios: 320 687 6633"
                    tel_clean = ''.join(filter(str.isdigit, str(telefono)))
                    if len(tel_clean) == 10: tel_clean = "57" + tel_clean
                    link = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(msg_bienvenida)}"
                    st.markdown(f'<a href="{link}" target="_blank" class="whatsapp-btn">📲 Enviar Bienvenida</a>', unsafe_allow_html=True)
            else:
                st.warning("Completa los campos obligatorios.")
    
    st.markdown("---")
    df = leer_datos(ws_cli)
    st.dataframe(df, use_container_width=True)

def tab_gestion_capital(ws_cap, ws_gas):
    st.markdown(f"### <span style='color:{COLOR_ACENTO}'>💰</span> Inversión y Gastos", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📉 Gastos Operativos", "💸 Pago Proveedores (Inv)", "📈 Capital"])

    # GASTOS OPERATIVOS
    with tab1:
        st.caption("Gastos generales: Arriendo, Servicios, Nómina, Aseo...")
        with st.form("form_gasto"):
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("Concepto", ["Arriendo", "Nómina", "Servicios", "Publicidad", "Transporte", "Insumos Aseo", "Otros"])
            desc = c1.text_input("Detalle")
            monto = c2.number_input("Monto ($)", min_value=0.0)
            origen = c2.selectbox("Origen del Dinero", ["Caja General", "Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata"])
            fecha = c2.date_input("Fecha", value=date.today())
            
            if st.form_submit_button("🔴 Registrar Gasto"):
                if monto > 0:
                    datos = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(fecha), "Gasto Operativo", tipo, desc, monto, "N/A", origen]
                    if escribir_fila(ws_gas, datos): st.success("Registrado.")

    # PAGO PROVEEDORES
    with tab2:
        st.caption("Compras de Mercancía. Esto NO es gasto operativo, es Costo de Venta.")
        with st.form("form_prov"):
            c1, c2 = st.columns(2)
            prov = c1.text_input("Proveedor")
            fact = c1.text_input("Factura #")
            nota = c1.text_area("Detalle Compra")
            monto = c2.number_input("Total Pagado ($)", min_value=0.0)
            origen = c2.selectbox("Método Pago", ["Bancolombia Ahorros", "Davivienda", "Nequi", "Efectivo", "Caja General"])
            fecha = c2.date_input("Fecha", value=date.today())

            if st.form_submit_button("💸 Registrar Pago Proveedor"):
                if monto > 0 and prov:
                    desc = f"[PROV: {prov}] [REF: {fact}] - {nota}"
                    # Importante: Categoría "Compra Inventario"
                    datos = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(fecha), "Costo de Venta", "Compra Inventario", desc, monto, "N/A", origen]
                    if escribir_fila(ws_gas, datos): st.success(f"Pago a {prov} registrado.")

    # CAPITAL
    with tab3:
        if ws_cap:
            with st.form("form_cap"):
                c1, c2 = st.columns(2)
                tipo = c1.selectbox("Tipo", ["Inyección Capital", "Préstamo Socio"])
                monto = c1.number_input("Monto ($)", min_value=0.0)
                dest = c2.selectbox("Entra a:", ["Bancolombia Ahorros", "Caja General"])
                desc = c2.text_input("Socio/Detalle")
                if st.form_submit_button("🔵 Ingresar Capital"):
                    datos = [datetime.now().strftime("%Y%m%d%H%M"), str(date.today()), tipo, monto, dest, desc]
                    escribir_fila(ws_cap, datos)
                    st.success("Capital registrado.")

def tab_cuadre_diario_flujo(ws_ven, ws_gas, ws_cie):
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>⚖️</span> Cuadre Diario de Caja (Flujo Continuo)", unsafe_allow_html=True)
    st.info("Este módulo calcula el efectivo físico basándose en el cierre de ayer.")

    # 1. OBTENER BASE ANTERIOR (Automática)
    df_cierres = leer_datos(ws_cie)
    base_traida = 0.0
    fecha_ultimo_cierre = "Sin registros previos"
    
    if not df_cierres.empty:
        # Asumiendo orden cronológico, tomamos la última fila
        ultimo_cierre = df_cierres.iloc[-1]
        try:
            # La base de hoy es el "Total_Real" de ayer
            base_traida = float(ultimo_cierre['Total_Real'])
            fecha_ultimo_cierre = str(ultimo_cierre['Fecha'])
        except:
            base_traida = 0.0

    # 2. SELECCIONAR FECHA DE HOY
    fecha_hoy = st.date_input("Fecha de Cierre", value=date.today())
    
    st.write(f"**💰 Base Inicial (Viene del cierre del {fecha_ultimo_cierre}):** ${base_traida:,.0f}")
    
    # 3. CALCULAR ENTRADAS Y SALIDAS DE HOY (EFECTIVO SOLAMENTE)
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)

    if not df_v.empty: df_v['Fecha_Dt'] = df_v['Fecha'].dt.date
    if not df_g.empty: df_g['Fecha_Dt'] = df_g['Fecha'].dt.date
    
    # Filtrar solo registros de HOY
    v_hoy = df_v[df_v['Fecha_Dt'] == fecha_hoy] if not df_v.empty else pd.DataFrame()
    g_hoy = df_g[df_g['Fecha_Dt'] == fecha_hoy] if not df_g.empty else pd.DataFrame()
    
    # A. Ventas en Efectivo (+)
    entradas_efectivo = 0.0
    if not v_hoy.empty and 'Metodo_Pago' in v_hoy.columns:
        entradas_efectivo = v_hoy[v_hoy['Metodo_Pago'] == 'Efectivo']['Total'].sum()
    
    # B. Gastos pagados en Efectivo (-) (Incluye pagos a proveedores si salieron de Caja General)
    salidas_gastos_efectivo = 0.0
    if not g_hoy.empty and 'Banco_Origen' in g_hoy.columns:
        # Filtramos por origen "Caja General" o "Efectivo"
        mask_origen = g_hoy['Banco_Origen'].isin(['Caja General', 'Efectivo', 'Caja Menor'])
        salidas_gastos_efectivo = g_hoy[mask_origen]['Monto'].sum()

    # C. Retiros / Consignaciones Bancarias (-)
    # Esto es manual porque es un movimiento físico que haces al cerrar o durante el día
    st.markdown("---")
    st.subheader("🏦 Movimientos de Caja a Bancos (Hoy)")
    st.caption("Si sacaste dinero de la caja para consignar en el banco hoy, ingrésalo aquí para que descuente del efectivo.")
    retiro_bancos = st.number_input("Total Consignado / Retirado de Caja hoy ($)", min_value=0.0, step=1000.0)

    # 4. CÁLCULO TEÓRICO
    # Base + Ventas - Gastos - Retiros
    saldo_teorico = base_traida + entradas_efectivo - salidas_gastos_efectivo - retiro_bancos
    
    # VISUALIZACIÓN DE FLUJO
    st.markdown("#### 🌊 Flujo de Efectivo del Día")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("1. Base Inicial", f"${base_traida:,.0f}")
    col2.metric("2. (+) Ventas Efec.", f"${entradas_efectivo:,.0f}")
    col3.metric("3. (-) Gastos Efec.", f"${salidas_gastos_efectivo:,.0f}")
    col4.metric("4. (-) A Bancos", f"${retiro_bancos:,.0f}")
    col5.metric("= CAJA DEBE TENER", f"${saldo_teorico:,.0f}", delta="Objetivo")

    st.markdown("---")
    
    # 5. CONTEO REAL Y CIERRE
    st.subheader("🔐 Cierre Físico")
    
    with st.form("form_cierre_caja"):
        saldo_real = st.number_input("💵 ¿Cuánto dinero contaste realmente en el cajón?", min_value=0.0, step=100.0)
        notas_cierre = st.text_area("Notas / Observaciones del día")
        
        diferencia = saldo_real - saldo_teorico
        
        # Alerta visual
        if saldo_real > 0:
            if abs(diferencia) < 50:
                st.success(f"✅ CUADRE PERFECTO (Dif: ${diferencia:,.0f})")
            elif diferencia > 0:
                st.info(f"💰 Sobra dinero: ${diferencia:,.0f}")
            else:
                st.error(f"🚨 Faltante: ${diferencia:,.0f}")

        st.markdown("**Al guardar, el 'Saldo Real' se convertirá en la 'Base Inicial' de mañana.**")
        
        if st.form_submit_button("🔒 GUARDAR CIERRE DE CAJA DIARIO", type="primary"):
            # Verificar si ya existe cierre hoy para no duplicar (Opcional, pero recomendado)
            # Aquí permitimos guardar múltiples por si hay correcciones, pero idealmente se hace uno.
            
            datos_cierre = [
                str(fecha_hoy),
                datetime.now().strftime("%H:%M:%S"),
                base_traida,
                entradas_efectivo,
                salidas_gastos_efectivo,
                retiro_bancos,
                saldo_teorico,
                saldo_real,
                diferencia,
                notas_cierre
            ]
            
            if escribir_fila(ws_cie, datos_cierre):
                st.balloons()
                st.success("Cierre guardado exitosamente. ¡Hasta mañana!")
                time.sleep(2)
                st.rerun()

def tab_finanzas_pro(ws_ven, ws_gas, ws_cie):
    st.markdown(f"## <span style='color:{COLOR_PRIMARIO}'>📊</span> Resultados Reales (Ganancia)", unsafe_allow_html=True)

    # Filtros
    c1, c2 = st.columns(2)
    f_inicio = c1.date_input("Desde", value=date.today().replace(day=1))
    f_fin = c2.date_input("Hasta", value=date.today())

    # Carga Data
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)

    if not df_v.empty: df_v['Fecha_Dt'] = df_v['Fecha'].dt.date
    if not df_g.empty: df_g['Fecha_Dt'] = df_g['Fecha'].dt.date

    # Filtrar Rango
    v_rango = df_v[(df_v['Fecha_Dt'] >= f_inicio) & (df_v['Fecha_Dt'] <= f_fin)] if not df_v.empty else pd.DataFrame()
    g_rango = df_g[(df_g['Fecha_Dt'] >= f_inicio) & (df_g['Fecha_Dt'] <= f_fin)] if not df_g.empty else pd.DataFrame()

    # --- CÁLCULOS CRÍTICOS (GANANCIA REAL) ---
    
    # 1. Ingresos Totales (Venta Bruta)
    ingresos = v_rango['Total'].sum() if not v_rango.empty else 0
    
    # 2. Costo de Mercancía Vendida (COGS)
    # Sumamos la columna 'Costo_Total' de las ventas en el rango
    costo_mercancia = v_rango['Costo_Total'].sum() if not v_rango.empty and 'Costo_Total' in v_rango.columns else 0
    
    # 3. Utilidad Bruta
    utilidad_bruta = ingresos - costo_mercancia
    margen_bruto = (utilidad_bruta / ingresos * 100) if ingresos > 0 else 0

    # 4. Gastos Operativos (Filtrar compras de inventario para no duplicar si se analizan aparte)
    # En este modelo, los gastos operativos son todo lo que está en 'Gastos' EXCEPTO lo marcado como Costo de Venta
    # Si quieres restar las compras de inventario del flujo de caja, es una cosa.
    # Pero para GANANCIA (P&L), restamos el costo del producto vendido (ya calculado arriba) y los gastos fijos.
    
    gastos_operativos = 0
    if not g_rango.empty:
        # Excluimos "Compra Inventario" o "Costo de Venta" de los gastos operativos puros, 
        # porque el costo de venta ya lo restamos arriba basado en lo vendido (Accrual basis vs Cash basis).
        # Si prefieres flujo de caja puro: Resta todo lo que salió de la cuenta.
        # Aquí haremos P&L (Estado de Resultados): Venta - Costo Prod Vendido - Gastos Fijos
        
        mask_operativo = ~g_rango['Tipo_Gasto'].isin(['Costo de Venta']) 
        gastos_operativos = g_rango[mask_operativo]['Monto'].sum()

    # 5. Utilidad Neta
    utilidad_neta = utilidad_bruta - gastos_operativos
    margen_neto = (utilidad_neta / ingresos * 100) if ingresos > 0 else 0

    # VISUALIZACIÓN
    st.markdown("### Estado de Resultados")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("1. Ventas", f"${ingresos:,.0f}")
    k2.metric("2. (-) Costo Prod. Vendido", f"${costo_mercancia:,.0f}", help="Costo de inventario de lo que se vendió")
    k3.metric("3. (-) Gastos Operativos", f"${gastos_operativos:,.0f}", help="Arriendos, nómina, servicios (excluye compra inventario)")
    k4.metric("= Utilidad Neta", f"${utilidad_neta:,.0f}", delta=f"{margen_neto:.1f}% Margen")

    st.progress(max(0, min(100, int(margen_neto))))

    # GRÁFICO CASCADA (Waterfall)
    fig = go.Figure(go.Waterfall(
        name = "P&L", orientation = "v",
        measure = ["relative", "relative", "total", "relative", "total"],
        x = ["Ventas", "Costo Mercancía", "Utilidad Bruta", "Gastos Op.", "Utilidad Neta"],
        textposition = "outside",
        text = [f"{ingresos/1e6:.2f}M", f"-{costo_mercancia/1e6:.2f}M", f"{utilidad_bruta/1e6:.2f}M", f"-{gastos_operativos/1e6:.2f}M", f"{utilidad_neta/1e6:.2f}M"],
        y = [ingresos, -costo_mercancia, utilidad_bruta, -gastos_operativos, utilidad_neta],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
        decreasing = {"marker":{"color":COLOR_ACENTO}},
        increasing = {"marker":{"color":COLOR_PRIMARIO}},
        totals = {"marker":{"color":COLOR_SECUNDARIO}}
    ))
    fig.update_layout(title = "Estructura de Ganancia Real", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # BOTÓN EXCEL
    st.markdown("---")
    if st.button("📥 Descargar Reporte Financiero (Excel)"):
        # Necesitamos cargar Capital para pasar al generador
        ws_cap_temp = conectar_google_sheets()[4] # Hack sucio para reusar funcion conexion
        df_c_temp = leer_datos(ws_cap_temp)
        
        excel_data = generar_excel_financiero(v_rango, g_rango, df_c_temp, f_inicio, f_fin)
        if excel_data:
            st.download_button("📄 Clic para guardar", data=excel_data, file_name="Reporte_Financiero.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- MAIN ---

def main():
    configurar_pagina()
    
    with st.sidebar:
        st.markdown(f"<h1 style='color:{COLOR_PRIMARIO}; text-align: center;'>Nexus Pro</h1>", unsafe_allow_html=True)
        st.markdown(f"<center><span style='background-color:{COLOR_ACENTO}; color:white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;'>v7.0 Cuadre Real</span></center>", unsafe_allow_html=True)
        st.markdown("---")
        
        opcion = st.radio("Menú Principal", 
            ["Punto de Venta", "Despachos y Envíos", "Gestión de Clientes", "Inversión y Gastos", "Cuadre Diario (Caja)", "Finanzas & Resultados"],
            index=0
        )
        st.markdown("---")
        with st.container(border=True):
            st.caption("Recuerda llenar el Costo en Inventario para que el cálculo de ganancias sea exacto.")

    ws_inv, ws_cli, ws_ven, ws_gas, ws_cap, ws_cie = conectar_google_sheets()

    if not ws_inv:
        st.warning("🔄 Conectando...")
        return

    if opcion == "Punto de Venta":
        tab_punto_venta(ws_inv, ws_cli, ws_ven)
    elif opcion == "Despachos y Envíos":
        tab_logistica(ws_ven)
    elif opcion == "Gestión de Clientes":
        tab_clientes(ws_cli)
    elif opcion == "Inversión y Gastos":
        tab_gestion_capital(ws_cap, ws_gas)
    elif opcion == "Cuadre Diario (Caja)":
        tab_cuadre_diario_flujo(ws_ven, ws_gas, ws_cie)
    elif opcion == "Finanzas & Resultados":
        tab_finanzas_pro(ws_ven, ws_gas, ws_cie)

if __name__ == "__main__":
    main()
