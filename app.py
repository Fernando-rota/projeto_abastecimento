import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")

def limpa_monetario(col):
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

def calcula_indicadores(df):
    agrupado = df.groupby('AnoMes').agg(
        litros_totais=('Quantidade de litros', 'sum'),
        valor_total_pago=('Valor Total', 'sum')
    ).reset_index()
    agrupado['preco_medio_litro'] = agrupado.apply(
        lambda r: r['valor_total_pago'] / r['litros_totais'] if r['litros_totais'] > 0 else 0, axis=1)
    agrupado = agrupado.sort_values('AnoMes', ascending=False)
    return agrupado

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

    st.sidebar.header("Upload da planilha Excel com duas abas")
    arquivo = st.sidebar.file_uploader("Escolha o arquivo Excel (.xlsx)", type=['xlsx'])
    
    if arquivo is None:
        st.warning("Faça upload do arquivo Excel que contenha as abas 'Abastecimento Interno' e 'Abastecimento Externo'.")
        return

    # Lê as duas abas
    df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
    df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')

    st.subheader("Amostra Abastecimento Interno")
    st.dataframe(df_interno.head())
    st.subheader("Amostra Abastecimento Externo")
    st.dataframe(df_externo.head())

    df_interno_proc = processa_interno(df_interno)
    df_externo_proc = processa_externo(df_externo)

    indicadores_interno = calcula_indicadores(df_interno_proc)
    indicadores_externo = calcula_indicadores(df_externo_proc)

    # Consolidação mensal
    consolidado = pd.merge(
        indicadores_interno, indicadores_externo,
        on='AnoMes', how='outer', suffixes=('_interno', '_externo')).fillna(0)

    consolidado['litros_totais'] = consolidado['litros_totais_interno'] + consolidado['litros_totais_externo']
    consolidado['valor_total_pago'] = consolidado['valor_total_pago_interno'] + consolidado['valor_total_pago_externo']
    consolidado['preco_medio_litro'] = consolidado.apply(
        lambda r: r['valor_total_pago'] / r['litros_totais'] if r['litros_totais'] > 0 else 0, axis=1)

    consolidado = consolidado[['AnoMes', 'litros_totais', 'valor_total_pago', 'preco_medio_litro']].sort_values('AnoMes', ascending=False)

    st.header("Indicadores Consolidados Mensais")
    st.dataframe(consolidado.style.format({
        'litros_totais': '{:.2f}',
        'valor_total_pago': 'R$ {:.2f}',
        'preco_medio_litro': 'R$ {:.3f}'
    }))

    plota_graficos(consolidado, "Consolidado")

if __name__ == "__main__":
    main()
