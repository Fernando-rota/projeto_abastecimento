import streamlit as st
import pandas as pd
import unicodedata

# Função para normalizar colunas
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

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

st.title("📊 Dashboard de Abastecimento Interno x Externo")

# Upload da planilha
arquivo = st.file_uploader("📂 Envie a planilha de abastecimento (com abas 'interno' e 'externo')", type=["xlsx"])

if arquivo:
    # Lê todas as abas
    abas = pd.read_excel(arquivo, sheet_name=None)

    # Identifica abas pelo nome (ignora maiúsculas/minúsculas)
    nomes_abas = {nome.lower(): nome for nome in abas.keys()}
    nome_interno = next((n for n in nomes_abas if "interno" in n), None)
    nome_externo = next((n for n in nomes_abas if "externo" in n), None)

    if nome_interno and nome_externo:
        df_interno = normalizar_colunas(abas[nomes_abas[nome_interno]])
        df_externo = normalizar_colunas(abas[nomes_abas[nome_externo]])

        # Conversão de datas
        if "data" in df_interno.columns:
            df_interno["data"] = pd.to_datetime(df_interno["data"], errors="coerce")
        if "data" in df_externo.columns:
            df_externo["data"] = pd.to_datetime(df_externo["data"], errors="coerce")

        # KPIs
        total_litros_interno = df_interno["quantidade de litros"].sum()
        total_litros_externo = df_externo["quantidade de litros"].sum()

        total_valor_interno = df_interno["valor total"].sum()
        total_valor_externo = df_externo["valor total"].sum()

        tabs = st.tabs(["📈 Visão Geral", "🏭 Abastecimento Interno", "⛽ Abastecimento Externo"])

        with tabs[0]:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🚛 Total Litros Interno", f"{total_litros_interno:,.2f} L")
            col2.metric("⛽ Total Litros Externo", f"{total_litros_externo:,.2f} L")
            col3.metric("💰 Valor Interno", f"R$ {total_valor_interno:,.2f}")
            col4.metric("💵 Valor Externo", f"R$ {total_valor_externo:,.2f}")

        with tabs[1]:
            with st.expander("📋 Tabela Interno"):
                st.dataframe(df_interno)

        with tabs[2]:
            with st.expander("📋 Tabela Externo"):
                st.dataframe(df_externo)
    else:
        st.error("Não foi possível encontrar as abas 'interno' e 'externo' na planilha.")
