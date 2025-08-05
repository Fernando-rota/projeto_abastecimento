import streamlit as st
import pandas as pd
from utils import processar_planilha, calcular_consumo, comparar_fontes, gerar_graficos

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("📊 Dashboard de Abastecimento de Frota")

# Upload da planilha
arquivo = st.file_uploader("📂 Faça upload da planilha de abastecimento (.xlsx)", type=["xlsx"])
if arquivo:
    df_unificado, df_interno, df_externo = processar_planilha(arquivo)
    
    # Filtros globais
    placas = sorted(df_unificado['placa'].dropna().unique())
    placa_selecionada = st.multiselect("🚚 Filtrar por Placa", placas, default=placas)
    tipo_selecionado = st.multiselect("⛽ Tipo de Abastecimento", ["Interno", "Externo"], default=["Interno", "Externo"])
    data_min, data_max = df_unificado["data"].min(), df_unificado["data"].max()
    data_range = st.date_input("📅 Período", [data_min, data_max])

    df_filtrado = df_unificado[
        (df_unificado['placa'].isin(placa_selecionada)) &
        (df_unificado['tipo'].isin(tipo_selecionado)) &
        (df_unificado['data'].between(pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])))
    ]

    st.subheader("📈 Consumo Médio por Veículo (km/l)")
    consumo_df = calcular_consumo(df_filtrado)
    st.dataframe(consumo_df)

    st.subheader("⚖️ Comparativo Interno x Externo")
    comparativo_df = comparar_fontes(df_filtrado)
    st.dataframe(comparativo_df)

    st.subheader("📊 Gráficos Interativos")
    gerar_graficos(df_filtrado)
