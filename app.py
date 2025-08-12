import streamlit as st
import pandas as pd
import plotly.express as px

def limpar_valor(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, str):
        return float(valor.replace('R$', '').replace('.', '').replace(',', '.').strip())
    try:
        return float(valor)
    except:
        return None

@st.cache_data
def carregar_dados(arquivo):
    df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
    df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')
    
    # Limpar datas
    df_interno['Data'] = pd.to_datetime(df_interno['Data'], errors='coerce')
    df_externo['Data'] = pd.to_datetime(df_externo['Data'], errors='coerce')
    
    # Remover placas inválidas
    invalidas = ['-', 'correção']
    df_interno = df_interno[~df_interno['Placa'].astype(str).str.lower().isin(invalidas)]
    df_externo = df_externo[~df_externo['Placa'].astype(str).str.lower().isin(invalidas)]
    
    # Converter colunas numéricas
    df_interno['Quantidade de litros'] = pd.to_numeric(df_interno['Quantidade de litros'], errors='coerce').fillna(0)
    df_interno['KM Atual'] = pd.to_numeric(df_interno['KM Atual'], errors='coerce')
    df_interno['Valor Unitario'] = df_interno['Valor Unitario'].apply(limpar_valor)
    df_interno['Valor Total'] = df_interno['Valor Total'].apply(limpar_valor)
    df_interno['Tipo'] = df_interno['Tipo'].astype(str).str.upper().str.strip()
    df_interno['Placa'] = df_interno['Placa'].astype(str).str.upper().str.strip()
    
    df_externo['Quantidade de litros'] = pd.to_numeric(df_externo['Quantidade de litros'], errors='coerce').fillna(0)
    df_externo['KM Atual'] = pd.to_numeric(df_externo['KM Atual'], errors='coerce')
    df_externo['Valor Unitario'] = df_externo['Valor Unitario'].apply(limpar_valor)
    df_externo['Valor Total'] = df_externo['Valor Total'].apply(limpar_valor)
    df_externo['Placa'] = df_externo['Placa'].astype(str).str.upper().str.strip()
    
    # Tipo combustível externo (se existir coluna) - se não, usa Descrição Despesa
    if 'Tipo Combustivel' in df_externo.columns:
        df_externo['Tipo'] = df_externo['Tipo Combustivel'].astype(str).str.upper().str.strip()
    elif 'Descrição Despesa' in df_externo.columns:
        df_externo['Tipo'] = df_externo['Descrição Despesa'].astype(str).str.upper().str.strip()
    else:
        df_externo['Tipo'] = ''
    
    return df_interno, df_externo

def consumo_medio(df_interno, df_externo, filtro_placa=None):
    df_km = pd.concat([
        df_interno[['Placa', 'KM Atual']],
        df_externo[['Placa', 'KM Atual']]
    ], ignore_index=True)
    if filtro_placa and filtro_placa != 'Todas':
        df_km = df_km[df_km['Placa'] == filtro_placa]
    resultado = []
    for placa, grupo in df_km.groupby('Placa'):
        km_max = grupo['KM Atual'].max()
        km_min = grupo['KM Atual'].min()
        km_rodado = km_max - km_min if pd.notna(km_max) and pd.notna(km_min) else 0
        resultado.append({'Placa': placa, 'KM Rodado': km_rodado})
    return pd.DataFrame(resultado).sort_values('KM Rodado', ascending=False)

def preco_medio_ponderado(df, mes_min=7, filtro_placa=None, filtro_tipo=None):
    df = df.copy()
    df = df[df['Data'].dt.month >= mes_min]
    if filtro_placa and filtro_placa != 'Todas':
        df = df[df['Placa'] == filtro_placa]
    if filtro_tipo and filtro_tipo != 'Todos':
        df = df[df['Tipo'] == filtro_tipo]
    df = df.dropna(subset=['Valor Unitario', 'Quantidade de litros'])
    df = df[df['Quantidade de litros'] > 0]
    if df.empty:
        return pd.DataFrame(columns=['Periodo','Litros','Preco Medio (R$/L)','Custo Total (R$)'])
    grouped = df.groupby(df['Data'].dt.to_period('M')).apply(
        lambda x: pd.Series({
            'Litros': x['Quantidade de litros'].sum(),
            'Preco Medio (R$/L)': (x['Valor Unitario'] * x['Quantidade de litros']).sum() / x['Quantidade de litros'].sum(),
            'Custo Total (R$)': (x['Valor Unitario'] * x['Quantidade de litros']).sum()
        })
    ).reset_index().rename(columns={'Data': 'Periodo'})
    grouped['Periodo'] = grouped['Periodo'].dt.to_timestamp()
    return grouped.sort_values('Periodo')

def indicadores_mensais(df_interno, df_externo, filtro_placa=None, filtro_tipo=None, filtro_mes_ano=None):
    # Filtro placas e tipo
    df_interno_f = df_interno.copy()
    df_externo_f = df_externo.copy()
    
    if filtro_placa and filtro_placa != 'Todas':
        df_interno_f = df_interno_f[df_interno_f['Placa'] == filtro_placa]
        df_externo_f = df_externo_f[df_externo_f['Placa'] == filtro_placa]
    if filtro_tipo and filtro_tipo != 'Todos':
        df_interno_f = df_interno_f[df_interno_f['Tipo'] == filtro_tipo]
        df_externo_f = df_externo_f[df_externo_f['Tipo'] == filtro_tipo]
    if filtro_mes_ano:
        df_interno_f = df_interno_f[df_interno_f['Data'].dt.to_period('M') == filtro_mes_ano]
        df_externo_f = df_externo_f[df_externo_f['Data'].dt.to_period('M') == filtro_mes_ano]
    
    def agrega(df, label):
        grouped = df.groupby(df['Data'].dt.to_period('M')).agg({
            'Quantidade de litros':'sum',
            'Valor Total':'sum'
        }).rename(columns={
            'Quantidade de litros': f'Litros {label}',
            'Valor Total': f'Custo {label}'
        })
        return grouped
    
    interno_agg = agrega(df_interno_f, 'Interno')
    externo_agg = agrega(df_externo_f, 'Externo')
    df_result = interno_agg.join(externo_agg, how='outer').fillna(0)
    df_result.index = df_result.index.to_timestamp()
    return df_result.sort_index()

def main():
    st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")
    st.title("📊 Dashboard de Abastecimento Interno x Externo")

    st.sidebar.header("Upload do arquivo Excel")
    arquivo = st.sidebar.file_uploader("Faça upload da planilha com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xls', 'xlsx'])
    
    if not arquivo:
        st.info("Por favor, faça upload do arquivo para visualizar os indicadores.")
        return

    df_interno, df_externo = carregar_dados(arquivo)

    # Filtros disponíveis
    placas = sorted(set(df_interno['Placa'].unique()).union(set(df_externo['Placa'].unique())))
    placas = ['Todas'] + placas
    tipos_combustivel = sorted(set(df_interno['Tipo'].unique()).union(set(df_externo['Tipo'].unique())))
    tipos_combustivel = ['Todos'] + tipos_combustivel

    anos_meses = pd.concat([df_interno['Data'], df_externo['Data']]).dropna()
    anos_meses = sorted(anos_meses.dt.to_period('M').unique())
    anos_meses_display = [period.strftime('%Y-%m') for period in anos_meses]
    anos_meses_display = ['Todos'] + anos_meses_display

    with st.sidebar:
        filtro_placa = st.selectbox("Filtrar por Placa", placas)
        filtro_tipo = st.selectbox("Filtrar por Tipo Combustível", tipos_combustivel)
        filtro_mes_ano = st.selectbox("Filtrar por Mês/Ano", anos_meses_display)

    # Ajusta filtro mes/ano
    if filtro_mes_ano == 'Todos':
        filtro_mes_ano = None
    else:
        filtro_mes_ano = pd.Period(filtro_mes_ano)

    # === Abas ===
    aba1, aba2, aba3 = st.tabs(["📌 Consumo Médio", "⛽ Preço Médio Ponderado", "📅 Indicadores Mensais"])

    with aba1:
        st.subheader("Consumo Médio por Placa (KM Rodado)")
        df_consumo = consumo_medio(df_interno, df_externo, filtro_placa)
        st.dataframe(df_consumo, use_container_width=True)

    with aba2:
        st.subheader("Preço Médio Ponderado - Interno (a partir de Julho)")
        preco_interno = preco_medio_ponderado(df_interno, 7, filtro_placa, filtro_tipo)
        st.dataframe(preco_interno, use_container_width=True)

        st.subheader("Preço Médio Ponderado - Externo (a partir de Julho)")
        preco_externo = preco_medio_ponderado(df_externo, 7, filtro_placa, filtro_tipo)
        st.dataframe(preco_externo, use_container_width=True)

        if not preco_interno.empty or not preco_externo.empty:
            fig = px.line(
                pd.concat([
                    preco_interno.assign(Tipo="Interno"),
                    preco_externo.assign(Tipo="Externo")
                ]),
                x="Periodo", y="Preco Medio (R$/L)", color="Tipo", markers=True,
                title="Preço Médio Ponderado do Combustível (Mensal)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Sem dados para gráfico de preço médio.")

    with aba3:
        st.subheader("Litros e Custos Mensais - Interno x Externo")
        indicadores = indicadores_mensais(df_interno, df_externo, filtro_placa, filtro_tipo, filtro_mes_ano)
        if indicadores.empty:
            st.write("Sem dados para os indicadores mensais.")
        else:
            fig_litros = px.bar(indicadores.reset_index(), x='Data', y=['Litros Interno', 'Litros Externo'], barmode='group', title="Litros Abastecidos por Mês")
            fig_custos = px.bar(indicadores.reset_index(), x='Data', y=['Custo Interno', 'Custo Externo'], barmode='group', title="Custo Total por Mês")
            st.plotly_chart(fig_litros, use_container_width=True)
            st.plotly_chart(fig_custos, use_container_width=True)

if __name__ == "__main__":
    main()
