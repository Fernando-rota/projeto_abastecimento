import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import io

# Configuração inicial
st.set_page_config(page_title="Indicadores de Combustível", layout="wide")
st.title("📊 Indicadores de Consumo de Combustível")

# Função para carregar dados do arquivo
def load_data(uploaded_file):
    try:
        # Ler o arquivo Excel
        xls = pd.ExcelFile(uploaded_file)
        
        # Carregar abas específicas
        df_interno = pd.read_excel(xls, sheet_name='Abastecimento Interno')
        df_externo = pd.read_excel(xls, sheet_name='Abastecimento Externo')
        
        # Verificar e padronizar nomes de colunas
        df_interno.columns = df_interno.columns.str.strip()
        df_externo.columns = df_externo.columns.str.strip()
        
        # Converter datas
        date_cols_int = ['Data', 'Carimbo de data/hora']
        date_cols_ext = ['Data']
        
        for col in date_cols_int:
            if col in df_interno.columns:
                df_interno[col] = pd.to_datetime(df_interno[col], dayfirst=True, errors='coerce')
        
        for col in date_cols_ext:
            if col in df_externo.columns:
                df_externo[col] = pd.to_datetime(df_externo[col], dayfirst=True, errors='coerce')
        
        # Processar valores monetários (externo)
        if 'Valor Unitario' in df_externo.columns:
            df_externo['Valor Unitario'] = (
                df_externo['Valor Unitario']
                .astype(str)
                .str.replace('R\$', '')
                .str.replace(',', '.')
                .str.strip()
                .replace('', np.nan)
                .astype(float)
            )
        
        if 'Valor Total' in df_externo.columns:
            df_externo['Valor Total'] = (
                df_externo['Valor Total']
                .astype(str)
                .str.replace('R\$', '')
                .str.replace(',', '.')
                .str.strip()
                .replace('', np.nan)
                .astype(float)
            )
        
        # Remover linhas vazias
        df_interno = df_interno.dropna(how='all')
        df_externo = df_externo.dropna(how='all')
        
        return df_interno, df_externo
    
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {str(e)}")
        return None, None

# Upload do arquivo
uploaded_file = st.file_uploader("Carregue o arquivo de abastecimento (Excel)", type=['xlsx', 'xls'])

if uploaded_file is not None:
    df_interno, df_externo = load_data(uploaded_file)
    
    if df_interno is not None and df_externo is not None:
        # Mostrar pré-visualização dos dados
        st.subheader("Pré-visualização dos Dados")
        
        tab1, tab2 = st.tabs(["Abastecimento Interno", "Abastecimento Externo"])
        
        with tab1:
            st.dataframe(df_interno.head())
        
        with tab2:
            st.dataframe(df_externo.head())
        
        # Processamento dos dados
        def process_data(df_interno, df_externo):
            # Criar DataFrames mensais
            interno_mensal = df_interno.copy()
            interno_mensal['Mês'] = interno_mensal['Data'].dt.to_period('M')
            
            externo_mensal = df_externo.copy()
            externo_mensal['Mês'] = externo_mensal['Data'].dt.to_period('M')
            
            # Agregar dados internos por mês
            interno_agg = interno_mensal.groupby('Mês').agg({
                'Quantidade de litros': 'sum',
                'Placa': 'nunique'
            }).reset_index()
            
            # Calcular KM Rodados separadamente para evitar erros
            km_rodados = interno_mensal.groupby('Mês')['KM Atual'].agg(
                lambda x: x.max() - x.min() if pd.api.types.is_numeric_dtype(x) and len(x) > 1 else 0
            ).reset_index()
            km_rodados.columns = ['Mês', 'KM Rodados']
            
            interno_agg = pd.merge(interno_agg, km_rodados, on='Mês', how='left')
            interno_agg.columns = ['Mês', 'Litros Internos', 'Veículos Únicos', 'KM Rodados']
            
            interno_agg['Consumo Médio (KM/L)'] = np.where(
                interno_agg['Litros Internos'] > 0,
                interno_agg['KM Rodados'] / interno_agg['Litros Internos'],
                0
            )
            
            # Agregar dados externos por mês
            externo_agg = pd.DataFrame()
            
            if not df_externo.empty:
                externo_agg = externo_mensal.groupby('Mês').agg({
                    'Quantidade de litros': 'sum',
                    'Valor Unitario': 'mean',
                    'Valor Total': 'sum',
                    'Placa': 'nunique'
                }).reset_index()
                
                externo_agg.columns = ['Mês', 'Litros Externos', 'Preço Médio (R$)', 'Custo Total (R$)', 'Veículos Únicos']
            
            # Combinar dados
            if not externo_agg.empty:
                df_combined = pd.merge(interno_agg, externo_agg, on='Mês', how='outer').fillna(0)
            else:
                df_combined = interno_agg.copy()
                df_combined['Litros Externos'] = 0
                df_combined['Preço Médio (R$)'] = 0
                df_combined['Custo Total (R$)'] = 0
                df_combined['Veículos Únicos_y'] = 0
            
            df_combined['Mês'] = df_combined['Mês'].astype(str)
            df_combined['Total Litros'] = df_combined['Litros Internos'] + df_combined['Litros Externos']
            
            # Ordenar por mês em ordem decrescente
            df_combined = df_combined.sort_values('Mês', ascending=False)
            
            return df_combined
        
        df_combined = process_data(df_interno, df_externo)
        
        # Visualização no Streamlit
        st.header("Indicadores Mensais de Combustível")
        
        # Mostrar tabela com todos os indicadores
        st.subheader("Visão Geral Mensal")
        st.dataframe(df_combined.style.format({
            'Consumo Médio (KM/L)': '{:.2f}',
            'Preço Médio (R$)': '{:.2f}',
            'Custo Total (R$)': '{:.2f}',
            'KM Rodados': '{:,.0f}',
            'Litros Internos': '{:,.2f}',
            'Litros Externos': '{:,.2f}',
            'Total Litros': '{:,.2f}'
        }), use_container_width=True)
        
        # Gráficos
        st.subheader("Visualizações Gráficas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Consumo de Litros por Mês**")
            fig, ax = plt.subplots()
            
            if 'Litros Externos' in df_combined.columns:
                df_combined.plot(kind='bar', x='Mês', y=['Litros Internos', 'Litros Externos'], ax=ax, stacked=True)
            else:
                df_combined.plot(kind='bar', x='Mês', y='Litros Internos', ax=ax)
            
            plt.ylabel('Litros')
            plt.xticks(rotation=45)
            st.pyplot(fig)
        
        with col2:
            if 'Custo Total (R$)' in df_combined.columns:
                st.markdown("**Custo Total por Mês**")
                fig, ax = plt.subplots()
                df_combined.plot(kind='bar', x='Mês', y='Custo Total (R$)', ax=ax, color='orange')
                plt.ylabel('R$')
                plt.xticks(rotation=45)
                st.pyplot(fig)
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("**Consumo Médio (KM/L)**")
            fig, ax = plt.subplots()
            df_combined.plot(kind='line', x='Mês', y='Consumo Médio (KM/L)', ax=ax, marker='o', color='green')
            plt.ylabel('KM/L')
            plt.xticks(rotation=45)
            st.pyplot(fig)
        
        with col4:
            if 'Preço Médio (R$)' in df_combined.columns:
                st.markdown("**Preço Médio do Combustível**")
                fig, ax = plt.subplots()
                df_combined.plot(kind='line', x='Mês', y='Preço Médio (R$)', ax=ax, marker='o', color='red')
                plt.ylabel('R$/L')
                plt.xticks(rotation=45)
                st.pyplot(fig)
        
        # Métricas resumidas
        st.subheader("Métricas Principais")
        
        total_litros = df_combined['Total Litros'].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Litros Consumidos", f"{total_litros:,.2f} L")
        
        if 'Custo Total (R$)' in df_combined.columns:
            total_custo = df_combined['Custo Total (R$)'].sum()
            col2.metric("Custo Total Combustível", f"R$ {total_custo:,.2f}")
        
        if 'Consumo Médio (KM/L)' in df_combined.columns:
            consumo_medio = df_combined['Consumo Médio (KM/L)'].mean()
            col3.metric("Consumo Médio", f"{consumo_medio:.2f} KM/L")
        
        if 'Preço Médio (R$)' in df_combined.columns:
            preco_medio = df_combined['Preço Médio (R$)'].mean()
            col4.metric("Preço Médio por Litro", f"R$ {preco_medio:.2f}")
        
        # Análise por veículo
        st.subheader("Análise por Veículo")
        
        # Dados internos por veículo
        if 'Placa' in df_interno.columns and 'Quantidade de litros' in df_interno.columns and 'KM Atual' in df_interno.columns:
            interno_veiculo = df_interno.groupby('Placa').agg({
                'Quantidade de litros': 'sum',
                'KM Atual': lambda x: x.max() - x.min() if len(x) > 1 and pd.api.types.is_numeric_dtype(x) else 0
            }).reset_index()
            interno_veiculo.columns = ['Placa', 'Litros Consumidos', 'KM Rodados']
            interno_veiculo['Consumo (KM/L)'] = np.where(
                interno_veiculo['Litros Consumidos'] > 0,
                interno_veiculo['KM Rodados'] / interno_veiculo['Litros Consumidos'],
                0
            )
            
            st.markdown("**Abastecimento Interno por Veículo**")
            st.dataframe(interno_veiculo.style.format({
                'Consumo (KM/L)': '{:.2f}',
                'KM Rodados': '{:,.0f}',
                'Litros Consumidos': '{:,.2f}'
            }), use_container_width=True)
        
        # Dados externos por veículo
        if not df_externo.empty and 'Placa' in df_externo.columns and 'Quantidade de litros' in df_externo.columns:
            externo_veiculo = df_externo.groupby('Placa').agg({
                'Quantidade de litros': 'sum'
            }).reset_index()
            externo_veiculo.columns = ['Placa', 'Litros Abastecidos']
            
            if 'Valor Total' in df_externo.columns:
                externo_veiculo['Custo Total'] = df_externo.groupby('Placa')['Valor Total'].sum().values
            
            st.markdown("**Abastecimento Externo por Veículo**")
            st.dataframe(externo_veiculo, use_container_width=True)
    else:
        st.warning("Não foi possível carregar os dados do arquivo. Verifique o formato e tente novamente.")
else:
    st.info("Por favor, carregue um arquivo Excel para gerar os indicadores.")
