import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata

# ==== Função para normalizar nomes de colunas ====
def normalizar_colunas(df):
    df.columns = [
        unicodedata.normalize("NFKD", str(col))  # Remove acentos
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .strip()
        .lower()
        .replace("  ", " ")  # Remove espaços duplos
        for col in df.columns
    ]
    return df

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

st.title("📊 BI de Abastecimento Interno e Externo")

# Upload único da planilha
file_abastecimento = st.sidebar.file_uploader("📂 Upload da Planilha de Abastecimento (com abas interno e externo)", type=["xlsx"])

if file_abastecimento:
    # Lendo todas as abas
    dfs = pd.read_excel(file_abastecimento, sheet_name=None)

    # Identifica abas interno e externo
    nome_interno = next((k for k in dfs.keys() if "interno" in k.lower()), list(dfs.keys())[0])
    nome_externo = next((k for k in dfs.keys() if "externo" in k.lower()), list(dfs.keys())[1])

    # Normaliza colunas
    df_interno = normalizar_colunas(dfs[nome_interno])
    df_externo = normalizar_colunas(dfs[nome_externo])

    # Converte datas se existir coluna "data"
    if "data" in df_interno.columns:
        df_interno["data"] = pd.to_datetime(df_interno["data"], errors="coerce")
    if "data" in df_externo.columns:
        df_externo["data"] = pd.to_datetime(df_externo["data"], errors="coerce")

    # Garante que existe coluna valor_total no interno
    if "valor total" not in df_interno.columns or df_interno["valor total"].isnull().all():
        if "valor unitario" in df_interno.columns and "quantidade de litro" in df_interno.columns:
            df_interno["valor total"] = df_interno["quantidade de litro"] * df_interno["valor unitario"].fillna(0)

    # ===== Criação das abas =====
    aba = st.tabs(["📌 Resumo Geral", "🚚 Consumo por Veículo", "💰 Preço Médio", "📈 Tendência"])

    # ===== ABA 1: RESUMO GERAL =====
    with aba[0]:
        st.subheader("📌 Resumo Geral")
        total_litros_interno = df_interno["quantidade de litro"].sum()
        total_litros_externo = df_externo["quantidade de litro"].sum()
        custo_total_interno = df_interno["valor total"].sum()
        custo_total_externo = df_externo["valor total"].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Litros Interno", f"{total_litros_interno:,.0f}")
        col2.metric("Litros Externo", f"{total_litros_externo:,.0f}")
        col3.metric("Custo Interno", f"R$ {custo_total_interno:,.2f}")
        col4.metric("Custo Externo", f"R$ {custo_total_externo:,.2f}")

    # ===== ABA 2: CONSUMO POR VEÍCULO =====
    with aba[1]:
        st.subheader("🚚 Ranking de Consumo por Veículo")
        ranking_interno = df_interno.groupby("placa").agg({
            "quantidade de litro": "sum",
            "valor total": "sum"
        }).reset_index().sort_values(by="quantidade de litro", ascending=False)

        ranking_externo = df_externo.groupby("placa").agg({
            "quantidade de litro": "sum",
            "valor total": "sum"
        }).reset_index().sort_values(by="quantidade de litro", ascending=False)

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
        preco_interno = (df_interno["valor total"].sum() / df_interno["quantidade de litro"].sum()) if df_interno["quantidade de litro"].sum() > 0 else 0
        preco_externo = (df_externo["valor total"].sum() / df_externo["quantidade de litro"].sum()) if df_externo["quantidade de litro"].sum() > 0 else 0

        df_preco = pd.DataFrame({
            "Tipo": ["Interno", "Externo"],
            "Preço Médio": [preco_interno, preco_externo]
        })

        fig_preco = px.bar(df_preco, x="Tipo", y="Preço Médio", text_auto=".2f", color="Tipo", title="Comparativo Preço Médio (R$/litro)")
        st.plotly_chart(fig_preco, use_container_width=True)

    # ===== ABA 4: TENDÊNCIA =====
    with aba[3]:
        st.subheader("📈 Evolução de Abastecimento")
        df_interno_g = df_interno.groupby("data").agg({"quantidade de litro": "sum"}).reset_index()
        df_interno_g["tipo"] = "Interno"
        df_externo_g = df_externo.groupby("data").agg({"quantidade de litro": "sum"}).reset_index()
        df_externo_g["tipo"] = "Externo"

        df_tendencia = pd.concat([df_interno_g, df_externo_g])

        fig_tendencia = px.line(df_tendencia, x="data", y="quantidade de litro", color="tipo", markers=True, title="Tendência de Abastecimento")
        st.plotly_chart(fig_tendencia, use_container_width=True)

else:
    st.info("📥 Envie a planilha única com abas 'interno' e 'externo' para gerar o dashboard.")
