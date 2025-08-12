import streamlit as st
import pandas as pd
import numpy as np

st.title("Indicadores Profissionais de Abastecimento")

arquivo_interno = st.file_uploader("Upload Abastecimento Interno (Excel)", type=["xlsx"])
arquivo_externo = st.file_uploader("Upload Abastecimento Externo (Excel)", type=["xlsx"])

@st.cache_data
def carregar_planilhas(arquivo_int, arquivo_ext):
    df_int = pd.read_excel(arquivo_int) if arquivo_int else pd.DataFrame()
    df_ext = pd.read_excel(arquivo_ext) if arquivo_ext else pd.DataFrame()
    return df_int, df_ext

if arquivo_interno and arquivo_externo:
    df_int, df_ext = carregar_planilhas(arquivo_interno, arquivo_externo)

    # Limpeza básico interno
    df_int = df_int[df_int['Placa'].notna()]
    df_int['Data'] = pd.to_datetime(df_int['Data'], errors='coerce')
    df_int = df_int[df_int['Quantidade de litros'] > 0]
    df_int['Tipo'] = df_int['Tipo'].str.strip().str.upper()
    
    # Limpeza básico externo
    df_ext = df_ext[df_ext['Placa'].notna()]
    df_ext['Data'] = pd.to_datetime(df_ext['Data'], errors='coerce')
    df_ext = df_ext[df_ext['Quantidade de litros'] > 0]
    
    def limpar_valor(v):
        if pd.isna(v):
            return np.nan
        if isinstance(v, (int,float)):
            return v
        v = str(v).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        try:
            return float(v)
        except:
            return np.nan

    df_ext['Valor Unitario'] = df_ext['Valor Unitario'].apply(limpar_valor)
    df_ext['Valor Total'] = df_ext['Valor Total'].apply(limpar_valor)

    # Preço médio por litro externo
    preco_medio_externo = df_ext['Valor Unitario'].mean()

    # Total litros por placa
    litros_interno = df_int.groupby('Placa')['Quantidade de litros'].sum().sort_values(ascending=False)
    litros_externo = df_ext.groupby('Placa')['Quantidade de litros'].sum().sort_values(ascending=False)

    # Gasto total externo por placa
    gasto_externo = df_ext.groupby('Placa')['Valor Total'].sum().sort_values(ascending=False)

    # Consumo médio km/l externo (simplificado)
    df_ext = df_ext.sort_values(['Placa', 'Data'])
    df_ext['KM Atual'] = pd.to_numeric(df_ext['KM Atual'], errors='coerce')
    df_ext['Litros'] = df_ext['Quantidade de litros']
    df_ext['KM Anterior'] = df_ext.groupby('Placa')['KM Atual'].shift(1)
    df_ext['KM Rodados'] = df_ext['KM Atual'] - df_ext['KM Anterior']
    df_ext['Consumo (km/l)'] = df_ext['KM Rodados'] / df_ext['Litros']
    df_ext = df_ext[df_ext['Consumo (km/l)'] > 0]
    consumo_medio = df_ext.groupby('Placa')['Consumo (km/l)'].mean().sort_values(ascending=False)

    st.header("Resumo dos Indicadores")

    st.metric("Preço Médio por Litro (Externo)", f"R$ {preco_medio_externo:.2f}")

    st.subheader("Total Litros Abastecidos (Interno) - Top 5")
    for placa, litros in litros_interno.head(5).items():
        st.write(f"{placa}: {litros:.1f} litros")

    st.subheader("Total Litros Abastecidos (Externo) - Top 5")
    for placa, litros in litros_externo.head(5).items():
        st.write(f"{placa}: {litros:.1f} litros")

    st.subheader("Gasto Total Externo - Top 5")
    for placa, gasto in gasto_externo.head(5).items():
        st.write(f"{placa}: R$ {gasto:.2f}")

    st.subheader("Consumo Médio (km/l) - Top 5")
    for placa, consumo in consumo_medio.head(5).items():
        st.write(f"{placa}: {consumo:.2f} km/l")

else:
    st.info("Faça upload das planilhas de Abastecimento Interno e Externo para visualizar os indicadores.")

