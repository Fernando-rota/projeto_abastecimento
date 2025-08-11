import io
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.io as pio
from pptx import Presentation
from pptx.util import Inches

st.set_page_config(page_title="📊 BI Consumo + Export PPTX", layout="wide")
st.title("📊 BI Completo: Consumo e Abastecimento + Exportação PPTX")

@st.cache_data
def load_data(file):
    interno = pd.read_excel(file, sheet_name="interno")
    externo = pd.read_excel(file, sheet_name="externo")
    consumo = pd.read_excel(file, sheet_name="consumo")
    return interno, externo, consumo

def calcular_consumo_medio(df):
    df = df.rename(columns=lambda x: x.strip())  # remove espaços extras
    resultados = []
    for placa, grupo in df.groupby("PLACA"):
        grupo = grupo.dropna(subset=["KM", "QTD LITROS"])
        if len(grupo) < 2:
            continue
        menor_km = grupo["KM"].min()
        maior_km = grupo["KM"].max()
        km_rodados = maior_km - menor_km
        litros_total = grupo["QTD LITROS"].sum()
        consumo_medio = km_rodados / litros_total if litros_total > 0 else None
        resultados.append({
            "PLACA": placa,
            "KM Inicial": menor_km,
            "KM Final": maior_km,
            "KM Rodados": km_rodados,
            "Litros Consumidos": litros_total,
            "Consumo Médio (km/l)": round(consumo_medio, 2) if consumo_medio else None
        })
    return pd.DataFrame(resultados)

def fig_to_image(fig):
    try:
        png_bytes = pio.to_image(fig, format="png", width=900, height=500, scale=2)
        return io.BytesIO(png_bytes)
    except RuntimeError as e:
        st.error(
            "⚠️ Erro ao gerar imagem PNG do gráfico. O Kaleido precisa do Google Chrome instalado para funcionar.\n"
            "Por favor, instale o Chrome para gerar PPTX com gráficos.\n\nErro:\n" + str(e)
        )
        return None

def criar_ppt(resumo_consumo, fig_consumo, resumo_abastecimento, fig_abastecimento, consumo_medio_df, fig_consumo_medio):
    prs = Presentation()

    # Slide 1 - Resumo Consumo Interno
    slide1 = prs.slides.add_slide(prs.slide_layouts[5])
    tb1 = slide1.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(5))
    tf1 = tb1.text_frame
    tf1.text = "Resumo Consumo Interno\n\n" + resumo_consumo.to_string(index=False)

    # Slide 2 - Gráfico Consumo Interno
    if fig_consumo is not None:
        img = fig_to_image(fig_consumo)
        if img is not None:
            slide2 = prs.slides.add_slide(prs.slide_layouts[5])
            slide2.shapes.add_picture(img, Inches(0.5), Inches(0.5), Inches(9), Inches(5))

    # Slide 3 - Resumo Abastecimento Externo
    slide3 = prs.slides.add_slide(prs.slide_layouts[5])
    tb3 = slide3.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(5))
    tf3 = tb3.text_frame
    tf3.text = "Resumo Abastecimento Externo\n\n" + resumo_abastecimento.to_string(index=False)

    # Slide 4 - Gráfico Abastecimento Externo
    if fig_abastecimento is not None:
        img = fig_to_image(fig_abastecimento)
        if img is not None:
            slide4 = prs.slides.add_slide(prs.slide_layouts[5])
            slide4.shapes.add_picture(img, Inches(0.5), Inches(0.5), Inches(9), Inches(5))

    # Slide 5 - Consumo Médio
    slide5 = prs.slides.add_slide(prs.slide_layouts[5])
    tb5 = slide5.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(5))
    tf5 = tb5.text_frame
    tf5.text = "Consumo Médio Real (km/l)\n\n" + consumo_medio_df.to_string(index=False)

    # Slide 6 - Gráfico Consumo Médio
    if fig_consumo_medio is not None:
        img = fig_to_image(fig_consumo_medio)
        if img is not None:
            slide6 = prs.slides.add_slide(prs.slide_layouts[5])
            slide6.shapes.add_picture(img, Inches(0.5), Inches(0.5), Inches(9), Inches(5))

    pptx_io = io.BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

file = st.file_uploader("📂 Envie o arquivo Excel (.xlsx)", type=["xlsx"])

if file:
    interno, externo, consumo = load_data(file)

    # Limpar espaços nas colunas
    interno.columns = interno.columns.str.strip()
    externo.columns = externo.columns.str.strip()
    consumo.columns = consumo.columns.str.strip()

    # Criar abas para separar os relatórios
    tab1, tab2, tab3 = st.tabs(["Consumo Interno", "Abastecimento Externo", "Consumo Médio Real"])

    with tab1:
        resumo_consumo = interno.groupby("Placa")["Quantidade de litros"].sum().reset_index()
        fig_consumo = px.bar(resumo_consumo, x="Placa", y="Quantidade de litros",
                             title="Consumo Interno", text_auto=True)
        st.dataframe(resumo_consumo)
        st.plotly_chart(fig_consumo, use_container_width=True)

    with tab2:
        resumo_abastecimento = externo.groupby("Placa")["Quantidade de litros"].sum().reset_index()
        fig_abastecimento = px.bar(resumo_abastecimento, x="Placa", y="Quantidade de litros",
                                  title="Abastecimento Externo", text_auto=True)
        st.dataframe(resumo_abastecimento)
        st.plotly_chart(fig_abastecimento, use_container_width=True)

    with tab3:
        consumo_medio_df = calcular_consumo_medio(consumo)
        fig_consumo_medio = px.bar(consumo_medio_df, x="PLACA", y="Consumo Médio (km/l)",
                                  title="Consumo Médio Real (Menor/Maior KM)", text_auto=True)
        st.dataframe(consumo_medio_df)
        st.plotly_chart(fig_consumo_medio, use_container_width=True)

    pptx_file = criar_ppt(
        resumo_consumo if 'resumo_consumo' in locals() else pd.DataFrame(),
        fig_consumo if 'fig_consumo' in locals() else None,
        resumo_abastecimento if 'resumo_abastecimento' in locals() else pd.DataFrame(),
        fig_abastecimento if 'fig_abastecimento' in locals() else None,
        consumo_medio_df if 'consumo_medio_df' in locals() else pd.DataFrame(),
        fig_consumo_medio if 'fig_consumo_medio' in locals() else None
    )

    st.download_button(
        label="📥 Baixar Relatório PPTX",
        data=pptx_file,
        file_name="relatorio_consumo.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
