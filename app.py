import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

st.title("📊 BI de Abastecimento Interno e Externo")

# Upload dos arquivos
st.sidebar.header("📂 Upload das Planilhas")
file_interno = st.sidebar.file_uploader("Abastecimento Interno (.xlsx)", type=["xlsx"])
file_externo = st.sidebar.file_uploader("Abastecimento Externo (.xlsx)", type=["xlsx"])

if file_interno and file_externo:
    # Leitura dos arquivos
    df_interno = pd.read_excel(file_interno)
    df_externo = pd.read_excel(file_externo)

    # Normalização dos nomes de colunas
    df_interno.columns = df_interno.columns.str.strip()
    df_externo.columns = df_externo.columns.str.strip()

    # Ajustes de tipos
    df_interno["Data"] = pd.to_datetime(df_interno["Data"], errors="coerce")
    df_externo["Data"] = pd.to_datetime(df_externo["Data"], errors="coerce")

    # Calcular valor total interno (caso não exista)
    if "Valor Total" not in df_interno.columns or df_interno["Valor Total"].isnull().all():
        if "Valor Unitario" in df_interno.columns:
            df_interno["Valor Total"] = df_interno["Quantidade de litro"] * df_interno["Valor Unitario"].fillna(0)

    # ===== ABA 1: RESUMO GERAL =====
    aba = st.tabs(["📌 Resumo Geral", "🚚 Consumo por Veículo", "💰 Preço Médio", "📈 Tendência"])

    with aba[0]:
        st.subheader("📌 Resumo Geral")
        total_litros_interno = df_interno["Quantidade de litro"].sum()
        total_litros_externo = df_externo["Quantidade de litro"].sum()
        custo_total_interno = df_interno["Valor Total"].sum()
        custo_total_externo = df_externo["Valor Total"].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Litros Interno", f"{total_litros_interno:,.0f}")
        col2.metric("Litros Externo", f"{total_litros_externo:,.0f}")
        col3.metric("Custo Interno", f"R$ {custo_total_interno:,.2f}")
        col4.metric("Custo Externo", f"R$ {custo_total_externo:,.2f}")

    # ===== ABA 2: CONSUMO POR VEÍCULO =====
    with aba[1]:
        st.subheader("🚚 Ranking de Consumo por Veículo")
        ranking_interno = df_interno.groupby("Placa").agg({
            "Quantidade de litro": "sum",
            "Valor Total": "sum"
        }).reset_index().sort_values(by="Quantidade de litro", ascending=False)

        ranking_externo = df_externo.groupby("Placa").agg({
            "Quantidade de litro": "sum",
            "Valor Total": "sum"
        }).reset_index().sort_values(by="Quantidade de litro", ascending=False)

        col1, col2 = st.columns(2)
        with col1:
            st.write("🔹 Interno")
            st.dataframe(ranking_interno)
        with col2:
            st.write("🔹 Externo")
            st.dataframe(ranking_externo)

    # ===== ABA 3: PREÇO MÉDIO =====
    with aba[2]:
        st.subheader("💰 Preço Médio por Litro")
        preco_interno = (df_interno["Valor Total"].sum() / df_interno["Quantidade de litro"].sum()) if df_interno["Quantidade de litro"].sum() > 0 else 0
        preco_externo = (df_externo["Valor Total"].sum() / df_externo["Quantidade de litro"].sum()) if df_externo["Quantidade de litro"].sum() > 0 else 0

        df_preco = pd.DataFrame({
            "Tipo": ["Interno", "Externo"],
            "Preço Médio": [preco_interno, preco_externo]
        })

        fig_preco = px.bar(df_preco, x="Tipo", y="Preço Médio", text_auto=".2f", color="Tipo", title="Comparativo Preço Médio (R$/litro)")
        st.plotly_chart(fig_preco, use_container_width=True)

    # ===== ABA 4: TENDÊNCIA =====
    with aba[3]:
        st.subheader("📈 Evolução de Abastecimento")
        df_interno_g = df_interno.groupby("Data").agg({"Quantidade de litro": "sum"}).reset_index()
        df_interno_g["Tipo"] = "Interno"
        df_externo_g = df_externo.groupby("Data").agg({"Quantidade de litro": "sum"}).reset_index()
        df_externo_g["Tipo"] = "Externo"

        df_tendencia = pd.concat([df_interno_g, df_externo_g])

        fig_tendencia = px.line(df_tendencia, x="Data", y="Quantidade de litro", color="Tipo", markers=True, title="Tendência de Abastecimento")
        st.plotly_chart(fig_tendencia, use_container_width=True)

else:
    st.info("Por favor, envie as planilhas de abastecimento interno e externo para gerar o dashboard.")
