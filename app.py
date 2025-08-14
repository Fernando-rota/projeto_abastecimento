import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

# ===== UPLOAD DE PLANILHAS =====
st.title("📊 Dashboard de Abastecimento - Interno & Externo")

file = st.file_uploader("Carregue o arquivo Excel com as abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=["xlsx"])

if file:
    # Leitura dos dados
    df_interno = pd.read_excel(file, sheet_name="Abastecimento Interno")
    df_externo = pd.read_excel(file, sheet_name="Abastecimento Externo")

    # Padronização das colunas (interno)
    df_interno.columns = df_interno.columns.str.strip().str.lower()
    df_externo.columns = df_externo.columns.str.strip().str.lower()

    # Converte colunas de data
    df_interno["data"] = pd.to_datetime(df_interno["data"], errors="coerce")
    df_externo["data"] = pd.to_datetime(df_externo["data"], errors="coerce")

    # Filtro de datas
    min_date = min(df_interno["data"].min(), df_externo["data"].min())
    max_date = max(df_interno["data"].max(), df_externo["data"].max())
    start_date, end_date = st.date_input("Selecione o período", [min_date, max_date])

    # Aplica filtro de período
    df_interno = df_interno[(df_interno["data"] >= pd.to_datetime(start_date)) & (df_interno["data"] <= pd.to_datetime(end_date))]
    df_externo = df_externo[(df_externo["data"] >= pd.to_datetime(start_date)) & (df_externo["data"] <= pd.to_datetime(end_date))]

    # Filtro por tipo de combustível
    combustiveis = sorted(set(df_interno["descrição despesa"].dropna().unique()) | set(df_externo["descrição despesa"].dropna().unique()))
    combustivel_sel = st.multiselect("Selecione o combustível", combustiveis, default=combustiveis)

    df_interno = df_interno[df_interno["descrição despesa"].isin(combustivel_sel)]
    df_externo = df_externo[df_externo["descrição despesa"].isin(combustivel_sel)]

    # ===== Cálculos =====
    # Valor médio interno (apenas entradas com valor unitário válido)
    df_interno_valido = df_interno[(df_interno["tipo"].str.lower() == "entrada") & (pd.to_numeric(df_interno["valor unitario"], errors="coerce") > 0)]
    valor_medio_interno = df_interno_valido["valor unitario"].mean()

    # Valor médio externo (apenas com valor unitário válido)
    valor_medio_externo = pd.to_numeric(df_externo["valor unitario"], errors="coerce").dropna().mean()

    # ===== Layout KPIs =====
    col1, col2 = st.columns(2)
    col1.metric("💰 Preço Médio Interno (R$/L)", f"{valor_medio_interno:.2f}" if not pd.isna(valor_medio_interno) else "N/A")
    col2.metric("⛽ Preço Médio Externo (R$/L)", f"{valor_medio_externo:.2f}" if not pd.isna(valor_medio_externo) else "N/A")

    # ===== Gráfico de Consumo por Tipo de Combustível =====
    consumo_combustivel = pd.concat([
        df_interno.groupby("descrição despesa")["quantidade de litros"].sum(),
        df_externo.groupby("descrição despesa")["quantidade de litros"].sum()
    ], axis=1, keys=["Interno", "Externo"]).fillna(0).reset_index()

    fig = px.bar(consumo_combustivel, x="descrição despesa", y=["Interno", "Externo"],
                 barmode="group", title="Consumo por Tipo de Combustível",
                 labels={"value": "Litros", "descrição despesa": "Tipo de Combustível"})
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Por favor, carregue a planilha para visualizar o dashboard.")
