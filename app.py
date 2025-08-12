import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import io

# Configuração inicial
st.set_page_config(page_title="Indicadores de Combustível", layout="wide")
st.title("📊 Indicadores de Consumo de Combustível - Interativo")

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
        
        # Processamento dos dados - Cálculo robusto do consumo médio
        def calculate_consumo(df):
            # Ordenar por placa e data
            df = df.sort_values(['Placa', 'Data'])
            
            # Calcular diferença de KM e litros entre abastecimentos
            df['KM Anterior'] = df.groupby('Placa')['KM Atual'].shift(1)
            df['Litros Anteriores'] = df.groupby('Placa')['Quantidade de litros'].shift(1)
            df['Data Anterior'] = df.groupby('Placa')['Data'].shift(1)
            
            # Calcular KM rodados e litros consumidos entre abastecimentos
            df['KM Rodados'] = df['KM Atual'] - df['KM Anterior']
            df['Dias Entre Abastecimentos'] = (df['Data'] - df['Data Anterior']).dt.days
            
            # Calcular consumo médio (KM/L)
            df['Consumo (KM/L)'] = np.where(
                (df['KM Rodados'] > 0) & (df['Quantidade de litros'] > 0),
                df['KM Rodados'] / df['Quantidade de litros'],
                np.nan
            )
            
            # Calcular consumo diário (KM/Dia)
            df['Consumo Diário (KM/Dia)'] = np.where(
                df['Dias Entre Abastecimentos'] > 0,
                df['KM Rodados'] / df['Dias Entre Abastecimentos'],
                np.nan
            )
            
            return df

        # Aplicar cálculo de consumo se tivermos os dados necessários
        if 'Placa' in df_interno.columns and 'KM Atual' in df_interno.columns and 'Quantidade de litros' in df_interno.columns:
            df_interno = calculate_consumo(df_interno.copy())
        
        # Processamento para indicadores mensais
        def process_data(df_interno, df_externo):
            # Criar DataFrames mensais
            interno_mensal = df_interno.copy()
            interno_mensal['Mês'] = interno_mensal['Data'].dt.to_period('M')
            
            externo_mensal = df_externo.copy()
            externo_mensal['Mês'] = externo_mensal['Data'].dt.to_period('M')
            
            # Agregar dados internos por mês
            interno_agg = interno_mensal.groupby('Mês').agg({
                'Quantidade de litros': 'sum',
                'KM Rodados': 'sum',
                'Consumo (KM/L)': 'mean',
                'Placa': 'nunique'
            }).reset_index()
            
            interno_agg.columns = ['Mês', 'Litros Internos', 'KM Rodados', 'Consumo Médio (KM/L)', 'Veículos Únicos']
            
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
        
        # Gráficos interativos com Plotly
        st.subheader("Visualizações Gráficas Interativas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Consumo de Litros por Mês**")
            fig = px.bar(df_combined, x='Mês', y=['Litros Internos', 'Litros Externos'], 
                         barmode='stack', title='Consumo de Litros por Mês',
                         labels={'value': 'Litros', 'variable': 'Tipo'})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'Custo Total (R$)' in df_combined.columns:
                st.markdown("**Custo Total por Mês**")
                fig = px.bar(df_combined, x='Mês', y='Custo Total (R$)', 
                             title='Custo Total por Mês', color_discrete_sequence=['orange'])
                st.plotly_chart(fig, use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("**Consumo Médio (KM/L)**")
            fig = px.line(df_combined, x='Mês', y='Consumo Médio (KM/L)', 
                          title='Consumo Médio (KM/L)', markers=True)
            st.plotly_chart(fig, use_container_width=True)
        
        with col4:
            if 'Preço Médio (R$)' in df_combined.columns:
                st.markdown("**Preço Médio do Combustível**")
                fig = px.line(df_combined, x='Mês', y='Preço Médio (R$)', 
                              title='Preço Médio (R$/L)', markers=True, color_discrete_sequence=['red'])
                st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico adicional interativo - Análise por veículo
        if 'Placa' in df_interno.columns and 'Consumo (KM/L)' in df_interno.columns:
            st.subheader("Análise Detalhada por Veículo")
            
            # Selecionar veículo específico
            veiculos = df_interno['Placa'].unique()
            selected_veiculo = st.selectbox("Selecione um veículo para análise detalhada:", veiculos)
            
            df_veiculo = df_interno[df_interno['Placa'] == selected_veiculo].sort_values('Data')
            
            if not df_veiculo.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Consumo do Veículo {selected_veiculo}**")
                    fig = px.line(df_veiculo, x='Data', y='Consumo (KM/L)', 
                                  title=f'Consumo (KM/L) - {selected_veiculo}', markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown(f"**Quilometragem do Veículo {selected_veiculo}**")
                    fig = px.line(df_veiculo, x='Data', y='KM Atual', 
                                  title=f'Quilometragem - {selected_veiculo}', markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Mostrar tabela detalhada
                st.dataframe(df_veiculo[[
                    'Data', 'Quantidade de litros', 'KM Atual', 'KM Rodados', 
                    'Consumo (KM/L)', 'Dias Entre Abastecimentos', 'Consumo Diário (KM/Dia)'
                ]].sort_values('Data', ascending=False).style.format({
                    'Consumo (KM/L)': '{:.2f}',
                    'KM Rodados': '{:,.0f}',
                    'Consumo Diário (KM/Dia)': '{:.2f}',
                    'Quantidade de litros': '{:.2f}'
                }), use_container_width=True)
        
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
    else:
        st.warning("Não foi possível carregar os dados do arquivo. Verifique o formato e tente novamente.")
else:
    st.info("Por favor, carregue um arquivo Excel para gerar os indicadores.")
