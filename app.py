import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Dashboard Frota - Consumo & Abastecimento", layout="wide")

@st.cache_data
def load_data(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    df_interno = pd.read_excel(xls, 'interno')
    df_externo = pd.read_excel(xls, 'externo')
    df_consumo = pd.read_excel(xls, 'consumo')

    # Datas
    df_interno['Data'] = pd.to_datetime(df_interno['Data'], dayfirst=True, errors='coerce')
    df_externo['Data'] = pd.to_datetime(df_externo['Data'], dayfirst=True, errors='coerce')
    df_consumo['DATA'] = pd.to_datetime(df_consumo['DATA'], dayfirst=True, errors='coerce')

    # Números
    df_interno['Quantidade de litros'] = pd.to_numeric(df_interno['Quantidade de litros'], errors='coerce')
    df_externo['Quantidade de litros'] = pd.to_numeric(df_externo['Quantidade de litros'], errors='coerce')
    df_consumo['QTD LITROS'] = pd.to_numeric(df_consumo['QTD LITROS'], errors='coerce')

    # Limpar valores monetários
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

def calcula_indicadores(df, litros_col='Quantidade de litros', valor_col='Valor Total', placa_col='Placa'):
    # Remove placa '-' para análises de veículos
    df = df[df[placa_col] != '-']
    total_litros = df[litros_col].sum()
    total_valor = df[valor_col].sum() if valor_col in df.columns else np.nan
    valor_medio_litro = total_valor / total_litros if total_litros > 0 else np.nan
    placas_unicas = df[placa_col].dropna().unique().tolist()
    return {
        "total_litros": total_litros,
        "total_valor": total_valor,
        "valor_medio_litro": valor_medio_litro,
        "num_veiculos": len(placas_unicas),
        "placas": placas_unicas,
    }

def consumo_medio_por_placa(df_consumo):
    # Remove placa '-' e limpa dados
    df = df_consumo[df_consumo['PLACA'] != '-'].copy()
    placas = df['PLACA'].unique()
    resultados = []
    for placa in placas:
        df_p = df[df['PLACA'] == placa]
        km_min = df_p['KM'].min()
        km_max = df_p['KM'].max()
        litros_total = df_p['QTD LITROS'].sum()
        km_rodados = km_max - km_min
        km_por_litro = km_rodados / litros_total if litros_total > 0 else np.nan
        resultados.append({
            'PLACA': placa,
            'KM Inicial': km_min,
            'KM Final': km_max,
            'Km Rodados': km_rodados,
            'Total Litros': litros_total,
            'Consumo (km/litro)': km_por_litro
        })
    return pd.DataFrame(resultados)

def main():
    st.title("Dashboard Frota: Consumo & Abastecimento")

    uploaded_file = st.file_uploader("Envie seu arquivo Excel com abas 'interno', 'externo' e 'consumo'", type=['xlsx'])
    if not uploaded_file:
        st.info("Por favor, envie o arquivo para iniciar.")
        return

    df_interno, df_externo, df_consumo = load_data(uploaded_file)

    # Preparar filtros gerais
    placas_interno = set(df_interno['Placa'].dropna().unique()) - {'-'}
    placas_externo = set(df_externo['Placa'].dropna().unique()) - {'-'}
    placas_consumo = set(df_consumo['PLACA'].dropna().unique()) - {'-'}

    placas = sorted(placas_interno | placas_externo | placas_consumo)

    combustiveis = sorted(set(
        df_interno['Tipo Combustivel'].dropna().unique().tolist() +
        df_externo['Tipo Combustivel'].dropna().unique().tolist() +
        df_consumo['TIPO'].dropna().unique().tolist()
    ))

    with st.sidebar:
        st.header("Filtros Gerais")
        placas_selecionadas = st.multiselect("Selecione placas:", options=placas, default=placas)
        combustivel_selecionado = st.multiselect("Selecione combustível(s):", options=combustiveis, default=combustiveis)

        data_min = min(df_interno['Data'].min(), df_externo['Data'].min(), df_consumo['DATA'].min())
        data_max = max(df_interno['Data'].max(), df_externo['Data'].max(), df_consumo['DATA'].max())

        data_inicio, data_fim = st.date_input("Período:", value=[data_min, data_max], min_value=data_min, max_value=data_max)

    # Função para filtrar dataframe conforme filtros selecionados
    def filtrar(df, data_col, placa_col, tipo_col=None, litros_col=None):
        df_f = df.copy()
        df_f = df_f[df_f[placa_col].isin(placas_selecionadas)]
        df_f = df_f[(df_f[data_col] >= pd.to_datetime(data_inicio)) & (df_f[data_col] <= pd.to_datetime(data_fim))]
        if tipo_col:
            df_f = df_f[df_f[tipo_col].isin(combustivel_selecionado)]
        if litros_col:
            df_f = df_f[pd.notnull(df_f[litros_col])]
        return df_f

    df_interno_f = filtrar(df_interno, 'Data', 'Placa', 'Tipo Combustivel', 'Quantidade de litros')
    df_externo_f = filtrar(df_externo, 'Data', 'Placa', 'Tipo Combustivel', 'Quantidade de litros')
    df_consumo_f = filtrar(df_consumo, 'DATA', 'PLACA', 'TIPO', 'QTD LITROS')

    # Começar com abas para mostrar cada fonte separada + comparação
    abas = st.tabs(["Abastecimento Interno", "Abastecimento Externo", "Consumo", "Comparações"])

    with abas[0]:
        st.header("Abastecimento Interno")
        ind_interno = calcula_indicadores(df_interno_f)
        st.metric("Total litros", f"{ind_interno['total_litros']:.2f}")
        st.metric("Total gasto (R$)", f"{ind_interno['total_valor']:.2f}")
        st.metric("Valor médio por litro (R$)", f"{ind_interno['valor_medio_litro']:.2f}")
        st.metric("Veículos (placas únicas)", ind_interno['num_veiculos'])

        st.subheader("Dados filtrados")
        st.dataframe(df_interno_f)

    with abas[1]:
        st.header("Abastecimento Externo")
        ind_externo = calcula_indicadores(df_externo_f)
        st.metric("Total litros", f"{ind_externo['total_litros']:.2f}")
        st.metric("Total gasto (R$)", f"{ind_externo['total_valor']:.2f}")
        st.metric("Valor médio por litro (R$)", f"{ind_externo['valor_medio_litro']:.2f}")
        st.metric("Veículos (placas únicas)", ind_externo['num_veiculos'])

        st.subheader("Dados filtrados")
        st.dataframe(df_externo_f)

    with abas[2]:
        st.header("Consumo")
        ind_consumo = calcula_indicadores(df_consumo_f, litros_col='QTD LITROS', valor_col=None, placa_col='PLACA')
        st.metric("Total litros", f"{ind_consumo['total_litros']:.2f}")
        st.metric("Veículos (placas únicas)", ind_consumo['num_veiculos'])

        df_consumo_med = consumo_medio_por_placa(df_consumo_f)
        st.subheader("Consumo médio por veículo")
        st.dataframe(df_consumo_med)

        fig_consumo = px.bar(df_consumo_med, x='PLACA', y='Consumo (km/litro)',
                            labels={'PLACA': 'Placa', 'Consumo (km/litro)': 'Km por Litro'},
                            title="Consumo médio (Km por litro) por veículo")
        st.plotly_chart(fig_consumo, use_container_width=True)

    with abas[3]:
        st.header("Comparações Entre Abastecimentos e Consumo")

        # Comparar total litros e gasto entre interno e externo lado a lado
        comp_df = pd.DataFrame({
            "Fonte": ["Interno", "Externo"],
            "Total Litros": [ind_interno['total_litros'], ind_externo['total_litros']],
            "Total Gasto (R$)": [ind_interno['total_valor'], ind_externo['total_valor']]
        })
        st.subheader("Total litros e gasto por fonte")
        st.dataframe(comp_df)

        fig_comp_litros = px.bar(comp_df, x='Fonte', y='Total Litros', title="Comparação de Litros Abastecidos")
        st.plotly_chart(fig_comp_litros, use_container_width=True)

        fig_comp_gasto = px.bar(comp_df, x='Fonte', y='Total Gasto (R$)', title="Comparação de Gasto Total")
        st.plotly_chart(fig_comp_gasto, use_container_width=True)

        # Mostrar placas comuns e diferentes
        placas_comuns = set(ind_interno['placas']) & set(ind_externo['placas'])
        placas_somente_interno = set(ind_interno['placas']) - placas_comuns
        placas_somente_externo = set(ind_externo['placas']) - placas_comuns

        st.write(f"Placas em comum: {', '.join(sorted(placas_comuns)) if placas_comuns else 'Nenhuma'}")
        st.write(f"Placas somente em interno: {', '.join(sorted(placas_somente_interno)) if placas_somente_interno else 'Nenhuma'}")
        st.write(f"Placas somente em externo: {', '.join(sorted(placas_somente_externo)) if placas_somente_externo else 'Nenhuma'}")

if __name__ == "__main__":
    main()
