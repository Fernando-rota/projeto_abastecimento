import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Painel de Manutenção e Movimentação de Pneus", layout="wide")

st.title("📊 Painel de Manutenção e Movimentação de Pneus")
st.markdown("⬆️ Faça upload da planilha com as abas 'manutencao' e 'pneu' (movimentação)")

uploaded_file = st.file_uploader("Upload da Planilha Excel", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)

    if 'manutencao' in xls.sheet_names and 'pneu' in xls.sheet_names:
        df_manut = pd.read_excel(xls, sheet_name='manutencao')
        df_pneu = pd.read_excel(xls, sheet_name='pneu')

        # Normaliza nomes colunas
        df_manut.columns = df_manut.columns.str.strip().str.upper()
        df_pneu.columns = df_pneu.columns.str.strip().str.upper()

        # Conversão de datas
        date_cols_manut = [col for col in df_manut.columns if 'DATA' in col]
        for c in date_cols_manut:
            df_manut[c] = pd.to_datetime(df_manut[c], errors='coerce')

        date_cols_pneu = [col for col in df_pneu.columns if 'DATA' in col]
        for c in date_cols_pneu:
            df_pneu[c] = pd.to_datetime(df_pneu[c], errors='coerce')

        # Converter valores monetários para numérico (ex: VALOR)
        if 'VALOR' in df_pneu.columns:
            df_pneu['VALOR'] = pd.to_numeric(df_pneu['VALOR'], errors='coerce')

        # Padronizar coluna PLACA
        for df in [df_manut, df_pneu]:
            if 'VEÍCULO - PLACA' in df.columns:
                df.rename(columns={'VEÍCULO - PLACA': 'PLACA'}, inplace=True)

        # Verificação colunas essenciais
        if 'PLACA' not in df_manut.columns:
            st.error("❌ Coluna obrigatória ausente: PLACA na aba 'manutencao'")
        elif 'PLACA' not in df_pneu.columns:
            st.error("❌ Coluna obrigatória ausente: PLACA na aba 'pneu'")
        else:
            # Filtros: placas e datas
            placas = sorted(set(df_manut['PLACA'].dropna().unique()) | set(df_pneu['PLACA'].dropna().unique()))
            st.sidebar.header("Filtros")
            selected_placas = st.sidebar.multiselect("Selecione as Placas", placas, default=placas)

            # Filtro de datas
            data_min_manut = df_manut['DATA DA MANUTENÇÃO'].min()
            data_max_manut = df_manut['DATA DA MANUTENÇÃO'].max()
            data_min_pneu = df_pneu['DATA DA MOVIMENTAÇÃO'].min()
            data_max_pneu = df_pneu['DATA DA MOVIMENTAÇÃO'].max()

            data_min = min(data_min_manut, data_min_pneu)
            data_max = max(data_max_manut, data_max_pneu)

            selected_data = st.sidebar.date_input("Intervalo de Datas", [data_min, data_max])

            # Aplica filtros
            if selected_placas:
                df_manut = df_manut[df_manut['PLACA'].isin(selected_placas)]
                df_pneu = df_pneu[df_pneu['PLACA'].isin(selected_placas)]

            if len(selected_data) == 2:
                start_date, end_date = pd.to_datetime(selected_data[0]), pd.to_datetime(selected_data[1])
                df_manut = df_manut[(df_manut['DATA DA MANUTENÇÃO'] >= start_date) & (df_manut['DATA DA MANUTENÇÃO'] <= end_date)]
                df_pneu = df_pneu[(df_pneu['DATA DA MOVIMENTAÇÃO'] >= start_date) & (df_pneu['DATA DA MOVIMENTAÇÃO'] <= end_date)]

            abas = st.tabs(["📊 Resumo Geral", "📈 Gráficos", "🔍 Detalhamento", "⚠️ Indicadores Pneus"])

            with abas[0]:
                st.subheader("📊 Indicadores Gerais")

                # Total manutenções e pneus movimentados
                total_manut = len(df_manut)
                total_pneu = len(df_pneu)

                st.markdown(f"**Total de Manutenções no Período:** {total_manut}")
                st.markdown(f"**Total de Movimentações de Pneus no Período:** {total_pneu}")

                # Manutenções por tipo
                if 'DESCRIÇÃO DA MANUTENÇÃO' in df_manut.columns:
                    manut_counts = df_manut['DESCRIÇÃO DA MANUTENÇÃO'].value_counts().rename_axis('Tipo de Manutenção').reset_index(name='Quantidade')
                    st.markdown("**Manutenções por Tipo:**")
                    st.dataframe(manut_counts)

                # Movimentação pneus por tipo
                if 'TIPO DA MOVIMENTAÇÃO' in df_pneu.columns:
                    pneu_counts = df_pneu['TIPO DA MOVIMENTAÇÃO'].value_counts().rename_axis('Tipo de Movimentação').reset_index(name='Quantidade')
                    st.markdown("**Movimentação de Pneus por Tipo:**")
                    st.dataframe(pneu_counts)

                # Valor gasto com pneus
                if 'VALOR' in df_pneu.columns:
                    total_valor = df_pneu['VALOR'].sum()
                    st.markdown(f"**Valor Total Gasto com Pneus:** R$ {total_valor:,.2f}")

                # KM médio entre manutenções por veículo
                if 'KM DO VEÍCULO' in df_manut.columns:
                    km_medio = df_manut.groupby('PLACA')['KM DO VEÍCULO'].apply(lambda x: x.sort_values().diff().mean()).reset_index()
                    km_medio.columns = ['PLACA', 'KM Médio Entre Manutenções']
                    st.markdown("**KM Médio Entre Manutenções por Veículo:**")
                    st.dataframe(km_medio)

            with abas[1]:
                st.subheader("📈 Visualizações Gráficas")

                # Manutenções por veículo ao longo do tempo
                if not df_manut.empty:
                    fig_manut = px.histogram(df_manut, x='DATA DA MANUTENÇÃO', color='PLACA',
                                            title='Frequência de Manutenções por Veículo',
                                            nbins=30)
                    st.plotly_chart(fig_manut, use_container_width=True)

                # Movimentação pneus por tipo
                if 'TIPO DA MOVIMENTAÇÃO' in df_pneu.columns:
                    fig_pneu = px.histogram(df_pneu, x='TIPO DA MOVIMENTAÇÃO', color='PLACA',
                                            title='Movimentação de Pneus por Tipo e Veículo')
                    st.plotly_chart(fig_pneu, use_container_width=True)

                # Valor gasto em pneus por veículo
                if 'VALOR' in df_pneu.columns:
                    fig_valor = px.bar(df_pneu.groupby('PLACA')['VALOR'].sum().reset_index(),
                                       x='PLACA', y='VALOR',
                                       title='Valor Total Gasto em Pneus por Veículo')
                    st.plotly_chart(fig_valor, use_container_width=True)

            with abas[2]:
                st.subheader("🔍 Detalhamento")

                st.markdown("**Registros de Manutenção**")
                st.dataframe(df_manut)

                st.markdown("**Registros de Movimentação de Pneus**")
                st.dataframe(df_pneu)

            with abas[3]:
                st.subheader("⚠️ Indicadores Específicos dos Pneus")

                # Top 10 pneus com menor autonomia (se existir)
                if 'AUTONOMIA' in df_pneu.columns:
                    df_pneu['AUTONOMIA'] = pd.to_numeric(df_pneu['AUTONOMIA'], errors='coerce')
                    df_piores = df_pneu.sort_values(by='AUTONOMIA').head(10)
                    st.markdown("Top 10 Pneus com Menor Autonomia")
                    st.dataframe(df_piores)
                else:
                    st.info("Coluna 'AUTONOMIA' não encontrada na aba 'pneu'.")

    else:
        st.error("❌ A planilha deve conter as abas 'manutencao' e 'pneu'.")
