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
    abas = pd.read_excel(arquivo, sheet_name=None)

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

        # --- FILTROS ---
        st.sidebar.header("Filtros")

        # Filtro de data - intervalo comum para interno e externo
        min_data = min(
            df_interno["data"].min() if "data" in df_interno.columns else pd.Timestamp.min,
            df_externo["data"].min() if "data" in df_externo.columns else pd.Timestamp.min,
        )
        max_data = max(
            df_interno["data"].max() if "data" in df_interno.columns else pd.Timestamp.max,
            df_externo["data"].max() if "data" in df_externo.columns else pd.Timestamp.max,
        )

        data_inicio = st.sidebar.date_input("Data início", min_data)
        data_fim = st.sidebar.date_input("Data fim", max_data)

        # Validação básica para intervalo de datas
        if data_inicio > data_fim:
            st.sidebar.error("Data início não pode ser maior que Data fim.")
        
        # Filtro por placa (se existir em ambas as tabelas)
        placas_interno = set(df_interno["placa"].dropna().unique()) if "placa" in df_interno.columns else set()
        placas_externo = set(df_externo["placa"].dropna().unique()) if "placa" in df_externo.columns else set()
        placas_comuns = sorted(list(placas_interno.intersection(placas_externo)))

        placa_selecionada = None
        if placas_comuns:
            placa_selecionada = st.sidebar.selectbox("Selecione a placa", options=["Todas"] + placas_comuns)
        
        # --- FILTRAGEM DOS DADOS ---
        def filtrar_df(df):
            df_filtrado = df.copy()
            if "data" in df_filtrado.columns:
                df_filtrado = df_filtrado[
                    (df_filtrado["data"] >= pd.to_datetime(data_inicio)) &
                    (df_filtrado["data"] <= pd.to_datetime(data_fim))
                ]
            if placa_selecionada and placa_selecionada != "Todas" and "placa" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["placa"] == placa_selecionada]
            return df_filtrado

        df_interno_filtro = filtrar_df(df_interno)
        df_externo_filtro = filtrar_df(df_externo)

        # --- KPIs dinâmicos ---
        total_litros_interno = df_interno_filtro["quantidade de litros"].sum()
        total_litros_externo = df_externo_filtro["quantidade de litros"].sum()

        total_valor_interno = df_interno_filtro["valor total"].sum()
        total_valor_externo = df_externo_filtro["valor total"].sum()

        tabs = st.tabs(["📈 Visão Geral", "🏭 Abastecimento Interno", "⛽ Abastecimento Externo"])

        with tabs[0]:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🚛 Total Litros Interno", f"{total_litros_interno:,.2f} L")
            col2.metric("⛽ Total Litros Externo", f"{total_litros_externo:,.2f} L")
            col3.metric("💰 Valor Interno", f"R$ {total_valor_interno:,.2f}")
            col4.metric("💵 Valor Externo", f"R$ {total_valor_externo:,.2f}")

            st.markdown("---")
            st.write(f"**Filtros aplicados:**")
            st.write(f"- Data: {data_inicio} até {data_fim}")
            if placa_selecionada and placa_selecionada != "Todas":
                st.write(f"- Placa: {placa_selecionada}")
            else:
                st.write(f"- Placa: Todas")

        with tabs[1]:
            with st.expander("📋 Tabela Interno (filtrada)"):
                st.dataframe(df_interno_filtro)

        with tabs[2]:
            with st.expander("📋 Tabela Externo (filtrada)"):
                st.dataframe(df_externo_filtro)

    else:
        st.error("Não foi possível encontrar as abas 'interno' e 'externo' na planilha.")
