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
            # Actualizar fila
            ws_cli.update(f"A{cell.row}", [datos_limpios])
            return True
        else:
            # Crear nuevo
            ws_cli.append_row(datos_limpios)
            return True
    except Exception as e:
        st.error(f"Error guardando cliente: {e}")
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
                stock_actual_val = ws_inv.cell(fila_num, 4).value 
                try:
                    stock_actual = int(float(stock_actual_val)) if stock_actual_val else 0
                except:
                    stock_actual = 0
                
                # Restamos permitiendo negativos
                nuevo_stock = stock_actual - int(item['Cantidad'])
                
                ws_inv.update_cell(fila_num, 4, nuevo_stock) 
                
        return True
    except Exception as e:
        st.error(f"Error actualizando stock: {e}")
        return False

def actualizar_estado_envio(ws_ven, id_venta, nuevo_estado):
    """
    Busca la venta por ID_Venta y actualiza la columna 'Estado_Envio' a 'nuevo_estado'.
    """
    try:
        # 1. Encontrar la celda del ID
        cell = ws_ven.find(str(id_venta))
        
        if cell:
            # 2. Encontrar dinámicamente la columna 'Estado_Envio'
            headers = ws_ven.row_values(1)
            try:
                col_index = headers.index("Estado_Envio") + 1
            except ValueError:
                # Fallback si no encuentra el nombre exacto
                col_index = 7 
            
            # 3. Actualizar la celda específica
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
            <center>
                <img src="BigotesyPaticas.png" width="60">
            </center>
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
        # --- BUSCADOR AVANZADO DE CLIENTES ---
        st.markdown("#### 👤 Buscar Cliente")
        df_c = leer_datos(ws_cli)
        if not df_c.empty:
            df_c['Cedula'] = df_c['Cedula'].astype(str)
            df_c['Telefono'] = df_c['Telefono'].astype(str)
            df_c['Mascota'] = df_c['Mascota'].astype(str)
            df_c['Nombre'] = df_c['Nombre'].astype(str)
            search = st.text_input("Buscar por nombre, cédula, mascota o teléfono")
            if search:
                mask = (
                    df_c['Nombre'].str.contains(search, case=False, na=False) |
                    df_c['Cedula'].str.contains(search, case=False, na=False) |
                    df_c['Mascota'].str.contains(search, case=False, na=False) |
                    df_c['Telefono'].str.contains(search, case=False, na=False)
                )
                resultados = df_c[mask]
            else:
                resultados = df_c

            st.dataframe(resultados[['Cedula', 'Nombre', 'Mascota', 'Telefono']], use_container_width=True, hide_index=True)
            selected_idx = st.selectbox("Selecciona un cliente", resultados.index, format_func=lambda i: f"{resultados.loc[i, 'Nombre']} ({resultados.loc[i, 'Cedula']})")
            if st.button("Cargar Cliente"):
                cliente_data = resultados.loc[selected_idx].to_dict()
                # Cargar mascotas
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
                st.toast(f"Cliente cargado: {st.session_state.cliente_actual.get('Nombre')}", icon="✅")
                st.session_state.mascota_seleccionada = mascotas_para_dropdown[0] if mascotas_para_dropdown else None
                st.rerun()

        # --- HISTORIAL DE VENTAS DEL CLIENTE ---
        if st.session_state.cliente_actual:
            st.info(f"🟢 **{st.session_state.cliente_actual.get('Nombre')}**")
            df_v = leer_datos(ws_ven)
            if not df_v.empty:
                df_v['Cedula_Cliente'] = df_v['Cedula_Cliente'].astype(str)
                historial = df_v[df_v['Cedula_Cliente'] == st.session_state.cliente_actual.get('Cedula', '')]
                st.markdown("##### 🧾 Historial de Ventas")
                if not historial.empty:
                    st.dataframe(historial[['Fecha', 'Total', 'Items', 'Metodo_Pago', 'Tipo_Entrega']], use_container_width=True, hide_index=True)
                else:
                    st.info("No hay ventas registradas para este cliente.")
    # ...rest of POS code...
