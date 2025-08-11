import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Dashboard de Abastecimento e Consumo", layout="wide")

@st.cache_data
def load_data(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    df_interno = pd.read_excel(xls, 'interno')
    df_externo = pd.read_excel(xls, 'externo')
    df_consumo = pd.read_excel(xls, 'consumo')

    # Converter datas
    df_interno['Data'] = pd.to_datetime(df_interno['Data'], dayfirst=True, errors='coerce')
    df_externo['Data'] = pd.to_datetime(df_externo['Data'], dayfirst=True, errors='coerce')
    df_consumo['DATA'] = pd.to_datetime(df_consumo['DATA'], dayfirst=True, errors='coerce')

    # Converter litros
    df_interno['Quantidade de litros'] = pd.to_numeric(df_interno['Quantidade de litros'], errors='coerce')
    df_externo['Quantidade de litros'] = pd.to_numeric(df_externo['Quantidade de litros'], errors='coerce')
    df_consumo['QTD LITROS'] = pd.to_numeric(df_consumo['QTD LITROS'], errors='coerce')

    # Função para limpar valor (ex: "R$ 3,33" -> 3.33 float)
    def clean_valor(valor):
        if pd.isna(valor):
            return np.nan
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
            try:
                return float(valor)
            except:
                return np.nan
        return np.nan

    df_externo['Valor Unitario'] = df_externo['Valor Unitario'].apply(clean_valor)
    df_externo['Valor Total'] = df_externo['Valor Total'].apply(clean_valor)
    df_interno['Valor Unitario'] = df_interno['Valor Unitario'].apply(clean_valor)
    df_interno['Valor Total'] = df_interno['Valor Total'].apply(clean_valor)

    return df_interno, df_externo, df_consumo

def calcula_eficiencia(df_consumo):
    # Consumo médio litros por km rodado (km/litro)
    df = df_consumo.copy()
    df = df.sort_values('DATA')
    df['km_diff'] = df.groupby('PLACA')['KM'].diff()
    df['litros_diff'] = df.groupby('PLACA')['QTD LITROS'].diff()
    # Evita divisão por zero e valores negativos
    df = df[(df['km_diff'] > 0) & (df['litros_diff'] > 0)]
    df['km_por_litro'] = df['km_diff'] / df['litros_diff']
    return df

def main():
    st.title("Dashboard BI de Abastecimento e Consumo de Frota")

    uploaded_file = st.file_uploader("Faça upload do arquivo Excel com as abas 'interno', 'externo' e 'consumo'", type=['xlsx'])
    if uploaded_file is None:
        st.info("Carregue o arquivo para continuar")
        return

    df_interno, df_externo, df_consumo = load_data(uploaded_file)

    # Filtros - agora permite múltiplas placas
    st.sidebar.header("Filtros")
    placas_interno = df_interno['Placa'].dropna().unique().tolist()
    placas_externo = df_externo['Placa'].dropna().unique().tolist()
    placas_consumo = df_consumo['PLACA'].dropna().unique().tolist()
    placas = sorted(set(placas_interno + placas_externo + placas_consumo))

    placas_selecionadas = st.sidebar.multiselect("Selecione uma ou mais placas:", options=placas, default=placas)

    combustiveis = sorted(set(
        df_interno['Tipo Combustivel'].dropna().unique().tolist() +
        df_externo['Tipo Combustivel'].dropna().unique().tolist() +
        df_consumo['TIPO'].dropna().unique().tolist()
    ))
    combustivel_selecionado = st.sidebar.multiselect("Selecione o(s) combustível(s):", options=combustiveis, default=combustiveis)

    min_date = min(df_interno['Data'].min(), df_externo['Data'].min(), df_consumo['DATA'].min())
    max_date = max(df_interno['Data'].max(), df_externo['Data'].max(), df_consumo['DATA'].max())

    data_inicio, data_fim = st.sidebar.date_input("Período", [min_date, max_date], min_value=min_date, max_value=max_date)

    def filtrar(df, data_col, placa_col, tipo_col=None, litros_col=None):
        df_f = df.copy()
        if placas_selecionadas:
            df_f = df_f[df_f[placa_col].isin(placas_selecionadas)]
        else:
            # Se não selecionar placa, mostra vazio
            return df_f.iloc[0:0]
        df_f = df_f[(df_f[data_col] >= pd.to_datetime(data_inicio)) & (df_f[data_col] <= pd.to_datetime(data_fim))]
        if tipo_col:
            df_f = df_f[df_f[tipo_col].isin(combustivel_selecionado)]
        if litros_col:
            df_f = df_f[pd.notnull(df_f[litros_col])]
        return df_f

    df_interno_f = filtrar(df_interno, 'Data', 'Placa', 'Tipo Combustivel', 'Quantidade de litros')
    df_externo_f = filtrar(df_externo, 'Data', 'Placa', 'Tipo Combustivel', 'Quantidade de litros')
    df_consumo_f = filtrar(df_consumo, 'DATA', 'PLACA', 'TIPO', 'QTD LITROS')

    # Indicadores resumidos
    def indicadores(df, litros_col='Quantidade de litros', valor_col='Valor Total'):
        total_litros = df[litros_col].sum()
        total_valor = df[valor_col].sum() if valor_col in df.columns else np.nan
        valor_medio_litro = total_valor / total_litros if total_litros > 0 else np.nan
        return {
            "Total litros": total_litros,
            "Total valor (R$)": total_valor,
            "Valor médio por litro (R$)": valor_medio_litro,
        }

    ind_interno = indicadores(df_interno_f)
    ind_externo = indicadores(df_externo_f)

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

    # Gráficos consumo por data e combustível
    st.header("Gráficos de Consumo")

    fig1 = px.line(df_consumo_f, x='DATA', y='QTD LITROS', color='TIPO',
                   title="Consumo de litros por tipo de combustível ao longo do tempo",
                   labels={"DATA": "Data", "QTD LITROS": "Litros", "TIPO": "Combustível"})
    st.plotly_chart(fig1, use_container_width=True)

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

    # --- Nova seção: Eficiência e Custo ---
    st.header("Análise de Eficiência e Custo")

    df_eficiencia = calcula_eficiencia(df_consumo_f)

    if not df_eficiencia.empty:
        fig_eficiencia = px.box(df_eficiencia, x='PLACA', y='km_por_litro',
                                title='Distribuição do Consumo (km por litro) por Placa',
                                labels={'km_por_litro': 'Km por Litro', 'PLACA': 'Placa'})
        st.plotly_chart(fig_eficiencia, use_container_width=True)

        media_eficiencia = df_eficiencia.groupby('PLACA')['km_por_litro'].mean().reset_index()
        st.dataframe(media_eficiencia.rename(columns={'km_por_litro': 'Média Km por Litro'}))
    else:
        st.info("Dados insuficientes para cálculo de eficiência.")

    # Custo médio por km rodado (interno + externo)
    df_combined = pd.concat([
        df_interno_f.rename(columns={'Quantidade de litros': 'litros', 'Valor Total': 'valor'}),
        df_externo_f.rename(columns={'Quantidade de litros': 'litros', 'Valor Total': 'valor'})
    ], ignore_index=True)

    custo_por_placa = []
    for placa in placas_selecionadas:
        df_placa = df_combined[df_combined['Placa'] == placa]
        litros_total = df_placa['litros'].sum()
        valor_total = df_placa['valor'].sum()
        custo_litro = valor_total / litros_total if litros_total > 0 else np.nan

        df_km = df_consumo_f[df_consumo_f['PLACA'] == placa]
        km_rodados = df_km['KM'].max() - df_km['KM'].min() if not df_km.empty else np.nan

        custo_km = valor_total / km_rodados if (km_rodados and km_rodados > 0) else np.nan

        custo_por_placa.append({
            'Placa': placa,
            'Custo Médio por Litro (R$)': custo_litro,
            'Km Rodados': km_rodados,
            'Custo Médio por Km Rodado (R$)': custo_km,
            'Total Gasto (R$)': valor_total,
            'Total Litros': litros_total,
        })

    df_custo = pd.DataFrame(custo_por_placa)
    st.subheader("Custo Médio por Placa")
    st.dataframe(df_custo)

    fig_custo = px.bar(df_custo, x='Placa', y='Custo Médio por Km Rodado (R$)', title='Custo Médio por Km Rodado por Placa')
    st.plotly_chart(fig_custo, use_container_width=True)

    # Distribuição combustível
    st.header("Distribuição de Combustíveis Consumidos")

    litros_por_combustivel = pd.concat([
        df_interno_f.groupby('Tipo Combustivel')['Quantidade de litros'].sum(),
        df_externo_f.groupby('Tipo Combustivel')['Quantidade de litros'].sum(),
        df_consumo_f.groupby('TIPO')['QTD LITROS'].sum()
    ]).groupby(level=0).sum()

    fig_dist = px.pie(values=litros_por_combustivel.values, names=litros_por_combustivel.index,
                      title='Distribuição de litros por tipo de combustível')
    st.plotly_chart(fig_dist, use_container_width=True)

    # Visualização dos dados tabulares
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
