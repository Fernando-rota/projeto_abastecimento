import io
from pptx import Presentation
from pptx.util import Inches
import tempfile

# Função para criar apresentação PPTX
def criar_ppt(resumo_consumo_df, fig_consumo, resumo_consumo_ab_df, fig_consumo_ab):
    prs = Presentation()
    blank_slide_layout = prs.slide_layouts[6]  # slide vazio

    # Slide 1: título
    slide1 = prs.slides.add_slide(blank_slide_layout)
    title_shape = slide1.shapes.title
    if title_shape:
        title_shape.text = "Dashboard Consumo e Abastecimento - Resumo"
    else:
        txBox = slide1.shapes.add_textbox(Inches(1), Inches(0.5), Inches(8), Inches(1))
        tf = txBox.text_frame
        tf.text = "Dashboard Consumo e Abastecimento - Resumo"

    # Slide 2: gráfico consumo médio
    slide2 = prs.slides.add_slide(blank_slide_layout)
    slide2.shapes.add_picture(fig_to_image(fig_consumo), Inches(0.5), Inches(0.5), Inches(9), Inches(5))

    # Slide 3: tabela resumo consumo médio (convertida em texto simples)
    slide3 = prs.slides.add_slide(blank_slide_layout)
    text = "Resumo Consumo Médio por Veículo\n\n"
    for _, row in resumo_consumo_df.iterrows():
        text += f"Placa: {row['placa']} | Km rodados: {row['km_rodados']:.0f} | Litros: {row['litros_totais']:.2f} | Consumo Médio: {row['consumo_medio_km_por_litro']:.2f}\n"
    txBox = slide3.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(6))
    tf = txBox.text_frame
    tf.text = text

    # Slide 4: gráfico litros consumidos (aba consumo)
    slide4 = prs.slides.add_slide(blank_slide_layout)
    slide4.shapes.add_picture(fig_to_image(fig_consumo_ab), Inches(0.5), Inches(0.5), Inches(9), Inches(5))

    # Slide 5: tabela resumo aba consumo
    slide5 = prs.slides.add_slide(blank_slide_layout)
    text2 = "Indicadores Aba Consumo\n\n"
    for _, row in resumo_consumo_ab_df.iterrows():
        text2 += f"Placa: {row['placa']} | Total Litros: {row['total_litros_consumo']:.2f} | Média Km: {row['media_km_consumo']:.0f} | Registros: {row['registros']}\n"
    txBox2 = slide5.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(6))
    tf2 = txBox2.text_frame
    tf2.text = text2

    # Salvar em buffer
    pptx_io = io.BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

# Função auxiliar para converter figura Plotly em imagem PNG em disco temporário
def fig_to_image(fig):
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    fig.write_image(tmp.name)
    return tmp.name

# --- No seu código Streamlit, após criar os gráficos e DataFrames resumo_consumo, fig_consumo, resumo_consumo_ab, fig_consumo_ab ---

pptx_file = criar_ppt(resumo_consumo, fig1, resumo_consumo_ab, fig2)

st.download_button(
    label="📥 Exportar Apresentação PowerPoint",
    data=pptx_file,
    file_name="dashboard_consumo_veiculos.pptx",
    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
