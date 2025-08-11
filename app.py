import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# (Mantém o código anterior, incluindo load_data, clean_valor, etc.)

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

    # Indicadores resumidos (mantém os anteriores)

    # --- Nova seção: Eficiência ---
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

    # Custo médio por km rodado (usando interno + externo)
    df_combined = pd.concat([df_interno_f.rename(columns={'Quantidade de litros': 'litros', 'Valor Total': 'valor'}),
                             df_externo_f.rename(columns={'Quantidade de litros': 'litros', 'Valor Total': 'valor'})],
                            ignore_index=True)

    custo_por_placa = []
    for placa in placas_selecionadas:
        df_placa = df_combined[df_combined['Placa'] == placa]
        litros_total = df_placa['litros'].sum()
        valor_total = df_placa['valor'].sum()
        if litros_total > 0:
            custo_litro = valor_total / litros_total
        else:
            custo_litro = np.nan

        # km rodados na tabela consumo
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

    # Gráfico comparativo custo por km
    fig_custo = px.bar(df_custo, x='Placa', y='Custo Médio por Km Rodado (R$)', title='Custo Médio por Km Rodado por Placa')
    st.plotly_chart(fig_custo, use_container_width=True)

    # Gráfico de distribuição tipos de combustível
    st.header("Distribuição de Combustíveis Consumidos")

    # Somar litros por tipo combustível nas 3 bases filtradas
    litros_por_combustivel = pd.concat([
        df_interno_f.groupby('Tipo Combustivel')['Quantidade de litros'].sum(),
        df_externo_f.groupby('Tipo Combustivel')['Quantidade de litros'].sum(),
        df_consumo_f.groupby('TIPO')['QTD LITROS'].sum()
    ]).groupby(level=0).sum()

    fig_dist = px.pie(values=litros_por_combustivel.values, names=litros_por_combustivel.index,
                      title='Distribuição de litros por tipo de combustível')
    st.plotly_chart(fig_dist, use_container_width=True)

    # Mantém as visualizações e indicadores anteriores...

if __name__ == "__main__":
    main()
