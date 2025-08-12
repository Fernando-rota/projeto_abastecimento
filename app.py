import streamlit as st
import pandas as pd
import plotly.express as px

@st.cache_data(show_spinner=True)
def carregar_dados(arquivo):
    """Lê as abas do Excel e retorna dois DataFrames."""
    try:
        df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
        df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')
        return df_interno, df_externo
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
        return None, None

def limpa_monetario(col):
    """Remove o símbolo R$ e converte para float."""
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True), errors='coerce')

def processa_abastecimento(df, interno=True):
    """Limpa e prepara o DataFrame de abastecimento."""
    colunas_esperadas = ['Data', 'Quantidade de litros', 'Valor Total', 'Valor Unitario', 'KM Atual']
    for c in colunas_esperadas:
        if c not in df.columns:
            st.warning(f"Atenção: coluna '{c}' não encontrada na planilha.")
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    df['AnoMes'] = df['Data'].dt.to_period('M').astype(str)
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    if 'Valor Total' in df.columns:
        df['Valor Total'] = pd.to_numeric(df['Valor Total'], errors='coerce')
    if 'Valor Unitario' in df.columns:
        df['Valor Unitario'] = limpa_monetario(df['Valor Unitario'])
    df['KM Atual'] = pd.to_numeric(df['KM Atual'], errors='coerce')
    df['Origem'] = 'Interno' if interno else 'Externo'
    if interno and 'Tipo' in df.columns:
        df = df[df['Tipo'].str.lower() == 'entrada']
    return df

def calcula_autonomia(df):
    """Calcula autonomia (km/L) para cada veículo."""
    autonomia = {}
    for placa, grupo in df.groupby('Placa'):
        km_max = grupo['KM Atual'].max()
        km_min = grupo['KM Atual'].min()
        litros = grupo['Quantidade de litros'].sum()
        if pd.notna(km_max) and pd.notna(km_min) and litros > 0:
            autonomia[placa] = (km_max - km_min) / litros
        else:
            autonomia[placa] = None
    return autonomia

def filtra_dados(df, placa_sel, ano_mes_sel, origem_sel, data_inicio, data_fim):
    """Aplica filtros selecionados no DataFrame."""
    df_filtrado = df.copy()
    if placa_sel != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Placa'] == placa_sel]
    if ano_mes_sel != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['AnoMes'] == ano_mes_sel]
    if origem_sel != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Origem'] == origem_sel]
    df_filtrado = df_filtrado[(df_filtrado['Data'] >= pd.to_datetime(data_inicio)) & (df_filtrado['Data'] <= pd.to_datetime(data_fim))]
    return df_filtrado

def main():
    st.title("🚛 Dashboard Avançado de Abastecimento")

    arquivo = st.sidebar.file_uploader("Upload da planilha Excel com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xlsx'])
    if arquivo is None:
        st.warning("Faça upload do arquivo para continuar.")
        return

    df_interno, df_externo = carregar_dados(arquivo)
    if df_interno is None or df_externo is None:
        return

    df_interno = processa_abastecimento(df_interno, interno=True)
    df_externo = processa_abastecimento(df_externo, interno=False)

    df = pd.concat([df_interno, df_externo], ignore_index=True)
    df = df.dropna(subset=['Placa', 'Quantidade de litros', 'Data'])

    # Filtros disponíveis
    placas = ['Todas'] + sorted(df['Placa'].dropna().unique())
    anos_meses = ['Todos'] + sorted(df['AnoMes'].unique())
    origens = ['Todos', 'Interno', 'Externo']

    st.sidebar.header("Filtros Globais")
    placa_sel = st.sidebar.selectbox("Placa", placas)
    ano_mes_sel = st.sidebar.selectbox("Mês (AAAA-MM)", anos_meses)
    origem_sel = st.sidebar.selectbox("Origem do abastecimento", origens)

    data_min = df['Data'].min().date()
    data_max = df['Data'].max().date()
    data_inicio, data_fim = st.sidebar.date_input("Período", [data_min, data_max], min_value=data_min, max_value=data_max)

    df_filtrado = filtra_dados(df, placa_sel, ano_mes_sel, origem_sel, data_inicio, data_fim)

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros aplicados.")
        return

    litros_totais = df_filtrado['Quantidade de litros'].sum()
    valor_total = df_filtrado['Valor Total'].sum()
    preco_medio = valor_total / litros_totais if litros_totais > 0 else 0

    autonomia_dict = calcula_autonomia(df_filtrado)
    autonomia_df = pd.DataFrame([
        {'Placa': placa, 'Autonomia (km/L)': val if val is not None else None}
        for placa, val in autonomia_dict.items()
    ]).sort_values(by='Autonomia (km/L)', ascending=False)

    autonomia_df["Autonomia (km/L)"] = autonomia_df["Autonomia (km/L)"].apply(
        lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A"
    ).reset_index(drop=True)

    litros_mes_origem = df_filtrado.groupby(['AnoMes', 'Origem']).agg({'Quantidade de litros': 'sum'}).reset_index()
    preco_mes_origem = df_filtrado.groupby(['AnoMes', 'Origem']).apply(
        lambda x: x['Valor Total'].sum() / x['Quantidade de litros'].sum() if x['Quantidade de litros'].sum() > 0 else 0
    ).reset_index(name='Preco Medio')

    tab1, tab2, tab3 = st.tabs(["Indicadores Gerais", "Autonomia por Veículo", "Gráficos"])

    with tab1:
        st.header("📊 Indicadores Gerais")
        c1, c2, c3 = st.columns(3)
        c1.metric("Litros Totais", f"{litros_totais:,.2f} L")
        c2.metric("Valor Total Gasto", f"R$ {valor_total:,.2f}")
        c3.metric("Preço Médio por Litro", f"R$ {preco_medio:,.3f} / L")

    with tab2:
        st.header("🚙 Autonomia por Veículo")
        st.dataframe(autonomia_df)

    with tab3:
        st.header("📈 Litros Mensais por Origem")
        fig1 = px.bar(litros_mes_origem, x='AnoMes', y='Quantidade de litros', color='Origem',
                      barmode='group', labels={'AnoMes': 'Mês', 'Quantidade de litros': 'Litros'},
                      title='Litros Mensais - Interno x Externo')
        st.plotly_chart(fig1, use_container_width=True)

        st.header("📈 Preço Médio Mensal por Origem")
        fig2 = px.line(preco_mes_origem, x='AnoMes', y='Preco Medio', color='Origem',
                       markers=True, labels={'AnoMes': 'Mês', 'Preco Medio': 'R$ / Litro'},
                       title='Preço Médio Mensal - Interno x Externo')
        st.plotly_chart(fig2, use_container_width=True)

    # Sugestões extras
    st.sidebar.markdown("---")
    st.sidebar.header("O que mais posso fazer?")
    st.sidebar.markdown("""
    - Filtragem avançada por fornecedor, posto ou motorista
    - Alertas de consumo anormal ou custos elevados
    - Exportação de relatórios CSV/PDF
    - Dashboards históricos para comparação anual
    """)

if __name__ == "__main__":
    main()
