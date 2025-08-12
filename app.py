import re
from pathlib import Path
from typing import Dict, Optional, List

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")


# -------------------------
# Utilitários
# -------------------------
def try_parse_number(s):
    """Parseia strings monetárias/numéricas em formatos BR/EN (ex: 'R$ 1.234,56' ou '5.79')."""
    if s is None:
        return np.nan
    s = str(s).strip()
    if s == "" or s.lower() in {"nan", "none", "na"}:
        return np.nan

    # remove R$ e espaços
    s = re.sub(r"[Rr]\$\s*", "", s)
    # se tem ambos '.' e ',' => assumimos '.' thousands e ',' decimal: "1.234,56" -> "1234.56"
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    # se tem ',' e não tem '.' => "5,79" -> "5.79"
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    # else: só tem '.' => provavelmente já em formato en "5.79" (mantemos)
    try:
        return float(s)
    except Exception:
        # última tentativa removendo qualquer não-dígito exceto '.' and '-'
        s2 = re.sub(r"[^\d\.\-]", "", s)
        try:
            return float(s2) if s2 not in ("", ".", "-") else np.nan
        except Exception:
            return np.nan


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """
    Retorna o nome real da coluna do dataframe que mais se aproxima das 'candidates' (insensível a maiúsculas).
    """
    cols = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    # tentativa por substring
    for k_lower, orig in cols.items():
        for cand in candidates:
            if cand.lower() in k_lower:
                return orig
    return None


# -------------------------
# Carregamento + padronização
# -------------------------
@st.cache_data(show_spinner=True)
def load_excel_two_sheets(file) -> Dict[str, pd.DataFrame]:
    """
    Tenta ler as abas 'Abastecimento Interno' e 'Abastecimento Externo'.
    Se não encontrar, lê as duas primeiras abas e informa no app.
    """
    xls = pd.ExcelFile(file)
    sheets = xls.sheet_names
    result = {}
    # prefer names exactos
    preferidas = ["Abastecimento Interno", "Abastecimento Externo"]
    for pref in preferidas:
        if pref in sheets:
            result[pref] = pd.read_excel(xls, sheet_name=pref)
    # se alguma preferida faltou, pega as primeiras abas não lidas
    if len(result) < 2:
        for s in sheets:
            if s not in result and len(result) < 2:
                result[s] = pd.read_excel(xls, sheet_name=s)
    return result


def standardize_df(df: pd.DataFrame, origem_label: str) -> pd.DataFrame:
    """
    Padroniza colunas com nomes variados para um conjunto de nomes internos:
    data, placa, qtd_litros, valor_unit, valor_total, km, descricao, tipo (se existir).
    Também converte tipos e cria 'AnoMes' e 'Origem'.
    """
    # limpeza de colunas: remover espaços desnecessários
    df = df.rename(columns=lambda c: str(c).strip())
    # candidatos possíveis para cada campo
    mapper = {
        "data": ["data", "date", "carimbo de data/hora", "data_hora", "data hora"],
        "placa": ["placa", "plate"],
        "qtd_litros": ["quantidade de litros", "quantidade litros", "litros", "quantidade_de_litros", "qtd litros", "qtd_litros"],
        "valor_unit": ["valor unitario", "valor unitário", "valor_unitario", "valor unit", "valor_unit"],
        "valor_total": ["valor total", "valor_total", "valor", "valor_total_pago", "valor pago", "valor_pago"],
        "km": ["km atual", "km_atual", "km", "odometro", "odômetro", "kmatual"],
        "descricao": ["descrição despesa", "descrição do abastecimento", "descricao despesa", "descricao do abastecimento", "descrição", "descricao", "descricao do abastecimento", "descrição do abastecimento", "descrição despesa"],
        "tipo": ["tipo", "tipo abastecimento", "tipo de abastecimento", "type"]
    }

    found = {}
    for key, cands in mapper.items():
        col = find_column(df, cands)
        found[key] = col

    # criar colunas padronizadas com fallback
    def safe_col(name):
        return found.get(name) if found.get(name) in df.columns else None

    # copia para evitar alterar original
    out = df.copy()

    # Data
    data_col = safe_col("data")
    if data_col is None:
        st.warning("Coluna de data não encontrada — muitas análises dependem de datas.")
        out["data"] = pd.NaT
    else:
        out["data"] = pd.to_datetime(out[data_col], dayfirst=True, errors="coerce")

    # Placa
    placa_col = safe_col("placa")
    out["placa"] = out[placa_col].astype(str).str.strip() if placa_col else np.nan

    # Quantidade litros
    qtd_col = safe_col("qtd_litros")
    if qtd_col:
        out["qtd_litros"] = pd.to_numeric(out[qtd_col].astype(str).str.replace(",", ".").str.replace(" ", ""), errors="coerce")
    else:
        out["qtd_litros"] = np.nan

    # Valor unitario
    vu_col = safe_col("valor_unit")
    if vu_col:
        out["valor_unit"] = out[vu_col].apply(try_parse_number)
    else:
        out["valor_unit"] = np.nan

    # Valor total
    vt_col = safe_col("valor_total")
    if vt_col:
        out["valor_total"] = out[vt_col].apply(try_parse_number)
    else:
        # se não existir, calcular quando possível
        out["valor_total"] = out["valor_unit"] * out["qtd_litros"]

    # KM
    km_col = safe_col("km")
    if km_col:
        out["km"] = pd.to_numeric(out[km_col].astype(str).str.replace(".", "").str.replace(",", "."), errors="coerce")
    else:
        out["km"] = np.nan

    # descricao (tipo de combustivel)
    desc_col = safe_col("descricao")
    if desc_col:
        out["descricao"] = out[desc_col].astype(str).str.strip()
    else:
        out["descricao"] = "DESCONHECIDO"

    # tipo (opcional)
    tipo_col = safe_col("tipo")
    if tipo_col:
        out["tipo"] = out[tipo_col].astype(str).str.strip().str.lower()
    else:
        out["tipo"] = np.nan

    # Origem e AnoMes
    out["origem"] = origem_label
    out["AnoMes"] = out["data"].dt.to_period("M").astype(str)

    # Retornar apenas colunas úteis
    return out[["data", "AnoMes", "placa", "qtd_litros", "valor_unit", "valor_total", "km", "descricao", "tipo", "origem"]]


# -------------------------
# Cálculos
# -------------------------
def compute_autonomy_table(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna DataFrame com km_min, km_max, litros_total e autonomia por placa (numeric)."""
    rows = []
    grouped = df.groupby("placa", dropna=True)
    for placa, g in grouped:
        km_min = g["km"].min()
        km_max = g["km"].max()
        litros = g["qtd_litros"].sum()
        autonomia = (km_max - km_min) / litros if pd.notna(km_min) and pd.notna(km_max) and litros > 0 else np.nan
        rows.append({
            "placa": placa,
            "km_min": km_min,
            "km_max": km_max,
            "litros": litros,
            "autonomia": autonomia
        })
    df_aut = pd.DataFrame(rows)
    df_aut = df_aut.sort_values("autonomia", ascending=False, na_position="last")
    return df_aut


# -------------------------
# UI / App
# -------------------------
def app():
    st.title("🚛 Dashboard de Abastecimento (robusto e compatível)")

    uploaded = st.sidebar.file_uploader("Carregue arquivo Excel (.xlsx) com as 2 abas", type=["xlsx"])
    if not uploaded:
        st.info("Faça upload do arquivo Excel que contém as abas de Abastecimento Interno e Externo.")
        st.stop()

    sheets = load_excel_two_sheets(uploaded)
    # detect sheet names chosen
    # assumimos que o primeiro é interno e o segundo externo caso nomes não confiram
    sheet_keys = list(sheets.keys())
    if len(sheet_keys) < 2:
        st.error("Não foi possível encontrar duas abas no arquivo.")
        st.stop()

    # escolher quais folhas são interno/externo (se o nome for óbvio, usamos)
    name_interno = None
    name_externo = None
    for name in sheet_keys:
        if "intern" in name.lower():
            name_interno = name
        if "extern" in name.lower() or "externo" in name.lower():
            name_externo = name
    if not name_interno:
        name_interno = sheet_keys[0]
    if not name_externo:
        name_externo = sheet_keys[1] if len(sheet_keys) > 1 else sheet_keys[0]

    df_raw_interno = sheets[name_interno]
    df_raw_externo = sheets[name_externo]

    # processa e padroniza
    df_interno = standardize_df(df_raw_interno, origem_label="Interno")
    df_externo = standardize_df(df_raw_externo, origem_label="Externo")

    # concatena
    df = pd.concat([df_interno, df_externo], ignore_index=True)

    # limpa registros sem placa/data/litros
    df = df[ (df["placa"].notna()) & (df["data"].notna()) & (df["qtd_litros"].notna()) ]

    if df.empty:
        st.error("Após a padronização, não restaram dados válidos. Verifique as colunas da planilha.")
        st.stop()

    # Sidebar filtros
    st.sidebar.header("Filtros")
    placas = ["Todas"] + sorted(df["placa"].dropna().unique().tolist())
    placa_sel = st.sidebar.selectbox("Placa", placas)

    origens = ["Todos"] + sorted(df["origem"].unique().tolist())
    origem_sel = st.sidebar.selectbox("Origem", origens)

    combustiveis = ["Todos"] + sorted(df["descricao"].dropna().unique().tolist())
    combustivel_sel = st.sidebar.multiselect("Tipo de combustível (vários)", options=sorted(df["descricao"].unique()), default=sorted(df["descricao"].unique()))

    # intervalo de datas
    data_min = df["data"].min().date()
    data_max = df["data"].max().date()
    data_inicio, data_fim = st.sidebar.date_input("Período", [data_min, data_max], min_value=data_min, max_value=data_max)

    # aplicação dos filtros
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

    # indicadores principais
    total_litros = df_f["qtd_litros"].sum()
    total_custo = df_f["valor_total"].sum()
    preco_medio = total_custo / total_litros if total_litros > 0 else np.nan

    # abas
    tab1, tab2, tab3, tab4 = st.tabs(["Resumo", "Autonomia", "Por Combustível", "Gráficos"])

    with tab1:
        st.header("📌 Resumo Rápido")
        c1, c2, c3 = st.columns(3)
        c1.metric("Litros (periodo)", f"{total_litros:,.2f} L")
        c2.metric("Custo Total (periodo)", f"R$ {total_custo:,.2f}")
        c3.metric("Preço Médio (R$/L)", f"R$ {preco_medio:,.3f}")

        st.markdown("**Top 10 placas por consumo de litros no período**")
        top_placas = df_f.groupby("placa")["qtd_litros"].sum().reset_index().sort_values("qtd_litros", ascending=False).head(10)
        st.dataframe(top_placas.rename(columns={"placa":"Placa","qtd_litros":"Litros"}), use_container_width=True)

    with tab2:
        st.header("🚗 Autonomia por Placa (km / L)")
        aut_df = compute_autonomy_table(df_f)
        # mostra com formatação sem perder a ordenação numérica
        display_aut = aut_df.copy()
        display_aut["autonomia_str"] = display_aut["autonomia"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "N/A")
        display_aut = display_aut.rename(columns={
            "placa":"Placa","km_min":"KM Mínimo","km_max":"KM Máximo","litros":"Litros","autonomia":"Autonomia (km/L)"
        })
        st.dataframe(display_aut[["Placa","KM Mínimo","KM Máximo","Litros","autonomia_str"]].rename(columns={"autonomia_str":"Autonomia (km/L)"}), use_container_width=True)

    with tab3:
        st.header("⛽ Consumo e Custo por Tipo de Combustível")
        resumo_comb = df_f.groupby("descricao").agg(
            litros_total = ("qtd_litros","sum"),
            custo_total = ("valor_total","sum"),
            valor_unit_medio = ("valor_unit", lambda x: np.nanmean(x.dropna()) if len(x.dropna())>0 else np.nan)
        ).reset_index().sort_values("litros_total", ascending=False)
        resumo_comb = resumo_comb.rename(columns={"descricao":"Combustível","litros_total":"Litros","custo_total":"Custo Total","valor_unit_medio":"Valor Unit Médio"})
        resumo_comb["Preço Médio (R$/L)"] = resumo_comb["Custo Total"] / resumo_comb["Litros"]
        st.dataframe(resumo_comb, use_container_width=True)

        # gráfico de barras custo por combustível
        fig_cost = px.bar(resumo_comb, x="Combustível", y="Custo Total", hover_data=["Litros","Preço Médio (R$/L)"], title="Custo por Combustível")
        st.plotly_chart(fig_cost, use_container_width=True)

    with tab4:
        st.header("📈 Séries por Mês")
        liters_month = df_f.groupby(["AnoMes","origem"]).agg(Litros=("qtd_litros","sum")).reset_index()
        price_month = df_f.groupby(["AnoMes","origem"]).apply(
            lambda x: x["valor_total"].sum() / x["qtd_litros"].sum() if x["qtd_litros"].sum()>0 else np.nan
        ).reset_index(name="Preço Médio (R$/L)")

        fig_litros = px.bar(liters_month, x="AnoMes", y="Litros", color="origem", barmode="group", title="Litros por Mês (Interno x Externo)")
        st.plotly_chart(fig_litros, use_container_width=True)

        fig_price = px.line(price_month, x="AnoMes", y="Preço Médio (R$/L)", color="origem", markers=True, title="Preço Médio por Mês (Interno x Externo)")
        st.plotly_chart(fig_price, use_container_width=True)

    # rodapé com instruções
    st.sidebar.markdown("---")
    st.sidebar.info("Dicas: \n• Use múltiplos combustíveis no filtro.\n• Ajuste período para comparar janelas.\n\nSe quiser, eu deixo esse layout com exportação CSV e alertas de anomalia.")

if __name__ == "__main__":
    app()
