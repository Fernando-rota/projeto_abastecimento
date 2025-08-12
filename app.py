import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Dashboard Abastecimento Completo", layout="wide")

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
        df = df[df['Tipo'].str.lower() == 'entrada']
    return df

def processa_externo(df):
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    df['AnoMes'] = df['Data'].dt.to_period('M').astype(str)
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['Valor Unitario'] = limpa_monetario(df['Valor Unitario'])
    df['Valor Total'] = limpa_monetario(df['Valor Total'])
    return df

def calcula_indicadores_mes(df):
    agrupado = df.groupby('AnoMes').agg(
        litros_totais=('Quantidade de litros', 'sum'),
        valor_total_pago=('Valor Total', 'sum')
    ).reset_index()
    agrupado['preco_medio_litro'] = agrupado.apply(
        lambda r: r['valor_total_pago'] / r['litros_totais'] if r['litros_totais'] > 0 else 0, axis=1)
    agrupado = agrupado.sort_values('AnoMes', ascending=True)
    return agrupado

def plota_litros_mes(df_interno, df_externo):
    plt.figure(figsize=(12,5))
    sns.barplot(x='AnoMes', y='litros_totais', data=df_interno, color='blue', label='Interno')
    sns.barplot(x='AnoMes', y='litros_totais', data=df_externo, color='orange', label='Externo', alpha=0.6)
    plt.xticks(rotation=45)
    plt.ylabel("Litros Totais")
    plt.title("Litros Mensais: Interno x Externo")
    plt.legend()
    st.pyplot(plt.gcf())
    plt.clf()

def plota_preco_medio_mes(df_interno, df_externo):
    plt.figure(figsize=(12,5))
    plt.plot(df_interno['AnoMes'], df_interno['preco_medio_litro'], marker='o', label='Interno', color='blue')
    plt.plot(df_externo['AnoMes'], df_externo['preco_medio_litro'], marker='o', label='Externo', color='orange')
    plt.xticks(rotation=45)
    plt.ylabel("Preço Médio R$/Litro")
    plt.title("Preço Médio do Litro por Mês")
    plt.legend()
    st.pyplot(plt.gcf())
    plt.clf()

def main():
    st.title("🚛 Dashboard Completo de Abastecimento")

    arquivo = st.sidebar.file_uploader("Upload Excel com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xlsx'])
    if arquivo is None:
        st.warning("Faça upload do arquivo Excel com as abas corretas para continuar.")
        return

    df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
    df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')

    df_interno = processa_interno(df_interno)
    df_externo = processa_externo(df_externo)

    indicadores_interno = calcula_indicadores_mes(df_interno)
    indicadores_externo = calcula_indicadores_mes(df_externo)

    # Consolida para cálculo total
    consolidado = pd.merge(
        indicadores_interno, indicadores_externo, on='AnoMes', how='outer',
        suffixes=('_interno', '_externo')).fillna(0)

    consolidado['litros_totais'] = consolidado['litros_totais_interno'] + consolidado['litros_totais_externo']
    consolidado['valor_total_pago'] = consolidado['valor_total_pago_interno'] + consolidado['valor_total_pago_externo']
    consolidado['preco_medio_litro'] = consolidado.apply(
        lambda r: r['valor_total_pago'] / r['litros_totais'] if r['litros_totais'] > 0 else 0, axis=1)

    # Indicadores mês atual em cards
    from datetime import date
    ano_mes_atual = date.today().strftime('%Y-%m')

    def indicadores_do_mes(df, ano_mes):
        sel = df[df['AnoMes'] == ano_mes]
        if sel.empty:
            return 0, 0, 0
        row = sel.iloc[0]
        return row['litros_totais'], row['valor_total_pago'], row['preco_medio_litro']

    st.header(f"Indicadores do mês atual ({ano_mes_atual})")

    li_interno, vi_interno, pi_interno = indicadores_do_mes(indicadores_interno, ano_mes_atual)
    li_externo, vi_externo, pi_externo = indicadores_do_mes(indicadores_externo, ano_mes_atual)
    li_total, vi_total, pi_total = indicadores_do_mes(consolidado, ano_mes_atual)

    col1, col2, col3 = st.columns(3)
    col1.metric("Litros Internos", f"{li_interno:.2f} L")
    col2.metric("Valor Interno", f"R$ {vi_interno:.2f}")
    col3.metric("Preço Médio Interno", f"R$ {pi_interno:.3f} / L")

    col4, col5, col6 = st.columns(3)
    col4.metric("Litros Externos", f"{li_externo:.2f} L")
    col5.metric("Valor Externo", f"R$ {vi_externo:.2f}")
    col6.metric("Preço Médio Externo", f"R$ {pi_externo:.3f} / L")

    col7, col8, col9 = st.columns(3)
    col7.metric("Litros Totais", f"{li_total:.2f} L")
    col8.metric("Valor Total", f"R$ {vi_total:.2f}")
    col9.metric("Preço Médio Total", f"R$ {pi_total:.3f} / L")

    st.markdown("---")
    st.header("Evolução Mensal")

    st.subheader("Litros Mensais: Interno x Externo")
    plota_litros_mes(indicadores_interno, indicadores_externo)

    st.subheader("Preço Médio do Litro por Mês")
    plota_preco_medio_mes(indicadores_interno, indicadores_externo)

    # Exemplo simples de autonomia: autonomia = litros totais / consumo médio estimado
    # Como você não forneceu consumo médio, vamos só exibir litros totais por mês como referência
    st.markdown("---")
    st.header("Autonomia Estimada")
    st.info("Para calcular autonomia real, forneça consumo médio por km ou outra métrica.")

if __name__ == "__main__":
    main()
