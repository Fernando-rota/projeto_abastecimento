import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

def limpa_monetario(col):
    # Remove "R$" e converte para float
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True), errors='coerce')

def processa_interno(df):
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    df['AnoMes'] = df['Data'].dt.to_period('M').astype(str)
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['Valor Unitario'] = pd.to_numeric(df['Valor Unitario'], errors='coerce')
    df['Valor Total'] = pd.to_numeric(df['Valor Total'], errors='coerce')
    if 'Tipo' in df.columns:
        df_entradas = df[df['Tipo'].str.lower() == 'entrada']
    else:
        df_entradas = df
    return df_entradas

def processa_externo(df):
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    df['AnoMes'] = df['Data'].dt.to_period('M').astype(str)
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['Valor Unitario'] = limpa_monetario(df['Valor Unitario'])
    df['Valor Total'] = limpa_monetario(df['Valor Total'])
    return df

def calcula_indicadores(df, group_by_placa=False):
    if group_by_placa:
        agrupado = df.groupby(['AnoMes', 'Placa']).agg(
            litros_totais=('Quantidade de litros', 'sum'),
            valor_total_pago=('Valor Total', 'sum')
        ).reset_index()
        agrupado['preco_medio_litro'] = agrupado.apply(
            lambda r: r['valor_total_pago']/r['litros_totais'] if r['litros_totais'] > 0 else 0, axis=1)
        return agrupado.sort_values(['AnoMes'], ascending=False)
    else:
        agrupado = df.groupby('AnoMes').agg(
            litros_totais=('Quantidade de litros', 'sum'),
            valor_total_pago=('Valor Total', 'sum')
        ).reset_index()
        agrupado['preco_medio_litro'] = agrupado.apply(
            lambda r: r['valor_total_pago']/r['litros_totais'] if r['litros_totais'] > 0 else 0, axis=1)
        return agrupado.sort_values('AnoMes', ascending=False)

def plota_graficos(df, titulo):
    st.markdown(f"### Gráficos de {titulo}")
    fig, ax1 = plt.subplots(figsize=(12,5))
    sns.barplot(x='AnoMes', y='litros_totais', data=df, ax=ax1, color='skyblue')
    ax1.set_ylabel('Litros Totais')
    ax1.set_xlabel('Mês')
    ax1.tick_params(axis='x', rotation=45)

    ax2 = ax1.twinx()
    sns.lineplot(x='AnoMes', y='preco_medio_litro', data=df, ax=ax2, color='red', marker="o")
    ax2.set_ylabel('Preço Médio R$/Litro')

    plt.title(f"Litros Totais e Preço Médio - {titulo}")
    st.pyplot(fig)

def main():
    st.title("🚛 Dashboard de Abastecimento - Interno e Externo")

    st.sidebar.header("Upload das planilhas")
    arquivo_interno = st.sidebar.file_uploader("Abastecimento Interno (Excel/CSV)", type=['xlsx','xls','csv'])
    arquivo_externo = st.sidebar.file_uploader("Abastecimento Externo (Excel/CSV)", type=['xlsx','xls','csv'])

    if arquivo_interno is None or arquivo_externo is None:
        st.warning("Por favor, faça upload das duas planilhas para visualizar os indicadores.")
        return

    # Leitura das planilhas
    if arquivo_interno.name.endswith(('xlsx','xls')):
        df_interno = pd.read_excel(arquivo_interno)
    else:
        df_interno = pd.read_csv(arquivo_interno)

    if arquivo_externo.name.endswith(('xlsx','xls')):
        df_externo = pd.read_excel(arquivo_externo)
    else:
        df_externo = pd.read_csv(arquivo_externo)

    # Processa dados
    df_interno_proc = processa_interno(df_interno)
    df_externo_proc = processa_externo(df_externo)

    # Indicadores gerais (sem filtro placa)
    indicadores_interno = calcula_indicadores(df_interno_proc)
    indicadores_externo = calcula_indicadores(df_externo_proc)

    # Indicadores consolidados
    consolidado = pd.merge(
        indicadores_interno, indicadores_externo, on='AnoMes', how='outer', suffixes=('_interno', '_externo')).fillna(0)
    consolidado['litros_totais'] = consolidado['litros_totais_interno'] + consolidado['litros_totais_externo']
    consolidado['valor_total_pago'] = consolidado['valor_total_pago_interno'] + consolidado['valor_total_pago_externo']
    consolidado['preco_medio_litro'] = consolidado.apply(
        lambda r: r['valor_total_pago']/r['litros_totais'] if r['litros_totais'] > 0 else 0, axis=1)
    consolidado = consolidado[['AnoMes', 'litros_totais', 'valor_total_pago', 'preco_medio_litro']].sort_values('AnoMes', ascending=False)

    # Filtro por veículo (placa)
    todas_placas = sorted(set(df_interno_proc['Placa'].dropna().unique()) | set(df_externo_proc['Placa'].dropna().unique()))
    placa_selecionada = st.sidebar.selectbox("Filtrar por Placa (veículo)", ["Todas"] + todas_placas)

    st.header("Indicadores Consolidados (todos veículos)")
    st.dataframe(consolidado.style.format({
        'litros_totais': '{:.2f}',
        'valor_total_pago': 'R$ {:.2f}',
        'preco_medio_litro': 'R$ {:.3f}'
    }))

    plota_graficos(consolidado, "Consolidado")

    if placa_selecionada != "Todas":
        st.header(f"Indicadores para o veículo: {placa_selecionada}")

        interno_placa = df_interno_proc[df_interno_proc['Placa'] == placa_selecionada]
        externo_placa = df_externo_proc[df_externo_proc['Placa'] == placa_selecionada]

        indic_interno_placa = calcula_indicadores(interno_placa)
        indic_externo_placa = calcula_indicadores(externo_placa)

        consolidado_placa = pd.merge(
            indic_interno_placa, indic_externo_placa, on='AnoMes', how='outer', suffixes=('_interno', '_externo')).fillna(0)
        consolidado_placa['litros_totais'] = consolidado_placa['litros_totais_interno'] + consolidado_placa['litros_totais_externo']
        consolidado_placa['valor_total_pago'] = consolidado_placa['valor_total_pago_interno'] + consolidado_placa['valor_total_pago_externo']
        consolidado_placa['preco_medio_litro'] = consolidado_placa.apply(
            lambda r: r['valor_total_pago']/r['litros_totais'] if r['litros_totais'] > 0 else 0, axis=1)
        consolidado_placa = consolidado_placa[['AnoMes', 'litros_totais', 'valor_total_pago', 'preco_medio_litro']].sort_values('AnoMes', ascending=False)

        st.dataframe(consolidado_placa.style.format({
            'litros_totais': '{:.2f}',
            'valor_total_pago': 'R$ {:.2f}',
            'preco_medio_litro': 'R$ {:.3f}'
        }))

        plota_graficos(consolidado_placa, f"Veículo {placa_selecionada}")

if __name__ == "__main__":
    main()
