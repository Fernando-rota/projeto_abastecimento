import pandas as pd
import plotly.express as px
import streamlit as st


@st.cache_data
def processar_planilha(arquivo):
    try:
        xls = pd.ExcelFile(arquivo)
        externo = pd.read_excel(xls, "Abastecimento Externo")
        interno = pd.read_excel(xls, "Abastecimento Interno")
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return pd.DataFrame()

    externo['tipo'] = 'Externo'
    interno['tipo'] = interno.get('Tipo', '').fillna('Saída')
    interno = interno[interno['tipo'].str.lower().str.contains('saída', na=False)]

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

    interno['valor_unit'] = interno.get('valor_unit') \
        .fillna(interno['valor_total'] / interno['litros'])

    for df in [externo, interno]:
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df.dropna(subset=['data'], inplace=True)

    colunas = ['data', 'placa', 'litros', 'valor_unit', 'valor_total', 'km_atual', 'tipo']
    df = pd.concat([externo[colunas], interno[colunas]], ignore_index=True)

    df['placa'] = df['placa'].astype(str).str.upper().str.strip()
    df = df[~df['placa'].isin(['-', '', 'CORREÇÃO'])]

    return df


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
    df_consumo = calcular_consumo(df)
    media_consumo = df_consumo['consumo_km_l'].mean()
    return round(total_litros, 2), round(total_gasto, 2), round(media_consumo, 2)


def ranking_eficiencia(df_consumo):
    return df_consumo.groupby('placa')['consumo_km_l'].mean().reset_index().round(2).sort_values(by='consumo_km_l', ascending=False)


def gerar_graficos(df_filtrado, df_consumo):
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
