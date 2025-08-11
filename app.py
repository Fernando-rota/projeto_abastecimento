import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Dashboard Consumo e Abastecimento", layout="wide")
st.title("📊 Dashboard Consumo e Abastecimento de Veículos")

@st.cache_data
def load_data(file_path):
    interno = pd.read_excel(file_path, sheet_name='interno')
    externo = pd.read_excel(file_path, sheet_name='externo')
    consumo = pd.read_excel(file_path, sheet_name='consumo')

    # Padronizar colunas
    for df in [interno, externo, consumo]:
        df.rename(columns=lambda x: x.strip().lower().replace(' ', '_'), inplace=True)
    
    # Converter datas
    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')
    consumo['data'] = pd.to_datetime(consumo['data'], errors='coerce')

    # Remover linhas com data inválida
    interno.dropna(subset=['data'], inplace=True)
    externo.dropna(subset=['data'], inplace=True)
    consumo.dropna(subset=['data'], inplace=True)

    return interno, externo, consumo

uploaded_file = st.file_uploader("📁 Carregue sua planilha Excel com abas: interno, externo, consumo", type=['xlsx'])
if uploaded_file:
    interno, externo, consumo = load_data(uploaded_file)

    st.sidebar.header("Filtros")

    # Datas para filtro geral - mínimo e máximo de todas as abas
    datas = pd.concat([interno['data'], externo['data'], consumo['data']])
    min_date, max_date = datas.min(), datas.max()
    date_range = st.sidebar.date_input("Período", [min_date, max_date])

    # Placas para filtro (interno + externo)
    placas_interno = interno['placa'].dropna().unique()
    placas_externo = externo['placa'].dropna().unique()
    placas_consumo = consumo['placa'].dropna().unique()
    placas = sorted(set(placas_interno) | set(placas_externo) | set(placas_consumo))
    placas_selected = st.sidebar.multiselect("Selecione Placa(s)", placas, default=placas)

    # Combustíveis para filtro (interno + externo)
    combust_interno = interno['tipo'].dropna().unique() if 'tipo' in interno.columns else []
    combust_externo = externo['tipo_combustivel'].dropna().unique() if 'tipo_combustivel' in externo.columns else []
    combustiveis = sorted(set(combust_interno) | set(combust_externo))
    combustiveis_selected = st.sidebar.multiselect("Tipo de Combustível", combustiveis, default=combustiveis)

    # Filtrar datas
    data_start, data_end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    interno_filt = interno[(interno['data'] >= data_start) & (interno['data'] <= data_end)]
    externo_filt = externo[(externo['data'] >= data_start) & (externo['data'] <= data_end)]
    consumo_filt = consumo[(consumo['data'] >= data_start) & (consumo['data'] <= data_end)]

    # Filtrar placas
    interno_filt = interno_filt[interno_filt['placa'].isin(placas_selected)]
    externo_filt = externo_filt[externo_filt['placa'].isin(placas_selected)]
    consumo_filt = consumo_filt[consumo_filt['placa'].isin(placas_selected)]

    # Filtrar combustíveis
    if 'tipo' in interno_filt.columns:
        interno_filt = interno_filt[interno_filt['tipo'].isin(combustiveis_selected)]
    if 'tipo_combustivel' in externo_filt.columns:
        externo_filt = externo_filt[externo_filt['tipo_combustivel'].isin(combustiveis_selected)]

    # --- Indicadores com interno + externo para consumo médio ---

    interno_filt = interno_filt.rename(columns={'quantidade_de_litros': 'litros', 'km_atual': 'km', 'tipo': 'combustivel'})
    externo_filt = externo_filt.rename(columns={'quantidade_de_litros': 'litros', 'km_atual': 'km', 'tipo_combustivel': 'combustivel'})

    cols_needed = ['data', 'placa', 'combustivel', 'litros', 'km']
    interno_sel = interno_filt[cols_needed]
    externo_sel = externo_filt[cols_needed]

    abastecimentos = pd.concat([interno_sel, externo_sel], ignore_index=True)

    # Ajustar vírgulas e converter para numérico
    abastecimentos['km'] = abastecimentos['km'].astype(str).str.replace(',', '.', regex=False)
    abastecimentos['litros'] = abastecimentos['litros'].astype(str).str.replace(',', '.', regex=False)
    abastecimentos['km'] = pd.to_numeric(abastecimentos['km'], errors='coerce')
    abastecimentos['litros'] = pd.to_numeric(abastecimentos['litros'], errors='coerce')

    abastecimentos.dropna(subset=['km', 'litros'], inplace=True)

    resumo_consumo = abastecimentos.groupby('placa').agg(
        km_min=('km', 'min'),
        km_max=('km', 'max'),
        litros_totais=('litros', 'sum')
    ).reset_index()

    resumo_consumo['km_rodados'] = resumo_consumo['km_max'] - resumo_consumo['km_min']
    resumo_consumo['consumo_medio_km_por_litro'] = resumo_consumo.apply(
        lambda row: row['km_rodados'] / row['litros_totais'] if row['litros_totais'] > 0 else None,
        axis=1
    )

    resumo_consumo = resumo_consumo.sort_values('consumo_medio_km_por_litro', ascending=False)

    st.header("🚛 Consumo Médio por Veículo (Interno + Externo)")
    st.dataframe(resumo_consumo.style.format({
        'km_min': '{:,.0f}',
        'km_max': '{:,.0f}',
        'litros_totais': '{:,.2f}',
        'km_rodados': '{:,.0f}',
        'consumo_medio_km_por_litro': '{:.2f}'
    }))

    fig1 = px.bar(resumo_consumo, x='placa', y='consumo_medio_km_por_litro',
                  labels={'consumo_medio_km_por_litro': 'Km por Litro', 'placa': 'Placa'},
                  title='Consumo Médio (Km por Litro) por Veículo')
    st.plotly_chart(fig1, use_container_width=True)

    # --- Indicadores da aba consumo (exemplo) ---

    # Converter litros e km para numérico, tratar vírgula
    consumo_filt['qtd_litros'] = consumo_filt['qtd_litros'].astype(str).str.replace(',', '.', regex=False)
    consumo_filt['km'] = consumo_filt['km'].astype(str).str.replace(',', '.', regex=False)
    consumo_filt['qtd_litros'] = pd.to_numeric(consumo_filt['qtd_litros'], errors='coerce')
    consumo_filt['km'] = pd.to_numeric(consumo_filt['km'], errors='coerce')

    consumo_filt.dropna(subset=['qtd_litros', 'km'], inplace=True)

    resumo_consumo_ab = consumo_filt.groupby('placa').agg(
        total_litros_consumo=('qtd_litros', 'sum'),
        media_km_consumo=('km', 'mean'),
        registros=('data', 'count')
    ).reset_index()

    st.header("⛽ Indicadores da aba Consumo")
    st.dataframe(resumo_consumo_ab.style.format({
        'total_litros_consumo': '{:,.2f}',
        'media_km_consumo': '{:,.0f}',
        'registros': '{:,.0f}'
    }))

    fig2 = px.bar(resumo_consumo_ab, x='placa', y='total_litros_consumo',
                  labels={'total_litros_consumo': 'Total Litros', 'placa': 'Placa'},
                  title='Total de Litros Consumidos por Veículo (Aba Consumo)')
    st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("Faça upload da planilha Excel para começar.")
