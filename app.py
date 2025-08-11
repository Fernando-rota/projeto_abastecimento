import streamlit as st
import pandas as pd
import plotly.express as px

def limpar_valor(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, str):
        return float(valor.replace('R$', '').replace('.', '').replace(',', '.').strip())
    return float(valor)

def carregar_dados(arquivo):
    df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
    df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')

    df_interno['Data'] = pd.to_datetime(df_interno['Data'], dayfirst=True, errors='coerce')
    df_interno['Quantidade de litros'] = pd.to_numeric(df_interno['Quantidade de litros'], errors='coerce').fillna(0)
    df_interno['Valor Unitario'] = df_interno['Valor Unitario'].apply(limpar_valor)
    df_interno['Valor Total'] = df_interno['Valor Total'].apply(limpar_valor)
    df_interno['Placa'] = df_interno['Placa'].astype(str).str.strip().str.upper()
    df_interno['Descrição Despesa'] = df_interno['Descrição Despesa'].astype(str).str.strip().str.upper()
    df_interno['KM Atual'] = pd.to_numeric(df_interno['KM Atual'], errors='coerce')

    df_externo['Data'] = pd.to_datetime(df_externo['Data'], dayfirst=True, errors='coerce')
    df_externo['Quantidade de litros'] = df_externo['Quantidade de litros'].astype(str).str.replace(',', '.').astype(float)
    df_externo['Valor Unitario'] = df_externo['Valor Unitario'].apply(limpar_valor)
    df_externo['Valor Total'] = df_externo['Valor Total'].apply(limpar_valor)
    df_externo['Placa'] = df_externo['Placa'].astype(str).str.strip().str.upper()
    df_externo['Descrição Despesa'] = df_externo['Descrição Despesa'].astype(str).str.strip().str.upper()
    df_externo['KM Atual'] = pd.to_numeric(df_externo['KM Atual'], errors='coerce')

    return df_interno, df_externo

def calcula_consumo_medio(df_interno, df_externo):
    df_combined = pd.concat([df_interno[['Placa', 'KM Atual', 'Quantidade de litros']],
                             df_externo[['Placa', 'KM Atual', 'Quantidade de litros']]])

    placas_invalidas = ['-', 'CORREÇÃO']
    df_combined = df_combined[~df_combined['Placa'].isin(placas_invalidas)]

    consumo = df_combined.groupby('Placa').agg(
        km_min=('KM Atual', 'min'),
        km_max=('KM Atual', 'max'),
        litros_total=('Quantidade de litros', 'sum')
    ).reset_index()

    consumo['Consumo Médio (km/l)'] = (consumo['km_max'] - consumo['km_min']) / consumo['litros_total']
    consumo['Consumo Médio (km/l)'] = consumo['Consumo Médio (km/l)'].round(2)

    # Ordenar do maior para o menor consumo médio
    consumo = consumo.sort_values(by='Consumo Médio (km/l)', ascending=False).reset_index(drop=True)

    return consumo

def indicadores_mensais(df_interno, df_externo):
    # Criar coluna ano-mes
    df_interno['Ano-Mes'] = df_interno['Data'].dt.to_period('M').astype(str)
    df_externo['Ano-Mes'] = df_externo['Data'].dt.to_period('M').astype(str)

    placas_invalidas = ['-', 'CORREÇÃO']
    df_interno = df_interno[~df_interno['Placa'].isin(placas_invalidas)]
    df_externo = df_externo[~df_externo['Placa'].isin(placas_invalidas)]

    # Agrupamento litros e valor total por mês e origem
    interno_agg = df_interno.groupby('Ano-Mes').agg(
        litros_interno=('Quantidade de litros', 'sum'),
        valor_interno=('Valor Total', 'sum')
    ).reset_index()

    externo_agg = df_externo.groupby('Ano-Mes').agg(
        litros_externo=('Quantidade de litros', 'sum'),
        valor_externo=('Valor Total', 'sum')
    ).reset_index()

    # Combinar
    mensal = pd.merge(interno_agg, externo_agg, on='Ano-Mes', how='outer').fillna(0)

    # Preço médio por mês (valor total / litros)
    mensal['Preço Médio Interno (R$/L)'] = mensal.apply(lambda row: (row['valor_interno'] / row['litros_interno']) if row['litros_interno'] > 0 else 0, axis=1)
    mensal['Preço Médio Externo (R$/L)'] = mensal.apply(lambda row: (row['valor_externo'] / row['litros_externo']) if row['litros_externo'] > 0 else 0, axis=1)

    return mensal

def main():
    st.title("Dashboard Abastecimento Interno x Externo com Indicadores Mensais")

    st.sidebar.header("Upload da planilha Excel")
    arquivo = st.sidebar.file_uploader("Envie a planilha com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xls', 'xlsx'])

    if arquivo:
        df_interno, df_externo = carregar_dados(arquivo)

        placas_invalidas = ['-', 'CORREÇÃO']
        df_interno = df_interno[~df_interno['Placa'].isin(placas_invalidas)]
        df_externo = df_externo[~df_externo['Placa'].isin(placas_invalidas)]

        placas = sorted(set(df_interno['Placa'].unique()) | set(df_externo['Placa'].unique()))
        combustiveis = sorted(set(df_interno['Descrição Despesa'].unique()) | set(df_externo['Descrição Despesa'].unique()))

        placa_selecionada = st.sidebar.selectbox("Filtrar por placa", ['Todas'] + placas)
        combustivel_selecionado = st.sidebar.selectbox("Filtrar por combustível", ['Todos'] + combustiveis)

        data_min = min(df_interno['Data'].min(), df_externo['Data'].min())
        data_max = max(df_interno['Data'].max(), df_externo['Data'].max())
        periodo = st.sidebar.date_input("Filtrar por período", [data_min, data_max])

        if placa_selecionada != 'Todas':
            df_interno = df_interno[df_interno['Placa'] == placa_selecionada]
            df_externo = df_externo[df_externo['Placa'] == placa_selecionada]

        if combustivel_selecionado != 'Todos':
            df_interno = df_interno[df_interno['Descrição Despesa'] == combustivel_selecionado]
            df_externo = df_externo[df_externo['Descrição Despesa'] == combustivel_selecionado]

        if len(periodo) == 2:
            data_start, data_end = pd.to_datetime(periodo[0]), pd.to_datetime(periodo[1])
            df_interno = df_interno[(df_interno['Data'] >= data_start) & (df_interno['Data'] <= data_end)]
            df_externo = df_externo[(df_externo['Data'] >= data_start) & (df_externo['Data'] <= data_end)]

        st.subheader("Indicadores Gerais")
        litros_interno = df_interno['Quantidade de litros'].sum()
        valor_interno = df_interno['Valor Total'].sum()
        custo_medio_interno = valor_interno / litros_interno if litros_interno > 0 else 0

        litros_externo = df_externo['Quantidade de litros'].sum()
        valor_externo = df_externo['Valor Total'].sum()
        custo_medio_externo = valor_externo / litros_externo if litros_externo > 0 else 0

        col1, col2 = st.columns(2)
        col1.metric("Litros Internos", f"{litros_interno:.2f} L")
        col1.metric("Custo Médio Interno (R$/L)", f"R$ {custo_medio_interno:.2f}")

        col2.metric("Litros Externos", f"{litros_externo:.2f} L")
        col2.metric("Custo Médio Externo (R$/L)", f"R$ {custo_medio_externo:.2f}")

        st.subheader("Consumo Médio por Placa (km/l)")
        consumo = calcula_consumo_medio(df_interno, df_externo)
        if placa_selecionada != 'Todas':
            consumo = consumo[consumo['Placa'] == placa_selecionada]
        st.dataframe(consumo)

        # Indicadores mensais
        st.subheader("Abastecimento Interno x Externo - Litros e Valores Mensais")
        mensal = indicadores_mensais(df_interno, df_externo)
        st.dataframe(mensal)

        # Gráficos de litros mensais
        fig_litros = px.bar(mensal.melt(id_vars='Ano-Mes', value_vars=['litros_interno', 'litros_externo'], var_name='Origem', value_name='Litros'),
                           x='Ano-Mes', y='Litros', color='Origem',
                           labels={'Ano-Mes': 'Mês', 'Litros': 'Litros', 'Origem': 'Origem'},
                           title='Litros Abastecidos Mensalmente')
        st.plotly_chart(fig_litros, use_container_width=True)

        # Gráficos de valores mensais
        fig_valor = px.bar(mensal.melt(id_vars='Ano-Mes', value_vars=['valor_interno', 'valor_externo'], var_name='Origem', value_name='Valor (R$)'),
                           x='Ano-Mes', y='Valor (R$)', color='Origem',
                           labels={'Ano-Mes': 'Mês', 'Valor (R$)': 'Valor (R$)', 'Origem': 'Origem'},
                           title='Valor Total Abastecido Mensalmente')
        st.plotly_chart(fig_valor, use_container_width=True)

        # Gráficos de preço médio mensal
        st.subheader("Preço Médio do Combustível por Mês (R$/L)")
        fig_preco = px.line(mensal.melt(id_vars='Ano-Mes', value_vars=['Preço Médio Interno (R$/L)', 'Preço Médio Externo (R$/L)'],
                                        var_name='Origem', value_name='Preço Médio (R$/L)'),
                           x='Ano-Mes', y='Preço Médio (R$/L)', color='Origem',
                           labels={'Ano-Mes': 'Mês', 'Preço Médio (R$/L)': 'Preço Médio (R$/L)', 'Origem': 'Origem'},
                           title='Preço Médio Mensal do Combustível')
        st.plotly_chart(fig_preco, use_container_width=True)

    else:
        st.info("Faça upload da planilha com abas 'Abastecimento Interno' e 'Abastecimento Externo'.")

if __name__ == "__main__":
    main()
