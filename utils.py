import pandas as pd
import streamlit as st
import plotly.express as px


# ------------------------ CARREGAR E PROCESSAR PLANILHA ------------------------

@st.cache_data
def processar_planilha(arquivo):
    try:
        xls = pd.ExcelFile(arquivo)
        externo = pd.read_excel(xls, "Abastecimento Externo")
        interno = pd.read_excel(xls, "Abastecimento Interno")
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return pd.DataFrame()

    # Adiciona tipo
    externo['tipo'] = 'Externo'
    interno['tipo'] = interno.get('Tipo', '').fillna('Saída')

    # Filtra apenas saídas no abastecimento interno
    interno = interno[interno['tipo'].str.lower().str.contains('saída', na=False)]

    # Renomeia colunas
    renomear = {
        'Data': 'data',
        'Placa': 'placa',
        'Quantidade de litros': 'litros',
        'Valor Unitario': 'valor_unit',
        'Valor Total': 'valor_total',
        'KM Atual': 'km_atual'
    }

    externo = externo.rename(columns=renomear)
    interno = interno.rename(columns=renomear)

    # Preenche valor_unit no interno (caso ausente) como valor_total / litros
    interno['valor_unit'] = interno.get('valor_unit') \
        .fillna(interno['valor_total'] / interno['litros'])

    # Conversão de datas
    for df in [externo, interno]:
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df.dropna(subset=['data'], inplace=True)

    colunas = ['data', 'placa', 'litros', 'valor_unit', 'valor_total', 'km_atual', 'tipo']
    df = pd.concat([externo[colunas], interno[colunas]], ignore_index=True)

    # Limpa placas
    df['placa'] = df['placa'].astype(str).str.upper().str.strip()
    df = df[~df['placa'].isin(['-', '', 'CORREÇÃO'])]

    return df


# ------------------------ CÁLCULOS ------------------------

def calcular_consumo(df):
    df = df.sort_values(['placa', 'data']).copy()
    df['km_anterior'] = df.groupby('placa')['km_atual'].shift(1)
    df['km_rodado'] = df['km_atual'] - df['km_anterior']
    df = df[(df['km_rodado'] > 0) & (df['litros'] > 0)]
    df['consumo_km_l'] = df['km_rodado'] / df['litros']
    return df


def indicadores_resumo(df):
    total_litros = df['litros'].sum()
    total_gasto = df['valor_total'].sum()
    consumo_df = calcular_consumo(df)
    media_consumo = consumo_df['consumo_km_l'].mean()
    return round(total_litros, 2), round(total_gasto, 2), round(media_consumo, 2)


def ranking_eficiencia(df_consumo):
    return df_consumo.groupby('placa')['consumo_km_l'].mean().reset_index().round(2).sort_values(by='consumo_km_l', ascending=False)


# ------------------------ INTERFACE ------------------------

st.set_page_config("📊 Dashboard Abastecimento", layout="wide")
st.title("📊 Dashboard de Indicadores de Consumo e Abastecimento")

arquivo = st.file_uploader("📂 Faça upload da planilha (.xlsx)", type=["xlsx"])

if arquivo:
    df = processar_planilha(arquivo)

    if df.empty:
        st.warning("Nenhum dado encontrado.")
        st.stop()

    # Filtros
    st.sidebar.header("🔎 Filtros")
    placas = sorted(df['placa'].unique())
    tipos = df['tipo'].unique()

    placa_sel = st.sidebar.multiselect("Placa", placas, default=placas)
    tipo_sel = st.sidebar.multiselect("Tipo de Abastecimento", tipos, default=tipos)
    data_min, data_max = df['data'].min(), df['data'].max()
    data_sel = st.sidebar.date_input("Período", [data_min, data_max])

    df_filtrado = df[
        (df['placa'].isin(placa_sel)) &
        (df['tipo'].isin(tipo_sel)) &
        (df['data'].between(pd.to_datetime(data_sel[0]), pd.to_datetime(data_sel[1])))
    ]

    df_consumo = calcular_consumo(df_filtrado)

    # ------------------------ ABA 1: RESUMO ------------------------
    aba1, aba2, aba3 = st.tabs(["📋 Resumo Geral", "📈 Gráficos", "🏆 Ranking de Consumo"])

    with aba1:
        st.subheader("🔧 Indicadores Principais")
        col1, col2, col3 = st.columns(3)
        total_litros, total_gasto, media_consumo = indicadores_resumo(df_filtrado)

        col1.metric("🔸 Total de Litros", f"{total_litros} L")
        col2.metric("💰 Total Gasto", f"R$ {total_gasto:,.2f}")
        col3.metric("⛽ Consumo Médio", f"{media_consumo} km/L")

        st.divider()
        st.subheader("📄 Tabela de Dados Filtrados")
        st.dataframe(df_filtrado.sort_values(by='data', ascending=False), use_container_width=True)

    # ------------------------ ABA 2: GRÁFICOS ------------------------
    with aba2:
        col1, col2 = st.columns(2)

        with col1:
            fig1 = px.bar(
                df_filtrado,
                x='data',
                y='litros',
                color='tipo',
                title="⛽ Litros Abastecidos ao Longo do Tempo",
                labels={'litros': 'Litros', 'data': 'Data'}
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.box(
                df_filtrado,
                x='placa',
                y='valor_unit',
                color='tipo',
                title="💸 Valor por Litro por Veículo",
                labels={'valor_unit': 'Valor Unitário (R$)'}
            )
            st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.line(
            df_consumo,
            x='data',
            y='consumo_km_l',
            color='placa',
            title="📉 Tendência de Consumo (km/L)",
            labels={'consumo_km_l': 'Consumo (km/L)', 'data': 'Data'}
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ------------------------ ABA 3: RANKING ------------------------
    with aba3:
        st.subheader("🏁 Ranking de Eficiência (km/L)")
        ranking = ranking_eficiencia(df_consumo)
        st.dataframe(ranking.rename(columns={'placa': 'Placa', 'consumo_km_l': 'Consumo Médio (km/L)'}), use_container_width=True)

