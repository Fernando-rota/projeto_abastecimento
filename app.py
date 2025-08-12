import streamlit as st
import pandas as pd
import plotly.express as px

def limpa_monetario(col):
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True), errors='coerce')

def processa_abastecimento(df, interno=True):
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

def main():
    st.title("🚛 Dashboard Avançado de Abastecimento")

    arquivo = st.sidebar.file_uploader("Upload da planilha Excel com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xlsx'])
    if arquivo is None:
        st.warning("Faça upload do arquivo para continuar.")
        return

    df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
    df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')

    df_interno = processa_abastecimento(df_interno, interno=True)
    df_externo = processa_abastecimento(df_externo, interno=False)

    df = pd.concat([df_interno, df_externo], ignore_index=True)
    df = df.dropna(subset=['Placa', 'Quantidade de litros', 'Data'])

    # Filtros globais
    placas = ['Todas'] + sorted(df['Placa'].dropna().unique())
    anos_meses = ['Todos'] + sorted(df['AnoMes'].unique())

    st.sidebar.header("Filtros Globais")
    placa_sel = st.sidebar.selectbox("Placa", placas)
    ano_mes_sel = st.sidebar.selectbox("Mês (AAAA-MM)", anos_meses)

    df_filtrado = df.copy()
    if placa_sel != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Placa'] == placa_sel]
    if ano_mes_sel != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['AnoMes'] == ano_mes_sel]

    # Indicadores gerais
    litros_totais = df_filtrado['Quantidade de litros'].sum()
    valor_total = df_filtrado['Valor Total'].sum()
    preco_medio = valor_total / litros_totais if litros_totais > 0 else 0

    autonomia_dict = calcula_autonomia(df_filtrado)
    autonomia_df = pd.DataFrame([
        {'Placa': placa, 'Autonomia (km/L)': val if val is not None else None}
        for placa, val in autonomia_dict.items()
    ])
    autonomia_df = autonomia_df.sort_values(by='Autonomia (km/L)', ascending=False)

    # Agrupamentos para gráficos
    litros_mes_origem = df_filtrado.groupby(['AnoMes', 'Origem']).agg({'Quantidade de litros': 'sum'}).reset_index()
    preco_mes_origem = df_filtrado.groupby(['AnoMes', 'Origem']).apply(
        lambda x: x['Valor Total'].sum() / x['Quantidade de litros'].sum() if x['Quantidade de litros'].sum() > 0 else 0
    ).reset_index(name='Preco Medio')

    # Organização em abas
    tab1, tab2, tab3 = st.tabs(["Indicadores Gerais", "Autonomia por Veículo", "Gráficos"])

    with tab1:
        st.header("📊 Indicadores Gerais")
        c1, c2, c3 = st.columns(3)
        c1.metric("Litros Totais", f"{litros_totais:.2f} L")
        c2.metric("Valor Total Gasto", f"R$ {valor_total:.2f}")
        c3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f} / L")

    with tab2:
        st.header("🚙 Autonomia por Veículo")
        st.dataframe(autonomia_df.style.format({"Autonomia (km/L)": "{:.3f}"}).hide_index())

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

    # O que mais pode ser feito:
    st.sidebar.markdown("---")
    st.sidebar.header("O que mais posso fazer?")
    st.sidebar.markdown("""
    - Filtragem por período customizado (datas específicas)
    - Indicadores de consumo médio por veículo e por tipo de combustível
    - Alertas de consumo anormal ou custos elevados
    - Exportação de relatórios em CSV/PDF
    - Integração com dados de manutenção para cruzar custos
    - Dashboards históricos para comparação anual
    - Detalhamento por posto, fornecedor e motorista
    """)

if __name__ == "__main__":
    main()
