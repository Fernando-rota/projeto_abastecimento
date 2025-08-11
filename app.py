import streamlit as st
import pandas as pd
import plotly.express as px

def limpar_valor(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, str):
        return float(valor.replace('R$', '').replace('.', '').replace(',', '.').strip())
    return float(valor)

def carregar_dados(abastecimento_path):
    df_interno = pd.read_excel(abastecimento_path, sheet_name='Abastecimento Interno')
    df_externo = pd.read_excel(abastecimento_path, sheet_name='Abastecimento Externo')
    
    # Limpeza interno
    df_interno['Data'] = pd.to_datetime(df_interno['Data'], dayfirst=True, errors='coerce')
    df_interno['Quantidade de litros'] = pd.to_numeric(df_interno['Quantidade de litros'], errors='coerce').fillna(0)
    # Valor Unitario pode estar vazio, tratar
    df_interno['Valor Unitario'] = df_interno['Valor Unitario'].apply(limpar_valor)
    df_interno['Valor Total'] = df_interno['Valor Total'].apply(limpar_valor)
    df_interno['Placa'] = df_interno['Placa'].astype(str).str.strip().str.upper()
    df_interno['Descrição Despesa'] = df_interno['Descrição Despesa'].astype(str).str.strip().str.upper()
    
    # Limpeza externo
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
    arquivo = st.sidebar.file_uploader("Faça upload da planilha com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xls', 'xlsx'])
    
    if arquivo:
        df_interno, df_externo = carregar_dados(arquivo)
        
        placas = sorted(set(df_interno['Placa'].unique()).union(set(df_externo['Placa'].unique())))
        combustiveis = sorted(set(df_interno['Descrição Despesa'].unique()).union(set(df_externo['Descrição Despesa'].unique())))
        
        placa_selecionada = st.sidebar.selectbox("Filtrar por placa", ['Todas'] + placas)
        combustivel_selecionado = st.sidebar.selectbox("Filtrar por combustível", ['Todos'] + combustiveis)
        
        if placa_selecionada != 'Todas':
            df_interno = df_interno[df_interno['Placa'] == placa_selecionada]
            df_externo = df_externo[df_externo['Placa'] == placa_selecionada]
        
        if combustivel_selecionado != 'Todos':
            df_interno = df_interno[df_interno['Descrição Despesa'] == combustivel_selecionado]
            df_externo = df_externo[df_externo['Descrição Despesa'] == combustivel_selecionado]
        
        st.subheader("Indicadores Gerais")
        
        total_litros_interno = df_interno['Quantidade de litros'].sum()
        total_valor_interno = df_interno['Valor Total'].sum()
        custo_medio_interno = (total_valor_interno / total_litros_interno) if total_litros_interno > 0 else 0
        
        total_litros_externo = df_externo['Quantidade de litros'].sum()
        total_valor_externo = df_externo['Valor Total'].sum()
        custo_medio_externo = (total_valor_externo / total_litros_externo) if total_litros_externo > 0 else 0
        
        col1, col2 = st.columns(2)
        col1.metric("Total Litros Interno", f"{total_litros_interno:.2f} L")
        col1.metric("Custo Médio Interno (R$/L)", f"R$ {custo_medio_interno:.2f}")
        
        col2.metric("Total Litros Externo", f"{total_litros_externo:.2f} L")
        col2.metric("Custo Médio Externo (R$/L)", f"R$ {custo_medio_externo:.2f}")
        
        st.subheader("Evolução do Custo Total (Interno x Externo)")
        
        df_interno_plot = df_interno.groupby('Data').agg({'Valor Total': 'sum'}).reset_index()
        df_interno_plot['Origem'] = 'Interno'
        
        df_externo_plot = df_externo.groupby('Data').agg({'Valor Total': 'sum'}).reset_index()
        df_externo_plot['Origem'] = 'Externo'
        
        df_custos = pd.concat([df_interno_plot, df_externo_plot]).sort_values('Data')
        
        if not df_custos.empty:
            fig = px.line(df_custos, x='Data', y='Valor Total', color='Origem',
                          labels={'Valor Total':'Valor Total (R$)', 'Data':'Data', 'Origem':'Origem'},
                          title='Custo Total ao Longo do Tempo')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Sem dados para gráfico.")
        
        st.subheader("Evolução da Quantidade de Litros Abastecidos (Interno x Externo)")
        
        df_interno_litros = df_interno.groupby('Data').agg({'Quantidade de litros': 'sum'}).reset_index()
        df_interno_litros['Origem'] = 'Interno'
        
        df_externo_litros = df_externo.groupby('Data').agg({'Quantidade de litros': 'sum'}).reset_index()
        df_externo_litros['Origem'] = 'Externo'
        
        df_litros = pd.concat([df_interno_litros, df_externo_litros]).sort_values('Data')
        
        if not df_litros.empty:
            fig2 = px.line(df_litros, x='Data', y='Quantidade de litros', color='Origem',
                           labels={'Quantidade de litros':'Litros', 'Data':'Data', 'Origem':'Origem'},
                           title='Litros Abastecidos ao Longo do Tempo')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.write("Sem dados para gráfico.")
    else:
        st.info("Faça upload da planilha Excel com abas 'Abastecimento Interno' e 'Abastecimento Externo' para visualizar os dados.")

if __name__ == "__main__":
    main()
