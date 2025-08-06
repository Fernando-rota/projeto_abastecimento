import streamlit as st
import pandas as pd
import plotly.express as px
from utils import (
    carregar_dados,
    preparar_dados,
    calcular_preco_medio_interno,
    aplicar_valor_interno,
    calcular_consumo,
    calcular_indicadores_resumo,
    calcular_ranking_eficiencia,
    preparar_estoque_tanque,
)

st.set_page_config(page_title="Dashboard de Abastecimento", layout="wide")
st.title("⛽ Dashboard de Abastecimento - Frota")

# === Upload ===
st.sidebar.header("📂 Importar Planilha")
arquivo = st.sidebar.file_uploader("Selecione o arquivo Excel (.xlsx)", type="xlsx")

if arquivo:
    externo_raw, interno_raw = carregar_dados(arquivo)
    preco_medio_interno = calcular_preco_medio_interno(interno_raw)

    df_base = preparar_dados(externo_raw, interno_raw)
    df_base = aplicar_valor_interno(df_base, preco_medio_interno)
    df_base = calcular_consumo(df_base)

    # === Filtro período ===
    st.sidebar.header("📅 Filtrar por Período")
    min_data = df_base['data'].min()
    max_data = df_base['data'].max()
    data_inicio, data_fim = st.sidebar.date_input(
        "Selecione o intervalo",
        [min_data, max_data],
        min_value=min_data,
        max_value=max_data
    )
    df_base = df_base[(df_base['data'] >= pd.to_datetime(data_inicio)) & (df_base['data'] <= pd.to_datetime(data_fim))]

    # === Filtros globais ===
    st.sidebar.header("🔎 Filtros")
    placas_validas = sorted(df_base['placa'].dropna().unique())
    placa_sel = st.sidebar.multiselect("Filtrar por placa", placas_validas, default=placas_validas)

    tipo_sel = st.sidebar.multiselect("Tipo de abastecimento", ['Interno', 'Externo'], default=['Interno', 'Externo'])

    df_filtro = df_base[
        (df_base['placa'].isin(placa_sel)) &
        (df_base['origem'].isin(tipo_sel))
    ]

    abas = st.tabs(["📊 Resumo Geral", "🏅 Ranking de Eficiência", "📈 Tendência de Abastecimento", "⛽ Estoque do Tanque"])

    # === Aba 1: Resumo Geral ===
    with abas[0]:
        st.subheader("📊 Indicadores Gerais")
        indicadores = calcular_indicadores_resumo(df_filtro)

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("🚛 Total de Litros", f"{indicadores['total_litros']:.0f} L")
        col2.metric("💰 Valor Total", f"R$ {indicadores['total_valor']:.2f}")
        col3.metric("⚖️ Valor Médio por Litro", f"R$ {indicadores['valor_medio']:.2f}")
        col4.metric("🏷️ % Interno", f"{indicadores['pct_interno']*100:.0f}%")
        col5.metric("💸 Custo por KM", f"R$ {indicadores['custo_por_km']:.4f}")

        st.divider()
        st.subheader("📌 Abastecimentos por Origem")
        df_origem = df_filtro.groupby('origem')['litros'].sum().reset_index()
        fig_origem = px.pie(df_origem, names='origem', values='litros', hole=0.4, title="Distribuição por Origem")
        st.plotly_chart(fig_origem, use_container_width=True)

    # === Aba 2: Ranking de Eficiência ===
    with abas[1]:
        st.subheader("🏅 Ranking de Consumo Médio (km/l)")
        df_rank = calcular_ranking_eficiencia(df_filtro)
        st.dataframe(df_rank, use_container_width=True)

        fig_rank = px.bar(df_rank, x='placa', y='km_litro', text_auto='.2f', title="Ranking de Eficiência")
        fig_rank.update_layout(xaxis_title="Placa", yaxis_title="km/l")
        st.plotly_chart(fig_rank, use_container_width=True)

    # === Aba 3: Tendência ===
    with abas[2]:
        st.subheader("📈 Evolução Mensal dos Abastecimentos")
        df_mes = df_filtro.copy()
        df_mes['ano_mes'] = df_mes['data'].dt.to_period('M').astype(str)
        tendencia = df_mes.groupby(['ano_mes', 'origem'])['litros'].sum().reset_index()

        fig_tendencia = px.bar(
            tendencia,
            x='ano_mes',
            y='litros',
            color='origem',
            barmode='group',
            title="Litros Abastecidos por Mês"
        )
        st.plotly_chart(fig_tendencia, use_container_width=True)

    # === Aba 4: Estoque Tanque ===
    with abas[3]:
        st.subheader("⛽ Histórico de Entradas no Tanque (Reservatório)")
        df_tanque = preparar_estoque_tanque(interno_raw)

        col5, col6 = st.columns(2)
        with col5:
            fig_ent = px.line(df_tanque, x='data', y='litros', title="Entradas de Litros no Tanque")
            st.plotly_chart(fig_ent, use_container_width=True)

        with col6:
            fig_med = px.line(df_tanque, x='data', y='medidor', title="Medidor do Tanque")
            st.plotly_chart(fig_med, use_container_width=True)

        st.divider()
        st.dataframe(df_tanque[['data', 'litros', 'medidor', 'soma_medidor']], use_container_width=True)

else:
    st.info("Faça o upload da planilha para começar a análise.")
