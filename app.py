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
        df_consumo = pd.read_excel(arquivo, sheet_name='Consumo')
        return df_interno, df_externo, df_consumo
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None, None, None

def limpa_monetario(col):
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True).str.replace(',', '.'), errors='coerce')

def prepara_dados(df_int, df_ext):
    # Padronizar colunas
    df_int.columns = df_int.columns.str.strip().str.lower()
    df_ext.columns = df_ext.columns.str.strip().str.lower()
    
    # Renomear colunas importantes, somente se existirem
    if 'valor total' in df_int.columns:
        df_int = df_int.rename(columns={"valor total": "valor_total"})
    if 'valor unitario' in df_int.columns:
        df_int = df_int.rename(columns={"valor unitario": "valor_unitario"})
    if 'descricao despesa' in df_int.columns and 'descricao' not in df_int.columns:
        df_int = df_int.rename(columns={"descricao despesa":"descricao"})
        
    if 'valor total' in df_ext.columns:
        df_ext = df_ext.rename(columns={"valor total": "valor_total"})
    if 'valor unitario' in df_ext.columns:
        df_ext = df_ext.rename(columns={"valor unitario": "valor_unitario"})
    if 'descricao despesa' in df_ext.columns and 'descricao' not in df_ext.columns:
        df_ext = df_ext.rename(columns={"descricao despesa":"descricao"})

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
    df_int['descricao'] = df_int.get('descricao', pd.Series()).astype(str)

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
    df_ext['descricao'] = df_ext.get('descricao', pd.Series()).astype(str)

    return df_int, df_ext

def prepara_consumo(df_int, df_ext):
    # Considerar apenas saídas internas com preço calculado
    df_int_valid = df_int[(df_int['tipo'] == 'saída') & (df_int['valor_unitario'].notna())]
    df_comb = pd.concat([
        df_int_valid[['data','placa','quantidade de litros','valor_unitario','valor_total','km atual','origem','descricao']],
        df_ext[['data','placa','quantidade de litros','valor_unitario','valor_total','km atual','origem','descricao']]
    ], ignore_index=True)
    df_comb = df_comb.dropna(subset=['placa','quantidade de litros','data'])
    return df_comb

# ---------------------------
# Streamlit App
# ---------------------------
def main():
    st.title("🚛 Insights da Frota - Abastecimento")

    arquivo = st.file_uploader("Faça upload da planilha Excel com abas 'Abastecimento Interno', 'Abastecimento Externo' e 'Consumo'", type='xlsx')
    if not arquivo:
        st.info("Aguardando upload do arquivo...")
        return

    df_interno, df_externo, df_consumo = carregar_planilha(arquivo)
    if df_interno is None or df_externo is None or df_consumo is None:
        return

    df_interno, df_externo = prepara_dados(df_interno, df_externo)
    df_comb = prepara_consumo(df_interno, df_externo)

    # ---------------------------
    # Filtros
    # ---------------------------
    placas = ['Todas'] + sorted(df_comb['placa'].dropna().unique())
    placa_sel = st.sidebar.selectbox("Selecionar Placa", placas)

    combustiveis = ['Todos'] + sorted(df_comb['descricao'].dropna().unique())
    combustivel_sel = st.sidebar.selectbox("Selecionar Combustível", combustiveis)

    data_min = df_comb['data'].min().date()
    data_max = df_comb['data'].max().date()
    data_range = st.sidebar.date_input("Selecione o período", [data_min, data_max], min_value=data_min, max_value=data_max)

    df_filtro = df_comb.copy()
    if placa_sel != 'Todas':
        df_filtro = df_filtro[df_filtro['placa'] == placa_sel]
    if combustivel_sel != 'Todos':
        df_filtro = df_filtro[df_filtro['descricao'] == combustivel_sel]
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
    for comb in df_filtro['descricao'].dropna().unique():
        df_combustivel = df_filtro[(df_filtro['descricao'] == comb) & (df_filtro['valor_unitario'].notna())]
        litros_totais = df_combustivel['quantidade de litros'].sum()
        valor_total = df_combustivel['valor_total'].sum()
        preco_medio = valor_total / litros_totais if litros_totais > 0 else 0

        st.markdown(f"**{comb}**")
        col1, col2, col3 = st.columns(3)
        col1.metric("Litros Totais", f"{litros_totais:,.2f} L")
        col2.metric("Valor Total Gasto", f"R$ {valor_total:,.2f}")
        col3.metric("Preço Médio/Litro", f"R$ {preco_medio:.2f}")

    # ---------------------------
    # Aba Consumo
    # ---------------------------
    st.subheader("🚙 Consumo por Veículo")
    df_consumo_sorted = df_consumo.sort_values('AUTONOMIA')
    st.dataframe(df_consumo_sorted.style.format({
        'TOTAL LITROS':'{:.2f} L',
        'KM RODADO':'{:.0f} km',
        'AUTONOMIA':'{:.2f} km/L'
    }).hide_index())

    # ---------------------------
    # Evolução mensal litros por combustível
    # ---------------------------
    st.subheader("⛽ Evolução Mensal de Litros por Combustível")
    litros_mes = df_filtro.groupby(['AnoMes','descricao'])['quantidade de litros'].sum().reset_index()
    fig_litros = px.bar(litros_mes, x='AnoMes', y='quantidade de litros', color='descricao',
                        barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros','descricao':'Combustível'},
                        title="Litros Mensais por Combustível")
    st.plotly_chart(fig_litros, use_container_width=True)
    st.dataframe(litros_mes.style.format({'quantidade de litros':'{:.2f} L'}).hide_index())

    # ---------------------------
    # Evolução mensal preço médio por litro
    # ---------------------------
    st.subheader("💲 Evolução Mensal do Preço Médio por Litro")
    preco_mes = df_filtro.dropna(subset=['quantidade de litros','valor_total']).groupby(['AnoMes','descricao']).apply(
        lambda g: g['valor_total'].sum()/g['quantidade de litros'].sum() if g['quantidade de litros'].sum()>0 else 0
    ).reset_index().rename(columns={0:'Preço Médio'})
    fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color='descricao', markers=True,
                        labels={'AnoMes':'Mês','Preço Médio':'R$ / Litro','descricao':'Combustível'},
                        title="Preço Médio Mensal por Combustível")
    st.plotly_chart(fig_preco, use_container_width=True)
    st.dataframe(preco_mes.style.format({'Preço Médio':'R$ {:.2f}'}).hide_index())

    # ---------------------------
    # Comparativo Interno x Externo
    # ---------------------------
    st.subheader("📊 Comparativo Mensal Interno x Externo (Litros)")
    comparativo = df_filtro.groupby(['AnoMes','origem'])['quantidade de litros'].sum().reset_index()
    fig_comp = px.bar(comparativo, x='AnoMes', y='quantidade de litros', color='origem',
                      barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros','origem':'Origem'},
                      title="Abastecimento Interno x Externo Mensal")
    st.plotly_chart(fig_comp, use_container_width=True)
    st.dataframe(comparativo.style.format({'quantidade de litros':'{:.2f} L'}).hide_index())

if __name__ == "__main__":
    main()
