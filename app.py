import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Dashboard Consumo Médio", layout="wide")
st.title("📊 Dashboard Consumo Médio de Veículos")

# --- FUNÇÃO PARA CARREGAR OS DADOS ---
@st.cache_data
def load_data(file_path):
    # Carregar abas da planilha Excel
    interno = pd.read_excel(file_path, sheet_name='interno')
    externo = pd.read_excel(file_path, sheet_name='externo')
    consumo = pd.read_excel(file_path, sheet_name='consumo')
    
    # Padronizar colunas internas (exemplo)
    interno.rename(columns=lambda x: x.strip().lower().replace(' ', '_'), inplace=True)
    externo.rename(columns=lambda x: x.strip().lower().replace(' ', '_'), inplace=True)
    consumo.rename(columns=lambda x: x.strip().lower().replace(' ', '_'), inplace=True)
    
    # Converter datas para datetime
    if 'data' in interno.columns:
        interno['data'] = pd.to_datetime(interno['data'])
    if 'data' in externo.columns:
        externo['data'] = pd.to_datetime(externo['data'])
    if 'data' in consumo.columns:
        consumo['data'] = pd.to_datetime(consumo['data'])
    
    return interno, externo, consumo

# --- CARREGAR ARQUIVO ---
uploaded_file = st.file_uploader("📁 Carregue sua planilha Excel com abas: interno, externo, consumo", type=['xlsx'])
if uploaded_file:
    interno, externo, consumo = load_data(uploaded_file)

    # --- FILTROS ---
    st.sidebar.header("Filtros")

    # Datas min/max para filtro
    min_date = min(interno['data'].min(), externo['data'].min())
    max_date = max(interno['data'].max(), externo['data'].max())
    date_range = st.sidebar.date_input("Período", [min_date, max_date])

    # Filtrar por placa: obter placas únicas das duas bases
    placas_interno = interno['placa'].dropna().unique()
    placas_externo = externo['placa'].dropna().unique()
    placas = sorted(set(placas_interno).union(set(placas_externo)))
    placas_selected = st.sidebar.multiselect("Selecione Placa(s)", options=placas, default=placas)

    # Filtrar por tipo combustível (exemplo - pode precisar ajustar nomes)
    combustiveis_interno = interno['tipo'].dropna().unique() if 'tipo' in interno.columns else []
    combustiveis_externo = externo['tipo_combustivel'].dropna().unique() if 'tipo_combustivel' in externo.columns else []
    combustiveis = sorted(set(combustiveis_interno).union(set(combustiveis_externo)))
    combustiveis_selected = st.sidebar.multiselect("Tipo de Combustível", options=combustiveis, default=combustiveis)

    # --- FILTRAR DATA ---
    data_start, data_end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    interno_filt = interno[(interno['data'] >= data_start) & (interno['data'] <= data_end)]
    externo_filt = externo[(externo['data'] >= data_start) & (externo['data'] <= data_end)]

    # --- FILTRAR PLACA ---
    interno_filt = interno_filt[interno_filt['placa'].isin(placas_selected)]
    externo_filt = externo_filt[externo_filt['placa'].isin(placas_selected)]

    # --- FILTRAR COMBUSTÍVEL ---
    if 'tipo' in interno_filt.columns:
        interno_filt = interno_filt[interno_filt['tipo'].isin(combustiveis_selected)]
    if 'tipo_combustivel' in externo_filt.columns:
        externo_filt = externo_filt[externo_filt['tipo_combustivel'].isin(combustiveis_selected)]

    # --- CONCATENAR BASES para cálculo ---
    # Padronizar colunas para concatenar
    interno_filt = interno_filt.rename(columns={'quantidade_de_litros': 'litros', 'km_atual': 'km', 'tipo': 'combustivel'})
    externo_filt = externo_filt.rename(columns={'quantidade_de_litros': 'litros', 'km_atual': 'km', 'tipo_combustivel': 'combustivel'})

    cols_necessarias = ['data', 'placa', 'combustivel', 'litros', 'km']
    interno_sel = interno_filt[cols_necessarias]
    externo_sel = externo_filt[cols_necessarias]

    abastecimentos = pd.concat([interno_sel, externo_sel], ignore_index=True)

    # --- CALCULAR CONSUMO MÉDIO POR PLACA ---
    # Para cada placa, pegar menor e maior KM, somar litros e calcular consumo médio
    resumo = abastecimentos.groupby('placa').agg(
        km_min=('km', 'min'),
        km_max=('km', 'max'),
        litros_totais=('litros', 'sum')
    ).reset_index()

    resumo['km_rodados'] = resumo['km_max'] - resumo['km_min']
    resumo['consumo_medio_km_por_litro'] = resumo['km_rodados'] / resumo['litros_totais']
    resumo = resumo.sort_values('consumo_medio_km_por_litro', ascending=False)

    st.header("Resumo Consumo Médio por Veículo")
    st.dataframe(resumo.style.format({
        'km_min': '{:,.0f}',
        'km_max': '{:,.0f}',
        'litros_totais': '{:,.2f}',
        'km_rodados': '{:,.0f}',
        'consumo_medio_km_por_litro': '{:.2f}'
    }))

    # --- GRÁFICO ---
    fig = px.bar(
        resumo,
        x='placa',
        y='consumo_medio_km_por_litro',
        labels={'consumo_medio_km_por_litro': 'Km por Litro', 'placa': 'Placa'},
        title='Consumo Médio (Km por Litro) por Veículo'
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Faça upload da planilha Excel para começar.")
