# app.py
import re
from typing import List, Optional, Dict

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Dashboard Abastecimento (Interno+Externo)", layout="wide")


# ---------------------------
# Utilitários
# ---------------------------
def try_parse_number(x):
    """Parseia números monetários tanto BR (1.234,56 / R$ 1.234,56) quanto EN (1234.56)."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if s == "":
        return np.nan
    # remove R$ e espaços
    s = re.sub(r"[Rr]\$\s*", "", s)
    # se tem '.' e ',' -> assume '.' thousands e ',' decimal
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    # se só tem ',' -> troca por '.'
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    # remove outros caracteres possíveis
    s = re.sub(r"[^\d\.\-]", "", s)
    try:
        return float(s)
    except Exception:
        return np.nan


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """
    Tenta encontrar no dataframe a coluna que corresponde a qualquer dos 'candidates'
    (comparação case-insensitive, tenta substring).
    """
    cols_map = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_map:
            return cols_map[cand.lower()]
    # tentativa por substring
    for k_lower, orig in cols_map.items():
        for cand in candidates:
            if cand.lower() in k_lower:
                return orig
    return None


# ---------------------------
# Carregamento e padronização
# ---------------------------
@st.cache_data(show_spinner=True)
def load_two_sheets(file) -> Dict[str, pd.DataFrame]:
    """Lê o arquivo Excel e retorna dicionário com até duas folhas lidas."""
    xls = pd.ExcelFile(file)
    sheets = xls.sheet_names
    # preferir nomes exatos
    prefer = ["Abastecimento Interno", "Abastecimento Externo"]
    out = {}
    for p in prefer:
        if p in sheets:
            out[p] = pd.read_excel(xls, sheet_name=p)
    # se alguma preferida ausente, pega as primeiras folhas
    if len(out) < 2:
        for s in sheets:
            if s not in out and len(out) < 2:
                out[s] = pd.read_excel(xls, sheet_name=s)
    return out


def standardize_df(df: pd.DataFrame, origem_label: str) -> pd.DataFrame:
    """
    Padroniza um DataFrame de abastecimento para as colunas:
    data, AnoMes, placa, qtd_litros, valor_unit, valor_total, km, descricao, tipo, origem
    """
    df = df.rename(columns=lambda c: str(c).strip())  # trim cols
    # candidatas por campo (variações comuns)
    mapper = {
        "data": ["data", "date", "carimbo de data/hora", "carimbo", "data_hora"],
        "placa": ["placa", "plate"],
        "qtd_litros": ["quantidade de litros", "quantidade litros", "quantidade_de_litros", "litros", "qtd_litros"],
        "valor_unit": ["valor unitario", "valor unitário", "valor_unitario", "valor_unit"],
        "valor_total": ["valor total", "valor_total", "valor pago", "valor_pago", "valor"],
        "km": ["km atual", "km_atual", "km", "odometro", "odômetro", "kmatual"],
        "descricao": ["descrição despesa", "descrição do abastecimento", "descricao despesa", "descricao", "descrição"],
        "tipo": ["tipo", "tipo abastecimento", "type"]
    }

    found = {}
    for key, cands in mapper.items():
        col = find_column(df, cands)
        found[key] = col

    out = df.copy()

    # data
    if found["data"]:
        out["data"] = pd.to_datetime(out[found["data"]], dayfirst=True, errors="coerce")
    else:
        out["data"] = pd.NaT
        st.warning("Coluna de data não encontrada. Algumas análises dependem de datas.")

    out["AnoMes"] = out["data"].dt.to_period("M").astype(str)

    # placa
    if found["placa"]:
        out["placa"] = out[found["placa"]].astype(str).str.strip()
    else:
        out["placa"] = np.nan

    # quantidade de litros
    if found["qtd_litros"]:
        out["qtd_litros"] = pd.to_numeric(out[found["qtd_litros"]].astype(str).str.replace(",", "."), errors="coerce")
    else:
        out["qtd_litros"] = np.nan

    # valor unitario
    if found["valor_unit"]:
        out["valor_unit"] = out[found["valor_unit"]].apply(try_parse_number)
    else:
        out["valor_unit"] = np.nan

    # valor total
    if found["valor_total"]:
        out["valor_total"] = out[found["valor_total"]].apply(try_parse_number)
    else:
        # tenta calcular valor_total = valor_unit * qtd_litros
        out["valor_total"] = out["valor_unit"] * out["qtd_litros"]

    # km
    if found["km"]:
        out["km"] = pd.to_numeric(out[found["km"]].astype(str).str.replace(".", "").str.replace(",", "."), errors="coerce")
    else:
        out["km"] = np.nan

    # descricao (combustível)
    if found["descricao"]:
        out["descricao"] = out[found["descricao"]].astype(str).str.strip()
    else:
        out["descricao"] = "DESCONHECIDO"

    # tipo (opcional)
    if found["tipo"]:
        out["tipo"] = out[found["tipo"]].astype(str).str.strip().str.lower()
    else:
        out["tipo"] = np.nan

    out["origem"] = origem_label

    # retorna apenas colunas úteis
    cols = ["data", "AnoMes", "placa", "qtd_litros", "valor_unit", "valor_total", "km", "descricao", "tipo", "origem"]
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    return out[cols]


# ---------------------------
# Cálculos principais
# ---------------------------
def compute_autonomy_table(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula km_min, km_max, litros_total e autonomia por placa (numero)."""
    rows = []
    grouped = df.groupby("placa", dropna=True)
    for placa, g in grouped:
        km_min = g["km"].min()
        km_max = g["km"].max()
        litros = g["qtd_litros"].sum()
        autonomia = (km_max - km_min) / litros if pd.notna(km_min) and pd.notna(km_max) and litros > 0 else np.nan
        rows.append({"placa": placa, "km_min": km_min, "km_max": km_max, "litros": litros, "autonomia": autonomia})
    df_aut = pd.DataFrame(rows)
    df_aut = df_aut.sort_values("autonomia", ascending=False, na_position="last")
    return df_aut


# ---------------------------
# App principal
# ---------------------------
def app():
    st.title("🚛 Dashboard Abastecimento (Interno + Externo)")

    uploaded = st.sidebar.file_uploader("Faça upload do arquivo .xlsx (duas abas: Interno + Externo)", type=["xlsx"])
    if not uploaded:
        st.info("Carregue a planilha com as abas 'Abastecimento Interno' e 'Abastecimento Externo'.")
        st.stop()

    # leitura
    sheets = load_two_sheets(uploaded)
    if len(sheets) < 2:
        st.error("Não foram encontradas duas abas. Verifique o arquivo.")
        st.stop()

    # detectar qual é interno/externo
    keys = list(sheets.keys())
    name_interno = None
    name_externo = None
    for name in keys:
        ln = name.lower()
        if "intern" in ln:
            name_interno = name
        if "extern" in ln or "externo" in ln:
            name_externo = name
    if not name_interno:
        name_interno = keys[0]
    if not name_externo:
        name_externo = keys[1] if len(keys) > 1 else keys[0]

    df_raw_int = sheets[name_interno]
    df_raw_ext = sheets[name_externo]

    # padroniza
    df_int = standardize_df(df_raw_int, origem_label="Interno")
    df_ext = standardize_df(df_raw_ext, origem_label="Externo")

    # concatena
    df = pd.concat([df_int, df_ext], ignore_index=True)

    # remove registros sem placa/data/litros (essenciais)
    df = df[(df["placa"].notna()) & (df["data"].notna()) & (df["qtd_litros"].notna())]

    if df.empty:
        st.error("Após padronização não há dados válidos (placa/data/litros). Verifique planilha.")
        st.stop()

    # -----------------------
    # FILTROS NA SIDEBAR
    # -----------------------
    st.sidebar.header("Filtros")
    placas = ["Todas"] + sorted(df["placa"].dropna().unique().tolist())
    placa_sel = st.sidebar.selectbox("Placa", placas)

    origens = ["Todos"] + sorted(df["origem"].unique().tolist())
    origem_sel = st.sidebar.selectbox("Origem", origens)

    combustiveis = sorted(df["descricao"].dropna().unique().tolist())
    combustivel_sel = st.sidebar.multiselect("Tipo combustível (multiselect)", options=combustiveis, default=combustiveis)

    # período
    data_min = df["data"].min().date()
    data_max = df["data"].max().date()
    data_inicio, data_fim = st.sidebar.date_input("Período", [data_min, data_max], min_value=data_min, max_value=data_max)

    # aplicar filtros
    df_f = df.copy()
    if placa_sel != "Todas":
        df_f = df_f[df_f["placa"] == placa_sel]
    if origem_sel != "Todos":
        df_f = df_f[df_f["origem"] == origem_sel]
    if combustivel_sel:
        df_f = df_f[df_f["descricao"].isin(combustivel_sel)]
    df_f = df_f[(df_f["data"] >= pd.to_datetime(data_inicio)) & (df_f["data"] <= pd.to_datetime(data_fim))]

    if df_f.empty:
        st.warning("Sem dados para os filtros aplicados.")
        st.stop()

    # -----------------------
    # INDICADORES
    # -----------------------
    total_litros = df_f["qtd_litros"].sum()
    total_custo = df_f["valor_total"].sum()
    preco_medio = total_custo / total_litros if total_litros > 0 else np.nan

    # autonomia tabela
    aut_df = compute_autonomy_table(df_f)

    # resumo por combustível
    resumo_comb = df_f.groupby("descricao").agg(
        litros_total=("qtd_litros", "sum"),
        custo_total=("valor_total", "sum"),
        valor_unit_medio=("valor_unit", lambda x: np.nanmean(x.dropna()) if x.dropna().size > 0 else np.nan)
    ).reset_index().sort_values("litros_total", ascending=False)
    resumo_comb["preco_medio_calc"] = resumo_comb["custo_total"] / resumo_comb["litros_total"]

    # séries por mês
    series_litros = df_f.groupby(["AnoMes", "origem"]).agg(Litros=("qtd_litros", "sum")).reset_index()
    series_price = df_f.groupby(["AnoMes", "origem"]).apply(
        lambda x: x["valor_total"].sum() / x["qtd_litros"].sum() if x["qtd_litros"].sum() > 0 else np.nan
    ).reset_index(name="Preço Médio (R$/L)")

    # -----------------------
    # LAYOUT POR ABAS
    # -----------------------
    tab1, tab2, tab3, tab4 = st.tabs(["Resumo", "Autonomia", "Por Combustível", "Gráficos"])

    with tab1:
        st.header("Resumo Geral")
        c1, c2, c3 = st.columns(3)
        c1.metric("Litros (período)", f"{total_litros:,.2f} L")
        c2.metric("Custo Total (período)", f"R$ {total_custo:,.2f}")
        c3.metric("Preço Médio (R$/L)", f"R$ {preco_medio:,.3f}")

        st.markdown("**Top 10 placas por litros (no período)**")
        top_placas = df_f.groupby("placa")["qtd_litros"].sum().reset_index().sort_values("qtd_litros", ascending=False).head(10)
        st.dataframe(top_placas.rename(columns={"placa": "Placa", "qtd_litros": "Litros"}), use_container_width=True)

        # botão para exportar os dados filtrados
        csv = df_f.to_csv(index=False).encode("utf-8")
        st.download_button("⤓ Exportar dados filtrados (CSV)", csv, "abastecimento_filtrado.csv", "text/csv")

    with tab2:
        st.header("Autonomia por Placa (km/L) — ordenada decrescente")
        display_aut = aut_df.copy()
        display_aut["autonomia_str"] = display_aut["autonomia"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
        display_aut = display_aut.rename(columns={
            "placa": "Placa", "km_min": "KM Mínimo", "km_max": "KM Máximo", "litros": "Litros", "autonomia": "Autonomia (km/L)"
        })
        st.dataframe(display_aut[["Placa", "KM Mínimo", "KM Máximo", "Litros", "autonomia_str"]].rename(columns={"autonomia_str": "Autonomia (km/L)"}), use_container_width=True)

    with tab3:
        st.header("Consumo e Custo por Tipo de Combustível")
        resumo_comb_display = resumo_comb.rename(columns={
            "descricao": "Combustível",
            "litros_total": "Litros",
            "custo_total": "Custo Total",
            "valor_unit_medio": "Valor Unitário Médio",
            "preco_medio_calc": "Preço Médio (R$/L)"
        })
        st.dataframe(resumo_comb_display, use_container_width=True)

        fig_cost = px.bar(resumo_comb_display, x="Combustível", y="Custo Total",
                          hover_data=["Litros", "Preço Médio (R$/L)"], title="Custo por Combustível")
        st.plotly_chart(fig_cost, use_container_width=True)

    with tab4:
        st.header("Séries Mensais")
        fig1 = px.bar(series_litros, x="AnoMes", y="Litros", color="origem", barmode="group",
                      title="Litros por Mês (Interno x Externo)")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.line(series_price, x="AnoMes", y="Preço Médio (R$/L)", color="origem", markers=True,
                       title="Preço Médio por Mês (Interno x Externo)")
        st.plotly_chart(fig2, use_container_width=True)

    # dicas
    st.sidebar.markdown("---")
    st.sidebar.info("Dicas: use o filtro de combustíveis (multiselect) para comparar tipos; exporte os dados filtrados com o botão.")

if __name__ == "__main__":
    app()
