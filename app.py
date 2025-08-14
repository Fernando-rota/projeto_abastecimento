import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------
# Funções auxiliares
# ---------------------------
@st.cache_data
def carregar_planilha(arquivo):
    try:
        df = pd.read_excel(arquivo)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None

def limpa_monetario(col):
    """Remove R$, substitui vírgula por ponto e converte para float"""
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True).str.replace(',', '.'), errors='coerce')

def prepara_dados(df):
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(columns={
        "valor unitario": "valor_unitario",
        "valor tot": "valor_total",
        "km atu": "km atual",
        "descrição despe": "descrição despesa"
    })
    df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['data'])
    df['quantidade de litros'] = pd.to_numeric(df['quantidade de litros'], errors='coerce')
    df['km atual'] = pd.to_numeric(df['km atual'], errors='coerce')
    df['valor_unitario'] = limpa_monetario(df.get('valor_unitario', pd.Series()))
    df['valor_total'] = limpa_monetario(df.get('valor_total', pd.Series()))
    df['tipo'] = df['tipo'].str.lower()
    return df

def calcula_autonomia(df):
    resultados = []
    # Filtra apenas linhas válidas
    df_valid = df.dropna(subset=['km atual','quantidade de litros'])
    df_valid = df_valid[df_valid['km atual'] > 0]
    
    for placa, g in df_valid.groupby('placa'):
        km_max = g['km atual'].max()
        km_min = g['km atual'].min()
        litros = g['quantidade de litros'].sum()
        autonomia = (km_max - km_min) / litros if litros > 0 and km_max > km_min else None
        resultados.append({'Placa': placa, 'Autonomia (km/L)': autonomia})
    
    return pd.DataFrame(resultados).sort_values('Autonomia (km/L)', ascending=False)

# ---------------------------
# Streamlit App
# ---------------------------
def main():
    st.title("🚛 Insights da Frota - Abastecimento")

    arquivo = st.file_uploader("Faça upload da planilha Excel", type='xlsx')
    if not arquivo:
        st.info("Aguardando upload do arquivo...")
        return

    df = carregar_planilha(arquivo)
    if df is None:
        return

    df = prepara_dados(df)
    df['AnoMes'] = df['data'].dt.to_period('M').astype(str)

    # ---------------------------
    # Filtros
    # ---------------------------
    placas = ['Todas'] + sorted(df['placa'].dropna().unique())
    placa_sel = st.sidebar.selectbox("Selecionar Placa", placas)

    combustiveis = ['Todos'] + sorted(df['descrição despesa'].dropna().unique())
    combustivel_sel = st.sidebar.selectbox("Selecionar Combustível", combustiveis)

    data_min = df['data'].min().date()
    data_max = df['data'].max().date()
    data_range = st.sidebar.date_input("Selecione o período", [data_min, data_max], min_value=data_min, max_value=data_max)

    df_filtro = df.copy()
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

    # ---------------------------
    # Métricas Gerais
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
    # Autonomia
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
    preco_mes = df_filtro.dropna(subset=['quantidade de litros','valor_total']).groupby(
        ['AnoMes','descrição despesa']
    ).apply(lambda x: x['valor_total'].sum()/x['quantidade de litros'].sum() if x['quantidade de litros'].sum() > 0 else 0
    ).reset_index().rename(columns={0:'Preço Médio'})
    fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color='descrição despesa', markers=True,
                        labels={'AnoMes':'Mês','Preço Médio':'R$ / Litro'},
                        title="Preço Médio Mensal por Combustível")
    st.plotly_chart(fig_preco, use_container_width=True)

    # ---------------------------
    # Comparativo Interno x Externo
    # ---------------------------
    st.subheader("📊 Comparativo Mensal Interno x Externo (Litros)")
    comparativo = df_filtro.groupby(['AnoMes','tipo'])['quantidade de litros'].sum().reset_index()
    fig_comp = px.bar(comparativo, x='AnoMes', y='quantidade de litros', color='tipo',
                      barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros','tipo':'Origem'},
                      title="Abastecimento Interno x Externo Mensal")
    st.plotly_chart(fig_comp, use_container_width=True)

if __name__ == "__main__":
    main()
