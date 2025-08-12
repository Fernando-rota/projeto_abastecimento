import streamlit as st
import pandas as pd

# Função para processar dados de abastecimento interno
def processa_abastecimento_interno(df):
    # Converter coluna 'Data' para datetime
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])  # remover linhas com data inválida
    
    # Extrair ano e mês para agrupamento
    df['AnoMes'] = df['Data'].dt.to_period('M')
    
    # Converter 'Quantidade de litros' para numérico
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['Valor Unitario'] = pd.to_numeric(df['Valor Unitario'], errors='coerce')
    df['Valor Total'] = pd.to_numeric(df['Valor Total'], errors='coerce')
    
    # Filtrar só abastecimento do tipo 'Entrada' se existir, ou considerar tudo (ajuste aqui conforme necessidade)
    # Aqui como a planilha tem 'Tipo' Saída, vamos considerar só entradas para valor médio:
    df_entradas = df[df['Tipo'].str.lower() == 'entrada'] if 'Tipo' in df.columns else df
    
    # Agrupar por AnoMes e calcular total litros e valor total pago
    agrupado = df_entradas.groupby('AnoMes').agg(
        litros_totais = ('Quantidade de litros', 'sum'),
        valor_total_pago = ('Valor Total', 'sum')
    ).reset_index()
    
    # Calcular preço médio por litro (tratando divisão por zero)
    agrupado['preco_medio_litro'] = agrupado.apply(
        lambda row: row['valor_total_pago'] / row['litros_totais'] if row['litros_totais'] > 0 else 0, axis=1)
    
    # Ordenar em ordem decrescente de AnoMes
    agrupado = agrupado.sort_values(by='AnoMes', ascending=False)
    
    return agrupado

# Função para processar dados de abastecimento externo
def processa_abastecimento_externo(df):
    # Converter coluna 'Data' para datetime
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    
    # Extrair ano e mês
    df['AnoMes'] = df['Data'].dt.to_period('M')
    
    # Ajustar colunas numéricas (ex: Quantidade de litros, Valor Unitario, Valor Total)
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    # Remover "R$" e converter Valor Unitario e Valor Total para float
    df['Valor Unitario'] = df['Valor Unitario'].str.replace(r'R\$\s*', '', regex=True)
    df['Valor Unitario'] = pd.to_numeric(df['Valor Unitario'], errors='coerce')
    df['Valor Total'] = df['Valor Total'].str.replace(r'R\$\s*', '', regex=True)
    df['Valor Total'] = pd.to_numeric(df['Valor Total'], errors='coerce')
    
    agrupado = df.groupby('AnoMes').agg(
        litros_totais = ('Quantidade de litros', 'sum'),
        valor_total_pago = ('Valor Total', 'sum')
    ).reset_index()
    
    agrupado['preco_medio_litro'] = agrupado.apply(
        lambda row: row['valor_total_pago'] / row['litros_totais'] if row['litros_totais'] > 0 else 0, axis=1)
    
    agrupado = agrupado.sort_values(by='AnoMes', ascending=False)
    
    return agrupado

def main():
    st.title("Indicadores Mensais de Abastecimento")
    
    # Upload dos arquivos Excel (pode adaptar para CSV ou outro formato)
    st.sidebar.header("Carregar dados")
    arquivo_interno = st.sidebar.file_uploader("Upload Planilha Abastecimento Interno", type=["xlsx", "xls", "csv"])
    arquivo_externo = st.sidebar.file_uploader("Upload Planilha Abastecimento Externo", type=["xlsx", "xls", "csv"])
    
    if arquivo_interno is not None:
        if arquivo_interno.name.endswith(('xlsx','xls')):
            df_interno = pd.read_excel(arquivo_interno)
        else:
            df_interno = pd.read_csv(arquivo_interno)
        st.subheader("Abastecimento Interno")
        st.dataframe(df_interno.head())
        df_interno_proc = processa_abastecimento_interno(df_interno)
        st.subheader("Indicadores Mensais Abastecimento Interno")
        st.dataframe(df_interno_proc.style.format({
            'litros_totais': '{:.2f}',
            'valor_total_pago': 'R$ {:.2f}',
            'preco_medio_litro': 'R$ {:.3f}'
        }))
    
    if arquivo_externo is not None:
        if arquivo_externo.name.endswith(('xlsx','xls')):
            df_externo = pd.read_excel(arquivo_externo)
        else:
            df_externo = pd.read_csv(arquivo_externo)
        st.subheader("Abastecimento Externo")
        st.dataframe(df_externo.head())
        df_externo_proc = processa_abastecimento_externo(df_externo)
        st.subheader("Indicadores Mensais Abastecimento Externo")
        st.dataframe(df_externo_proc.style.format({
            'litros_totais': '{:.2f}',
            'valor_total_pago': 'R$ {:.2f}',
            'preco_medio_litro': 'R$ {:.3f}'
        }))
    
    if arquivo_interno is not None and arquivo_externo is not None:
        st.subheader("Indicadores Consolidados")
        # Merge por AnoMes somando litros e valores
        df_total = pd.merge(df_interno_proc, df_externo_proc, on='AnoMes', how='outer', suffixes=('_interno', '_externo')).fillna(0)
        df_total['litros_totais'] = df_total['litros_totais_interno'] + df_total['litros_totais_externo']
        df_total['valor_total_pago'] = df_total['valor_total_pago_interno'] + df_total['valor_total_pago_externo']
        df_total['preco_medio_litro'] = df_total.apply(
            lambda row: row['valor_total_pago'] / row['litros_totais'] if row['litros_totais'] > 0 else 0, axis=1)
        df_total = df_total[['AnoMes', 'litros_totais', 'valor_total_pago', 'preco_medio_litro']].sort_values('AnoMes', ascending=False)
        
        st.dataframe(df_total.style.format({
            'litros_totais': '{:.2f}',
            'valor_total_pago': 'R$ {:.2f}',
            'preco_medio_litro': 'R$ {:.3f}'
        }))

if __name__ == "__main__":
    main()
