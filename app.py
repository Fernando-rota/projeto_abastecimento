import streamlit as st
import pandas as pd
import plotly.express as px

def limpar_valor(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, str):
        return float(valor.replace('R$', '').replace('.', '').replace(',', '.').strip())
    return float(valor)

def carregar_dados(uploaded_file):
    df_interno = pd.read_excel(uploaded_file, sheet_name="Abastecimento Interno")
    df_externo = pd.read_excel(uploaded_file, sheet_name="Abastecimento Externo")
    
    # Converter datas
    df_interno["Data"] = pd.to_datetime(df_interno["Data"], errors="coerce")
    df_externo["Data"] = pd.to_datetime(df_externo["Data"], errors="coerce")
    
    # Remover placas inválidas
    placas_invalidas = ["-", "correção"]
    df_interno = df_interno[~df_interno["Placa"].isin(placas_invalidas)]
    df_externo = df_externo[~df_externo["Placa"].isin(placas_invalidas)]
    
    # Remover linhas sem data
    df_interno = df_interno.dropna(subset=["Data"])
    df_externo = df_externo.dropna(subset=["Data"])
    
    # Converter colunas numéricas
    df_interno["Quantidade de litros"] = pd.to_numeric(df_interno["Quantidade de litros"], errors="coerce").fillna(0)
    df_interno["Valor Unitario"] = pd.to_numeric(df_interno["Valor Unitario"], errors="coerce").fillna(0)
    df_interno["KM Atual"] = pd.to_numeric(df_interno["KM Atual"], errors="coerce")

    df_externo["Quantidade de litros"] = (
        df_externo["Quantidade de litros"].astype(str)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    df_externo["Valor Unitario"] = df_externo["Valor Unitario"].apply(limpar_valor)
    df_externo["KM Atual"] = pd.to_numeric(df_externo["KM Atual"], errors="coerce")
    
    return df_interno, df_externo

def calcular_consumo_medio(df_interno, df_externo):
    df_km = pd.concat([df_interno[['Placa', 'KM Atual']], df_externo[['Placa', 'KM Atual']]])
    df_km = df_km.dropna(subset=['KM Atual'])
    consumo = df_km.groupby('Placa').agg({'KM Atual': ['max', 'min']})
    consumo.columns = ['km_max', 'km_min']
    consumo['km_rodado'] = consumo['km_max'] - consumo['km_min']
    consumo = consumo.sort_values('km_rodado', ascending=False).reset_index()
    return consumo

def preco_medio_ponderado(df):
    df_filtrado = df[df["Data"].dt.month >= 7]  # considerando meses a partir de julho
    return df_filtrado.groupby(df_filtrado["Data"].dt.to_period("M")).apply(
        lambda x: pd.Series({
            "Litros": x["Quantidade de litros"].sum(),
            "Preco Medio (R$/L)": (x["Valor Unitario"] * x["Quantidade de litros"]).sum() / x["Quantidade de litros"].sum() if x["Quantidade de litros"].sum() > 0 else 0,
            "Custo Total (R$)": (x["Valor Unitario"] * x["Quantidade de litros"]).sum()
        })
    ).reset_index()

def main():
    st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")
    st.title("📊 Dashboard de Abastecimento")

    arquivo = st.file_uploader("Faça upload da planilha Excel com as abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=["xls", "xlsx"])
    if arquivo is not None:
        df_interno, df_externo = carregar_dados(arquivo)

        consumo_medio = calcular_consumo_medio(df_interno, df_externo)
        preco_interno = preco_medio_ponderado(df_interno)
        preco_externo = preco_medio_ponderado(df_externo)
        
        preco_interno.rename(columns={"Data": "Periodo"}, inplace=True)
        preco_externo.rename(columns={"Data": "Periodo"}, inplace=True)

        aba1, aba2, aba3 = st.tabs(["📌 Consumo Médio", "⛽ Preço Médio Ponderado", "📅 Indicadores Mensais"])

        with aba1:
            st.subheader("Consumo Médio por Placa (KM Rodado)")
            st.dataframe(consumo_medio, use_container_width=True)

        with aba2:
            st.subheader("Preço Médio Ponderado - Interno (a partir de Julho)")
            st.dataframe(preco_interno.sort_values(by="Preco Medio (R$/L)", ascending=False), use_container_width=True)

            st.subheader("Preço Médio Ponderado - Externo (a partir de Julho)")
            st.dataframe(preco_externo.sort_values(by="Preco Medio (R$/L)", ascending=False), use_container_width=True)

            fig = px.line(
                pd.concat([
                    preco_interno.assign(Tipo="Interno"),
                    preco_externo.assign(Tipo="Externo")
                ]),
                x="Periodo", y="Preco Medio (R$/L)", color="Tipo", markers=True,
                title="Preço Médio Ponderado do Combustível (Mensal)"
            )
            st.plotly_chart(fig, use_container_width=True)

        with aba3:
            st.subheader("Litros e Custos Mensais - Interno x Externo")
            indicadores = pd.concat([
                preco_interno.assign(Tipo="Interno"),
                preco_externo.assign(Tipo="Externo")
            ])
            fig_litros = px.bar(indicadores, x="Periodo", y="Litros", color="Tipo", barmode="group", title="Litros Abastecidos por Mês")
            fig_custos = px.bar(indicadores, x="Periodo", y="Custo Total (R$)", color="Tipo", barmode="group", title="Custo Total por Mês")

            st.plotly_chart(fig_litros, use_container_width=True)
            st.plotly_chart(fig_custos, use_container_width=True)

    else:
        st.info("Por favor, faça upload da planilha para gerar os indicadores.")

if __name__ == "__main__":
    main()
