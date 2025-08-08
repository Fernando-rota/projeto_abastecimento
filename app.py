import streamlit as st
import pandas as pd
import unicodedata
import plotly.express as px

# Função para normalizar colunas e substituir espaços por underline
def normalizar_colunas(df):
    df.columns = [
        unicodedata.normalize("NFKD", str(col))
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .strip()
        .lower()
        .replace("  ", " ")
        .replace(" ", "_")  # espaço por underline
        for col in df.columns
    ]
    return df

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")
st.title("📊 Dashboard de Abastecimento Interno x Externo")

arquivo = st.file_uploader("📂 Envie a planilha de abastecimento (com abas 'interno' e 'externo')", type=["xlsx"])

def calcula_consumo_medio(df):
    if not {"placa", "km_atual", "quantidade_de_litros"}.issubset(df.columns):
        return pd.DataFrame(columns=["placa", "descricao_despesa", "consumo_medio_km_l"])

    if "data" in df.columns:
        df = df.sort_values(by=["placa", "data", "km_atual"])
    else:
        df = df.sort_values(by=["placa", "km_atual"])

    resultados = []

    for placa, grupo in df.groupby("placa"):
        if "descricao_despesa" in grupo.columns:
            for combustivel, subgrupo in grupo.groupby("descricao_despesa"):
                subgrupo = subgrupo.sort_values(by="km_atual")
                kms = subgrupo["km_atual"].values
                litros = subgrupo["quantidade_de_litros"].values

                km_rodados = kms[1:] - kms[:-1]
                litros_consumidos = litros[1:]

                mask = km_rodados > 0
                km_rodados = km_rodados[mask]
                litros_consumidos = litros_consumidos[mask]

                if len(km_rodados) == 0 or litros_consumidos.sum() == 0:
                    consumo_medio = float('nan')
                else:
                    consumo_medio = km_rodados.sum() / litros_consumidos.sum()

                resultados.append({
                    "placa": placa,
                    "descricao_despesa": combustivel,
                    "consumo_medio_km_l": consumo_medio
                })
        else:
            grupo = grupo.sort_values(by="km_atual")
            kms = grupo["km_atual"].values
            litros = grupo["quantidade_de_litros"].values

            km_rodados = kms[1:] - kms[:-1]
            litros_consumidos = litros[1:]

            mask = km_rodados > 0
            km_rodados = km_rodados[mask]
            litros_consumidos = litros_consumidos[mask]

            if len(km_rodados) == 0 or litros_consumidos.sum() == 0:
                consumo_medio = float('nan')
            else:
                consumo_medio = km_rodados.sum() / litros_consumidos.sum()

            resultados.append({
                "placa": placa,
                "descricao_despesa": "n/a",
                "consumo_medio_km_l": consumo_medio
            })

    return pd.DataFrame(resultados)

if arquivo:
    abas = pd.read_excel(arquivo, sheet_name=None)

    nomes_abas = {nome.lower(): nome for nome in abas.keys()}
    nome_interno = next((n for n in nomes_abas if "interno" in n), None)
    nome_externo = next((n for n in nomes_abas if "externo" in n), None)

    if nome_interno and nome_externo:
        df_interno = normalizar_colunas(abas[nomes_abas[nome_interno]])
        df_externo = normalizar_colunas(abas[nomes_abas[nome_externo]])

        st.write("Colunas Interno:", df_interno.columns.tolist())
        st.write("Colunas Externo:", df_externo.columns.tolist())

        if "data" in df_interno.columns:
            df_interno["data"] = pd.to_datetime(df_interno["data"], errors="coerce")
        if "data" in df_externo.columns:
            df_externo["data"] = pd.to_datetime(df_externo["data"], errors="coerce")

        for df in [df_interno, df_externo]:
            df["km_atual"] = pd.to_numeric(df["km_atual"], errors="coerce")
            df["quantidade_de_litros"] = pd.to_numeric(df["quantidade_de_litros"], errors="coerce")
            if "valor_total" in df.columns:
                df["valor_total"] = pd.to_numeric(df["valor_total"], errors="coerce")
            df.dropna(subset=["km_atual", "quantidade_de_litros"], inplace=True)

        for df in [df_interno, df_externo]:
            if "descricao_despesa" not in df.columns:
                df["descricao_despesa"] = "n/a"
            else:
                df["descricao_despesa"] = df["descricao_despesa"].fillna("n/a").astype(str).str.strip().str.lower()

        st.write("Valores únicos em descricao_despesa (interno):", df_interno["descricao_despesa"].unique())
        st.write("Valores únicos em descricao_despesa (externo):", df_externo["descricao_despesa"].unique())

        df_interno_sem_bomba = df_interno[df_interno["placa"] != "-"] if "placa" in df_interno.columns else df_interno.copy()

        st.sidebar.header("Filtros")

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

        placas_interno = set(df_interno_sem_bomba["placa"].dropna().unique()) if "placa" in df_interno.columns else set()
        placas_externo = set(df_externo["placa"].dropna().unique()) if "placa" in df_externo.columns else set()
        placas_comuns = sorted(list(placas_interno.intersection(placas_externo)))
        placa_selecionada = None
        if placas_comuns:
            placa_selecionada = st.sidebar.selectbox("Selecione a placa", options=["Todas"] + placas_comuns)

        combustiveis_interno = sorted(df_interno["descricao_despesa"].unique())
        combustiveis_externo = sorted(df_externo["descricao_despesa"].unique())
        combustiveis_comuns = sorted(set(combustiveis_interno) | set(combustiveis_externo))

        combustivel_selecionado = st.sidebar.selectbox(
            "Selecione o tipo de combustível",
            options=["Todos"] + combustiveis_comuns
        )

        def filtrar_df(df, excluir_bomba=False):
            df_filtrado = df.copy()
            if "data" in df_filtrado.columns:
                df_filtrado = df_filtrado[
                    (df_filtrado["data"] >= pd.to_datetime(data_inicio)) &
                    (df_filtrado["data"] <= pd.to_datetime(data_fim))
                ]
            if placa_selecionada and placa_selecionada != "Todas" and "placa" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["placa"] == placa_selecionada]
            if combustivel_selecionado and combustivel_selecionado != "Todos" and "descricao_despesa" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["descricao_despesa"] == combustivel_selecionado]
            if excluir_bomba and "placa" in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado["placa"] != "-"]
            return df_filtrado

        df_interno_filtro = filtrar_df(df_interno, excluir_bomba=True)
        df_externo_filtro = filtrar_df(df_externo)

        total_litros_interno = df_interno_filtro["quantidade_de_litros"].sum()
        total_litros_externo = df_externo_filtro["quantidade_de_litros"].sum()

        total_valor_interno = df_interno_filtro["valor_total"].sum() if "valor_total" in df_interno_filtro.columns else 0
        total_valor_externo = df_externo_filtro["valor_total"].sum() if "valor_total" in df_externo_filtro.columns else 0

        tabs = st.tabs(["📈 Visão Geral", "🏭 Abastecimento Interno", "⛽ Abastecimento Externo"])

        with tabs[0]:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🚛 Total Litros Interno", f"{total_litros_interno:,.2f} L")
            col2.metric("⛽ Total Litros Externo", f"{total_litros_externo:,.2f} L")
            col3.metric("💰 Valor Interno", f"R$ {total_valor_interno:,.2f}")
            col4.metric("💵 Valor Externo", f"R$ {total_valor_externo:,.2f}")

            if not df_interno_filtro.empty and "placa" in df_interno_filtro.columns:
                media_litros_interno = df_interno_filtro.groupby("placa")["quantidade_de_litros"].mean().reset_index()
                media_litros_interno.columns = ["placa", "média litros (interno)"]
            else:
                media_litros_interno = pd.DataFrame(columns=["placa", "média litros (interno)"])

            if not df_externo_filtro.empty and "placa" in df_externo_filtro.columns:
                media_litros_externo = df_externo_filtro.groupby("placa")["quantidade_de_litros"].mean().reset_index()
                media_litros_externo.columns = ["placa", "média litros (externo)"]
            else:
                media_litros_externo = pd.DataFrame(columns=["placa", "média litros (externo)"])

            media_veiculos = pd.merge(media_litros_interno, media_litros_externo, on="placa", how="outer").fillna(0)
            st.subheader("📊 Média de Litros por Veículo")
            st.dataframe(media_veiculos.style.format({"média litros (interno)": "{:.2f}", "média litros (externo)": "{:.2f}"}))

            consumo_interno = calcula_consumo_medio(df_interno_filtro)
            st.subheader("🚛 Consumo Médio por Veículo e Tipo de Combustível (Interno) - km/l")
            if consumo_interno.empty:
                st.write("Não há dados suficientes para calcular o consumo médio interno.")
            else:
                st.dataframe(consumo_interno.style.format({"consumo_medio_km_l": "{:.2f}"}))

            consumo_externo = calcula_consumo_medio(df_externo_filtro)
            st.subheader("⛽ Consumo Médio por Veículo e Tipo de Combustível (Externo) - km/l")
            if consumo_externo.empty:
                st.write("Não há dados suficientes para calcular o consumo médio externo.")
            else:
                st.dataframe(consumo_externo.style.format({"consumo_medio_km_l": "{:.2f}"}))

            df_interno_filtro["ano_mes"] = df_interno_filtro["data"].dt.to_period("M").astype(str)
            df_externo_filtro["ano_mes"] = df_externo_filtro["data"].dt.to_period("M").astype(str)

            interno_mes = df_interno_filtro.groupby("ano_mes").agg(
                litros_interno=("quantidade_de_litros", "sum"),
                valor_interno=("valor_total", "sum")
            ).reset_index()

            externo_mes = df_externo_filtro.groupby("ano_mes").agg(
                litros_externo=("quantidade_de_litros", "sum"),
                valor_externo=("valor_total", "sum")
            ).reset_index()

            mes_completo = pd.merge(interno_mes, externo_mes, on="ano_mes", how="outer").fillna(0)

            fig_litros = px.line(
                mes_completo, x="ano_mes",
                y=["litros_interno", "litros_externo"],
                title="Litros Abastecidos por Mês",
                labels={"value": "Litros", "ano_mes": "Mês"},
            )
            fig_valor = px.line(
                mes_completo, x="ano_mes",
                y=["valor_interno", "valor_externo"],
                title="Valor Abastecido por Mês (R$)",
                labels={"value": "Valor (R$)", "ano_mes": "Mês"},
            )

            st.plotly_chart(fig_litros, use_container_width=True)
            st.plotly_chart(fig_valor, use_container_width=True)

        with tabs[1]:
            st.subheader("🏭 Abastecimento Interno")

            if not df_interno_filtro.empty and "placa" in df_interno_filtro.columns:
                agg_placa = df_interno_filtro.groupby("placa")["quantidade_de_litros"].sum().reset_index()
                agg_placa = agg_placa.sort_values(by="quantidade_de_litros", ascending=False)
                fig_placa = px.bar(
                    agg_placa, x="placa", y="quantidade_de_litros",
                    title="Litros por Veículo (Interno)",
                    labels={"quantidade_de_litros": "Litros"}
                )
                st.plotly_chart(fig_placa, use_container_width=True)

            if "descricao_despesa" in df_interno_filtro.columns and not df_interno_filtro.empty:
                agg_comb = df_interno_filtro.groupby("descricao_despesa")["quantidade_de_litros"].sum().reset_index()
                agg_comb = agg_comb.sort_values(by="quantidade_de_litros", ascending=False)
                fig_comb = px.pie(
                    agg_comb, values="quantidade_de_litros", names="descricao_despesa",
                    title="Distribuição por Tipo de Combustível (Interno)"
                )
                st.plotly_chart(fig_comb, use_container_width=True)

            with st.expander("📋 Tabela Interno (filtrada)"):
                st.dataframe(df_interno_filtro)

        with tabs[2]:
            st.subheader("⛽ Abastecimento Externo")

            if not df_externo_filtro.empty and "placa" in df_externo_filtro.columns:
                agg_placa = df_externo_filtro.groupby("placa")["quantidade_de_litros"].sum().reset_index()
                agg_placa = agg_placa.sort_values(by="quantidade_de_litros", ascending=False)
                fig_placa = px.bar(
                    agg_placa, x="placa", y="quantidade_de_litros",
                    title="Litros por Veículo (Externo)",
                    labels={"quantidade_de_litros": "Litros"}
                )
                st.plotly_chart(fig_placa, use_container_width=True)

            if "descricao_despesa" in df_externo_filtro.columns and not df_externo_filtro.empty:
                agg_comb = df_externo_filtro.groupby("descricao_despesa")["quantidade_de_litros"].sum().reset_index()
                agg_comb = agg_comb.sort_values(by="quantidade_de_litros", ascending=False)
                fig_comb = px.pie(
                    agg_comb, values="quantidade_de_litros", names="descricao_despesa",
                    title="Distribuição por Tipo de Combustível (Externo)"
                )
                st.plotly_chart(fig_comb, use_container_width=True)

            df_externo_filtro["ano_mes"] = df_externo_filtro["data"].dt.to_period("M").astype(str)
            externo_mes = df_externo_filtro.groupby("ano_mes")["quantidade_de_litros"].sum().reset_index()
            fig_mes_externo = px.line(
                externo_mes, x="ano_mes", y="quantidade_de_litros",
                title="Litros Abastecidos Externos por Mês",
                labels={"ano_mes": "Mês", "quantidade_de_litros": "Litros"}
            )
            st.plotly_chart(fig_mes_externo, use_container_width=True)

            with st.expander("📋 Tabela Externo (filtrada)"):
                st.dataframe(df_externo_filtro)

    else:
        st.error("Não foi possível encontrar as abas 'interno' e 'externo' na planilha.")
