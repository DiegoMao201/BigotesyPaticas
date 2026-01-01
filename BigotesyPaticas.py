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
import plotly.graph_objects as go
import xlsxwriter
import urllib.parse
import json

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
    
    # CSS Personalizado
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
            ws_cap = None # Opcional

        try:
            ws_cie = sh.worksheet("Cierres")
            if not ws_cie.get_all_values():
                ws_cie.append_row(["Fecha", "Hora", "Base_Inicial", "Ventas_Efectivo", "Gastos_Efectivo", "Dinero_A_Bancos", "Saldo_Teorico", "Saldo_Real", "Diferencia", "Notas"])
        except:
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
        df.columns = df.columns.str.strip()
        
        cols_numericas = ['Precio', 'Stock', 'Monto', 'Total', 'Costo', 'Costo_Total', 'Base_Inicial', 'Ventas_Efectivo', 'Gastos_Efectivo', 'Total_Real', 'Dinero_A_Bancos', 'Saldo_Teorico', 'Saldo_Real', 'Diferencia']
        
        for col in cols_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
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

def actualizar_cierre_diario(ws_cie, fecha_str, datos_nuevos):
    try:
        cell = ws_cie.find(fecha_str) 
        datos_limpios = [sanitizar_dato(d) for d in datos_nuevos]
        
        if cell:
            ws_cie.update(f"A{cell.row}", [datos_limpios])
            return "actualizado"
        else:
            ws_cie.append_row(datos_limpios)
            return "creado"
    except Exception as e:
        st.error(f"Error en persistencia de cierre: {e}")
        return "error"

def guardar_actualizar_cliente(ws_cli, cedula, nuevos_datos):
    try:
        cell = ws_cli.find(str(cedula))
        datos_limpios = [sanitizar_dato(d) for d in nuevos_datos]
        
        if cell:
            ws_cli.update(f"A{cell.row}", [datos_limpios])
            return True
        else:
            ws_cli.append_row(datos_limpios)
            return True
    except Exception as e:
        st.error(f"Error guardando cliente: {e}")
        return False

# --- FUNCIÓN CORREGIDA: INVENTARIO NEGATIVO PERMITIDO ---
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
                stock_actual_val = ws_inv.cell(fila_num, 4).value 
                try:
                    stock_actual = int(float(stock_actual_val)) if stock_actual_val else 0
                except:
                    stock_actual = 0
                
                # AQUÍ ESTÁ EL CAMBIO: Se permite stock negativo
                nuevo_stock = stock_actual - int(item['Cantidad'])
                
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
    if 'mascota_seleccionada' not in st.session_state: st.session_state.mascota_seleccionada = None
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
                        cliente_data = res.iloc[0].to_dict()
                        
                        # --- CORRECCIÓN LÓGICA MASCOTAS ---
                        mascotas_clean_list = []
                        json_raw = cliente_data.get('Info_Mascotas', '')
                        
                        # 1. Intentar Parsear JSON
                        try:
                            if json_raw and str(json_raw).strip():
                                parsed = json.loads(str(json_raw))
                                if isinstance(parsed, list):
                                    mascotas_clean_list = parsed
                        except:
                            mascotas_clean_list = []
                        
                        # 2. Si falló o estaba vacío, buscar en columnas LEGACY
                        if not mascotas_clean_list:
                            nombre_old = cliente_data.get('Mascota', '')
                            tipo_old = cliente_data.get('Tipo_Mascota', 'N/A')
                            if nombre_old:
                                mascotas_clean_list = [{'Nombre': nombre_old, 'Tipo': tipo_old}]
                        
                        cliente_data['Lista_Mascotas_Clean'] = mascotas_clean_list
                        st.session_state.cliente_actual = cliente_data
                        
                        st.toast(f"Cliente cargado: {st.session_state.cliente_actual.get('Nombre')}", icon="✅")
                    else:
                        st.warning("Cliente no encontrado.")
        
        if st.session_state.cliente_actual:
            # Aquí extraemos SOLO LOS NOMBRES para el selectbox
            lista_objs = st.session_state.cliente_actual.get('Lista_Mascotas_Clean', [])
            nombres_mascotas = [m.get('Nombre', 'Sin Nombre') for m in lista_objs]
            
            if not nombres_mascotas:
                nombres_mascotas = ["General / Varios"]
            else:
                nombres_mascotas.append("General / Varios")
            
            st.info(f"🟢 **{st.session_state.cliente_actual.get('Nombre')}**")
            
            # Selector de Mascota corregido (Muestra nombres, no JSON)
            st.session_state.mascota_seleccionada = st.selectbox("🐾 ¿Para quién es esta compra?", options=nombres_mascotas)

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
                        
                        costo_unitario = float(info_p.get('Costo', 0))
                        
                        existe = False
                        for item in st.session_state.carrito:
                            if str(item['ID_Producto']) == str(info_p['ID_Producto']):
                                item['Cantidad'] += 1
                                item['Subtotal'] = item['Cantidad'] * item['Precio']
                                item['Costo_Total_Item'] = item['Cantidad'] * costo_unitario 
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
                                "Costo_Total_Item": costo_unitario, 
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
            cols_visibles = ["Nombre_Producto", "Cantidad", "Precio", "Subtotal", "Eliminar"]

            edited_df = st.data_editor(
                df_carrito[cols_visibles], 
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                key="editor_carrito",
                num_rows="dynamic"
            )

            items_actualizados = []
            for index, row in edited_df.iterrows():
                if not row['Eliminar']:
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
                    st.session_state.mascota_seleccionada = None
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
                            
                            mascota_final = st.session_state.mascota_seleccionada if st.session_state.mascota_seleccionada else "Varios"

                            # Guardar en Sheet Ventas
                            datos_venta = [
                                id_venta, fecha, 
                                str(st.session_state.cliente_actual.get('Cedula', '0')), 
                                st.session_state.cliente_actual.get('Nombre', 'Consumidor'),
                                tipo_entrega, direccion_envio, estado_envio,
                                metodo, banco_destino, 
                                total_general, items_str,
                                total_costo_venta, # Costo total
                                mascota_final # Guardar para qué mascota fue
                            ]
                            
                            # Generar Link WhatsApp
                            telefono = str(st.session_state.cliente_actual.get('Telefono', ''))
                            telefono = ''.join(filter(str.isdigit, telefono))
                            if telefono and not telefono.startswith('57') and len(telefono) == 10: telefono = '57' + telefono
                            
                            items_wa = "\n".join([f"• {i['Nombre_Producto']} x{i['Cantidad']}" for i in st.session_state.carrito])
                            
                            mensaje_wa = generar_mensaje_whatsapp(
                                st.session_state.cliente_actual.get('Nombre', 'Cliente'),
                                mascota_final,
                                "RECURRENTE", items_wa, total_general
                            )
                            st.session_state.whatsapp_link = {"telefono": telefono, "mensaje": mensaje_wa}

                            if escribir_fila(ws_ven, datos_venta):
                                actualizar_stock(ws_inv, st.session_state.carrito)
                                
                                cliente_pdf_data = {
                                    "ID": id_venta, "Fecha": fecha,
                                    "Cliente": st.session_state.cliente_actual.get('Nombre', 'Consumidor'),
                                    "Cedula_Cliente": str(st.session_state.cliente_actual.get('Cedula', '')),
                                    "Direccion": direccion_envio, 
                                    "Mascota": mascota_final,
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
                    <p><i>{row.get('Items', '')}</i></p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"🚀 Marcar Enviado #{row.get('ID')}", key=f"btn_{index}"):
                    actualizar_estado_envio(ws_ven, row.get('ID', ''), "Enviado")
                    st.rerun()

def tab_clientes(ws_cli):
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>👥</span> Gestión de Clientes Multi-Mascota", unsafe_allow_html=True)
    
    # Buscador para editar clientes existentes
    st.caption("🔍 Busca un cliente para ver sus mascotas o crea uno nuevo abajo.")
    cedula_buscar = st.text_input("Buscar Cliente por Cédula (para editar/ver)", key="search_cli_edit")
    
    cliente_en_edicion = None
    mascotas_init = [{"Nombre": "", "Tipo": "Perro", "Cumpleaños": date.today()}]
    
    if cedula_buscar:
        df = leer_datos(ws_cli)
        if not df.empty:
            res = df[df['Cedula'].astype(str) == str(cedula_buscar)]
            if not res.empty:
                cliente_en_edicion = res.iloc[0].to_dict()
                st.success(f"Editando a: {cliente_en_edicion.get('Nombre')}")
                
                # Cargar mascotas existentes (JSON o Legacy)
                json_raw = cliente_en_edicion.get('Info_Mascotas', '')
                try:
                    if json_raw and len(str(json_raw)) > 2:
                        mascotas_init = json.loads(str(json_raw))
                        # Convertir fecha string a date object para el editor
                        for m in mascotas_init:
                            try:
                                m['Cumpleaños'] = datetime.strptime(m['Cumpleaños'], "%Y-%m-%d").date()
                            except:
                                m['Cumpleaños'] = date.today()
                    else:
                        # Legacy
                        if cliente_en_edicion.get('Mascota'):
                            mascotas_init = [{
                                "Nombre": cliente_en_edicion.get('Mascota'),
                                "Tipo": cliente_en_edicion.get('Tipo_Mascota', 'N/A'),
                                "Cumpleaños": date.today() 
                            }]
                except:
                      mascotas_init = [{"Nombre": "", "Tipo": "Perro", "Cumpleaños": date.today()}]

    with st.form("form_cliente"):
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.markdown("##### Datos del Dueño")
            # Prellenar si estamos editando
            val_ced = cliente_en_edicion.get('Cedula') if cliente_en_edicion else ""
            val_nom = cliente_en_edicion.get('Nombre') if cliente_en_edicion else ""
            val_tel = cliente_en_edicion.get('Telefono') if cliente_en_edicion else ""
            val_ema = cliente_en_edicion.get('Email') if cliente_en_edicion else ""
            val_dir = cliente_en_edicion.get('Direccion') if cliente_en_edicion else ""
            
            cedula = st.text_input("Cédula / ID *", value=str(val_ced))
            nombre = st.text_input("Nombre Completo *", value=str(val_nom))
            telefono = st.text_input("Teléfono *", value=str(val_tel))
            email = st.text_input("Correo", value=str(val_ema))
            direccion = st.text_input("Dirección", value=str(val_dir))
        
        with col2:
            st.markdown("##### 🐶 Mis Mascotas (Agrega hasta 10)")
            
            # Editor de mascotas en tabla
            df_mascotas_input = pd.DataFrame(mascotas_init)
            
            column_config = {
                "Nombre": st.column_config.TextColumn("Nombre", required=True),
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Perro", "Gato", "Ave", "Roedor", "Otro"], required=True),
                "Cumpleaños": st.column_config.DateColumn("Cumpleaños")
            }
            
            edited_mascotas = st.data_editor(
                df_mascotas_input, 
                column_config=column_config, 
                num_rows="dynamic", 
                use_container_width=True,
                key="editor_mascotas"
            )

        if st.form_submit_button("💾 Guardar Cliente y Mascotas", type="primary"):
            if cedula and nombre:
                # Convertir mascotas a JSON
                mascotas_finales = []
                mascota_principal = ""
                tipo_principal = ""
                cumple_principal = ""

                # Iterar sobre el dataframe editado
                for index, row in edited_mascotas.iterrows():
                    if row['Nombre']: # Solo guardar si tiene nombre
                        mascotas_finales.append({
                            "Nombre": row['Nombre'],
                            "Tipo": row['Tipo'],
                            "Cumpleaños": str(row['Cumpleaños'])
                        })
                
                # Definir datos para columnas legacy (usamos la primera mascota de la lista)
                if mascotas_finales:
                    mascota_principal = mascotas_finales[0]['Nombre']
                    tipo_principal = mascotas_finales[0]['Tipo']
                    cumple_principal = mascotas_finales[0]['Cumpleaños']
                
                json_mascotas = json.dumps(mascotas_finales)
                
                # Columnas del usuario
                datos = [
                    cedula, nombre, telefono, email, direccion, 
                    mascota_principal, tipo_principal, cumple_principal, 
                    str(date.today()), json_mascotas
                ]
                
                if guardar_actualizar_cliente(ws_cli, cedula, datos):
                    st.success("Cliente guardado correctamente.")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Completa Cédula y Nombre como mínimo.")
    
    st.markdown("---")
    df = leer_datos(ws_cli)
    if not df.empty:
        # Mostrar tabla resumen
        cols_mostrar = ['Cedula', 'Nombre', 'Telefono', 'Mascota']
        st.dataframe(df[[c for c in cols_mostrar if c in df.columns]], use_container_width=True)

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

def tab_cuadre_diario_avanzado(ws_ven, ws_gas, ws_cie):
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>⚖️</span> Centro de Control y Cuadre Diario", unsafe_allow_html=True)
    
    # 1. SELECCIÓN DE FECHA
    col_f1, col_f2 = st.columns([1, 3])
    fecha_cierre = col_f1.date_input("📅 Fecha a Cuadrar", value=date.today())
    
    # 2. CARGA DE DATOS
    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)
    df_c = leer_datos(ws_cie)

    if not df_v.empty: df_v['Fecha_Dt'] = df_v['Fecha'].dt.date
    if not df_g.empty: df_g['Fecha_Dt'] = df_g['Fecha'].dt.date
    if not df_c.empty: df_c['Fecha_Dt'] = df_c['Fecha'].dt.date

    # Filtrar movimientos SOLO de la fecha seleccionada
    v_dia = df_v[df_v['Fecha_Dt'] == fecha_cierre] if not df_v.empty else pd.DataFrame()
    g_dia = df_g[df_g['Fecha_Dt'] == fecha_cierre] if not df_g.empty else pd.DataFrame()
    
    # --- LOGICA DE CONTINUIDAD DE CAJA ---
    
    # A) Buscar si YA existe un cierre para HOY (Modo Edición)
    registro_hoy = df_c[df_c['Fecha_Dt'] == fecha_cierre] if not df_c.empty else pd.DataFrame()
    
    modo_edicion = False
    base_sugerida = 0.0
    consignacion_guardada = 0.0
    saldo_real_guardado = 0.0
    msg_base = ""

    if not registro_hoy.empty:
        modo_edicion = True
        fila = registro_hoy.iloc[0]
        base_sugerida = float(fila.get('Base_Inicial', 0))
        consignacion_guardada = float(fila.get('Dinero_A_Bancos', 0))
        saldo_real_guardado = float(fila.get('Saldo_Real', 0))
        msg_base = "🟡 Editando cierre existente (sobreescribirá al guardar)."
        st.warning(f"⚠️ Ya existe un cierre para el {fecha_cierre}. Estás en modo EDICIÓN.")
    else:
        # B) Es un día nuevo. Buscar el cierre del día ANTERIOR más cercano
        msg_base = "Día nuevo."
        if not df_c.empty:
            cierres_anteriores = df_c[df_c['Fecha_Dt'] < fecha_cierre].sort_values(by='Fecha_Dt', ascending=True)
            
            if not cierres_anteriores.empty:
                ultimo_cierre = cierres_anteriores.iloc[-1] 
                base_sugerida = float(ultimo_cierre.get('Saldo_Real', 0.0))
                msg_base = f"🟢 Base traída automáticamente del cierre anterior (${base_sugerida:,.0f})"
            else:
                base_sugerida = 0.0
                msg_base = "No hay cierres anteriores. Base inicia en 0."
        else:
            msg_base = "Primera vez que se usa el módulo de Cierres."
        
        consignacion_guardada = 0.0
        saldo_real_guardado = 0.0

    # --- CÁLCULOS DEL DÍA ---
    venta_total_dia = v_dia['Total'].sum() if not v_dia.empty else 0
    
    if not v_dia.empty:
        ventas_efectivo = v_dia[v_dia['Metodo_Pago'] == 'Efectivo']['Total'].sum()
        ventas_bancos = v_dia[v_dia['Metodo_Pago'] != 'Efectivo']['Total'].sum()
        costo_dia = v_dia['Costo_Total'].sum() if 'Costo_Total' in v_dia.columns else 0
        utilidad_dia = venta_total_dia - costo_dia
    else:
        ventas_efectivo = 0; ventas_bancos = 0; costo_dia = 0; utilidad_dia = 0

    gastos_total_dia = g_dia['Monto'].sum() if not g_dia.empty else 0
    gastos_efectivo = 0
    if not g_dia.empty:
        mask_efec = g_dia['Banco_Origen'].isin(['Caja General', 'Efectivo', 'Caja Menor'])
        gastos_efectivo = g_dia[mask_efec]['Monto'].sum()

    # --- VISUALIZACIÓN ---
    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ventas Totales", f"${venta_total_dia:,.0f}")
    k2.metric("Entró a Bancos", f"${ventas_bancos:,.0f}")
    k3.metric("Entró en Efectivo", f"${ventas_efectivo:,.0f}")
    k4.metric("Utilidad Bruta", f"${utilidad_dia:,.0f}")

    st.markdown("---")
    st.subheader("🔐 Cuadre de Caja (Efectivo)")
    
    with st.form("form_cuadre_diario"):
        col_base, col_info = st.columns([1, 2])
        
        with col_base:
            base_inicial = st.number_input(
                "Base Inicial (Dinero en caja al abrir)", 
                value=base_sugerida, 
                step=1000.0, 
                help="Debe coincidir con el Saldo Real del día anterior."
            )
        
        with col_info:
            st.info(msg_base)

        st.markdown("##### Movimientos de Efectivo")
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**(+) Ventas Efec:** ${ventas_efectivo:,.0f}")
        c2.markdown(f"**(-) Gastos Efec:** ${gastos_efectivo:,.0f}")
        
        dinero_a_bancos = c3.number_input(
            "(-) Consignación a Bancos", 
            min_value=0.0, 
            value=consignacion_guardada,
            step=1000.0, 
            help="Dinero físico que sacaste hoy para meter al banco"
        )

        # Fórmula Maestra de Flujo de Caja
        saldo_teorico = base_inicial + ventas_efectivo - gastos_efectivo - dinero_a_bancos
        
        st.markdown(f"### 🎯 La caja DEBE tener: <span style='color:{COLOR_PRIMARIO}'>${saldo_teorico:,.0f}</span>", unsafe_allow_html=True)
        
        saldo_real = st.number_input("💵 ¿Cuánto dinero contaste REALMENTE?", min_value=0.0, step=50.0, value=saldo_real_guardado if modo_edicion else 0.0)
        notas = st.text_area("Observaciones del cierre")
        
        diferencia = saldo_real - saldo_teorico
        
        if saldo_real > 0:
            if abs(diferencia) < 100:
                st.success(f"✅ CUADRE PERFECTO. Mañana iniciarás con: ${saldo_real:,.0f}")
            elif diferencia > 0:
                st.info(f"💰 Sobra: ${diferencia:,.0f}")
            else:
                st.error(f"🚨 Falta: ${diferencia:,.0f}")

        texto_boton = "🔄 ACTUALIZAR CIERRE" if modo_edicion else "💾 GUARDAR NUEVO CIERRE"

        if st.form_submit_button(texto_boton, type="primary", use_container_width=True):
            datos_cierre = [
                str(fecha_cierre), datetime.now().strftime("%H:%M:%S"),
                base_inicial, ventas_efectivo, gastos_efectivo, dinero_a_bancos,
                saldo_teorico, saldo_real, diferencia, notas
            ]
            
            res = actualizar_cierre_diario(ws_cie, str(fecha_cierre), datos_cierre)
            
            if res != "error":
                st.balloons()
                if res == "actualizado":
                    st.success("✅ Cierre actualizado correctamente.")
                else:
                    st.success("✅ Cierre guardado. Mañana la base se cargará automáticamente.")
                time.sleep(1.5)
                st.rerun()

def tab_finanzas_pro(ws_ven, ws_gas, ws_cie):
    st.markdown(f"## <span style='color:{COLOR_PRIMARIO}'>📊</span> Resultados Reales (Ganancia)", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    f_inicio = c1.date_input("Desde", value=date.today().replace(day=1))
    f_fin = c2.date_input("Hasta", value=date.today())

    df_v = leer_datos(ws_ven)
    df_g = leer_datos(ws_gas)

    if not df_v.empty: df_v['Fecha_Dt'] = df_v['Fecha'].dt.date
    if not df_g.empty: df_g['Fecha_Dt'] = df_g['Fecha'].dt.date

    v_rango = df_v[(df_v['Fecha_Dt'] >= f_inicio) & (df_v['Fecha_Dt'] <= f_fin)] if not df_v.empty else pd.DataFrame()
    g_rango = df_g[(df_g['Fecha_Dt'] >= f_inicio) & (df_g['Fecha_Dt'] <= f_fin)] if not df_g.empty else pd.DataFrame()

    ingresos = v_rango['Total'].sum() if not v_rango.empty else 0
    costo_mercancia = v_rango['Costo_Total'].sum() if not v_rango.empty and 'Costo_Total' in v_rango.columns else 0
    utilidad_bruta = ingresos - costo_mercancia
    margen_bruto = (utilidad_bruta / ingresos * 100) if ingresos > 0 else 0

    gastos_operativos = 0
    if not g_rango.empty:
        mask_operativo = ~g_rango['Tipo_Gasto'].isin(['Costo de Venta']) 
        gastos_operativos = g_rango[mask_operativo]['Monto'].sum()

    utilidad_neta = utilidad_bruta - gastos_operativos
    margen_neto = (utilidad_neta / ingresos * 100) if ingresos > 0 else 0

    st.markdown("### Estado de Resultados")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("1. Ventas", f"${ingresos:,.0f}")
    k2.metric("2. (-) Costo Prod. Vendido", f"${costo_mercancia:,.0f}", help="Costo de inventario de lo que se vendió")
    k3.metric("3. (-) Gastos Operativos", f"${gastos_operativos:,.0f}", help="Arriendos, nómina, servicios (excluye compra inventario)")
    k4.metric("= Utilidad Neta", f"${utilidad_neta:,.0f}", delta=f"{margen_neto:.1f}% Margen")

    st.progress(max(0, min(100, int(margen_neto))))

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

    st.markdown("---")
    if st.button("📥 Descargar Reporte Financiero (Excel)"):
        ws_cap_temp = conectar_google_sheets()[4] 
        df_c_temp = leer_datos(ws_cap_temp)
        
        excel_data = generar_excel_financiero(v_rango, g_rango, df_c_temp, f_inicio, f_fin)
        if excel_data:
            st.download_button("📄 Clic para guardar", data=excel_data, file_name="Reporte_Financiero.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- MAIN ---

def main():
    configurar_pagina()
    
    with st.sidebar:
        st.markdown(f"<h1 style='color:{COLOR_PRIMARIO}; text-align: center;'>Nexus Pro</h1>", unsafe_allow_html=True)
        st.markdown(f"<center><span style='background-color:{COLOR_ACENTO}; color:white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;'>v9.1 Multi-Pet Hybrid</span></center>", unsafe_allow_html=True)
        st.markdown("---")
        
        opcion = st.radio("Menú Principal", 
            ["Punto de Venta", "Despachos y Envíos", "Gestión de Clientes", "Inversión y Gastos", "Cuadre Diario (Caja)", "Finanzas & Resultados"],
            index=0
        )
        st.markdown("---")
        with st.container(border=True):
            st.caption("Sistema integrado para Bigotes y Patitas.")

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
        tab_cuadre_diario_avanzado(ws_ven, ws_gas, ws_cie)
    elif opcion == "Finanzas & Resultados":
        tab_finanzas_pro(ws_ven, ws_gas, ws_cie)

if __name__ == "__main__":
    main()
