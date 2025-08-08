import streamlit as st
import pandas as pd
import unicodedata
import plotly.express as px

# ========================
# Função para padronizar nomes de colunas
# ========================
def normalizar_colunas(df):
    df.columns = [
        unicodedata.normalize("NFKD", str(col))
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .strip()
        .lower()
        .replace("  ", " ")
        for col in df.columns
    ]
    return df

# ========================
# Título do Dashboard
# ========================
st.set_page_config(page_title="BI Abastecimento Interno x Externo", layout="wide")
st.title("⛽ BI de Abastecimento - Interno x Externo")

# ========================
# Upload da planilha
# ========================
arquivo = st.file_uploader("📂 Envie a planilha com abas 'interno' e 'externo'", type=["xlsx"])

if arquivo is not None:
    # Lendo todas as abas
    abas = pd.read_excel(arquivo, sheet_name=None)

    # Normalizando nomes das abas para buscar
    abas_normalizadas = {unicodedata.normalize("NFKD", str(k)).encode("ASCII", "ignore").decode("utf-8").strip().lower(): v for k, v in abas.items()}

    # Pegando as abas pelo nome
    df_interno = normalizar_colunas(abas_normalizadas.get("interno", pd.DataFrame()))
    df_externo = normalizar_colunas(abas_normalizadas.get("externo", pd.DataFrame()))

    if df_interno.empty or df_externo.empty:
        st.error("⚠️ Não foi possível encontrar abas chamadas 'interno' e 'externo'. Verifique o nome exato das abas na planilha.")
    else:
        # ========================
        # KPIs principais
        # ========================
        total_litros_interno = df_interno["quantidade de litro"].sum()
        total_litros_externo = df_externo["quantidade de litro"].sum()

        col1, col2 = st.columns(2)
        col1.metric("🚛 Litros Abastecimento Interno", f"{total_litros_interno:,.0f} L")
        col2.metric("⛽ Litros Abastecimento Externo", f"{total_litros_externo:,.0f} L")

        # ========================
        # Abas do BI
        # ========================
        tab1, tab2, tab3 = st.tabs(["📊 Resumo", "📅 Tendência", "🚗 Ranking por Veículo"])

        with tab1:
            st.subheader("Resumo Comparativo")
            resumo_df = pd.DataFrame({
                "Tipo": ["Interno", "Externo"],
                "Litros": [total_litros_interno, total_litros_externo]
            })
            fig = px.bar(resumo_df, x="Tipo", y="Litros", color="Tipo", text="Litros", title="Litros Abastecidos - Comparativo")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("Tendência Mensal")
            if "data" in df_interno.columns:
                df_interno["mes"] = pd.to_datetime(df_interno["data"]).dt.to_period("M").astype(str)
            if "data" in df_externo.columns:
                df_externo["mes"] = pd.to_datetime(df_externo["data"]).dt.to_period("M").astype(str)

            litros_mes_interno = df_interno.groupby("mes")["quantidade de litro"].sum().reset_index()
            litros_mes_externo = df_externo.groupby("mes")["quantidade de litro"].sum().reset_index()

            litros_mes_interno["Tipo"] = "Interno"
            litros_mes_externo["Tipo"] = "Externo"
            tendencia_df = pd.concat([litros_mes_interno, litros_mes_externo])

            fig_tend = px.line(tendencia_df, x="mes", y="quantidade de litro", color="Tipo", markers=True,
                               title="Evolução Mensal dos Litros Abastecidos")
            st.plotly_chart(fig_tend, use_container_width=True)

        with tab3:
            st.subheader("Ranking de Veículos - Litros Abastecidos")
            if "placa" in df_interno.columns:
                ranking_interno = df_interno.groupby("placa")["quantidade de litro"].sum().reset_index()
                ranking_interno["Tipo"] = "Interno"
            else:
                ranking_interno = pd.DataFrame()

            if "placa" in df_externo.columns:
                ranking_externo = df_externo.groupby("placa")["quantidade de litro"].sum().reset_index()
                ranking_externo["Tipo"] = "Externo"
            else:
                ranking_externo = pd.DataFrame()

            ranking_df = pd.concat([ranking_interno, ranking_externo])
            fig_rank = px.bar(ranking_df, x="placa", y="quantidade de litro", color="Tipo", title="Litros Abastecidos por Veículo")
            st.plotly_chart(fig_rank, use_container_width=True)

else:
    st.info("📥 Envie a planilha para visualizar o BI.")
