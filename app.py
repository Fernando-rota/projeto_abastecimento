import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Dashboard Abastecimento Avançado", layout="wide")

def limpa_monetario(col):
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True), errors='coerce')

def processa_interno(df):
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    df['AnoMes'] = df['Data'].dt.to_period('M').astype(str)
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['Valor Unitario'] = pd.to_numeric(df['Valor Unitario'], errors='coerce')
    df['Valor Total'] = pd.to_numeric(df['Valor Total'], errors='coerce')
    df['KM Atual'] = pd.to_numeric(df['KM Atual'], errors='coerce')
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
    df['KM Atual'] = pd.to_numeric(df['KM Atual'], errors='coerce')
    return df

def calcula_indicadores(df, placa_selecionada, ano_mes_selecionado):
    df_filtrado = df.copy()
    if placa_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Placa'] == placa_selecionada]
    if ano_mes_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['AnoMes'] == ano_mes_selecionado]
    
    litros = df_filtrado['Quantidade de litros'].sum()
    valor = df_filtrado['Valor Total'].sum()
    preco_medio = valor / litros if litros > 0 else 0
    
    # Cálculo da autonomia = (km_max - km_min) / litros_totais, se possível
    km_max = df_filtrado['KM Atual'].max()
    km_min = df_filtrado['KM Atual'].min()
    autonomia = ((km_max - km_min) / litros) if litros > 0 and pd.notna(km_max) and pd.notna(km_min) else None
    
    return litros, valor, preco_medio, autonomia

def plota_litros_mes(df, placa_selecionada):
    df_plot = df.copy()
    if placa_selecionada != "Todas":
        df_plot = df_plot[df_plot['Placa'] == placa_selecionada]
    agrupado = df_plot.groupby('AnoMes')['Quantidade de litros'].sum().reset_index()
    if agrupado.empty:
        st.info("Sem dados para os filtros selecionados.")
        return
    plt.figure(figsize=(10,4))
    sns.barplot(x='AnoMes', y='Quantidade de litros', data=agrupado, color='green')
    plt.xticks(rotation=45)
    plt.title(f"Litros mês a mês - placa: {placa_selecionada}")
    plt.ylabel("Litros")
    plt.xlabel("Mês")
    st.pyplot(plt.gcf())
    plt.clf()

def plota_preco_medio_mes(df, placa_selecionada):
    df_plot = df.copy()
    if placa_selecionada != "Todas":
        df_plot = df_plot[df_plot['Placa'] == placa_selecionada]
    agrupado = df_plot.groupby('AnoMes').apply(
        lambda x: x['Valor Total'].sum() / x['Quantidade de litros'].sum() if x['Quantidade de litros'].sum() > 0 else 0
    ).reset_index(name='Preco Medio')
    if agrupado.empty:
        st.info("Sem dados para os filtros selecionados.")
        return
    plt.figure(figsize=(10,4))
    sns.lineplot(x='AnoMes', y='Preco Medio', data=agrupado, marker='o', color='blue')
    plt.xticks(rotation=45)
    plt.title(f"Preço médio do litro mês a mês - placa: {placa_selecionada}")
    plt.ylabel("Preço Médio (R$/L)")
    plt.xlabel("Mês")
    st.pyplot(plt.gcf())
    plt.clf()

def main():
    st.title("🚛 Dashboard Abastecimento - Indicadores Dinâmicos e Autonomia")

    arquivo = st.sidebar.file_uploader("Upload planilha Excel com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xlsx'])
    if arquivo is None:
        st.warning("Faça upload do arquivo para continuar.")
        return

    df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
    df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')

    df_interno = processa_interno(df_interno)
    df_externo = processa_externo(df_externo)

    # Listas de placas e meses
    placas_interno = sorted(df_interno['Placa'].dropna().unique())
    placas_externo = sorted(df_externo['Placa'].dropna().unique())
    placas = sorted(set(placas_interno) | set(placas_externo))
    placas.insert(0, "Todas")

    meses_interno = sorted(df_interno['AnoMes'].dropna().unique())
    meses_externo = sorted(df_externo['AnoMes'].dropna().unique())
    meses = sorted(set(meses_interno) | set(meses_externo))
    meses.insert(0, "Todos")

    # Seleções dinâmicas
    st.sidebar.header("Filtros")
    placa_selecionada_interno = st.sidebar.selectbox("Placa - Abastecimento Interno", placas)
    mes_selecionado_interno = st.sidebar.selectbox("Mês - Abastecimento Interno", meses)

    placa_selecionada_externo = st.sidebar.selectbox("Placa - Abastecimento Externo", placas)
    mes_selecionado_externo = st.sidebar.selectbox("Mês - Abastecimento Externo", meses)

    # Indicadores internos
    litros_i, valor_i, preco_i, autonomia_i = calcula_indicadores(df_interno, placa_selecionada_interno, mes_selecionado_interno)
    # Indicadores externos
    litros_e, valor_e, preco_e, autonomia_e = calcula_indicadores(df_externo, placa_selecionada_externo, mes_selecionado_externo)

    st.header("📊 Indicadores - Abastecimento Interno")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Litros", f"{litros_i:.2f} L")
    col2.metric("Valor Total", f"R$ {valor_i:.2f}")
    col3.metric("Preço Médio", f"R$ {preco_i:.3f} / L")
    col4.metric("Autonomia (km/L)", f"{autonomia_i:.3f}" if autonomia_i is not None else "N/A")

    st.subheader("Gráficos - Abastecimento Interno")
    plota_litros_mes(df_interno, placa_selecionada_interno)
    plota_preco_medio_mes(df_interno, placa_selecionada_interno)

    st.markdown("---")

    st.header("📊 Indicadores - Abastecimento Externo")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Litros", f"{litros_e:.2f} L")
    col2.metric("Valor Total", f"R$ {valor_e:.2f}")
    col3.metric("Preço Médio", f"R$ {preco_e:.3f} / L")
    col4.metric("Autonomia (km/L)", f"{autonomia_e:.3f}" if autonomia_e is not None else "N/A")

    st.subheader("Gráficos - Abastecimento Externo")
    plota_litros_mes(df_externo, placa_selecionada_externo)
    plota_preco_medio_mes(df_externo, placa_selecionada_externo)

if __name__ == "__main__":
    main()
