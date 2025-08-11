import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Dashboard de Abastecimento e Consumo", layout="wide")

@st.cache_data
def load_data(uploaded_file):
    # Carrega o Excel com várias abas
    xls = pd.ExcelFile(uploaded_file)
    df_interno = pd.read_excel(xls, 'interno')
    df_externo = pd.read_excel(xls, 'externo')
    df_consumo = pd.read_excel(xls, 'consumo')
    
    # Ajustes básicos de dados
    # Convertendo datas para datetime
    df_interno['Data'] = pd.to_datetime(df_interno['Data'], dayfirst=True, errors='coerce')
    df_externo['Data'] = pd.to_datetime(df_externo['Data'], dayfirst=True, errors='coerce')
    df_consumo['DATA'] = pd.to_datetime(df_consumo['DATA'], dayfirst=True, errors='coerce')
    
    # Limpar colunas e tipos
    df_interno['Quantidade de litros'] = pd.to_numeric(df_interno['Quantidade de litros'], errors='coerce')
    df_externo['Quantidade de litros'] = pd.to_numeric(df_externo['Quantidade de litros'], errors='coerce')
    df_consumo['QTD LITROS'] = pd.to_numeric(df_consumo['QTD LITROS'], errors='coerce')
    
    # Limpar colunas valor unitário (remover R$ e converter)
    def clean_valor(valor):
        if pd.isna(valor):
            return np.nan
        if isinstance(valor, str):
            return float(valor.replace('R$', '').replace('.', '').replace(',', '.').strip())
        return valor
    df_externo['Valor Unitario'] = df_externo['Valor Unitario'].apply(clean_valor)
    
    return df_interno, df_externo, df_consumo


def main():
    st.title("Dashboard BI de Abastecimento e Consumo de Frota")
    
    uploaded_file = st.file_uploader("Faça upload do arquivo Excel com as abas 'interno', 'externo' e 'consumo'", type=['xlsx'])
    if uploaded_file is None:
        st.info("Carregue o arquivo para continuar")
        return
    
    df_interno, df_externo, df_consumo = load_data(uploaded_file)
    
    # Sidebar - filtros
    st.sidebar.header("Filtros")
    placas_interno = df_interno['Placa'].dropna().unique().tolist()
    placas_externo = df_externo['Placa'].dropna().unique().tolist()
    placas_consumo = df_consumo['PLACA'].dropna().unique().tolist()
    placas = sorted(set(placas_interno + placas_externo + placas_consumo))
    
    placa_selecionada = st.sidebar.selectbox("Selecione a placa:", options=["Todas"] + placas)
    
    combustiveis = sorted(set(
        df_interno['Tipo Combustivel'].dropna().unique().tolist() +
        df_externo['Tipo Combustivel'].dropna().unique().tolist() +
        df_consumo['TIPO'].dropna().unique().tolist()
    ))
    combustivel_selecionado = st.sidebar.multiselect("Selecione o(s) combustível(s):", options=combustiveis, default=combustiveis)
    
    # Filtro de data - intervalo comum entre as bases
    min_date = min(df_interno['Data'].min(), df_externo['Data'].min(), df_consumo['DATA'].min())
    max_date = max(df_interno['Data'].max(), df_externo['Data'].max(), df_consumo['DATA'].max())
    
    data_inicio, data_fim = st.sidebar.date_input("Período", [min_date, max_date], min_value=min_date, max_value=max_date)
    
    # Aplicar filtros
    def filtrar(df, data_col, placa_col, tipo_col=None):
        df_f = df.copy()
        if placa_selecionada != "Todas":
            df_f = df_f[df_f[placa_col] == placa_selecionada]
        df_f = df_f[(df_f[data_col] >= pd.to_datetime(data_inicio)) & (df_f[data_col] <= pd.to_datetime(data_fim))]
        if tipo_col:
            df_f = df_f[df_f[tipo_col].isin(combustivel_selecionado)]
        return df_f
    
    df_interno_f = filtrar(df_interno, 'Data', 'Placa', 'Tipo Combustivel')
    df_externo_f = filtrar(df_externo, 'Data', 'Placa', 'Tipo Combustivel')
    df_consumo_f = filtrar(df_consumo, 'DATA', 'PLACA', 'TIPO')
    
    # Indicadores principais
    st.header("Indicadores Gerais")
    
    def indicadores(df, label):
        total_litros = df['Quantidade de litros'].sum() if 'Quantidade de litros' in df.columns else df['QTD LITROS'].sum()
        total_valor = df['Valor Total'].replace('R$', '', regex=True).str.replace('.', '', regex=True).str.replace(',', '.', regex=True)
        try:
            total_valor = total_valor.astype(float).sum()
        except:
            total_valor = np.nan
        valor_medio_litro = total_valor / total_litros if total_litros > 0 else np.nan
        return {
            "Total litros": total_litros,
            "Total valor (R$)": total_valor,
            "Valor médio por litro (R$)": valor_medio_litro,
        }
    
    ind_interno = indicadores(df_interno_f, 'Interno')
    ind_externo = indicadores(df_externo_f, 'Externo')
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Abastecimento Interno")
        st.metric("Total litros", f"{ind_interno['Total litros']:.2f}")
        st.metric("Total gasto (R$)", f"{ind_interno['Total valor (R$)']:.2f}")
        st.metric("Valor médio por litro (R$)", f"{ind_interno['Valor médio por litro (R$)']:.2f}")
    with col2:
        st.subheader("Abastecimento Externo")
        st.metric("Total litros", f"{ind_externo['Total litros']:.2f}")
        st.metric("Total gasto (R$)", f"{ind_externo['Total valor (R$)']:.2f}")
        st.metric("Valor médio por litro (R$)", f"{ind_externo['Valor médio por litro (R$)']:.2f}")
    
    # Gráficos de consumo ao longo do tempo
    st.header("Gráficos de Consumo")
    
    fig1 = px.line(df_consumo_f, x='DATA', y='QTD LITROS', color='TIPO',
                   title="Consumo de litros por tipo de combustível ao longo do tempo",
                   labels={"DATA": "Data", "QTD LITROS": "Litros", "TIPO": "Combustível"})
    st.plotly_chart(fig1, use_container_width=True)
    
    # Comparação litros interno x externo
    st.header("Comparação Litros Interno x Externo")
    
    df_interno_sum = df_interno_f.groupby(['Data', 'Tipo Combustivel']).agg({'Quantidade de litros': 'sum'}).reset_index()
    df_externo_sum = df_externo_f.groupby(['Data', 'Tipo Combustivel']).agg({'Quantidade de litros': 'sum'}).reset_index()
    
    df_interno_sum['Origem'] = 'Interno'
    df_externo_sum['Origem'] = 'Externo'
    
    df_comparacao = pd.concat([df_interno_sum, df_externo_sum])
    
    fig2 = px.bar(df_comparacao, x='Data', y='Quantidade de litros', color='Origem', barmode='group',
                  facet_col='Tipo Combustivel',
                  title="Comparação de litros abastecidos interno x externo por tipo combustível")
    st.plotly_chart(fig2, use_container_width=True)
    
    # Visualização tabelas filtradas
    st.header("Visualização dos Dados Filtrados")
    
    aba = st.radio("Selecione a aba para visualizar os dados:", options=["Interno", "Externo", "Consumo"])
    if aba == "Interno":
        st.dataframe(df_interno_f)
    elif aba == "Externo":
        st.dataframe(df_externo_f)
    else:
        st.dataframe(df_consumo_f)
    

if __name__ == "__main__":
    main()
