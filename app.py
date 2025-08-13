import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

def carregar_dados():
    st.sidebar.header("📂 Upload dos Arquivos")
    interno_file = st.sidebar.file_uploader("Abastecimento Interno", type=["xlsx"])
    externo_file = st.sidebar.file_uploader("Abastecimento Externo", type=["xlsx"])

    if interno_file and externo_file:
        interno = pd.read_excel(interno_file)
        externo = pd.read_excel(externo_file)
        return interno, externo
    else:
        return None, None

def tratar_dados(interno, externo):
    # Padronizar nomes de colunas
    interno.columns = interno.columns.str.strip().str.lower()
    externo.columns = externo.columns.str.strip().str.lower()

    # Filtrar abastecimentos internos (tipo = 'saída') e entradas separadas
    interno_saida = interno[interno["tipo"].str.lower() == "saída"].copy()
    interno_entrada = interno[interno["tipo"].str.lower() == "entrada"].copy()

    # Calcular preço médio do diesel interno a partir das entradas
    preco_medio_interno = None
    if not interno_entrada.empty:
        interno_entrada["valor total"] = interno_entrada["quantidade de litros"] * interno_entrada["valor unitario"]
        preco_medio_interno = interno_entrada["valor total"].sum() / interno_entrada["quantidade de litros"].sum()

    # Adicionar preço médio no abastecimento interno (saída)
    if preco_medio_interno:
        interno_saida["valor total"] = interno_saida["quantidade de litros"] * preco_medio_interno
        interno_saida["valor unitario"] = preco_medio_interno

    # Externo já contém valores pagos
    externo["valor total"] = externo["valor pago"]

    # Unificar datasets
    interno_saida["origem"] = "Interno"
    externo["origem"] = "Externo"
    externo.rename(columns={"consumo": "quantidade de litros"}, inplace=True)

    dados = pd.concat([
        interno_saida[["data", "placa", "quantidade de litros", "valor total", "valor unitario", "origem"]],
        externo[["data", "placa", "quantidade de litros", "valor total", "valor unitario", "origem"]]
    ], ignore_index=True)

    dados["data"] = pd.to_datetime(dados["data"], errors="coerce")
    dados["mes"] = dados["data"].dt.to_period("M").astype(str)
    return dados, preco_medio_interno

def filtros(dados):
    st.sidebar.header("🔍 Filtros")
    origem_sel = st.sidebar.multiselect("Origem", options=dados["origem"].unique(), default=dados["origem"].unique())
    placas_sel = st.sidebar.multiselect("Placas", options=sorted(dados["placa"].dropna().unique()), default=sorted(dados["placa"].dropna().unique()))
    periodo = st.sidebar.date_input("Período", [dados["data"].min(), dados["data"].max()])

    filtrado = dados[
        (dados["origem"].isin(origem_sel)) &
        (dados["placa"].isin(placas_sel)) &
        (dados["data"].between(periodo[0], periodo[1]))
    ]
    return filtrado

def indicadores(df):
    litros_totais = df["quantidade de litros"].sum()
    custo_total = df["valor total"].sum()
    preco_medio = custo_total / litros_totais if litros_totais > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("⛽ Litros Totais", f"{litros_totais:,.2f}")
    col2.metric("💰 Custo Total (R$)", f"{custo_total:,.2f}")
    col3.metric("📈 Preço Médio (R$/L)", f"{preco_medio:,.2f}")

def aba_resumo(df):
    st.subheader("📊 Resumo Geral")
    indicadores(df)
    graf = df.groupby("mes")[["quantidade de litros", "valor total"]].sum().reset_index()
    fig = px.bar(graf, x="mes", y="quantidade de litros", title="Litros Abastecidos por Mês")
    st.plotly_chart(fig, use_container_width=True)

def aba_autonomia(df):
    st.subheader("🚗 Ranking de Autonomia")
    # Aqui poderia ser calculada autonomia se tivermos km rodado
    autonomia_df = df.groupby("placa")["quantidade de litros"].sum().reset_index()
    autonomia_df["Autonomia (km/L)"] = 0  # Placeholder, pois depende de outra planilha
    autonomia_df = autonomia_df.sort_values(by="Autonomia (km/L)", ascending=False)
    st.dataframe(autonomia_df, hide_index=True)

def aba_custos(df):
    st.subheader("💰 Custos por Tipo de Combustível / Origem")
    graf = df.groupby(["mes", "origem"])["valor total"].sum().reset_index()
    fig = px.bar(graf, x="mes", y="valor total", color="origem", barmode="group", title="Custos por Origem")
    st.plotly_chart(fig, use_container_width=True)

def aba_tendencia(df):
    st.subheader("📈 Tendência Mensal")
    graf = df.groupby("mes")[["quantidade de litros", "valor total"]].sum().reset_index()
    fig1 = px.line(graf, x="mes", y="quantidade de litros", title="Evolução dos Litros")
    fig2 = px.line(graf, x="mes", y="valor total", title="Evolução do Custo")
    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)

def main():
    interno, externo = carregar_dados()
    if interno is not None and externo is not None:
        dados, preco_medio_interno = tratar_dados(interno, externo)
        filtrado = filtros(dados)

        aba = st.tabs(["📊 Resumo Geral", "🚗 Ranking de Autonomia", "💰 Custos por Tipo", "📈 Tendência Mensal"])
        with aba[0]:
            aba_resumo(filtrado)
        with aba[1]:
            aba_autonomia(filtrado)
        with aba[2]:
            aba_custos(filtrado)
        with aba[3]:
            aba_tendencia(filtrado)
    else:
        st.warning("Faça o upload das duas planilhas para começar.")

if __name__ == "__main__":
    main()
