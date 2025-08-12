import streamlit as st
import pandas as pd
import plotly.express as px

# === Leitura das abas da planilha ===
arquivo = "abastecimento.xlsx"
df_interno = pd.read_excel(arquivo, sheet_name="Abastecimento Interno")
df_externo = pd.read_excel(arquivo, sheet_name="Abastecimento Externo")

# === Tratamento de dados ===
df_interno["Data"] = pd.to_datetime(df_interno["Data"], errors="coerce")
df_externo["Data"] = pd.to_datetime(df_externo["Data"], errors="coerce")

# Remove placas inválidas
placas_invalidas = ["-", "correção"]
df_interno = df_interno[~df_interno["Placa"].isin(placas_invalidas)]
df_externo = df_externo[~df_externo["Placa"].isin(placas_invalidas)]

# Remove linhas sem data
df_interno = df_interno.dropna(subset=["Data"])
df_externo = df_externo.dropna(subset=["Data"])

# Converte valores para numérico
df_interno["Quantidade de litros"] = pd.to_numeric(df_interno["Quantidade de litros"], errors="coerce")
df_interno["Valor Unitario"] = pd.to_numeric(df_interno["Valor Unitario"], errors="coerce")

df_externo["Quantidade de litros"] = pd.to_numeric(df_externo["Quantidade de litros"], errors="coerce")
df_externo["Valor Unitario"] = (
    df_externo["Valor Unitario"].astype(str)
    .str.replace("R$", "", regex=False)
    .str.replace(",", ".", regex=False)
)
df_externo["Valor Unitario"] = pd.to_numeric(df_externo["Valor Unitario"], errors="coerce")

# === Cálculo do consumo médio por placa ===
def consumo_medio(df1, df2):
    df = pd.concat([df1[["Placa", "KM Atual"]], df2[["Placa", "KM Atual"]]])
    resultado = []
    for placa, grupo in df.groupby("Placa"):
        km_max = grupo["KM Atual"].max()
        km_min = grupo["KM Atual"].min()
        km_rodado = km_max - km_min
        resultado.append({"Placa": placa, "KM Rodado": km_rodado})
    return pd.DataFrame(resultado).sort_values(by="KM Rodado", ascending=False)

df_consumo = consumo_medio(df_interno, df_externo)

# === Cálculo do valor médio ponderado (a partir de julho) ===
def preco_medio_ponderado(df):
    df_filtrado = df[df["Data"].dt.month >= 7]
    return df_filtrado.groupby(df_filtrado["Data"].dt.to_period("M")).apply(
        lambda x: pd.Series({
            "Litros": x["Quantidade de litros"].sum(),
            "Preco Medio (R$/L)": (x["Valor Unitario"] * x["Quantidade de litros"]).sum() / x["Quantidade de litros"].sum()
        })
    ).reset_index()

preco_interno = preco_medio_ponderado(df_interno)
preco_externo = preco_medio_ponderado(df_externo)

# === Dashboard Streamlit ===
st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

st.title("📊 Dashboard de Abastecimento")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Consumo Médio por Placa (KM Rodado)")
    st.dataframe(df_consumo)

with col2:
    st.subheader("Preço Médio Ponderado - Interno (a partir de Julho)")
    st.dataframe(preco_interno.sort_values(by="Preco Medio (R$/L)", ascending=False))

    st.subheader("Preço Médio Ponderado - Externo (a partir de Julho)")
    st.dataframe(preco_externo.sort_values(by="Preco Medio (R$/L)", ascending=False))

# === Gráfico de preços médios ===
fig = px.line(
    pd.concat([
        preco_interno.assign(Tipo="Interno"),
        preco_externo.assign(Tipo="Externo")
    ]),
    x="Data", y="Preco Medio (R$/L)", color="Tipo", markers=True,
    title="Preço Médio Ponderado do Combustível (Mensal)"
)
st.plotly_chart(fig, use_container_width=True)
