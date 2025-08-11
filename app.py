import io
import tempfile
import pandas as pd
import streamlit as st
import plotly.express as px
from pptx import Presentation
from pptx.util import Inches

st.set_page_config(page_title="BI Consumo + Export PPTX", layout="wide")
st.title("📊 BI Completo: Consumo e Abastecimento + Exportação PPTX")

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

def fig_to_image(fig):
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    fig.write_image(tmp.name)
    return tmp.name

def criar_ppt(resumo_consumo_df, fig_consumo, resumo_consumo_ab_df, fig_consumo_ab):
    prs = Presentation()
    blank_slide_layout = prs.slide_layouts[6]

    # Slide 1: título
    slide1 = prs.slides.add_slide(blank_slide_layout)
    txBox = slide1.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(1))
    tf = txBox.text_frame
    tf.text = "Dashboard Consumo e Abastecimento - Resumo"

    # Slide 2: gráfico consumo médio (aba consumo)
    slide2 = prs.slides.add_slide(blank_slide_layout)
    slide2.shapes.add_picture(fig_to_image(fig_consumo), Inches(0.5), Inches(0.5), Inches(9), Inches(5))

    # Slide 3: tabela resumo consumo médio (aba consumo)
    slide3 = prs.slides.add_slide(blank_slide_layout)
    text = "Resumo Consumo Médio (Base: Aba Consumo)\n\n"
    for _, row in resumo_consumo_df.iterrows():
        text += f"Placa: {row['placa']} | Km rodados: {row['km_rodados']:.0f} | Litros: {row['litros_totais']:.2f} | Consumo Médio: {row['consumo_medio_km_por_litro']:.2f}\n"
    txBox3 = slide3.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(6))
    tf3 = txBox3.text_frame
    tf3.text = text

    # Slide 4: gráfico litros consumidos (aba interno + externo)
    slide4 = prs.slides.add_slide(blank_slide_layout)
    slide4.shapes.add_picture(fig_to_image(fig_consumo_ab), Inches(0.5), Inches(0.5), Inches(9), Inches(5))

    # Slide 5: tabela resumo aba interno + externo
    slide5 = prs.slides.add_slide(blank_slide_layout)
    text2 = "Indicadores Abastecimento Interno + Externo\n\n"
    for _, row in resumo_consumo_ab_df.iterrows():
        text2 += f"Placa: {row['placa']} | Total Litros: {row['total_litros_consumo']:.2f} | Média Km: {row['media_km_consumo']:.0f} | Registros: {row['registros']}\n"
    txBox5 = slide5.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(6))
    tf5 = txBox5.text_frame
    tf5.text = text2

    pptx_io = io.BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

uploaded_file = st.file_uploader("📁 Carregue sua planilha Excel com abas: interno, externo, consumo", type=['xlsx'])
if uploaded_file:
    interno, externo, consumo = load_data(uploaded_file)

    st.sidebar.header("Filtros Globais")

    placas_unicas = sorted(set(interno['placa'].dropna().unique()) |
                          set(externo['placa'].dropna().unique()) |
                          set(consumo['placa'].dropna().unique()))
    placas_selected = st.sidebar.multiselect("Placas", placas_unicas, default=placas_unicas)

    combust_interno = interno['tipo'].dropna().unique() if 'tipo' in interno.columns else []
    combust_externo = externo['tipo_combustivel'].dropna().unique() if 'tipo_combustivel' in externo.columns else []
    combust_unificados = sorted(set(combust_interno) | set(combust_externo))
    combust_selected = st.sidebar.multiselect("Tipo Combustível", combust_unificados, default=combust_unificados)

    data_min = min(interno['data'].min(), externo['data'].min(), consumo['data'].min())
    data_max = max(interno['data'].max(), externo['data'].max(), consumo['data'].max())
    data_range = st.sidebar.date_input("Período", [data_min, data_max])

    data_start, data_end = pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])

    # Filtro nas abas interno e externo
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

    # Processar abas interno e externo para indicadores de litros e km
    interno_proc = preprocess_abastecimentos(interno_filt, 'quantidade_de_litros', 'km_atual', 'tipo')
    externo_proc = preprocess_abastecimentos(externo_filt, 'quantidade_de_litros', 'km_atual', 'tipo_combustivel')

    abastecimentos = pd.concat([interno_proc, externo_proc], ignore_index=True)

    resumo_consumo_ab = abastecimentos.groupby('placa').agg(
        total_litros_consumo=('litros', 'sum'),
        media_km_consumo=('km', 'mean'),
        registros=('data', 'count')
    ).reset_index()

    # Filtro e processamento da aba consumo para cálculo do consumo médio real
    consumo_filt = consumo[
        (consumo['placa'].isin(placas_selected)) &
        (consumo['data'] >= data_start) & (consumo['data'] <= data_end)
    ]

    consumo_filt.rename(columns={'qtd_litros': 'litros', 'km': 'km_consumo'}, inplace=True)

    consumo_filt['litros'] = consumo_filt['litros'].astype(str).str.replace(',', '.', regex=False)
    consumo_filt['km_consumo'] = consumo_filt['km_consumo'].astype(str).str.replace(',', '.', regex=False)
    consumo_filt['litros'] = pd.to_numeric(consumo_filt['litros'], errors='coerce')
    consumo_filt['km_consumo'] = pd.to_numeric(consumo_filt['km_consumo'], errors='coerce')
    consumo_filt.dropna(subset=['litros', 'km_consumo'], inplace=True)

    # Para o consumo médio: usamos km min e km max da aba consumo e soma dos litros da mesma aba (reflete consumo real)
    resumo_consumo = consumo_filt.groupby('placa').agg(
        km_min=('km_consumo', 'min'),
        km_max=('km_consumo', 'max'),
        litros_totais=('litros', 'sum')
    ).reset_index()
    resumo_consumo['km_rodados'] = resumo_consumo['km_max'] - resumo_consumo['km_min']
    resumo_consumo['consumo_medio_km_por_litro'] = resumo_consumo.apply(
        lambda r: r['km_rodados'] / r['litros_totais'] if r['litros_totais'] > 0 else None, axis=1)
    resumo_consumo = resumo_consumo.sort_values('consumo_medio_km_por_litro', ascending=False)

    # Exibir indicadores consumo médio (aba consumo)
    st.header("🚛 Consumo Médio por Veículo (Base: Aba Consumo)")
    st.dataframe(resumo_consumo.style.format({
        'km_min': '{:,.0f}',
        'km_max': '{:,.0f}',
        'litros_totais': '{:,.2f}',
        'km_rodados': '{:,.0f}',
        'consumo_medio_km_por_litro': '{:.2f}'
    }))

    fig1 = px.bar(resumo_consumo, x='placa', y='consumo_medio_km_por_litro',
                  labels={'consumo_medio_km_por_litro': 'Km por Litro', 'placa': 'Placa'},
                  title='Consumo Médio (Km por Litro) por Veículo')
    st.plotly_chart(fig1, use_container_width=True)

    # Exibir indicadores interno + externo (litros e km médios)
    st.header("⛽ Indicadores Abastecimento Interno + Externo")
    st.dataframe(resumo_consumo_ab.style.format({
        'total_litros_consumo': '{:,.2f}',
        'media_km_consumo': '{:,.0f}',
        'registros': '{:,.0f}'
    }))

    fig2 = px.bar(resumo_consumo_ab, x='placa', y='total_litros_consumo',
                  labels={'total_litros_consumo': 'Total Litros', 'placa': 'Placa'},
                  title='Total de Litros Consumidos por Veículo (Aba Interno + Externo)')
    st.plotly_chart(fig2, use_container_width=True)

    # Botão de exportação PPTX com gráficos e dados atuais
    pptx_file = criar_ppt(resumo_consumo, fig1, resumo_consumo_ab, fig2)
    st.download_button(
        label="📥 Exportar Apresentação PowerPoint",
        data=pptx_file,
        file_name="dashboard_consumo_veiculos.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

else:
    st.info("Faça upload da planilha Excel para começar.")
