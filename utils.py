import pandas as pd
import streamlit as st
import plotly.express as px


def processar_planilha(arquivo):
    """
    Processa a planilha Excel contendo duas abas:
    'Abastecimento Externo' e 'Abastecimento Interno'.
    Retorna os DataFrames: df_unificado, interno, externo.
    """
    try:
        xls = pd.ExcelFile(arquivo)
        externo = pd.read_excel(xls, "Abastecimento Externo")
        interno = pd.read_excel(xls, "Abastecimento Interno")
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Adiciona coluna 'tipo'
    externo['tipo'] = 'Externo'
    interno['tipo'] = interno.get('Tipo', '').fillna('Saída')

    # Filtra apenas saídas no abastecimento interno
    interno = interno[interno['tipo'].str.lower().str.contains('saída', na=False)]

    # Colunas para padronização
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

    # Conversão de datas com tratamento
    for df in [externo, interno]:
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df.dropna(subset=['data'], inplace=True)

    # Colunas padronizadas
    colunas = ['data', 'placa', 'litros', 'valor_unit', 'valor_total', 'km_atual', 'tipo']
    df_unificado = pd.concat([externo[colunas], interno[colunas]], ignore_index=True)

    # Limpeza das placas
    df_unificado['placa'] = df_unificado['placa'].astype(str).str.upper().str.strip()
    df_unificado = df_unificado[
        (~df_unificado['placa'].isin(['-', '', 'CORREÇÃO']))
    ]

    return df_unificado, interno, externo


def calcular_consumo(df):
    """
    Calcula o consumo médio (km/l) por veículo com base nos abastecimentos.
    """
    df = df.sort_values(['placa', 'data']).copy()
    df['km_anterior'] = df.groupby('placa')['km_atual'].shift(1)
    df['km_rodado'] = df['km_atual'] - df['km_anterior']

    # Remove dados inválidos
    df = df[(df['km_rodado'] > 0) & (df['litros'] > 0)]

    # Calcula consumo
    df['consumo_km_l'] = df['km_rodado'] / df['litros']

    consumo = df.groupby('placa').agg({
        'km_rodado': 'sum',
        'litros': 'sum',
        'consumo_km_l': 'mean'
    }).reset_index()

    consumo.columns = ['Placa', 'KM Rodado', 'Litros Consumidos', 'Consumo Médio (km/l)']
    return consumo.round(2)


def comparar_fontes(df):
    """
    Compara abastecimento Interno vs Externo:
    total de litros, valor total e valor médio por litro.
    """
    comp = df.groupby('tipo').agg({
        'litros': 'sum',
        'valor_total': 'sum'
    }).reset_index()

    comp['valor_medio_litro'] = comp['valor_total'] / comp['litros']
    comp.columns = ['Tipo', 'Total de Litros', 'Total Pago', 'Valor Médio por Litro']
    return comp.round(2)


def gerar_graficos(df):
    """
    Gera gráficos interativos com Plotly:
    - Litros abastecidos por data
    - Valor por litro por veículo
    """
    st.markdown("#### 📊 Gráficos de Abastecimento")

    col1, col2 = st.columns(2)

    with col1:
        fig1 = px.histogram(
            df,
            x='data',
            y='litros',
            color='tipo',
            barmode='group',
            title='⛽ Litros Abastecidos por Data'
        )
        fig1.update_layout(
            xaxis_title="Data",
            yaxis_title="Litros",
            legend_title="Tipo",
            margin=dict(t=40, b=0)
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.box(
            df,
            x='placa',
            y='valor_unit',
            color='tipo',
            title='💰 Valor por Litro por Veículo'
        )
        fig2.update_layout(
            xaxis_title="Placa",
            yaxis_title="Valor Unitário (R$)",
            legend_title="Tipo",
            margin=dict(t=40, b=0)
        )
        st.plotly_chart(fig2, use_container_width=True)
