import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import gspread
import numpy as np
import time
from datetime import datetime
import math
import uuid

try:
    # si normalizar_id_producto vive en el módulo principal
    from BigotesyPaticas import normalizar_id_producto
except Exception:
    # fallback defensivo si ya existe localmente con otro nombre
    def normalizar_id_producto(x):
        return str(x or "").strip().upper()

# ==========================================
# 3. FUNCIONES DE ACTUALIZACIÓN DE MAPEO PROVEEDORES
# ==========================================

def _upsert_maestro_proveedores(ws_map, meta_xml, sku_prov, sku_interno, producto_uid, factor, costo_prov, iva_pct):
    """
    Inserta o actualiza la relación entre SKU_Proveedor, SKU_Interno y Producto_UID en Maestro_Proveedores.
    Si ya existe la fila (por SKU_Proveedor y SKU_Interno), actualiza los datos; si no, inserta una nueva.
    """
    try:
        headers = _ensure_headers(ws_map, [
            "ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor", "SKU_Interno", "Producto_UID",
            "Factor_Pack", "Ultima_Actualizacion", "Email", "Costo_Proveedor", "Ultimo_IVA"
        ])
        recs = ws_map.get_all_records()
        df = pd.DataFrame(recs)
        # Normalizar columnas clave
        for col in ["SKU_Proveedor", "SKU_Interno", "Producto_UID"]:
            if col not in df.columns:
                df[col] = ""
        # Buscar si ya existe la fila
        mask = (
            (df["SKU_Proveedor"].astype(str).str.strip().str.upper() == str(sku_prov).strip().upper()) &
            (df["SKU_Interno"].astype(str).str.strip().str.upper() == str(sku_interno).strip().upper())
        )
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        id_prov = meta_xml.get("ID_Proveedor", "") if meta_xml else ""
        # Usar 'Proveedor' si 'Nombre_Proveedor' no existe
        nombre_prov = meta_xml.get("Nombre_Proveedor") or meta_xml.get("Proveedor", "") if meta_xml else ""
        email = meta_xml.get("Email_Proveedor", "") if meta_xml else ""
        row_data = [
            id_prov,
            nombre_prov,
            sku_prov,
            sku_interno,
            producto_uid,
            factor,
            now,
            email,
            costo_prov,
            iva_pct
        ]
        if mask.any():
            # Actualizar fila existente
            idx = mask[mask].index[0]
            ws_map.update(f'A{idx+2}:J{idx+2}', [row_data])
        else:
            # Insertar nueva fila
            ws_map.append_row(row_data)
    except Exception as e:
        st.warning(f"Error actualizando Maestro_Proveedores: {e}")
# 1. CONFIGURACIÓN Y ESTILOS (NEXUS PRO THEME)
# ==========================================

COLOR_PRIMARIO = "#187f77"      # Cian Oscuro
COLOR_SECUNDARIO = "#125e58"    # Variante oscura
COLOR_ACENTO = "#f5a641"        # Naranja
COLOR_FONDO = "#f8f9fa"         # Gris claro
COLOR_BLANCO = "#ffffff"

st.set_page_config(
    page_title="Compras & Recepción | Nexus Pro", 
    page_icon="📥", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    .stApp {{ background-color: {COLOR_FONDO}; font-family: 'Inter', sans-serif; }}
    
    h1, h2, h3 {{ color: {COLOR_PRIMARIO}; font-weight: 700; }}
    
    .main-header {{ 
        font-size: 2.5rem; 
        font-weight: 800; 
        color: {COLOR_PRIMARIO}; 
        margin-top: 1rem;
        margin-bottom: 0.5rem; 
        text-align: center; 
    }}
    
    .sub-header {{ 
        font-size: 1.1rem; 
        color: #64748b; 
        margin-bottom: 2rem; 
        text-align: center; 
    }}

    .metric-container {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }}
    .metric-card {{
        background-color: {COLOR_BLANCO};
        border-radius: 12px;
        padding: 20px;
        width: 30%;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid {COLOR_ACENTO};
        text-align: center;
    }}
    .metric-label {{ color: #64748b; font-size: 0.85rem; text-transform: uppercase; font-weight: 600; margin-bottom: 5px; }}
    .metric-value {{ color: {COLOR_PRIMARIO}; font-size: 1.5rem; font-weight: 800; }}

    .stButton>button {{ border-radius: 8px; font-weight: bold; height: 3rem; transition: all 0.3s ease; }}
    div[data-testid="stExpander"] {{ background-color: {COLOR_BLANCO}; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: none; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UTILIDADES MATEMÁTICAS
# ==========================================

MARGEN_BRUTO_OBJ = 0.20  # 20%

def precio_con_margen(costo_neto_unit: float, margen: float = MARGEN_BRUTO_OBJ) -> float:
    """Margen bruto sobre precio: P = C / (1 - m)."""
    try:
        c = float(costo_neto_unit or 0.0)
        m = float(margen or 0.0)
        if c <= 0:
            return 0.0
        m = max(0.0, min(0.95, m))
        return c / (1.0 - m)
    except Exception:
        return 0.0

def _fmt_qty(x):
    """Evita 1.0, 2.0 cuando son enteros."""
    try:
        f = float(x)
        return int(f) if f.is_integer() else f
    except Exception:
        return x

def _get_meta_safe():
    """Meta robusto (evita KeyError en step 2)."""
    meta = st.session_state.get("invoice_meta") or {}
    return {
        "Proveedor": meta.get("Proveedor", "").strip(),
        "ID_Proveedor": meta.get("ID_Proveedor", "").strip(),
        "Folio": meta.get("Folio", "").strip(),
        "Total": float(meta.get("Total", 0.0) or 0.0),
    }

def normalizar_str(valor):
    if pd.isna(valor) or valor == "": return ""
    return str(valor).strip().upper()

def clean_currency(val):
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').strip()
        if not val: return 0.0
        try:
            if ',' in val and '.' in val:
                if val.find('.') < val.find(','): val = val.replace('.', '').replace(',', '.')
                else: val = val.replace(',', '')
            elif ',' in val: val = val.replace(',', '.')
            return float(val)
        except: return 0.0
    return 0.0

def sanitizar_para_sheet(val):
    if isinstance(val, (np.int64, np.int32)): return int(val)
    if isinstance(val, (np.float64, np.float32)): return float(val)
    return val

def redondear_centena(valor):
    if not valor: return 0.0
    return math.ceil(valor / 100.0) * 100.0

# ==========================================
# 3. CONEXIÓN A GOOGLE SHEETS
# ==========================================

def _ensure_headers(ws, required_cols: list[str]) -> list[str]:
    """
    Asegura que existan columnas en la fila 1 (headers) de una worksheet.
    Retorna la lista final de headers.
    """
    headers = ws.row_values(1) or []
    headers = [h.strip() for h in headers]

    changed = False
    for col in required_cols:
        if col not in headers:
            headers.append(col)
            ws.update_cell(1, len(headers), col)
            changed = True

    return ws.row_values(1) if changed else headers

def _build_inv_indexes(ws_inv):
    """
    Índices para Inventario (Sheets) usados por compras XML/manual.
    Retorna: headers, idx_uid, idx_id, idx_norm, idx_stock, idx_costo, idx_precio, idx_nombre, uid_to_row, norm_to_row, norm_to_uid
    """
    headers = _ensure_headers(
        ws_inv,
        ["Producto_UID", "ID_Producto", "ID_Producto_Norm", "Nombre", "Stock", "Costo", "Precio"]
    )

    data = ws_inv.get_all_values() or []
    if not data:
        idx_uid = headers.index("Producto_UID")
        idx_id = headers.index("ID_Producto")
        idx_norm = headers.index("ID_Producto_Norm")
        idx_nombre = headers.index("Nombre")
        idx_stock = headers.index("Stock")
        idx_costo = headers.index("Costo")
        idx_precio = headers.index("Precio")
        return (headers, idx_uid, idx_id, idx_norm, idx_stock, idx_costo, idx_precio, idx_nombre, {}, {}, {})

    headers = data[0]

    # Reasegurar por si la fila 1 está vacía en la hoja
    if "Producto_UID" not in headers or "ID_Producto" not in headers or "ID_Producto_Norm" not in headers:
        headers = _ensure_headers(
            ws_inv,
            ["Producto_UID", "ID_Producto", "ID_Producto_Norm", "Nombre", "Stock", "Costo", "Precio"]
        )
        data = ws_inv.get_all_values() or []
        headers = data[0] if data else headers

    idx_uid = headers.index("Producto_UID")
    idx_id = headers.index("ID_Producto")
    idx_norm = headers.index("ID_Producto_Norm")
    idx_nombre = headers.index("Nombre") if "Nombre" in headers else None
    idx_stock = headers.index("Stock") if "Stock" in headers else None
    idx_costo = headers.index("Costo") if "Costo" in headers else None
    idx_precio = headers.index("Precio") if "Precio" in headers else None

    uid_to_row, norm_to_row, norm_to_uid = {}, {}, {}

    for sheet_row, r in enumerate(data[1:], start=2):
        uid = str(r[idx_uid]).strip() if idx_uid < len(r) else ""
        pid = str(r[idx_id]).strip() if idx_id < len(r) else ""
        norm = str(r[idx_norm]).strip() if idx_norm < len(r) else ""

        if not norm and pid:
            norm = normalizar_str(pid) # Fallback simple

        if uid:
            uid_to_row[uid] = sheet_row
        if norm:
            norm_to_row[norm] = sheet_row
        if uid and norm:
            norm_to_uid[norm] = uid

    return (
        headers,
        idx_uid, idx_id, idx_norm, idx_stock, idx_costo, idx_precio, idx_nombre,
        uid_to_row, norm_to_row, norm_to_uid
    )

@st.cache_resource(ttl=600)
def conectar_sheets():
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Falta configuración en secrets.toml")
            st.stop()

        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])

        try:
            ws_inv = sh.worksheet("Inventario")
        except:
            st.error("Falta hoja 'Inventario'")
            st.stop()

        # ✅ ya no falla: helper existe
        _ensure_headers(ws_inv, ["Producto_UID", "ID_Producto", "ID_Producto_Norm", "Stock", "Costo", "Precio", "Nombre"])

        try: ws_map = sh.worksheet("Maestro_Proveedores")
        except:
            ws_map = sh.add_worksheet("Maestro_Proveedores", 1000, 10)
            ws_map.append_row([
                "ID_Proveedor", "Nombre_Proveedor", "SKU_Proveedor",
                "SKU_Interno", "Producto_UID", "Factor_Pack",
                "Ultima_Actualizacion", "Email", "Costo_Proveedor", "Ultimo_IVA"
            ])

        # Asegurar headers mínimos Maestro_Proveedores (por si ya existe vieja)
        _ensure_headers(ws_map, ["Producto_UID", "SKU_Interno", "Factor_Pack", "Ultimo_IVA", "Costo_Proveedor"])

        try: ws_hist = sh.worksheet("Historial_Recepciones")
        except:
            ws_hist = sh.add_worksheet("Historial_Recepciones", 1000, 7)
            ws_hist.append_row(["Fecha", "Folio", "Proveedor", "Items", "Total", "Usuario", "Estado"])
        
        try: ws_gas = sh.worksheet("Gastos")
        except:
            ws_gas = sh.add_worksheet("Gastos", 1000, 8)
            ws_gas.append_row(["ID_Gasto","Fecha","Tipo_Gasto","Categoria","Descripcion","Monto","Metodo_Pago","Banco_Origen"])

        return sh, ws_inv, ws_map, ws_hist, ws_gas
    except Exception as e:
        st.error(f"Error Conexión Sheets: {e}")
        st.stop()

# ==========================================
# 4. CEREBRO Y MEMORIA
# ==========================================

@st.cache_data(ttl=120)
def cargar_proveedores(_ws_map) -> tuple[list[str], dict[str, str]]:
    """
    Retorna:
      - lista_nombres (para selectbox)
      - nombre_to_id (Nombre_Proveedor -> ID_Proveedor)
    """
    try:
        recs = _ws_map.get_all_records()
        if not recs:
            return (["(Nuevo proveedor)"], {})
        df = pd.DataFrame(recs)
        if "Nombre_Proveedor" not in df.columns:
            return (["(Nuevo proveedor)"], {})
        df["Nombre_Proveedor"] = df["Nombre_Proveedor"].fillna("").astype(str).str.strip()
        if "ID_Proveedor" in df.columns:
            df["ID_Proveedor"] = df["ID_Proveedor"].fillna("").astype(str).str.strip()
        df = df[df["Nombre_Proveedor"] != ""].drop_duplicates(subset=["Nombre_Proveedor"])
        nombres = sorted(df["Nombre_Proveedor"].tolist())
        nombres = ["(Nuevo proveedor)"] + nombres
        nombre_to_id = {}
        if "ID_Proveedor" in df.columns:
            nombre_to_id = dict(zip(df["Nombre_Proveedor"], df["ID_Proveedor"]))
        return (nombres, nombre_to_id)
    except Exception:
        return (["(Nuevo proveedor)"], {})

@st.cache_data(ttl=60)
def cargar_cerebro(_ws_inv, _ws_map):
    try:
        d_inv = _ws_inv.get_all_records()
        df_inv = pd.DataFrame(d_inv)
        col_id = next((c for c in df_inv.columns if 'ID' in c or 'SKU' in c), 'ID_Producto')
        col_nm = next((c for c in df_inv.columns if 'Nombre' in c), 'Nombre')
        df_inv['Display'] = df_inv[col_id].astype(str) + " | " + df_inv[col_nm].astype(str)
        lista_prods = sorted(df_inv['Display'].unique().tolist())
        lista_prods.insert(0, "NUEVO (Crear Producto)")
        dict_prods = pd.Series(df_inv['Display'].values, index=df_inv[col_id].apply(normalizar_id_producto)).to_dict()
    except:
        lista_prods, dict_prods = ["NUEVO (Crear Producto)"], {}

    memoria = {}
    try:
        d_map = _ws_map.get_all_records()
        for r in d_map:
            k = f"{normalizar_str(r.get('ID_Proveedor'))}_{normalizar_str(r.get('SKU_Proveedor'))}"
            iva_guardado = r.get('Ultimo_IVA')
            iva_val = int(float(iva_guardado)) if iva_guardado in [0, 5, 19, "0", "5", "19", 0.0, 5.0, 19.0] else 0
            memoria[k] = {
                "SKU_Interno": normalizar_str(r.get("SKU_Interno")),
                "Producto_UID": str(r.get("Producto_UID", "")).strip(),   # ✅ NUEVO
                "Factor": float(r.get("Factor_Pack", 1)) if r.get("Factor_Pack") else 1.0,
                "IVA_Aprendido": iva_val
            }
    except:
        pass

    return lista_prods, dict_prods, memoria

# ==========================================
# 5. PARSER XML COLOMBIA
# ==========================================

def parsear_xml_colombia(archivo):
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()
        ns_map = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }

        invoice_root = root
        if 'AttachedDocument' in root.tag:
            desc_node = root.find('.//cac:Attachment/cac:ExternalReference/cbc:Description', ns_map)
            if desc_node is not None and desc_node.text and "<Invoice" in desc_node.text:
                xml_string = desc_node.text.strip()
                xml_string = xml_string[xml_string.find("<Invoice"):]
                invoice_root = ET.fromstring(xml_string)

        ns = ns_map 
        try:
            prov_node = invoice_root.find('.//cac:AccountingSupplierParty/cac:Party', ns)
            prov_tax = prov_node.find('.//cac:PartyTaxScheme', ns)
            nombre_prov = prov_tax.find('cbc:RegistrationName', ns).text
            nit_prov = prov_tax.find('cbc:CompanyID', ns).text
        except:
            nombre_prov = "Proveedor Desconocido"
            nit_prov = "000000"

        try: folio = invoice_root.find('cbc:ID', ns).text
        except: folio = "S/F"

        try: total_pagar_factura = float(invoice_root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns).text)
        except: total_pagar_factura = 0.0

        items = []
        lines = invoice_root.findall('.//cac:InvoiceLine', ns)
        
        for line in lines:
            try:
                qty = float(line.find('cbc:InvoicedQuantity', ns).text)
                price_node = line.find('.//cac:Price/cbc:PriceAmount', ns)
                base_price = float(price_node.text) if price_node is not None else 0.0
                
                discount_amount = 0.0
                allowances = line.findall('.//cac:AllowanceCharge', ns)
                if allowances:
                    first_allowance = allowances[0] 
                    if first_allowance.find('cbc:ChargeIndicator', ns).text == 'false':
                        val = first_allowance.find('cbc:Amount', ns).text
                        discount_amount = float(val) if val else 0.0

                final_base_price = base_price - discount_amount
                
                item_node = line.find('cac:Item', ns)
                desc = item_node.find('cbc:Description', ns).text
                
                sku_prov = "S/C"
                std_id = item_node.find('.//cac:StandardItemIdentification/cbc:ID', ns)
                seller_id = item_node.find('.//cac:SellersItemIdentification/cbc:ID', ns)
                
                if std_id is not None and std_id.text: sku_prov = std_id.text
                elif seller_id is not None: sku_prov = seller_id.text
                
                items.append({
                    'SKU_Proveedor': sku_prov,
                    'Descripcion': desc,
                    'Cantidad': qty,
                    'Costo_Base_Unitario': final_base_price 
                })
            except: continue

        return {
            'Proveedor': nombre_prov,
            'ID_Proveedor': nit_prov,
            'Folio': folio,
            'Total': total_pagar_factura,
            'Items': items
        }

    except Exception as e:
        st.error(f"Error parseando XML: {e}")
        return None

# ==========================================
# 6. LÓGICA DE GUARDADO
# ==========================================

def procesar_guardado(ws_map, ws_inv, ws_hist, ws_gas, df_final, meta_xml, info_pago):
    """
    Garantía: cada renglón termina con Producto_UID y el update de inventario se hace por UID.
    """
    try:
        # 1) Indexes inventario nube
        (inv_headers, idx_uid, idx_id, idx_norm, idx_stock, idx_costo, idx_precio, idx_nombre,
         uid_to_row, norm_to_row, norm_to_uid) = _build_inv_indexes(ws_inv)

        # 2) Validación: df_final debe tener la selección (tu UI ya lo crea)
        if df_final is None or df_final.empty:
            return False, ["No hay items para guardar."]

        if "SKU_Interno_Seleccionado" not in df_final.columns:
            return False, ["Falta columna SKU_Interno_Seleccionado en df_final (selección del usuario)."]

        # 3) Prorrateo (transporte/descuento)
        total_items = len(df_final)
        pr_trans = float(info_pago.get("Transporte", 0.0) or 0.0)
        pr_desc = float(info_pago.get("Descuento", 0.0) or 0.0)

        updates = []
        appends = []
        logs = []

        for _, row in df_final.iterrows():
            sel = str(row.get("SKU_Interno_Seleccionado", "")).strip()
            sku_prov = str(row.get("SKU_Proveedor", "")).strip()

            factor = float(row.get("Factor_Pack", 1) or 1)
            if factor <= 0:
                factor = 1.0

            cant_pack = float(row.get("Cantidad_Recibida", 0) or 0)
            iva_pct = float(row.get("IVA_Porcentaje", 0) or 0)
            costo_base_xml = float(row.get("Costo_Base_Unitario", 0) or 0)

            pr_item_trans = (pr_trans / total_items) if total_items else 0.0
            pr_item_desc = (pr_desc / total_items) if total_items else 0.0

            # costo unitario real por unidad (no por pack) + IVA
            costo_base_unit = (costo_base_xml + pr_item_trans - pr_item_desc) / factor
            iva_unit = costo_base_unit * (iva_pct / 100.0)
            costo_neto_unit = costo_base_unit + iva_unit

            unidades = cant_pack * factor

            # ✅ PRECIO: si el usuario no envió Precio_Sugerido, calcularlo aquí (con IVA y margen 20%)
            precio_editado = row.get("Precio_Sugerido", None)
            try:
                precio_editado = float(precio_editado) if precio_editado not in (None, "", "None") else 0.0
            except Exception:
                precio_editado = 0.0

            if precio_editado and precio_editado > 0:
                precio_final = precio_editado
            else:
                precio_final = redondear_centena(precio_con_margen(costo_neto_unit, MARGEN_BRUTO_OBJ))

            # ---- Inventario: update por UID/Norm; append si no existe ----
            es_nuevo = ("NUEVO" in sel.upper()) or (sel == "") or (sel.upper().startswith("NUEVO"))
            if es_nuevo:
                sku_interno = sku_prov if sku_prov and sku_prov != "S/C" else f"N-{int(time.time())}"
                producto_uid = uuid.uuid4().hex
            else:
                sku_interno = sel.split(" | ")[0].strip()
                producto_uid = norm_to_uid.get(normalizar_id_producto(sku_interno), "")

            sku_norm = normalizar_id_producto(sku_interno)

            # ---- Upsert Maestro_Proveedores (si hay SKU proveedor) ----
            if sku_prov and sku_prov != "S/C":
                costo_prov_pack = costo_neto_unit * factor
                _upsert_maestro_proveedores(
                    ws_map=ws_map,
                    meta_xml=meta_xml,
                    sku_prov=sku_prov,
                    sku_interno=sku_interno,
                    producto_uid=producto_uid,
                    factor=factor,
                    costo_prov=costo_prov_pack,
                    iva_pct=iva_pct,
                )

            # ---- Inventario: update por UID si existe; si no, por Norm; si no existe, append ----
            fila = None
            if producto_uid:
                fila = uid_to_row.get(producto_uid)
            if fila is None and sku_norm:
                fila = norm_to_row.get(sku_norm)

            # ✅ FIX: si existe la fila pero no hay UID aún, crear uno y curar la fila
            if fila is not None and (not producto_uid):
                producto_uid = uuid.uuid4().hex  # UID nuevo
                # importante: también lo guardamos en el mapping proveedor si aplica (más abajo ya se upsertea)
                updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_uid + 1), "values": [[producto_uid]]})
                updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_norm + 1), "values": [[sku_norm]]})
                logs.append(f"🧱 CURADO: {sku_interno} ahora tiene UID {producto_uid[:8]}...")

            if fila is None:
                # Crear nuevo en inventario
                new_row = [""] * len(inv_headers)
                new_row[idx_id] = sku_interno
                new_row[idx_uid] = producto_uid
                new_row[idx_norm] = sku_norm

                if idx_nombre is not None:
                    new_row[idx_nombre] = str(row.get("Nombre_Inventario", row.get("Descripcion", ""))).strip()

                if idx_stock is not None:
                    new_row[idx_stock] = str(unidades)
                if idx_costo is not None:
                    new_row[idx_costo] = str(costo_neto_unit)

                # ✅ Guardar precio calculado con IVA + margen 20%
                if idx_precio is not None:
                    new_row[idx_precio] = str(precio_final)

                appends.append(new_row)
                logs.append(f"✨ CREADO inventario: {sku_interno} | UID {producto_uid[:8]}... (+{unidades})")
            else:
                # Update stock/costo en fila existente
                # leer stock actual de la nube (robusto)
                stock_actual = 0.0
                if idx_stock is not None:
                    try:
                        v = ws_inv.cell(fila, idx_stock + 1).value
                        stock_actual = float(str(v).replace(",", "").strip() or 0)
                    except Exception:
                        stock_actual = 0.0

                nuevo_stock = stock_actual + unidades

                if idx_stock is not None:
                    updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_stock + 1), "values": [[nuevo_stock]]})
                if idx_costo is not None:
                    updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_costo + 1), "values": [[costo_neto_unit]]})

                # ✅ Actualizar precio (IVA + margen 20%) si hay columna Precio
                if idx_precio is not None:
                    updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_precio + 1), "values": [[precio_final]]})

                # asegurar UID/Norm en esa fila (por si estaba incompleto)
                updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_uid + 1), "values": [[producto_uid]]})
                updates.append({"range": gspread.utils.rowcol_to_a1(fila, idx_norm + 1), "values": [[sku_norm]]})

                logs.append(f"📦 ACTUALIZADO: {sku_interno} | UID {producto_uid[:8]}... Stock {stock_actual}→{nuevo_stock}")

        if updates:
            ws_inv.batch_update(updates)
        if appends:
            ws_inv.append_rows(appends)

        # Guardar historial
        ws_hist.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(meta_xml['Folio']), str(meta_xml['Proveedor']),
            len(df_final), meta_xml['Total'], "Admin Nexus", "OK"
        ])

        # ✅ FIX: fecha para registro de gasto (evita NameError)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            descripcion_gasto = f"[PROV: {meta_xml['Proveedor']}] [REF: {meta_xml['Folio']}] - Compra Mercancía"
            monto_total_gasto = float(meta_xml.get('Total', 0.0) or 0.0) + float(info_pago.get("Transporte", 0.0)) - float(info_pago.get("Descuento", 0.0))
            ts = int(time.time())

            datos_gasto = [
                f"GAS-{ts}", fecha, "Variable", "Compra Inventario", descripcion_gasto,
                monto_total_gasto, info_pago['Origen'], info_pago['Origen']
            ]
            ws_gas.append_row(datos_gasto)
            logs.append(f"💰 Gasto Registrado: ${monto_total_gasto:,.0f} desde {info_pago['Origen']}")
        except Exception as ex_gas:
            logs.append(f"⚠️ Alerta: No se registró en Gastos: {ex_gas}")

        return True, logs

    except Exception as e:
        return False, [f"Error del Sistema: {e}"]

# ==========================================
# 7. INTERFAZ PRINCIPAL (STREAMLIT) - REFACTORIZADA
# ==========================================

def main():
    st.markdown('<div class="main-header">Recepción & Compras 📥</div>', unsafe_allow_html=True)
    
    # === CONTROL DE ESTADOS ===
    if 'step' not in st.session_state: st.session_state.step = 1
    if 'invoice_meta' not in st.session_state: st.session_state.invoice_meta = {}
    if 'invoice_items' not in st.session_state: st.session_state.invoice_items = []

    # Conexión
    sh, ws_inv, ws_map, ws_hist, ws_gas = conectar_sheets()

    # ✅ Botón para recargar catálogo (cuando alguien cambia Sheets)
    cR1, cR2 = st.columns([1, 3])
    if cR1.button("🔄 Recargar catálogo", help="Recarga Inventario/Proveedores/Memory"):
        st.cache_data.clear()
        for k in ["lst_prods_cache", "dct_prods_cache", "memoria_cache", "proveedores_cache", "prov_id_cache"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    # Cerebro (productos + memoria)
    if "lst_prods_cache" not in st.session_state:
        l, d, m = cargar_cerebro(ws_inv, ws_map)
        st.session_state.lst_prods_cache = l
        st.session_state.dct_prods_cache = d
        st.session_state.memoria_cache = m

    # ✅ Proveedores (para manual)
    if "proveedores_cache" not in st.session_state:
        provs, prov_to_id = cargar_proveedores(ws_map)
        st.session_state.proveedores_cache = provs
        st.session_state.prov_id_cache = prov_to_id

    # ✅ Categorías reales desde Inventario
    categorias = []
    try:
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        col_cat = "Categoria" if "Categoria" in df_inv.columns else ("Categoría" if "Categoría" in df_inv.columns else None)
        if col_cat:
            categorias = sorted([c for c in df_inv[col_cat].fillna("").astype(str).unique().tolist() if c.strip()])
    except Exception:
        categorias = []
    if not categorias:
        categorias = ["Sin Categoría"]

    # ==========================================
    # PASO 1: CARGA DE DATOS (XML O MANUAL)
    # ==========================================
    if st.session_state.step == 1:
        st.markdown('<div class="sub-header">Selecciona el método de ingreso</div>', unsafe_allow_html=True)
        
        tab_xml, tab_manual = st.tabs(["📂 Cargar XML (Factura Electrónica)", "✍️ Ingreso Manual"])
        
        # OPCIÓN A: XML
        with tab_xml:
            st.info("Arrastra tu Factura XML de la DIAN para autocompletar.")
            uploaded = st.file_uploader("📂 Sube tu Factura XML DIAN aquí", type=['xml'], key="xml_upl")
            
            if uploaded:
                with st.spinner("🤖 Analizando XML y Consultando Memoria..."):
                    data = parsear_xml_colombia(uploaded)
                    if not data:
                        st.error("❌ El XML no pudo ser leído. Verifica que sea una factura DIAN válida o consulta soporte.")
                        st.stop()
                    
                    # Guardar en sesión y avanzar
                    st.session_state.invoice_meta = {
                        "Proveedor": data["Proveedor"], "ID_Proveedor": data["ID_Proveedor"],
                        "Folio": data["Folio"], "Total": data["Total"]
                    }
                    st.session_state.invoice_items = data["Items"]
                    st.session_state.step = 2
                    st.rerun()

        # OPCIÓN B: MANUAL
        with tab_manual:
            with st.form("form_manual_ingreso"):
                c1, c2, c3 = st.columns(3)

                prov_sel = c1.selectbox(
                    "Proveedor",
                    options=st.session_state.get("proveedores_cache", ["(Nuevo proveedor)"]),
                )

                prov_man = prov_sel
                nit_default = st.session_state.get("prov_id_cache", {}).get(prov_sel, "") if prov_sel != "(Nuevo proveedor)" else ""

                if prov_sel == "(Nuevo proveedor)":
                    prov_man = c1.text_input("Nombre proveedor (nuevo)", placeholder="Ej: Italcol")

                nit_man = c2.text_input("NIT / ID Proveedor", value=nit_default or "000")

                folio_man = c3.text_input("No. Factura", placeholder="FAC-123")

                st.markdown("---")
                st.write("📝 **Items de la Factura**")

                df_template = pd.DataFrame([{
                    "Descripción": "", "Cantidad": 1, "Costo_Total_Línea": 0.0
                }])

                edited_manual = st.data_editor(
                    df_template, num_rows="dynamic", use_container_width=True,
                    column_config={
                        "Descripción": st.column_config.TextColumn("Descripción del Producto", required=True),
                        "Cantidad": st.column_config.NumberColumn("Cant.", min_value=1),
                        "Costo_Total_Línea": st.column_config.NumberColumn("Costo Total ($)", min_value=0.0)
                    }
                )

                submit_manual = st.form_submit_button("Siguiente Paso ➡️")
                
                if submit_manual:
                    if not prov_man or not folio_man:
                        st.error("⚠️ Falta Proveedor o Factura.")
                    else:
                        items_std = []
                        total_manual = 0.0
                        for i, row in edited_manual.iterrows():
                            if row["Descripción"]:
                                qty = float(row["Cantidad"])
                                c_tot = float(row["Costo_Total_Línea"])
                                base_unit = (c_tot / qty) if qty > 0 else 0.0
                                total_manual += c_tot
                                
                                items_std.append({
                                    'SKU_Proveedor': "S/C",
                                    'Descripcion': row["Descripción"],
                                    'Cantidad': qty,
                                    'Costo_Base_Unitario': base_unit
                                })
                        
                        st.session_state.invoice_meta = {
                            "Proveedor": prov_man, "ID_Proveedor": nit_man,
                            "Folio": folio_man, "Total": total_manual
                        }
                        st.session_state.invoice_items = items_std
                        st.session_state.step = 2
                        st.rerun()

    # ==========================================
    # PASO 2: REVISIÓN, MAPEO Y GUARDADO
    # ==========================================
    elif st.session_state.step == 2:
        st.markdown('<div class="sub-header">Revisión, Mapeo y Finanzas</div>', unsafe_allow_html=True)

        # ✅ meta robusto (NO KeyError)
        meta = _get_meta_safe()
        if not meta["Proveedor"] or not meta["Folio"]:
            st.error("⚠️ No hay cabecera de compra válida (Proveedor/Folio). Vuelve a ingresar la compra.")
            st.session_state.step = 1
            st.rerun()

        st.info(
            f"🏢 **Proveedor:** {meta.get('Proveedor','—')} | "
            f"📄 **Folio:** {meta.get('Folio','—')} | "
            f"💰 **Total Base:** ${float(meta.get('Total',0.0) or 0.0):,.2f}"
        )

        # --- LÓGICA DE MEMORIA (CEREBRO) ---
        df_revision_data = []

        for item in st.session_state.invoice_items:
            qty = float(item.get("Cantidad", 1) or 1)

            nit_prov_norm = normalizar_str(meta['ID_Proveedor'])
            sku_prov_norm = normalizar_str(item.get('SKU_Proveedor', 'S/C'))
            clave_memoria = f"{nit_prov_norm}_{sku_prov_norm}"

            prod_interno_val = "NUEVO (Crear Producto)"
            iva_val = 0
            factor_val = 1.0

            # --- Búsqueda robusta: 1) NIT+SKU, 2) solo SKU, 3) por nombre ---
            memoria = st.session_state.memoria_cache
            lst_prods = st.session_state.lst_prods_cache
            encontrado = False

            # 1. Buscar por NIT+SKU
            if clave_memoria in memoria:
                recuerdo = memoria[clave_memoria]
                sku_interno_recordado = recuerdo.get('SKU_Interno', "")
                match = next((p for p in lst_prods if p.startswith(sku_interno_recordado + " |")), None)
                if match:
                    prod_interno_val = match
                    iva_val = recuerdo.get('IVA_Aprendido', 0)
                    factor_val = recuerdo.get('Factor', 1.0)
                    encontrado = True

            # 2. Si no se encontró, buscar por solo SKU_Proveedor (sin NIT)
            if not encontrado and sku_prov_norm != "S/C":
                posibles = [k for k in memoria.keys() if k.endswith(f"_{sku_prov_norm}")]
                if posibles:
                    recuerdo = memoria[posibles[0]]
                    sku_interno_recordado = recuerdo.get('SKU_Interno', "")
                    match = next((p for p in lst_prods if p.startswith(sku_interno_recordado + " |")), None)
                    if match:
                        prod_interno_val = match
                        iva_val = recuerdo.get('IVA_Aprendido', 0)
                        factor_val = recuerdo.get('Factor', 1.0)
                        encontrado = True

            # 3. Si aún no, buscar por nombre normalizado en inventario
            if not encontrado:
                nombre_item = normalizar_str(item.get('Descripcion', ''))
                for p in lst_prods:
                    # p = "SKU | Nombre"
                    partes = p.split(" | ", 1)
                    if len(partes) > 1 and normalizar_str(partes[1]) == nombre_item:
                        prod_interno_val = p
                        encontrado = True
                        break

            base_unit = float(item.get("Costo_Base_Unitario", 0.0) or 0.0)
            factor_val = float(factor_val or 1.0)
            if factor_val <= 0:
                factor_val = 1.0
            iva_val = float(iva_val or 0.0)

            costo_base_unit_est = base_unit / factor_val
            costo_neto_unit_est = costo_base_unit_est * (1.0 + (iva_val / 100.0))
            precio_sug_est = redondear_centena(precio_con_margen(costo_neto_unit_est, MARGEN_BRUTO_OBJ))

            df_revision_data.append({
                "SKU_Proveedor": item.get('SKU_Proveedor', 'S/C'),
                "Descripcion": item.get('Descripcion', ''),
                "Nombre_Inventario": item.get('Descripcion', ''),
                "Cantidad": _fmt_qty(qty),
                "Costo_Base_Unitario": base_unit,
                "📌 Producto_Interno": prod_interno_val,
                "IVA_%": int(iva_val) if float(iva_val).is_integer() else iva_val,
                "Factor_Pack": factor_val,
                "Precio_Sugerido": float(precio_sug_est or 0.0),
                "Categoría": "Sin Categoría"
            })

        df_revision = pd.DataFrame(df_revision_data)

        edited_revision = st.data_editor(
            df_revision,
            use_container_width=True,
            hide_index=True,
            column_config={
                "SKU_Proveedor": st.column_config.TextColumn("SKU Prov.", disabled=True),
                "Descripcion": st.column_config.TextColumn("Desc. Factura", disabled=True),
                "Nombre_Inventario": st.column_config.TextColumn("✍️ Nombre a Crear (Editable)", disabled=False, width="medium"),

                # ✅ Asociar a inventario (lista real)
                "📌 Producto_Interno": st.column_config.SelectboxColumn(
                    "📌 Asociar a",
                    options=st.session_state.lst_prods_cache,
                    required=True,
                ),

                # ✅ IVA seleccionable
                "IVA_%": st.column_config.SelectboxColumn(
                    "IVA %",
                    options=[0, 5, 19],
                    required=True,
                ),

                # ✅ Categoría seleccionable
                "Categoría": st.column_config.SelectboxColumn(
                    "Categoría",
                    options=categorias,
                    required=True,
                ),

                "Cantidad": st.column_config.NumberColumn("Cant.", disabled=True, step=1, format="%.0f"),  # ✅ sin 1.0
                "Costo_Base_Unitario": st.column_config.NumberColumn("Costo Unit. Base", format="$%.0f", disabled=True),
                "Factor_Pack": st.column_config.NumberColumn("Factor/Caja", min_value=1.0, step=1.0, format="%.0f"),  # ✅
                "Precio_Sugerido": st.column_config.NumberColumn("Precio Sugerido (20%)", format="$%.0f", min_value=0.0),  # ✅
            },
        )

        st.markdown("---")
        st.markdown("### 2. Liquidación y Pago")
        
        c1, c2, c3 = st.columns(3)
        c_transporte = c1.number_input("Costo Transporte ($)", min_value=0.0, value=0.0)
        c_descuento = c2.number_input("Descuento Total ($)", min_value=0.0, value=0.0)
        origen_pago = c3.selectbox("Cuenta de Egreso (Gastos)", ["Bancolombia Ahorros", "Davivienda", "Nequi", "DaviPlata", "Efectivo", "Caja General", "Crédito Proveedor (CxP)"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Confirmar y Guardar en Base de Datos", type="primary", use_container_width=True):
            
            df_to_save = edited_revision.copy()
            df_to_save = df_to_save.rename(columns={
                "📌 Producto_Interno": "SKU_Interno_Seleccionado",
                "IVA_%": "IVA_Porcentaje",
                "Cantidad": "Cantidad_Recibida"
            })
            
            info_pago = {
                "Origen": origen_pago,
                "Transporte": float(c_transporte),
                "Descuento": float(c_descuento)
            }
            
            with st.spinner("Guardando en Google Sheets..."):
                ok, logs = procesar_guardado(ws_map, ws_inv, ws_hist, ws_gas, df_to_save, meta, info_pago)
            
            if ok:
                st.success("¡Compra registrada correctamente!")
                st.balloons()
                with st.expander("Ver bitácora de operaciones"):
                    for l in logs: st.text(l)

                # Limpiar caché y recargar memoria para sugerencias inmediatas
                st.cache_data.clear()
                for k in ["lst_prods_cache", "dct_prods_cache", "memoria_cache", "proveedores_cache", "prov_id_cache"]:
                    if k in st.session_state:
                        del st.session_state[k]

                # Resetear la sesión
                st.session_state.invoice_meta = {}
                st.session_state.invoice_items = []

                if st.button("Volver al Inicio"):
                    st.session_state.step = 1
                    st.rerun()
            else:
                st.error("Error guardando datos.")
                for l in logs: st.error(l)

if __name__ == "__main__":
    main()