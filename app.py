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
    """Remove R$, substitui vírgula por ponto e converte para float"""
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True).str.replace(',', '.'), errors='coerce')

def prepara_dados(df_int, df_ext):
    # Padronizar colunas
    df_int.columns = df_int.columns.str.strip().str.lower()
    df_ext.columns = df_ext.columns.str.strip().str.lower()
    
    # Renomear colunas importantes
    df_int = df_int.rename(columns={"valor total": "valor_total", "valor unitario": "valor_unitario"})
    df_ext = df_ext.rename(columns={"valor total": "valor_total", "valor unitario": "valor_unitario"})

    # Interno
    df_int['data'] = pd.to_datetime(df_int['data'], dayfirst=True, errors='coerce')
    df_int = df_int.dropna(subset=['data'])
    df_int['quantidade de litros'] = pd.to_numeric(df_int['quantidade de litros'], errors='coerce')
    df_int['km atual'] = pd.to_numeric(df_int['km atual'], errors='coerce')
    df_int['valor_unitario'] = limpa_monetario(df_int.get('valor_unitario', pd.Series()))
    df_int['valor_total'] = pd.to_numeric(df_int.get('valor_total', pd.Series()), errors='coerce')
    df_int['origem'] = 'Interno'
    df_int['tipo'] = df_int['tipo'].str.lower()
    df_int['placa'] = df_int.get('placa', pd.Series()).astype(str).str.upper().str.strip()
    df_int['placa'].replace(['-', 'NONE', 'NAN', 'NULL', ''], pd.NA, inplace=True)
    df_int['descrição despesa'] = df_int.get('descrição despesa', pd.Series()).astype(str)

    # Externo
    df_ext['data'] = pd.to_datetime(df_ext['data'], dayfirst=True, errors='coerce')
    df_ext = df_ext.dropna(subset=['data'])
    df_ext['quantidade de litros'] = pd.to_numeric(df_ext['quantidade de litros'], errors='coerce')
    df_ext['km atual'] = pd.to_numeric(df_ext['km atual'], errors='coerce')
    df_ext['valor_unitario'] = limpa_monetario(df_ext.get('valor_unitario', pd.Series()))
    df_ext['valor_total'] = limpa_monetario(df_ext.get('valor_total', pd.Series()))
    df_ext['origem'] = 'Externo'
    df_ext['tipo'] = 'externo'
    df_ext['placa'] = df_ext.get('placa', pd.Series()).astype(str).str.upper().str.strip()
    df_ext['placa'].replace(['-', 'NONE', 'NAN', 'NULL', ''], pd.NA, inplace=True)
    df_ext['descrição despesa'] = df_ext.get('descrição despesa', pd.Series()).astype(str)

    return df_int, df_ext

def calcula_preco_medio_entrada(df_int):
    """Calcula preço médio do combustível comprado internamente (placa vazia ou '-')"""
    entradas = df_int[(df_int['tipo'] == 'entrada') & (df_int['placa'].isna())]
    entradas = entradas.dropna(subset=['valor_unitario','quantidade de litros'])
    if entradas.empty:
        return 0
    litros_totais = entradas['quantidade de litros'].sum()
    valor_total = (entradas['quantidade de litros'] * entradas['valor_unitario']).sum()
    return valor_total / litros_totais if litros_totais > 0 else 0

def prepara_consumo(df_int, df_ext):
    preco_entrada = calcula_preco_medio_entrada(df_int)
    # Considerar apenas saídas para abastecimento interno
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
        g = g.dropna(subset=['km atual','quantidade de litros'])
        g = g[g['quantidade de litros'] > 0].sort_values('data')
        if len(g) < 2:
            continue
        km_diff = g['km atual'].diff().iloc[1:]  # diferença entre kms consecutivos
        litros = g['quantidade de litros'].iloc[1:]  # litros correspondentes ao intervalo
        km_diff = km_diff[km_diff > 0]
        litros = litros.loc[km_diff.index]
        if litros.sum() == 0:
            autonomia = None
        else:
            autonomia = km_diff.sum() / litros.sum()
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
    # Filtros
    # ---------------------------
    placas = ['Todas'] + sorted(df_comb['placa'].dropna().unique())
    placa_sel = st.sidebar.selectbox("Selecionar Placa", placas)

    combustiveis = ['Todos'] + sorted(df_comb['descrição despesa'].dropna().unique())
    combustivel_sel = st.sidebar.selectbox("Selecionar Combustível", combustiveis)

    data_min = df_comb['data'].min().date()
    data_max = df_comb['data'].max().date()
    data_range = st.sidebar.date_input("Selecione o período", [data_min, data_max], min_value=data_min, max_value=data_max)

    df_filtro = df_comb.copy()
    if placa_sel != 'Todas':
        df_filtro = df_filtro[df_filtro['placa'] == placa_sel]
    if combustivel_sel != 'Todos':
        df_filtro = df_filtro[df_filtro['descrição despesa'] == combustivel_sel]
    if len(data_range) == 2:
        dt_ini, dt_fim = pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])
        df_filtro = df_filtro[(df_filtro['data'] >= dt_ini) & (df_filtro['data'] <= dt_fim)]

    if df_filtro.empty:
        st.warning("Nenhum dado encontrado com os filtros aplicados.")
        return

    df_filtro['AnoMes'] = df_filtro['data'].dt.to_period('M').astype(str)

    # ---------------------------
    # Aba Métricas Gerais
    # ---------------------------
    st.subheader("📊 Métricas Gerais")
    for comb in df_filtro['descrição despesa'].dropna().unique():
        df_combustivel = df_filtro[df_filtro['descrição despesa'] == comb].dropna(subset=['quantidade de litros','valor_total'])
        litros_totais = df_combustivel['quantidade de litros'].sum()
        valor_total = df_combustivel['valor_total'].sum()
        preco_medio = valor_total / litros_totais if litros_totais > 0 else 0
        st.markdown(f"**{comb}**")
        col1, col2, col3 = st.columns(3)
        col1.metric("Litros Totais", f"{litros_totais:,.2f} L")
        col2.metric("Valor Total Gasto", f"R$ {valor_total:,.2f}")
        col3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f}")

    # ---------------------------
    # Aba Autonomia
    # ---------------------------
    st.subheader("🚙 Autonomia (km/L) por Veículo")
    autonomia_df = calcula_autonomia(df_filtro)
    autonomia_df["Autonomia (km/L)"] = autonomia_df["Autonomia (km/L)"].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A")
    st.dataframe(autonomia_df)

    # ---------------------------
    # Evolução mensal litros por combustível
    # ---------------------------
    st.subheader("⛽ Evolução Mensal de Litros por Combustível")
    litros_mes = df_filtro.groupby(['AnoMes','descrição despesa'])['quantidade de litros'].sum().reset_index()
    fig_litros = px.bar(litros_mes, x='AnoMes', y='quantidade de litros', color='descrição despesa',
                        barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros'},
                        title="Litros Mensais por Combustível")
    st.plotly_chart(fig_litros, use_container_width=True)

    # ---------------------------
    # Evolução mensal preço médio por litro
    # ---------------------------
    st.subheader("💲 Evolução Mensal do Preço Médio por Litro")
    preco_mes = df_filtro.dropna(subset=['quantidade de litros','valor_total']).groupby(['AnoMes','descrição despesa']).apply(
        lambda x: x['valor_total'].sum()/x['quantidade de litros'].sum() if x['quantidade de litros'].sum()>0 else 0
    ).reset_index().rename(columns={0:'Preço Médio'})
    fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color='descrição despesa', markers=True,
                        labels={'AnoMes':'Mês','Preço Médio':'R$ / Litro'},
                        title="Preço Médio Mensal por Combustível")
    st.plotly_chart(fig_preco, use_container_width=True)

    # ---------------------------
    # Comparativo Interno x Externo
    # ---------------------------
    st.subheader("📊 Comparativo Mensal Interno x Externo (Litros)")
    comparativo = df_filtro.groupby(['AnoMes','origem'])['quantidade de litros'].sum().reset_index()
    fig_comp = px.bar(comparativo, x='AnoMes', y='quantidade de litros', color='origem',
                      barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros','origem':'Origem'},
                      title="Abastecimento Interno x Externo Mensal")
    st.plotly_chart(fig_comp, use_container_width=True)

if __name__ == "__main__":
    main()
