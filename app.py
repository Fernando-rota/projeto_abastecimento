import streamlit as st
import pandas as pd
import unicodedata
import plotly.express as px

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

        # Data
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

        if data_inicio > data_fim:
            st.sidebar.error("Data início não pode ser maior que Data fim.")

        # Placa
        placas_interno = set(df_interno["placa"].dropna().unique()) if "placa" in df_interno.columns else set()
        placas_externo = set(df_externo["placa"].dropna().unique()) if "placa" in df_externo.columns else set()
        placas_comuns = sorted(list(placas_interno.intersection(placas_externo)))
        placa_selecionada = None
        if placas_comuns:
            placa_selecionada = st.sidebar.selectbox("Selecione a placa", options=["Todas"] + placas_comuns)

        # Tipo de combustível
        combustiveis_interno = set(df_interno["tipo de combustível"].dropna().unique()) if "tipo de combustível" in df_interno.columns else set()
        combustiveis_externo = set(df_externo["tipo de combustível"].dropna().unique()) if "tipo de combustível" in df_externo.columns else set()
        combustiveis_comuns = sorted(list(combustiveis_interno.union(combustiveis_externo)))
        combustivel_selecionado = None
        if combustiveis_comuns:
            combustivel_selecionado = st.sidebar.selectbox("Selecione o tipo de combustível", options=["Todos"] + combustiveis_comuns)

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
            if combustivel_selecionado and combustivel_selecionado != "Todos" and "tipo de combustível" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["tipo de combustível"] == combustivel_selecionado]
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
            st.write(f"- Placa: {placa_selecionada if placa_selecionada else 'Todas'}")
            st.write(f"- Combustível: {combustivel_selecionado if combustivel_selecionado else 'Todos'}")

            # Gráfico geral Litros por data (interno x externo)
            df_interno_agg = df_interno_filtro.groupby("data")["quantidade de litros"].sum().reset_index()
            df_externo_agg = df_externo_filtro.groupby("data")["quantidade de litros"].sum().reset_index()

            fig = px.line(title="Litros Abastecidos por Data")
            fig.add_scatter(x=df_interno_agg["data"], y=df_interno_agg["quantidade de litros"], mode="lines+markers", name="Interno")
            fig.add_scatter(x=df_externo_agg["data"], y=df_externo_agg["quantidade de litros"], mode="lines+markers", name="Externo")
            fig.update_layout(xaxis_title="Data", yaxis_title="Litros")
            st.plotly_chart(fig, use_container_width=True)

        with tabs[1]:
            st.subheader("Abastecimento Interno")

            # Gráfico Litros por Placa
            if "placa" in df_interno_filtro.columns:
                agg_placa = df_interno_filtro.groupby("placa")["quantidade de litros"].sum().reset_index()
                fig_placa = px.bar(agg_placa, x="placa", y="quantidade de litros", title="Litros por Veículo (Interno)", labels={"quantidade de litros": "Litros"})
                st.plotly_chart(fig_placa, use_container_width=True)

            # Gráfico Litros por Combustível
            if "tipo de combustível" in df_interno_filtro.columns:
                agg_comb = df_interno_filtro.groupby("tipo de combustível")["quantidade de litros"].sum().reset_index()
                fig_comb = px.pie(agg_comb, values="quantidade de litros", names="tipo de combustível", title="Distribuição por Tipo de Combustível (Interno)")
                st.plotly_chart(fig_comb, use_container_width=True)

            with st.expander("📋 Tabela Interno (filtrada)"):
                st.dataframe(df_interno_filtro)

        with tabs[2]:
            st.subheader("Abastecimento Externo")

            # Gráfico Litros por Placa
            if "placa" in df_externo_filtro.columns:
                agg_placa = df_externo_filtro.groupby("placa")["quantidade de litros"].sum().reset_index()
                fig_placa = px.bar(agg_placa, x="placa", y="quantidade de litros", title="Litros por Veículo (Externo)", labels={"quantidade de litros": "Litros"})
                st.plotly_chart(fig_placa, use_container_width=True)

            # Gráfico Litros por Combustível
            if "tipo de combustível" in df_externo_filtro.columns:
                agg_comb = df_externo_filtro.groupby("tipo de combustível")["quantidade de litros"].sum().reset_index()
                fig_comb = px.pie(agg_comb, values="quantidade de litros", names="tipo de combustível", title="Distribuição por Tipo de Combustível (Externo)")
                st.plotly_chart(fig_comb, use_container_width=True)

            with st.expander("📋 Tabela Externo (filtrada)"):
                st.dataframe(df_externo_filtro)

    else:
        st.error("Não foi possível encontrar as abas 'interno' e 'externo' na planilha.")
