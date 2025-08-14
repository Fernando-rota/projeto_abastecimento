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
    return pd.to_numeric(col.astype(str)
                         .str.replace(r'R\$\s*', '', regex=True)
                         .str.replace(',', '.'), errors='coerce')

def padroniza_placa(serie):
    """Padroniza formato da placa e remove inválidas"""
    s = serie.astype(str).str.upper().str.strip()
    s = s.replace(['-', 'NONE', 'NAN', 'NULL', '', 'CORREÇÃO'], pd.NA)
    return s

def prepara_dados(df):
    df.columns = df.columns.str.strip().str.lower()
    
    df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['data'])
    
    df['quantidade de litros'] = pd.to_numeric(df['quantidade de litros'], errors='coerce')
    df['valor_unitario'] = limpa_monetario(df.get('valor_unitario', pd.Series()))
    df['valor_total'] = pd.to_numeric(df.get('valor_total', pd.Series()), errors='coerce')
    df['placa'] = padroniza_placa(df['placa'])
    df['descricao_despesa'] = df.get('descricao_despesa', pd.Series()).astype(str)
    df['km_atual'] = pd.to_numeric(df['km atual'], errors='coerce')
    
    return df

def calcula_preco_medio_entrada(df):
    """Preço médio do combustível comprado internamente (placa inválida)"""
    entradas = df[df['placa'].isna()]
    entradas = entradas.dropna(subset=['valor_unitario','quantidade de litros'])
    if entradas.empty:
        return 0
    litros_totais = entradas['quantidade de litros'].sum()
    valor_total = (entradas['quantidade de litros'] * entradas['valor_unitario']).sum()
    return valor_total / litros_totais if litros_totais > 0 else 0

def calcula_autonomia(df):
    resultados = []
    for placa, g in df.groupby('placa'):
        if pd.isna(placa):
            continue
        g = g.sort_values('data')
        g = g[g['quantidade de litros'] > 0]
        if len(g) < 2:
            continue
        km_max = g['km_atual'].max()
        km_min = g['km_atual'].min()
        litros = g['quantidade de litros'].sum()
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

    df = carregar_planilha(arquivo)
    if df is None:
        return

    df = prepara_dados(df)

    # ---------------------------
    # Filtros
    # ---------------------------
    placas = ['Todas'] + sorted(df['placa'].dropna().unique(), key=lambda x: str(x))
    placa_sel = st.sidebar.selectbox("Selecionar Placa", placas)

    combustiveis = ['Todos'] + sorted(df['descricao_despesa'].dropna().unique())
    combustivel_sel = st.sidebar.selectbox("Selecionar Combustível", combustiveis)

    data_min = df['data'].min().date()
    data_max = df['data'].max().date()
    data_range = st.sidebar.date_input("Selecione o período", [data_min, data_max], min_value=data_min, max_value=data_max)

    df_filtro = df.copy()
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

    df_filtro['AnoMes'] = df_filtro['data'].dt.to_period('M').astype(str)

    # ---------------------------
    # Métricas Gerais
    # ---------------------------
    st.subheader("📊 Métricas Gerais")
    for comb in df_filtro['descricao_despesa'].dropna().unique():
        df_combustivel = df_filtro[df_filtro['descricao_despesa'] == comb].dropna(subset=['quantidade de litros','valor_total'])
        df_combustivel = df_combustivel.sort_values('quantidade de litros', ascending=False)  # ordem decrescente
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
    autonomia_df["Autonomia (km/L)"] = autonomia_df["Autonomia (km/L)"].apply(lambda x: float(f"{x:.3f}") if pd.notnull(x) else None)
    autonomia_df = autonomia_df.sort_values('Autonomia (km/L)', ascending=False)  # ordem decrescente
    st.dataframe(autonomia_df, use_container_width=True)

    # Gráfico de barras
    st.subheader("📊 Gráfico de Autonomia por Veículo")
    fig_autonomia = px.bar(autonomia_df, x='Placa', y='Autonomia (km/L)',
                           color='Autonomia (km/L)', color_continuous_scale='Viridis',
                           labels={'Autonomia (km/L)':'Autonomia (km/L)', 'Placa':'Veículo'},
                           title="Autonomia (km/L) por Veículo")
    st.plotly_chart(fig_autonomia, use_container_width=True)

    # ---------------------------
    # Evolução Mensal Litros
    # ---------------------------
    st.subheader("⛽ Evolução Mensal de Litros por Combustível")
    litros_mes = df_filtro.groupby(['AnoMes','descricao_despesa'])['quantidade de litros'].sum().reset_index()
    litros_mes = litros_mes.sort_values('quantidade de litros', ascending=False)
    fig_litros = px.bar(litros_mes, x='AnoMes', y='quantidade de litros', color='descricao_despesa',
                        barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros'},
                        title="Litros Mensais por Combustível")
    st.plotly_chart(fig_litros, use_container_width=True)

    # ---------------------------
    # Evolução Mensal Preço Médio
    # ---------------------------
    st.subheader("💲 Evolução Mensal do Preço Médio por Litro")
    preco_mes = df_filtro.dropna(subset=['quantidade de litros','valor_total']).groupby(['AnoMes','descricao_despesa']).apply(
        lambda x: x['valor_total'].sum()/x['quantidade de litros'].sum() if x['quantidade de litros'].sum()>0 else 0
    ).reset_index()
    preco_mes = preco_mes.rename(columns={0:'Preço Médio'})
    preco_mes = preco_mes.sort_values('Preço Médio', ascending=False)
    fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color='descricao_despesa', markers=True,
                        labels={'AnoMes':'Mês','Preço Médio':'R$ / Litro'},
                        title="Preço Médio Mensal por Combustível")
    st.plotly_chart(fig_preco, use_container_width=True)

    # ---------------------------
    # Comparativo Interno x Externo
    # ---------------------------
    st.subheader("📊 Comparativo Mensal Interno x Externo (Litros)")
    comparativo = df_filtro.groupby(['AnoMes','origem'])['quantidade de litros'].sum().reset_index()
    comparativo = comparativo.sort_values('quantidade de litros', ascending=False)
    fig_comp = px.bar(comparativo, x='AnoMes', y='quantidade de litros', color='origem',
                      barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros','origem':'Origem'},
                      title="Abastecimento Interno x Externo Mensal")
    st.plotly_chart(fig_comp, use_container_width=True)

if __name__ == "__main__":
    main()
