import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------
# Funções auxiliares
# ---------------------------
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
    df_int.columns = df_int.columns.str.strip().str.lower()
    df_ext.columns = df_ext.columns.str.strip().str.lower()
    
    df_int = df_int.rename(columns={"valor total": "valor_total", "valor unitario": "valor_unitario"})
    df_ext = df_ext.rename(columns={"valor total": "valor_total", "valor unitario": "valor_unitario"})

    df_int['data'] = pd.to_datetime(df_int['data'], dayfirst=True, errors='coerce')
    df_int = df_int.dropna(subset=['data'])
    df_int['quantidade de litros'] = pd.to_numeric(df_int['quantidade de litros'], errors='coerce')
    df_int['km atual'] = pd.to_numeric(df_int['km atual'], errors='coerce')
    df_int['valor_unitario'] = limpa_monetario(df_int.get('valor_unitario', pd.Series()))
    df_int['valor_total'] = pd.to_numeric(df_int.get('valor_total', pd.Series()), errors='coerce')
    df_int['origem'] = 'Interno'
    df_int['tipo'] = df_int['tipo'].str.lower()

    df_ext['data'] = pd.to_datetime(df_ext['data'], dayfirst=True, errors='coerce')
    df_ext = df_ext.dropna(subset=['data'])
    df_ext['quantidade de litros'] = pd.to_numeric(df_ext['quantidade de litros'], errors='coerce')
    df_ext['km atual'] = pd.to_numeric(df_ext['km atual'], errors='coerce')
    df_ext['valor_unitario'] = limpa_monetario(df_ext.get('valor_unitario', pd.Series()))
    df_ext['valor_total'] = limpa_monetario(df_ext.get('valor_total', pd.Series()))
    df_ext['origem'] = 'Externo'
    df_ext['tipo'] = 'externo'

    return df_int, df_ext

def calcula_preco_medio_entrada(df_int):
    entradas = df_int[(df_int['tipo'] == 'entrada') & (df_int['placa'].isin(['-', None, '']) | df_int['placa'].isna())]
    if entradas.empty:
        return 0
    litros_totais = entradas['quantidade de litros'].sum()
    valor_total = (entradas['quantidade de litros'] * entradas['valor_unitario']).sum()
    return valor_total / litros_totais if litros_totais > 0 else 0

def prepara_consumo(df_int, df_ext):
    preco_entrada = calcula_preco_medio_entrada(df_int)
    saidas = df_int[df_int['tipo'] == 'saída'].copy()
    saidas['valor_unitario_calc'] = preco_entrada
    saidas['valor_total_calc'] = saidas['quantidade de litros'] * preco_entrada

    df_comb = pd.concat([
        saidas[['data','placa','quantidade de litros','valor_unitario_calc','valor_total_calc','km atual','origem','descrição despesa']],
        df_ext[['data','placa','quantidade de litros','valor_unitario','valor_total','km atual','origem','descrição despesa']]
    ], ignore_index=True)

    df_comb['valor_unitario'] = df_comb['valor_unitario'].fillna(df_comb.get('valor_unitario_calc'))
    df_comb['valor_total'] = df_comb['valor_total'].fillna(df_comb.get('valor_total_calc'))
    df_comb = df_comb.dropna(subset=['placa','quantidade de litros','data'])
    return df_comb

def calcula_autonomia(df):
    resultados = []
    for placa, g in df.groupby('placa'):
        km_max = g['km atual'].max()
        km_min = g['km atual'].min()
        litros = g['quantidade de litros'].sum()
        autonomia = (km_max - km_min) / litros if litros > 0 and pd.notnull(km_max) and pd.notnull(km_min) else None
        resultados.append({'Placa': placa, 'Autonomia (km/L)': autonomia})
    return pd.DataFrame(resultados).sort_values('Autonomia (km/L)', ascending=False)

# ---------------------------
# Streamlit App
# ---------------------------
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

    # ---------------------------
    # Filtros gerais
    # ---------------------------
    combustiveis = ['Todos'] + sorted(df_comb['descrição despesa'].dropna().unique())
    combustivel_sel = st.sidebar.selectbox("Selecionar Combustível", combustiveis)

    data_min = df_comb['data'].min().date()
    data_max = df_comb['data'].max().date()
    data_range = st.sidebar.date_input("Selecione o período", [data_min, data_max], min_value=data_min, max_value=data_max)

    df_filtro = df_comb.copy()
    if combustivel_sel != 'Todos':
        df_filtro = df_filtro[df_filtro['descrição despesa'] == combustivel_sel]
    if len(data_range) == 2:
        dt_ini, dt_fim = pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])
        df_filtro = df_filtro[(df_filtro['data'] >= dt_ini) & (df_filtro['data'] <= dt_fim)]

    if df_filtro.empty:
        st.warning("Nenhum dado encontrado com os filtros aplicados.")
        return

    # ---------------------------
    # Abas
    # ---------------------------
    aba1, aba2, aba3, aba4 = st.tabs(["Métricas Gerais", "Autonomia", "Evolução Mensal", "Comparativo Interno x Externo"])

    # ---------------------------
    # Aba 1 - Métricas Gerais
    # ---------------------------
    with aba1:
        st.subheader("📊 Métricas Gerais")
        combustiveis_presentes = df_filtro['descrição despesa'].dropna().unique()
        for comb in combustiveis_presentes:
            df_combustivel = df_filtro[df_filtro['descrição despesa'] == comb]
            df_combustivel = df_combustivel[df_combustivel['valor_total'].notna() & (df_combustivel['valor_total'] > 0)]
            litros_totais = df_combustivel['quantidade de litros'].sum()
            valor_total = df_combustivel['valor_total'].sum()
            preco_medio = valor_total / litros_totais if litros_totais > 0 else 0
            st.markdown(f"**{comb}**")
            col1, col2, col3 = st.columns(3)
            col1.metric("Litros Totais", f"{litros_totais:,.2f} L")
            col2.metric("Valor Total Gasto", f"R$ {valor_total:,.2f}")
            col3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f}")

    # ---------------------------
    # Aba 2 - Autonomia
    # ---------------------------
    with aba2:
        st.subheader("🚙 Autonomia (km/L) por Veículo")
        autonomia_df = calcula_autonomia(df_filtro)
        autonomia_df["Autonomia (km/L)"] = autonomia_df["Autonomia (km/L)"].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A")
        st.dataframe(autonomia_df)

    # ---------------------------
    # Aba 3 - Evolução Mensal
    # ---------------------------
    with aba3:
        df_filtro['AnoMes'] = df_filtro['data'].dt.to_period('M').astype(str)
        st.subheader("⛽ Evolução Mensal de Litros por Combustível")
        litros_mes = df_filtro.groupby(['AnoMes','descrição despesa'])['quantidade de litros'].sum().reset_index()
        fig_litros = px.bar(litros_mes, x='AnoMes', y='quantidade de litros', color='descrição despesa',
                            barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros'},
                            title="Litros Mensais por Combustível")
        st.plotly_chart(fig_litros, use_container_width=True)

        st.subheader("💲 Evolução Mensal do Preço Médio por Litro")
        preco_mes = df_filtro.groupby(['AnoMes','descrição despesa']).apply(
            lambda x: x['valor_total'].sum()/x['quantidade de litros'].sum() if x['quantidade de litros'].sum()>0 else 0
        ).reset_index(name='Preço Médio')
        fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color='descrição despesa', markers=True,
                            labels={'AnoMes':'Mês','Preço Médio':'R$ / Litro'},
                            title="Preço Médio Mensal por Combustível")
        st.plotly_chart(fig_preco, use_container_width=True)

    # ---------------------------
    # Aba 4 - Comparativo Interno x Externo
    # ---------------------------
    with aba4:
        st.subheader("📊 Comparativo: Abastecimento Interno vs Externo")
        df_comparativo = df_filtro[df_filtro['valor_total'].notna() & (df_filtro['valor_total'] > 0)]
        resumo_origem = df_comparativo.groupby('origem').agg(
            litros_totais=('quantidade de litros','sum'),
            valor_total=('valor_total','sum')
        ).reset_index()
        resumo_origem['preco_medio'] = resumo_origem['valor_total'] / resumo_origem['litros_totais']

        cols = st.columns(2)
        for idx, row in resumo_origem.iterrows():
            cols[idx].metric(f"{row['origem']}", f"{row['litros_totais']:,.2f} L", f"R$ {row['preco_medio']:.3f} /L")

        fig_litros_origem = px.bar(resumo_origem, x='origem', y='litros_totais', text='litros_totais',
                                   labels={'origem':'Origem','litros_totais':'Litros Totais'},
                                   title="Litros Totais: Interno x Externo")
        st.plotly_chart(fig_litros_origem, use_container_width=True)

        fig_preco_origem = px.bar(resumo_origem, x='origem', y='preco_medio', text='preco_medio',
                                  labels={'origem':'Origem','preco_medio':'Preço Médio (R$/L)'},
                                  title="Preço Médio por Litro: Interno x Externo")
        st.plotly_chart(fig_preco_origem, use_container_width=True)


if __name__ == "__main__":
    main()
