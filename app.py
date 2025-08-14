import pandas as pd
import streamlit as st

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")

st.title("📊 Dashboard de Abastecimento")

# Upload das planilhas
file_interno = st.file_uploader("Upload da Planilha de Abastecimento Interno", type=["xlsx"])
file_externo = st.file_uploader("Upload da Planilha de Abastecimento Externo", type=["xlsx"])

if file_interno and file_externo:
    # Leitura das abas
    df_interno = pd.read_excel(file_interno)
    df_externo = pd.read_excel(file_externo)

    # Normalizar colunas internas
    df_interno.columns = df_interno.columns.str.strip().str.lower()
    df_interno.rename(columns={
        "placa": "placa",
        "km atual": "km atual",
        "quantidade de litros": "quantidade de litros",
        "data": "data"
    }, inplace=True)

    # Normalizar colunas externas
    df_externo.columns = df_externo.columns.str.strip().str.lower()
    df_externo.rename(columns={
        "placa": "placa",
        "km atual": "km atual",
        "consumo": "quantidade de litros",
        "data": "data"
    }, inplace=True)

    # Padronizar tipos
    for df in [df_interno, df_externo]:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df["quantidade de litros"] = pd.to_numeric(df["quantidade de litros"], errors="coerce")
        df["km atual"] = pd.to_numeric(df["km atual"], errors="coerce")

    # Juntar os dois
    df_total = pd.concat([df_interno, df_externo], ignore_index=True)

    # Calcular autonomia
    def calcula_autonomia(df):
        resultados = []
        # Filtrar placas inválidas e litros > 0
        df = df[~df['placa'].isin(['CORREÇÃO', '-', 'correção'])]
        df = df[df['quantidade de litros'] > 0]
        for placa, g in df.groupby('placa'):
            g = g.sort_values('data')
            g = g.drop_duplicates(subset=['km atual'], keep='last')  # evita duplicatas de KM
            if len(g) < 2:
                continue
            km_max = g['km atual'].max()
            km_min = g['km atual'].min()
            litros = g['quantidade de litros'].sum()
            if litros <= 0:
                continue
            autonomia = (km_max - km_min) / litros
            resultados.append({'Placa': placa, 'Autonomia (km/L)': autonomia})
        return pd.DataFrame(resultados).sort_values('Autonomia (km/L)', ascending=False)

    df_autonomia = calcula_autonomia(df_total)

    # Exibir resultado
    st.subheader("🚗 Autonomia (km/L) por Veículo")
    st.dataframe(df_autonomia, use_container_width=True)

else:
    st.info("Por favor, envie as duas planilhas para continuar.")
