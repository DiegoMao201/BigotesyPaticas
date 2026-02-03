import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Análisis Financiero | Bigotes y Patitas",
    page_icon="📈",
    layout="wide"
)

# --- CARGA DE DATOS DESDE SESSION_STATE ---
def cargar_datos():
    if 'db' not in st.session_state:
        st.error("Primero debes sincronizar los datos desde la app principal.")
        st.stop()
    df_ven = st.session_state.db['ven'].copy()
    df_gas = st.session_state.db['gas'].copy()
    return df_ven, df_gas

# --- FILTRO DE FECHAS ---
def filtrar_por_fecha(df, col='Fecha', desde=None, hasta=None):
    df = df.copy()
    df[col] = pd.to_datetime(df[col], errors='coerce')
    if desde:
        df = df[df[col] >= desde]
    if hasta:
        df = df[df[col] <= hasta]
    return df

# --- KPIs ---
def calcular_kpis(df_ven, df_gas):
    total_ventas = df_ven['Total'].sum()
    total_gastos = df_gas['Monto'].sum()
    costo_ventas = df_ven['Costo_Total'].sum() if 'Costo_Total' in df_ven.columns else 0
    margen = total_ventas - costo_ventas
    margen_pct = (margen / total_ventas * 100) if total_ventas > 0 else 0
    return total_ventas, margen, margen_pct, total_gastos

# --- PUNTO DE EQUILIBRIO ---
def calcular_punto_equilibrio(df_ven, df_gas):
    # Buscar columna 'Tipo' ignorando mayúsculas y espacios
    tipo_col = next((c for c in df_gas.columns if c.strip().lower() == 'tipo'), None)
    if tipo_col:
        gastos_fijos = df_gas[df_gas[tipo_col] == 'Fijo']['Monto'].sum()
    else:
        gastos_fijos = 0
    # Margen de contribución: margen promedio sobre ventas
    total_ventas = df_ven['Total'].sum()
    costo_ventas = df_ven['Costo_Total'].sum() if 'Costo_Total' in df_ven.columns else 0
    if total_ventas == 0:
        return 0, 0
    margen_contribucion = (total_ventas - costo_ventas) / total_ventas
    if margen_contribucion == 0:
        return 0, 0
    punto_equilibrio = gastos_fijos / margen_contribucion
    return punto_equilibrio, margen_contribucion

# --- PROYECCIÓN FINANCIERA ---
def proyeccion_financiera(df_ven, df_gas, meses=12):
    # Promedios mensuales
    df_ven['Mes'] = pd.to_datetime(df_ven['Fecha']).dt.to_period('M')
    df_gas['Mes'] = pd.to_datetime(df_gas['Fecha']).dt.to_period('M')
    ventas_mensuales = df_ven.groupby('Mes')['Total'].sum().mean()
    gastos_mensuales = df_gas.groupby('Mes')['Monto'].sum().mean()
    costo_ventas_mensual = df_ven.groupby('Mes')['Costo_Total'].sum().mean() if 'Costo_Total' in df_ven.columns else 0
    margen_mensual = ventas_mensuales - costo_ventas_mensual

    proy = []
    saldo = 0
    for m in range(1, meses+1):
        saldo += margen_mensual - gastos_mensuales
        proy.append({
            "Mes": f"{m}",
            "Ventas": ventas_mensuales,
            "Gastos": gastos_mensuales,
            "Margen": margen_mensual,
            "Saldo_Acumulado": saldo
        })
    return pd.DataFrame(proy)

# --- UI PRINCIPAL ---
def main():
    st.title("📈 Análisis Financiero y Proyección")
    df_ven, df_gas = cargar_datos()

    # --- FILTRO DE FECHAS ---
    st.sidebar.header("Filtros de Fecha")
    min_date = min(df_ven['Fecha'].min(), df_gas['Fecha'].min())
    max_date = max(df_ven['Fecha'].max(), df_gas['Fecha'].max())
    desde = st.sidebar.date_input("Desde", min_date)
    hasta = st.sidebar.date_input("Hasta", max_date)

    # Convertir a datetime para evitar TypeError
    desde_dt = pd.to_datetime(desde)
    hasta_dt = pd.to_datetime(hasta) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    df_ven_f = filtrar_por_fecha(df_ven, 'Fecha', desde_dt, hasta_dt)
    df_gas_f = filtrar_por_fecha(df_gas, 'Fecha', desde_dt, hasta_dt)

    tabs = st.tabs(["📊 KPIs & Resumen", "📅 Ventas y Gastos", "⚖️ Punto de Equilibrio", "🚀 Proyección 6-12 Meses"])

    # --- TAB 1: KPIs ---
    with tabs[0]:
        st.header("KPIs Generales")
        total_ventas, margen, margen_pct, total_gastos = calcular_kpis(df_ven_f, df_gas_f)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ventas", f"${total_ventas:,.0f}")
        c2.metric("Margen Ganado", f"${margen:,.0f}", f"{margen_pct:.1f}%")
        c3.metric("Gastos", f"${total_gastos:,.0f}")
        c4.metric("Utilidad Neta", f"${(margen-total_gastos):,.0f}")

        st.markdown("#### Detalle de Ventas")
        st.dataframe(df_ven_f[['Fecha','Nombre_Cliente','Total','Costo_Total']], use_container_width=True)
        st.markdown("#### Detalle de Gastos")
        st.dataframe(df_gas_f[['Fecha','Categoria','Descripcion','Monto']], use_container_width=True)

    # --- TAB 2: VENTAS Y GASTOS ---
    with tabs[1]:
        st.header("Evolución de Ventas y Gastos")
        df_ven_f['Fecha_D'] = pd.to_datetime(df_ven_f['Fecha']).dt.date
        df_gas_f['Fecha_D'] = pd.to_datetime(df_gas_f['Fecha']).dt.date
        ventas_diario = df_ven_f.groupby('Fecha_D')['Total'].sum()
        gastos_diario = df_gas_f.groupby('Fecha_D')['Monto'].sum()
        df_plot = pd.DataFrame({
            "Ventas": ventas_diario,
            "Gastos": gastos_diario
        }).fillna(0)
        st.line_chart(df_plot)

        st.markdown("#### Top 10 Ventas")
        top_ventas = df_ven_f.sort_values('Total', ascending=False).head(10)
        st.table(top_ventas[['Fecha','Nombre_Cliente','Total']])

        st.markdown("#### Top 10 Gastos")
        top_gastos = df_gas_f.sort_values('Monto', ascending=False).head(10)
        st.table(top_gastos[['Fecha','Categoria','Descripcion','Monto']])

    # --- TAB 3: PUNTO DE EQUILIBRIO ---
    with tabs[2]:
        st.header("Punto de Equilibrio")
        pe, mc = calcular_punto_equilibrio(df_ven_f, df_gas_f)
        st.metric("Punto de Equilibrio (Ventas necesarias)", f"${pe:,.0f}")
        st.metric("Margen de Contribución", f"{mc*100:.1f}%")
        st.info("El punto de equilibrio es el nivel de ventas donde cubres todos tus gastos fijos.")

    # --- TAB 4: PROYECCIÓN ---
    with tabs[3]:
        st.header("Proyección Financiera")
        st.markdown("Proyección basada en el promedio mensual de ventas, costos y gastos.")
        proy6 = proyeccion_financiera(df_ven_f, df_gas_f, meses=6)
        proy12 = proyeccion_financiera(df_ven_f, df_gas_f, meses=12)
        st.subheader("Próximos 6 meses")
        st.dataframe(proy6, use_container_width=True)
        st.line_chart(proy6.set_index("Mes")[["Saldo_Acumulado"]])
        st.subheader("Próximos 12 meses")
        st.dataframe(proy12, use_container_width=True)
        st.line_chart(proy12.set_index("Mes")[["Saldo_Acumulado"]])

if __name__ == "__main__":
    main()