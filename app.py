import streamlit as st
import pandas as pd
import unicodedata
import plotly.express as px
import re

# Função para normalizar colunas: remove acentos, deixa minúsculas, troca espaços por underline
def normalizar_colunas(df):
    df.columns = [
        unicodedata.normalize("NFKD", str(col))
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .strip()
        .lower()
        .replace(" ", "_")  # troca espaços por underline
        for col in df.columns
    ]
    return df

def limpar_valor_monetario(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    valor_str = str(valor)
    valor_limpo = re.sub(r"[R$\s\.]", "", valor_str)
    valor_limpo = valor_limpo.replace(",", ".")
    try:
        return float(valor_limpo)
    except:
        return 0.0

def calcula_consumo_medio(df):
    df = df.copy()

    if "placa" in df.columns:
        df["placa"] = df["placa"].astype(str).str.upper().str.strip()
        df = df[~df["placa"].isin(["-", "N/A", "", "NA"])]

    df["km_atual"] = pd.to_numeric(df["km_atual"], errors="coerce")
    df["quantidade_de_litros"] = pd.to_numeric(df["quantidade_de_litros"], errors="coerce")
    df = df.dropna(subset=["km_atual", "quantidade_de_litros"])

    if "tipo_combustivel" not in df.columns:
        df["tipo_combustivel"] = "N/A"
    else:
        df["tipo_combustivel"] = df["tipo_combustivel"].fillna("N/A").astype(str).str.upper().str.strip()

    resultados = []

    for (placa, combustivel), grupo in df.groupby(["placa", "tipo_combustivel"]):
        grupo = grupo.sort_values(by="km_atual")
        kms = grupo["km_atual"].values
        litros = grupo["quantidade_de_litros"].values

        if len(kms) < 2:
            consumo_medio = float("nan")
        else:
            km_rodados = kms[1:] - kms[:-1]
            litros_usados = litros[1:]

            mask_valid = (km_rodados > 0) & (litros_usados > 0)
            km_rodados = km_rodados[mask_valid]
            litros_usados = litros_usados[mask_valid]

            if len(km_rodados) == 0:
                consumo_medio = float("nan")
            else:
                consumo_medio = km_rodados.sum() / litros_usados.sum()

        resultados.append({
            "placa": placa,
            "tipo_combustivel": combustivel,
            "consumo_medio_km_l": consumo_medio
        })

    df_consumo = pd.DataFrame(resultados)
    df_consumo = df_consumo.dropna(subset=["consumo_medio_km_l"])
    df_consumo = df_consumo.sort_values(by="consumo_medio_km_l", ascending=False).reset_index(drop=True)
    return df_consumo

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")
st.title("📊 Dashboard de Abastecimento Interno x Externo")

arquivo = st.file_uploader("📂 Envie a planilha de abastecimento (com abas 'interno' e 'externo')", type=["xlsx"])

if arquivo:
    abas = pd.read_excel(arquivo, sheet_name=None)

    nomes_abas = {nome.lower(): nome for nome in abas.keys()}
    nome_interno = next((n for n in nomes_abas if "interno" in n), None)
    nome_externo = next((n for n in nomes_abas if "externo" in n), None)

    if nome_interno and nome_externo:
        df_interno = normalizar_colunas(abas[nomes_abas[nome_interno]])
        df_externo = normalizar_colunas(abas[nomes_abas[nome_externo]])

        # Converter Data
        if "data" in df_interno.columns:
            df_interno["data"] = pd.to_datetime(df_interno["data"], errors="coerce", dayfirst=True)
        if "data" in df_externo.columns:
            df_externo["data"] = pd.to_datetime(df_externo["data"], errors="coerce", dayfirst=True)

        # Limpar valores monetários no valor total e valor unitario
        for df in [df_interno, df_externo]:
            if "valor_total" in df.columns:
                df["valor_total"] = df["valor_total"].apply(limpar_valor_monetario)
            else:
                df["valor_total"] = 0.0
            if "valor_unitario" in df.columns:
                df["valor_unitario"] = df["valor_unitario"].apply(limpar_valor_monetario)
            else:
                df["valor_unitario"] = 0.0

        # Padronizar placa e tipo combustivel
        for df in [df_interno, df_externo]:
            df["placa"] = df["placa"].astype(str).str.upper().str.strip()
            df["tipo_combustivel"] = df["tipo_combustivel"].fillna("N/A").astype(str).str.upper().str.strip()

            df["quantidade_de_litros"] = pd.to_numeric(df["quantidade_de_litros"], errors="coerce")
            df["km_atual"] = pd.to_numeric(df["km_atual"], errors="coerce")

            # Remove linhas inválidas
            df.dropna(subset=["placa", "quantidade_de_litros", "km_atual"], inplace=True)

        # Remove placa '-' do interno
        df_interno = df_interno[df_interno["placa"] != "-"]

        st.sidebar.header("Filtros")

        data_min = min(df_interno["data"].min(), df_externo["data"].min())
        data_max = max(df_interno["data"].max(), df_externo["data"].max())

        data_inicio = st.sidebar.date_input("Data Início", data_min)
        data_fim = st.sidebar.date_input("Data Fim", data_max)

        if data_inicio > data_fim:
            st.sidebar.error("Data Início não pode ser maior que Data Fim")

        placas = sorted(set(df_interno["placa"]).union(set(df_externo["placa"])))
        placa_selecionada = st.sidebar.selectbox("Selecione a Placa", ["Todas"] + placas)

        combustiveis = sorted(set(df_interno["tipo_combustivel"]).union(set(df_externo["tipo_combustivel"])))
        combustivel_selecionado = st.sidebar.selectbox("Selecione o Tipo de Combustível", ["Todos"] + combustiveis)

        def filtrar(df):
            dff = df.copy()
            dff = dff[(dff["data"] >= pd.to_datetime(data_inicio)) & (dff["data"] <= pd.to_datetime(data_fim))]
            if placa_selecionada != "Todas":
                dff = dff[dff["placa"] == placa_selecionada]
            if combustivel_selecionado != "Todos":
                dff = dff[dff["tipo_combustivel"] == combustivel_selecionado]
            return dff

        df_interno_f = filtrar(df_interno)
        df_externo_f = filtrar(df_externo)

        total_litros_interno = df_interno_f["quantidade_de_litros"].sum()
        total_litros_externo = df_externo_f["quantidade_de_litros"].sum()
        total_valor_interno = df_interno_f["valor_total"].sum()
        total_valor_externo = df_externo_f["valor_total"].sum()

        tabs = st.tabs(["📈 Visão Geral", "🏭 Abastecimento Interno", "⛽ Abastecimento Externo"])

        with tabs[0]:
            st.subheader("Indicadores Gerais")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🚛 Litros Interno", f"{total_litros_interno:,.2f} L")
            col2.metric("⛽ Litros Externo", f"{total_litros_externo:,.2f} L")
            col3.metric("💰 Valor Interno", f"R$ {total_valor_interno:,.2f}")
            col4.metric("💵 Valor Externo", f"R$ {total_valor_externo:,.2f}")

            consumo_interno = calcula_consumo_medio(df_interno_f)
            consumo_externo = calcula_consumo_medio(df_externo_f)

            st.subheader("Consumo Médio por Veículo e Combustível (Interno) [km/l]")
            if consumo_interno.empty:
                st.write("Sem dados suficientes para cálculo.")
            else:
                st.dataframe(consumo_interno.style.format({"consumo_medio_km_l": "{:.2f}"}))

            st.subheader("Consumo Médio por Veículo e Combustível (Externo) [km/l]")
            if consumo_externo.empty:
                st.write("Sem dados suficientes para cálculo.")
            else:
                st.dataframe(consumo_externo.style.format({"consumo_medio_km_l": "{:.2f}"}))

            # Consumo mês a mês
            df_interno_f["ano_mes"] = df_interno_f["data"].dt.to_period("M").astype(str)
            df_externo_f["ano_mes"] = df_externo_f["data"].dt.to_period("M").astype(str)

            interno_mes = df_interno_f.groupby("ano_mes").agg(
                litros=("quantidade_de_litros", "sum"),
                valor=("valor_total", "sum")
            ).reset_index()

            externo_mes = df_externo_f.groupby("ano_mes").agg(
                litros=("quantidade_de_litros", "sum"),
                valor=("valor_total", "sum")
            ).reset_index()

            df_mes = pd.merge(interno_mes, externo_mes, on="ano_mes", how="outer", suffixes=("_interno", "_externo")).fillna(0)

            fig_litros = px.line(df_mes, x="ano_mes", y=["litros_interno", "litros_externo"],
                                 labels={"value": "Litros", "ano_mes": "Mês"},
                                 title="Litros Abastecidos Interno x Externo por Mês")
            fig_valor = px.line(df_mes, x="ano_mes", y=["valor_interno", "valor_externo"],
                                labels={"value": "Valor (R$)", "ano_mes": "Mês"},
                                title="Valor Abastecido Interno x Externo por Mês (R$)")

            st.plotly_chart(fig_litros, use_container_width=True)
            st.plotly_chart(fig_valor, use_container_width=True)

        with tabs[1]:
            st.subheader("🏭 Abastecimento Interno")
            if not df_interno_f.empty:
                agg_placa = df_interno_f.groupby("placa")["quantidade_de_litros"].sum().reset_index().sort_values(by="quantidade_de_litros", ascending=False)
                fig_placa = px.bar(agg_placa, x="placa", y="quantidade_de_litros",
                                  title="Litros por Veículo (Interno)", labels={"quantidade_de_litros": "Litros"})
                st.plotly_chart(fig_placa, use_container_width=True)

                agg_comb = df_interno_f.groupby("tipo_combustivel")["quantidade_de_litros"].sum().reset_index().sort_values(by="quantidade_de_litros", ascending=False)
                fig_comb = px.pie(agg_comb, values="quantidade_de_litros", names="tipo_combustivel",
                                 title="Distribuição por Tipo de Combustível (Interno)")
                st.plotly_chart(fig_comb, use_container_width=True)

            with st.expander("Tabela Interno (filtrada)"):
                st.dataframe(df_interno_f)

        with tabs[2]:
            st.subheader("⛽ Abastecimento Externo")
            if not df_externo_f.empty:
                agg_placa = df_externo_f.groupby("placa")["quantidade_de_litros"].sum().reset_index().sort_values(by="quantidade_de_litros", ascending=False)
                fig_placa = px.bar(agg_placa, x="placa", y="quantidade_de_litros",
                                  title="Litros por Veículo (Externo)", labels={"quantidade_de_litros": "Litros"})
                st.plotly_chart(fig_placa, use_container_width=True)

                agg_comb = df_externo_f.groupby("tipo_combustivel")["quantidade_de_litros"].sum().reset_index().sort_values(by="quantidade_de_litros", ascending=False)
                fig_comb = px.pie(agg_comb, values="quantidade_de_litros", names="tipo_combustivel",
                                 title="Distribuição por Tipo de Combustível (Externo)")
                st.plotly_chart(fig_comb, use_container_width=True)

            externo_mes = df_externo_f.groupby("ano_mes")["quantidade_de_litros"].sum().reset_index()
            fig_mes_externo = px.line(externo_mes, x="ano_mes", y="quantidade_de_litros",
                                     labels={"ano_mes": "Mês", "quantidade_de_litros": "Litros"},
                                     title="Litros Abastecidos Externos por Mês")
            st.plotly_chart(fig_mes_externo, use_container_width=True)

            with st.expander("Tabela Externo (filtrada)"):
                st.dataframe(df_externo_f)

    else:
        st.error("Não foi possível encontrar as abas 'interno' e 'externo' na planilha.")
