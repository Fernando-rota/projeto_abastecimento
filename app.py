import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Dashboard Consumo Médio", layout="wide")
st.title("📊 Dashboard Consumo Médio de Veículos")

@st.cache_data
def load_data(file_path):
    interno = pd.read_excel(file_path, sheet_name='interno')
    externo = pd.read_excel(file_path, sheet_name='externo')
    consumo = pd.read_excel(file_path, sheet_name='consumo')

    # Padronizar nomes colunas para minúsculo e sem espaços
    interno.rename(columns=lambda x: x.strip().lower().replace(' ', '_'), inplace=True)
    externo.rename(columns=lambda x: x.strip().lower().replace(' ', '_'), inplace=True)
    consumo.rename(columns=lambda x: x.strip().lower().replace(' ', '_'), inplace=True)

    # Converter datas, ignorando erros e convertendo inválidos para NaT
    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')
    consumo['data'] = pd.to_datetime(consumo['data'], errors='coerce')

    # Remover linhas com datas inválidas (NaT)
    interno.dropna(subset=['data'], inplace=True)
    externo.dropna(subset=['data'], inplace=True)
    consumo.dropna(subset=['data'], inplace=True)

    return interno, externo, consumo

uploaded_file = st.file_uploader("📁 Carregue sua planilha Excel com abas: interno, externo, consumo", type=['xlsx'])
if uploaded_file:
    interno, externo, consumo = load_data(uploaded_file)

    st.sidebar.header("Filtros")

    min_date = min(interno['data'].min(), externo['data'].min())
    max_date = max(interno['data'].max(), externo['data'].max())
    date_range = st.sidebar.date_input("Período", [min_date, max_date])

    placas_interno = interno['placa'].dropna().unique()
    placas_externo = externo['placa'].dropna().unique()
    placas = sorted(set(placas_interno).union(set(placas_externo)))
    placas_selected = st.sidebar.multiselect("Selecione Placa(s)", options=placas, default=placas)

    combustiveis_interno = interno['tipo'].dropna().unique() if 'tipo' in interno.columns else []
    combustiveis_externo = externo['tipo_combustivel'].dropna().unique() if 'tipo_combustivel' in externo.columns else []
    combustiveis = sorted(set(combustiveis_interno).union(set(combustiveis_externo)))
    combustiveis_selected = st.sidebar.multiselect("Tipo de Combustível", options=combustiveis, default=combustiveis)

    data_start, data_end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    interno_filt = interno[(interno['data'] >= data_start) & (interno['data'] <= data_end)]
    externo_filt = externo[(externo['data'] >= data_start) & (externo['data'] <= data_end)]

    interno_filt = interno_filt[interno_filt['placa'].isin(placas_selected)]
    externo_filt = externo_filt[externo_filt['placa'].isin(placas_selected)]

    if 'tipo' in interno_filt.columns:
        interno_filt = interno_filt[interno_filt['tipo'].isin(combustiveis_selected)]
    if 'tipo_combustivel' in externo_filt.columns:
        externo_filt = externo_filt[externo_filt['tipo_combustivel'].isin(combustiveis_selected)]

    interno_filt = interno_filt.rename(columns={'quantidade_de_litros': 'litros', 'km_atual': 'km', 'tipo': 'combustivel'})
    externo_filt = externo_filt.rename(columns={'quantidade_de_litros': 'litros', 'km_atual': 'km', 'tipo_combustivel': 'combustivel'})

    cols_necessarias = ['data', 'placa', 'combustivel', 'litros', 'km']
    interno_sel = interno_filt[cols_necessarias]
    externo_sel = externo_filt[cols_necessarias]

    abastecimentos = pd.concat([interno_sel, externo_sel], ignore_index=True)

    # Tratar vírgulas e converter para numérico
    abastecimentos['km'] = abastecimentos['km'].astype(str).str.replace(',', '.', regex=False)
    abastecimentos['litros'] = abastecimentos['litros'].astype(str).str.replace(',', '.', regex=False)
    abastecimentos['km'] = pd.to_numeric(abastecimentos['km'], errors='coerce')
    abastecimentos['litros'] = pd.to_numeric(abastecimentos['litros'], errors='coerce')

    # Remover linhas com km ou litros inválidos
    abastecimentos.dropna(subset=['km', 'litros'], inplace=True)

    resumo = abastecimentos.groupby('placa').agg(
        km_min=('km', 'min'),
        km_max=('km', 'max'),
        litros_totais=('litros', 'sum')
    ).reset_index()

    resumo['km_rodados'] = resumo['km_max'] - resumo['km_min']
    resumo['consumo_medio_km_por_litro'] = resumo.apply(
        lambda row: row['km_rodados'] / row['litros_totais'] if row['litros_totais'] > 0 else None,
        axis=1
    )

    resumo = resumo.sort_values('consumo_medio_km_por_litro', ascending=False)

    st.header("Resumo Consumo Médio por Veículo")
    st.dataframe(resumo.style.format({
        'km_min': '{:,.0f}',
        'km_max': '{:,.0f}',
        'litros_totais': '{:,.2f}',
        'km_rodados': '{:,.0f}',
        'consumo_medio_km_por_litro': '{:.2f}'
    }))

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
