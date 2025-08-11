import io
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.io as pio
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime

st.set_page_config(page_title="Dashboard Consumo e Abastecimento", layout="wide")

@st.cache_data(show_spinner=False)
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

@st.cache_data(show_spinner=False)
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
                 labels={'consumo_medio_km_por_litro': 'Km/Litro', 'placa': 'Placa'},
                 title='Consumo Médio (Km/Litro) por Veículo')
    return resumo_consumo, fig

def plot_litros_total(abastecimentos):
    resumo_ab = abastecimentos.groupby('placa').agg(
        total_litros=('litros', 'sum'),
        media_km=('km', 'mean'),
        registros=('data', 'count')
    ).reset_index()
    fig = px.bar(resumo_ab, x='placa', y='total_litros',
                 labels={'total_litros': 'Total Litros', 'placa': 'Placa'},
                 title='Total Litros Consumidos por Veículo')
    return resumo_ab, fig

def plot_autonomia_real(consumo_df, abastecimento_df):
    consumo_sum = consumo_df.groupby('placa').agg(
        km_min=('km', 'min'),
        km_max=('km', 'max'),
        litros_consumo=('litros', 'sum')
    ).reset_index()
    consumo_sum['km_rodados'] = consumo_sum['km_max'] - consumo_sum['km_min']

    abastecimento_sum = abastecimento_df.groupby('placa').agg(
        litros_abastecidos=('litros', 'sum')
    ).reset_index()

    df = pd.merge(consumo_sum, abastecimento_sum, on='placa', how='left')
    df['autonomia_real'] = df.apply(lambda r: r['km_rodados'] / r['litros_abastecidos']
                                   if r['litros_abastecidos'] and r['litros_abastecidos'] > 0 else None, axis=1)

    fig = px.bar(df.sort_values('autonomia_real', ascending=False), x='placa', y='autonomia_real',
                 labels={'autonomia_real': 'Autonomia (Km/L)', 'placa': 'Placa'},
                 title='Autonomia Real (Km/L) por Veículo')
    return df, fig

def plot_consumo_por_combustivel(abastecimentos):
    df = abastecimentos.groupby(['combustivel']).agg(total_litros=('litros', 'sum')).reset_index()
    fig = px.pie(df, values='total_litros', names='combustivel', title='Consumo Total por Tipo de Combustível')
    return df, fig

def plot_media_diaria_abastecimento(abastecimentos):
    df = abastecimentos.copy()
    df['data'] = pd.to_datetime(df['data'])
    df_diario = df.groupby(['data']).agg(total_litros=('litros', 'sum')).reset_index()
    df_diario['media_movel_7d'] = df_diario['total_litros'].rolling(window=7).mean()
    fig = px.line(df_diario, x='data', y='total_litros', title='Consumo Diário de Litros')
    fig.add_scatter(x=df_diario['data'], y=df_diario['media_movel_7d'], mode='lines', name='Média Móvel 7 dias')
    return df_diario, fig

def plot_tendencia_mensal(consumo_filt):
    df = consumo_filt.copy()
    df['mes'] = df['data'].dt.to_period('M')
    df_mensal = df.groupby('mes').agg(
        km_rodados=('km', lambda x: x.max() - x.min()),
        litros_totais=('litros', 'sum')
    ).reset_index()
    df_mensal['consumo_medio'] = df_mensal.apply(
        lambda r: r['km_rodados'] / r['litros_totais'] if r['litros_totais'] > 0 else None, axis=1)
    df_mensal['mes'] = df_mensal['mes'].dt.to_timestamp()
    fig = px.line(df_mensal, x='mes', y='consumo_medio', title='Tendência Mensal Consumo Médio (Km/L)')
    return df_mensal, fig

def save_fig_to_bytes(fig):
    img_bytes = pio.to_image(fig, format='png', width=700, height=400, scale=2)
    return io.BytesIO(img_bytes)

def gerar_pdf(resumo_consumo, resumo_abastecimento, autonomia_df, fig1_bytes, fig2_bytes, fig3_bytes):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Relatório Consumo e Abastecimento")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # Consumo médio
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 100, "Consumo Médio (Km/L) por Veículo")
    y = height - 120
    c.setFont("Helvetica", 9)
    for i, row in resumo_consumo.iterrows():
        linha = f"{row['placa']}: Km Rodados: {int(row['km_rodados'])}, Litros: {row['litros_totais']:.2f}, Consumo Médio: {row['consumo_medio_km_por_litro']:.2f}"
        c.drawString(50, y, linha)
        y -= 15
        if y < 150:
            c.showPage()
            y = height - 50

    c.showPage()
    c.drawImage(ImageReader(fig1_bytes), 50, height/2 - 100, width=width-100, height=300)

    # Abastecimento total litros
    c.showPage()
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 50, "Total Litros Consumidos por Veículo")
    y = height - 70
    c.setFont("Helvetica", 9)
    for i, row in resumo_abastecimento.iterrows():
        linha = f"{row['placa']}: Total Litros: {row['total_litros']:.2f}, Média Km: {int(row['media_km'])}, Registros: {row['registros']}"
        c.drawString(50, y, linha)
        y -= 15
        if y < 150:
            c.showPage()
            y = height - 50

    c.showPage()
    c.drawImage(ImageReader(fig2_bytes), 50, height/2 - 100, width=width-100, height=300)

    # Autonomia real
    c.showPage()
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 50, "Autonomia Real (Km/L) por Veículo")
    y = height - 70
    c.setFont("Helvetica", 9)
    for i, row in autonomia_df.iterrows():
        autonomia = f"{row['autonomia_real']:.2f}" if pd.notna(row['autonomia_real']) else "N/A"
        linha = f"{row['placa']}: Autonomia Real: {autonomia}"
        c.drawString(50, y, linha)
        y -= 15
        if y < 150:
            c.showPage()
            y = height - 50

    c.showPage()
    c.drawImage(ImageReader(fig3_bytes), 50, height/2 - 100, width=width-100, height=300)

    c.save()
    buffer.seek(0)
    return buffer

st.title("🚛 Dashboard de Consumo e Abastecimento")

uploaded_file = st.file_uploader("📁 Faça upload do arquivo Excel com abas: interno, externo, consumo", type=["xlsx"])
if not uploaded_file:
    st.info("Por favor, faça upload do arquivo Excel para começar.")
    st.stop()

interno, externo, consumo = load_data(uploaded_file)

# Sidebar com filtros
st.sidebar.header("Filtros Globais")

placas_unicas = sorted(set(interno['placa'].dropna().unique()) |
                      set(externo['placa'].dropna().unique()) |
                      set(consumo['placa'].dropna().unique()))
placas_selected = st.sidebar.multiselect("Placas", placas_unicas, default=placas_unicas)

combust_interno = interno['tipo'].dropna().unique() if 'tipo' in interno.columns else []
combust_externo = externo['tipo_combustivel'].dropna().unique() if 'tipo_combustivel' in externo.columns else []
combust_unificados = sorted(set(combust_interno) | set(combust_externo))
combust_selected = st.sidebar.multiselect("Tipos de Combustível", combust_unificados, default=combust_unificados)

data_min = min(interno['data'].min(), externo['data'].min(), consumo['data'].min())
data_max = max(interno['data'].max(), externo['data'].max(), consumo['data'].max())

data_range = st.sidebar.date_input("Período", [data_min, data_max])
if isinstance(data_range, (tuple, list)):
    data_start, data_end = pd.to_datetime(data_range[0]), pd.to_datetime(data_range[1])
else:
    data_start = data_end = pd.to_datetime(data_range)

# Filtrar dados
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

consumo_filt = consumo[
    (consumo['placa'].isin(placas_selected)) &
    (consumo['data'] >= data_start) & (consumo['data'] <= data_end)
]

if 'qtd_litros' in consumo_filt.columns:
    consumo_filt.rename(columns={'qtd_litros': 'litros'}, inplace=True)

consumo_filt['litros'] = consumo_filt['litros'].astype(str).str.replace(',', '.', regex=False)
consumo_filt['km'] = consumo_filt['km'].astype(str).str.replace(',', '.', regex=False)
consumo_filt['litros'] = pd.to_numeric(consumo_filt['litros'], errors='coerce')
consumo_filt['km'] = pd.to_numeric(consumo_filt['km'], errors='coerce')
consumo_filt.dropna(subset=['litros', 'km'], inplace=True)

# Abas com indicadores e gráficos
tabs = st.tabs([
    "Resumo Consumo",
    "Abastecimento",
    "Autonomia Real",
    "Gráficos Gerais",
    "Indicadores Extras",
    "Relatório PDF"
])

with tabs[0]:
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

with tabs[1]:
    resumo_ab, fig2 = plot_litros_total(abastecimentos)
    st.header("⛽ Total Litros Consumidos")
    st.dataframe(resumo_ab.style.format({
        'total_litros': '{:,.2f}',
        'media_km': '{:,.0f}',
        'registros': '{:,.0f}'
    }))
    st.plotly_chart(fig2, use_container_width=True)

with tabs[2]:
    autonomia_df, fig3 = plot_autonomia_real(consumo_filt, abastecimentos)
    st.header("🔋 Autonomia Real (Km/L)")
    st.dataframe(autonomia_df.style.format({
        'km_min': '{:,.0f}',
        'km_max': '{:,.0f}',
        'litros_consumo': '{:,.2f}',
        'litros_abastecidos': '{:,.2f}',
        'km_rodados': '{:,.0f}',
        'autonomia_real': '{:.2f}'
    }))
    st.plotly_chart(fig3, use_container_width=True)

with tabs[3]:
    st.header("📊 Gráficos Gerais")
    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)
    st.plotly_chart(fig3, use_container_width=True)

with tabs[4]:
    st.header("📈 Indicadores Extras")

    df_combustivel, fig_combustivel = plot_consumo_por_combustivel(abastecimentos)
    st.subheader("Consumo Total por Tipo de Combustível")
    st.dataframe(df_combustivel.style.format({'total_litros': '{:,.2f}'}))
    st.plotly_chart(fig_combustivel, use_container_width=True)

    df_diario, fig_diario = plot_media_diaria_abastecimento(abastecimentos)
    st.subheader("Consumo Diário e Média Móvel 7 dias")
    st.dataframe(df_diario.style.format({'total_litros': '{:,.2f}', 'media_movel_7d': '{:,.2f}'}))
    st.plotly_chart(fig_diario, use_container_width=True)

    df_tendencia, fig_tendencia = plot_tendencia_mensal(consumo_filt)
    st.subheader("Tendência Mensal Consumo Médio (Km/L)")
    st.dataframe(df_tendencia.style.format({
        'km_rodados': '{:,.0f}',
        'litros_totais': '{:,.2f}',
        'consumo_medio': '{:.2f}'
    }))
    st.plotly_chart(fig_tendencia, use_container_width=True)

with tabs[5]:
    st.header("📄 Gerar Relatório PDF")
    if st.button("Gerar PDF com Indicadores e Gráficos"):
        fig1_bytes = save_fig_to_bytes(fig1)
        fig2_bytes = save_fig_to_bytes(fig2)
        fig3_bytes = save_fig_to_bytes(fig3)
        pdf_buffer = gerar_pdf(resumo_consumo, resumo_ab, autonomia_df, fig1_bytes, fig2_bytes, fig3_bytes)
        st.download_button(
            label="📥 Baixar Relatório PDF",
            data=pdf_buffer,
            file_name="relatorio_consumo_abastecimento.pdf",
            mime="application/pdf"
        )
