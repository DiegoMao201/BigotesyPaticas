import streamlit as st
import pandas as pd
import gspread
import importlib
from datetime import datetime, date, timedelta
import json
import urllib.parse
import jinja2
from io import BytesIO
from pathlib import Path
import pytz
import numpy as np
import time  # Necesario para manejar las esperas en el error 429
import uuid  # ya lo tienes; mantener
import re  # ✅ nuevo

try:
    HTML = importlib.import_module("weasyprint").HTML
except Exception:
    HTML = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
except Exception:
    colors = None
    A4 = None
    mm = None
    canvas = None

# --- CONFIGURACIÓN DE ZONA HORARIA ---
TZ_CO = pytz.timezone("America/Bogota")
BASE_DIR = Path(__file__).resolve().parent
FACTURA_TEMPLATE_PATH = BASE_DIR / "factura.html"

def now_co():
    return datetime.now(TZ_CO)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Nexus Pro | Bigotes y Paticas", page_icon="🐾", layout="wide")

# ==========================================
# 1. SISTEMA ANTI-BLOQUEO (RETRY LOGIC)
# ==========================================
def safe_api_call(func, *args, **kwargs):
    """
    Ejecuta cualquier función de gspread. Si da error 429 (Cuota excedida),
    espera y reintenta hasta 5 veces.
    """
    max_retries = 5
    wait_time = 2  # Segundos iniciales de espera
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota exceeded" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    wait_time *= 2  # Espera exponencial (2s, 4s, 8s...)
                    continue
                else:
                    st.error("⚠️ La API de Google está saturada. Por favor espera 1 minuto.")
                    raise e
            else:
                raise e

# ==========================================
# 2. CONEXIÓN Y LECTURA OPTIMIZADA
# ==========================================
@st.cache_resource(ttl=3600)
def conectar_google_sheets():
    """Conecta a Google Sheets y devuelve el objeto Spreadsheet principal"""
    try:
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        return sh
    except Exception as e:
        st.error(f"Error crítico conectando a Google Sheets: {e}")
        st.stop()

def obtener_worksheets(sh):
    """Devuelve un diccionario con las hojas para fácil acceso"""
    return {
        "inv": sh.worksheet("Inventario"),
        "cli": sh.worksheet("Clientes"),
        "ven": sh.worksheet("Ventas"),
        "gas": sh.worksheet("Gastos"),
        "cie": sh.worksheet("Cierres"),
        # Agrega las otras si las usas activamente, por ahora estas son las vitales para el POS
    }

def limpiar_dataframe(raw_data):
    """Convierte datos crudos de Sheets a DataFrame limpio"""
    if not raw_data:
        return pd.DataFrame()
    
    header = raw_data[0]
    # Limpieza de encabezados duplicados o vacíos
    seen = {}
    clean_header = []
    for i, h in enumerate(header):
        if not h or h.strip() == "":
            h = f"Col_{i+1}"
        h = h.strip()
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0
        clean_header.append(h)

    df = pd.DataFrame(raw_data[1:], columns=clean_header)

    # Convertir columnas numéricas y fechas
    cols_money = ['Precio', 'Costo', 'Monto', 'Total', 'Costo_Total', 
                  'Base_Inicial', 'Ventas_Efectivo', 'Gastos_Efectivo', 
                  'Dinero_A_Bancos', 'Saldo_Teorico', 'Saldo_Real', 'Diferencia']
    cols_numeric = ['Stock']

    for col in cols_money:
        if col in df.columns:
            df[col] = df[col].apply(clean_currency)

    for col in cols_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        
    return df

def cargar_datos_iniciales():
    """Carga TODOS los datos al Session State de una sola vez."""
    sh = conectar_google_sheets()
    h = obtener_worksheets(sh)
    
    with st.spinner("🔄 Sincronizando datos con la nube..."):
        # Usamos safe_api_call para leer
        data_inv = safe_api_call(h["inv"].get_all_values)
        data_cli = safe_api_call(h["cli"].get_all_values)
        data_ven = safe_api_call(h["ven"].get_all_values)
        data_gas = safe_api_call(h["gas"].get_all_values)
        data_cie = safe_api_call(h["cie"].get_all_values)

        st.session_state.db = {
            "inv": limpiar_dataframe(data_inv),
            "cli": limpiar_dataframe(data_cli),
            "ven": limpiar_dataframe(data_ven),
            "gas": limpiar_dataframe(data_gas),
            "cie": limpiar_dataframe(data_cie)
        }
        st.session_state.ultima_sincronizacion = now_co()

# ==========================================
# 3. FUNCIONES DE UTILIDAD (Tus funciones originales)
# ==========================================
def sanitizar_para_sheet(val):
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32, float)): return int(round(float(val)))
    if isinstance(val, (pd.Timestamp, datetime, date)): return val.strftime("%Y-%m-%d %H:%M:%S") if isinstance(val, datetime) else val.strftime("%Y-%m-%d")
    return val

def normalizar_id_producto(id_prod):
    if pd.isna(id_prod): return ""
    s = str(id_prod).strip().upper()
    s = s.replace(" ", "").replace(",", "").replace(".", "")
    if s.isdigit(): s = str(int(s))
    if s.endswith("00") and s[:-2].isdigit(): s = s[:-2]
    return s

def clean_currency(val):
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        return int(round(float(val)))
    s = str(val or "").strip().replace("$", "").replace(" ", "")
    if not s:
        return 0
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    s = re.sub(r"[^0-9,\.]", "", s)
    if not s:
        return 0

    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(",") > 1:
        s = s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif "," in s:
        left, right = s.split(",", 1)
        if len(right) <= 2:
            s = f"{left}.{right}"
        elif len(right) == 3 and len(left) <= 3:
            s = left + right
        elif len(right) == 3 and len(left) > 3:
            s = f"{left}.{right}"
        else:
            s = left + right
    elif "." in s:
        left, right = s.split(".", 1)
        if len(right) <= 2:
            s = f"{left}.{right}"
        elif len(right) == 3 and len(left) <= 3:
            s = left + right
        elif len(right) == 3 and len(left) > 3:
            s = f"{left}.{right}"
        else:
            s = left + right

    try:
        out = int(round(float(s)))
    except Exception:
        out = int(re.sub(r"[^0-9]", "", s) or 0)
    return -out if neg else out

def limpiar_tel(tel):
    t = str(tel).replace(" ", "").replace("+", "").replace("-", "").replace("(", "").replace(")", "").strip()
    if len(t) == 10 and not t.startswith("57"): t = "57" + t
    return t

def _wa_resumir_items(items_str: str, max_len: int = 180) -> str:
    s = (items_str or "").strip()
    if not s:
        return "—"
    s = " ".join(s.split())
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"

def _wa_items_bullets(items_str: str, max_items: int = 10) -> str:
    parts = [p.strip() for p in (items_str or "").split(",") if p.strip()]
    # 1.0x -> 1x
    parts = [re.sub(r"^(\d+)\.0x\s*", r"\1x ", p) for p in parts]
    if len(parts) > max_items:
        extra = len(parts) - max_items
        parts = parts[:max_items] + [f"• y {extra} más…"]
        return "\n".join([f"• {p}" if not p.startswith("•") else p for p in parts])
    return "\n".join([f"• {p}" for p in parts]) if parts else "• —"

def msg_venta(nombre: str, mascota: str, items_str: str, total: float) -> str:
    """
    Mensaje post-venta WhatsApp (bonito, corto, con emojis) compatible con WhatsApp Web/App.
    """
    nombre = (nombre or "Cliente").strip()
    mascota = (mascota or "tu peludito").strip()
    items_bullets = _wa_items_bullets(items_str)

    return (
        f"Hola *{nombre}* 👋🐾\n\n"
        f"¡Gracias por tu compra en *Bigotes y Paticas*! 💚\n"
        f"Hoy consentimos a *{mascota}* ✨\n\n"
        f"🛍️ *Productos:*\n{items_bullets}\n\n"
        f"💳 *Total:* ${float(total or 0):,.0f}\n\n"
        f"Si quieres, te ayudo con recomendaciones para {mascota} (alimento, premios y porciones). 🐶🐱\n"
        f"¡Gracias por confiar en nosotros! 🙌"
    )

def msg_venta_fidelidad(nombre: str, mascota: str, items_str: str, total: float) -> str:
    return msg_venta(nombre, mascota, items_str, total)

def msg_bienvenida(nombre, mascota):
    return f"""🐾 ¡Hola {nombre}! Bienvenido/a a Bigotes y Paticas.
🎉 Estamos felices de consentir a {mascota or 'tu peludito'}.
📦 Necesites comida, snacks o juguetes, aquí estamos.
🤗 Gracias por confiar en nosotros."""

def reset_pos_workflow(clear_cliente=True):
    if clear_cliente:
        st.session_state.pop("cliente_actual", None)
        st.session_state.pop("mascota_seleccionada", None)
    for key in [
        "carrito",
        "ultimo_pdf",
        "ultimo_pdf_nombre",
        "ultima_venta_id",
        "ultima_venta_resumen",
        "whatsapp_link",
        "whatsapp_link_web",
        "pos_last_producto_key",
        "pos_cant",
        "pos_precio",
        "pos_desc",
        "busca_cli_pos",
        "pos_dir",
        "editor_carrito",
    ]:
        st.session_state.pop(key, None)

def construir_resumen_venta(id_venta, fecha, metodo, entrega, dir_envio, cliente, mascota, carrito, total_num):
    items_normalizados = []
    unidades_total = 0.0
    descuento_total = 0
    for item in carrito:
        cantidad = float(item.get("Cantidad", 0) or 0)
        precio = clean_currency(item.get("Precio", item.get("Precio_Unitario", 0)) or 0)
        descuento = clean_currency(item.get("Descuento", item.get("Descuento_Unitario", 0)) or 0)
        subtotal = clean_currency(item.get("Subtotal", item.get("Subtotal_Linea", (precio - descuento) * cantidad)) or 0)
        unidades_total += cantidad
        descuento_total += clean_currency(descuento * cantidad)
        items_normalizados.append(
            {
                "Producto_UID": item.get("Producto_UID", ""),
                "ID_Producto": item.get("ID_Producto", item.get("ID", "")),
                "Nombre_Producto": item.get("Nombre_Producto", item.get("Nombre", "Producto")),
                "Cantidad": cantidad,
                "Precio": precio,
                "Descuento": descuento,
                "Subtotal": subtotal,
            }
        )

    return {
        "venta": {
            "ID": id_venta,
            "Fecha": fecha,
            "Cliente": cliente.get("Nombre", "Consumidor Final") if cliente else "Consumidor Final",
            "Cedula_Cliente": cliente.get("Cedula", "") if cliente else "",
            "Direccion": dir_envio or (cliente.get("Direccion", "") if cliente else "Local"),
            "Mascota": mascota or "",
            "Metodo_Pago": metodo,
            "Tipo_Entrega": entrega,
            "Total": clean_currency(total_num or 0),
            "Total_Items": len(items_normalizados),
            "Unidades": unidades_total,
            "Descuento_Total": descuento_total,
        },
        "items": items_normalizados,
    }

def _row_pick(row, candidates, default=""):
    for key in candidates:
        if key in row:
            value = row.get(key)
            if pd.notna(value) and str(value).strip() != "":
                return value
    return default

def _normalizar_items_factura(items):
    items_normalizados = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        cantidad = float(item.get("Cantidad", item.get("Qty", 0)) or 0)
        precio = clean_currency(item.get("Precio", item.get("Precio_Unitario", 0)) or 0)
        descuento = clean_currency(item.get("Descuento", item.get("Descuento_Unitario", 0)) or 0)
        subtotal = clean_currency(item.get("Subtotal", item.get("Subtotal_Linea", (precio - descuento) * cantidad)) or 0)
        items_normalizados.append(
            {
                "Nombre_Producto": item.get("Nombre_Producto", item.get("Nombre", item.get("Descripcion", "Producto"))),
                "Cantidad": cantidad,
                "Precio": precio,
                "Descuento": descuento,
                "Subtotal": subtotal,
            }
        )
    return items_normalizados

def _items_desde_texto(items_str, total_num):
    partes = [p.strip() for p in str(items_str or "").split(",") if p.strip()]
    if not partes:
        return []
    items = []
    distribuir_total = len(partes) == 1
    for parte in partes:
        match = re.match(r"^([\d\.,]+)x\s+(.+)$", parte)
        if match:
            cantidad = float(str(match.group(1)).replace(",", "."))
            nombre = match.group(2).strip()
        else:
            cantidad = 1.0
            nombre = parte
        subtotal = clean_currency(total_num) if distribuir_total else 0
        precio = int(round(subtotal / cantidad)) if distribuir_total and cantidad > 0 else 0
        items.append(
            {
                "Nombre_Producto": nombre,
                "Cantidad": cantidad,
                "Precio": precio,
                "Descuento": 0,
                "Subtotal": subtotal,
            }
        )
    return items

def construir_resumen_venta_desde_fila(row):
    row_dict = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    total_num = clean_currency(_row_pick(row_dict, ["Total", "Monto", "Valor_Total"], 0))

    items_json_raw = _row_pick(
        row_dict,
        ["Items_JSON", "Items_Json", "Items_Detalle", "Detalle_JSON", "Detalle_Venta", "Productos_JSON"],
        "",
    )
    parsed_items = []
    if items_json_raw:
        try:
            loaded = json.loads(str(items_json_raw))
            if isinstance(loaded, list):
                parsed_items = _normalizar_items_factura(loaded)
        except Exception:
            parsed_items = []

    if not parsed_items:
        items_text = _row_pick(row_dict, ["Items", "Detalle", "Productos", "Descripcion"], "")
        parsed_items = _items_desde_texto(items_text, total_num)

    if not parsed_items:
        parsed_items = [
            {
                "Nombre_Producto": "Venta registrada",
                "Cantidad": 1,
                "Precio": total_num,
                "Descuento": 0,
                "Subtotal": total_num,
            }
        ]

    cliente = {
        "Nombre": _row_pick(row_dict, ["Nombre_Cliente", "Cliente", "Nombre"], "Consumidor Final"),
        "Cedula": _row_pick(row_dict, ["Cedula_Cliente", "Cedula", "Documento"], ""),
        "Direccion": _row_pick(row_dict, ["Direccion", "Dirección", "Direccion_Entrega"], "Local"),
    }

    return construir_resumen_venta(
        id_venta=str(_row_pick(row_dict, ["ID_Venta", "ID", "Venta_ID"], "SIN-ID")),
        fecha=str(_row_pick(row_dict, ["Fecha", "Fecha_Venta"], "")),
        metodo=str(_row_pick(row_dict, ["Metodo_Pago", "Método_Pago", "Pago"], "Efectivo")),
        entrega=str(_row_pick(row_dict, ["Tipo_Entrega", "Entrega", "Modalidad_Entrega"], "Local")),
        dir_envio=str(_row_pick(row_dict, ["Direccion", "Dirección", "Direccion_Entrega"], "Local")),
        cliente=cliente,
        mascota=str(_row_pick(row_dict, ["Mascota", "Nombre_Mascota"], "")),
        carrito=parsed_items,
        total_num=total_num,
    )

def generar_pdf_reportlab(venta_data, items):
    if canvas is None or colors is None or A4 is None or mm is None:
        return None

    items_render = []
    subtotal_bruto = 0
    descuento_total = 0
    total_unidades = 0.0
    for item in items:
        cantidad = float(item.get("Cantidad", 0) or 0)
        precio = clean_currency(item.get("Precio", item.get("Precio_Unitario", 0)) or 0)
        descuento = clean_currency(item.get("Descuento", item.get("Descuento_Unitario", 0)) or 0)
        subtotal = clean_currency(item.get("Subtotal", item.get("Subtotal_Linea", (precio - descuento) * cantidad)) or 0)
        subtotal_bruto += clean_currency(precio * cantidad)
        descuento_total += clean_currency(descuento * cantidad)
        total_unidades += cantidad
        items_render.append(
            {
                "Nombre_Producto": str(item.get("Nombre_Producto", item.get("Nombre", "Producto"))),
                "Cantidad": cantidad,
                "Precio": precio,
                "Descuento": descuento,
                "Subtotal": subtotal,
            }
        )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 13 * mm
    teal = colors.HexColor("#187f77")
    teal_deep = colors.HexColor("#0f5f5a")
    gold = colors.HexColor("#f5a641")
    sand = colors.HexColor("#f8f4eb")
    mist = colors.HexColor("#eef6f5")
    ink = colors.HexColor("#16313f")
    muted = colors.HexColor("#5c7280")
    white = colors.white
    compact_mode = len(items_render) <= 8

    def money(value):
        return f"${clean_currency(value or 0):,.0f}"

    def draw_base_header():
        pdf.setFillColor(white)
        pdf.roundRect(margin - 4, margin - 2, width - (2 * margin) + 8, height - (2 * margin) + 4, 18, stroke=0, fill=1)
        pdf.setFillColor(gold)
        pdf.roundRect(margin - 4, height - margin + 8, width - (2 * margin) + 8, 10, 5, stroke=0, fill=1)
        header_height = 76 if compact_mode else 88
        pdf.setFillColor(teal)
        pdf.roundRect(margin - 4, height - margin - (header_height - 10), width - (2 * margin) + 8, header_height, 18, stroke=0, fill=1)
        pdf.setFillColor(teal_deep)
        pdf.roundRect(width - margin - 165, height - margin - 54, 150, 48, 16, stroke=0, fill=1)

        logo_path = BASE_DIR / "BigotesyPaticas.png"
        if logo_path.exists():
            try:
                pdf.drawImage(str(logo_path), margin + 10, height - margin - 58, width=42, height=42, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass

        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin + 62, height - margin - 16, "FACTURA POST VENTA")
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawString(margin + 62, height - margin - 38, "Bigotes y Paticas")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(margin + 62, height - margin - 54, "Tu tienda de confianza para consentir a cada peludito.")
        pdf.drawString(margin + 62, height - margin - 67, "Tel: 3206876633")

        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawRightString(width - margin - 28, height - margin - 22, "RECIBO")
        pdf.setFont("Helvetica", 10)
        pdf.drawRightString(width - margin - 28, height - margin - 38, f"No: {venta_data.get('ID', '')}")
        pdf.drawRightString(width - margin - 28, height - margin - 52, f"Fecha: {venta_data.get('Fecha', '')}")

    def draw_summary_cards(top_y):
        card_width = (width - (2 * margin) - 20) / 3
        card_height = 34 if compact_mode else 42
        value_offset = 22 if compact_mode else 26
        foot_offset = 30 if compact_mode else 37
        cards = [
            ("Total cobrado", money(venta_data.get("Total", 0)), "Factura lista para descargar"),
            ("Unidades", f"{total_unidades:,.0f}", "Productos entregados"),
            ("Ahorro", money(descuento_total), "Descuentos aplicados"),
        ]
        x = margin
        for title, value, foot in cards:
            pdf.setFillColor(sand)
            pdf.roundRect(x, top_y - card_height, card_width, card_height - 2, 14, stroke=0, fill=1)
            pdf.setStrokeColor(colors.HexColor("#d9e5e3"))
            pdf.roundRect(x, top_y - card_height, card_width, card_height - 2, 14, stroke=1, fill=0)
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica-Bold", 7.5)
            pdf.drawString(x + 10, top_y - 12, title.upper())
            pdf.setFillColor(ink)
            pdf.setFont("Helvetica-Bold", 13 if compact_mode else 14)
            pdf.drawString(x + 10, top_y - value_offset, value)
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica", 7.8 if compact_mode else 8.5)
            pdf.drawString(x + 10, top_y - foot_offset, foot)
            x += card_width + 10

    def draw_info_box(x, y, box_width, title, lines):
        box_height = 48 if compact_mode else 56
        pdf.setFillColor(white)
        pdf.roundRect(x, y - box_height, box_width, box_height, 14, stroke=0, fill=1)
        pdf.setStrokeColor(colors.HexColor("#d9e5e3"))
        pdf.roundRect(x, y - box_height, box_width, box_height, 14, stroke=1, fill=0)
        pdf.setFillColor(teal)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(x + 10, y - 12, title.upper())
        pdf.setFillColor(ink)
        current_y = y - 24
        for idx, line in enumerate(lines):
            pdf.setFont("Helvetica-Bold" if idx == 0 else "Helvetica", 8.8 if compact_mode else 9.5)
            pdf.drawString(x + 10, current_y, str(line)[:58])
            current_y -= 9 if compact_mode else 11

    def draw_table_header(y):
        pdf.setFillColor(mist)
        pdf.roundRect(margin, y - 16, width - (2 * margin), 16, 8, stroke=0, fill=1)
        pdf.setFillColor(teal)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(margin + 10, y - 12, "Descripcion")
        pdf.drawCentredString(margin + 265, y - 12, "Cant.")
        pdf.drawRightString(width - margin - 115, y - 12, "Precio Unit.")
        pdf.drawRightString(width - margin - 10, y - 12, "Subtotal")

    draw_base_header()
    draw_summary_cards(height - margin - (92 if compact_mode else 98))

    info_top = height - margin - (136 if compact_mode else 152)
    info_width = (width - (2 * margin) - 12) / 2
    draw_info_box(
        margin,
        info_top,
        info_width,
        "Facturado a",
        [
            venta_data.get("Cliente", "Consumidor Final"),
            f"ID: {venta_data.get('Cedula_Cliente', '---')}",
            venta_data.get("Direccion", "Local"),
            f"Mascota: {venta_data.get('Mascota', '---')}",
        ],
    )
    draw_info_box(
        margin + info_width + 12,
        info_top,
        info_width,
        "Detalles de la operacion",
        [
            f"Metodo: {venta_data.get('Metodo_Pago', 'Efectivo')}",
            f"Entrega: {venta_data.get('Tipo_Entrega', 'Local')}",
            "Estado: Pagado",
            f"Items: {venta_data.get('Total_Items', len(items_render))}",
        ],
    )

    y = info_top - (64 if compact_mode else 76)
    draw_table_header(y)
    y -= 22 if compact_mode else 26

    for item in items_render:
        if y < margin + 88:
            pdf.showPage()
            draw_base_header()
            y = height - margin - 32
            draw_table_header(y)
            y -= 26
        row_height = 14 if compact_mode and item["Descuento"] <= 0 else 18 if item["Descuento"] <= 0 else 20 if compact_mode else 24
        pdf.setStrokeColor(colors.HexColor("#edf3f2"))
        pdf.line(margin, y - row_height + 4, width - margin, y - row_height + 4)
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica-Bold", 8.7 if compact_mode else 9.2)
        nombre = item["Nombre_Producto"]
        if len(nombre) > (46 if compact_mode else 38):
            nombre = nombre[:43] + "..." if compact_mode else nombre[:35] + "..."
        pdf.drawString(margin + 10, y - 7, nombre)
        if item["Descuento"] > 0:
            pdf.setFillColor(colors.HexColor("#9a6200"))
            pdf.setFont("Helvetica", 7.1 if compact_mode else 7.8)
            pdf.drawString(margin + 10, y - 17, f"Descuento unitario {money(item['Descuento'])}")
        pdf.setFillColor(ink)
        pdf.setFont("Helvetica", 8.4 if compact_mode else 9)
        pdf.drawCentredString(margin + 265, y - 7, f"{item['Cantidad']:,.0f}")
        pdf.drawRightString(width - margin - 115, y - 7, money(item["Precio"]))
        pdf.drawRightString(width - margin - 10, y - 7, money(item["Subtotal"]))
        y -= row_height

    note_y = max(y - (6 if compact_mode else 10), margin + 68)
    pdf.setFillColor(mist)
    pdf.roundRect(margin, note_y - (36 if compact_mode else 44), width - (2 * margin) - 168, 36 if compact_mode else 44, 14, stroke=0, fill=1)
    pdf.setFillColor(teal)
    pdf.setFont("Helvetica-Bold", 10 if compact_mode else 11)
    pdf.drawString(margin + 12, note_y - 14, "Una factura que deja huella")
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 7.8 if compact_mode else 8.5)
    pdf.drawString(margin + 12, note_y - 28, "Resumen elegante, claro y listo para respaldo, cambios o garantias dentro del plazo informado.")

    totals_x = width - margin - 156
    pdf.setFillColor(colors.HexColor("#fffaf2"))
    pdf.roundRect(totals_x, note_y - 52, 156, 52, 14, stroke=0, fill=1)
    pdf.setStrokeColor(colors.HexColor("#efd2a5"))
    pdf.roundRect(totals_x, note_y - 52, 156, 52, 14, stroke=1, fill=0)
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(totals_x + 10, note_y - 14, f"Subtotal bruto: {money(subtotal_bruto)}")
    pdf.drawString(totals_x + 10, note_y - 25, f"Descuentos: {money(descuento_total)}")
    pdf.drawString(totals_x + 10, note_y - 36, f"Items: {venta_data.get('Total_Items', len(items_render))}")
    pdf.setFillColor(gold)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(totals_x + 146, note_y - 16, money(venta_data.get("Total", 0)))

    footer_y = margin + 14
    pdf.setStrokeColor(colors.HexColor("#e2eceb"))
    pdf.line(margin, footer_y + 14, width - margin, footer_y + 14)
    pdf.setFillColor(teal)
    pdf.setFont("Helvetica-Bold", 10.5)
    pdf.drawString(margin, footer_y, "Gracias por consentir a tu mascota con nosotros")
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 8.2)
    pdf.drawString(margin, footer_y - 10, "Conserva este recibo para cambios o garantias durante los siguientes 5 dias habiles.")
    pdf.drawRightString(width - margin, footer_y - 2, "Bigotes y Paticas · Servicio con detalle")

    pdf.save()
    return buffer.getvalue()

def generar_pdf_html(venta_data, items):
    try:
        if HTML is None:
            pdf_alt = generar_pdf_reportlab(venta_data, items)
            if pdf_alt is not None:
                return pdf_alt
            st.warning("No se pudo cargar WeasyPrint y tampoco está disponible ReportLab para generar el PDF.")
            return None
        try:
            with FACTURA_TEMPLATE_PATH.open("r", encoding="utf-8") as f:
                template_str = f.read()
        except FileNotFoundError:
            # Plantilla de respaldo por si falla la lectura del archivo
            template_str = "<html><body><h1>Factura {{id_venta}}</h1><p>Total: {{total}}</p></body></html>"

        items_render = []
        subtotal_bruto = 0
        descuento_total = 0
        total_unidades = 0.0
        for item in items:
            cantidad = float(item.get("Cantidad", 0) or 0)
            precio = clean_currency(item.get("Precio", item.get("Precio_Unitario", 0)) or 0)
            descuento = clean_currency(item.get("Descuento", item.get("Descuento_Unitario", 0)) or 0)
            subtotal = clean_currency(item.get("Subtotal", item.get("Subtotal_Linea", (precio - descuento) * cantidad)) or 0)
            subtotal_bruto += clean_currency(precio * cantidad)
            descuento_total += clean_currency(descuento * cantidad)
            total_unidades += cantidad
            items_render.append(
                {
                    "Nombre_Producto": item.get("Nombre_Producto", item.get("Nombre", "Producto")),
                    "Cantidad": cantidad,
                    "Precio": precio,
                    "Descuento": descuento,
                    "Subtotal": subtotal,
                }
            )

        context = {
            "id_venta": venta_data['ID'],
            "fecha": venta_data['Fecha'],
            "cliente_nombre": venta_data.get('Cliente', 'Consumidor Final'),
            "cliente_cedula": venta_data.get('Cedula_Cliente', '---'),
            "cliente_direccion": venta_data.get('Direccion', 'Local'),
            "cliente_mascota": venta_data.get('Mascota', '---'),
            "metodo_pago": venta_data.get('Metodo_Pago', 'Efectivo'),
            "tipo_entrega": venta_data.get('Tipo_Entrega', 'Local'),
            "items": items_render,
            "subtotal_bruto": subtotal_bruto,
            "descuento_total": descuento_total,
            "total_unidades": total_unidades,
            "total_items": venta_data.get("Total_Items", len(items_render)),
            "compact_mode": len(items_render) <= 8,
            "total": clean_currency(venta_data['Total']),
        }
        template = jinja2.Template(template_str)
        html_renderizado = template.render(context)
        try:
            pdf_file = HTML(string=html_renderizado, base_url=str(BASE_DIR)).write_pdf()
            return pdf_file
        except Exception:
            pdf_alt = generar_pdf_reportlab(venta_data, items)
            if pdf_alt is not None:
                return pdf_alt
            raise
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None

def normalizar_todas_las_referencias():
    sh = conectar_google_sheets()
    ws_inv = sh.worksheet("Inventario")
    df = st.session_state.db['inv']
    
    if 'ID_Producto' not in df.columns:
        st.error("No se encontró ID_Producto")
        return

    col_valores = [normalizar_id_producto(x) for x in df['ID_Producto']]
    
    # Encontrar indice de columna
    headers = safe_api_call(ws_inv.row_values, 1)
    if 'ID_Producto_Norm' not in headers:
        safe_api_call(ws_inv.update_cell, 1, len(headers)+1, 'ID_Producto_Norm')
        col_idx = len(headers) + 1
    else:
        col_idx = headers.index('ID_Producto_Norm') + 1

    # Update masivo (vertical)
    valores_lista = [[v] for v in col_valores]
    rango = f"{gspread.utils.rowcol_to_a1(2, col_idx)}:{gspread.utils.rowcol_to_a1(len(valores_lista)+1, col_idx)}"
    safe_api_call(ws_inv.update, rango, valores_lista)
    st.success("Referencias normalizadas en la Nube. Recarga los datos.")

# ==============================
# NUEVO: Reparación robusta UID
# ==============================

def _ensure_sheet_columns(ws, required_cols):
    """Asegura columnas en fila 1. Retorna headers finales."""
    headers = safe_api_call(ws.row_values, 1) or []
    changed = False
    for c in required_cols:
        if c not in headers:
            headers.append(c)
            safe_api_call(ws.update_cell, 1, len(headers), c)
            changed = True
    if changed:
        headers = safe_api_call(ws.row_values, 1) or headers
    return headers


def asegurar_ids_inventario_nube():
    """
    One-shot: crea/llena Producto_UID e ID_Producto_Norm en Inventario (nube + session_state.db['inv']).
    Debe estar DEFINIDA a nivel módulo (sin indentación) para que main() la pueda llamar.
    """
    if "db" not in st.session_state or "inv" not in st.session_state.db:
        st.error("Primero debes usar '🔄 Sincronizar Datos' para cargar Inventario en memoria.")
        return

    df = st.session_state.db["inv"].copy()
    if df.empty:
        st.warning("Inventario está vacío en memoria. Sincroniza y reintenta.")
        return

    if "ID_Producto" not in df.columns:
        st.error("Inventario no tiene columna 'ID_Producto'.")
        return

    # 1) Asegurar columnas locales
    if "ID_Producto_Norm" not in df.columns:
        df["ID_Producto_Norm"] = df["ID_Producto"].apply(normalizar_id_producto)

    if "Producto_UID" not in df.columns:
        df["Producto_UID"] = ""

    # 2) Generar UIDs faltantes
    uid_ser = df["Producto_UID"].fillna("").astype(str).str.strip()
    mask_missing = uid_ser.eq("")
    if mask_missing.any():
        df.loc[mask_missing, "Producto_UID"] = [uuid.uuid4().hex for _ in range(int(mask_missing.sum()))]

    # 3) Subir a Google Sheets
    sh = conectar_google_sheets()
    ws_inv = obtener_worksheets(sh)["inv"]

    headers = _ensure_sheet_columns(ws_inv, ["Producto_UID", "ID_Producto_Norm"])
    col_uid = headers.index("Producto_UID") + 1
    col_norm = headers.index("ID_Producto_Norm") + 1

    uid_vals = [[str(x)] for x in df["Producto_UID"].astype(str).tolist()]
    norm_vals = [[str(x)] for x in df["ID_Producto_Norm"].astype(str).tolist()]

    rango_uid = f"{gspread.utils.rowcol_to_a1(2, col_uid)}:{gspread.utils.rowcol_to_a1(len(uid_vals)+1, col_uid)}"
    rango_norm = f"{gspread.utils.rowcol_to_a1(2, col_norm)}:{gspread.utils.rowcol_to_a1(len(norm_vals)+1, col_norm)}"

    safe_api_call(ws_inv.update, rango_uid, uid_vals)
    safe_api_call(ws_inv.update, rango_norm, norm_vals)

    # 4) Persistir en memoria
    st.session_state.db["inv"] = df
    st.success("✅ Reparación lista: Producto_UID + ID_Producto_Norm actualizados en Inventario (nube y memoria).")

# ==========================================
# 4. FUNCIONES DE ESCRITURA (OPTIMIZADAS)
# ==========================================

# ...existing code...

def _to_float(x, default=0.0):
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return float(s.replace(",", ""))
    except Exception:
        return default

def _build_inventory_index(ws_inv):
    """
    Index seguro del Inventario (nube) para descontar stock sin ws.find().
    Retorna: headers, rows, col_stock, col_uid, col_norm, uid_to_row, norm_to_row
    """
    headers = safe_api_call(ws_inv.row_values, 1) or []

    # Asegurar columnas críticas
    if "Producto_UID" not in headers or "ID_Producto_Norm" not in headers:
        headers = _ensure_sheet_columns(ws_inv, ["Producto_UID", "ID_Producto_Norm"])

    all_vals = safe_api_call(ws_inv.get_all_values) or []
    if not all_vals:
        return [], [], None, None, None, {}, {}

    headers = all_vals[0]
    rows = all_vals[1:]

    if "Stock" not in headers:
        raise ValueError("Inventario nube no tiene columna 'Stock'.")

    col_stock = headers.index("Stock")
    col_uid = headers.index("Producto_UID") if "Producto_UID" in headers else None
    col_norm = headers.index("ID_Producto_Norm") if "ID_Producto_Norm" in headers else None

    uid_to_row = {}
    norm_to_row = {}

    for sheet_row, r in enumerate(rows, start=2):
        if col_uid is not None and col_uid < len(r):
            uid = str(r[col_uid]).strip()
            if uid:
                uid_to_row[uid] = sheet_row
        if col_norm is not None and col_norm < len(r):
            norm = str(r[col_norm]).strip()
            if norm:
                norm_to_row[norm] = sheet_row

    return headers, rows, col_stock, col_uid, col_norm, uid_to_row, norm_to_row

# ...existing code...
def registrar_venta(fila_datos, carrito):
    """Escribe venta y descuenta stock de forma confiable por Producto_UID."""
    sh = conectar_google_sheets()
    ws_ven = obtener_worksheets(sh)["ven"]
    ws_inv = obtener_worksheets(sh)["inv"]

    # 1) Escribir venta
    fila_datos = [sanitizar_para_sheet(v) for v in fila_datos]
    safe_api_call(ws_ven.append_row, fila_datos)

    # 2) Preparar inventario local
    df_inv = st.session_state.db["inv"].copy()
    if "Producto_UID" not in df_inv.columns:
        df_inv["Producto_UID"] = ""
    if "ID_Producto_Norm" not in df_inv.columns and "ID_Producto" in df_inv.columns:
        df_inv["ID_Producto_Norm"] = df_inv["ID_Producto"].apply(normalizar_id_producto)

    df_inv["Producto_UID"] = df_inv["Producto_UID"].fillna("").astype(str).str.strip()
    df_inv["ID_Producto_Norm"] = df_inv["ID_Producto_Norm"].fillna("").astype(str).str.strip()

    # 3) Index nube (sin ws.find)
    headers, rows, col_stock, col_uid, col_norm, uid_to_row, norm_to_row = _build_inventory_index(ws_inv)

    # 4) Acumular deltas por fila (por si se repite un producto en carrito)
    deltas_by_row = {}  # row -> total_delta (negativo)
    local_updates = []  # (idx_df, new_stock)

    for item in carrito:
        cant = _to_float(item.get("Cantidad", 0), 0.0)
        if cant <= 0:
            continue

        uid = str(item.get("Producto_UID", "")).strip()
        id_norm = str(item.get("ID_Producto_Norm", "")).strip()
        if not id_norm:
            id_norm = normalizar_id_producto(item.get("ID_Producto", ""))

        sheet_row = None
        if uid:
            sheet_row = uid_to_row.get(uid)
        if sheet_row is None and id_norm:
            sheet_row = norm_to_row.get(id_norm)

        if sheet_row is None:
            # no descontar a ciegas: si no se encuentra, se omite (y se debe corregir el inventario)
            continue

        deltas_by_row[sheet_row] = deltas_by_row.get(sheet_row, 0.0) - cant

        # update local por UID preferido
        m = pd.DataFrame()
        if uid:
            m = df_inv[df_inv["Producto_UID"] == uid]
        if m.empty and id_norm:
            m = df_inv[df_inv["ID_Producto_Norm"] == id_norm]
        if not m.empty:
            idx = m.index[0]
            stock_actual_local = _to_float(df_inv.at[idx, "Stock"], 0.0)
            df_inv.at[idx, "Stock"] = stock_actual_local - cant

    # 5) Batch update nube (calcular stock actual desde snapshot rows)
    updates = []
    # map fila->stock actual desde rows
    for sheet_row, delta in deltas_by_row.items():
        r = rows[sheet_row - 2]  # rows empieza en fila 2
        stock_actual = _to_float(r[col_stock] if col_stock < len(r) else 0.0, 0.0)
        nuevo_stock = stock_actual + delta
        cell_a1 = gspread.utils.rowcol_to_a1(sheet_row, col_stock + 1)
        updates.append({"range": cell_a1, "values": [[nuevo_stock]]})

    if updates:
        safe_api_call(ws_inv.batch_update, updates)

    # 6) Persistir inventario local
    st.session_state.db["inv"] = df_inv

    # 7) Actualizar Venta LOCAL (lo tuyo)
    cols = st.session_state.db["ven"].columns
    if len(fila_datos) < len(cols):
        fila_datos += [""] * (len(cols) - len(fila_datos))
    nuevo_df = pd.DataFrame([fila_datos], columns=cols)
    if "Total" in nuevo_df.columns:
        nuevo_df["Total"] = nuevo_df["Total"].apply(clean_currency)
    if "Costo_Total" in nuevo_df.columns:
        nuevo_df["Costo_Total"] = nuevo_df["Costo_Total"].apply(clean_currency)
    if "Fecha" in nuevo_df.columns:
        nuevo_df["Fecha"] = pd.to_datetime(nuevo_df["Fecha"], errors="coerce")
    st.session_state.db["ven"] = pd.concat([st.session_state.db["ven"], nuevo_df], ignore_index=True)

def registrar_gasto(fila_datos):
    sh = conectar_google_sheets()
    ws_gas = obtener_worksheets(sh)["gas"]
    
    fila_datos = [sanitizar_para_sheet(v) for v in fila_datos]
    safe_api_call(ws_gas.append_row, fila_datos)
    
    # Update local
    cols = st.session_state.db['gas'].columns
    if len(fila_datos) < len(cols): fila_datos += [""] * (len(cols) - len(fila_datos))
    nuevo_df = pd.DataFrame([fila_datos], columns=cols)
    if 'Monto' in nuevo_df.columns: nuevo_df['Monto'] = nuevo_df['Monto'].apply(clean_currency)
    st.session_state.db['gas'] = pd.concat([st.session_state.db['gas'], nuevo_df], ignore_index=True)

def registrar_cliente(fila_datos, update=False, row_idx=None):
    sh = conectar_google_sheets()
    ws_cli = obtener_worksheets(sh)["cli"]
    
    if update and row_idx:
        # Update rango A:J (asumiendo 10 columnas)
        rango = f"A{row_idx}:J{row_idx}"
        safe_api_call(ws_cli.update, rango, [fila_datos])
        # Para simplificar la consistencia en edición, forzamos recarga completa la próxima vez
        # o podríamos actualizar el DF local buscando por índice.
        # Por seguridad en datos maestros:
        cargar_datos_iniciales()
    else:
        safe_api_call(ws_cli.append_row, fila_datos)
        # Update local append
        cols = st.session_state.db['cli'].columns
        if len(fila_datos) < len(cols): fila_datos += [""] * (len(cols) - len(fila_datos))
        nuevo_df = pd.DataFrame([fila_datos], columns=cols)
        st.session_state.db['cli'] = pd.concat([st.session_state.db['cli'], nuevo_df], ignore_index=True)

def actualizar_estado_envio(id_venta, nuevo_estado):
    sh = conectar_google_sheets()
    ws_ven = obtener_worksheets(sh)["ven"]
    
    try:
        cell = safe_api_call(ws_ven.find, str(id_venta))
        if cell:
            # Buscar columna estado
            headers = safe_api_call(ws_ven.row_values, 1)
            col_idx = headers.index("Estado_Envio") + 1
            safe_api_call(ws_ven.update_cell, cell.row, col_idx, nuevo_estado)
            
            # Update Local
            df_ven = st.session_state.db['ven']
            idx = df_ven[df_ven['ID_Venta'] == id_venta].index
            if not idx.empty:
                st.session_state.db['ven'].at[idx[0], 'Estado_Envio'] = nuevo_estado
            return True
    except:
        return False

# ==========================================
# 5. PESTAÑAS (UI)
# ==========================================

def tab_pos():
    st.markdown("""
        <style>
        .main-title { color: #187f77; font-size: 2.2rem; font-weight: 800; margin-bottom: 0.5rem; }
        .sub-title { color: #f5a641; font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem; }
        .mascota-box { background: #f8f9fa; border-radius: 12px; padding: 10px 18px; margin-bottom: 10px; border-left: 5px solid #f5a641; }
        .carrito-total { background: #f5a641; color: white; font-size: 1.5rem; font-weight: bold; border-radius: 10px; padding: 12px 24px; text-align: right; margin-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">🐾 Punto de Venta Bigotes y Paticas</div>', unsafe_allow_html=True)
    
    # Inicializar variables POS
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'cliente_actual' not in st.session_state: st.session_state.cliente_actual = None
    if 'mascota_seleccionada' not in st.session_state: st.session_state.mascota_seleccionada = None
    if 'ultimo_pdf' not in st.session_state: st.session_state.ultimo_pdf = None
    if 'ultimo_pdf_nombre' not in st.session_state: st.session_state.ultimo_pdf_nombre = None
    if 'ultima_venta_id' not in st.session_state: st.session_state.ultima_venta_id = None
    if 'ultima_venta_resumen' not in st.session_state: st.session_state.ultima_venta_resumen = None
    if 'whatsapp_link' not in st.session_state: st.session_state.whatsapp_link = None
    if 'whatsapp_link_web' not in st.session_state: st.session_state.whatsapp_link_web = None

    df_c = st.session_state.db['cli']
    df_inv = st.session_state.db['inv']

    # --- 1. BUSCAR CLIENTE ---
    st.markdown("### 👤 Cliente")
    if not df_c.empty:
        search = st.text_input("Buscar cliente (Nombre, Cédula, Mascota)", key="busca_cli_pos")
        if search:
            mask = (
                df_c['Nombre'].astype(str).str.contains(search, case=False, na=False) |
                df_c['Cedula'].astype(str).str.contains(search, case=False, na=False) |
                df_c['Mascota'].astype(str).str.contains(search, case=False, na=False)
            )
            resultados = df_c[mask]
        else:
            resultados = df_c.head(0) # No mostrar nada si no hay busqueda

        if not resultados.empty:
            selected_idx = st.selectbox("Seleccionar:", resultados.index, format_func=lambda i: f"{resultados.loc[i, 'Nombre']} - {resultados.loc[i, 'Cedula']}")
            
            if st.button("Cargar Cliente"):
                cliente_data = resultados.loc[selected_idx].to_dict()
                # Parsear mascotas
                mascotas_lista = []
                try:
                    raw_json = cliente_data.get('Info_Mascotas', '')
                    if raw_json and str(raw_json).strip():
                        parsed = json.loads(str(raw_json))
                        if isinstance(parsed, list):
                            mascotas_lista = [m.get('Nombre') for m in parsed if m.get('Nombre')]
                except: pass
                
                if not mascotas_lista:
                    old_m = cliente_data.get('Mascota', '')
                    if old_m: mascotas_lista = [old_m]
                
                if not mascotas_lista: mascotas_lista = ["Varios"]
                
                cliente_data['Lista_Mascotas'] = mascotas_lista
                st.session_state.cliente_actual = cliente_data
                st.session_state.mascota_seleccionada = mascotas_lista[0]
                st.toast("Cliente cargado", icon="✅")
                st.rerun()

    if st.session_state.cliente_actual:
        c_act = st.session_state.cliente_actual
        st.info(f"Cliente: **{c_act['Nombre']}** | Mascota: **{st.session_state.mascota_seleccionada}**")

    # --- 2. PRODUCTOS (SELECCIÓN + AGREGAR) ---
    st.markdown("### 🛒 Productos")

    if df_inv is None or df_inv.empty:
        st.info("No hay productos en inventario.")
        return

    # Asegurar columnas claves
    if "Producto_UID" not in df_inv.columns:
        df_inv["Producto_UID"] = ""
    if "ID_Producto_Norm" not in df_inv.columns:
        df_inv["ID_Producto_Norm"] = df_inv["ID_Producto"].apply(normalizar_id_producto)

    df_inv["Producto_UID"] = df_inv["Producto_UID"].fillna("").astype(str).str.strip()

    # Display humano
    df_inv["Display"] = df_inv.apply(
        lambda x: f"{x.get('Nombre','')} | ID: {x.get('ID_Producto','')} | Stock: {int(float(x.get('Stock',0) or 0))} | ${int(float(x.get('Precio',0) or 0)):,}",
        axis=1,
    )
    mapa_display_a_uid = dict(zip(df_inv["Display"], df_inv["Producto_UID"]))

    prod_sel = st.selectbox("Buscar Producto", df_inv["Display"].tolist(), key="pos_prod_sel")

    # Resolver producto seleccionado (por UID preferido)
    uid_sel = str(mapa_display_a_uid.get(prod_sel, "")).strip()
    row_prod = None
    if uid_sel:
        m = df_inv[df_inv["Producto_UID"].astype(str).str.strip() == uid_sel]
        if not m.empty:
            row_prod = m.iloc[0]

    # Fallback si falta UID en alguna fila (no ideal, pero evita bloquear POS)
    if row_prod is None:
        df_inv["__ID_Norm"] = df_inv["ID_Producto"].apply(normalizar_id_producto)
        id_sel = df_inv.loc[df_inv["Display"] == prod_sel, "__ID_Norm"].iloc[0]
        mm = df_inv[df_inv["__ID_Norm"] == id_sel]
        if not mm.empty:
            row_prod = mm.iloc[0]

    if row_prod is None:
        st.error("No pude resolver el producto seleccionado.")
        return

    producto_uid = str(row_prod.get("Producto_UID", "")).strip()
    id_prod = str(row_prod.get("ID_Producto", "")).strip()
    id_norm = str(row_prod.get("ID_Producto_Norm", normalizar_id_producto(id_prod))).strip()
    nombre = str(row_prod.get("Nombre", "")).strip()
    stock_disp = float(row_prod.get("Stock", 0) or 0)
    precio_base = clean_currency(row_prod.get("Precio", 0) or 0)
    costo_base = clean_currency(row_prod.get("Costo", 0) or 0)

    # =========================
    # FIX: Reset de inputs por producto
    # =========================
    # Si no hay UID, usamos el id_norm como fallback estable
    producto_key = producto_uid if producto_uid else f"NORM:{id_norm}"

    if st.session_state.get("pos_last_producto_key") != producto_key:
        st.session_state["pos_last_producto_key"] = producto_key
        st.session_state["pos_cant"] = 1.0
        st.session_state["pos_precio"] = clean_currency(precio_base or 0)
        st.session_state["pos_desc"] = 0.0

    # =========================
    # UI: Tarjeta ejecutiva del producto seleccionado
    # =========================
    st.markdown(
        f"""
<div style="background:#ffffff;border:1px solid rgba(0,0,0,0.06);border-radius:14px;padding:14px 16px;margin:8px 0 14px 0;box-shadow:0 6px 18px rgba(0,0,0,0.05);">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
    <div>
      <div style="font-weight:900;color:#187f77;font-size:1.05rem;line-height:1.15;">{nombre}</div>
      <div style="color:#64748b;font-size:0.85rem;margin-top:4px;">ID: <b>{id_prod}</b></div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:0.85rem;color:#64748b;">Stock</div>
      <div style="font-weight:900;font-size:1.25rem;">{int(stock_disp):,}</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    cA, cB, cC, cD = st.columns([1, 1, 1, 1])
    with cA:
        cant = st.number_input("Cantidad", min_value=1.0, step=1.0, key="pos_cant")
    with cB:
        precio = st.number_input("Precio unit.", min_value=0.0, step=100.0, key="pos_precio")
    with cC:
        descuento = st.number_input("Descuento unit.", min_value=0.0, step=100.0, key="pos_desc")
    with cD:
        # Vista rápida de totales de línea (profesional)
        precio = clean_currency(precio)
        descuento = clean_currency(descuento)
        subtotal_linea = clean_currency((precio - descuento) * float(cant or 0))
        st.caption("Subtotal línea")
        st.write(f"${subtotal_linea:,.0f}")

    if st.button("➕ Agregar al carrito", type="primary", key="pos_add"):
        # si ya existe en carrito por UID (o por ID_norm), sumar cantidad
        existe = False
        for it in st.session_state.carrito:
            if (producto_uid and str(it.get("Producto_UID", "")).strip() == producto_uid) or (
                (not producto_uid) and str(it.get("ID_Producto_Norm", "")).strip() == id_norm
            ):
                it["Cantidad"] = float(it.get("Cantidad", 0) or 0) + float(cant)
                it["Precio"] = clean_currency(precio)
                it["Descuento"] = clean_currency(descuento)
                it["Subtotal"] = clean_currency((it["Precio"] - it["Descuento"]) * float(it["Cantidad"]))
                existe = True
                break

        if not existe:
            st.session_state.carrito.append(
                {
                    "Producto_UID": producto_uid,
                    "ID_Producto": id_prod,
                    "ID_Producto_Norm": id_norm,
                    "Nombre_Producto": nombre,
                    "Cantidad": float(cant),
                    "Precio": clean_currency(precio),
                    "Descuento": clean_currency(descuento),
                    "Costo": clean_currency(costo_base),
                    "Subtotal": clean_currency((clean_currency(precio) - clean_currency(descuento)) * float(cant)),
                }
            )
        st.rerun()

    # --- 3. CARRITO (FUERA del bloque de selección) ---
    st.markdown("### 🧺 Detalle de Compra")

    if not st.session_state.carrito:
        st.info("Carrito vacío. Agrega productos para continuar.")
        return

    df_car = pd.DataFrame(st.session_state.carrito).copy()

    # Tipos numéricos (evita que el editor “no aplique” bien)
    for c in ["Cantidad", "Precio", "Descuento", "Costo", "Subtotal"]:
        if c in df_car.columns:
            df_car[c] = pd.to_numeric(df_car[c], errors="coerce").fillna(0.0)

    # Columna acción para eliminar (se ve al lado en la tabla)
    if "🗑️ Eliminar" not in df_car.columns:
        df_car.insert(0, "🗑️ Eliminar", False)

    # Subtotal siempre consistente
    if "Subtotal" not in df_car.columns:
        df_car["Subtotal"] = ((df_car["Precio"] - df_car["Descuento"]) * df_car["Cantidad"]).round().astype(int)

    with st.form("pos_carrito_form", clear_on_submit=False):
        edited_car = st.data_editor(
            df_car,
            key="editor_carrito",
            num_rows="fixed",
            hide_index=True,
            column_config={
                "🗑️ Eliminar": st.column_config.CheckboxColumn("🗑️", help="Marca para eliminar esta línea"),
                "Producto_UID": st.column_config.TextColumn("Producto_UID", disabled=True, width="small"),
                "ID_Producto": st.column_config.TextColumn("ID_Producto", disabled=True, width="small"),
                "ID_Producto_Norm": st.column_config.TextColumn("ID_Producto_Norm", disabled=True, width="small"),
                "Nombre_Producto": st.column_config.TextColumn("Producto", disabled=True, width="large"),
                "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0),
                "Precio": st.column_config.NumberColumn("Precio", format="$%.0f", step=100.0),
                "Descuento": st.column_config.NumberColumn("Desc.", format="$%.0f", step=100.0),
                "Costo": st.column_config.NumberColumn("Costo", format="$%.0f", step=100.0),
                "Subtotal": st.column_config.NumberColumn("Subtotal", format="$%.0f", disabled=True),
            },
        )

        cA, cB, cC = st.columns([1, 1, 2])
        aplicar = cA.form_submit_button("💾 Aplicar cambios", type="primary")
        vaciar = cB.form_submit_button("🗑️ Vaciar carrito")

        if vaciar:
            st.session_state.carrito = []
            st.rerun()

        if aplicar:
            # 1) Eliminar marcados
            if "🗑️ Eliminar" in edited_car.columns:
                edited_car = edited_car[edited_car["🗑️ Eliminar"] != True].copy()

            # 2) Recalcular subtotal SIEMPRE (aquí se arregla “no cambia el precio”)
            for c in ["Cantidad", "Precio", "Descuento", "Costo"]:
                if c in edited_car.columns:
                    edited_car[c] = pd.to_numeric(edited_car[c], errors="coerce").fillna(0.0)

            if not edited_car.empty:
                edited_car["Subtotal"] = ((edited_car["Precio"] - edited_car["Descuento"]) * edited_car["Cantidad"]).round().astype(int)

            # 3) Guardar en session_state (sin columna de acción)
            if "🗑️ Eliminar" in edited_car.columns:
                edited_car = edited_car.drop(columns=["🗑️ Eliminar"])

            st.session_state.carrito = edited_car.to_dict("records")
            st.rerun()

    # Total (fuera del form)
    if st.session_state.carrito:
        df_total = pd.DataFrame(st.session_state.carrito)
        for c in ["Cantidad", "Precio", "Descuento", "Subtotal"]:
            if c in df_total.columns:
                df_total[c] = pd.to_numeric(df_total[c], errors="coerce").fillna(0.0)
                if c in ["Precio", "Descuento", "Subtotal"]:
                    df_total[c] = df_total[c].round().astype(int)
        if "Subtotal" not in df_total.columns and {"Precio", "Descuento", "Cantidad"}.issubset(df_total.columns):
            df_total["Subtotal"] = ((df_total["Precio"] - df_total["Descuento"]) * df_total["Cantidad"]).round().astype(int)
        total = clean_currency(df_total["Subtotal"].sum()) if "Subtotal" in df_total.columns else 0
    else:
        total = 0

    st.markdown(f"**TOTAL:** ${total:,.0f}")

    # --- 4. PAGO + FINALIZAR (FUERA del bloque del carrito) ---
    st.markdown("---")
    c1, c2 = st.columns(2)
    metodo = c1.selectbox("Pago", ["Efectivo", "Nequi", "Daviplata", "Transferencia", "Tarjeta"], key="pos_metodo")
    entrega = c2.selectbox("Entrega", ["Local", "Domicilio"], key="pos_entrega")
    dir_envio = st.text_input(
        "Dirección",
        value=st.session_state.cliente_actual.get("Direccion", "") if st.session_state.cliente_actual else "",
        key="pos_dir",
    )

    if st.button("✅ FINALIZAR VENTA", type="primary", width="stretch", key="pos_fin"):
        if not st.session_state.cliente_actual:
            st.error("Falta seleccionar cliente")
            return

        with st.spinner("Procesando..."):
            id_venta = f"VEN-{int(now_co().timestamp())}"
            fecha = now_co().strftime("%Y-%m-%d %H:%M:%S")
            carrito_cerrado = [dict(item) for item in st.session_state.carrito]

            items_str = ", ".join([f"{x['Cantidad']}x {x['Nombre_Producto']}" for x in carrito_cerrado])

            # total ya lo calculas más arriba; asegurar float
            total_num = clean_currency(total or 0)

            items_json = json.dumps(
                [
                    {
                        "Producto_UID": x.get("Producto_UID", ""),
                        "ID": x.get("ID_Producto", ""),
                        "ID_Producto_Norm": x.get("ID_Producto_Norm", ""),
                        "Nombre": x.get("Nombre_Producto", ""),
                        "Cantidad": x.get("Cantidad", 0),
                        "Precio_Unitario": clean_currency(x.get("Precio", 0) or 0),
                        "Descuento_Unitario": clean_currency(x.get("Descuento", 0) or 0),
                        "Costo_Unitario": clean_currency(x.get("Costo", 0) or 0),
                        "Subtotal_Linea": clean_currency(x.get("Subtotal", 0) or 0),
                    }
                    for x in carrito_cerrado
                ]
            )

            costo_total = clean_currency(sum(
                [clean_currency(x.get("Costo", 0) or 0) * float(x.get("Cantidad", 0) or 0) for x in carrito_cerrado]
            ))

            fila = [
                id_venta,
                fecha,
                st.session_state.cliente_actual.get("Cedula", ""),
                st.session_state.cliente_actual.get("Nombre", ""),
                entrega,
                dir_envio,
                "Pendiente" if entrega != "Local" else "Entregado",
                metodo,
                "",
                total_num,
                items_str,
                items_json,
                costo_total,
                st.session_state.mascota_seleccionada,
            ]

            registrar_venta(fila, carrito_cerrado)

            resumen_venta = construir_resumen_venta(
                id_venta=id_venta,
                fecha=fecha,
                metodo=metodo,
                entrega=entrega,
                dir_envio=dir_envio,
                cliente=st.session_state.cliente_actual,
                mascota=st.session_state.mascota_seleccionada,
                carrito=carrito_cerrado,
                total_num=total_num,
            )
            st.session_state.ultimo_pdf = generar_pdf_html(resumen_venta["venta"], resumen_venta["items"])
            st.session_state.ultimo_pdf_nombre = f"Factura_{id_venta}.pdf"
            st.session_state.ultima_venta_resumen = resumen_venta

            # ===== POST-VENTA WhatsApp (SOLO 1 mensaje) =====
            tel_raw = _get_cliente_tel(st.session_state.cliente_actual)
            msg = msg_venta_fidelidad(
                st.session_state.cliente_actual.get("Nombre", ""),
                st.session_state.mascota_seleccionada,
                items_str,
                total_num,
            )

            st.session_state.ultima_venta_id = id_venta
            link_app, link_web = build_whatsapp_links(tel_raw, msg)
            st.session_state.whatsapp_link = link_app
            st.session_state.whatsapp_link_web = link_web

            st.session_state.carrito = []
            st.success("Venta registrada. Acciones post-venta disponibles abajo.")

    # ===== UI POST-VENTA =====
    if st.session_state.get("ultima_venta_id"):
        st.markdown("### Acciones post-venta")
        resumen = st.session_state.get("ultima_venta_resumen") or {}
        venta_resumen = resumen.get("venta", {})
        items_resumen = resumen.get("items", [])
        st.markdown(
            f"""
<div style="background:linear-gradient(135deg,#0f766e 0%,#164e63 58%,#082f49 100%);border-radius:22px;padding:22px 24px;color:white;box-shadow:0 18px 42px rgba(8,47,73,0.22);margin:10px 0 16px 0;">
  <div style="display:flex;justify-content:space-between;gap:20px;align-items:flex-start;flex-wrap:wrap;">
    <div>
      <div style="font-size:0.78rem;letter-spacing:.14em;text-transform:uppercase;opacity:.8;font-weight:700;">Venta confirmada</div>
      <div style="font-size:1.9rem;font-weight:900;line-height:1.05;margin:6px 0 10px 0;">{venta_resumen.get('ID', st.session_state.get('ultima_venta_id', ''))}</div>
      <div style="font-size:1rem;opacity:.92;max-width:720px;">Factura lista para descargar. Cliente: <b>{venta_resumen.get('Cliente', 'Consumidor Final')}</b> · Mascota: <b>{venta_resumen.get('Mascota', 'Sin registro')}</b></div>
    </div>
    <div style="min-width:220px;background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.18);border-radius:18px;padding:14px 16px;backdrop-filter:blur(8px);">
      <div style="font-size:0.78rem;text-transform:uppercase;letter-spacing:.08em;opacity:.8;">Total cobrado</div>
      <div style="font-size:1.8rem;font-weight:900;margin-top:4px;">${venta_resumen.get('Total', 0):,.0f}</div>
      <div style="margin-top:6px;font-size:0.94rem;opacity:.9;">{venta_resumen.get('Total_Items', len(items_resumen))} líneas · {venta_resumen.get('Unidades', 0):,.0f} unidades</div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        if items_resumen:
            preview_items = pd.DataFrame(items_resumen)[["Nombre_Producto", "Cantidad", "Precio", "Descuento", "Subtotal"]].copy()
            st.dataframe(
                preview_items,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Nombre_Producto": st.column_config.TextColumn("Producto", width="large"),
                    "Cantidad": st.column_config.NumberColumn("Cant.", format="%.0f"),
                    "Precio": st.column_config.NumberColumn("Precio", format="$%.0f"),
                    "Descuento": st.column_config.NumberColumn("Desc.", format="$%.0f"),
                    "Subtotal": st.column_config.NumberColumn("Subtotal", format="$%.0f"),
                },
            )
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            st.download_button(
                "📄 Descargar factura PDF",
                data=st.session_state.get("ultimo_pdf") or b"",
                file_name=st.session_state.get("ultimo_pdf_nombre") or f"Factura_{st.session_state.get('ultima_venta_id', 'venta')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                disabled=not bool(st.session_state.get("ultimo_pdf")),
                key="pos_download_pdf",
            )
            if not st.session_state.get("ultimo_pdf"):
                st.caption("La venta se guardó, pero el PDF no se pudo generar en este entorno.")
        with c2:
            if st.session_state.get("whatsapp_link"):
                st.link_button("📲 Enviar WhatsApp (Celular / App)", st.session_state["whatsapp_link"], type="secondary", use_container_width=True)
            else:
                st.warning("No hay teléfono válido para WhatsApp en este cliente.")
        with c3:
            if st.session_state.get("whatsapp_link_web"):
                st.link_button("💻 Abrir WhatsApp Web (PC)", st.session_state["whatsapp_link_web"], use_container_width=True)
        st.button(
            "✨ Nueva venta limpia",
            key="pos_nueva_venta",
            use_container_width=True,
            on_click=reset_pos_workflow,
            kwargs={"clear_cliente": True},
        )

def _get_cliente_tel(cliente: dict) -> str:
    """Obtiene teléfono de forma robusta desde el dict de cliente."""
    if not cliente:
        return ""
    for k in ["Telefono", "Teléfono", "Celular", "Movil", "Móvil"]:
        v = cliente.get(k, "")
        if v and str(v).strip():
            return str(v).strip()
    return ""

def build_whatsapp_links(telefono: str, mensaje: str) -> tuple[str | None, str | None]:
    """Links estables para celular (wa.me) y PC (WhatsApp Web)."""
    if not telefono:
        return None, None
    tel = limpiar_tel(telefono)
    if not tel or len(tel) < 7:
        return None, None
    encoded = urllib.parse.quote(str(mensaje or ""), safe="")
    return (
        f"https://wa.me/{tel}?text={encoded}",
        f"https://web.whatsapp.com/send?phone={tel}&text={encoded}",
    )

# ✅ DEFINICIÓN FINAL (única) DEL MENSAJE POST-VENTA
# (si existían versiones anteriores, esta las sobre-escribe y elimina el “doble mensaje”)
def msg_venta(nombre: str, mascota: str, items_str: str, total: float) -> str:
    """
    Mensaje post-venta WhatsApp (bonito, corto, con emojis) compatible con WhatsApp Web/App.
    """
    nombre = (nombre or "Cliente").strip()
    mascota = (mascota or "tu peludito").strip()
    items_bullets = _wa_items_bullets(items_str)

    return (
        f"Hola *{nombre}* 👋🐾\n\n"
        f"¡Gracias por tu compra en *Bigotes y Paticas*! 💚\n"
        f"Hoy consentimos a *{mascota}* ✨\n\n"
        f"🛍️ *Productos:*\n{items_bullets}\n\n"
        f"💳 *Total:* ${float(total or 0):,.0f}\n\n"
        f"Si quieres, te ayudo con recomendaciones para {mascota} (alimento, premios y porciones). 🐶🐱\n"
        f"¡Gracias por confiar en nosotros! 🙌"
    )

def msg_venta_fidelidad(nombre: str, mascota: str, items_str: str, total: float) -> str:
    return msg_venta(nombre, mascota, items_str, total)

def tab_clientes_ui():
    st.header("Gestión de Clientes")
    # Formulario creación
    with st.expander("Nuevo Cliente"):
        with st.form("nuevo_cli"):
            cedula = st.text_input("Cédula")
            nombre = st.text_input("Nombre")
            tel = st.text_input("Teléfono")
            email = st.text_input("Email")
            dir = st.text_input("Dirección")
            mascota = st.text_input("Nombre Mascota Principal")
            tipo = st.selectbox("Tipo", ["Perro", "Gato", "Otro"])
            cumple = st.date_input("Cumpleaños Mascota")
            
            if st.form_submit_button("Guardar"):
                # Crear JSON simple
                info_m = json.dumps([{"Nombre": mascota, "Tipo": tipo, "Cumpleaños": str(cumple)}])
                fila = [cedula, nombre, tel, email, dir, mascota, tipo, str(cumple), now_co().strftime("%Y-%m-%d"), info_m]
                
                # Check si existe (local)
                df = st.session_state.db['cli']
                existe = df[df['Cedula'].astype(str) == str(cedula)]
                
                if not existe.empty:
                    # Update (más complejo, requeriría row_idx, por simplicidad en versión fixed sugerimos append o avisar)
                    st.warning("Cliente ya existe con esa cédula (Lógica update pendiente)")
                else:
                    registrar_cliente(fila)
                    st.success("Cliente guardado")
                    
                    # Generar link bienvenida
                    link = f"https://wa.me/{limpiar_tel(tel)}?text={urllib.parse.quote(msg_bienvenida(nombre, mascota))}"
                    st.markdown(f"[📲 Enviar Bienvenida]({link})")

    st.dataframe(st.session_state.db['cli'], use_container_width=True)

    # Botón para limpiar selección y permitir crear un nuevo cliente
    if st.button("🆕 Nuevo Cliente", help="Registrar un cliente desde cero"):
        st.session_state.cliente_actual = None
        st.session_state.mascota_seleccionada = None
        st.rerun()

def tab_despachos_ui():
    st.header("🚚 Despachos")
    df = st.session_state.db['ven']
    pendientes = df[df['Estado_Envio'].isin(["Pendiente", "En camino"])]
    
    if pendientes.empty:
        st.info("No hay despachos pendientes")
    else:
        st.dataframe(pendientes)
        sel_id = st.selectbox("Actualizar ID", pendientes['ID_Venta'])
        nuevo = st.selectbox("Nuevo Estado", ["Entregado", "Pagado", "Cancelado"])
        if st.button("Actualizar"):
            ok = actualizar_estado_envio(sel_id, nuevo)
            if ok: 
                st.success("Actualizado")
                st.rerun()
            else: st.error("Error al actualizar")

def tab_facturas_ui():
    st.header("Facturas y Reimpresiones")
    df = st.session_state.db['ven'].copy()
    if df.empty:
        st.info("No hay ventas registradas todavía.")
        return

    if 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.sort_values('Fecha', ascending=False)
        fechas_validas = df['Fecha'].dropna()
    else:
        fechas_validas = pd.Series(dtype='datetime64[ns]')

    texto = st.text_input("Buscar venta", placeholder="Cliente, cédula, mascota o ID de venta", key="buscar_factura_texto")
    c1, c2 = st.columns(2)
    usar_rango = c1.toggle("Filtrar por rango de fechas", value=False, key="facturas_filtrar_fechas")

    fecha_ini = fecha_fin = None
    if usar_rango and not fechas_validas.empty:
        min_fecha = fechas_validas.min().date()
        max_fecha = fechas_validas.max().date()
        fecha_ini = c1.date_input("Desde", value=min_fecha, min_value=min_fecha, max_value=max_fecha, key="facturas_desde")
        fecha_fin = c2.date_input("Hasta", value=max_fecha, min_value=min_fecha, max_value=max_fecha, key="facturas_hasta")
    else:
        c2.caption("Activa el rango solo cuando quieras acotar la búsqueda.")

    filtrado = df.copy()
    if usar_rango and fecha_ini and fecha_fin and 'Fecha' in filtrado.columns:
        if fecha_ini > fecha_fin:
            fecha_ini, fecha_fin = fecha_fin, fecha_ini
        filtrado = filtrado[(filtrado['Fecha'].dt.date >= fecha_ini) & (filtrado['Fecha'].dt.date <= fecha_fin)].copy()

    if texto.strip():
        q = texto.strip()
        columnas_busqueda = [col for col in ["ID_Venta", "Nombre_Cliente", "Cedula_Cliente", "Mascota", "Items", "Direccion"] if col in filtrado.columns]
        if columnas_busqueda:
            mask = pd.Series(False, index=filtrado.index)
            for col in columnas_busqueda:
                mask = mask | filtrado[col].astype(str).str.contains(q, case=False, na=False)
            filtrado = filtrado[mask].copy()

    if filtrado.empty:
        st.info("No encontré ventas con esos filtros.")
        return

    mostrar_cols = [col for col in ["Fecha", "ID_Venta", "Nombre_Cliente", "Cedula_Cliente", "Mascota", "Metodo_Pago", "Total"] if col in filtrado.columns]
    vista = filtrado[mostrar_cols].copy()
    st.dataframe(
        vista,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fecha": st.column_config.DatetimeColumn("Fecha", format="YYYY-MM-DD HH:mm"),
            "Total": st.column_config.NumberColumn("Total", format="$%.0f"),
        },
    )

    id_col = "ID_Venta" if "ID_Venta" in filtrado.columns else filtrado.columns[0]
    selected_id = st.selectbox(
        "Selecciona la venta para descargar la factura",
        filtrado[id_col].astype(str).tolist(),
        key="facturas_select_id",
    )
    venta_sel = filtrado[filtrado[id_col].astype(str) == str(selected_id)].iloc[0]
    resumen = construir_resumen_venta_desde_fila(venta_sel)
    pdf_data = generar_pdf_html(resumen["venta"], resumen["items"])

    st.markdown(
        f"""
<div style="background:linear-gradient(135deg,#0f766e 0%,#164e63 58%,#082f49 100%);border-radius:20px;padding:18px 20px;color:white;box-shadow:0 14px 34px rgba(8,47,73,0.18);margin:12px 0 14px 0;">
  <div style="display:flex;justify-content:space-between;gap:18px;align-items:flex-start;flex-wrap:wrap;">
    <div>
      <div style="font-size:.76rem;letter-spacing:.14em;text-transform:uppercase;opacity:.78;font-weight:700;">Factura histórica</div>
      <div style="font-size:1.55rem;font-weight:900;margin-top:4px;">{resumen['venta'].get('ID', '')}</div>
      <div style="font-size:.98rem;opacity:.92;max-width:720px;">{resumen['venta'].get('Cliente', 'Consumidor Final')} · {resumen['venta'].get('Fecha', '')}</div>
    </div>
    <div style="min-width:200px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.16);border-radius:16px;padding:12px 14px;">
      <div style="font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;opacity:.8;">Total</div>
      <div style="font-size:1.55rem;font-weight:900;">${resumen['venta'].get('Total', 0):,.0f}</div>
      <div style="font-size:.9rem;opacity:.88;">{resumen['venta'].get('Total_Items', 0)} artículos</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if resumen["items"]:
        st.dataframe(
            pd.DataFrame(resumen["items"])[["Nombre_Producto", "Cantidad", "Precio", "Descuento", "Subtotal"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Nombre_Producto": st.column_config.TextColumn("Producto", width="large"),
                "Cantidad": st.column_config.NumberColumn("Cant.", format="%.0f"),
                "Precio": st.column_config.NumberColumn("Precio", format="$%.0f"),
                "Descuento": st.column_config.NumberColumn("Desc.", format="$%.0f"),
                "Subtotal": st.column_config.NumberColumn("Subtotal", format="$%.0f"),
            },
        )

    st.download_button(
        "📄 Descargar factura PDF",
        data=pdf_data or b"",
        file_name=f"Factura_{resumen['venta'].get('ID', 'venta')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        disabled=not bool(pdf_data),
        key="hist_download_pdf",
    )
    if not pdf_data:
        st.caption("No se pudo generar el PDF para esta venta. Revisa si el detalle guardado está incompleto.")

def tab_gastos_ui():
    st.header("Gastos")
    with st.form("gastos"):
        tipo = st.selectbox("Tipo", ["Variable", "Fijo"])
        cat = st.selectbox("Categoría", ["Inventario", "Servicios", "Nómina", "Otro"])
        desc = st.text_input("Descripción")
        monto = st.number_input("Monto", min_value=0.0)
        metodo = st.selectbox("Pago", ["Efectivo", "Bancos", "Nequi"])
        
        if st.form_submit_button("Registrar"):
            ts = int(now_co().timestamp())
            fila = [f"GAS-{ts}", now_co().strftime("%Y-%m-%d"), tipo, cat, desc, monto, metodo, ""]
            registrar_gasto(fila)
            st.success("Gasto guardado")

def tab_cuadre_ui():
    st.header("Cuadre de Caja")

    # --- NUEVO: Registro de Gastos/Pagos desde Cuadre de Caja ---
    with st.expander("Registrar Gasto o Pago (afecta cuadre)", expanded=False):
        with st.form("gasto_cuadre"):
            tipo = st.selectbox("Tipo", ["Variable", "Fijo"])
            cat = st.selectbox("Categoría", ["Inventario", "Servicios", "Nómina", "Otro"])
            desc = st.text_input("Descripción")
            monto = st.number_input("Monto", min_value=0.0)
            metodo = st.selectbox("Pago", ["Efectivo", "Bancos", "Nequi"])
            
            if st.form_submit_button("Registrar Gasto/Pago"):
                ts = int(now_co().timestamp())
                fila = [f"GAS-{ts}", now_co().strftime("%Y-%m-%d"), tipo, cat, desc, monto, metodo, ""]
                registrar_gasto(fila)
                st.success("Gasto/Pago guardado y descontado del cuadre")
                st.rerun()

    df_ven = st.session_state.db['ven']
    df_gas = st.session_state.db['gas']
    df_cie = st.session_state.db['cie']

    fecha = st.date_input("Fecha", now_co().date())

    # --- 1. Saldos previos (último cierre) ---
    base_inicial = 0.0
    if not df_cie.empty:
        df_cie['Fecha_dt'] = pd.to_datetime(df_cie['Fecha'], errors='coerce').dt.date
        prev_cierre = df_cie[df_cie['Fecha_dt'] < fecha].sort_values('Fecha_dt', ascending=False)
        if not prev_cierre.empty:
            base_inicial = prev_cierre.iloc[0]['Saldo_Real']
    # Forzar tipo float
    try:
        base_inicial = float(base_inicial)
    except Exception:
        base_inicial = 0.0

    # --- 2. Filtros locales ---
    df_ven['Fecha_dt'] = pd.to_datetime(df_ven['Fecha']).dt.date
    if 'Fecha' in df_gas.columns:
        df_gas['Fecha_dt'] = pd.to_datetime(df_gas['Fecha'], errors='coerce').dt.date
    else:
        df_gas['Fecha_dt'] = None

    v_dia = df_ven[df_ven['Fecha_dt'] == fecha]
    g_dia = df_gas[df_gas['Fecha_dt'] == fecha]

    # --- 3. Ventas por método ---
    v_efec = v_dia[v_dia['Metodo_Pago'] == 'Efectivo']['Total'].sum()
    v_tarj = v_dia[v_dia['Metodo_Pago'] == 'Tarjeta']['Total'].sum()
    v_digi = v_dia[v_dia['Metodo_Pago'].isin(['Nequi', 'Daviplata', 'Transferencia'])]['Total'].sum()
    v_elec = v_tarj + v_digi

    # --- 4. Gastos efectivo ---
    g_efec = g_dia[g_dia['Metodo_Pago'] == 'Efectivo']['Monto'].sum()

    # --- 5. Costo mercancía y margen ---
    costo_merc = v_dia['Costo_Total'].sum() if 'Costo_Total' in v_dia.columns else 0.0
    margen_ganado = v_dia['Total'].sum() - costo_merc
    margen_pct = (margen_ganado / costo_merc * 100) if costo_merc > 0 else 0

    # --- 6. KPIs ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Ventas Efectivo", f"${v_efec:,.0f}")
    c2.metric("Ventas Electrónico", f"${v_elec:,.0f}")
    c3.metric("Ventas Tarjeta", f"${v_tarj:,.0f}")
    c4.metric("Gastos Efectivo", f"${g_efec:,.0f}")
    c5.metric("Margen Ganado", f"${margen_ganado:,.0f}", f"{margen_pct:.1f}%")

    st.markdown("---")
    with st.form("cierre_caja"):
        base = st.number_input("Base Inicial", value=base_inicial, min_value=0.0)
        bancos = st.number_input("Enviado a Bancos", 0.0)
        real = st.number_input("Saldo Real (Conteo)", 0.0)
        notas = st.text_area("Notas")

        teorico = base + v_efec - g_efec - bancos
        dif = real - teorico
        st.caption(f"Teórico: ${teorico:,.0f} | Diferencia: ${dif:,.0f}")

        if st.form_submit_button("Guardar Cierre"):
            sh = conectar_google_sheets()
            ws_cie = obtener_worksheets(sh)["cie"]
            fila = [
                fecha.strftime("%Y-%m-%d"),
                now_co().strftime("%H:%M:%S"),
                base,
                v_efec,
                v_elec,
                g_efec,
                bancos,
                teorico,
                real,
                dif,
                notas,
                costo_merc,
                margen_ganado
            ]
            fila = [sanitizar_para_sheet(x) for x in fila]
            safe_api_call(ws_cie.append_row, fila)
            st.success("Cierre guardado en la nube")

def tab_resumen_ui():
    st.header("Resumen Gerencial")
    df = st.session_state.db['ven']
    if not df.empty:
        total = df['Total'].sum()
        st.metric("Ventas Históricas", f"${total:,.0f}")
        
        # Grafico simple
        df['Fecha_D'] = pd.to_datetime(df['Fecha']).dt.date
        diario = df.groupby('Fecha_D')['Total'].sum()
        st.bar_chart(diario)

# ==========================================
# 6. MAIN APP
# ==========================================

def main():
    # Inicialización de DB
    if 'db' not in st.session_state:
        cargar_datos_iniciales()
    
    # Barra Lateral
    with st.sidebar:
        st.title("Nexus Pro")
        if st.button("🔄 Sincronizar Datos", help="Trae cambios de la nube si alguien más editó el Excel"):
            st.cache_resource.clear()
            cargar_datos_iniciales()
            st.rerun()
        st.caption(f"Última sinc: {st.session_state.get('ultima_sincronizacion', 'Nunca').strftime('%H:%M:%S')}")
        
        st.divider()
        if st.button("🧱 Reparar IDs (Producto_UID + Norm)"):
            asegurar_ids_inventario_nube()

    # Tabs
    tabs = st.tabs(["🛒 POS", "🧾 Facturas", "👤 Clientes", "🚚 Despachos", "💳 Gastos", "💵 Cuadre", "📊 Resumen"])
    
    with tabs[0]: tab_pos()
    with tabs[1]: tab_facturas_ui()
    with tabs[2]: tab_clientes_ui()
    with tabs[3]: tab_despachos_ui()
    with tabs[4]: tab_gastos_ui()
    with tabs[5]: tab_cuadre_ui()
    with tabs[6]: tab_resumen_ui()

if __name__ == "__main__":
    main()