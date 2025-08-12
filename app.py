import streamlit as st
import pandas as pd
import plotly.express as px

def limpar_valor(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, str):
        return float(valor.replace("R$", "").replace(".", "").replace(",", ".").strip())
    return float(valor)

def carregar_dados(uploaded_file):
    df_interno = pd.read_excel(uploaded_file, sheet_name="Abastecimento Interno")
    df_externo = pd.read_excel(uploaded_file, sheet_name="Abastecimento Externo")

    # Parse datas
    df_interno["Data"] = pd.to_datetime(df_interno["Data"], errors="coerce")
    df_externo["Data"] = pd.to_datetime(df_externo["Data"], errors="coerce")

    # Remove placas inválidas
    placas_invalidas = ["-", "correção"]
    df_interno = df_interno[~df_interno["Placa"].isin(placas_invalidas)]
    df_externo = df_externo[~df_externo["Placa"].isin(placas_invalidas)]

    # Converte colunas para numérico, limpa valores monetários
    df_interno["Quantidade de litros"] = pd.to_numeric(df_interno["Quantidade de litros"], errors="coerce").fillna(0)
    df_interno["Valor Unitario"] = df_interno["Valor Unitario"].apply(limpar_valor)
    df_interno["Valor Total"] = df_interno["Valor Total"].apply(limpar_valor)
    df_interno["KM Atual"] = pd.to_numeric(df_interno["KM Atual"], errors="coerce")

    df_externo["Quantidade de litros"] = pd.to_numeric(df_externo["Quantidade de litros"], errors="coerce").fillna(0)
    df_externo["Valor Unitario"] = df_externo["Valor Unitario"].apply(limpar_valor)
    df_externo["Valor Total"] = df_externo["Valor Total"].apply(limpar_valor)
    df_externo["KM Atual"] = pd.to_numeric(df_externo["KM Atual"], errors="coerce")

    # Padroniza texto para filtro de combustível
    df_interno["Descrição Despesa"] = df_interno["Descrição Despesa"].astype(str).str.upper().str.strip()
    df_externo["Descrição Despesa"] = df_externo["Descrição Despesa"].astype(str).str.upper().str.strip()

    # Padroniza placa
    df_interno["Placa"] = df_interno["Placa"].astype(str).str.upper().str.strip()
    df_externo["Placa"] = df_externo["Placa"].astype(str).str.upper().str.strip()

    return df_interno, df_externo

def filtrar_dados(df_interno, df_externo, placas_selecionadas, combustiveis_selecionados, meses_selecionados):
    if placas_selecionadas:
        df_interno = df_interno[df_interno["Placa"].isin(placas_selecionadas)]
        df_externo = df_externo[df_externo["Placa"].isin(placas_selecionadas)]

    if combustiveis_selecionados:
        df_interno = df_interno[df_interno["Descrição Despesa"].isin(combustiveis_selecionados)]
        df_externo = df_externo[df_externo["Descrição Despesa"].isin(combustiveis_selecionados)]

    if meses_selecionados:
        df_interno = df_interno[df_interno["Data"].dt.month.isin(meses_selecionados)]
        df_externo = df_externo[df_externo["Data"].dt.month.isin(meses_selecionados)]

    return df_interno, df_externo

def calcular_consumo_medio(df_interno, df_externo):
    df_km = pd.concat([df_interno[["Placa", "KM Atual"]], df_externo[["Placa", "KM Atual"]]])
    consumo = df_km.groupby('Placa').agg(KM_max=('KM Atual','max'), KM_min=('KM Atual','min'))
    consumo['KM Rodado'] = consumo['KM_max'] - consumo['KM_min']

    litros = pd.concat([
        df_interno.groupby('Placa')['Quantidade de litros'].sum(),
        df_externo.groupby('Placa')['Quantidade de litros'].sum()
    ], axis=1).fillna(0)

    litros['Total Litros'] = litros.sum(axis=1)

    consumo = consumo.join(litros['Total Litros'])
    consumo['Autonomia (KM/L)'] = consumo['KM Rodado'] / consumo['Total Litros'].replace(0, pd.NA)
    consumo = consumo.sort_values('KM Rodado', ascending=False).reset_index()
    return consumo

def indicadores_mensais(df_interno, df_externo):
    df_interno['AnoMes'] = df_interno['Data'].dt.to_period('M')
    df_externo['AnoMes'] = df_externo['Data'].dt.to_period('M')

    interno_agg = df_interno.groupby(['AnoMes', 'Descrição Despesa']).agg({
        'Quantidade de litros':'sum',
        'Valor Total':'sum'
    }).reset_index()
    externo_agg = df_externo.groupby(['AnoMes', 'Descrição Despesa']).agg({
        'Quantidade de litros':'sum',
        'Valor Total':'sum'
    }).reset_index()

    return interno_agg, externo_agg

def main():
    st.title("📊 Dashboard de Abastecimento")

    arquivo = st.file_uploader("Faça upload da planilha Excel com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=["xls", "xlsx"])

    if arquivo:
        df_interno, df_externo = carregar_dados(arquivo)

        # Filtros
        placas = sorted(set(df_interno["Placa"].unique()) | set(df_externo["Placa"].unique()))
        combustiveis = sorted(set(df_interno["Descrição Despesa"].unique()) | set(df_externo["Descrição Despesa"].unique()))
        meses = sorted(set(df_interno["Data"].dt.month.dropna().astype(int).unique()) | set(df_externo["Data"].dt.month.dropna().astype(int).unique()))

        placas_selecionadas = st.multiselect("Selecione as placas", placas, default=placas)
        combustiveis_selecionados = st.multiselect("Selecione os combustíveis", combustiveis, default=combustiveis)
        meses_selecionados = st.multiselect("Selecione os meses (numérico)", meses, default=meses)

        df_interno_filtrado, df_externo_filtrado = filtrar_dados(df_interno, df_externo, placas_selecionadas, combustiveis_selecionados, meses_selecionados)

        aba1, aba2 = st.tabs(["Consumo Médio por Placa", "Indicadores Mensais"])

        with aba1:
            consumo = calcular_consumo_medio(df_interno_filtrado, df_externo_filtrado)
            st.subheader("Consumo Médio e Autonomia por Veículo")
            st.dataframe(consumo.style.format({
                "KM Rodado": "{:,.0f}",
                "Total Litros": "{:,.2f}",
                "Autonomia (KM/L)": "{:,.2f}"
            }), use_container_width=True)

        with aba2:
            interno_agg, externo_agg = indicadores_mensais(df_interno_filtrado, df_externo_filtrado)
            st.subheader("Litros Abastecidos Mensalmente - Interno")
            st.dataframe(interno_agg, use_container_width=True)

            st.subheader("Litros Abastecidos Mensalmente - Externo")
            st.dataframe(externo_agg, use_container_width=True)

            # Gráfico Litros
            litros_agg = pd.concat([
                interno_agg.assign(Tipo='Interno'),
                externo_agg.assign(Tipo='Externo')
            ])
            fig_litros = px.bar(litros_agg, x='AnoMes', y='Quantidade de litros', color='Tipo', barmode='group', title="Litros Abastecidos Mensalmente")
            st.plotly_chart(fig_litros, use_container_width=True)

            # Gráfico Custos
            fig_custos = px.bar(litros_agg, x='AnoMes', y='Valor Total', color='Tipo', barmode='group', title="Custos Mensais de Abastecimento")
            st.plotly_chart(fig_custos, use_container_width=True)

    else:
        st.info("Faça upload da planilha para iniciar a análise.")

if __name__ == "__main__":
    main()
