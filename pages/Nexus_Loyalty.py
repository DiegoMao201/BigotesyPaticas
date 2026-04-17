from __future__ import annotations

import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import re
from datetime import datetime, timedelta, date
from urllib.parse import quote
import unicodedata

def money_int(val):
    if isinstance(val, (int, float)):
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

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS (NEXUS PRO THEME)
# ==========================================

COLOR_PRIMARIO = "#187f77"      # Cian Oscuro (Teal)
COLOR_SECUNDARIO = "#125e58"    # Variante más oscura
COLOR_ACENTO = "#f5a641"        # Naranja (Alertas)
COLOR_FONDO = "#f8f9fa"         # Gris claro
COLOR_BLANCO = "#ffffff"
COLOR_TEXTO = "#262730"

st.set_page_config(
    page_title="Nexus Loyalty | Bigotes y Patitas",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
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

    /* Tarjetas Métricas */
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

    /* Inputs y Tabs */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
        border-radius: 8px;
        border-color: #e0e0e0;
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
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

    /* CLASE ESPECIAL PARA LA ALERTA DE CUMPLEAÑOS */
    .cumple-hoy {{
        background-color: #ffead0;
        border: 2px solid {COLOR_ACENTO};
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        color: #8a4b00;
        font-weight: bold;
        text-align: center;
        font-size: 1.2rem;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2.B UTILIDADES ROBUSTAS (ANTI-ERRORES)
# ==========================================

def _norm_col(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace(" ", "_")
    return s

def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Encuentra columna aunque tenga tildes/espacios/cambios menores."""
    if df is None or df.empty:
        return None
    norm_map = {_norm_col(c): c for c in df.columns}
    for cand in candidates:
        key = _norm_col(cand)
        if key in norm_map:
            return norm_map[key]
    # fallback: contains
    for cand in candidates:
        key = _norm_col(cand)
        for k, orig in norm_map.items():
            if key in k:
                return orig
    return None

def _safe_to_datetime(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")

def _safe_to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def _clean_tel_basic(tel: str) -> str:
    t = "" if tel is None else str(tel)
    t = t.replace(" ", "").replace("+", "").replace("-", "").replace(".", "").replace("(", "").replace(")", "").strip()
    if len(t) == 10 and not t.startswith("57"):
        t = "57" + t
    return t

# ==========================================
# 2.C INTEGRACIÓN CON EL FLUJO DE LA APP (SESSION_STATE.DB)
# ==========================================

def _preparar_fuente_cli_ven(df_cli: pd.DataFrame, df_ven: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normaliza columnas mínimas para evitar master vacío o sin campos críticos."""
    df_cli = df_cli.copy() if df_cli is not None else pd.DataFrame()
    df_ven = df_ven.copy() if df_ven is not None else pd.DataFrame()

    df_cli = limpiar_columnas(df_cli)
    df_ven = limpiar_columnas(df_ven)

    # Asegurar columnas clave (aunque vengan con otros nombres)
    # Clientes
    col_nom = _find_col(df_cli, ["Nombre", "Nombre_Cliente"])
    if col_nom and col_nom != "Nombre":
        df_cli = df_cli.rename(columns={col_nom: "Nombre"})
    if "Nombre" not in df_cli.columns:
        df_cli["Nombre"] = ""

    col_masc = _find_col(df_cli, ["Mascota", "Mascota_Principal", "Nombre Mascota Principal"])
    if col_masc and col_masc != "Mascota":
        df_cli = df_cli.rename(columns={col_masc: "Mascota"})
    if "Mascota" not in df_cli.columns:
        df_cli["Mascota"] = ""

    col_tel = _find_col(df_cli, ["Telefono", "Teléfono", "Celular", "Movil"])
    if col_tel and col_tel != "Telefono":
        df_cli = df_cli.rename(columns={col_tel: "Telefono"})
    if "Telefono" not in df_cli.columns:
        df_cli["Telefono"] = ""

    col_email = _find_col(df_cli, ["Email", "Correo", "Correo_Electronico"])
    if col_email and col_email != "Email":
        df_cli = df_cli.rename(columns={col_email: "Email"})
    if "Email" not in df_cli.columns:
        df_cli["Email"] = ""

    col_ced = _find_col(df_cli, ["Cedula", "Cédula", "Cedula_Cliente", "Documento"])
    if col_ced and col_ced != "Cedula":
        df_cli = df_cli.rename(columns={col_ced: "Cedula"})
    if "Cedula" not in df_cli.columns:
        df_cli["Cedula"] = ""

    df_cli["Cedula"] = df_cli["Cedula"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    df_cli["Nombre"] = df_cli["Nombre"].fillna("").astype(str).str.strip()
    df_cli["Mascota"] = df_cli["Mascota"].fillna("").astype(str).str.strip()
    df_cli["Telefono"] = df_cli["Telefono"].fillna("").astype(str).str.strip()

    # Ventas
    col_fecha_v = _find_col(df_ven, ["Fecha"])
    if col_fecha_v and col_fecha_v != "Fecha":
        df_ven = df_ven.rename(columns={col_fecha_v: "Fecha"})
    if "Fecha" not in df_ven.columns:
        df_ven["Fecha"] = pd.NaT
    df_ven["Fecha"] = pd.to_datetime(df_ven["Fecha"], errors="coerce")

    col_total_v = _find_col(df_ven, ["Total", "Monto", "Valor"])
    if col_total_v and col_total_v != "Total":
        df_ven = df_ven.rename(columns={col_total_v: "Total"})
    if "Total" not in df_ven.columns:
        df_ven["Total"] = 0.0
    df_ven["Total"] = df_ven["Total"].apply(money_int)

    col_ced_v = _find_col(df_ven, ["Cedula_Cliente", "Cedula", "Cédula", "Documento"])
    if col_ced_v and col_ced_v != "Cedula_Cliente":
        df_ven = df_ven.rename(columns={col_ced_v: "Cedula_Cliente"})
    if "Cedula_Cliente" not in df_ven.columns:
        df_ven["Cedula_Cliente"] = ""
    df_ven["Cedula_Cliente"] = df_ven["Cedula_Cliente"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

    col_items = _find_col(df_ven, ["Items", "Items_Detalle"])
    if col_items and col_items != "Items":
        df_ven = df_ven.rename(columns={col_items: "Items"})
    if "Items" not in df_ven.columns:
        df_ven["Items"] = ""

    return df_cli, df_ven

def procesar_inteligencia_df(df_cli: pd.DataFrame, df_ven: pd.DataFrame):
    """
    MISMA SALIDA que `procesar_inteligencia(ws_cli, ws_ven)` pero usando DataFrames
    provenientes de `st.session_state.db` (flujo oficial de la app).
    """
    df_cli, df_ven = _preparar_fuente_cli_ven(df_cli, df_ven)

    if df_cli.empty:
        return pd.DataFrame(), df_ven, "Sin clientes"

    # --- Ventas / RFM básico ---
    if df_ven.empty or df_ven["Fecha"].isna().all():
        df_cli["Estado"] = "⚪ Nuevo"
        df_cli["Dias_Sin_Compra"] = 999
        df_cli["Ultima_Compra_Dt"] = pd.NaT
        df_cli["Total_Gastado"] = 0.0
        df_cli["Ultimo_Producto"] = "N/A"
    else:
        resumen = (
            df_ven.groupby("Cedula_Cliente", as_index=False)
            .agg(Ultima_Compra_Dt=("Fecha", "max"), Total_Gastado=("Total", "sum"), Ultimo_Producto=("Items", "last"))
        )

        df_cli = df_cli.merge(resumen, left_on="Cedula", right_on="Cedula_Cliente", how="left")
        hoy = pd.Timestamp.now()
        df_cli["Dias_Sin_Compra"] = (hoy - pd.to_datetime(df_cli["Ultima_Compra_Dt"], errors="coerce")).dt.days.fillna(999).astype(int)

        def clasificar(dias: int) -> str:
            if dias <= 30: return "🟢 Activo"
            if 31 <= dias <= 60: return "🟡 Recompra (Alerta)"
            if 61 <= dias <= 90: return "🟠 Riesgo"
            if dias > 90 and dias != 999: return "🔴 Perdido"
            return "⚪ Nuevo"

        df_cli["Estado"] = df_cli["Dias_Sin_Compra"].apply(clasificar)

        # limpiar columna extra si quedó del merge
        if "Cedula_Cliente" in df_cli.columns:
            df_cli = df_cli.drop(columns=["Cedula_Cliente"])

    # --- Cumpleaños mascota robusto (None / YYYY-MM-DD) ---
    df_cli["Es_Cumple_Mes"] = False
    df_cli["Es_Cumple_Hoy"] = False
    df_cli["Cumple_Mascota_DT"] = pd.NaT

    col_nac = _find_col(df_cli, ["Cumpleaños_mascota", "Cumpleanos_mascota", "Cumpleaños Mascota", "Cumpleanos Mascota"])
    if col_nac:
        if "Cumpleaños_mascota" not in df_cli.columns:
            df_cli["Cumpleaños_mascota"] = df_cli[col_nac]
        df_cli["Cumple_Mascota_DT"] = pd.to_datetime(df_cli[col_nac], errors="coerce")

        hoy_dt = datetime.now()
        mask_valid = df_cli["Cumple_Mascota_DT"].notna()
        df_cli.loc[mask_valid, "Es_Cumple_Mes"] = df_cli.loc[mask_valid, "Cumple_Mascota_DT"].dt.month == hoy_dt.month
        df_cli.loc[mask_valid, "Es_Cumple_Hoy"] = (
            (df_cli.loc[mask_valid, "Cumple_Mascota_DT"].dt.month == hoy_dt.month) &
            (df_cli.loc[mask_valid, "Cumple_Mascota_DT"].dt.day == hoy_dt.day)
        )
    else:
        if "Cumpleaños_mascota" not in df_cli.columns:
            df_cli["Cumpleaños_mascota"] = None

    return df_cli, df_ven, "OK (Session DB)"

def cargar_datos_loyalty():
    """
    Flujo correcto:
    1) SI existe `st.session_state.db` (cargado por [`cargar_datos_iniciales`](BigotesyPaticas/BigotesyPaticas.py)),
       procesar ahí mismo (NO devolver crudo).
    2) Fallback: Google Sheets directo (como respaldo).
    """
    if "db" in st.session_state and isinstance(st.session_state.db, dict):
        df_cli_raw = st.session_state.db.get("cli", pd.DataFrame())
        df_ven_raw = st.session_state.db.get("ven", pd.DataFrame())
        master, df_ven, status = procesar_inteligencia_df(df_cli_raw, df_ven_raw)
        return master, df_ven, status

    # fallback a la lógica existente
    ws_cli, ws_ven = conectar_crm()
    if not ws_cli:
        return pd.DataFrame(), pd.DataFrame(), "Sin conexión CRM"
    master, df_ven, status = procesar_inteligencia(ws_cli, ws_ven)
    return master, df_ven, status

# ==========================================
# 2.D CALENDARIO DE CAMPAÑAS (FECHAS ESPECIALES)
# ==========================================

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """weekday: lunes=0 ... domingo=6"""
    d = date(year, month, 1)
    shift = (weekday - d.weekday()) % 7
    d = d + timedelta(days=shift + 7 * (n - 1))
    return d

def _third_sunday_of_june(year: int) -> date:
    return _nth_weekday(year, 6, 6, 3)

def _second_sunday_of_may(year: int) -> date:
    return _nth_weekday(year, 5, 6, 2)

def calendario_campanas(year: int | None = None) -> pd.DataFrame:
    y = year or datetime.now().year
    rows = [
        {"Evento": "Día de la Mujer", "Fecha": date(y, 3, 8), "Tag": "MUJER"},
        {"Evento": "Día de la Madre (CO)", "Fecha": _second_sunday_of_may(y), "Tag": "MADRE"},
        {"Evento": "Día del Padre (CO)", "Fecha": _third_sunday_of_june(y), "Tag": "PADRE"},
        {"Evento": "Amor y Amistad (CO)", "Fecha": date(y, 9, 20), "Tag": "AYAM"},
        {"Evento": "Halloween", "Fecha": date(y, 10, 31), "Tag": "HALLOWEEN"},
        {"Evento": "Black Friday (referencia)", "Fecha": date(y, 11, 29), "Tag": "BF"},
        {"Evento": "Navidad", "Fecha": date(y, 12, 24), "Tag": "NAVIDAD"},
        {"Evento": "Fin de Año", "Fecha": date(y, 12, 31), "Tag": "FIN_ANO"},
    ]
    df = pd.DataFrame(rows)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    return df.sort_values("Fecha")

def plantilla_evento(tag: str) -> str:
    # Templates cortos, claros, “bonitos” y accionables
    base = {
        "MUJER": "Hola {Nombre} 🐾\nHoy celebramos el *Día de la Mujer* 🌷\nQueremos consentirte a ti y a {Mascota}.\n🎁 Promo: {Promo}\n¿Te lo separamos para hoy?",
        "MADRE": "Hola {Nombre} 🐾\nFeliz *Día de la Madre* 🌼\n{Mascota} también quiere celebrarte.\n🎁 Promo: {Promo}\n¿Te lo llevamos a domicilio o pasas por la tienda?",
        "PADRE": "Hola {Nombre} 🐾\nFeliz *Día del Padre* 🧔‍♂️\nArma el plan con {Mascota}.\n🎁 Promo: {Promo}\n¿Te comparto opciones recomendadas?",
        "AYAM": "Hola {Nombre} 🐾\nEn *Amor y Amistad* celebramos la lealtad 💛\n🎁 Promo: {Promo}\n¿Te lo dejamos listo para hoy?",
        "HALLOWEEN": "Hola {Nombre} 🐾\n🎃 Halloween llegó y {Mascota} merece premio.\n🎁 Promo: {Promo}\n¿Quieres snacks o juguete?",
        "BF": "Hola {Nombre} 🐾\n🔥 Black Friday en Bigotes y Patitas.\n🎁 Promo: {Promo}\n¿Te aparto lo de {Mascota} antes de que se agote?",
        "NAVIDAD": "Hola {Nombre} 🐾\n🎄 Navidad con {Mascota} es mejor.\n🎁 Promo: {Promo}\n¿Te armamos un combo regalo?",
        "FIN_ANO": "Hola {Nombre} 🐾\n✨ Cerramos el año consintiendo a {Mascota}.\n🎁 Promo: {Promo}\n¿Te ayudo a elegir lo ideal?",
    }
    return base.get(tag, "Hola {Nombre} 🐾\n🎁 Promo: {Promo}\n¿Te lo separamos?")

def construir_links_campana(master: pd.DataFrame, template: str, promo: str) -> pd.DataFrame:
    tel_col = _find_col(master, ["Telefono", "Teléfono", "Celular", "Movil"])
    nom_col = _find_col(master, ["Nombre", "Nombre_Cliente"])
    mas_col = _find_col(master, ["Mascota", "Nombre Mascota Principal", "Mascota_Principal"])

    out = master.copy()
    if nom_col is None: out["__Nombre"] = "Cliente"
    else: out["__Nombre"] = out[nom_col].fillna("Cliente").astype(str)

    if mas_col is None: out["__Mascota"] = "tu peludito"
    else: out["__Mascota"] = out[mas_col].fillna("tu peludito").astype(str)

    if tel_col is None:
        out["__Telefono"] = ""
    else:
        out["__Telefono"] = out[tel_col].apply(_clean_tel_basic)

    def _render(row):
        msg = template.format(Nombre=row["__Nombre"], Mascota=row["__Mascota"], Promo=promo)
        return msg

    out["Mensaje"] = out.apply(_render, axis=1)
    out["Link"] = out["__Telefono"].apply(lambda t: f"https://wa.me/{t}?text={quote('')}" if not t else f"https://wa.me/{t}?text={quote('')}")
    # Usar tu helper existente si quieres: [`link_whatsapp`](BigotesyPaticas/pages/Nexus_Loyalty.py)
    out["Link"] = out.apply(lambda r: link_whatsapp(r["__Telefono"], r["Mensaje"]) if r["__Telefono"] else None, axis=1)

    return out[["__Nombre", "__Mascota", "__Telefono", "Mensaje", "Link"]].rename(
        columns={"__Nombre": "Nombre", "__Mascota": "Mascota", "__Telefono": "Telefono"}
    )

# ==========================================
# 2.E MOTOR CUMPLEAÑOS (VENTANA -8 / +8 DÍAS)
# ==========================================

def _nearest_bday_occurrence(bday_dt: pd.Timestamp, today: pd.Timestamp) -> tuple[pd.Timestamp, int]:
    """
    Retorna (fecha_ocurrencia_mas_cercana, diff_dias)
    diff_dias = (ocurrencia - today).days  -> negativo: ya pasó, positivo: falta
    Maneja cruces de año (dic/ene). Soporta NaT.
    """
    bday_dt = pd.to_datetime(bday_dt, errors="coerce")
    if pd.isna(bday_dt):
        return pd.NaT, 10**9

    m = int(bday_dt.month)
    d = int(bday_dt.day)
    y = int(today.year)

    candidates: list[pd.Timestamp] = []
    for yy in (y - 1, y, y + 1):
        try:
            candidates.append(pd.Timestamp(date(yy, m, d)))
        except Exception:
            continue

    if not candidates:
        return pd.NaT, 10**9

    today0 = today.normalize()
    best = min(((c, int((c - today0).days)) for c in candidates), key=lambda x: abs(x[1]))
    return best[0], best[1]

def construir_campana_cumple(master: pd.DataFrame, days_before: int = 8, days_after: int = 8) -> pd.DataFrame:
    """
    Filtra clientes con Cumple_Mascota_DT dentro de ventana [-days_after, +days_before]
    alrededor de HOY (por día/mes, cruzando año si aplica).
    Requiere/crea columnas: Nombre, Mascota, Telefono, Cumple_Mascota_DT.
    """
    if master is None or master.empty:
        return pd.DataFrame()

    df = master.copy()

    # asegurar columnas base para no reventar UI
    for c, default in [("Nombre", "Cliente"), ("Mascota", "tu peludito"), ("Telefono", "")]:
        if c not in df.columns:
            df[c] = default
        df[c] = df[c].fillna(default).astype(str)

    if "Cumple_Mascota_DT" not in df.columns:
        # si tu hoja trae Cumpleaños_mascota, intenta parsearla
        if "Cumpleaños_mascota" in df.columns:
            df["Cumple_Mascota_DT"] = pd.to_datetime(df["Cumpleaños_mascota"], errors="coerce")
        else:
            df["Cumple_Mascota_DT"] = pd.NaT
    else:
        df["Cumple_Mascota_DT"] = pd.to_datetime(df["Cumple_Mascota_DT"], errors="coerce")

    hoy = pd.Timestamp.now().normalize()

    occ_list = []
    diff_list = []
    for v in df["Cumple_Mascota_DT"]:
        occ, diff = _nearest_bday_occurrence(v, hoy)
        occ_list.append(occ)
        diff_list.append(diff)

    df["Cumple_Ocurrencia"] = occ_list
    df["Cumple_Diff_Dias"] = diff_list

    df = df[(df["Cumple_Diff_Dias"] >= -int(days_after)) & (df["Cumple_Diff_Dias"] <= int(days_before))].copy()

    def _estado(diff: int) -> str:
        if diff == 0:
            return "🎂 Hoy"
        if diff > 0:
            return f"⏳ Faltan {diff} días"
        return f"✅ Pasó hace {abs(diff)} días"

    df["Estado_Cumple"] = df["Cumple_Diff_Dias"].apply(lambda x: _estado(int(x)) if pd.notna(x) else "N/D")

    # orden: primero los que vienen pronto, luego los recientes
    df = df.sort_values(["Cumple_Diff_Dias", "Nombre"], ascending=[False, True])
    return df

# ==========================================
# 2. CONEXIÓN Y PROCESAMIENTO
# ==========================================

@st.cache_resource(ttl=600)
def conectar_crm():
    try:
        # Verifica que existan los secretos configurados en Streamlit Cloud
        if "google_service_account" not in st.secrets:
            st.error("🚨 Falta configuración de secretos (google_service_account).")
            return None, None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        
        try: ws_cli = sh.worksheet("Clientes")
        except: ws_cli = None
        
        try: ws_ven = sh.worksheet("Ventas")
        except: ws_ven = None
            
        return ws_cli, ws_ven
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return None, None

def limpiar_columnas(df):
    """Elimina espacios en blanco al inicio y final de los nombres de columnas"""
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

def procesar_inteligencia(ws_cli, ws_ven):
    # 1) Cargar Datos
    data_cli = ws_cli.get_all_records() if ws_cli else []
    data_ven = ws_ven.get_all_records() if ws_ven else []

    df_cli = pd.DataFrame(data_cli)
    df_ven = pd.DataFrame(data_ven)

    df_cli = limpiar_columnas(df_cli)
    df_ven = limpiar_columnas(df_ven)

    if df_cli.empty:
        return pd.DataFrame(), pd.DataFrame(), "Sin clientes"

    # 2) Normalización (robusta)
    col_ced = _find_col(df_cli, ["Cedula", "Cédula", "Cedula_Cliente"])
    if col_ced is None:
        df_cli["Cedula"] = ""
        col_ced = "Cedula"
    df_cli[col_ced] = df_cli[col_ced].astype(str).str.replace(r"\.0$", "", regex=True)

    col_nom = _find_col(df_cli, ["Nombre", "Nombre_Cliente"])
    if col_nom is None:
        df_cli["Nombre"] = "Cliente"
        col_nom = "Nombre"

    col_masc = _find_col(df_cli, ["Mascota", "Nombre Mascota Principal", "Mascota_Principal"])
    if col_masc is None:
        df_cli["Mascota"] = "Tu Peludito"
        col_masc = "Mascota"

    # 3) Ventas / RFM básico (robusto)
    col_fecha_v = _find_col(df_ven, ["Fecha"])
    col_total_v = _find_col(df_ven, ["Total", "Monto", "Valor"])
    col_ced_v = _find_col(df_ven, ["Cedula_Cliente", "Cedula", "Cédula"])

    if df_ven.empty or col_fecha_v is None or col_total_v is None or col_ced_v is None:
        df_cli["Estado"] = "⚪ Nuevo"
        df_cli["Dias_Sin_Compra"] = 999
        df_cli["Ultima_Compra_Dt"] = pd.NaT
        df_cli["Ultimo_Producto"] = "N/A"
    else:
        df_ven[col_ced_v] = df_ven[col_ced_v].astype(str).str.replace(r"\.0$", "", regex=True)
        df_ven[col_fecha_v] = _safe_to_datetime(df_ven[col_fecha_v])
        df_ven[col_total_v] = _safe_to_num(df_ven[col_total_v])

        col_items = _find_col(df_ven, ["Items", "Items_Detalle"])
        if col_items is None:
            df_ven["Items"] = ""
            col_items = "Items"

        resumen_ventas = df_ven.groupby(col_ced_v).agg({
            col_fecha_v: "max",
            col_total_v: "sum",
            col_items: "last"
        }).reset_index()

        resumen_ventas.columns = ["Cedula", "Ultima_Compra_Dt", "Total_Gastado", "Ultimo_Producto"]

        df_cli = pd.merge(df_cli, resumen_ventas, left_on=col_ced, right_on="Cedula", how="left")
        hoy = pd.Timestamp.now()
        df_cli["Dias_Sin_Compra"] = (hoy - pd.to_datetime(df_cli["Ultima_Compra_Dt"], errors="coerce")).dt.days.fillna(999)

        def clasificar(dias):
            if dias <= 30: return "🟢 Activo"
            if 31 <= dias <= 60: return "🟡 Recompra (Alerta)"
            if 61 <= dias <= 90: return "🟠 Riesgo"
            if dias > 90 and dias != 999: return "🔴 Perdido"
            return "⚪ Nuevo"

        df_cli["Estado"] = df_cli["Dias_Sin_Compra"].apply(clasificar)

    # 4) Cumpleaños mascota (columna flexible) -> estandarizar a Cumple_Mascota_DT SIEMPRE
    df_cli["Es_Cumple_Mes"] = False
    df_cli["Es_Cumple_Hoy"] = False
    df_cli["Cumple_Mascota_DT"] = pd.NaT

    col_nac = _find_col(df_cli, ["Cumpleaños_mascota", "Cumpleanos_mascota", "Cumpleaños Mascota", "Cumpleanos Mascota"])
    if col_nac:
        # Mantener una columna display con el nombre esperado por la UI, aunque la fuente sea distinta
        if "Cumpleaños_mascota" not in df_cli.columns:
            df_cli["Cumpleaños_mascota"] = df_cli[col_nac]

        # Parse robusto: None/"" -> NaT, "2024-12-01" -> OK
        df_cli["Cumple_Mascota_DT"] = pd.to_datetime(df_cli[col_nac], errors="coerce")

        hoy_dt = datetime.now()
        mask_valid = df_cli["Cumple_Mascota_DT"].notna()
        df_cli.loc[mask_valid, "Es_Cumple_Mes"] = df_cli.loc[mask_valid, "Cumple_Mascota_DT"].dt.month == hoy_dt.month
        df_cli.loc[mask_valid, "Es_Cumple_Hoy"] = (
            (df_cli.loc[mask_valid, "Cumple_Mascota_DT"].dt.month == hoy_dt.month) &
            (df_cli.loc[mask_valid, "Cumple_Mascota_DT"].dt.day == hoy_dt.day)
        )
    else:
        # asegurar la columna para que la UI no truene
        if "Cumpleaños_mascota" not in df_cli.columns:
            df_cli["Cumpleaños_mascota"] = None

    return df_cli, df_ven, "OK"

# ==========================================
# 3. GENERADOR DE LINKS WHATSAPP
# ==========================================

def link_whatsapp(telefono, mensaje):
    if not telefono: return None
    # Limpieza agresiva del teléfono
    tel = str(telefono).replace(" ", "").replace("+", "").replace("-", "").replace(".", "").replace("(", "").replace(")", "").strip()
    
    if len(tel) < 7: return None
    # Asumimos código país 57 (Colombia) si es un número de 10 dígitos, ajústalo si estás en otro país
    if len(tel) == 10: tel = "57" + tel
    
    return f"https://wa.me/{tel}?text={quote(mensaje)}"

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================

# =============================
# UTILIDADES Y MENSAJES PROACTIVOS
# =============================
def _extraer_producto_bonito(ultimo_producto: str) -> str:
    """
    Limpia y deja bonito el nombre del producto para mensajes.
    """
    if not ultimo_producto:
        return "su producto favorito"
    prod = str(ultimo_producto).strip()
    for sep in ["-", "(", ")", "/", "[", "]"]:
        prod = prod.replace(sep, " ")
    prod = " ".join(prod.split())
    return prod.title()

def msg_cumple_5pct(nombre: str, mascota: str, estado: str) -> str:
    """
    Mensaje de cumpleaños con incentivo de recompra (5% de descuento).
    """
    nombre = (nombre or "Cliente").strip()
    mascota = (mascota or "tu peludito").strip()
    return (
        f"¡Hola {nombre}! 🎉\n"
        f"¡Hoy celebramos el cumpleaños de {mascota}! 🐾\n"
        f"En Bigotes & Patitas queremos consentirlos con un 5% de descuento en su próxima compra.\n"
        f"Solo responde este mensaje y te ayudamos a elegir lo mejor para {mascota}.\n"
        f"¡Gracias por ser parte de nuestra familia! {estado if estado else ''}"
    )

def msg_recompra(nombre: str, mascota: str, producto: str) -> str:
    """
    Mensaje estándar para la sección 'Plato Vacío' (30-60 días).
    """
    producto = _extraer_producto_bonito(producto)
    mascota = (mascota or "tu peludito").strip()
    nombre = (nombre or "Cliente").strip()
    return (
        f"Hola {nombre}.\n"
        f"¿Cómo va {mascota}? 🐾\n\n"
        f"Te escribo para ayudarte: ¿necesitas más de *{producto}*?\n"
        f"Si me confirmas, te lo dejamos listo hoy (y si quieres, lo enviamos a domicilio)."
    )

def msg_recompra_20(nombre: str, mascota: str, producto: str, dias: int) -> str:
    """
    Mensaje de recompra para clientes con más de 20 días sin comprar.
    """
    nombre = (nombre or "Cliente").strip()
    mascota = (mascota or "tu peludito").strip()
    producto = _extraer_producto_bonito(producto)
    return (
        f"¡Hola {nombre}! 👋\n"
        f"¿Cómo va {mascota}?\n\n"
        f"Hace {dias} días que no compras *{producto}* para {mascota}.\n"
        f"¿Te gustaría que te ayudemos a reponerlo?\n"
        f"Solo responde este mensaje y te asesoramos con mucho gusto."
    )

def msg_inactivo(nombre: str, mascota: str, gancho: str) -> str:
    """
    Mensaje para clientes inactivos, muy cálido y proactivo.
    """
    nombre = (nombre or "Cliente").strip()
    mascota = (mascota or "tu peludito").strip()
    return (
        f"¡Hola {nombre}! 🌈 Hace tiempo no vemos la colita feliz de {mascota} y los extrañamos mucho en Bigotes y Patitas 🥺🐾.\n"
        f"Soy Ángela 👋. Solo pasaba a saludarte y recordarte que aquí seguimos con el corazón abierto. ❤️\n"
        f"¿Cómo han estado? ¡Nos encantaría saber de ustedes! {gancho if gancho else ''} ✨🚚"
    )

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================

def main():
    # Sidebar
    with st.sidebar:
        st.markdown(f"<h1 style='color:{COLOR_PRIMARIO}; text-align: center;'>Nexus Loyalty</h1>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='color:{COLOR_TEXTO}; text-align: center; margin-top: -20px;'>Bigotes y Patitas 🐾</h4>", unsafe_allow_html=True)
        st.markdown("---")
        
        hoy_dt = datetime.now()
        hoy_str = hoy_dt.strftime('%d/%m/%Y')
        
        # Diccionario de meses para mostrar nombre en español
        meses_es = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        mes_actual_nombre = meses_es[hoy_dt.month]

        st.success(f"📅 Hoy es: {hoy_str}")
        st.info(f"🎂 Mes de: **{mes_actual_nombre}**")


    # Carga de datos (conectado al flujo de la app)
    master, df_ven, status = cargar_datos_loyalty()


    # --- MAPEO DE PRODUCTOS A CATEGORÍA (solo concentrados) ---
    # Intentar obtener inventario desde session_state (como en Inventario_Nexus)
    df_inv = None
    if "data_store" in st.session_state:
        df_inv = st.session_state["data_store"].get("df_Inventario", pd.DataFrame())
    if df_inv is not None and not df_inv.empty:
        # Mapeo: UID, ID normalizado, ID original y nombre normalizado a categoría
        prod_to_cat = {}
        nombres_concentrado = set()
        for _, row in df_inv.iterrows():
            cat = str(row.get("Categoria", "")).strip().upper()
            if not cat:
                continue
            # UID
            if "Producto_UID" in row and str(row["Producto_UID"]).strip():
                prod_to_cat[str(row["Producto_UID"]).strip().lower()] = cat
            # ID normalizado
            if "ID_Producto_Norm" in row and str(row["ID_Producto_Norm"]).strip():
                prod_to_cat[str(row["ID_Producto_Norm"]).strip().lower()] = cat
            # ID original
            if "ID_Producto" in row and str(row["ID_Producto"]).strip():
                prod_to_cat[str(row["ID_Producto"]).strip().upper()] = cat
            # Nombre normalizado (solo para concentrados)
            if cat == "CONCENTRADO" and "Nombre" in row and str(row["Nombre"]).strip():
                nombres_concentrado.add(_norm_col(row["Nombre"]))
    else:
        prod_to_cat = {}
        nombres_concentrado = set()


    def es_concentrado(prod):
        """
        Detecta si alguno de los productos vendidos (en una cadena separada por comas) es de la categoría CONCENTRADO
        por UID, ID, o coincidencia parcial de nombre. Limpia cantidades y formatos.
        """
        if not prod or (not prod_to_cat and not nombres_concentrado):
            return False
        # Separar por coma y analizar cada producto individual
        productos = [p.strip() for p in str(prod).split(",") if p.strip()]
        for p in productos:
            # Limpiar cantidades y formatos comunes
            p_limpio = p
            # Quitar cantidades tipo '1x', '2x', '1.0x', 'x1', '(x1)', etc.
            import re
            p_limpio = re.sub(r"^\d+(\.\d+)?x\s*", "", p_limpio, flags=re.IGNORECASE)  # 1x, 1.0x, 2x
            p_limpio = re.sub(r"\(x?\d+\)", "", p_limpio, flags=re.IGNORECASE)  # (x1), (1)
            p_limpio = re.sub(r"x\d+$", "", p_limpio, flags=re.IGNORECASE)  # x1 al final
            p_limpio = p_limpio.strip()
            # Probar como UID (lower)
            key_uid = p_limpio.strip().lower()
            if key_uid in prod_to_cat and prod_to_cat[key_uid] == "CONCENTRADO":
                return True
            # Probar como ID normalizado (lower)
            key_norm = _norm_col(p_limpio)
            if key_norm in prod_to_cat and prod_to_cat[key_norm] == "CONCENTRADO":
                return True
            # Probar como ID original (upper)
            key_id = p_limpio.strip().upper()
            if key_id in prod_to_cat and prod_to_cat[key_id] == "CONCENTRADO":
                return True
            # Coincidencia parcial por nombre normalizado
            for nombre_norm in nombres_concentrado:
                if nombre_norm in key_norm or key_norm in nombre_norm:
                    return True
        return False

    if master.empty:
        st.warning("⚠️ No se encontraron datos de clientes (cli). Sincroniza en la app principal.")
        return

    # --- KPI HEADER (igual que tienes) ---
    st.markdown(f"### <span style='color:{COLOR_PRIMARIO}'>📊</span> Tablero de Control", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    activos = len(master[master['Estado'] == "🟢 Activo"]) if 'Estado' in master.columns else 0
    alertas = len(master[master['Estado'] == "🟡 Recompra (Alerta)"]) if 'Estado' in master.columns else 0
    
    # Contadores de Cumpleaños
    cumple_hoy_count = len(master[master['Es_Cumple_Hoy'] == True]) if 'Es_Cumple_Hoy' in master.columns else 0
    # Cumple mes (excluyendo los de hoy para no duplicar en lógica visual, aunque el filtro de abajo lo maneja)
    cumple_mes_total = len(master[master['Es_Cumple_Mes'] == True]) if 'Es_Cumple_Mes' in master.columns else 0

    col1.metric("Clientes Totales", len(master))
    col2.metric("Activos (Mes)", activos)
    col3.metric("🔥 Recompra Urgente", alertas, delta="Prioridad Alta", delta_color="inverse")
    col4.metric("🎂 Cumpleaños HOY", cumple_hoy_count, delta=f"Total Mes: {cumple_mes_total}")

    st.markdown("---")

    # --- TABS DE GESTIÓN ---
    tabs = st.tabs([
        "🎂 Cumpleaños", 
        "🔄 Smart Rebuy", 
        "💁‍♀️ Servicios (Ángela)", 
        "📅 Campañas (Fechas especiales)",
        "🚑 Recuperación"
    ])

    # ==========================================
    # TAB 1: CUMPLEAÑOS (PRO + CAMPAÑA ±8 DÍAS)
    # ==========================================
    with tabs[0]:
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>🎂</span> Centro de Cumpleaños (Campaña -8/+8 días)", unsafe_allow_html=True)
        st.caption("Objetivo: activar recompra con un gesto de servicio + oferta clara (5% OFF snacks y concentrados).")

        if "Cumple_Mascota_DT" not in master.columns:
            master["Cumple_Mascota_DT"] = pd.NaT

        # KPIs rápidos de campaña
        df_camp = construir_campana_cumple(master, days_before=8, days_after=8)

        c1, c2, c3 = st.columns(3)
        c1.metric("En ventana (-8/+8)", len(df_camp))
        c2.metric("Cumple HOY", int((df_camp["Cumple_Diff_Dias"] == 0).sum()) if not df_camp.empty else 0)
        c3.metric("Próximos 8 días", int((df_camp["Cumple_Diff_Dias"] > 0).sum()) if not df_camp.empty else 0)

        st.markdown("---")
        st.markdown("##### 🎯 Campaña activa: *5% OFF Cumpleaños*")

        if df_camp.empty:
            st.info("No hay peluditos en ventana de cumpleaños (-8/+8) con fecha válida.")
        else:
            cols_show = [c for c in ["Nombre", "Mascota", "Telefono", "Cumple_Ocurrencia", "Estado_Cumple", "Cumple_Diff_Dias"] if c in df_camp.columns]
            st.dataframe(df_camp[cols_show], use_container_width=True, hide_index=True)

            st.markdown("##### 📲 Envío 1 a 1 (WhatsApp listo):")
            # limitar para no saturar
            for _, row in df_camp.head(40).iterrows():
                nom = row.get("Nombre", "Cliente")
                mascota = row.get("Mascota", "tu peludito")
                tel = row.get("Telefono", "")
                estado = row.get("Estado_Cumple", "Cumpleaños")

                msg = msg_cumple_5pct(nom, mascota, estado)
                link = link_whatsapp(tel, msg)

                if link:
                    st.markdown(f"- **{mascota}** (Dueño: {nom}) — {estado} → [Enviar WhatsApp]({link})")
                else:
                    st.write(f"- **{mascota}** (Dueño: {nom}) — {estado} → Teléfono no válido")

    # ==========================================
    # TAB 2: RECOMPRA INTELIGENTE
    # ==========================================
    with tabs[1]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🥣</span> Smart Rebuy (Recompras automáticas)", unsafe_allow_html=True)

        # --- NUEVO: Recompra rápida 20 días ---
        st.markdown("##### Recompra rápida (20 días sin compra)")
        cth1, cth2 = st.columns([1, 2])
        with cth1:
            umbral = st.slider("Umbral (días sin compra)", min_value=10, max_value=45, value=20, step=1)
        with cth2:
            st.caption("Mensaje pensado para activar volumen: corto, directo, con el nombre del peludito y el último alimento.")


        if "Dias_Sin_Compra" in master.columns:
            df_fast = master[(master["Dias_Sin_Compra"] >= umbral) & (master["Dias_Sin_Compra"] <= umbral + 10)].copy()
            # Filtrar solo clientes cuyo último producto es concentrado
            if not df_fast.empty and "Ultimo_Producto" in df_fast.columns:
                df_fast = df_fast[df_fast["Ultimo_Producto"].apply(es_concentrado)]
        else:
            df_fast = pd.DataFrame()

        if df_fast.empty:
            st.success("No hay clientes en la ventana de recompra rápida de concentrados.")
        else:
            cols = [c for c in ["Nombre", "Mascota", "Telefono", "Ultimo_Producto", "Dias_Sin_Compra"] if c in df_fast.columns]
            st.dataframe(df_fast[cols], use_container_width=True, hide_index=True)

            st.markdown("##### Envío 1 a 1 (WhatsApp listo):")
            for _, row in df_fast.head(60).iterrows():
                nom = row.get("Nombre", "Cliente")
                mascota = row.get("Mascota", "tu peludito")
                tel = row.get("Telefono", "")
                prod = row.get("Ultimo_Producto", "su alimento")
                dias = int(row.get("Dias_Sin_Compra", umbral))

                msg = msg_recompra_20(nom, mascota, prod, dias)
                link = link_whatsapp(tel, msg)

                if link:
                    st.markdown(f"- **{mascota}** (Dueño: {nom}) → [WhatsApp Recompra]({link})")

        st.divider()

        # --- EXISTENTE: Alerta 30-60 días (mantener lo tuyo) ---
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🥣</span> Alerta: Plato Vacío (30-60 días)", unsafe_allow_html=True)

        if 'Estado' in master.columns:
            df_rebuy = master[master['Estado'] == "🟡 Recompra (Alerta)"].copy()
            # Filtrar solo clientes cuyo último producto es concentrado
            if not df_rebuy.empty and "Ultimo_Producto" in df_rebuy.columns:
                df_rebuy = df_rebuy[df_rebuy["Ultimo_Producto"].apply(es_concentrado)]
        else:
            df_rebuy = pd.DataFrame()

        if df_rebuy.empty:
            st.success("✅ Todo al día. No hay alertas de recompra urgentes de concentrados.")
        else:
            cols_mostrar = ['Nombre', 'Mascota', 'Telefono', 'Ultimo_Producto', 'Dias_Sin_Compra']
            cols_existentes = [c for c in cols_mostrar if c in df_rebuy.columns]
            st.dataframe(df_rebuy[cols_existentes], use_container_width=True, hide_index=True)
            
            st.markdown("##### 🚀 Click para enviar Recordatorio Bonito:")
            for idx, row in df_rebuy.iterrows():
                nom = row.get('Nombre', 'Cliente')
                mascota = row.get('Mascota', 'tu mascota')
                prod = str(row.get('Ultimo_Producto', 'su alimento')).split('(')[0]
                tel = row.get('Telefono', '')
                
                msg = msg_recompra(nom, mascota, prod)
                link = link_whatsapp(tel, msg)
                
                if link:
                    st.markdown(f"🔸 **{mascota}** (Dueño: {nom}) → [📲 WhatsApp Recompra]({link})")

    # ==========================================
    # TAB 3: SERVICIOS (ÁNGELA)
    # ==========================================
    with tabs[2]:
        st.markdown(f"#### <span style='color:{COLOR_PRIMARIO}'>💁‍♀️</span> Mensajes de Ángela", unsafe_allow_html=True)
        
        if 'Estado' in master.columns:
            df_angela = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido", "⚪ Nuevo"])].copy()
        else:
            df_angela = master.copy()
        
        st.write(f"**Lista de envío ({len(df_angela)} clientes inactivos o nuevos):**")
        
        with st.expander("Ver lista detallada"):
            cols_angela = ['Nombre', 'Mascota', 'Telefono', 'Email']
            st.dataframe(df_angela[[c for c in cols_angela if c in df_angela.columns]], use_container_width=True)

        st.markdown("##### 💌 Enviar Saludo:")
        gancho = "Envío Gratis + una Sorpresa 🎁"  # Valor por defecto para evitar UnboundLocalError
        for idx, row in df_angela.iterrows():
            nom = row.get('Nombre', 'Vecino')
            mascota = row.get('Mascota', 'tu mascota')
            tel = row.get('Telefono', '')
            # Si quieres permitir personalización, podrías leer gancho de un input aquí
            msg_serv = f"¡Hola {nom}! 🌈 Hace tiempo no vemos la colita feliz de {mascota} y los extrañamos mucho en Bigotes y Patitas 🥺🐾. Soy Ángela 👋. Solo pasaba a saludarte y recordarte que aquí seguimos con el corazón abierto. ❤️ ¿Cómo han estado? ¡Nos encantaría saber de ustedes! {gancho if gancho else ''} ✨🚚"
            link = link_whatsapp(tel, msg_serv)
            if link:
                st.write(f"💕 **{nom} & {mascota}**: [Enviar Saludo]({link})")

    # ==========================================
    # TAB 4: CAMPAÑAS (NUEVO CENTRO)
    # ==========================================
    with tabs[3]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>📅</span> Campañas activas (calendario + segmentación)", unsafe_allow_html=True)

        cal = calendario_campanas()
        hoy = pd.Timestamp.now().normalize()
        proximas = cal[(cal["Fecha"] >= hoy) & (cal["Fecha"] <= hoy + pd.Timedelta(days=120))].copy()

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("**Próximas fechas (120 días):**")
            st.dataframe(proximas, use_container_width=True, hide_index=True)

        with c2:
            evento_sel = st.selectbox(
                "Elegir evento",
                options=proximas["Evento"].tolist() if not proximas.empty else cal["Evento"].tolist()
            )
            tag_sel = cal[cal["Evento"] == evento_sel]["Tag"].iloc[0]
            promo = st.text_input("Promo / Gancho", value="10% OFF + Domicilio gratis (hoy)", help="Corto, claro, con urgencia suave.")
            template = st.text_area("Mensaje (editable)", value=plantilla_evento(tag_sel), height=160)

        st.markdown("---")
        st.markdown("**Segmentación (a quién se le envía):**")
        seg = st.selectbox("Segmento", ["Todos", "🟢 Activo", "🟡 Recompra (Alerta)", "🟠 Riesgo", "🔴 Perdido", "⚪ Nuevo"])
        df_target = master.copy()
        if seg != "Todos" and "Estado" in df_target.columns:
            df_target = df_target[df_target["Estado"] == seg].copy()

        st.caption(f"Destinatarios: {len(df_target)}")

        if len(df_target) == 0:
            st.info("No hay destinatarios para ese segmento.")
        else:
            out = construir_links_campana(df_target, template=template, promo=promo)
            st.dataframe(out, use_container_width=True, hide_index=True)

            # export
            csv = out.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Descargar lista (CSV) con mensajes y links",
                data=csv,
                file_name=f"campana_{tag_sel}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.markdown("##### Links listos para enviar:")
            for _, r in out.head(25).iterrows():
                if r["Link"]:
                    st.markdown(f"- **{r['Nombre']}** ({r['Mascota']}) → [WhatsApp]({r['Link']})")

    # ==========================================
    # TAB 5: RECUPERACIÓN
    # ==========================================
    with tabs[4]:
        st.markdown(f"#### <span style='color:{COLOR_ACENTO}'>🚑</span> Rescate con Oferta", unsafe_allow_html=True)
        
        if 'Estado' in master.columns:
            df_risk = master[master['Estado'].isin(["🟠 Riesgo", "🔴 Perdido"])].copy()
            # Filtrar solo clientes cuyo último producto es concentrado
            if not df_risk.empty and "Ultimo_Producto" in df_risk.columns:
                df_risk = df_risk[df_risk["Ultimo_Producto"].apply(es_concentrado)]
        else:
            df_risk = pd.DataFrame()
        
        if df_risk.empty:
            st.success("¡Excelente! No tienes clientes perdidos de concentrados.")
        else:
            st.write(f"Detectamos {len(df_risk)} clientes para recuperar (concentrados).")
            gancho = st.text_input("Oferta Gancho:", "Envío Gratis + una Sorpresa 🎁")
            
            with st.expander("Ver lista de recuperación"):
                for idx, row in df_risk.iterrows():
                    nom = row.get('Nombre', 'Cliente')
                    mascota = row.get('Mascota', 'tu mascota')
                    tel = row.get('Telefono', '')
                    
                    msg = msg_inactivo(nom, mascota, gancho)
                    link = link_whatsapp(tel, msg)
                    
                    if link:
                        st.markdown(f"🎣 **Recuperar a {nom}**: [Enviar Oferta]({link})")

if __name__ == "__main__":
    main()
