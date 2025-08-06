import streamlit as st
import pandas as pd
import plotly.express as px
from utils import (
    carregar_dados,
    preparar_dados,
    calcular_consumo,
    calcular_preco_medio_interno
)

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")

st.title("📊 Dashboard de Abastecimento de Veículos")

# Upload
arquivo = st.sidebar.file_uploader("📂 Envie a planilha de abastecimento (.xlsx)", type=["xlsx"])

if arquivo:
    externo, interno = carregar_dados(arquivo)
    df = preparar_dados(externo, interno)
    consumo = calcular_consumo(df)
    preco_medio_interno = calcular_preco_medio_interno(interno)

    # Filtros globais
    placas_validas = df['placa'].dropna().unique()
    combustiveis_validos = df['combustivel'].dropna().unique()

    st.sidebar.markdown("### 🔎 Filtros")
    placa_sel = st.sidebar.multiselect("Filtrar por placa", options=sorted(placas_validas), default=sorted(placas_validas))
    combustivel_sel = st.sidebar.multiselect("Filtrar por combustível", options=sorted(combustiveis_validos), default=sorted(combustiveis_validos))
    data_min, data_max = df['data'].min(), df['data'].max()
    data_sel = st.sidebar.date_input("Período", [data_min, data_max], min_value=data_min, max_value=data_max)

    # Aplicar filtros
    df_filtros = df[
        (df['placa'].isin(placa_sel)) &
        (df['combustivel'].isin(combustivel_sel)) &
        (df['data'].between(pd.to_datetime(data_sel[0]), pd.to_datetime(data_sel[1])))
    ]
    consumo_filtros = consumo[
        (consumo['placa'].isin(placa_sel)) &
        (consumo['combustivel'].isin(combustivel_sel)) &
        (consumo['data'].between(pd.to_datetime(data_sel[0]), pd.to_datetime(data_sel[1])))
    ]

    # Abas
    aba = st.tabs([
        "📈 Resumo Geral",
        "⛽️ Abastecimento por Origem",
        "📉 Tendência de Abastecimento",
        "📊 Consumo Médio",
        "🧪 Indicadores Profissionais",
    ])

    # --- RESUMO GERAL ---
    with aba[0]:
        st.subheader("📈 Visão Geral dos Abastecimentos")

        total_litros = df_filtros['litros'].sum()
        total_externo = df_filtros[df_filtros['origem'] == 'Externo']['litros'].sum()
        total_interno = df_filtros[df_filtros['origem'] == 'Interno']['litros'].sum()

        pct_interno = (total_interno / total_litros * 100) if total_litros > 0 else 0
        pct_externo = (total_externo / total_litros * 100) if total_litros > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("🔁 Total Abastecido (L)", f"{total_litros:,.2f}")
        col2.metric("🏭 Interno (%)", f"{pct_interno:.1f}%")
        col3.metric("⛽ Externo (%)", f"{pct_externo:.1f}%")

        fig = px.pie(
            df_filtros,
            names="origem",
            values="litros",
            title="Distribuição por Origem",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- ABASTECIMENTO POR ORIGEM ---
    with aba[1]:
        st.subheader("⛽️ Litros Abastecidos por Origem")
        litros_por_origem = df_filtros.groupby(['origem', 'combustivel'])['litros'].sum().reset_index()
        fig = px.bar(
            litros_por_origem,
            x='combustivel',
            y='litros',
            color='origem',
            barmode='group',
            text_auto=True,
            title="Abastecimento por Combustível e Origem"
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- TENDÊNCIA ---
    with aba[2]:
        st.subheader("📉 Tendência Mensal de Abastecimento")
        tendencia = df_filtros.groupby(['mes', 'origem'])['litros'].sum().reset_index()
        fig = px.bar(
            tendencia,
            x='mes',
            y='litros',
            color='origem',
            barmode='group',
            title="Litros por Mês (Interno vs Externo)"
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- CONSUMO MÉDIO ---
    with aba[3]:
        st.subheader("📊 Consumo Médio por Veículo")
        media_consumo = consumo_filtros.groupby('placa')['km_litro'].mean().reset_index()
        media_consumo = media_consumo.sort_values(by='km_litro', ascending=False)

        fig = px.bar(
            media_consumo,
            x='placa',
            y='km_litro',
            text_auto=".2f",
            title="Ranking de Eficiência (KM/L)"
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- INDICADORES PROFISSIONAIS ---
    with aba[4]:
        st.subheader("🧪 Indicadores Profissionais")

        col1, col2 = st.columns(2)
        col1.metric("💰 Preço Médio Interno (estimado)", f"R$ {preco_medio_interno:.2f}" if preco_medio_interno else "N/A")

        litros_por_combustivel = df_filtros.groupby('combustivel')['litros'].sum().reset_index()
        fig = px.pie(
            litros_por_combustivel,
            names="combustivel",
            values="litros",
            hole=0.3,
            title="Distribuição por Tipo de Combustível"
        )
        st.plotly_chart(fig, use_container_width=True)
