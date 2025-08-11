import streamlit as st
import pandas as pd
import plotly.express as px

# Função para limpar e padronizar valores monetários e numéricos
def limpar_valor(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, str):
        return float(valor.replace('R$', '').replace('.', '').replace(',', '.').strip())
    return float(valor)

def carregar_dados(interno_path, externo_path, consumo_path):
    # Carregar planilhas
    df_interno = pd.read_excel(interno_path, sheet_name='interno')
    df_externo = pd.read_excel(externo_path, sheet_name='externo')
    df_consumo = pd.read_excel(consumo_path, sheet_name='consumo')
    
    # Limpeza e padronização interno
    df_interno['Data'] = pd.to_datetime(df_interno['Data'], dayfirst=True, errors='coerce')
    df_interno['Quantidade de litros'] = pd.to_numeric(df_interno['Quantidade de litros'], errors='coerce').fillna(0)
    df_interno['Valor Unitario'] = df_interno['Valor Unitario'].apply(limpar_valor)
    df_interno['Valor Total'] = df_interno['Valor Total'].apply(limpar_valor)
    df_interno['Placa'] = df_interno['Placa'].str.strip().str.upper()
    df_interno['Tipo Combustivel'] = df_interno['Tipo Combustivel'].str.strip().str.upper()
    
    # Limpeza externo
    df_externo['Data'] = pd.to_datetime(df_externo['Data'], dayfirst=True, errors='coerce')
    df_externo['Quantidade de litros'] = df_externo['Quantidade de litros'].astype(str).str.replace(',', '.').astype(float)
    df_externo['Valor Unitario'] = df_externo['Valor Unitario'].apply(limpar_valor)
    df_externo['Valor Total'] = df_externo['Valor Total'].apply(limpar_valor)
    df_externo['Placa'] = df_externo['Placa'].str.strip().str.upper()
    df_externo['Tipo Combustivel'] = df_externo['Tipo Combustivel'].str.strip().str.upper()
    
    # Limpeza consumo
    df_consumo['DATA'] = pd.to_datetime(df_consumo['DATA'], dayfirst=True, errors='coerce')
    df_consumo['QTD LITROS'] = df_consumo['QTD LITROS'].astype(float)
    df_consumo['PLACA'] = df_consumo['PLACA'].str.strip().str.upper()
    df_consumo['TIPO'] = df_consumo['TIPO'].str.strip().str.upper()
    
    return df_interno, df_externo, df_consumo

def main():
    st.title("Dashboard de Consumo e Abastecimento de Frota")
    
    st.sidebar.header("Configurações")
    
    # Upload arquivos Excel
    interno_file = st.sidebar.file_uploader("Upload planilha aba 'interno'", type=['xls', 'xlsx'])
    externo_file = st.sidebar.file_uploader("Upload planilha aba 'externo'", type=['xls', 'xlsx'])
    consumo_file = st.sidebar.file_uploader("Upload planilha aba 'consumo'", type=['xls', 'xlsx'])
    
    if interno_file and externo_file and consumo_file:
        df_interno, df_externo, df_consumo = carregar_dados(interno_file, externo_file, consumo_file)
        
        # Filtros
        placas = sorted(df_consumo['PLACA'].unique())
        combustiveis = sorted(df_consumo['TIPO'].unique())
        
        placa_selecionada = st.sidebar.selectbox("Selecione a placa", ['Todas'] + placas)
        combustivel_selecionado = st.sidebar.selectbox("Selecione o tipo de combustível", ['Todos'] + combustiveis)
        
        # Filtrar dados consumo
        df_consumo_filtrado = df_consumo.copy()
        if placa_selecionada != 'Todas':
            df_consumo_filtrado = df_consumo_filtrado[df_consumo_filtrado['PLACA'] == placa_selecionada]
        if combustivel_selecionado != 'Todos':
            df_consumo_filtrado = df_consumo_filtrado[df_consumo_filtrado['TIPO'] == combustivel_selecionado]
        
        st.subheader("Consumo por data")
        fig1 = px.line(df_consumo_filtrado, x='DATA', y='QTD LITROS', color='TIPO',
                       labels={'QTD LITROS':'Quantidade Litros', 'DATA':'Data', 'TIPO':'Combustível'},
                       title='Consumo diário de combustível')
        st.plotly_chart(fig1, use_container_width=True)
        
        # Indicadores básicos - consumo médio km/l
        # Para isso vamos calcular delta km e litros consumidos por período
        # Usaremos df_consumo para isso, agrupado por placa e tipo
        
        df_consumo_filtrado = df_consumo_filtrado.sort_values(['PLACA','DATA'])
        
        df_consumo_filtrado['KM_DIFF'] = df_consumo_filtrado.groupby(['PLACA','TIPO'])['KM'].diff()
        
        # Evitar divisão por zero e valores negativos
        df_consumo_filtrado = df_consumo_filtrado[df_consumo_filtrado['KM_DIFF'] > 0]
        
        df_consumo_filtrado['CONSUMO_KM_L'] = df_consumo_filtrado['KM_DIFF'] / df_consumo_filtrado['QTD LITROS']
        
        st.subheader("Indicadores de Eficiência")
        if not df_consumo_filtrado.empty:
            media_km_l = df_consumo_filtrado['CONSUMO_KM_L'].mean()
            st.metric("Consumo médio (km/l)", f"{media_km_l:.2f}")
        else:
            st.write("Dados insuficientes para cálculo de consumo médio km/l")
        
        # Custo médio por litro interno e externo
        st.subheader("Custo Médio por Litro - Interno x Externo")
        
        # Interno
        df_interno_filtrado = df_interno.copy()
        if placa_selecionada != 'Todas':
            df_interno_filtrado = df_interno_filtrado[df_interno_filtrado['Placa'] == placa_selecionada]
        if combustivel_selecionado != 'Todos':
            df_interno_filtrado = df_interno_filtrado[df_interno_filtrado['Tipo Combustivel'] == combustivel_selecionado]
        
        # Externo
        df_externo_filtrado = df_externo.copy()
        if placa_selecionada != 'Todas':
            df_externo_filtrado = df_externo_filtrado[df_externo_filtrado['Placa'] == placa_selecionada]
        if combustivel_selecionado != 'Todos':
            df_externo_filtrado = df_externo_filtrado[df_externo_filtrado['Tipo Combustivel'] == combustivel_selecionado]
        
        custo_medio_interno = (df_interno_filtrado['Valor Total'].sum() / df_interno_filtrado['Quantidade de litros'].sum()
                              if df_interno_filtrado['Quantidade de litros'].sum() > 0 else 0)
        custo_medio_externo = (df_externo_filtrado['Valor Total'].sum() / df_externo_filtrado['Quantidade de litros'].sum()
                              if df_externo_filtrado['Quantidade de litros'].sum() > 0 else 0)
        
        st.metric("Custo Médio Interno (R$/litro)", f"R$ {custo_medio_interno:.2f}")
        st.metric("Custo Médio Externo (R$/litro)", f"R$ {custo_medio_externo:.2f}")
        
        # Evolução custo total ao longo do tempo (interno + externo)
        st.subheader("Evolução do Custo Total ao Longo do Tempo")
        df_interno_plot = df_interno_filtrado.groupby('Data').agg({'Valor Total':'sum'}).reset_index()
        df_interno_plot['Tipo'] = 'Interno'
        df_externo_plot = df_externo_filtrado.groupby('Data').agg({'Valor Total':'sum'}).reset_index()
        df_externo_plot['Tipo'] = 'Externo'
        df_custos = pd.concat([df_interno_plot, df_externo_plot])
        
        if not df_custos.empty:
            fig2 = px.line(df_custos, x='Data', y='Valor Total', color='Tipo',
                           labels={'Valor Total':'Valor Total (R$)', 'Data':'Data', 'Tipo':'Origem'},
                           title='Custo Total por Data')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.write("Sem dados para gráfico de custo.")
        
    else:
        st.info("Faça upload das 3 planilhas para visualizar os dados.")
    
if __name__ == "__main__":
    main()
