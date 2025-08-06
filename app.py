import streamlit as st
import pandas as pd
from utils import processar_planilha, calcular_consumo, indicadores_resumo, ranking_eficiencia, gerar_graficos

st.set_page_config("📊 Dashboard Abastecimento", layout="wide")
st.title("📊 Dashboard de Indicadores de Consumo e Abastecimento")

arquivo = st.file_uploader("📂 Faça upload da planilha (.xlsx)", type=["xlsx"])

if arquivo:
    df = processar_planilha(arquivo)

    if df.empty:
        st.warning("Nenhum dado encontrado.")
        st.stop()

    # Filtros
    st.sidebar.header("🔎 Filtros")
    placas = sorted(df['placa'].unique())
    tipos = df['tipo'].unique()

    placa_sel = st.sidebar.multiselect("Placa", placas, default=placas)
    tipo_sel = st.sidebar.multiselect("Tipo de Abastecimento", tipos, default=tipos)
    data_min, data_max = df['data'].min(), df['data'].max()
    data_sel = st.sidebar.date_input("Período", [data_min, data_max])

    df_filtrado = df[
        (df['placa'].isin(placa_sel)) &
        (df['tipo'].isin(tipo_sel)) &
        (df['data'].between(pd.to_datetime(data_sel[0]), pd.to_datetime(data_sel[1])))
    ]

    df_consumo = calcular_consumo(df_filtrado)

    aba1, aba2, aba3 = st.tabs(["📋 Resumo Geral", "📈 Gráficos", "🏆 Ranking de Consumo"])

    with aba1:
        st.subheader("🔧 Indicadores Principais")
        col1, col2, col3 = st.columns(3)
        total_litros, total_gasto, media_consumo = indicadores_resumo(df_filtrado)

        col1.metric("🔸 Total de Litros", f"{total_litros} L")
        col2.metric("💰 Total Gasto", f"R$ {total_gasto:,.2f}")
        col3.metric("⛽ Consumo Médio", f"{media_consumo} km/L")

        st.divider()
        st.subheader("📄 Tabela de Dados Filtrados")
        st.dataframe(df_filtrado.sort_values(by='data', ascending=False), use_container_width=True)

    with aba2:
        gerar_graficos(df_filtrado, df_consumo)

    with aba3:
        st.subheader("🏁 Ranking de Eficiência (km/L)")
        ranking = ranking_eficiencia(df_consumo)
        st.dataframe(ranking.rename(columns={'placa': 'Placa', 'consumo_km_l': 'Consumo Médio (km/L)'}), use_container_width=True)
