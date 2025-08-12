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
    df_int = pd.read_excel(uploaded_file, sheet_name="Abastecimento Interno")
    df_ext = pd.read_excel(uploaded_file, sheet_name="Abastecimento Externo")

    # Datas
    df_int["Data"] = pd.to_datetime(df_int["Data"], errors="coerce")
    df_ext["Data"] = pd.to_datetime(df_ext["Data"], errors="coerce")

    # Remove placas inválidas
    placas_invalidas = ["-", "correção"]
    df_int = df_int[~df_int["Placa"].astype(str).str.strip().str.lower().isin(placas_invalidas)]
    df_ext = df_ext[~df_ext["Placa"].astype(str).str.strip().str.lower().isin(placas_invalidas)]

    # Limpa valores numéricos
    df_int["Quantidade de litros"] = pd.to_numeric(df_int["Quantidade de litros"], errors="coerce").fillna(0)
    df_int["Valor Total"] = df_int["Valor Total"].apply(limpar_valor)

    df_ext["Quantidade de litros"] = pd.to_numeric(df_ext["Quantidade de litros"], errors="coerce").fillna(0)
    df_ext["Valor Total"] = df_ext["Valor Total"].apply(limpar_valor)

    # Tipo combustível
    if "Tipo" in df_int.columns:
        df_int["Tipo"] = df_int["Tipo"].astype(str).str.strip().str.upper()
    else:
        df_int["Tipo"] = "N/A"
    if "Tipo" in df_ext.columns:
        df_ext["Tipo"] = df_ext["Tipo"].astype(str).str.strip().str.upper()
    else:
        df_ext["Tipo"] = "N/A"

    # Limpa placa (maiúscula e strip)
    df_int["Placa"] = df_int["Placa"].astype(str).str.strip().str.upper()
    df_ext["Placa"] = df_ext["Placa"].astype(str).str.strip().str.upper()

    # KM Atual numérico
    df_int["KM Atual"] = pd.to_numeric(df_int["KM Atual"], errors="coerce")
    df_ext["KM Atual"] = pd.to_numeric(df_ext["KM Atual"], errors="coerce")

    return df_int, df_ext

def consumo_e_autonomia(df_interno, df_externo, filtro_placa=None):
    df_km = pd.concat([df_interno[['Placa', 'KM Atual']], df_externo[['Placa', 'KM Atual']]], ignore_index=True)
    df_litros = pd.concat([df_interno[['Placa', 'Quantidade de litros']], df_externo[['Placa', 'Quantidade de litros']]], ignore_index=True)

    if filtro_placa:
        df_km = df_km[df_km['Placa'].isin(filtro_placa)]
        df_litros = df_litros[df_litros['Placa'].isin(filtro_placa)]

    resultado = []
    for placa in df_km['Placa'].unique():
        grupo_km = df_km[df_km['Placa'] == placa]
        km_max = grupo_km['KM Atual'].max()
        km_min = grupo_km['KM Atual'].min()
        km_rodado = km_max - km_min if pd.notna(km_max) and pd.notna(km_min) else 0

        grupo_litros = df_litros[df_litros['Placa'] == placa]
        litros_total = grupo_litros['Quantidade de litros'].sum()

        autonomia = km_rodado / litros_total if litros_total > 0 else None

        resultado.append({
            'Placa': placa,
            'KM Rodado': km_rodado,
            'Litros Consumidos': litros_total,
            'Autonomia (km/l)': round(autonomia, 2) if autonomia else None
        })
    return pd.DataFrame(resultado).sort_values('KM Rodado', ascending=False)

def indicadores_mensais(df_interno, df_externo, filtro_placa=None, filtro_tipo=None, filtro_mes_ano=None):
    df_interno_f = df_interno.copy()
    df_externo_f = df_externo.copy()

    if filtro_placa:
        df_interno_f = df_interno_f[df_interno_f['Placa'].isin(filtro_placa)]
        df_externo_f = df_externo_f[df_externo_f['Placa'].isin(filtro_placa)]
    if filtro_tipo:
        df_interno_f = df_interno_f[df_interno_f['Tipo'].isin(filtro_tipo)]
        df_externo_f = df_externo_f[df_externo_f['Tipo'].isin(filtro_tipo)]
    if filtro_mes_ano:
        df_interno_f = df_interno_f[df_interno_f['Data'].dt.to_period('M').isin(filtro_mes_ano)]
        df_externo_f = df_externo_f[df_externo_f['Data'].dt.to_period('M').isin(filtro_mes_ano)]

    def agrega(df, label):
        grouped = df.groupby(df['Data'].dt.to_period('M')).agg({
            'Quantidade de litros': 'sum',
            'Valor Total': 'sum'
        }).rename(columns={
            'Quantidade de litros': f'Litros {label}',
            'Valor Total': f'Custo {label}'
        })
        return grouped

    interno_agg = agrega(df_interno_f, 'Interno')
    externo_agg = agrega(df_externo_f, 'Externo')
    df_result = interno_agg.join(externo_agg, how='outer').fillna(0)
    df_result.index = df_result.index.to_timestamp()
    return df_result.sort_index()

def main():
    st.set_page_config(page_title="Dashboard Abastecimento", layout="wide")
    st.title("📊 Dashboard de Abastecimento")

    arquivo = st.sidebar.file_uploader("Upload da planilha Excel (.xlsx)", type=["xlsx"])
    if not arquivo:
        st.info("Faça upload da planilha com abas 'Abastecimento Interno' e 'Abastecimento Externo'.")
        return

    df_interno, df_externo = carregar_dados(arquivo)

    # Preparar filtros
    placas = sorted(set(df_interno['Placa']).union(set(df_externo['Placa'])))
    tipos_combustivel = sorted(set(df_interno['Tipo']).union(set(df_externo['Tipo'])))
    meses_anos = sorted(set(df_interno['Data'].dt.to_period('M').unique()).union(set(df_externo['Data'].dt.to_period('M').unique())))
    meses_anos_str = [str(m) for m in meses_anos]

    st.sidebar.markdown("### Filtros")
    filtro_placa = st.sidebar.multiselect("Selecione as placas", placas, default=placas)
    filtro_tipo = st.sidebar.multiselect("Selecione os tipos de combustível", tipos_combustivel, default=tipos_combustivel)
    filtro_mes_ano = st.sidebar.multiselect("Selecione mês/ano", meses_anos_str, default=meses_anos_str)
    filtro_mes_ano = [pd.Period(m) for m in filtro_mes_ano] if filtro_mes_ano else None

    abas = st.tabs(["Consumo Médio e Autonomia", "Indicadores Mensais"])

    with abas[0]:
        st.subheader("Consumo Médio e Autonomia por Placa")
        df_consumo = consumo_e_autonomia(df_interno, df_externo, filtro_placa)
        st.dataframe(df_consumo, use_container_width=True)

    with abas[1]:
        st.subheader("Litros e Custos Mensais")
        df_indicadores = indicadores_mensais(df_interno, df_externo, filtro_placa, filtro_tipo, filtro_mes_ano)
        st.dataframe(df_indicadores, use_container_width=True)

        fig_litros = px.bar(df_indicadores, x=df_indicadores.index, y=[col for col in df_indicadores.columns if col.startswith('Litros')],
                            barmode='group', title="Litros Abastecidos por Mês")
        st.plotly_chart(fig_litros, use_container_width=True)

        fig_custos = px.bar(df_indicadores, x=df_indicadores.index, y=[col for col in df_indicadores.columns if col.startswith('Custo')],
                            barmode='group', title="Custo Total por Mês (R$)")
        st.plotly_chart(fig_custos, use_container_width=True)

if __name__ == "__main__":
    main()
