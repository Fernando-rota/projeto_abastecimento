import streamlit as st
import pandas as pd
import plotly.express as px

def limpar_valor(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, str):
        return float(valor.replace('R$', '').replace('.', '').replace(',', '.').strip())
    return float(valor)

def main():
    st.title("Dashboard de Abastecimento")

    uploaded_file = st.file_uploader("Faça upload da planilha Excel 'abastecimento.xlsx' com as abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xls', 'xlsx'])
    if uploaded_file:
        # lê as abas da planilha
        df_interno = pd.read_excel(uploaded_file, sheet_name='Abastecimento Interno')
        df_externo = pd.read_excel(uploaded_file, sheet_name='Abastecimento Externo')

        # Tratamento básico
        df_interno["Data"] = pd.to_datetime(df_interno["Data"], errors="coerce")
        df_externo["Data"] = pd.to_datetime(df_externo["Data"], errors="coerce")

        # Remover placas inválidas
        placas_invalidas = ["-", "correção"]
        df_interno = df_interno[~df_interno["Placa"].isin(placas_invalidas)]
        df_externo = df_externo[~df_externo["Placa"].isin(placas_invalidas)]

        # Convertendo colunas numéricas
        df_interno["Quantidade de litros"] = pd.to_numeric(df_interno["Quantidade de litros"], errors="coerce").fillna(0)
        df_interno["Valor Unitario"] = df_interno["Valor Unitario"].apply(limpar_valor)

        df_externo["Quantidade de litros"] = pd.to_numeric(df_externo["Quantidade de litros"], errors="coerce").fillna(0)
        df_externo["Valor Unitario"] = df_externo["Valor Unitario"].apply(limpar_valor)

        # Consumo médio por placa (maior KM - menor KM das duas abas)
        df_km = pd.concat([
            df_interno[['Placa', 'KM Atual']],
            df_externo[['Placa', 'KM Atual']]
        ])
        consumo = df_km.groupby('Placa').agg({'KM Atual': ['max', 'min']})
        consumo.columns = ['km_max', 'km_min']
        consumo['km_rodado'] = consumo['km_max'] - consumo['km_min']
        consumo = consumo.sort_values('km_rodado', ascending=False).reset_index()

        st.subheader("Consumo médio por placa (km rodado)")
        st.dataframe(consumo)

        # Preço médio ponderado mensal (a partir de julho)
        def preco_medio_ponderado(df):
            df = df[df['Data'].dt.month >= 7]
            df = df.dropna(subset=['Quantidade de litros', 'Valor Unitario'])
            df['Valor Total'] = df['Quantidade de litros'] * df['Valor Unitario']
            return df.groupby(df['Data'].dt.to_period('M')).apply(
                lambda x: pd.Series({
                    'Litros': x['Quantidade de litros'].sum(),
                    'Custo Total (R$)': x['Valor Total'].sum(),
                    'Preço Médio (R$/L)': x['Valor Total'].sum() / x['Quantidade de litros'].sum() if x['Quantidade de litros'].sum() > 0 else 0
                })
            ).reset_index()

        preco_interno = preco_medio_ponderado(df_interno)
        preco_externo = preco_medio_ponderado(df_externo)

        st.subheader("Preço médio ponderado mensal - Interno")
        st.dataframe(preco_interno.sort_values('Preço Médio (R$/L)', ascending=False))

        st.subheader("Preço médio ponderado mensal - Externo")
        st.dataframe(preco_externo.sort_values('Preço Médio (R$/L)', ascending=False))

        # Gráfico preços
        preco_interno['Tipo'] = 'Interno'
        preco_externo['Tipo'] = 'Externo'
        df_precos = pd.concat([preco_interno, preco_externo])
        df_precos['Data'] = df_precos['Data'].dt.to_timestamp()

        fig = px.line(df_precos, x='Data', y='Preço Médio (R$/L)', color='Tipo',
                      title='Preço Médio Ponderado Mensal (Interno x Externo)', markers=True)
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Faça upload da planilha para gerar os indicadores.")

if __name__ == "__main__":
    main()
