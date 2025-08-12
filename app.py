import streamlit as st
import pandas as pd
import datetime

def limpa_monetario(col):
    return pd.to_numeric(col.astype(str).str.replace(r'R\$\s*', '', regex=True), errors='coerce')

def processa_interno(df):
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    df['AnoMes'] = df['Data'].dt.to_period('M').astype(str)
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['Valor Unitario'] = pd.to_numeric(df['Valor Unitario'], errors='coerce')
    df['Valor Total'] = pd.to_numeric(df['Valor Total'], errors='coerce')
    if 'Tipo' in df.columns:
        df_entradas = df[df['Tipo'].str.lower() == 'entrada']
    else:
        df_entradas = df
    return df_entradas

def processa_externo(df):
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data'])
    df['AnoMes'] = df['Data'].dt.to_period('M').astype(str)
    df['Quantidade de litros'] = pd.to_numeric(df['Quantidade de litros'], errors='coerce')
    df['Valor Unitario'] = limpa_monetario(df['Valor Unitario'])
    df['Valor Total'] = limpa_monetario(df['Valor Total'])
    return df

def calcula_indicadores_mes(df, ano_mes):
    df_mes = df[df['AnoMes'] == ano_mes]
    litros = df_mes['Quantidade de litros'].sum()
    valor = df_mes['Valor Total'].sum()
    preco_medio = valor / litros if litros > 0 else 0
    return litros, valor, preco_medio

def main():
    st.title("🚛 Indicadores Mensais de Abastecimento - Interno e Externo")

    arquivo = st.sidebar.file_uploader("Upload do arquivo Excel (.xlsx) com abas 'Abastecimento Interno' e 'Abastecimento Externo'", type=['xlsx'])

    if arquivo is None:
        st.warning("Faça upload da planilha com as duas abas para continuar.")
        return

    df_interno = pd.read_excel(arquivo, sheet_name='Abastecimento Interno')
    df_externo = pd.read_excel(arquivo, sheet_name='Abastecimento Externo')

    df_interno_proc = processa_interno(df_interno)
    df_externo_proc = processa_externo(df_externo)

    hoje = datetime.date.today()
    ano_mes_atual = hoje.strftime('%Y-%m')

    litros_interno, valor_interno, preco_interno = calcula_indicadores_mes(df_interno_proc, ano_mes_atual)
    litros_externo, valor_externo, preco_externo = calcula_indicadores_mes(df_externo_proc, ano_mes_atual)

    litros_total = litros_interno + litros_externo
    valor_total = valor_interno + valor_externo
    preco_medio_total = valor_total / litros_total if litros_total > 0 else 0

    st.subheader(f"Indicadores do mês atual: {ano_mes_atual}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Litros Internos", f"{litros_interno:.2f} L")
    col2.metric("Valor Interno", f"R$ {valor_interno:.2f}")
    col3.metric("Preço Médio Interno", f"R$ {preco_interno:.3f} / L")

    col4, col5, col6 = st.columns(3)
    col4.metric("Litros Externos", f"{litros_externo:.2f} L")
    col5.metric("Valor Externo", f"R$ {valor_externo:.2f}")
    col6.metric("Preço Médio Externo", f"R$ {preco_externo:.3f} / L")

    col7, col8, col9 = st.columns(3)
    col7.metric("Litros Totais", f"{litros_total:.2f} L")
    col8.metric("Valor Total", f"R$ {valor_total:.2f}")
    col9.metric("Preço Médio Total", f"R$ {preco_medio_total:.3f} / L")

if __name__ == "__main__":
    main()
