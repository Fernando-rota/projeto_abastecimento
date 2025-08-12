import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

@st.cache_data
def carregar_dados(arquivo):
    try:
        df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
        df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')
        return df_interno, df_externo
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
        return None, None

def limpa_monetario(col):
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True).str.replace(',', '.'), errors='coerce')

def prepara_dados(df_interno, df_externo):
    # --- Interno ---
    df_interno['Data'] = pd.to_datetime(df_interno['Data'], dayfirst=True, errors='coerce')
    df_interno = df_interno.dropna(subset=['Data'])
    df_interno['AnoMes'] = df_interno['Data'].dt.to_period('M').astype(str)
    df_interno['Quantidade de litros'] = pd.to_numeric(df_interno['Quantidade de litros'], errors='coerce')
    df_interno['KM Atual'] = pd.to_numeric(df_interno['KM Atual'], errors='coerce')
    df_interno['Valor Unitario'] = limpa_monetario(df_interno.get('Valor Unitario', pd.Series()))
    df_interno['Valor Total'] = pd.to_numeric(df_interno.get('Valor Total', pd.Series()), errors='coerce')
    df_interno['Origem'] = 'Interno'
    df_interno['Tipo'] = df_interno['Tipo'].str.lower()

    # --- Externo ---
    df_externo['Data'] = pd.to_datetime(df_externo['Data'], dayfirst=True, errors='coerce')
    df_externo = df_externo.dropna(subset=['Data'])
    df_externo['AnoMes'] = df_externo['Data'].dt.to_period('M').astype(str)
    df_externo['Quantidade de litros'] = pd.to_numeric(df_externo['Quantidade de litros'], errors='coerce')
    df_externo['KM Atual'] = pd.to_numeric(df_externo['KM Atual'], errors='coerce')
    df_externo['Valor Unitario'] = limpa_monetario(df_externo.get('Valor Unitario', pd.Series()))
    df_externo['Valor Total'] = limpa_monetario(df_externo.get('Valor Total', pd.Series()))
    df_externo['Origem'] = 'Externo'
    df_externo['Tipo'] = 'externo'

    return df_interno, df_externo

def calcula_preco_medio_entrada(df_interno):
    # Preço médio por litro das entradas no tanque (placa "-")
    entradas = df_interno[(df_interno['Tipo'] == 'entrada')]
    # Supondo que entrada no tanque não tem placa ou placa '-'
    entradas = entradas[entradas['Placa'].isin(['-', None, ''] ) | entradas['Placa'].isna()]
    if entradas.empty:
        return 0
    litros_totais = entradas['Quantidade de litros'].sum()
    valor_total = (entradas['Quantidade de litros'] * entradas['Valor Unitario']).sum()
    preco_medio = valor_total / litros_totais if litros_totais > 0 else 0
    return preco_medio

def prepara_consumo(df_interno, df_externo):
    # preço médio entrada tanque interno
    preco_entrada = calcula_preco_medio_entrada(df_interno)

    # Filtra saídas (abastecimentos para veículos)
    saidas = df_interno[df_interno['Tipo'] == 'saída'].copy()
    # Substituir Valor Unitario das saídas pelo preco médio calculado
    saidas['Valor Unitario Calc'] = preco_entrada
    saidas['Valor Total Calc'] = saidas['Quantidade de litros'] * preco_entrada

    # Concatenar abastecimento externo e interno saída (abastecimento real)
    df_comb = pd.concat([
        saidas[['Data','Placa','Quantidade de litros','Valor Unitario','Valor Total','KM Atual','Origem']],
        df_externo[['Data','Placa','Quantidade de litros','Valor Unitario','Valor Total','KM Atual','Origem']]
    ], ignore_index=True)

    # Ajustes para valores faltantes em Valor Total e Unitario no externo
    df_comb['Valor Unitario'] = df_comb['Valor Unitario'].fillna(df_comb['Valor Total'] / df_comb['Quantidade de litros'])
    df_comb['Valor Total'] = df_comb['Valor Total'].fillna(df_comb['Quantidade de litros'] * df_comb['Valor Unitario'])

    # Remove linhas sem placa ou litros
    df_comb = df_comb.dropna(subset=['Placa', 'Quantidade de litros', 'Data'])

    return df_comb

def calcula_autonomia(df):
    # autonomia por placa = (km max - km min) / total litros
    resultados = []
    for placa, g in df.groupby('Placa'):
        km_max = g['KM Atual'].max()
        km_min = g['KM Atual'].min()
        litros = g['Quantidade de litros'].sum()
        if pd.notnull(km_max) and pd.notnull(km_min) and litros > 0:
            autonomia = (km_max - km_min) / litros
        else:
            autonomia = np.nan
        resultados.append({'Placa': placa, 'Autonomia (km/L)': autonomia})
    df_auto = pd.DataFrame(resultados).sort_values(by='Autonomia (km/L)', ascending=False)
    return df_auto

def calcula_custo_por_km(df_comb):
    resultados = []
    for placa, g in df_comb.groupby('Placa'):
        km_max = g['KM Atual'].max()
        km_min = g['KM Atual'].min()
        km_rodados = km_max - km_min if pd.notnull(km_max) and pd.notnull(km_min) else np.nan
        custo_total = g['Valor Total'].sum()
        custo_km = custo_total / km_rodados if km_rodados > 0 else np.nan
        resultados.append({'Placa': placa, 'Custo Total (R$)': custo_total, 'Km Rodados': km_rodados, 'Custo por Km (R$)': custo_km})
    df_custo = pd.DataFrame(resultados).sort_values(by='Custo por Km (R$)')
    return df_custo

def main():
    st.title("🚛 Dashboard Avançado de Abastecimento")

    arquivo = st.sidebar.file_uploader("Faça upload da planilha Excel com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xlsx'])
    if arquivo is None:
        st.warning("Por favor, faça upload do arquivo para continuar.")
        return

    df_interno, df_externo = carregar_dados(arquivo)
    if df_interno is None or df_externo is None:
        return

    df_interno, df_externo = prepara_dados(df_interno, df_externo)

    df_comb = prepara_consumo(df_interno, df_externo)

    # Filtros
    placas = ['Todas'] + sorted(df_comb['Placa'].dropna().unique())
    origens = ['Todos', 'Interno', 'Externo']  # Origem aqui reflete a origem original, mas para combinado só temos "Interno" e "Externo"
    data_min = df_comb['Data'].min().date()
    data_max = df_comb['Data'].max().date()

    st.sidebar.header("Filtros")
    placa_sel = st.sidebar.selectbox("Selecione a placa", placas)
    data_range = st.sidebar.date_input("Selecione o período", [data_min, data_max], min_value=data_min, max_value=data_max)

    # Filtra o dataframe combinado
    df_filtrado = df_comb.copy()
    if placa_sel != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Placa'] == placa_sel]

    if len(data_range) == 2:
        dt_inicio, dt_fim = pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])
        df_filtrado = df_filtrado[(df_filtrado['Data'] >= dt_inicio) & (df_filtrado['Data'] <= dt_fim)]

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros aplicados.")
        return

    # Indicadores gerais
    litros_totais = df_filtrado['Quantidade de litros'].sum()
    valor_total = df_filtrado['Valor Total'].sum()
    preco_medio = valor_total / litros_totais if litros_totais > 0 else 0

    # Autonomia e custo por km
    autonomia_df = calcula_autonomia(df_filtrado)
    custo_df = calcula_custo_por_km(df_filtrado)

    # Mesclando indicadores para ranking
    df_rank = autonomia_df.merge(custo_df, on='Placa', how='outer')
    df_rank['Autonomia (km/L)'] = df_rank['Autonomia (km/L)'].round(3)
    df_rank['Custo Total (R$)'] = df_rank['Custo Total (R$)'].round(2)
    df_rank['Custo por Km (R$)'] = df_rank['Custo por Km (R$)'].round(4)

    # Ranking eficiência (top 25% melhor autonomia)
    q1 = df_rank['Autonomia (km/L)'].quantile(0.25)
    q3 = df_rank['Autonomia (km/L)'].quantile(0.75)

    def classifica_eficiencia(x):
        if pd.isna(x):
            return 'Sem dados'
        elif x >= q3:
            return 'Econômico'
        elif x <= q1:
            return 'Ineficiente'
        else:
            return 'Normal'

    df_rank['Classificação'] = df_rank['Autonomia (km/L)'].apply(classifica_eficiencia)

    # Gráficos de tendência mensal (litros e custo médio)
    df_filtrado['AnoMes'] = df_filtrado['Data'].dt.to_period('M').astype(str)
    litros_mes = df_filtrado.groupby(['AnoMes']).agg({'Quantidade de litros':'sum'}).reset_index()
    custo_mes = df_filtrado.groupby(['AnoMes']).apply(lambda x: x['Valor Total'].sum()/x['Quantidade de litros'].sum() if x['Quantidade de litros'].sum()>0 else 0).reset_index(name='Preço Médio')

    # Layout com abas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Resumo Geral",
        "🚛 Ranking Eficiência",
        "⛽ Tendência Mensal",
        "💲 Custo por Km"
    ])

    with tab1:
        st.header("Resumo Geral do Período")
        c1, c2, c3 = st.columns(3)
        c1.metric("Litros Totais", f"{litros_totais:,.2f} L")
        c2.metric("Valor Total Gasto", f"R$ {valor_total:,.2f}")
        c3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f} / L")

    with tab2:
        st.header("Ranking de Eficiência dos Veículos")
        st.dataframe(df_rank.style.format({
            'Autonomia (km/L)': "{:.3f}",
            'Custo Total (R$)': "R$ {:,.2f}",
            'Custo por Km (R$)': "R$ {:.4f}"
        }).set_precision(3))

    with tab3:
        st.header("Tendência Mensal de Litros Abastecidos")
        fig1 = px.bar(litros_mes, x='AnoMes', y='Quantidade de litros', labels={'AnoMes':'Mês', 'Quantidade de litros':'Litros'}, title="Litros Mensais Abastecidos")
        st.plotly_chart(fig1, use_container_width=True)

        st.header("Tendência Mensal do Preço Médio por Litro")
        fig2 = px.line(custo_mes, x='AnoMes', y='Preço Médio', markers=True, labels={'AnoMes':'Mês', 'Preço Médio':'R$ / Litro'}, title="Preço Médio Mensal")
        st.plotly_chart(fig2, use_container_width=True)

    with tab4:
        st.header("Custo por Km Rodado por Veículo")
        st.dataframe(df_rank[['Placa', 'Km Rodados', 'Custo por Km (R$)']].sort_values(by='Custo por Km (R$)'))

if __name__ == "__main__":
    main()
