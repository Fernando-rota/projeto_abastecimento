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

    # Limpeza e padronização Interno
    df_interno['Data'] = pd.to_datetime(df_interno['Data'], dayfirst=True, errors='coerce')
    df_interno['Quantidade de litros'] = pd.to_numeric(df_interno['Quantidade de litros'], errors='coerce').fillna(0)
    df_interno['Valor Unitario'] = df_interno['Valor Unitario'].apply(limpar_valor)
    df_interno['Valor Total'] = df_interno['Valor Total'].apply(limpar_valor)
    df_interno['Placa'] = df_interno['Placa'].astype(str).str.strip().str.upper()
    df_interno['Descrição Despesa'] = df_interno['Descrição Despesa'].astype(str).str.strip().str.upper()

    # Limpeza e padronização Externo
    df_externo['Data'] = pd.to_datetime(df_externo['Data'], dayfirst=True, errors='coerce')
    df_externo['Quantidade de litros'] = df_externo['Quantidade de litros'].astype(str).str.replace(',', '.').astype(float)
    df_externo['Valor Unitario'] = df_externo['Valor Unitario'].apply(limpar_valor)
    df_externo['Valor Total'] = df_externo['Valor Total'].apply(limpar_valor)
    df_externo['Placa'] = df_externo['Placa'].astype(str).str.strip().str.upper()
    df_externo['Descrição Despesa'] = df_externo['Descrição Despesa'].astype(str).str.strip().str.upper()

    return df_interno, df_externo

def main():
    st.title("Dashboard Abastecimento Interno x Externo")

    st.sidebar.header("Upload da planilha Excel")
    arquivo = st.sidebar.file_uploader("Envie a planilha com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xls', 'xlsx'])

    if arquivo:
        df_interno, df_externo = carregar_dados(arquivo)

        # Remover placas inválidas
        placas_invalidas = ['-', 'CORREÇÃO']
        df_interno = df_interno[~df_interno['Placa'].isin(placas_invalidas)]
        df_externo = df_externo[~df_externo['Placa'].isin(placas_invalidas)]

        # Filtros
        placas = sorted(set(df_interno['Placa'].unique()) | set(df_externo['Placa'].unique()))
        combustiveis = sorted(set(df_interno['Descrição Despesa'].unique()) | set(df_externo['Descrição Despesa'].unique()))

        placa_selecionada = st.sidebar.selectbox("Filtrar por placa", ['Todas'] + placas)
        combustivel_selecionado = st.sidebar.selectbox("Filtrar por combustível", ['Todos'] + combustiveis)

        data_min = min(df_interno['Data'].min(), df_externo['Data'].min())
        data_max = max(df_interno['Data'].max(), df_externo['Data'].max())
        periodo = st.sidebar.date_input("Filtrar por período", [data_min, data_max])

        # Aplicar filtros
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

        # Indicadores
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

        # Gráfico custo ao longo do tempo
        st.subheader("Evolução do Custo Total")

        interno_plot = df_interno.groupby('Data')['Valor Total'].sum().reset_index()
        interno_plot['Origem'] = 'Interno'

        externo_plot = df_externo.groupby('Data')['Valor Total'].sum().reset_index()
        externo_plot['Origem'] = 'Externo'

        df_custo = pd.concat([interno_plot, externo_plot]).sort_values('Data')

        if not df_custo.empty:
            fig1 = px.line(df_custo, x='Data', y='Valor Total', color='Origem',
                           labels={'Valor Total': 'Valor Total (R$)', 'Data': 'Data', 'Origem': 'Origem'},
                           title="Custo Total ao Longo do Tempo")
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.write("Sem dados para gráfico.")

        # Gráfico litros ao longo do tempo
        st.subheader("Evolução da Quantidade de Litros")

        interno_litros = df_interno.groupby('Data')['Quantidade de litros'].sum().reset_index()
        interno_litros['Origem'] = 'Interno'

        externo_litros = df_externo.groupby('Data')['Quantidade de litros'].sum().reset_index()
        externo_litros['Origem'] = 'Externo'

        df_litros = pd.concat([interno_litros, externo_litros]).sort_values('Data')

        if not df_litros.empty:
            fig2 = px.line(df_litros, x='Data', y='Quantidade de litros', color='Origem',
                           labels={'Quantidade de litros': 'Litros', 'Data': 'Data', 'Origem': 'Origem'},
                           title="Litros Abastecidos ao Longo do Tempo")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.write("Sem dados para gráfico.")
    else:
        st.info("Faça upload da planilha com abas 'Abastecimento Interno' e 'Abastecimento Externo'.")

if __name__ == "__main__":
    main()
