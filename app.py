import pandas as pd
import streamlit as st

# ==========================
# Funções auxiliares
# ==========================
def processa_abastecimento_externo(df):
    df['Valor Unitario'] = pd.to_numeric(
        df['Valor Unitario'].astype(str).str.replace(r'R\$\s*', '', regex=True).str.replace(',', '.'),
        errors='coerce'
    )
    df['Quantidade Litros'] = pd.to_numeric(df['Quantidade Litros'], errors='coerce')
    df['KM Atual'] = pd.to_numeric(df['KM Atual'], errors='coerce')
    df['Origem'] = 'Externo'
    return df

def processa_abastecimento_interno(df):
    df['Valor Unitario'] = pd.to_numeric(df.get('Valor Unitario', None), errors='coerce')
    df['Quantidade Litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['KM Atual'] = pd.to_numeric(df['KM Atual'], errors='coerce')
    df['Origem'] = 'Interno'
    return df

def calcula_autonomia(df):
    autonomia_list = []
    for placa, grupo in df.groupby('Placa'):
        km_max = grupo['KM Atual'].max()
        km_min = grupo['KM Atual'].min()
        litros_totais = grupo['Quantidade Litros'].sum()
        if litros_totais > 0:
            autonomia = (km_max - km_min) / litros_totais
        else:
            autonomia = None
        autonomia_list.append({
            'Placa': placa,
            'KM Mínimo': km_min,
            'KM Máximo': km_max,
            'Litros': litros_totais,
            'Autonomia (km/L)': autonomia
        })
    return pd.DataFrame(autonomia_list)

# ==========================
# App principal
# ==========================
def main():
    st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")

    st.title("📊 Dashboard de Abastecimento")

    uploaded_file = st.file_uploader("Carregue a planilha com as abas Interno e Externo", type=["xlsx"])
    if not uploaded_file:
        st.stop()

    # Leitura das duas abas
    df_externo = pd.read_excel(uploaded_file, sheet_name="Abastecimento Externo")
    df_interno = pd.read_excel(uploaded_file, sheet_name="Abastecimento Interno")

    # Processamento
    df_externo = processa_abastecimento_externo(df_externo)
    df_interno = processa_abastecimento_interno(df_interno)

    # Unir bases
    df_comb = pd.concat([df_externo, df_interno], ignore_index=True)

    # Filtros dinâmicos
    combustiveis = sorted(df_comb['Descrição do Abastecimento'].dropna().unique())
    origens = sorted(df_comb['Origem'].dropna().unique())

    filtro_comb = st.sidebar.multiselect("Filtrar por tipo de combustível", combustiveis, default=combustiveis)
    filtro_origem = st.sidebar.multiselect("Filtrar por origem", origens, default=origens)

    df_filtrado = df_comb[
        df_comb['Descrição do Abastecimento'].isin(filtro_comb) &
        df_comb['Origem'].isin(filtro_origem)
    ]

    # ==========================
    # Indicadores gerais
    # ==========================
    total_litros = df_filtrado['Quantidade Litros'].sum()
    custo_total = (df_filtrado['Valor Unitario'] * df_filtrado['Quantidade Litros']).sum()
    preco_medio = custo_total / total_litros if total_litros > 0 else None

    # ==========================
    # Abas do Dashboard
    # ==========================
    tab_resumo, tab_autonomia, tab_custos, tab_comp = st.tabs([
        "📌 Resumo Geral", "🚗 Autonomia", "💰 Custos por Combustível", "⚖️ Interno x Externo"
    ])

    with tab_resumo:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Litros", f"{total_litros:,.2f}")
        col2.metric("Custo Total", f"R$ {custo_total:,.2f}")
        col3.metric("Preço Médio (R$/L)", f"R$ {preco_medio:,.2f}" if preco_medio else "N/A")

    with tab_autonomia:
        autonomia_df = calcula_autonomia(df_filtrado)
        autonomia_df = autonomia_df.sort_values(by="Autonomia (km/L)", ascending=False)
        st.dataframe(
            autonomia_df.assign(
                **{"Autonomia (km/L)": autonomia_df["Autonomia (km/L)"].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A")}
            ).reset_index(drop=True)
        )

    with tab_custos:
        custo_por_comb = df_filtrado.groupby('Descrição do Abastecimento').apply(
            lambda x: pd.Series({
                "Litros": x['Quantidade Litros'].sum(),
                "Custo Total": (x['Valor Unitario'] * x['Quantidade Litros']).sum()
            })
        ).reset_index()
        custo_por_comb["Preço Médio (R$/L)"] = custo_por_comb["Custo Total"] / custo_por_comb["Litros"]
        st.dataframe(custo_por_comb)

    with tab_comp:
        comp_origem = df_filtrado.groupby('Origem').apply(
            lambda x: pd.Series({
                "Litros": x['Quantidade Litros'].sum(),
                "Custo Total": (x['Valor Unitario'] * x['Quantidade Litros']).sum()
            })
        ).reset_index()
        comp_origem["Preço Médio (R$/L)"] = comp_origem["Custo Total"] / comp_origem["Litros"]
        st.dataframe(comp_origem)

if __name__ == "__main__":
    main()
