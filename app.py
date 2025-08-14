import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")

# ==============================
# Função para cálculo de consumo médio
# ==============================
def calcular_consumo_medio(df):
    df = df[~df['Placa'].isin(['-', 'correção'])]
    df = df.dropna(subset=['KM Atual', 'Quantidade de litros'])
    df = df[df['Quantidade de litros'] > 0]

    resultados = []
    for placa, grupo in df.groupby('Placa'):
        km_max = grupo['KM Atual'].max()
        km_min = grupo['KM Atual'].min()
        litros_totais = grupo['Quantidade de litros'].sum()

        consumo_medio = None
        if litros_totais > 0 and km_max > km_min:
            consumo_medio = (km_max - km_min) / litros_totais

        resultados.append({
            'Placa': placa,
            'KM Máximo': km_max,
            'KM Mínimo': km_min,
            'Litros Totais': litros_totais,
            'Consumo Médio (km/L)': round(consumo_medio, 2) if consumo_medio else None
        })

    return pd.DataFrame(resultados)

# ==============================
# Upload dos arquivos
# ==============================
st.sidebar.header("Upload das Planilhas")
file_interno = st.sidebar.file_uploader("Abastecimento Interno (.xlsx)", type="xlsx")
file_externo = st.sidebar.file_uploader("Abastecimento Externo (.xlsx)", type="xlsx")

if file_interno and file_externo:
    df_interno = pd.read_excel(file_interno)
    df_externo = pd.read_excel(file_externo)

    # Garantir nomes consistentes
    df_interno.rename(columns={
        'Placa': 'Placa',
        'KM Atual': 'KM Atual',
        'Quantidade de litros': 'Quantidade de litros'
    }, inplace=True)

    df_externo.rename(columns={
        'placa': 'Placa',
        'km atual': 'KM Atual',
        'consumo': 'Quantidade de litros'
    }, inplace=True)

    # Filtros globais
    todas_placas = sorted(set(df_interno['Placa'].dropna()) | set(df_externo['Placa'].dropna()))
    todas_placas = [p for p in todas_placas if p not in ['-', 'correção']]

    filtro_placa = st.sidebar.multiselect("Filtrar por Placa", options=todas_placas, default=todas_placas)

    df_interno = df_interno[df_interno['Placa'].isin(filtro_placa)]
    df_externo = df_externo[df_externo['Placa'].isin(filtro_placa)]

    # ==============================
    # Abas
    # ==============================
    tab1, tab2, tab3 = st.tabs(["📊 Resumo Geral", "🏆 Top 10 Consumo Médio", "📈 Tendência"])

    with tab1:
        st.subheader("Resumo do Consumo Médio")
        consumo_interno = calcular_consumo_medio(df_interno)
        consumo_externo = calcular_consumo_medio(df_externo)
        consumo_total = pd.concat([consumo_interno, consumo_externo]).groupby("Placa").mean(numeric_only=True).reset_index()

        st.dataframe(consumo_total, use_container_width=True)

    with tab2:
        st.subheader("Top 10 Veículos Mais Econômicos")
        top10 = consumo_total.sort_values(by="Consumo Médio (km/L)", ascending=False).head(10)
        fig_top10 = px.bar(top10, x="Placa", y="Consumo Médio (km/L)", text="Consumo Médio (km/L)")
        st.plotly_chart(fig_top10, use_container_width=True)

    with tab3:
        st.subheader("Tendência de Consumo Médio")
        consumo_interno['Origem'] = 'Interno'
        consumo_externo['Origem'] = 'Externo'
        consumo_comb = pd.concat([consumo_interno, consumo_externo])

        fig_tend = px.line(consumo_comb, x="Placa", y="Consumo Médio (km/L)", color="Origem", markers=True)
        st.plotly_chart(fig_tend, use_container_width=True)

else:
    st.warning("Faça o upload das planilhas internas e externas para visualizar o dashboard.")
