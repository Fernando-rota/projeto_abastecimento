import streamlit as st
import pandas as pd
from utils import processar_planilha, calcular_consumo, comparar_fontes, gerar_graficos

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("🚚 Dashboard de Abastecimento de Frota")

# Upload da planilha
arquivo = st.file_uploader("📂 Faça upload da planilha de abastecimento (.xlsx)", type=["xlsx"])
if arquivo:
    df_unificado, df_interno, df_externo = processar_planilha(arquivo)

    # Layout dos filtros em colunas
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            placas = sorted(df_unificado['placa'].dropna().unique())
            placa_selecionada = st.multiselect("🚛 Placas", placas, default=placas)

        with col2:
            tipo_selecionado = st.multiselect("⛽ Tipo de Abastecimento", ["Interno", "Externo"], default=["Interno", "Externo"])

        with col3:
            data_min, data_max = df_unificado["data"].min(), df_unificado["data"].max()
            data_range = st.date_input("📅 Período", [data_min, data_max])

    # Aplicar filtros
    df_filtrado = df_unificado[
        (df_unificado['placa'].isin(placa_selecionada)) &
        (df_unificado['tipo'].isin(tipo_selecionado)) &
        (df_unificado['data'].between(pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])))
    ]

    # Abas do dashboard
    aba_resumo, aba_consumo, aba_comparativo, aba_graficos = st.tabs([
        "📊 Resumo Geral",
        "📈 Consumo Médio",
        "⚖️ Comparativo Interno x Externo",
        "📉 Gráficos Interativos"
    ])

    with aba_resumo:
        st.markdown("### 🔎 Registros Filtrados")
        st.dataframe(df_filtrado, use_container_width=True)

    with aba_consumo:
        st.markdown("### 📈 Relatório de Consumo Médio por Veículo (km/l)")
        consumo_df = calcular_consumo(df_filtrado)
        st.dataframe(consumo_df, use_container_width=True)

    with aba_comparativo:
        st.markdown("### ⚖️ Comparativo de Abastecimento Interno x Externo")
        comparativo_df = comparar_fontes(df_filtrado)
        st.dataframe(comparativo_df, use_container_width=True)

    with aba_graficos:
        st.markdown("### 📊 Gráficos Interativos")
        gerar_graficos(df_filtrado)
