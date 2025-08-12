import streamlit as st
import pandas as pd
import plotly.express as px

@st.cache_data
def carregar_planilha(arquivo):
    try:
        df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
        df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')
        return df_interno, df_externo
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None, None

def limpa_monetario(col):
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True).str.replace(',', '.'), errors='coerce')

def prepara_dados(df_int, df_ext):
    # Interno
    df_int['Data'] = pd.to_datetime(df_int['Data'], dayfirst=True, errors='coerce')
    df_int = df_int.dropna(subset=['Data'])
    df_int['Quantidade de litros'] = pd.to_numeric(df_int['Quantidade de litros'], errors='coerce')
    df_int['KM Atual'] = pd.to_numeric(df_int['KM Atual'], errors='coerce')
    df_int['Valor Unitario'] = limpa_monetario(df_int.get('Valor Unitario', pd.Series()))
    df_int['Valor Total'] = pd.to_numeric(df_int.get('Valor Total', pd.Series()), errors='coerce')
    df_int['Origem'] = 'Interno'
    df_int['Tipo'] = df_int['Tipo'].str.lower()

    # Externo
    df_ext['Data'] = pd.to_datetime(df_ext['Data'], dayfirst=True, errors='coerce')
    df_ext = df_ext.dropna(subset=['Data'])
    df_ext['Quantidade de litros'] = pd.to_numeric(df_ext['Quantidade de litros'], errors='coerce')
    df_ext['KM Atual'] = pd.to_numeric(df_ext['KM Atual'], errors='coerce')
    df_ext['Valor Unitario'] = limpa_monetario(df_ext.get('Valor Unitario', pd.Series()))
    df_ext['Valor Total'] = limpa_monetario(df_ext.get('Valor Total', pd.Series()))
    df_ext['Origem'] = 'Externo'
    df_ext['Tipo'] = 'externo'

    return df_int, df_ext

def calcula_preco_medio_entrada(df_int):
    entradas = df_int[(df_int['Tipo'] == 'entrada') & (df_int['Placa'].isin(['-', None, '']) | df_int['Placa'].isna())]
    if entradas.empty:
        return 0
    litros_totais = entradas['Quantidade de litros'].sum()
    valor_total = (entradas['Quantidade de litros'] * entradas['Valor Unitario']).sum()
    return valor_total / litros_totais if litros_totais > 0 else 0

def prepara_consumo(df_int, df_ext):
    preco_entrada = calcula_preco_medio_entrada(df_int)
    saidas = df_int[df_int['Tipo'] == 'saída'].copy()
    saidas['Valor Unitario Calc'] = preco_entrada
    saidas['Valor Total Calc'] = saidas['Quantidade de litros'] * preco_entrada
    df_comb = pd.concat([
        saidas[['Data','Placa','Quantidade de litros','Valor Unitario Calc','Valor Total Calc','KM Atual','Origem']],
        df_ext[['Data','Placa','Quantidade de litros','Valor Unitario','Valor Total','KM Atual','Origem']]
    ], ignore_index=True)
    # Ajustes
    df_comb['Valor Unitario'] = df_comb['Valor Unitario'].fillna(df_comb.get('Valor Unitario Calc'))
    df_comb['Valor Total'] = df_comb['Valor Total'].fillna(df_comb.get('Valor Total Calc'))
    df_comb = df_comb.dropna(subset=['Placa','Quantidade de litros','Data'])
    return df_comb

def calcula_autonomia(df):
    resultados = []
    for placa, g in df.groupby('Placa'):
        km_max = g['KM Atual'].max()
        km_min = g['KM Atual'].min()
        litros = g['Quantidade de litros'].sum()
        autonomia = (km_max - km_min) / litros if litros > 0 and pd.notnull(km_max) and pd.notnull(km_min) else None
        resultados.append({'Placa': placa, 'Autonomia (km/L)': autonomia})
    return pd.DataFrame(resultados).sort_values('Autonomia (km/L)', ascending=False)

def main():
    st.title("🚛 Insights da Frota - Abastecimento")

    arquivo = st.file_uploader("Faça upload da planilha Excel com as abas 'Abastecimento Interno' e 'Abastecimento Externo'", type='xlsx')
    if not arquivo:
        st.info("Aguardando upload do arquivo...")
        return

    df_interno, df_externo = carregar_planilha(arquivo)
    if df_interno is None or df_externo is None:
        return

    df_interno, df_externo = prepara_dados(df_interno, df_externo)
    df_comb = prepara_consumo(df_interno, df_externo)

    placas = ['Todas'] + sorted(df_comb['Placa'].dropna().unique())
    placa_sel = st.sidebar.selectbox("Selecionar Placa", placas)
    data_min = df_comb['Data'].min().date()
    data_max = df_comb['Data'].max().date()
    data_range = st.sidebar.date_input("Selecione o período", [data_min, data_max], min_value=data_min, max_value=data_max)

    df_filtro = df_comb.copy()
    if placa_sel != 'Todas':
        df_filtro = df_filtro[df_filtro['Placa'] == placa_sel]
    if len(data_range) == 2:
        dt_ini, dt_fim = pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])
        df_filtro = df_filtro[(df_filtro['Data'] >= dt_ini) & (df_filtro['Data'] <= dt_fim)]

    if df_filtro.empty:
        st.warning("Nenhum dado encontrado com os filtros aplicados.")
        return

    # Métricas gerais
    litros_totais = df_filtro['Quantidade de litros'].sum()
    valor_total = df_filtro['Valor Total'].sum()
    preco_medio = valor_total / litros_totais if litros_totais > 0 else 0
    st.subheader("📊 Métricas Gerais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Litros Totais", f"{litros_totais:,.2f} L")
    col2.metric("Valor Total Gasto", f"R$ {valor_total:,.2f}")
    col3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f}")

    # Autonomia
    st.subheader("🚙 Autonomia (km/l) por Veículo")
    autonomia_df = calcula_autonomia(df_filtro)
    autonomia_df["Autonomia (km/L)"] = autonomia_df["Autonomia (km/L)"].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A")
    st.dataframe(autonomia_df)

    # Evolução mensal
    df_filtro['AnoMes'] = df_filtro['Data'].dt.to_period('M').astype(str)
    litros_mes = df_filtro.groupby('AnoMes')['Quantidade de litros'].sum().reset_index()
    preco_mes = df_filtro.groupby('AnoMes').apply(lambda x: x['Valor Total'].sum()/x['Quantidade de litros'].sum() if x['Quantidade de litros'].sum()>0 else 0).reset_index(name='Preço Médio')

    st.subheader("⛽ Evolução Mensal de Litros Abastecidos")
    fig_litros = px.bar(litros_mes, x='AnoMes', y='Quantidade de litros', labels={'AnoMes':'Mês', 'Quantidade de litros':'Litros'}, title="Litros Mensais")
    st.plotly_chart(fig_litros, use_container_width=True)

    st.subheader("💲 Evolução Mensal do Preço Médio por Litro")
    fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', markers=True, labels={'AnoMes':'Mês', 'Preço Médio':'R$ / Litro'}, title="Preço Médio Mensal")
    st.plotly_chart(fig_preco, use_container_width=True)

if __name__ == "__main__":
    main()
