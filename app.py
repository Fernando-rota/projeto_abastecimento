import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path


# ===================================
# CARREGAMENTO DE DADOS
# ===================================
@st.cache_data(show_spinner=True)
def carregar_dados(arquivo):
    """
    Lê as abas 'Abastecimento Interno' e 'Abastecimento Externo' 
    de um arquivo Excel e retorna dois DataFrames.
    """
    try:
        df_interno = pd.read_excel(arquivo, sheet_name="Abastecimento Interno")
        df_externo = pd.read_excel(arquivo, sheet_name="Abastecimento Externo")
        return df_interno, df_externo
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
        return None, None


# ===================================
# PRÉ-PROCESSAMENTO
# ===================================
def limpa_monetario(coluna):
    """Remove 'R$' e converte valores monetários para float."""
    return pd.to_numeric(
        coluna.astype(str).str.replace(r"R\$\s*", "", regex=True),
        errors="coerce"
    )


def processa_abastecimento(df, interno=True):
    """
    Limpa e padroniza colunas do DataFrame de abastecimento.
    Se interno=True, mantém apenas registros do tipo 'entrada'.
    """
    colunas_esperadas = [
        "Data", "Quantidade de litros", "Valor Total", 
        "Valor Unitario", "KM Atual"
    ]
    
    for coluna in colunas_esperadas:
        if coluna not in df.columns:
            st.warning(f"Atenção: coluna '{coluna}' não encontrada.")

    # Conversões de tipos
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Data"])
    df["AnoMes"] = df["Data"].dt.to_period("M").astype(str)
    df["Quantidade de litros"] = pd.to_numeric(df["Quantidade de litros"], errors="coerce")

    if "Valor Total" in df.columns:
        df["Valor Total"] = pd.to_numeric(df["Valor Total"], errors="coerce")
    if "Valor Unitario" in df.columns:
        df["Valor Unitario"] = limpa_monetario(df["Valor Unitario"])

    df["KM Atual"] = pd.to_numeric(df["KM Atual"], errors="coerce")
    df["Origem"] = "Interno" if interno else "Externo"

    if interno and "Tipo" in df.columns:
        df = df[df["Tipo"].str.lower() == "entrada"]

    return df


# ===================================
# ANÁLISE E CÁLCULOS
# ===================================
def calcula_autonomia(df):
    """Calcula autonomia (km/L) para cada placa."""
    autonomia = {}
    for placa, grupo in df.groupby("Placa"):
        km_max = grupo["KM Atual"].max()
        km_min = grupo["KM Atual"].min()
        litros = grupo["Quantidade de litros"].sum()

        if pd.notna(km_max) and pd.notna(km_min) and litros > 0:
            autonomia[placa] = (km_max - km_min) / litros
        else:
            autonomia[placa] = None

    return autonomia


def filtra_dados(df, placa, ano_mes, origem, data_inicio, data_fim):
    """Filtra o DataFrame conforme os parâmetros selecionados."""
    df_filt = df.copy()

    if placa != "Todas":
        df_filt = df_filt[df_filt["Placa"] == placa]
    if ano_mes != "Todos":
        df_filt = df_filt[df_filt["AnoMes"] == ano_mes]
    if origem != "Todos":
        df_filt = df_filt[df_filt["Origem"] == origem]

    df_filt = df_filt[
        (df_filt["Data"] >= pd.to_datetime(data_inicio)) &
        (df_filt["Data"] <= pd.to_datetime(data_fim))
    ]
    return df_filt


# ===================================
# INTERFACE PRINCIPAL
# ===================================
def main():
    st.title("🚛 Dashboard Avançado de Abastecimento")

    # Upload do arquivo
    arquivo = st.sidebar.file_uploader(
        "Selecione o arquivo Excel",
        type=["xlsx"],
        help="O arquivo deve conter as abas 'Abastecimento Interno' e 'Abastecimento Externo'."
    )

    if arquivo is None:
        st.info("Envie o arquivo para começar.")
        return

    # Carregamento
    df_interno, df_externo = carregar_dados(arquivo)
    if df_interno is None or df_externo is None:
        return

    # Processamento
    df_interno = processa_abastecimento(df_interno, interno=True)
    df_externo = processa_abastecimento(df_externo, interno=False)
    df = pd.concat([df_interno, df_externo], ignore_index=True)
    df = df.dropna(subset=["Placa", "Quantidade de litros", "Data"])

    # Filtros
    placas = ["Todas"] + sorted(df["Placa"].dropna().unique())
    anos_meses = ["Todos"] + sorted(df["AnoMes"].unique())
    origens = ["Todos", "Interno", "Externo"]

    st.sidebar.header("Filtros")
    placa_sel = st.sidebar.selectbox("Placa", placas)
    ano_mes_sel = st.sidebar.selectbox("Mês (AAAA-MM)", anos_meses)
    origem_sel = st.sidebar.selectbox("Origem", origens)

    data_min, data_max = df["Data"].min().date(), df["Data"].max().date()
    data_inicio, data_fim = st.sidebar.date_input(
        "Período",
        [data_min, data_max],
        min_value=data_min,
        max_value=data_max
    )

    # Filtragem
    df_filt = filtra_dados(df, placa_sel, ano_mes_sel, origem_sel, data_inicio, data_fim)

    if df_filt.empty:
        st.warning("Nenhum dado encontrado para os filtros.")
        return

    # Indicadores
    litros_totais = df_filt["Quantidade de litros"].sum()
    valor_total = df_filt["Valor Total"].sum()
    preco_medio = valor_total / litros_totais if litros_totais > 0 else 0

    autonomia_df = pd.DataFrame([
        {"Placa": p, "Autonomia (km/L)": v if v is not None else "N/A"}
        for p, v in calcula_autonomia(df_filt).items()
    ]).sort_values(by="Autonomia (km/L)", ascending=False)

    litros_mes = df_filt.groupby(["AnoMes", "Origem"]).agg({"Quantidade de litros": "sum"}).reset_index()
    preco_mes = df_filt.groupby(["AnoMes", "Origem"]).apply(
        lambda x: x["Valor Total"].sum() / x["Quantidade de litros"].sum()
        if x["Quantidade de litros"].sum() > 0 else 0
    ).reset_index(name="Preco Medio")

    # Layout de abas
    tab1, tab2, tab3 = st.tabs([
        "📊 Indicadores",
        "🚙 Autonomia",
        "📈 Gráficos"
    ])

    with tab1:
        col1, col2, col3 = st.columns(3)
        col1.metric("Litros Totais", f"{litros_totais:,.2f} L")
        col2.metric("Valor Total", f"R$ {valor_total:,.2f}")
        col3.metric("Preço Médio", f"R$ {preco_medio:,.3f}/L")

    with tab2:
        st.dataframe(autonomia_df)

    with tab3:
        st.plotly_chart(
            px.bar(litros_mes, x="AnoMes", y="Quantidade de litros", color="Origem",
                   barmode="group", title="Litros Mensais - Interno x Externo"),
            use_container_width=True
        )
        st.plotly_chart(
            px.line(preco_mes, x="AnoMes", y="Preco Medio", color="Origem",
                    markers=True, title="Preço Médio Mensal - Interno x Externo"),
            use_container_width=True
        )

    # Rodapé
    st.sidebar.markdown("---")
    st.sidebar.info("💡 Dicas: filtre por placa, mês ou origem para análises mais detalhadas.")


if __name__ == "__main__":
    main()
