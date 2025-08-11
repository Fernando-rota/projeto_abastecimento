import io
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.io as pio
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime

st.set_page_config(page_title="Relatório PDF Consumo e Abastecimento", layout="wide")
st.title("📊 BI Consumo e Abastecimento + Exportação PDF")

@st.cache_data
def load_data(file_path):
    interno = pd.read_excel(file_path, sheet_name='interno')
    externo = pd.read_excel(file_path, sheet_name='externo')
    consumo = pd.read_excel(file_path, sheet_name='consumo')

    for df in [interno, externo, consumo]:
        df.rename(columns=lambda x: x.strip().lower().replace(' ', '_'), inplace=True)

    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')
    consumo['data'] = pd.to_datetime(consumo['data'], errors='coerce')

    interno.dropna(subset=['data'], inplace=True)
    externo.dropna(subset=['data'], inplace=True)
    consumo.dropna(subset=['data'], inplace=True)

    return interno, externo, consumo

def preprocess_abastecimentos(df, litros_col, km_col, combust_col):
    df = df.rename(columns={
        litros_col: 'litros',
        km_col: 'km',
        combust_col: 'combustivel'
    })
    df['km'] = df['km'].astype(str).str.replace(',', '.', regex=False)
    df['litros'] = df['litros'].astype(str).str.replace(',', '.', regex=False)
    df['km'] = pd.to_numeric(df['km'], errors='coerce')
    df['litros'] = pd.to_numeric(df['litros'], errors='coerce')
    df = df.dropna(subset=['km', 'litros', 'placa'])
    return df[['data', 'placa', 'combustivel', 'litros', 'km']]

def plot_consumo_medio(consumo_filt):
    resumo_consumo = consumo_filt.groupby('placa').agg(
        km_min=('km', 'min'),
        km_max=('km', 'max'),
        litros_totais=('litros', 'sum')
    ).reset_index()
    resumo_consumo['km_rodados'] = resumo_consumo['km_max'] - resumo_consumo['km_min']
    resumo_consumo['consumo_medio_km_por_litro'] = resumo_consumo.apply(
        lambda r: r['km_rodados'] / r['litros_totais'] if r['litros_totais'] > 0 else None, axis=1)
    resumo_consumo = resumo_consumo.sort_values('consumo_medio_km_por_litro', ascending=False)

    fig = px.bar(resumo_consumo, x='placa', y='consumo_medio_km_por_litro',
                 labels={'consumo_medio_km_por_litro': 'Km por Litro', 'placa': 'Placa'},
                 title='Consumo Médio (Km por Litro) por Veículo')
    return resumo_consumo, fig

def plot_litros_total(abastecimentos):
    resumo_ab = abastecimentos.groupby('placa').agg(
        total_litros=('litros', 'sum'),
        media_km=('km', 'mean'),
        registros=('data', 'count')
    ).reset_index()
    fig = px.bar(resumo_ab, x='placa', y='total_litros',
                 labels={'total_litros': 'Total Litros', 'placa': 'Placa'},
                 title='Total de Litros Consumidos por Veículo')
    return resumo_ab, fig

def save_fig_to_bytes(fig):
    img_bytes = pio.to_image(fig, format='png', width=700, height=400, scale=2)
    return io.BytesIO(img_bytes)

def gerar_pdf(resumo_consumo, resumo_abastecimento, fig1_bytes, fig2_bytes):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Relatório Consumo e Abastecimento")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # Consumo médio tabela
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 100, "Consumo Médio (Km por Litro) por Veículo")

    y = height - 120
    c.setFont("Helvetica", 9)
    for i, row in resumo_consumo.iterrows():
        linha = f"{row['placa']}: Km Rodados: {int(row['km_rodados'])}, Litros: {row['litros_totais']:.2f}, Consumo Médio: {row['consumo_medio_km_por_litro']:.2f}"
        c.drawString(50, y, linha)
        y -= 15
        if y < 100:
            c.showPage()
            y = height - 50

    # Inserir gráfico consumo médio
    c.showPage()
    c.drawImage(ImageReader(fig1_bytes), 50, height/2 - 100, width=width-100, height=300)

    # Página seguinte - Abastecimento total litros
    c.showPage()
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 50, "Total Litros Consumidos por Veículo")

    y = height - 70
    c.setFont("Helvetica", 9)
    for i, row in resumo_abastecimento.iterrows():
        linha = f"{row['placa']}: Total Litros: {row['total_litros']:.2f}, Média Km: {int(row['media_km'])}, Registros: {row['registros']}"
        c.drawString(50, y, linha)
        y -= 15
        if y < 100:
            c.showPage()
            y = height - 50

    # Inserir gráfico litros total
    c.showPage()
    c.drawImage(ImageReader(fig2_bytes), 50, height/2 - 100, width=width-100, height=300)

    c.save()
    buffer.seek(0)
    return buffer

uploaded_file = st.file_uploader("📁 Faça upload do arquivo Excel com abas: interno, externo, consumo", type=["xlsx"])
if uploaded_file:
    interno, externo, consumo = load_data(uploaded_file)

    placas_unicas = sorted(set(interno['placa'].dropna().unique()) |
                          set(externo['placa'].dropna().unique()) |
                          set(consumo['placa'].dropna().unique()))
    placas_selected = st.multiselect("Selecione placas:", placas_unicas, default=placas_unicas)

    combust_interno = interno['tipo'].dropna().unique() if 'tipo' in interno.columns else []
    combust_externo = externo['tipo_combustivel'].dropna().unique() if 'tipo_combustivel' in externo.columns else []
    combust_unificados = sorted(set(combust_interno) | set(combust_externo))
    combust_selected = st.multiselect("Selecione tipos de combustível:", combust_unificados, default=combust_unificados)

    data_min = min(interno['data'].min(), externo['data'].min(), consumo['data'].min())
    data_max = max(interno['data'].max(), externo['data'].max(), consumo['data'].max())
    data_range = st.date_input("Selecione período:", [data_min, data_max])

    data_start, data_end = pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])

    interno_filt = interno[
        (interno['placa'].isin(placas_selected)) &
        (interno['data'] >= data_start) & (interno['data'] <= data_end)
    ]
    externo_filt = externo[
        (externo['placa'].isin(placas_selected)) &
        (externo['data'] >= data_start) & (externo['data'] <= data_end)
    ]

    if 'tipo' in interno_filt.columns:
        interno_filt = interno_filt[interno_filt['tipo'].isin(combust_selected)]
    if 'tipo_combustivel' in externo_filt.columns:
        externo_filt = externo_filt[externo_filt['tipo_combustivel'].isin(combust_selected)]

    interno_proc = preprocess_abastecimentos(interno_filt, 'quantidade_de_litros', 'km_atual', 'tipo')
    externo_proc = preprocess_abastecimentos(externo_filt, 'quantidade_de_litros', 'km_atual', 'tipo_combustivel')

    abastecimentos = pd.concat([interno_proc, externo_proc], ignore_index=True)

    resumo_ab, fig2 = plot_litros_total(abastecimentos)

    consumo_filt = consumo[
        (consumo['placa'].isin(placas_selected)) &
        (consumo['data'] >= data_start) & (consumo['data'] <= data_end)
    ]

    consumo_filt.rename(columns={'qtd_litros': 'litros', 'km': 'km'}, inplace=True)
    consumo_filt['litros'] = consumo_filt['litros'].astype(str).str.replace(',', '.', regex=False)
    consumo_filt['km'] = consumo_filt['km'].astype(str).str.replace(',', '.', regex=False)
    consumo_filt['litros'] = pd.to_numeric(consumo_filt['litros'], errors='coerce')
    consumo_filt['km'] = pd.to_numeric(consumo_filt['km'], errors='coerce')
    consumo_filt.dropna(subset=['litros', 'km'], inplace=True)

    resumo_consumo, fig1 = plot_consumo_medio(consumo_filt)

    st.header("🚛 Consumo Médio por Veículo")
    st.dataframe(resumo_consumo.style.format({
        'km_min': '{:,.0f}',
        'km_max': '{:,.0f}',
        'litros_totais': '{:,.2f}',
        'km_rodados': '{:,.0f}',
        'consumo_medio_km_por_litro': '{:.2f}'
    }))
    st.plotly_chart(fig1, use_container_width=True)

    st.header("⛽ Total Litros Consumidos")
    st.dataframe(resumo_ab.style.format({
        'total_litros': '{:,.2f}',
        'media_km': '{:,.0f}',
        'registros': '{:,.0f}'
    }))
    st.plotly_chart(fig2, use_container_width=True)

    if st.button("📄 Gerar Relatório PDF"):
        fig1_bytes = save_fig_to_bytes(fig1)
        fig2_bytes = save_fig_to_bytes(fig2)
        pdf_buffer = gerar_pdf(resumo_consumo, resumo_ab, fig1_bytes, fig2_bytes)

        st.download_button(
            label="📥 Baixar Relatório PDF",
            data=pdf_buffer,
            file_name="relatorio_consumo_abastecimento.pdf",
            mime="application/pdf"
        )
else:
    st.info("Faça upload do arquivo Excel para começar.")
