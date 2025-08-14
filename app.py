import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------
# Funções auxiliares
# ---------------------------
@st.cache_data
def carregar_planilha(arquivo):
    try:
        df_int = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
        df_ext = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')
        return df_int, df_ext
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None, None

def padroniza_colunas(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    # Garante que colunas essenciais existam
    for col in ['valor_unitario','valor_total','quantidade_de_litros','km_atual','descricao_despesa']:
        if col not in df.columns:
            df[col] = 0 if 'valor' in col or 'quantidade' in col else ''
    return df

def limpa_monetario(col):
    return pd.to_numeric(col.astype(str)
                         .str.replace(r'R\$\s*', '', regex=True)
                         .str.replace(',', '.'), errors='coerce')

def padroniza_placa(serie):
    s = serie.astype(str).str.upper().str.strip()
    s = s.replace(['-', 'NONE', 'NAN', 'NULL', '', 'CORREÇÃO'], pd.NA)
    return s

def prepara_dados(df_int, df_ext):
    df_int = padroniza_colunas(df_int)
    df_ext = padroniza_colunas(df_ext)

    # Datas e placas
    for df in [df_int, df_ext]:
        df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['data'])
        df['placa'] = padroniza_placa(df['placa'])
        df['quantidade_de_litros'] = pd.to_numeric(df['quantidade_de_litros'], errors='coerce')
        df['valor_unitario'] = limpa_monetario(df['valor_unitario'])
        df['valor_total'] = pd.to_numeric(df['valor_total'], errors='coerce')
        df['km_atual'] = pd.to_numeric(df['km_atual'], errors='coerce')
    df_int['origem'] = 'Interno'
    df_ext['origem'] = 'Externo'
    return df_int, df_ext

def calcula_autonomia(df):
    resultados = []
    for placa, g in df.groupby('placa'):
        if pd.isna(placa):
            continue
        g = g[g['quantidade_de_litros'] > 0].sort_values('data')
        if len(g) < 2:
            continue
        km_max = g['km_atual'].max()
        km_min = g['km_atual'].min()
        litros = g['quantidade_de_litros'].sum()
        autonomia = (km_max - km_min) / litros if litros > 0 else None
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

    df_int, df_ext = carregar_planilha(arquivo)
    if df_int is None or df_ext is None:
        return

    df_int, df_ext = prepara_dados(df_int, df_ext)

    # Junta abas
    df_comb = pd.concat([df_int, df_ext], ignore_index=True)
    df_comb = df_comb.dropna(subset=['placa','quantidade_de_litros'])
    df_comb = df_comb[df_comb['quantidade_de_litros'] > 0]
    df_comb['AnoMes'] = df_comb['data'].dt.to_period('M').astype(str)

    # ---------------------------
    # Filtros
    # ---------------------------
    placas = ['Todas'] + sorted(df_comb['placa'].dropna().unique())
    placa_sel = st.sidebar.selectbox("Selecionar Placa", placas)

    combustiveis = ['Todos'] + sorted(df_comb['descricao_despesa'].dropna().unique())
    combustivel_sel = st.sidebar.selectbox("Selecionar Combustível", combustiveis)

    data_min = df_comb['data'].min().date()
    data_max = df_comb['data'].max().date()
    data_range = st.sidebar.date_input("Selecione o período", [data_min, data_max], min_value=data_min, max_value=data_max)

    df_filtro = df_comb.copy()
    if placa_sel != 'Todas':
        df_filtro = df_filtro[df_filtro['placa'] == placa_sel]
    if combustivel_sel != 'Todos':
        df_filtro = df_filtro[df_filtro['descricao_despesa'] == combustivel_sel]
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
    for comb in df_filtro['descricao_despesa'].dropna().unique():
        df_combustivel = df_filtro[df_filtro['descricao_despesa'] == comb]
        df_combustivel = df_combustivel.sort_values('quantidade_de_litros', ascending=False)
        litros_totais = df_combustivel['quantidade_de_litros'].sum()
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
    autonomia_df["Autonomia (km/L)"] = autonomia_df["Autonomia (km/L)"].apply(lambda x: float(f"{x:.3f}") if pd.notnull(x) else None)
    st.dataframe(autonomia_df, use_container_width=True)

    # ---------------------------
    # Evolução Mensal Litros
    # ---------------------------
    st.subheader("⛽ Evolução Mensal de Litros por Combustível")
    litros_mes = df_filtro.groupby(['AnoMes','descricao_despesa'])['quantidade_de_litros'].sum().reset_index()
    litros_mes = litros_mes.sort_values('quantidade_de_litros', ascending=False)
    fig_litros = px.bar(litros_mes, x='AnoMes', y='quantidade_de_litros', color='descricao_despesa',
                        barmode='group', labels={'AnoMes':'Mês','quantidade_de_litros':'Litros'},
                        title="Litros Mensais por Combustível")
    st.plotly_chart(fig_litros, use_container_width=True)

    # ---------------------------
    # Evolução Mensal Preço Médio
    # ---------------------------
    st.subheader("💲 Evolução Mensal do Preço Médio por Litro")
    preco_mes = df_filtro.dropna(subset=['quantidade_de_litros','valor_total']).groupby(['AnoMes','descricao_despesa']).apply(
        lambda x: x['valor_total'].sum()/x['quantidade_de_litros'].sum() if x['quantidade_de_litros'].sum()>0 else 0
    ).reset_index()
    preco_mes = preco_mes.rename(columns={0:'Preço Médio'})
    preco_mes = preco_mes.sort_values('Preço Médio', ascending=False)
    fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color='descricao_despesa', markers=True,
                        labels={'AnoMes':'Mês','Preço Médio':'R$ / Litro'},
                        title="Preço Médio Mensal por Combustível")
    st.plotly_chart(fig_preco, use_container_width=True)

if __name__ == "__main__":
    main()
