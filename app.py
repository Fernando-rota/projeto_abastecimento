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
        st.error(f"Erro ao ler planilha: {e}")
        return None, None, None

# ---------------------------
# Layout principal
# ---------------------------
st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")
st.title("📊 Dashboard de Abastecimento")

# Upload do arquivo principal
arquivo = st.file_uploader("Carregar arquivo Excel com Abastecimentos e Consumo", type=['xlsx'])

if arquivo:
    df_interno, df_externo, df_consumo = carregar_planilha(arquivo)

    if df_interno is not None and df_externo is not None:
        # Unir dados abastecimento
        df_interno["origem"] = "Interno"
        df_externo["origem"] = "Externo"
        df_filtro = pd.concat([df_interno, df_externo], ignore_index=True)

        # Detectar automaticamente a coluna de data
        coluna_data = None
        for nome_col in df_filtro.columns:
            if "data" in nome_col.lower():
                coluna_data = nome_col
                break

        if coluna_data:
            df_filtro[coluna_data] = pd.to_datetime(df_filtro[coluna_data], errors='coerce')
            df_filtro['AnoMes'] = df_filtro[coluna_data].dt.to_period('M').astype(str)
        else:
            st.error("❌ Nenhuma coluna de data encontrada nas abas de abastecimento.")
            st.stop()

        # Criar abas
        abas = st.tabs([
            "📊 Métricas Gerais",
            "🚙 Autonomia",
            "📈 Consumo",
            "⛽ Evolução Mensal",
            "💲 Preço Médio Mensal",
            "📊 Comparativo Interno x Externo"
        ])

        # Aba Métricas Gerais
        with abas[0]:
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

        # Aba Autonomia
        with abas[1]:
            st.subheader("Autonomia (km/L) por Veículo")
            autonomia_df = (
                df_filtro
                .dropna(subset=['placa','km atual','quantidade de litros'])
                .groupby('placa')
                .apply(lambda g: pd.Series({
                    'Autonomia (km/L)': (g['km atual'].max() - g['km atual'].min()) / g['quantidade de litros'].sum()
                    if g['quantidade de litros'].sum() > 0 else None
                }))
                .reset_index()
            )
            autonomia_df["Autonomia (km/L)"] = autonomia_df["Autonomia (km/L)"].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A")
            st.dataframe(autonomia_df)

        # Aba Consumo
        with abas[2]:
            st.subheader("📈 Consumo por Veículo (dados prontos)")
            colunas_esperadas = ['PLACA', 'TOTAL LITROS', 'KM RODADO', 'AUTONOMIA']
            if not all(col in df_consumo.columns for col in colunas_esperadas):
                st.error(f"A aba 'Consumo' no Excel precisa conter as colunas: {', '.join(colunas_esperadas)}")
            else:
                df_consumo['AUTONOMIA'] = df_consumo['AUTONOMIA'].apply(lambda x: f"{float(x):.3f}" if pd.notnull(x) else "N/A")
                st.dataframe(df_consumo)

        # Aba Evolução Mensal de Litros
        with abas[3]:
            litros_mes = df_filtro.groupby(['AnoMes','descrição despesa'])['quantidade de litros'].sum().reset_index()
            fig_litros = px.bar(litros_mes, x='AnoMes', y='quantidade de litros', color='descrição despesa',
                                barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros'},
                                title="Litros Mensais por Combustível")
            st.plotly_chart(fig_litros, use_container_width=True)

        # Aba Preço Médio Mensal
        with abas[4]:
            preco_mes = df_filtro.dropna(subset=['quantidade de litros','valor_total']).groupby(['AnoMes','descrição despesa']).apply(
                lambda x: x['valor_total'].sum()/x['quantidade de litros'].sum() if x['quantidade de litros'].sum()>0 else 0
            ).reset_index().rename(columns={0:'Preço Médio'})
            fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color='descrição despesa', markers=True,
                                labels={'AnoMes':'Mês','Preço Médio':'R$ / Litro'},
                                title="Preço Médio Mensal por Combustível")
            st.plotly_chart(fig_preco, use_container_width=True)

        # Aba Comparativo Interno x Externo
        with abas[5]:
            comparativo = df_filtro.groupby(['AnoMes','origem'])['quantidade de litros'].sum().reset_index()
            fig_comp = px.bar(comparativo, x='AnoMes', y='quantidade de litros', color='origem',
                              barmode='group', labels={'AnoMes':'Mês','quantidade de litros':'Litros','origem':'Origem'},
                              title="Abastecimento Interno x Externo Mensal")
            st.plotly_chart(fig_comp, use_container_width=True)
