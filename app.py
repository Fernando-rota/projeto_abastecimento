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

arquivo = st.file_uploader("Carregar arquivo Excel com Abastecimentos e Consumo", type=['xlsx'])

if arquivo:
    df_interno, df_externo, df_consumo = carregar_planilha(arquivo)

    if df_interno is not None and df_externo is not None:
        # Adicionar coluna origem
        df_interno["origem"] = "Interno"
        df_externo["origem"] = "Externo"

        # Concatenar interno + externo
        df_filtro = pd.concat([df_interno, df_externo], ignore_index=True)

        # Mapear colunas (agora com veículo)
        nomes_esperados = {
            "data": ["Data", "Carimbo de data/hora"],
            "descricao": ["Descrição Despesa", "descricao despesa", "Tipo"],
            "placa": ["Placa", "placa", "Veículo", "veiculo"],
            "veiculo": ["Veículo", "veiculo", "Modelo", "modelo"],
            "litros": ["Quantidade de litros", "quantidade de litros", "Litros", "litros"],
            "valor_total": ["Valor Total", "valor total", "valor_total"],
            "km": ["KM Atual", "km atual", "km"]
        }
        mapa_colunas = mapear_colunas(df_filtro, nomes_esperados)

        # Verificar colunas obrigatórias
        colunas_faltando = [c for c in ["data", "descricao", "placa", "litros", "valor_total"] if c not in mapa_colunas]
        if colunas_faltando:
            st.error(f"❌ Não foi possível encontrar as colunas: {', '.join(colunas_faltando)}")
            st.stop()

        # Processar datas
        df_filtro[mapa_colunas["data"]] = pd.to_datetime(df_filtro[mapa_colunas["data"]], errors='coerce')
        df_filtro["AnoMes"] = df_filtro[mapa_colunas["data"]].dt.to_period('M').astype(str)

        # Criar abas
        abas = st.tabs([
            "📊 Métricas Gerais",
            "📈 Consumo",
            "⛽ Evolução Mensal",
            "💲 Preço Médio Mensal",
            "📊 Comparativo Interno x Externo"
        ])

        # ---------------------------
        # Aba 1 - Métricas Gerais
        # ---------------------------
        with abas[0]:
            for comb in df_filtro[mapa_colunas["descricao"]].dropna().unique():
                df_combustivel = df_filtro[df_filtro[mapa_colunas["descricao"]] == comb].copy()

                df_validas = df_combustivel.dropna(subset=[mapa_colunas["valor_total"], mapa_colunas["litros"], mapa_colunas["placa"]])
                df_validas = df_validas[df_validas[mapa_colunas["valor_total"]] > 0]
                df_validas = df_validas[~df_validas[mapa_colunas["placa"]].astype(str).str.upper().isin(["-", "NONE", "NAN", "NULL", ""])]

                litros_totais = df_validas[mapa_colunas["litros"]].sum()
                valor_total = df_validas[mapa_colunas["valor_total"]].sum()
                preco_medio = valor_total / litros_totais if litros_totais > 0 else 0

                st.markdown(f"**{comb}**")
                col1, col2, col3 = st.columns(3)
                col1.metric("Litros Totais", f"{litros_totais:,.2f} L")
                col2.metric("Valor Total Gasto", f"R$ {valor_total:,.2f}")
                col3.metric("Preço Médio por Litro", f"R$ {preco_medio:.3f}")

        # ---------------------------
        # Aba 2 - Consumo
        # ---------------------------
        with abas[1]:
            st.subheader("📈 Consumo por Veículo (dados prontos)")
            colunas_esperadas = ['PLACA', 'VEÍCULO', 'TOTAL LITROS', 'KM RODADO', 'AUTONOMIA']
            if not all(col in df_consumo.columns for col in colunas_esperadas):
                st.error(f"A aba 'Consumo' no Excel precisa conter as colunas: {', '.join(colunas_esperadas)}")
            else:
                df_consumo['AUTONOMIA'] = pd.to_numeric(df_consumo['AUTONOMIA'], errors='coerce')
                df_consumo = df_consumo.sort_values('AUTONOMIA', ascending=True)
                df_consumo['TOTAL LITROS'] = df_consumo['TOTAL LITROS'].apply(lambda x: f"{x:,.2f} L")
                df_consumo['KM RODADO'] = df_consumo['KM RODADO'].apply(lambda x: f"{x:,.0f} km")
                df_consumo['AUTONOMIA'] = df_consumo['AUTONOMIA'].apply(lambda x: f"{x:.2f} km/L" if pd.notnull(x) else "N/A")
                st.dataframe(df_consumo)

        # ---------------------------
        # Aba 3 - Evolução Mensal
        # ---------------------------
        with abas[2]:
            litros_mes = df_filtro.groupby(['AnoMes', mapa_colunas["descricao"]])[mapa_colunas["litros"]].sum().reset_index()
            fig_litros = px.bar(litros_mes, x='AnoMes', y=mapa_colunas["litros"], color=mapa_colunas["descricao"],
                                barmode='group', labels={'AnoMes': 'Mês', mapa_colunas["litros"]: 'Litros'},
                                title="Litros Mensais por Combustível")
            st.plotly_chart(fig_litros, use_container_width=True)
            litros_mes_display = litros_mes.copy()
            litros_mes_display[mapa_colunas["litros"]] = litros_mes_display[mapa_colunas["litros"]].apply(lambda x: f"{x:,.2f} L")
            st.dataframe(litros_mes_display)

        # ---------------------------
        # Aba 4 - Preço Médio Mensal
        # ---------------------------
        with abas[3]:
            df_validas = df_filtro.dropna(subset=[mapa_colunas["valor_total"], mapa_colunas["litros"]])
            df_validas = df_validas[df_validas[mapa_colunas["valor_total"]] > 0]

            preco_mes = df_validas.groupby(['AnoMes', mapa_colunas["descricao"]]).apply(
                lambda x: x[mapa_colunas["valor_total"]].sum() / x[mapa_colunas["litros"]].sum()
                if x[mapa_colunas["litros"]].sum() > 0 else 0
            ).reset_index().rename(columns={0: 'Preço Médio'})

            fig_preco = px.line(preco_mes, x='AnoMes', y='Preço Médio', color=mapa_colunas["descricao"], markers=True,
                                labels={'AnoMes': 'Mês', 'Preço Médio': 'R$ / Litro'},
                                title="Preço Médio Mensal por Combustível")
            st.plotly_chart(fig_preco, use_container_width=True)
            preco_mes_display = preco_mes.copy()
            preco_mes_display['Preço Médio'] = preco_mes_display['Preço Médio'].apply(lambda x: f"R$ {x:.3f}")
            st.dataframe(preco_mes_display)

        # ---------------------------
        # Aba 5 - Comparativo Interno x Externo
        # ---------------------------
        with abas[4]:
            comparativo = df_filtro.groupby(['AnoMes', 'origem'])[mapa_colunas["litros"]].sum().reset_index()
            fig_comp = px.bar(comparativo, x='AnoMes', y=mapa_colunas["litros"], color='origem',
                              barmode='group', labels={'AnoMes': 'Mês', mapa_colunas["litros"]: 'Litros', 'origem': 'Origem'},
                              title="Abastecimento Interno x Externo Mensal")
            st.plotly_chart(fig_comp, use_container_width=True)
            comparativo_display = comparativo.copy()
            comparativo_display[mapa_colunas["litros"]] = comparativo_display[mapa_colunas["litros"]].apply(lambda x: f"{x:,.2f} L")
            st.dataframe(comparativo_display)
