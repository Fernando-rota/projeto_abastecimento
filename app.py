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
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True).str.replace(',', '.'), errors='coerce')

def prepara_dados(df):
    # Normaliza colunas
    df.columns = df.columns.str.strip().str.lower()
    col_map = {
        "data": "data",
        "placa": "placa",
        "codigo despesa": "codigo_despesa",
        "descrição despesa": "descricao_despesa",
        "cnpj fornecedor": "cnpj_fornecedor",
        "quantidade de litros": "quantidade_litros",
        "valor unitario": "valor_unitario",
        "valor total": "valor_total",
        "km atual": "km_atual",
        "tipo": "tipo"
    }
    df = df.rename(columns={c: col_map[c] for c in col_map if c in df.columns})
    
    # Converte datas
    if 'data' in df.columns:
        df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['data'])
    
    # Converte numéricos
    for col in ['quantidade_litros','km_atual']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in ['valor_unitario','valor_total']:
        if col in df.columns:
            df[col] = limpa_monetario(df[col])
    
    # Normaliza tipo e placa
    if 'tipo' in df.columns:
        df['tipo'] = df['tipo'].astype(str).str.lower()
    if 'placa' in df.columns:
        df['placa'] = df['placa'].replace('-', pd.NA)
    
    return df

def calcula_autonomia(df):
    if not {'km_atual','quantidade_litros','placa'}.issubset(df.columns):
        return pd.DataFrame(columns=['Placa','Autonomia (km/L)'])
    df_valid = df.dropna(subset=['km_atual','quantidade_litros','placa'])
    df_valid = df_valid[(df_valid['km_atual']>0) & (df_valid['quantidade_litros']>0)]
    
    resultados = []
    for placa, g in df_valid.groupby('placa'):
        km_max = g['km_atual'].max()
        km_min = g['km_atual'].min()
        litros = g['quantidade_litros'].sum()
        autonomia = (km_max - km_min)/litros if litros>0 and km_max>km_min else None
        resultados.append({'Placa': placa, 'Autonomia (km/L)': autonomia})
    
    return pd.DataFrame(resultados).sort_values('Autonomia (km/L)', ascending=False)

# ---------------------------
# App Streamlit
# ---------------------------
def main():
    st.title("🚛 Insights da Frota - Abastecimento")

    arquivo = st.file_uploader("Faça upload da planilha Excel", type='xlsx')
    if not arquivo:
        st.info("Aguardando upload do arquivo...")
        return

    df = carregar_planilha(arquivo)
    if df is None or df.empty:
        st.warning("Planilha não contém dados válidos.")
        return

    df = prepara_dados(df)
    if df.empty:
        st.warning("Após limpeza, não há dados válidos.")
        return

    df['AnoMes'] = df['data'].dt.to_period('M').astype(str)

    # ---------------------------
    # Filtros
    # ---------------------------
    placas = ['Todas'] + sorted(df['placa'].dropna().unique()) if 'placa' in df.columns else ['Todas']
    placa_sel = st.sidebar.selectbox("Selecionar Placa", placas)
    combustiveis = ['Todos'] + sorted(df['descricao_despesa'].dropna().unique()) if 'descricao_despesa' in df.columns else ['Todos']
    combustivel_sel = st.sidebar.selectbox("Selecionar Combustível", combustiveis)
    data_min = df['data'].min().date() if 'data' in df.columns else pd.to_datetime('today').date()
    data_max = df['data'].max().date() if 'data' in df.columns else pd.to_datetime('today').date()
    data_range = st.sidebar.date_input("Selecione o período", [data_min,data_max], min_value=data_min, max_value=data_max)

    df_filtro = df.copy()
    if placa_sel != 'Todas' and 'placa' in df_filtro.columns:
        df_filtro = df_filtro[df_filtro['placa']==placa_sel]
    if combustivel_sel != 'Todos' and 'descricao_despesa' in df_filtro.columns:
        df_filtro = df_filtro[df_filtro['descricao_despesa']==combustivel_sel]
    if len(data_range)==2:
        dt_ini, dt_fim = pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])
        df_filtro = df_filtro[(df_filtro['data']>=dt_ini)&(df_filtro['data']<=dt_fim)]

    if df_filtro.empty:
        st.warning("Nenhum dado encontrado com os filtros aplicados.")
        return

    # ---------------------------
    # Métricas Gerais
    # ---------------------------
    st.subheader("📊 Métricas Gerais")
    if 'descricao_despesa' in df_filtro.columns:
        for comb in df_filtro['descricao_despesa'].dropna().unique():
            df_comb = df_filtro[df_filtro['descricao_despesa']==comb].dropna(subset=['quantidade_litros','valor_total'])
            litros_tot = df_comb['quantidade_litros'].sum()
            valor_tot = df_comb['valor_total'].sum()
            preco_medio = valor_tot/litros_tot if litros_tot>0 else 0
            st.markdown(f"**{comb}**")
            col1,col2,col3 = st.columns(3)
            col1.metric("Litros Totais", f"{litros_tot:,.2f} L")
            col2.metric("Valor Total Gasto", f"R$ {valor_tot:,.2f}")
            col3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f}")

    # ---------------------------
    # Autonomia
    # ---------------------------
    st.subheader("🚙 Autonomia (km/L) por Veículo")
    autonomia_df = calcula_autonomia(df_filtro)
    if not autonomia_df.empty:
        autonomia_df["Autonomia (km/L)"] = autonomia_df["Autonomia (km/L)"].apply(lambda x:f"{x:.3f}" if pd.notnull(x) else "N/A")
        st.dataframe(autonomia_df)
    else:
        st.info("Não há dados suficientes para calcular autonomia.")

    # ---------------------------
    # Evolução mensal litros
    # ---------------------------
    st.subheader("⛽ Evolução Mensal de Litros por Combustível")
    if {'AnoMes','descricao_despesa','quantidade_litros'}.issubset(df_filtro.columns):
        litros_mes = df_filtro.groupby(['AnoMes','descricao_despesa'])['quantidade_litros'].sum().reset_index()
        fig_litros = px.bar(litros_mes,x='AnoMes',y='quantidade_litros',color='descricao_despesa',
                            barmode='group',labels={'AnoMes':'Mês','quantidade_litros':'Litros'},
                            title="Litros Mensais por Combustível")
        st.plotly_chart(fig_litros,use_container_width=True)

    # ---------------------------
    # Evolução preço médio
    # ---------------------------
    st.subheader("💲 Evolução Mensal do Preço Médio por Litro")
    if {'AnoMes','descricao_despesa','quantidade_litros','valor_total'}.issubset(df_filtro.columns):
        preco_mes = df_filtro.dropna(subset=['quantidade_litros','valor_total']).groupby(
            ['AnoMes','descricao_despesa']
        ).apply(lambda x:x['valor_total'].sum()/x['quantidade_litros'].sum() if x['quantidade_litros'].sum()>0 else 0
        ).reset_index().rename(columns={0:'Preço Médio'})
        fig_preco = px.line(preco_mes,x='AnoMes',y='Preço Médio',color='descricao_despesa',markers=True,
                            labels={'AnoMes':'Mês','Preço Médio':'R$ / Litro'},
                            title="Preço Médio Mensal por Combustível")
        st.plotly_chart(fig_preco,use_container_width=True)

    # ---------------------------
    # Comparativo Interno x Externo
    # ---------------------------
    st.subheader("📊 Comparativo Mensal Interno x Externo (Litros)")
    if {'AnoMes','tipo','quantidade_litros'}.issubset(df_filtro.columns):
        comparativo = df_filtro.groupby(['AnoMes','tipo'])['quantidade_litros'].sum().reset_index()
        fig_comp = px.bar(comparativo,x='AnoMes',y='quantidade_litros',color='tipo',
                          barmode='group',labels={'AnoMes':'Mês','quantidade_litros':'Litros','tipo':'Origem'},
                          title="Abastecimento Interno x Externo Mensal")
        st.plotly_chart(fig_comp,use_container_width=True)

if __name__=="__main__":
    main()
