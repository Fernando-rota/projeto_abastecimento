import io
import tempfile
import pandas as pd
import streamlit as st
import plotly.express as px
from pptx import Presentation
from pptx.util import Inches
import plotly.io as pio

st.set_page_config(page_title="BI Consumo + Export PPTX", layout="wide")
st.title("📊 BI Completo: Consumo e Abastecimento + Exportação PPTX")

@st.cache_data
def load_data(file_path):
    interno = pd.read_excel(file_path, sheet_name="Interno")
    externo = pd.read_excel(file_path, sheet_name="Externo")
    return interno, externo

# Função para converter figura Plotly em imagem PNG usando Kaleido
def fig_to_image(fig):
    png_bytes = pio.to_image(fig, format="png", width=900, height=500, scale=2)
    return io.BytesIO(png_bytes)

# Função para criar PPTX
def criar_ppt(resumo_consumo, fig_consumo, resumo_consumo_ab, fig_abastecimento):
    prs = Presentation()

    # Slide 1 - Resumo Consumo
    slide1 = prs.slides.add_slide(prs.slide_layouts[5])
    textbox = slide1.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(5))
    tf = textbox.text_frame
    tf.text = "Resumo Consumo\n\n" + resumo_consumo.to_string(index=False)

    # Slide 2 - Gráfico Consumo
    slide2 = prs.slides.add_slide(prs.slide_layouts[5])
    slide2.shapes.add_picture(fig_to_image(fig_consumo), Inches(0.5), Inches(0.5), Inches(9), Inches(5))

    # Slide 3 - Resumo Abastecimento
    slide3 = prs.slides.add_slide(prs.slide_layouts[5])
    textbox3 = slide3.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(5))
    tf3 = textbox3.text_frame
    tf3.text = "Resumo Abastecimento\n\n" + resumo_consumo_ab.to_string(index=False)

    # Slide 4 - Gráfico Abastecimento
    slide4 = prs.slides.add_slide(prs.slide_layouts[5])
    slide4.shapes.add_picture(fig_to_image(fig_abastecimento), Inches(0.5), Inches(0.5), Inches(9), Inches(5))

    # Salva o PPTX em memória
    pptx_io = io.BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

# Upload do arquivo
file = st.file_uploader("📂 Envie o arquivo Excel", type=["xlsx"])

if file:
    interno, externo = load_data(file)

    # Resumo Consumo (exemplo fictício)
    resumo_consumo = interno.groupby("Placa")["Litros"].sum().reset_index()
    fig1 = px.bar(resumo_consumo, x="Placa", y="Litros", title="Consumo Interno")

    # Resumo Abastecimento
    resumo_consumo_ab = externo.groupby("Placa")["Litros"].sum().reset_index()
    fig2 = px.bar(resumo_consumo_ab, x="Placa", y="Litros", title="Abastecimento Externo")

    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)

    pptx_file = criar_ppt(resumo_consumo, fig1, resumo_consumo_ab, fig2)

    st.download_button(
        label="📥 Baixar PPTX",
        data=pptx_file,
        file_name="relatorio_consumo.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
