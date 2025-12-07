import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta
import json
import uuid
from urllib.parse import quote

# ==========================================
# 1. CONFIGURATION & STYLING
# ==========================================

st.set_page_config(
    page_title="NEXUS PRO | Ultimate SCM",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Professional "Deep Space" & Glassmorphism CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Global Colors */
    :root {
        --primary: #4f46e5;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --bg-light: #f8fafc;
    }

    .stApp { background-color: var(--bg-light); }

    /* Cards/Metrics */
    div[data-testid="metric-container"] {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid var(--primary);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: scale(1.02);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 8px;
        padding-left: 20px;
        padding-right: 20px;
        border: 1px solid #e2e8f0;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary);
        color: white;
    }

    /* DataFrame */
    .stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #e5e7eb; }
    
    h1, h2, h3 { color: #1e293b; font-weight: 800; }
    .highlight { color: var(--primary); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ROBUST DATABASE ENGINE
# ==========================================

@st.cache_resource
def connect_db():
    """Persistent connection to Google Sheets."""
    try:
        if "google_service_account" not in st.secrets:
            st.error("❌ Missing 'google_service_account' in secrets.toml")
            return None
        
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sh = gc.open_by_url(st.secrets["SHEET_URL"])
        return sh
    except Exception as e:
        st.error(f"🔴 Connection Error: {e}")
        return None

def get_worksheet_safe(sh, name, headers):
    try:
        return sh.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=100, cols=20)
        ws.append_row(headers)
        return ws

def clean_currency(x):
    """Converts '$1,200.00' or strings to float safely."""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        clean = x.replace('$', '').replace(',', '').replace(' ', '').strip()
        if not clean: return 0.0
        try:
            return float(clean)
        except:
            return 0.0
    return 0.0

def load_data(sh):
    # Schemas
    schema_inv = ['ID_Producto', 'Nombre', 'Categoria', 'Stock', 'Costo', 'Precio', 'SKU_Proveedor'] # Added SKU_Proveedor
    schema_ven = ['ID_Venta', 'Fecha', 'Items', 'Total']
    schema_prov = ['Nombre_Proveedor', 'SKU_Interno', 'Costo_Proveedor', 'Factor_Pack', 'Email', 'Telefono']
    schema_hist = ['ID_Orden', 'Proveedor', 'Fecha_Orden', 'Items_JSON', 'Total', 'Estado', 'Fecha_Recepcion', 'Lead_Time_Real', 'Calificacion']

    # Load Sheets
    ws_inv = get_worksheet_safe(sh, "Inventario", schema_inv)
    ws_ven = get_worksheet_safe(sh, "Ventas", schema_ven)
    ws_prov = get_worksheet_safe(sh, "Maestro_Proveedores", schema_prov)
    ws_hist = get_worksheet_safe(sh, "Historial_Ordenes", schema_hist)

    # Convert to DF
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_ven = pd.DataFrame(ws_ven.get_all_records())
    df_prov = pd.DataFrame(ws_prov.get_all_records())
    df_hist = pd.DataFrame(ws_hist.get_all_records())

    # --- CRITICAL: DATA CLEANING ---
    
    # 1. Clean Inventory (The Source of Truth)
    if not df_inv.empty:
        df_inv['Stock'] = pd.to_numeric(df_inv['Stock'], errors='coerce').fillna(0)
        df_inv['Costo'] = df_inv['Costo'].apply(clean_currency)
        df_inv['Precio'] = df_inv['Precio'].apply(clean_currency)
        df_inv['ID_Producto'] = df_inv['ID_Producto'].astype(str).str.strip()
        # Remove duplicates in Inventory to prevent "4x value" bug
        df_inv = df_inv.drop_duplicates(subset=['ID_Producto'], keep='first')

    # 2. Clean Suppliers
    if not df_prov.empty:
        df_prov['SKU_Interno'] = df_prov['SKU_Interno'].astype(str).str.strip()
        df_prov['Costo_Proveedor'] = df_prov['Costo_Proveedor'].apply(clean_currency)
        df_prov['Factor_Pack'] = pd.to_numeric(df_prov['Factor_Pack'], errors='coerce').fillna(1)

    return df_inv, df_ven, df_prov, df_hist, ws_hist

# ==========================================
# 3. NEXUS BRAIN (LOGIC ENGINE)
# ==========================================

def run_intelligence(df_inv, df_ven, df_prov):
    """
    Separates the logic into two paths:
    1. Inventory Metrics (Strictly based on stock)
    2. Purchasing Logic (Based on suppliers)
    """

    # --- STEP 1: ANALYZE SALES (VELOCITY) ---
    df_ven['Fecha'] = pd.to_datetime(df_ven['Fecha'], errors='coerce')
    cutoff_90 = datetime.now() - timedelta(days=90)
    ven_recent = df_ven[df_ven['Fecha'] >= cutoff_90]
    
    stats = {}
    
    # Logic to parse items. Supports "ItemA, ItemB" or simple list
    for _, row in ven_recent.iterrows():
        items_raw = str(row['Items'])
        # Simple split by comma (enhance this if you use JSON in sales)
        items = [x.strip() for x in items_raw.split(',')]
        
        for item in items:
            # Clean name (remove parenthesis if 'Product (2)')
            prod_name = item.split('(')[0].strip()
            stats[prod_name] = stats.get(prod_name, 0) + 1

    df_sales = pd.DataFrame(list(stats.items()), columns=['Nombre', 'Units_90d'])
    
    # --- STEP 2: MERGE WITH INVENTORY (LEFT JOIN) ---
    # We maintain 1 row per product here. Crucial for correct valuation.
    master_inv = pd.merge(df_inv, df_sales, on='Nombre', how='left').fillna({'Units_90d': 0})
    
    # --- STEP 3: CALCULATE METRICS ---
    master_inv['Daily_Velocity'] = master_inv['Units_90d'] / 90
    
    # ABC Classification
    master_inv = master_inv.sort_values('Units_90d', ascending=False)
    master_inv['CumSum'] = master_inv['Units_90d'].cumsum()
    master_inv['Total_Sales'] = master_inv['Units_90d'].sum()
    
    if master_inv['Total_Sales'].sum() > 0:
        master_inv['Share'] = master_inv['CumSum'] / master_inv['Total_Sales']
        def classify_abc(x):
            if x <= 0.8: return 'A'
            elif x <= 0.95: return 'B'
            else: return 'C'
        master_inv['ABC'] = master_inv['Share'].apply(classify_abc)
    else:
        master_inv['ABC'] = 'C'

    # Reorder Logic
    LEAD_TIME_AVG = 15 # Days (can be dynamic per supplier in v6)
    SAFETY_STOCK = {'A': 21, 'B': 14, 'C': 7} # Buffer days
    
    master_inv['Safety_Days'] = master_inv['ABC'].map(SAFETY_STOCK)
    master_inv['Reorder_Point'] = master_inv['Daily_Velocity'] * (LEAD_TIME_AVG + master_inv['Safety_Days'])
    
    # Logic: If Stock <= Reorder Point -> Trigger Buy
    master_inv['Status'] = np.where(master_inv['Stock'] <= master_inv['Reorder_Point'], '🚨 Reorder', '✅ OK')
    master_inv['Qty_Needed'] = (master_inv['Reorder_Point'] * 1.5) - master_inv['Stock']
    master_inv['Qty_Needed'] = master_inv['Qty_Needed'].clip(lower=0) # No negative orders

    # --- STEP 4: PREPARE PURCHASE DATAFRAME (RELATIONSHIP: 1-to-Many) ---
    # This DF is ONLY for the Purchase Center, allowing multiple suppliers per product
    
    if not df_prov.empty and 'SKU_Interno' in df_prov.columns:
        # Merge Inventory with Suppliers based on ID/SKU
        master_buy = pd.merge(master_inv, df_prov, left_on='ID_Producto', right_on='SKU_Interno', how='inner')
    else:
        # Fallback if no suppliers configured
        master_buy = master_inv.copy()
        master_buy['Nombre_Proveedor'] = 'Generic Supplier'
        master_buy['Costo_Proveedor'] = master_buy['Costo']
        master_buy['Factor_Pack'] = 1
        master_buy['Telefono'] = ''
        master_buy['Email'] = ''

    # Final Purchase Calcs
    master_buy['Packs_To_Buy'] = np.ceil(master_buy['Qty_Needed'] / master_buy['Factor_Pack'])
    master_buy['Investment_Required'] = master_buy['Packs_To_Buy'] * master_buy['Factor_Pack'] * master_buy['Costo_Proveedor']

    return master_inv, master_buy

# ==========================================
# 4. EXPORT & ACTIONS
# ==========================================

def make_whatsapp_link(phone, provider_name, order_df):
    """
    Intelligent WhatsApp Link Generator.
    """
    if not phone: return None
    
    # Strip non-numeric characters
    clean_phone = ''.join(filter(str.isdigit, str(phone)))
    
    msg = f"👋 Hola *{provider_name}*, requerimos el siguiente pedido:\n\n"
    
    total_est = 0
    for _, row in order_df.iterrows():
        qty = row['Packs_To_Buy']
        name = row['Nombre']
        cost = row['Costo_Proveedor'] * row['Factor_Pack'] * qty
        total_est += cost
        msg += f"📦 *{int(qty)} unds/cajas* - {name}\n"
    
    msg += f"\n💰 *Total Estimado: ${total_est:,.0f}*\n"
    msg += "Quedo atento a la confirmación. ¡Gracias!"
    
    encoded_msg = quote(msg)
    return f"https://wa.me/{clean_phone}?text={encoded_msg}"

def generate_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='PO')
    return output.getvalue()

# ==========================================
# 5. MAIN UI (DASHBOARD)
# ==========================================

def main():
    sh = connect_db()
    if not sh: return

    # 1. Load Data
    df_inv, df_ven, df_prov, df_hist, ws_hist = load_data(sh)

    # 2. Run Brain
    # master_inv -> UNIQUE products (for KPIs)
    # master_buy -> Products X Suppliers (for Purchasing)
    master_inv, master_buy = run_intelligence(df_inv, df_ven, df_prov)

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("💠 NEXUS PRO")
        st.write("Supply Chain Intelligence")
        st.divider()
        
        # Alerts
        criticos = master_inv[master_inv['Status'] == '🚨 Reorder'].shape[0]
        if criticos > 0:
            st.error(f"{criticos} Products need attention!")
        else:
            st.success("All systems operational.")
            
        st.divider()
        st.info("💡 Tip: Update supplier prices in 'Maestro_Proveedores' for better accuracy.")

    # --- HEADER METRICS ---
    st.markdown("## Control Tower")
    
    m1, m2, m3, m4 = st.columns(4)
    
    # KPI 1: Inventory Value (Calculated on UNIQUE inventory, fixing the 4x bug)
    total_inv_val = (master_inv['Stock'] * master_inv['Costo']).sum()
    m1.metric("Inventory Value", f"${total_inv_val:,.0f}")
    
    # KPI 2: Cash Required (Sum of suggestions)
    # We take the best supplier option (min cost) per product to estimate cash needed
    needed_cash = master_buy.groupby('ID_Producto')['Investment_Required'].min().sum()
    m2.metric("Refill Budget", f"${needed_cash:,.0f}", "Projected")
    
    # KPI 3: Sales Velocity
    m3.metric("Sales Velocity", f"{master_inv['Daily_Velocity'].sum():.1f} units/day")
    
    # KPI 4: Pending Orders
    pending = df_hist[df_hist['Estado'] == 'Pendiente'].shape[0] if not df_hist.empty else 0
    m4.metric("Active Orders", pending)

    # --- MAIN TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analytics 360", "🚀 Smart Purchasing", "📥 Reception", "💾 Raw Data"])

    # === TAB 1: ANALYTICS ===
    with tab1:
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("ABC Value Distribution")
            if 'Categoria' in master_inv.columns:
                fig = px.treemap(master_inv, 
                                 path=[px.Constant("Inventory"), 'Categoria', 'Nombre'], 
                                 values='Total_Sales',
                                 color='ABC',
                                 color_discrete_map={'A':'#ef4444', 'B':'#f59e0b', 'C':'#10b981'},
                                 title="Sales Heatmap (Red = Best Sellers)")
                st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.subheader("Top Low Stock")
            low_stock = master_inv[master_inv['Status'] == '🚨 Reorder'].sort_values('ABC')
            st.dataframe(
                low_stock[['Nombre', 'Stock', 'Reorder_Point', 'ABC']],
                hide_index=True,
                column_config={
                    "Stock": st.column_config.NumberColumn("Current", format="%d"),
                    "Reorder_Point": st.column_config.NumberColumn("Trigger", format="%.1f")
                }
            )

    # === TAB 2: SMART PURCHASING (The Fix) ===
    with tab2:
        st.subheader("Purchase Command Center")
        
        # Filter: Only show products that need reordering
        to_buy = master_buy[master_buy['Packs_To_Buy'] > 0].copy()
        
        if to_buy.empty:
            st.success("🎉 Inventory is optimized! No purchases needed.")
        else:
            # 1. Select Supplier
            suppliers = to_buy['Nombre_Proveedor'].unique()
            selected_prov = st.selectbox("Select Supplier to Order From:", suppliers)
            
            # 2. Filter data for that supplier
            order_data = to_buy[to_buy['Nombre_Proveedor'] == selected_prov].copy()
            
            # Get supplier info
            prov_info = df_prov[df_prov['Nombre_Proveedor'] == selected_prov]
            current_phone = prov_info['Telefono'].values[0] if not prov_info.empty else ""
            
            c_left, c_right = st.columns([3, 1])
            
            with c_left:
                st.write(f"**Draft Order for {selected_prov}**")
                # Editable Grid
                edited_order = st.data_editor(
                    order_data[['ID_Producto', 'Nombre', 'Stock', 'Packs_To_Buy', 'Costo_Proveedor', 'Factor_Pack']],
                    hide_index=True,
                    num_rows="dynamic",
                    column_config={
                        "Packs_To_Buy": st.column_config.NumberColumn("Qty to Order", min_value=1),
                        "Costo_Proveedor": st.column_config.NumberColumn("Unit Cost", format="$%.2f"),
                        "ID_Producto": st.column_config.TextColumn("ID", disabled=True),
                        "Stock": st.column_config.NumberColumn("Stock", disabled=True),
                        "Nombre": st.column_config.TextColumn("Product", disabled=True),
                    },
                    use_container_width=True
                )
                
                # Calculate Totals
                total_po = (edited_order['Packs_To_Buy'] * edited_order['Factor_Pack'] * edited_order['Costo_Proveedor']).sum()
                st.metric("Total Purchase Order", f"${total_po:,.2f}")

            with c_right:
                st.markdown("### Actions")
                
                # Manual WhatsApp Input (Requested Feature)
                wa_phone = st.text_input("WhatsApp Number", value=str(current_phone), placeholder="e.g. 573001234567")
                
                # Logic to Generate Link
                if st.button("📲 Generate WhatsApp Link", type="secondary", use_container_width=True):
                    link = make_whatsapp_link(wa_phone, selected_prov, edited_order)
                    if link:
                        st.markdown(f"**[Click to Open WhatsApp]({link})**", unsafe_allow_html=True)
                    else:
                        st.error("Please enter a phone number.")
                
                # Download
                excel_data = generate_excel(edited_order)
                st.download_button("💾 Download Excel", excel_data, file_name=f"PO_{selected_prov}.xlsx", use_container_width=True)
                
                st.divider()
                
                # Commit to DB
                if st.button("🚀 Register Order", type="primary", use_container_width=True):
                    try:
                        order_id = f"PO-{uuid.uuid4().hex[:6].upper()}"
                        items_json = json.dumps(edited_order[['Nombre', 'Packs_To_Buy']].to_dict('records'))
                        
                        row_data = [
                            order_id, selected_prov, str(datetime.now().date()), 
                            items_json, total_po, "Pendiente", "", "", ""
                        ]
                        ws_hist.append_row(row_data)
                        st.balloons()
                        st.toast("Order Created Successfully!")
                    except Exception as e:
                        st.error(f"Error saving: {e}")

    # === TAB 3: RECEPTION ===
    with tab3:
        st.subheader("Inbound Logistics")
        
        pending_orders = df_hist[df_hist['Estado'] == 'Pendiente']
        
        if pending_orders.empty:
            st.info("No pending orders.")
        else:
            for i, row in pending_orders.iterrows():
                with st.expander(f"🚛 {row['Proveedor']} - ${row['Total']:,.0f} ({row['Fecha_Orden']})"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("Items:")
                        try:
                            st.json(json.loads(row['Items_JSON']))
                        except:
                            st.write(row['Items_JSON'])
                    with c2:
                        rec_date = st.date_input("Arrival Date", key=f"d_{row['ID_Orden']}")
                        rating = st.slider("Supplier Rating", 1, 5, 5, key=f"r_{row['ID_Orden']}")
                        
                        if st.button("Confirm Reception", key=f"b_{row['ID_Orden']}"):
                            # Update logic (Find row and update)
                            cell = ws_hist.find(row['ID_Orden'])
                            ws_hist.update_cell(cell.row, 6, "Recibido")
                            ws_hist.update_cell(cell.row, 7, str(rec_date))
                            ws_hist.update_cell(cell.row, 9, rating)
                            st.success("Inventory Updated!")
                            st.rerun()

    # === TAB 4: RAW DATA ===
    with tab4:
        st.info("Raw Database View (Admin)")
        st.dataframe(master_inv)

if __name__ == "__main__":
    main()
