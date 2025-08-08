import streamlit as st
import pandas as pd
import unicodedata
import plotly.express as px
import re

# -----------------------------
# FUNÇÕES AUXILIARES
# -----------------------------
def normalizar_colunas(df):
    df = df.copy()
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
    # remove R$ espaços e pontos. troca vírgula por ponto
    valor_limpo = re.sub(r"[R$\s\.]", "", valor_str)
    valor_limpo = valor_limpo.replace(",", ".")
    try:
        return float(valor_limpo)
    except:
        return 0.0

def calcular_consumo_medio_simples(df, por_combustivel=False):
    """
    Calcula consumo médio por grupo usando:
    (KM máximo - KM mínimo) / soma(total litros)
    Se por_combustivel=True, agrupa por (placa, tipo_combustivel).
    Retorna DataFrame com consumo_medio_km_l em alta precisão (float).
    """
    resultados = []
    if df is None or df.empty:
        cols = ["placa", "km_inicial", "km_final", "total_litros", "consumo_medio_km_l"]
        if por_combustivel:
            cols.insert(1, "tipo_combustivel")
        return pd.DataFrame(columns=cols)

    dff = df.copy()
    # Padroniza
    dff["placa"] = dff["placa"].astype(str).str.upper().str.strip()
    dff["km_atual"] = pd.to_numeric(dff.get("km_atual"), errors="coerce")
    dff["quantidade_de_litros"] = pd.to_numeric(dff.get("quantidade_de_litros"), errors="coerce")
    if "tipo_combustivel" in dff.columns:
        dff["tipo_combustivel"] = dff["tipo_combustivel"].fillna("N/A").astype(str).str.upper().str.strip()
    # Remove registros inválidos
    dff = dff.dropna(subset=["placa", "km_atual", "quantidade_de_litros"])
    dff = dff[dff["quantidade_de_litros"] > 0]

    group_cols = ["placa"]
    if por_combustivel and "tipo_combustivel" in dff.columns:
        group_cols = ["placa", "tipo_combustivel"]

    for group_key, grupo in dff.groupby(group_cols):
        # group_key pode ser string ou tupla
        if isinstance(group_key, tuple):
            placa = group_key[0]
            tipo = group_key[1]
        else:
            placa = group_key
            tipo = grupo["tipo_combustivel"].iloc[0] if "tipo_combustivel" in grupo.columns else None

        km_inicial = grupo["km_atual"].min()
        km_final = grupo["km_atual"].max()
        total_litros = grupo["quantidade_de_litros"].sum()

        if pd.isna(km_inicial) or pd.isna(km_final) or total_litros <= 0:
            continue
        if km_final <= km_inicial:
            continue

        consumo_medio = (km_final - km_inicial) / total_litros

        row = {
            "placa": placa,
            "km_inicial": float(km_inicial),
            "km_final": float(km_final),
            "total_litros": float(total_litros),
            "consumo_medio_km_l": float(consumo_medio)
        }
        if por_combustivel:
            row["tipo_combustivel"] = tipo
        resultados.append(row)

    df_res = pd.DataFrame(resultados)
    if df_res.empty:
        return df_res
    # Ordena do maior para o menor consumo
    df_res = df_res.sort_values("consumo_medio_km_l", ascending=False).reset_index(drop=True)
    return df_res

# -----------------------------
# DASHBOARD
# -----------------------------
st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")
st.title("📊 Dashboard de Abastecimento Interno x Externo — Cálculo KMmax-KMmin / Litros")

arquivo = st.file_uploader("📂 Envie a planilha de abastecimento (com abas 'interno' e 'externo')", type=["xlsx"])

if not arquivo:
    st.info("Envie a planilha .xlsx com as abas 'interno' e 'externo' para começar.")
    st.stop()

# Lê todas as abas
abas = pd.read_excel(arquivo, sheet_name=None)
nomes_abas = {nome.lower(): nome for nome in abas.keys()}
nome_interno = next((n for n in nomes_abas if "interno" in n), None)
nome_externo = next((n for n in nomes_abas if "externo" in n), None)

if not (nome_interno and nome_externo):
    st.error("Não foi possível encontrar as abas 'interno' e 'externo' na planilha.")
    st.stop()

# Normaliza
df_interno = normalizar_colunas(abas[nomes_abas[nome_interno]])
df_externo = normalizar_colunas(abas[nomes_abas[nome_externo]])

# Parse datas (se existirem)
if "data" in df_interno.columns:
    df_interno["data"] = pd.to_datetime(df_interno["data"], errors="coerce", dayfirst=True)
else:
    df_interno["data"] = pd.NaT

if "data" in df_externo.columns:
    df_externo["data"] = pd.to_datetime(df_externo["data"], errors="coerce", dayfirst=True)
else:
    df_externo["data"] = pd.NaT

# Limpeza e padronização de colunas importantes
def padronizar_df(df):
    df = df.copy()
    # Valores monetários
    if "valor_total" in df.columns:
        df["valor_total"] = df["valor_total"].apply(limpar_valor_monetario)
    else:
        df["valor_total"] = 0.0

    if "valor_unitario" in df.columns:
        df["valor_unitario"] = df["valor_unitario"].apply(limpar_valor_monetario)
    else:
        df["valor_unitario"] = 0.0

    # Placa / combustivel / numericos
    df["placa"] = df.get("placa", pd.Series([""] * len(df))).astype(str).str.upper().str.strip()
    if "tipo_combustivel" in df.columns:
        df["tipo_combustivel"] = df["tipo_combustivel"].fillna("N/A").astype(str).str.upper().str.strip()
    else:
        df["tipo_combustivel"] = "N/A"

    df["quantidade_de_litros"] = pd.to_numeric(df.get("quantidade_de_litros", pd.Series([pd.NA]*len(df))), errors="coerce")
    df["km_atual"] = pd.to_numeric(df.get("km_atual", pd.Series([pd.NA]*len(df))), errors="coerce")

    return df

df_interno = padronizar_df(df_interno)
df_externo = padronizar_df(df_externo)

# Remover registros de entrada de tanque (placa '-') do interno, se houver
if "placa" in df_interno.columns:
    df_interno = df_interno[df_interno["placa"] != "-"]

# FILTROS (global)
st.sidebar.header("Filtros")
# Datas combinadas
combined_dates = pd.concat([df_interno["data"], df_externo["data"]]).dropna()
if combined_dates.empty:
    data_min = pd.to_datetime("today").date()
    data_max = pd.to_datetime("today").date()
else:
    data_min = pd.to_datetime(combined_dates.min()).date()
    data_max = pd.to_datetime(combined_dates.max()).date()

data_inicio = st.sidebar.date_input("Data Início", value=data_min, min_value=data_min, max_value=data_max)
data_fim = st.sidebar.date_input("Data Fim", value=data_max, min_value=data_min, max_value=data_max)
if data_inicio > data_fim:
    st.sidebar.error("Data Início não pode ser maior que Data Fim.")

# Placas disponíveis (ignorando vazias e placeholders)
placas = sorted(set(df_interno["placa"].dropna().unique()).union(set(df_externo["placa"].dropna().unique())))
placas = [p for p in placas if p not in ("", "-", "N/A", "NA")]
placa_selecionada = st.sidebar.selectbox("Selecione a Placa", ["Todas"] + placas)

# Combustíveis disponíveis
combustiveis = sorted(set(df_interno["tipo_combustivel"].unique()).union(set(df_externo["tipo_combustivel"].unique())))
combustiveis = [c for c in combustiveis if c not in ("", "-", "N/A")]
combustivel_selecionado = st.sidebar.selectbox("Selecione o Tipo de Combustível", ["Todos"] + combustiveis)

# Caixa para checar uma placa específica (útil para validar cálculo)
placa_para_checar = st.sidebar.text_input("Verificar placa (ex: OQG06668) — mostra passo a passo", value="").strip().upper()

def aplicar_filtros(df):
    dff = df.copy()
    # Filtra por data (usa coluna data)
    dff = dff[(dff["data"] >= pd.to_datetime(data_inicio)) & (dff["data"] <= pd.to_datetime(data_fim))]
    if placa_selecionada != "Todas":
        dff = dff[dff["placa"] == placa_selecionada]
    if combustivel_selecionado != "Todos":
        dff = dff[dff["tipo_combustivel"] == combustivel_selecionado]
    return dff

df_interno_f = aplicar_filtros(df_interno)
df_externo_f = aplicar_filtros(df_externo)

# Combined (interno + externo) após filtros
df_combinado_f = pd.concat([df_interno_f, df_externo_f], ignore_index=True)

# Totais
total_litros_interno = df_interno_f["quantidade_de_litros"].sum()
total_litros_externo = df_externo_f["quantidade_de_litros"].sum()
total_valor_interno = df_interno_f["valor_total"].sum()
total_valor_externo = df_externo_f["valor_total"].sum()

# Cálculos de consumo (novo método simples)
consumo_interno = calcular_consumo_medio_simples(df_interno_f, por_combustivel=False)
consumo_externo = calcular_consumo_medio_simples(df_externo_f, por_combustivel=False)
consumo_combinado = calcular_consumo_medio_simples(df_combinado_f, por_combustivel=False)

# TABS
tabs = st.tabs(["📈 Visão Geral", "🏭 Interno", "⛽ Externo", "🔀 Combinado", "🔎 Checar Placa"])

with tabs[0]:
    st.subheader("Indicadores Principais")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🚛 Litros Interno", f"{total_litros_interno:,.2f} L")
    col2.metric("⛽ Litros Externo", f"{total_litros_externo:,.2f} L")
    col3.metric("💰 Valor Interno", f"R$ {total_valor_interno:,.2f}")
    col4.metric("💵 Valor Externo", f"R$ {total_valor_externo:,.2f}")
    col5.metric("📊 Média Combinada (km/l)",
                f"{consumo_combinado['consumo_medio_km_l'].mean():.3f}" if not consumo_combinado.empty else "-")

    st.markdown("**Top Consumo Combinado (Top 10)**")
    if not consumo_combinado.empty:
        st.table(consumo_combinado.head(10).style.format({"consumo_medio_km_l": "{:.9f}"}))
    else:
        st.write("Sem dados suficientes para cálculo.")

with tabs[1]:
    st.subheader("🏭 Abastecimento Interno")
    if not df_interno_f.empty:
        agg_placa = df_interno_f.groupby("placa")["quantidade_de_litros"].sum().reset_index().sort_values(by="quantidade_de_litros", ascending=False)
        st.plotly_chart(px.bar(agg_placa, x="placa", y="quantidade_de_litros", title="Litros por Veículo (Interno)"), use_container_width=True)
        st.markdown("**Consumo Médio (Interno)**")
        if not consumo_interno.empty:
            st.table(consumo_interno.style.format({"consumo_medio_km_l": "{:.9f}"}))
        else:
            st.write("Sem dados suficientes para cálculo (Interno).")
        with st.expander("Ver tabela detalhada (Interno)"):
            st.dataframe(df_interno_f)
    else:
        st.info("Sem registros internos no período/filtros selecionados.")

with tabs[2]:
    st.subheader("⛽ Abastecimento Externo")
    if not df_externo_f.empty:
        agg_placa = df_externo_f.groupby("placa")["quantidade_de_litros"].sum().reset_index().sort_values(by="quantidade_de_litros", ascending=False)
        st.plotly_chart(px.bar(agg_placa, x="placa", y="quantidade_de_litros", title="Litros por Veículo (Externo)"), use_container_width=True)
        st.markdown("**Consumo Médio (Externo)**")
        if not consumo_externo.empty:
            st.table(consumo_externo.style.format({"consumo_medio_km_l": "{:.9f}"}))
        else:
            st.write("Sem dados suficientes para cálculo (Externo).")
        with st.expander("Ver tabela detalhada (Externo)"):
            st.dataframe(df_externo_f)
    else:
        st.info("Sem registros externos no período/filtros selecionados.")

with tabs[3]:
    st.subheader("🔀 Consumo Médio Combinado (Interno + Externo)")
    st.markdown("**Método:** (KM máximo - KM mínimo) ÷ Soma dos litros no período filtrado.")
    if not consumo_combinado.empty:
        st.table(consumo_combinado.style.format({"consumo_medio_km_l": "{:.9f}"}))
        fig = px.bar(consumo_combinado, x="placa", y="consumo_medio_km_l", title="Consumo Médio Combinado por Placa")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Sem dados suficientes para cálculo combinado com os filtros aplicados.")

with tabs[4]:
    st.subheader("🔎 Checagem por Placa")
    st.markdown("Coloque a placa que você quer verificar (ex.: `OQG06668`). O app mostrará os registros usados no cálculo e o passo a passo.")
    placa_checar = placa_para_checar
    if placa_checar:
        placa_checar = placa_checar.upper().strip()
        dados_placa = df_combinado_f[df_combinado_f["placa"] == placa_checar].copy()
        if dados_placa.empty:
            st.warning(f"Nenhum registro encontrado para a placa {placa_checar} com os filtros atuais.")
        else:
            # mostra registros ordenados por data e km
            if "data" in dados_placa.columns:
                dados_placa = dados_placa.sort_values(["data", "km_atual"])
            else:
                dados_placa = dados_placa.sort_values("km_atual")
            st.markdown("**Registros usados:**")
            st.dataframe(dados_placa)

            km_inicial = float(dados_placa["km_atual"].min())
            km_final = float(dados_placa["km_atual"].max())
            total_litros = float(dados_placa["quantidade_de_litros"].sum())
            consumo = None
            if total_litros > 0 and km_final > km_inicial:
                consumo = (km_final - km_inicial) / total_litros

            st.markdown("**Passo a passo do cálculo:**")
            st.write(f"- KM inicial (mínimo): `{km_inicial}`")
            st.write(f"- KM final (máximo): `{km_final}`")
            st.write(f"- Total de litros (soma): `{total_litros}`")
            if consumo is not None:
                st.write(f"- Consumo médio = (km_final - km_inicial) / total_litros = `{consumo:.9f}` km/l")
            else:
                st.warning("Não foi possível calcular (verifique se há pelo menos 2 registros com km distintos e litros > 0).")

# Explanatory expander
with st.expander("Como esse cálculo funciona (detalhes técnicos)"):
    st.markdown("""
    - Estamos usando **KM mínimo** e **KM máximo** dentro do período/filtragem aplicados.
    - Soma-se **todos** os litros abastecidos nesse mesmo conjunto de registros.
    - Fórmula: **(KM máximo - KM mínimo) / Soma dos litros**.
    - Essa abordagem dá uma visão **média geral do período**, menos sensível a flutuações por abastecimentos parciais.
    - Se quiser uma granularidade por tipo de combustível, posso ativar `por_combustivel=True` para agrupar também por tipo.
    """)
