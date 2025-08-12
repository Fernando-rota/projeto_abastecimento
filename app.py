import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="BI Abastecimento Completo", layout="wide")
st.title("⛽ BI Abastecimento - Preço e Consumo Mês a Mês")

@st.cache_data
def load_data(file_path):
    interno = pd.read_excel(file_path, sheet_name='Abastecimento Interno')
    externo = pd.read_excel(file_path, sheet_name='Abastecimento Externo')

    interno.columns = interno.columns.str.strip().str.lower().str.replace(' ', '_')
    externo.columns = externo.columns.str.strip().str.lower().str.replace(' ', '_')

    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')

    interno.dropna(subset=['data'], inplace=True)
    externo.dropna(subset=['data'], inplace=True)

    return interno, externo

def preprocess_interno(df):
    # Converte colunas importantes
    df['quantidade_de_litros'] = df['quantidade_de_litros'].astype(str).str.replace(',', '.', regex=False)
    df['valor_unitario'] = df['valor_unitario'].astype(str).str.replace(',', '.', regex=False).str.replace('r$', '', case=False).str.strip()
    df['valor_unitario'] = pd.to_numeric(df['valor_unitario'], errors='coerce')
    df['quantidade_de_litros'] = pd.to_numeric(df['quantidade_de_litros'], errors='coerce')

    # Filtra dados válidos
    df = df.dropna(subset=['quantidade_de_litros', 'valor_unitario'])

    # Cria coluna mês-ano para agrupamento
    df['mes_ano'] = df['data'].dt.to_period('M').dt.to_timestamp()

    return df

def preprocess_externo(df):
    # Colunas já no formato esperado: 'quantidade_de_litros', 'valor_unitario'
    df['quantidade_de_litros'] = df['quantidade_de_litros'].astype(str).str.replace(',', '.', regex=False)
    df['valor_unitario'] = df['valor_unitario'].astype(str).str.replace(',', '.', regex=False).str.replace('r$', '', case=False).str.strip()
    df['valor_unitario'] = pd.to_numeric(df['valor_unitario'], errors='coerce')
    df['quantidade_de_litros'] = pd.to_numeric(df['quantidade_de_litros'], errors='coerce')

    df = df.dropna(subset=['quantidade_de_litros', 'valor_unitario'])
    df['mes_ano'] = df['data'].dt.to_period('M').dt.to_timestamp()

    return df

uploaded_file = st.file_uploader("📁 Carregue sua planilha Excel com abas: Abastecimento Interno e Abastecimento Externo", type=['xlsx'])
if uploaded_file:
    interno, externo = load_data(uploaded_file)

    interno = preprocess_interno(interno)
    externo = preprocess_externo(externo)

    st.sidebar.header("Filtros")

    placas = sorted(set(interno['placa'].dropna().unique()) | set(externo['placa'].dropna().unique()))
    placas_selected = st.sidebar.multiselect("Placas", placas, default=placas)

    combust_interno = interno['tipo'].dropna().unique() if 'tipo' in interno.columns else []
    combust_externo = externo['descrição_despesa'].dropna().unique() if 'descrição_despesa' in externo.columns else []
    combust_unificado = sorted(set(combust_interno) | set(combust_externo))
    combust_selected = st.sidebar.multiselect("Tipo Combustível", combust_unificado, default=combust_unificado)

    data_min = min(interno['data'].min(), externo['data'].min())
    data_max = max(interno['data'].max(), externo['data'].max())
    periodo = st.sidebar.date_input("Período", [data_min, data_max])

    start_date, end_date = pd.to_datetime(periodo[0]), pd.to_datetime(periodo[1])

    interno_filt = interno[
        (interno['placa'].isin(placas_selected)) &
        (interno['data'] >= start_date) & (interno['data'] <= end_date) &
        (interno['tipo'].isin(combust_selected))
    ]

    externo_filt = externo[
        (externo['placa'].isin(placas_selected)) &
        (externo['data'] >= start_date) & (externo['data'] <= end_date) &
        (externo['descrição_despesa'].isin(combust_selected))
    ]

    # Indicadores por mês e placa - Interno
    resumo_interno = interno_filt.groupby(['mes_ano', 'placa']).agg(
        total_litros=('quantidade_de_litros', 'sum'),
        preco_medio=('valor_unitario', 'mean'),
        custo_total=('valor_unitario', lambda x: (x * interno_filt.loc[x.index, 'quantidade_de_litros']).sum())
    ).reset_index()

    # Indicadores por mês e placa - Externo
    resumo_externo = externo_filt.groupby(['mes_ano', 'placa']).agg(
        total_litros=('quantidade_de_litros', 'sum'),
        preco_medio=('valor_unitario', 'mean'),
        custo_total=('valor_unitario', lambda x: (x * externo_filt.loc[x.index, 'quantidade_de_litros']).sum())
    ).reset_index()

    # União para visão geral
    resumo_geral = pd.concat([
        resumo_interno.assign(tipo_abastecimento='Interno'),
        resumo_externo.assign(tipo_abastecimento='Externo')
    ])

    # Total mensal geral (todos veículos juntos)
    resumo_mes = resumo_geral.groupby(['mes_ano', 'tipo_abastecimento']).agg(
        total_litros=('total_litros', 'sum'),
        custo_total=('custo_total', 'sum')
    ).reset_index()
    resumo_mes['preco_medio'] = resumo_mes['custo_total'] / resumo_mes['total_litros']

    st.header("📅 Preço Médio e Consumo Mensal")

    fig1 = px.line(resumo_mes, x='mes_ano', y='preco_medio', color='tipo_abastecimento',
                   labels={'mes_ano': 'Mês', 'preco_medio': 'Preço Médio (R$)', 'tipo_abastecimento': 'Tipo'},
                   title='Preço Médio Mensal por Tipo de Abastecimento')
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.bar(resumo_mes, x='mes_ano', y='total_litros', color='tipo_abastecimento',
                  labels={'mes_ano': 'Mês', 'total_litros': 'Total Litros', 'tipo_abastecimento': 'Tipo'},
                  title='Consumo Total de Litros por Mês e Tipo')
    st.plotly_chart(fig2, use_container_width=True)

    st.header("📊 Detalhado por Veículo e Mês")
    st.dataframe(resumo_geral.sort_values(['mes_ano', 'placa']), use_container_width=True)

else:
    st.info("Faça upload da planilha Excel para começar.")
