import streamlit as st
import pandas as pd
import unicodedata
import plotly.express as px
import re

# -----------------------------
# FUNÇÕES AUXILIARES
# -----------------------------
def normalizar_colunas(df):
    df.columns = [
        unicodedata.normalize("NFKD", str(col))
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .strip()
        .lower()
        .replace(" ", "_")
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
    df["placa"] = df["placa"].astype(str).str.upper().str.strip()
    df = df[~df["placa"].isin(["-", "N/A", "", "NA"])]
    df["km_atual"] = pd.to_numeric(df["km_atual"], errors="coerce")
    df["quantidade_de_litros"] = pd.to_numeric(df["quantidade_de_litros"], errors="coerce")
    df = df.dropna(subset=["km_atual", "quantidade_de_litros"])
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

def calcula_consumo_medio_combinado(df_interno, df_externo):
    df_comb = pd.concat([df_interno, df_externo], ignore_index=True)
    return calcula_consumo_medio(df_comb)

# -----------------------------
# CONFIGURAÇÃO DO DASHBOARD
# -----------------------------
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

        # Datas
        if "data" in df_interno.columns:
            df_interno["data"] = pd.to_datetime(df_interno["data"], errors="coerce", dayfirst=True)
        if "data" in df_externo.columns:
            df_externo["data"] = pd.to_datetime(df_externo["data"], errors="coerce", dayfirst=True)

        # Limpar valores monetários e padronizar
        for df in [df_interno, df_externo]:
            df["valor_total"] = df.get("valor_total", 0).apply(limpar_valor_monetario) if "valor_total" in df.columns else 0
            df["valor_unitario"] = df.get("valor_unitario", 0).apply(limpar_valor_monetario) if "valor_unitario" in df.columns else 0
            df["placa"] = df["placa"].astype(str).str.upper().str.strip()
            df["tipo_combustivel"] = df["tipo_combustivel"].fillna("N/A").astype(str).str.upper().str.strip()
            df["quantidade_de_litros"] = pd.to_numeric(df["quantidade_de_litros"], errors="coerce")
            df["km_atual"] = pd.to_numeric(df["km_atual"], errors="coerce")
            df.dropna(subset=["placa", "quantidade_de_litros", "km_atual"], inplace=True)

        # Remove entrada de tanque do interno
        df_interno = df_interno[df_interno["placa"] != "-"]

        # -----------------------------
        # FILTROS GLOBAIS
        # -----------------------------
        st.sidebar.header("Filtros")
        data_min = min(df_interno["data"].min(), df_externo["data"].min())
        data_max = max(df_interno["data"].max(), df_externo["data"].max())
        data_inicio = st.sidebar.date_input("Data Início", data_min)
        data_fim = st.sidebar.date_input("Data Fim", data_max)

        placas = sorted(set(df_interno["placa"]).union(set(df_externo["placa"])))
        placas = [p for p in placas if p not in ("-", "N/A", "")]
        placa_selecionada = st.sidebar.selectbox("Selecione a Placa", ["Todas"] + placas)

        combustiveis = sorted(set(df_interno["tipo_combustivel"]).union(set(df_externo["tipo_combustivel"])))
        combustiveis = [c for c in combustiveis if c not in ("-", "N/A", "")]
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

        # Totais
        total_litros_interno = df_interno_f["quantidade_de_litros"].sum()
        total_litros_externo = df_externo_f["quantidade_de_litros"].sum()
        total_valor_interno = df_interno_f["valor_total"].sum()
        total_valor_externo = df_externo_f["valor_total"].sum()

        # Consumos médios
        consumo_interno = calcula_consumo_medio(df_interno_f)
        consumo_externo = calcula_consumo_medio(df_externo_f)
        consumo_combinado = calcula_consumo_medio_combinado(df_interno_f, df_externo_f)

        # -----------------------------
        # ABAS
        # -----------------------------
        tabs = st.tabs(["📈 Visão Geral", "🏭 Interno", "⛽ Externo", "🔀 Combinado"])

        # Visão geral
        with tabs[0]:
            st.subheader("Indicadores Principais")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("🚛 Litros Interno", f"{total_litros_interno:,.0f} L")
            col2.metric("⛽ Litros Externo", f"{total_litros_externo:,.0f} L")
            col3.metric("💰 Valor Interno", f"R$ {total_valor_interno:,.2f}")
            col4.metric("💵 Valor Externo", f"R$ {total_valor_externo:,.2f}")
            col5.metric("📊 Média Geral (km/l)",
                        f"{consumo_combinado['consumo_medio_km_l'].mean():.2f}" if not consumo_combinado.empty else "-")

            st.subheader("Top 5 Consumo Médio Interno")
            st.table(consumo_interno.head(5).style.format({"consumo_medio_km_l": "{:.2f}"}))

            st.subheader("Top 5 Consumo Médio Externo")
            st.table(consumo_externo.head(5).style.format({"consumo_medio_km_l": "{:.2f}"}))

        # Interno
        with tabs[1]:
            st.subheader("🏭 Abastecimento Interno")
            agg_placa = df_interno_f.groupby("placa")["quantidade_de_litros"].sum().reset_index()
            st.plotly_chart(px.bar(agg_placa, x="placa", y="quantidade_de_litros"), use_container_width=True)
            st.dataframe(df_interno_f)

        # Externo
        with tabs[2]:
            st.subheader("⛽ Abastecimento Externo")
            agg_placa = df_externo_f.groupby("placa")["quantidade_de_litros"].sum().reset_index()
            st.plotly_chart(px.bar(agg_placa, x="placa", y="quantidade_de_litros"), use_container_width=True)
            st.dataframe(df_externo_f)

        # Combinado
        with tabs[3]:
            st.subheader("🔀 Consumo Médio Combinado")
            st.table(consumo_combinado.style.format({"consumo_medio_km_l": "{:.2f}"}))
            fig_comb = px.bar(consumo_combinado, x="placa", y="consumo_medio_km_l", color="tipo_combustivel")
            st.plotly_chart(fig_comb, use_container_width=True)

    else:
        st.error("Não foi possível encontrar as abas 'interno' e 'externo' na planilha.")
