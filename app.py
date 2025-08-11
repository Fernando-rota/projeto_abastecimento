import io
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="📄 Relatório PDF Consumo", layout="wide")
st.title("📄 Gerar Relatório PDF com Consumo e Abastecimento")

@st.cache_data
def load_data(file):
    interno = pd.read_excel(file, sheet_name="interno")
    externo = pd.read_excel(file, sheet_name="externo")
    consumo = pd.read_excel(file, sheet_name="consumo")
    return interno, externo, consumo

def calcular_consumo_medio(df):
    df = df.rename(columns=lambda x: x.strip())
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

def fig_bar(df, x_col, y_col, title):
    fig, ax = plt.subplots(figsize=(8,4))
    ax.bar(df[x_col], df[y_col], color='skyblue')
    ax.set_title(title)
    ax.set_ylabel(y_col)
    ax.set_xlabel(x_col)
    ax.grid(axis='y')
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def df_to_reportlab_table(df):
    data = [list(df.columns)]
    for row in df.itertuples(index=False):
        data.append(list(row))
    table = Table(data, repeatRows=1)
    style = [
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]
    table.setStyle(style)
    return table

def create_pdf(interno, externo, consumo, consumo_medio_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Relatório de Consumo e Abastecimento", styles['Title']))
    story.append(Spacer(1,12))

    # Tabelas resumo
    story.append(Paragraph("Consumo Interno (Litros por Placa):", styles['Heading2']))
    resumo_interno = interno.groupby("Placa")["Quantidade de litros"].sum().reset_index()
    story.append(df_to_reportlab_table(resumo_interno))
    story.append(Spacer(1,12))

    story.append(Paragraph("Abastecimento Externo (Litros por Placa):", styles['Heading2']))
    resumo_externo = externo.groupby("Placa")["Quantidade de litros"].sum().reset_index()
    story.append(df_to_reportlab_table(resumo_externo))
    story.append(Spacer(1,12))

    story.append(Paragraph("Consumo Médio Real (km/l):", styles['Heading2']))
    story.append(df_to_reportlab_table(consumo_medio_df))
    story.append(Spacer(1,12))

    # Gráficos - geramos imagens matplotlib no buffer e inserimos depois
    # Vamos salvar figuras temporárias e inserir como imagens

    # Consumo Interno gráfico
    fig1 = fig_bar(resumo_interno, "Placa", "Quantidade de litros", "Consumo Interno")
    img_buffer1 = io.BytesIO()
    fig1.savefig(img_buffer1, format='PNG')
    plt.close(fig1)
    img_buffer1.seek(0)

    # Abastecimento Externo gráfico
    fig2 = fig_bar(resumo_externo, "Placa", "Quantidade de litros", "Abastecimento Externo")
    img_buffer2 = io.BytesIO()
    fig2.savefig(img_buffer2, format='PNG')
    plt.close(fig2)
    img_buffer2.seek(0)

    # Consumo Médio gráfico
    fig3 = fig_bar(consumo_medio_df, "PLACA", "Consumo Médio (km/l)", "Consumo Médio Real")
    img_buffer3 = io.BytesIO()
    fig3.savefig(img_buffer3, format='PNG')
    plt.close(fig3)
    img_buffer3.seek(0)

    from reportlab.platypus import Image

    story.append(Paragraph("Gráficos:", styles['Heading2']))
    story.append(Spacer(1,12))

    story.append(Image(img_buffer1, width=400, height=200))
    story.append(Spacer(1,12))

    story.append(Image(img_buffer2, width=400, height=200))
    story.append(Spacer(1,12))

    story.append(Image(img_buffer3, width=400, height=200))
    story.append(Spacer(1,12))

    doc.build(story)
    buffer.seek(0)
    return buffer

file = st.file_uploader("📂 Envie o arquivo Excel (.xlsx)", type=["xlsx"])

if file:
    interno, externo, consumo = load_data(file)

    # Tirar espaços das colunas
    interno.columns = interno.columns.str.strip()
    externo.columns = externo.columns.str.strip()
    consumo.columns = consumo.columns.str.strip()

    consumo_medio_df = calcular_consumo_medio(consumo)

    st.subheader("Consumo Médio")
    st.dataframe(consumo_medio_df)

    pdf_buffer = create_pdf(interno, externo, consumo, consumo_medio_df)

    st.download_button(
        label="📥 Baixar Relatório PDF",
        data=pdf_buffer,
        file_name="relatorio_consumo.pdf",
        mime="application/pdf"
    )
