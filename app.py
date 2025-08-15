import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata

# ---------------------------
# Funções auxiliares
# ---------------------------
def normalizar_nome(nome):
    """Remove acentos, deixa minúsculo e tira espaços extras."""
    if not isinstance(nome, str):
        return ""
    nome = unicodedata.normalize('NFKD', nome)
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    return nome.strip().lower()

def mapear_colunas(df, nomes_esperados):
    """Mapeia nomes esperados para os reais no dataframe."""
    mapa = {}
    colunas_norm = {normalizar_nome(c): c for c in df.columns}
    for chave, lista_opcoes in nomes_esperados.items():
        for opcao in lista_opcoes:
            if normalizar_nome(opcao) in colunas_norm:
                mapa[chave] = colunas_norm[normalizar_nome(opcao)]
                break
    return mapa

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

# Upload do arquivo
arquivo = st.file_uploader("Carregar arquivo Excel com Abastecimentos e Consumo", type=['xlsx'])

if arquivo:
    df_interno, df_externo, df_consumo = carregar_planilha(arquivo)

    if df_interno is not None and df_externo is not None:
        # Unir dados abastecimento
        df_interno["origem"] = "Interno"
        df_externo["origem"] = "Externo"
        df_filtro = pd.concat([df_interno, df_externo], ignore_index=True)

        # Mapeamento de nomes de colunas que o script espera
        nomes_esperados = {
            "data": ["data", "data abastecimento", "dt abastecimento"],
            "descricao": ["descrição despesa", "descricao despesa", "tipo combustível", "tipo combustivel"],
            "placa": ["placa", "veículo", "veiculo"],
            "litros": ["quantidade de litros", "litros", "qtd litros"],
            "valor_total": ["valor_total", "valor total", "valor abastecimento"],
            "km": ["km atual", "km", "quilometragem"]
        }

        # Detectar colunas no df_filtro
        mapa_colunas = mapear_colunas(df_filtro, nomes_esperados)

        # Verificar se todas as colunas necessárias foram encontradas
        colunas_faltando = [c for c in nomes_esperados if c not in mapa_colunas]
        if colunas_faltando:
            st.error(f"❌ Não foi possível encontrar as colunas: {', '.join(colunas_faltando)}")
            st.stop()

        # Processar datas
        df_filtro[mapa_colunas["data"]] = pd.to_datetime(df_filtro[mapa_colunas["data"]], errors='coerce')
        df_filtro["AnoMes"] = df_filtro[mapa_colunas["data"]].dt.to_period('M').astype(str)

        # Criar abas
        abas = st.tabs([
            "📊 Métricas Gerais",
            "🚙 Autonomia",
            "📈 Consumo",
            "⛽ Evolução Mensal",
            "💲 Preço Médio Mensal",
            "📊 Comparativo Interno x Externo"
        ])

        # Aba 1 - Métricas Gerais
        with abas[0]:
            for comb in df_filtro[mapa_colunas["descricao"]].dropna().unique():
                df_combustivel = df_filtro[df_filtro[mapa_colunas["descricao"]] == comb].dropna(
                    subset=[mapa_colunas["litros"], mapa_colunas["valor_total"]]
                )
                litros_totais = df_combustivel[mapa_colunas["litros"]].sum()
                valor_total = df_combustivel[mapa_colunas["valor_total"]].sum()
                preco_medio = valor_total / litros_totais if litros_totais > 0 else 0
                st.markdown(f"**{comb}**")
                col1, col2, col3 = st.columns(3)
                col1.metric("Litros Totais", f"{litros_totais:,.2f} L")
                col2.metric("Valor Total Gasto", f"R$ {valor_total:,.2f}")
                col3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f}")

        # Aba 2 - Autonomia
        with abas[1]:
            st.subheader("Autonomia (km/L) por Veículo")
            autonomia_df = (
                df_filtro
                .dropna(subset=[mapa_colunas["placa"], mapa_colunas["km"], mapa_colunas["litros"]])
                .groupby(mapa_colunas["placa"])
                .apply(lambda g: pd.Series({
                    'Autonomia (km/L)': (g[mapa_colunas["km"]].max() - g[mapa_colunas["km"]].min()) /
                                        g[mapa_colunas["litros"]].sum()
                    if g[mapa_colunas["litros"]].sum() > 0 else None
                }))
                .reset_index()
            )
            autonomia_df["Autonomia (km/L)"] = autonomia_df["Autonomia (km/L)"].apply(
                lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A"
            )
            st.dataframe(autonomia_df)

        # Aba 3 - Consumo
        with abas[2]:
            st.subheader("📈 Consumo por Veículo (dados prontos)")
            colunas_esperadas = ['PLACA', 'TOTAL LITROS', 'KM RODADO', 'AUTONOMIA']
            if not all(col in df_consumo.columns for col in colunas_esperadas):
                st.error(f"A aba 'Consumo' no Excel precisa conter as colunas: {', '.join(colunas_esperadas)}")
            else:
                df_consumo['AUTONOMIA'] = df_consumo['AUTONOMIA'].apply(
                    lambda x: f"{float(x):.3f}" if pd.notnull(x) else "N/A"
                )
                st.dataframe(df_consumo)

        # Aba 4 - Evolução Mensal
        with abas[3]:
            litros_mes = df_filtro.groupby(['AnoMes', mapa_colunas["descricao"]])[mapa_colunas["litros"]].sum().reset_index()
            fig_litros = px.bar(litros_mes, x='AnoMes', y=mapa_colunas["litros"], color=mapa_colunas["descricao"],
                                barmode='group', labels={'AnoMes': 'Mês', mapa_colunas["litros"]: 'Litros'},
                                title="Litros Mensais por Combustível")
            st.plotly_chart(fig_litros, use_container_width=True)

        # Aba 5 - Preço Médio Mensal
        with abas[4]:
            preco_mes = df_filtro.dropna(subset=[mapa_colunas["litros"], mapa_colunas["valor_total"]]).groupby(
                ['AnoMes', mapa_colunas["descricao"]]
            ).apply(lambda x: x[mapa_colunas["valor_total"]].sum() / x[mapa_colunas["litros"]].sum()
                    if x[mapa_colunas["litros"]].sum() > 0 else 0).reset_index().rename(columns={0: 'Preço Médio'})
            fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color=mapa_colunas["descricao"], markers=True,
                                labels={'AnoMes': 'Mês', 'Preço Médio': 'R$ / Litro'},
                                title="Preço Médio Mensal por Combustível")
            st.plotly_chart(fig_preco, use_container_width=True)

        # Aba 6 - Comparativo Interno x Externo
        with abas[5]:
            comparativo = df_filtro.groupby(['AnoMes', 'origem'])[mapa_colunas["litros"]].sum().reset_index()
            fig_comp = px.bar(comparativo, x='AnoMes', y=mapa_colunas["litros"], color='origem',
                              barmode='group', labels={'AnoMes': 'Mês', mapa_colunas["litros"]: 'Litros', 'origem': 'Origem'},
                              title="Abastecimento Interno x Externo Mensal")
            st.plotly_chart(fig_comp, use_container_width=True)
