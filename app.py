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
    
    # Renomear colunas importantes
    df_int = df_int.rename(columns={"valor total": "valor_total", "valor unitario": "valor_unitario", "descricao despesa":"descricao"})
    df_ext = df_ext.rename(columns={"valor total": "valor_total", "valor unitario": "valor_unitario", "descricao despesa":"descricao"})

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
    df_comb = pd.concat([df_int, df_ext], ignore_index=True)
    df_comb = df_comb.dropna(subset=['placa','quantidade de litros','data'])
    return df_comb

# ---------------------------
# Streamlit App
# ---------------------------
def main():
    st.set_page_config(layout="wide")
    st.title("🚛 Insights da Frota - Abastecimento")

    arquivo = st.file_uploader("Faça upload da planilha Excel com abas: 'Abastecimento Interno', 'Abastecimento Externo' e 'Consumo'", type='xlsx')
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
    # Mapa de colunas
    # ---------------------------
    mapa_colunas = {
        "placa":"placa",
        "litros":"quantidade de litros",
        "valor_total":"valor_total",
        "descricao":"descricao",
        "km":"km atual"
    }

    # ---------------------------
    # Abas do App
    # ---------------------------
    abas = st.tabs(["Métricas Gerais","Autonomia","Evolução Litros","Preço Médio","Comparativo","Consumo"])

    # ---------------------------
    # Aba 1 - Métricas Gerais
    # ---------------------------
    with abas[0]:
        for comb in df_filtro[mapa_colunas["descricao"]].dropna().unique():
            df_validas = df_filtro[(df_filtro[mapa_colunas["descricao"]]==comb)].dropna(subset=[mapa_colunas["valor_total"], mapa_colunas["litros"]])
            df_validas = df_validas[df_validas[mapa_colunas["valor_total"]]>0]
            df_validas = df_validas[df_validas[mapa_colunas["placa"]].notna()]
            
            litros_totais = df_validas[mapa_colunas["litros"]].sum()
            valor_total = df_validas[mapa_colunas["valor_total"]].sum()
            preco_medio = valor_total / litros_totais if litros_totais>0 else 0

            st.markdown(f"**{comb}**")
            col1, col2, col3 = st.columns(3)
            col1.metric("Litros Totais", f"{litros_totais:,.2f} L")
            col2.metric("Valor Total Gasto", f"R$ {valor_total:,.2f}")
            col3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f}")

    # ---------------------------
    # Aba 2 - Autonomia
    # ---------------------------
    with abas[1]:
        st.markdown("🚙 Autonomia por Veículo (usando tabela de Consumo)")
        df_consumo['Litros'] = df_consumo['TOTAL LITROS'].map(lambda x: f"{x:,.2f} L")
        df_consumo['KM Rodado'] = df_consumo['KM RODADO'].map(lambda x: f"{x:,.0f} km")
        df_consumo['Autonomia'] = df_consumo['AUTONOMIA'].map(lambda x: f"{x:.2f} km/L")
        st.dataframe(df_consumo[['PLACA','Litros','KM Rodado','Autonomia']].sort_values('Autonomia'), hide_index=True)

    # ---------------------------
    # Aba 3 - Evolução Litros
    # ---------------------------
    with abas[2]:
        litros_mes = df_filtro.groupby(['AnoMes', mapa_colunas["descricao"]])[mapa_colunas["litros"]].sum().reset_index()
        litros_mes[mapa_colunas["litros"]] = litros_mes[mapa_colunas["litros"]].round(2)
        fig_litros = px.bar(litros_mes, x='AnoMes', y=mapa_colunas["litros"], color=mapa_colunas["descricao"],
                            barmode='group', labels={'AnoMes':'Mês', mapa_colunas["litros"]:'Litros'},
                            title="Litros Mensais por Combustível")
        st.plotly_chart(fig_litros, use_container_width=True)
        litros_mes['Litros'] = litros_mes[mapa_colunas["litros"]].map(lambda x: f"{x:,.2f} L")
        st.markdown("**📋 Tabela de Litros Mensais por Combustível**")
        st.dataframe(litros_mes.rename(columns={mapa_colunas["descricao"]:"Combustível"}), hide_index=True)

    # ---------------------------
    # Aba 4 - Preço Médio
    # ---------------------------
    with abas[3]:
        df_validas = df_filtro.dropna(subset=[mapa_colunas["valor_total"], mapa_colunas["litros"]])
        df_validas = df_validas[df_validas[mapa_colunas["valor_total"]]>0]
        preco_mes = df_validas.groupby(['AnoMes', mapa_colunas["descricao"]]).apply(
            lambda x: x[mapa_colunas["valor_total"]].sum()/x[mapa_colunas["litros"]].sum() if x[mapa_colunas["litros"]].sum()>0 else 0
        ).reset_index().rename(columns={0:'Preço Médio'})
        preco_mes['Preço Médio'] = preco_mes['Preço Médio'].round(2)
        fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color=mapa_colunas["descricao"], markers=True,
                            labels={'AnoMes':'Mês','Preço Médio':'R$/L'}, title="Preço Médio Mensal por Combustível")
        st.plotly_chart(fig_preco, use_container_width=True)
        preco_mes['Preço Médio'] = preco_mes['Preço Médio'].map(lambda x: f"R$ {x:,.2f}")
        st.markdown("**📋 Tabela de Preço Médio Mensal por Combustível**")
        st.dataframe(preco_mes.rename(columns={mapa_colunas["descricao"]:"Combustível"}), hide_index=True)

    # ---------------------------
    # Aba 5 - Comparativo Interno x Externo
    # ---------------------------
    with abas[4]:
        comparativo = df_filtro.groupby(['AnoMes','origem'])[mapa_colunas["litros"]].sum().reset_index()
        comparativo[mapa_colunas["litros"]] = comparativo[mapa_colunas["litros"]].round(2)
        fig_comp = px.bar(comparativo, x='AnoMes', y=mapa_colunas["litros"], color='origem',
                          barmode='group', labels={'AnoMes':'Mês', mapa_colunas["litros"]:'Litros','origem':'Origem'},
                          title="Abastecimento Interno x Externo Mensal")
        st.plotly_chart(fig_comp, use_container_width=True)
        comparativo['Litros'] = comparativo[mapa_colunas["litros"]].map(lambda x: f"{x:,.2f} L")
        st.markdown("**📋 Tabela Comparativa Interno x Externo**")
        st.dataframe(comparativo.rename(columns={'origem':'Origem'}), hide_index=True)

    # ---------------------------
    # Aba 6 - Consumo
    # ---------------------------
    with abas[5]:
        st.markdown("📊 Consumo por Veículo")
        df_consumo['Litros'] = df_consumo['TOTAL LITROS'].map(lambda x: f"{x:,.2f} L")
        df_consumo['KM Rodado'] = df_consumo['KM RODADO'].map(lambda x: f"{x:,.0f} km")
        df_consumo['Autonomia'] = df_consumo['AUTONOMIA'].map(lambda x: f"{x:.2f} km/L")
        st.dataframe(df_consumo[['PLACA','Litros','KM Rodado','Autonomia']].sort_values('Autonomia'), hide_index=True)

if __name__ == "__main__":
    main()
