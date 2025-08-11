import io
import tempfile
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from fpdf import FPDF

st.set_page_config(page_title="BI Consumo + Export PDF", layout="wide")
st.title("📊 BI Completo: Consumo e Abastecimento + Exportação PDF")

# Simples função para plotar gráfico de barras com matplotlib e retornar path da imagem
def plot_bar_matplotlib(df, x_col, y_col, title, ylabel):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(df[x_col], df[y_col], color='skyblue')
    ax.set_title(title)
    ax.set_xlabel(x_col.capitalize())
    ax.set_ylabel(ylabel)
    plt.xticks(rotation=45)
    plt.tight_layout()

    tmpfile = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmpfile.name)
    plt.close(fig)
    return tmpfile.name

def criar_pdf(resumo_consumo_df, fig1_path, resumo_consumo_ab_df, fig2_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Dashboard Consumo e Abastecimento - Resumo", ln=True, align='C')

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Consumo Médio por Veículo (Base: Aba Consumo)", ln=True)

    pdf.set_font("Arial", size=10)
    for _, row in resumo_consumo_df.iterrows():
        linha = f"Placa: {row['placa']} | Km rodados: {row['km_rodados']:.0f} | Litros: {row['litros_totais']:.2f} | Consumo Médio: {row['consumo_medio_km_por_litro']:.2f}"
        pdf.cell(0, 8, linha, ln=True)

    pdf.ln(5)
    pdf.cell(0, 10, "Gráfico Consumo Médio", ln=True)
    pdf.image(fig1_path, x=20, w=170)

    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Indicadores Abastecimento Interno + Externo", ln=True)

    pdf.set_font("Arial", size=10)
    for _, row in resumo_consumo_ab_df.iterrows():
        linha = f"Placa: {row['placa']} | Total Litros: {row['total_litros_consumo']:.2f} | Média Km: {row['media_km_consumo']:.0f} | Registros: {row['registros']}"
        pdf.cell(0, 8, linha, ln=True)

    pdf.ln(5)
    pdf.cell(0, 10, "Gráfico Litros Consumidos", ln=True)
    pdf.image(fig2_path, x=20, w=170)

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output


# === Código principal Streamlit ===

uploaded_file = st.file_uploader("📁 Carregue sua planilha Excel com abas: interno, externo, consumo", type=['xlsx'])
if uploaded_file:
    interno = pd.read_excel(uploaded_file, sheet_name='interno')
    externo = pd.read_excel(uploaded_file, sheet_name='externo')
    consumo = pd.read_excel(uploaded_file, sheet_name='consumo')

    # Padronizar colunas
    for df in [interno, externo, consumo]:
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    # Converter datas
    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')
    consumo['data'] = pd.to_datetime(consumo['data'], errors='coerce')

    interno.dropna(subset=['data'], inplace=True)
    externo.dropna(subset=['data'], inplace=True)
    consumo.dropna(subset=['data'], inplace=True)

    # Filtros simples para demo
    placas = sorted(set(interno['placa'].dropna()) | set(externo['placa'].dropna()) | set(consumo['placa'].dropna()))
    placas_selected = st.multiselect("Placas", placas, default=placas)

    interno_filt = interno[interno['placa'].isin(placas_selected)]
    externo_filt = externo[externo['placa'].isin(placas_selected)]
    consumo_filt = consumo[consumo['placa'].isin(placas_selected)]

    # Processar interno
    interno_filt['quantidade_de_litros'] = pd.to_numeric(interno_filt['quantidade_de_litros'].astype(str).str.replace(',', '.'), errors='coerce')
    interno_filt['km_atual'] = pd.to_numeric(interno_filt['km_atual'].astype(str).str.replace(',', '.'), errors='coerce')

    externo_filt['quantidade_de_litros'] = pd.to_numeric(externo_filt['quantidade_de_litros'].astype(str).str.replace(',', '.'), errors='coerce')
    externo_filt['km_atual'] = pd.to_numeric(externo_filt['km_atual'].astype(str).str.replace(',', '.'), errors='coerce')

    abastecimento = pd.concat([interno_filt[['placa', 'quantidade_de_litros', 'km_atual']], externo_filt[['placa', 'quantidade_de_litros', 'km_atual']]], ignore_index=True)

    resumo_abastecimento = abastecimento.groupby('placa').agg(
        total_litros_consumo=('quantidade_de_litros', 'sum'),
        media_km_consumo=('km_atual', 'mean'),
        registros=('placa', 'count')
    ).reset_index()

    # Processar consumo
    consumo_filt['qtd_litros'] = pd.to_numeric(consumo_filt['qtd_litros'].astype(str).str.replace(',', '.'), errors='coerce')
    consumo_filt['km'] = pd.to_numeric(consumo_filt['km'].astype(str).str.replace(',', '.'), errors='coerce')

    resumo_consumo = consumo_filt.groupby('placa').agg(
        km_min=('km', 'min'),
        km_max=('km', 'max'),
        litros_totais=('qtd_litros', 'sum')
    ).reset_index()

    resumo_consumo['km_rodados'] = resumo_consumo['km_max'] - resumo_consumo['km_min']
    resumo_consumo['consumo_medio_km_por_litro'] = resumo_consumo.apply(lambda r: r['km_rodados'] / r['litros_totais'] if r['litros_totais'] > 0 else None, axis=1)

    # Mostrar tabelas
    st.header("🚛 Consumo Médio por Veículo")
    st.dataframe(resumo_consumo)

    st.header("⛽ Abastecimento Interno + Externo")
    st.dataframe(resumo_abastecimento)

    # Gerar gráficos matplotlib
    fig1_path = plot_bar_matplotlib(resumo_consumo.dropna(), 'placa', 'consumo_medio_km_por_litro', 'Consumo Médio (Km/L) por Veículo', 'Km por Litro')
    fig2_path = plot_bar_matplotlib(resumo_abastecimento, 'placa', 'total_litros_consumo', 'Total Litros Consumidos por Veículo', 'Litros')

    st.pyplot(plt.imread(fig1_path))
    st.pyplot(plt.imread(fig2_path))

    # Botão exportar PDF
    pdf_file = criar_pdf(resumo_consumo.dropna(), fig1_path, resumo_abastecimento, fig2_path)
    st.download_button("📥 Exportar Relatório em PDF", data=pdf_file, file_name="relatorio_consumo_abastecimento.pdf", mime="application/pdf")

else:
    st.info("Faça upload da planilha Excel para começar.")
