import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="BI Abastecimento Frota", layout="wide")
st.title("📊 BI Abastecimento - Interno e Externo")

@st.cache_data
def load_data(file_path):
    interno = pd.read_excel(file_path, sheet_name='interno')
    externo = pd.read_excel(file_path, sheet_name='externo')

    # Padronizar nomes (minusculo, sem espaços, com _)
    interno.columns = interno.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('ú', 'u')
    externo.columns = externo.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('ú', 'u')

    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')

    interno.dropna(subset=['data'], inplace=True)
    externo.dropna(subset=['data'], inplace=True)

    return interno, externo

def preprocess_abastecimentos(df, litros_col, km_col, combust_col=None, combust_default=None):
    # Renomear colunas importantes para padrão interno
    rename_map = {
        litros_col: 'litros',
        km_col: 'km',
    }
    if combust_col and combust_col in df.columns:
        rename_map[combust_col] = 'combustivel'
    df = df.rename(columns=rename_map)

    df['km'] = df['km'].astype(str).str.replace(',', '.', regex=False)
    df['litros'] = df['litros'].astype(str).str.replace(',', '.', regex=False)
    df['km'] = pd.to_numeric(df['km'], errors='coerce')
    df['litros'] = pd.to_numeric(df['litros'], errors='coerce')

    if combust_col not in df.columns and combust_default:
        df['combustivel'] = combust_default

    df = df.dropna(subset=['km', 'litros', 'placa'])
    return df[['data', 'placa', 'combustivel', 'litros', 'km']]

uploaded_file = st.file_uploader("📁 Carregue sua planilha Excel com abas: interno e externo", type=['xlsx'])
if uploaded_file:
    interno, externo = load_data(uploaded_file)

    st.sidebar.header("Filtros Globais")

    placas_unicas = sorted(set(interno['placa'].dropna().unique()) | set(externo['placa'].dropna().unique()))
    placas_selected = st.sidebar.multiselect("Placas", placas_unicas, default=placas_unicas)

    # Combustível: no interno temos coluna 'tipo', no externo usaremos 'descrição_despesa' como tipo combustível
    combust_interno = interno['tipo'].dropna().unique() if 'tipo' in interno.columns else []
    combust_externo = externo['descrição_despesa'].dropna().unique() if 'descrição_despesa' in externo.columns else []
    combust_unificados = sorted(set(combust_interno) | set(combust_externo))
    combust_selected = st.sidebar.multiselect("Tipo Combustível", combust_unificados, default=combust_unificados)

    data_min = min(interno['data'].min(), externo['data'].min())
    data_max = max(interno['data'].max(), externo['data'].max())
    data_range = st.sidebar.date_input("Período", [data_min, data_max])

    data_start, data_end = pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])

    interno_filt = interno[
        (interno['placa'].isin(placas_selected)) &
        (interno['data'] >= data_start) & (interno['data'] <= data_end)
    ]
    externo_filt = externo[
        (externo['placa'].isin(placas_selected)) &
        (externo['data'] >= data_start) & (externo['data'] <= data_end)
    ]

    if 'tipo' in interno_filt.columns:
        interno_filt = interno_filt[interno_filt['tipo'].isin(combust_selected)]
    if 'descrição_despesa' in externo_filt.columns:
        externo_filt = externo_filt[externo_filt['descrição_despesa'].isin(combust_selected)]

    interno_proc = preprocess_abastecimentos(interno_filt, 'quantidade_de_litros', 'km_atual', combust_col='tipo')
    externo_proc = preprocess_abastecimentos(externo_filt, 'quantidade_de_litros', 'km_atual', combust_col='descrição_despesa')

    abastecimentos = pd.concat([interno_proc, externo_proc], ignore_index=True)

    resumo_ab = abastecimentos.groupby('placa').agg(
        total_litros=('litros', 'sum'),
        media_km=('km', 'mean'),
        registros=('data', 'count')
    ).reset_index()

    resumo_ab = resumo_ab.sort_values('total_litros', ascending=False)

    st.header("⛽ Indicadores Abastecimento Interno + Externo")
    st.dataframe(resumo_ab.style.format({
        'total_litros': '{:,.2f}',
        'media_km': '{:,.0f}',
        'registros': '{:,.0f}'
    }))

    fig = px.bar(resumo_ab, x='placa', y='total_litros',
                 labels={'total_litros': 'Total Litros', 'placa': 'Placa'},
                 title='Total de Litros Consumidos por Veículo')
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Faça upload da planilha Excel para começar.")
