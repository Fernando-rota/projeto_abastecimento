import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")

# -------------------------
# FUNÇÕES AUXILIARES
# -------------------------

@st.cache_data
def carregar_dados(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        return df
    return pd.DataFrame()

def calcular_consumo_medio(df_filtrado):
    """
    Calcula o consumo médio por veículo usando:
    (KM mais recente - KM mais antigo) / Soma de litros abastecidos
    Considera apenas o período e filtros aplicados.
    """
    resultados = []

    if df_filtrado.empty:
        return pd.DataFrame(columns=[
            "Placa", "KM Inicial", "KM Final", "Total Litros", "Consumo Médio (km/l)"
        ])

    # Normaliza colunas
    df_filtrado["km_atual"] = pd.to_numeric(df_filtrado["km_atual"], errors="coerce")
    df_filtrado["quantidade_de_litros"] = pd.to_numeric(df_filtrado["quantidade_de_litros"], errors="coerce")

    # Remove registros inválidos
    df_filtrado = df_filtrado.dropna(subset=["km_atual", "quantidade_de_litros"])
    df_filtrado = df_filtrado[df_filtrado["quantidade_de_litros"] > 0]

    for placa, grupo in df_filtrado.groupby("placa"):
        grupo = grupo.sort_values("km_atual")

        km_inicial = grupo["km_atual"].iloc[0]
        km_final = grupo["km_atual"].iloc[-1]
        total_litros = grupo["quantidade_de_litros"].sum()

        if km_final > km_inicial and total_litros > 0:
            consumo_medio = (km_final - km_inicial) / total_litros
            resultados.append({
                "Placa": placa,
                "KM Inicial": km_inicial,
                "KM Final": km_final,
                "Total Litros": round(total_litros, 2),
                "Consumo Médio (km/l)": round(consumo_medio, 2)
            })

    return pd.DataFrame(resultados).sort_values(by="Consumo Médio (km/l)", ascending=False)

# -------------------------
# INTERFACE STREAMLIT
# -------------------------

st.title("⛽ Dashboard de Abastecimento - Interno + Externo")

# Upload dos arquivos
st.sidebar.header("📂 Upload de Arquivos")
file_interno = st.sidebar.file_uploader("Abastecimento Interno", type=["xlsx"])
file_externo = st.sidebar.file_uploader("Abastecimento Externo", type=["xlsx"])

df_interno = carregar_dados(file_interno)
df_externo = carregar_dados(file_externo)

# Padroniza nomes de colunas para compatibilidade
if not df_interno.empty:
    df_interno.rename(columns={
        "Data": "data",
        "Placa": "placa",
        "KM Atual": "km_atual",
        "Quantidade de litros": "quantidade_de_litros"
    }, inplace=True)
    df_interno["origem"] = "Interno"

if not df_externo.empty:
    df_externo.rename(columns={
        "DATA": "data",
        "PLACA": "placa",
        "KM ATUAL": "km_atual",
        "CONSUMO": "quantidade_de_litros"
    }, inplace=True)
    df_externo["origem"] = "Externo"

