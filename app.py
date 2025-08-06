import streamlit as st
import pandas as pd
import plotly.express as px
from utils import (
    carregar_dados,
    calcular_indicadores_resumo,
    preparar_dados_tendencia,
    calcular_consumo_medio,
)

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

st.title("⛽ Dashboard de Abastecimento de Frota")

uploaded_file = st.sidebar.file_uploader("📤 Envie a planilha (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = carregar_dados(uploaded_file)

    # Filtros globais
    placas = df['placa'].dropna().unique()
    combustiveis = df['combustivel'].unique()

    placa_filtro = st.sidebar.multiselect("🔎 Filtrar por Placa", placas, default=placas)
    combustivel_filtro = st.sidebar.multiselect("⛽ Tipo de Combustível", combustiveis, default=combustiveis)

    df = df[df['placa'].isin(placa_filtro)]
    df = df[df['combustivel'].isin(combustivel_filtro)]

    aba = st.selectbox("📂 Escolha uma aba", [
        "📊 Resumo Geral",
        "🏆 Top Veículos",
        "📈 Tendência de Abastecimento",
        "⛽ Consumo Médio"
    ])

    if aba == "📊 Resumo Geral":
        indicadores = calcular_indicadores_resumo(df)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🔧 Total de Litros", f"{indicadores['total_litros']:.0f} L")
        col2.metric("💸 Total Gasto (apenas externo)", f"R$ {indicadores['total_valor']:.2f}")
        col3.metric("💰 Valor Médio por Litro", f"R$ {indicadores['valor_medio']:.2f}")
        col4.metric("🏭 % Interno", f"{indicadores['pct_interno']*100:.1f}%")

    elif aba == "🏆 Top Veículos":
        top_veiculos = df.groupby('placa')['litros'].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(top_veiculos, x='placa', y='litros', title="Top 10 Veículos por Litros Abastecidos")
        st.plotly_chart(fig, use_container_width=True)

    elif aba == "📈 Tendência de Abastecimento":
        tendencia = preparar_dados_tendencia(df)
        fig_tendencia = px.bar(
            tendencia,
            x='ano_mes',
            y='litros',
            color='origem',
            barmode='stack',
            text_auto='.0f',
            title="Litros Abastecidos por Mês"
        )
        fig_tendencia.update_layout(xaxis_title="Mês", yaxis_title="Litros Abastecidos")
        st.plotly_chart(fig_tendencia, use_container_width=True)

    elif aba == "⛽ Consumo Médio":
        consumo = calcular_consumo_medio(df)
        media = consumo.groupby('placa')['km_por_litro'].mean().sort_values(ascending=False).reset_index()
        fig = px.bar(media, x='placa', y='km_por_litro', title="Consumo Médio (km/l)")
        fig.update_layout(xaxis_title="Placa", yaxis_title="km/l")
        st.plotly_chart(fig, use_container_width=True)
