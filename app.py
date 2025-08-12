import streamlit as st
import pandas as pd
import plotly.express as px

def limpa_monetario(col):
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True), errors='coerce')

def processa_abastecimento(df, interno=True):
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    df['AnoMes'] = df['Data'].dt.to_period('M').astype(str)
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['Valor Total'] = pd.to_numeric(df['Valor Total'], errors='coerce') if 'Valor Total' in df.columns else None
    if 'Valor Unitario' in df.columns:
        df['Valor Unitario'] = limpa_monetario(df['Valor Unitario'])
    df['KM Atual'] = pd.to_numeric(df['KM Atual'], errors='coerce')
    df['Origem'] = 'Interno' if interno else 'Externo'
    # Para interno, filtra tipo == entrada
    if interno and 'Tipo' in df.columns:
        df = df[df['Tipo'].str.lower() == 'entrada']
    return df

def calcula_autonomia(df):
    autonomia = {}
    for placa, grupo in df.groupby('Placa'):
        km_max = grupo['KM Atual'].max()
        km_min = grupo['KM Atual'].min()
        litros = grupo['Quantidade de litros'].sum()
        if pd.notna(km_max) and pd.notna(km_min) and litros > 0:
            autonomia[placa] = (km_max - km_min) / litros
        else:
            autonomia[placa] = None
    return autonomia

def main():
    st.title("🚛 Dashboard Integrado de Abastecimento")

    arquivo = st.sidebar.file_uploader("Upload da planilha Excel com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xlsx'])
    if arquivo is None:
        st.warning("Faça upload do arquivo para continuar.")
        return

    df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
    df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')

    df_interno = processa_abastecimento(df_interno, interno=True)
    df_externo = processa_abastecimento(df_externo, interno=False)

    # Junta as duas abas num dataframe só
    df = pd.concat([df_interno, df_externo], ignore_index=True)

    # Remove placas ou dados inválidos
    df = df.dropna(subset=['Placa', 'Quantidade de litros', 'Data'])

    # Filtros dinâmicos
    placas = ['Todas'] + sorted(df['Placa'].dropna().unique())
    anos_meses = ['Todos'] + sorted(df['AnoMes'].unique())

    st.sidebar.header("Filtros")
    placa_sel = st.sidebar.selectbox("Selecione a placa", placas)
    ano_mes_sel = st.sidebar.selectbox("Selecione o mês (AAAA-MM)", anos_meses)

    df_filtrado = df.copy()
    if placa_sel != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Placa'] == placa_sel]
    if ano_mes_sel != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['AnoMes'] == ano_mes_sel]

    # Indicadores gerais
    litros_totais = df_filtrado['Quantidade de litros'].sum()
    valor_total = df_filtrado['Valor Total'].sum()
    preco_medio = valor_total / litros_totais if litros_totais > 0 else 0

    st.header("📈 Indicadores Gerais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Litros Totais", f"{litros_totais:.2f} L")
    col2.metric("Valor Total Gasto", f"R$ {valor_total:.2f}")
    col3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f} / L")

    # Autonomia por placa (com base no filtro, ou para todas se filtro 'Todas')
    autonomia_dict = calcula_autonomia(df_filtrado)
    st.subheader("Autonomia por Veículo (km/litro)")

    # Mostra numa tabela interativa
    autonomia_df = pd.DataFrame([
        {'Placa': placa, 'Autonomia (km/L)': f"{val:.3f}" if val is not None else "N/A"}
        for placa, val in autonomia_dict.items()
    ]).sort_values('Placa')

    st.dataframe(autonomia_df)

    # Gráfico litros mês a mês por origem (interno x externo)
    st.subheader("Litros Mensais por Origem")
    df_agrupado = df.groupby(['AnoMes', 'Origem']).agg({'Quantidade de litros': 'sum'}).reset_index()
    if placa_sel != 'Todas':
        df_agrupado = df_agrupado[df_agrupado['Placa'] == placa_sel] if 'Placa' in df_agrupado.columns else df_agrupado
    fig1 = px.bar(df_agrupado, x='AnoMes', y='Quantidade de litros', color='Origem',
                  labels={'AnoMes': 'Mês', 'Quantidade de litros': 'Litros'}, barmode='group',
                  title='Litros Mensais - Interno x Externo')
    st.plotly_chart(fig1, use_container_width=True)

    # Gráfico preço médio mês a mês por origem
    st.subheader("Preço Médio Mensal por Origem")
    df_precos = df.groupby(['AnoMes', 'Origem']).apply(
        lambda x: x['Valor Total'].sum() / x['Quantidade de litros'].sum() if x['Quantidade de litros'].sum() > 0 else 0
    ).reset_index(name='Preco Medio')
    fig2 = px.line(df_precos, x='AnoMes', y='Preco Medio', color='Origem',
                   labels={'AnoMes': 'Mês', 'Preco Medio': 'R$ / Litro'}, markers=True,
                   title='Preço Médio Mensal - Interno x Externo')
    st.plotly_chart(fig2, use_container_width=True)

    # Filtro rápido por veículo na tabela de autonomia: link para selecionar placa (não implementado, mas podemos criar dropdown para filtrar)

if __name__ == "__main__":
    main()
