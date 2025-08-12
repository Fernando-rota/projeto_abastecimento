import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Dashboard Abastecimento Frota", layout="wide")

st.title("Dashboard de Abastecimento de Veículos")

# Upload dos arquivos Excel
st.sidebar.header("Carregar Planilhas")
arquivo_interno = st.sidebar.file_uploader("Upload Abastecimento Interno (Excel)", type=["xlsx"])
arquivo_externo = st.sidebar.file_uploader("Upload Abastecimento Externo (Excel)", type=["xlsx"])

@st.cache_data
def carregar_planilhas(arquivo_int, arquivo_ext):
    # Carregar planilha interna
    df_interno = pd.read_excel(arquivo_int) if arquivo_int else pd.DataFrame()
    # Carregar planilha externa
    df_externo = pd.read_excel(arquivo_ext) if arquivo_ext else pd.DataFrame()
    return df_interno, df_externo

if arquivo_interno and arquivo_externo:
    df_int, df_ext = carregar_planilhas(arquivo_interno, arquivo_externo)
    
    st.subheader("Dados Brutos - Interno")
    st.dataframe(df_int.head(10))
    
    st.subheader("Dados Brutos - Externo")
    st.dataframe(df_ext.head(10))
    
    ## Pré-processamento
    
    # Limpeza e padronização das colunas para interno
    df_int = df_int.rename(columns=lambda x: x.strip() if isinstance(x, str) else x)
    # Filtra apenas os registros relevantes (excluir linhas vazias ou placa nula)
    df_int = df_int[df_int['Placa'].notna()]
    # Transformar data em datetime
    df_int['Data'] = pd.to_datetime(df_int['Data'], errors='coerce')
    df_int = df_int.dropna(subset=['Data'])
    # Remover linhas com litros <= 0 (se houver)
    df_int = df_int[df_int['Quantidade de litros'] > 0]
    # Normalizar coluna 'Tipo' para maiúsculas e tirar espaços
    df_int['Tipo'] = df_int['Tipo'].str.strip().str.upper()
    
    # Limpeza e padronização das colunas para externo
    df_ext = df_ext.rename(columns=lambda x: x.strip() if isinstance(x, str) else x)
    df_ext = df_ext[df_ext['Placa'].notna()]
    df_ext['Data'] = pd.to_datetime(df_ext['Data'], errors='coerce')
    df_ext = df_ext.dropna(subset=['Data'])
    # Limpar colunas numéricas que podem estar como string (ex: "R$ 6,09")
    # Remove R$, espaços e substitui vírgula por ponto
    def limpar_monetario(valor):
        if pd.isna(valor):
            return np.nan
        if isinstance(valor, (int, float)):
            return valor
        valor = str(valor).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        try:
            return float(valor)
        except:
            return np.nan

    df_ext['Valor Unitario'] = df_ext['Valor Unitario'].apply(limpar_monetario)
    df_ext['Valor Total'] = df_ext['Valor Total'].apply(limpar_monetario)
    df_ext['Quantidade de litros'] = pd.to_numeric(df_ext['Quantidade de litros'], errors='coerce')

    # Filtra litros > 0
    df_ext = df_ext[df_ext['Quantidade de litros'] > 0]

    # Calcular preço médio por litro interno (somente entradas)
    df_int_entrada = df_int[df_int['Tipo'] == 'ENTRADA']  # Entradas no tanque
    preco_medio_interno = np.nan
    if not df_int_entrada.empty:
        # Somar valor total interno (se disponível) / litros para achar preço médio
        # Não temos valor unitário no interno? Se não, podemos deixar NaN.
        # Como não há valor unitário na tabela interna, vamos deixar NaN ou ignorar.
        preco_medio_interno = np.nan
    
    # Calcular preço médio por litro externo
    preco_medio_externo = df_ext['Valor Unitario'].mean()
    
    # Total litros abastecidos por placa (interno e externo)
    litros_interno_por_placa = df_int.groupby('Placa')['Quantidade de litros'].sum().sort_values(ascending=False)
    litros_externo_por_placa = df_ext.groupby('Placa')['Quantidade de litros'].sum().sort_values(ascending=False)
    
    # Total gasto por placa externo
    gasto_externo_por_placa = df_ext.groupby('Placa')['Valor Total'].sum().sort_values(ascending=False)
    
    # Consumo médio: calcular km/litro baseado no km atual e litros abastecidos.
    # Isso é complexo pois precisa do histórico de km e litros. Vamos tentar fazer para externo:
    df_ext = df_ext.sort_values(['Placa', 'Data'])
    df_ext['KM Atual'] = pd.to_numeric(df_ext['KM Atual'], errors='coerce')
    df_ext['Litros'] = df_ext['Quantidade de litros']
    
    # Cálculo simplificado: diferença de KM entre abastecimentos dividido pela quantidade de litros do abastecimento atual
    df_ext['KM Anterior'] = df_ext.groupby('Placa')['KM Atual'].shift(1)
    df_ext['KM Rodados'] = df_ext['KM Atual'] - df_ext['KM Anterior']
    df_ext['Consumo (km/l)'] = df_ext['KM Rodados'] / df_ext['Litros']
    df_ext = df_ext[df_ext['Consumo (km/l)'] > 0]  # remover valores inválidos
    
    consumo_medio_por_placa = df_ext.groupby('Placa')['Consumo (km/l)'].mean().sort_values(ascending=False)
    
    ### Apresentação dos indicadores
    
    st.header("Indicadores Gerais")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Preço Médio Litro Externo (R$)", f"{preco_medio_externo:.2f}" if not np.isnan(preco_medio_externo) else "N/D")
    with col2:
        st.metric("Preço Médio Litro Interno (R$)", "N/D (sem dados de valor)")
    
    st.subheader("Total de Litros Abastecidos por Veículo (Interno)")
    st.dataframe(litros_interno_por_placa.to_frame().rename(columns={"Quantidade de litros": "Litros Internos"}))
    
    st.subheader("Total de Litros Abastecidos por Veículo (Externo)")
    st.dataframe(litros_externo_por_placa.to_frame().rename(columns={"Quantidade de litros": "Litros Externos"}))
    
    st.subheader("Total Gasto Externo por Veículo (R$)")
    st.dataframe(gasto_externo_por_placa.to_frame())
    
    st.subheader("Consumo Médio (km/l) por Veículo (Baseado no Externo)")
    st.dataframe(consumo_medio_por_placa.to_frame())
    
    ### Gráficos profissionais
    
    st.header("Visualizações Gráficas")
    
    fig1, ax1 = plt.subplots(figsize=(10,5))
    litros_interno_por_placa.plot(kind='bar', ax=ax1, color='orange')
    ax1.set_title('Litros Abastecidos Internamente por Veículo')
    ax1.set_xlabel('Placa')
    ax1.set_ylabel('Litros')
    ax1.grid(axis='y')
    st.pyplot(fig1)
    
    fig2, ax2 = plt.subplots(figsize=(10,5))
    litros_externo_por_placa.plot(kind='bar', ax=ax2, color='green')
    ax2.set_title('Litros Abastecidos Externamente por Veículo')
    ax2.set_xlabel('Placa')
    ax2.set_ylabel('Litros')
    ax2.grid(axis='y')
    st.pyplot(fig2)
    
    fig3, ax3 = plt.subplots(figsize=(10,5))
    gasto_externo_por_placa.plot(kind='bar', ax=ax3, color='red')
    ax3.set_title('Gasto Total Externo por Veículo (R$)')
    ax3.set_xlabel('Placa')
    ax3.set_ylabel('Reais')
    ax3.grid(axis='y')
    st.pyplot(fig3)
    
    fig4, ax4 = plt.subplots(figsize=(10,5))
    consumo_medio_por_placa.plot(kind='bar', ax=ax4, color='blue')
    ax4.set_title('Consumo Médio (km/l) por Veículo')
    ax4.set_xlabel('Placa')
    ax4.set_ylabel('km/l')
    ax4.grid(axis='y')
    st.pyplot(fig4)
    
else:
    st.info("Por favor, faça upload dos arquivos de Abastecimento Interno e Externo para continuar.")
