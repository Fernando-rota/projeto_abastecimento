import pandas as pd
import streamlit as st

# ============================
# CONFIGURAÇÃO
# ============================
ARQUIVO = "abastecimento.xlsx"  # nome do arquivo local

# ============================
# LEITURA DOS DADOS
# ============================
df_interno = pd.read_excel(ARQUIVO, sheet_name="Abastecimento Interno")
df_externo = pd.read_excel(ARQUIVO, sheet_name="Abastecimento Externo")

# Normalizar colunas
df_interno.columns = df_interno.columns.str.strip()
df_externo.columns = df_externo.columns.str.strip()

# Ajustar tipos de dados
df_interno["Data"] = pd.to_datetime(df_interno["Data"], errors="coerce", dayfirst=True)
df_externo["Data"] = pd.to_datetime(df_externo["Data"], errors="coerce", dayfirst=True)

# Tratar valores numéricos
for col in ["Quantidade de litros", "Valor Unitario", "Valor Total", "KM Atual"]:
    if col in df_interno.columns:
        df_interno[col] = pd.to_numeric(df_interno[col], errors="coerce", downcast="float")

for col in ["Quantidade de litros", "Valor Unitario", "Valor Total", "KM Atual"]:
    if col in df_externo.columns:
        df_externo[col] = pd.to_numeric(df_externo[col], errors="coerce", downcast="float")

# ============================
# LIMPEZA
# ============================
# Remover placas indesejadas
placas_invalidas = ["-", "correção"]
df_interno = df_interno[~df_interno["Placa"].isin(placas_invalidas)]
df_externo = df_externo[~df_externo["Placa"].isin(placas_invalidas)]

# ============================
# CONSUMO MÉDIO POR PLACA
# ============================
def consumo_medio(df):
    resultados = []
    for placa, dados in df.groupby("Placa"):
        km_max = dados["KM Atual"].max()
        km_min = dados["KM Atual"].min()
        litros = dados["Quantidade de litros"].sum()
        if litros > 0 and km_max > km_min:
            media = (km_max - km_min) / litros
            resultados.append({"Placa": placa, "Consumo Médio (Km/L)": media})
    return pd.DataFrame(resultados).sort_values(by="Consumo Médio (Km/L)", ascending=False)

consumo_interno = consumo_medio(df_interno)
consumo_externo = consumo_medio(df_externo)

# ============================
# PREÇO MÉDIO INTERNO (apenas a partir de julho)
# ============================
df_interno_com_preco = df_interno[df_interno["Valor Unitario"].notna()]
df_interno_com_preco = df_interno_com_preco[df_interno_com_preco["Data"].dt.month >= 7]
preco_medio_interno = df_interno_com_preco["Valor Unitario"].mean()

# ============================
# INDICADORES MENSAIS
# ============================
def indicadores_mensais(df, tipo):
    df["AnoMes"] = df["Data"].dt.to_period("M")
    agg = df.groupby("AnoMes").agg({
        "Quantidade de litros": "sum",
        "Valor Total": "sum",
        "Valor Unitario": "mean"
    }).reset_index()
    agg["Tipo"] = tipo
    return agg

mensal_interno = indicadores_mensais(df_interno, "Interno")
mensal_externo = indicadores_mensais(df_externo, "Externo")

mensal_todos = pd.concat([mensal_interno, mensal_externo])
mensal_todos = mensal_todos.sort_values(by="AnoMes", ascending=False)

# ============================
# DASHBOARD STREAMLIT
# ============================
st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

st.title("📊 Dashboard de Abastecimento")

aba1, aba2, aba3 = st.tabs(["🚛 Consumo Médio", "📅 Indicadores Mensais", "💰 Preço Médio Interno"])

with aba1:
    st.subheader("Consumo Médio por Placa - Interno")
    st.dataframe(consumo_interno, use_container_width=True)

    st.subheader("Consumo Médio por Placa - Externo")
    st.dataframe(consumo_externo, use_container_width=True)

with aba2:
    st.subheader("Abastecimento Interno x Externo - Indicadores Mensais")
    st.dataframe(mensal_todos, use_container_width=True)

with aba3:
    st.metric(label="Preço Médio Interno (a partir de Jul)", value=f"R$ {preco_medio_interno:.2f}")
