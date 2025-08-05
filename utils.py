import pandas as pd
import streamlit as st
import plotly.express as px

def processar_planilha(arquivo):
    xls = pd.ExcelFile(arquivo)
    externo = pd.read_excel(xls, "Abastecimento Externo")
    interno = pd.read_excel(xls, "Abastecimento Interno")

    # Marcar o tipo
    externo['tipo'] = 'Externo'
    interno['tipo'] = interno['Tipo'].fillna('Saída')

    # Manter apenas saídas no abastecimento interno
    interno = interno[interno['tipo'].str.lower().str.contains('saída')]

    # Renomear colunas para padronizar
    externo = externo.rename(columns={
        'Data': 'data',
        'Placa': 'placa',
        'Quantidade de litros': 'litros',
        'Valor Unitario': 'valor_unit',
        'Valor Total': 'valor_total',
        'KM Atual': 'km_atual',
    })

    interno = interno.rename(columns={
        'Data': 'data',
        'Placa': 'placa',
        'Quantidade de litros': 'litros',
        'Valor Unitario': 'valor_unit',
        'Valor Total': 'valor_total',
        'KM Atual': 'km_atual',
    })

    # Conversão segura de datas
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')
    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')

    # Remover linhas com datas inválidas
    externo = externo.dropna(subset=['data'])
    interno = interno.dropna(subset=['data'])

    # Selecionar e padronizar colunas
    colunas = ['data', 'placa', 'litros', 'valor_unit', 'valor_total', 'km_atual', 'tipo']
    df_unificado = pd.concat([externo[colunas], interno[colunas]], ignore_index=True)

    # Limpar placas inválidas
    df_unificado['placa'] = df_unificado['placa'].astype(str).str.upper().str.strip()
    df_unificado = df_unificado[df_unificado['placa'] != '-']
    df_unificado = df_unificado[df_unificado['placa'].str.lower() != 'correção']

    return df_unificado, interno, externo


def calcular_consumo(df):
    df = df.sort_values(['placa', 'data']).copy()
    df['km_anterior'] = df.groupby('placa')['km_atual'].shift(1)
    df['km_rodado'] = df['km_atual'] - df['km_anterior']

    # Eliminar casos com km_rodado <= 0 ou litros <= 0
    df = df[(df['km_rodado'] > 0) & (df['litros'] > 0)]

    df['consumo_km_l'] = df['km_rodado'] / df['litros']
    consumo = df.groupby('placa').agg({
        'km_rodado': 'sum',
        'litros': 'sum',
        'consumo_km_l': 'mean'
    }).reset_index()

    consumo.columns = ['Placa', 'KM Rodado', 'Litros Consumidos', 'Consumo Médio (km/l)']
    return consumo.round(2)


def comparar_fontes(df):
    comp = df.groupby(['tipo']).agg({
        'litros': 'sum',
        'valor_total': 'sum'
    }).reset_index()

    comp['valor_medio_litro'] = comp['valor_total'] / comp['litros']
    comp.columns = ['Tipo', 'Total de Litros', 'Total Pago', 'Valor Médio por Litro']
    return comp.round(2)


def gerar_graficos(df):
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
        fig1.update_layout(xaxis_title="Data", yaxis_title="Litros")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.box(
            df,
            x='placa',
            y='valor_unit',
            color='tipo',
            title='💰 Distribuição do Valor por Litro por Veículo'
        )
        fig2.update_layout(xaxis_title="Placa", yaxis_title="Valor Unitário (R$)")
        st.plotly_chart(fig2, use_container_width=True)
