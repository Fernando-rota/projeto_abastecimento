import pandas as pd

def carregar_planilhas(uploaded_file):
    # Lê as abas da planilha
    xls = pd.ExcelFile(uploaded_file)
    externo = pd.read_excel(xls, "Abastecimento Externo")
    interno = pd.read_excel(xls, "Abastecimento Interno")
    combustivel = pd.read_excel(xls, "Combustível")

    return externo, interno, combustivel


def preparar_dados(externo_raw, interno_raw):
    # --- Normaliza colunas ---
    externo = externo_raw.copy()
    interno = interno_raw.copy()

    externo.columns = externo.columns.str.strip().str.lower()
    interno.columns = interno.columns.str.strip().str.lower()

    # --- Trata abastecimento externo ---
    externo = externo.rename(columns={
        "data": "data",
        "placa": "placa",
        "km atual": "km",
        "km": "km",
        "consumo": "litros",
        "quantidade de litros": "litros",
        "custo total": "valor",
        "valor pago": "valor"
    })

    externo['origem'] = 'Externo'

    colunas_externo = ['data', 'placa', 'km', 'litros', 'valor', 'origem']
    externo = externo[[col for col in colunas_externo if col in externo.columns]]

    # --- Trata abastecimento interno (apenas Saídas) ---
    interno = interno.rename(columns={
        "data": "data",
        "tipo": "tipo",
        "placa": "placa",
        "km atual": "km",
        "quantidade de litros": "litros"
    })

    interno_saida = interno[interno['tipo'].str.lower().str.strip() == 'saída'].copy()
    interno_saida['valor'] = None  # será calculado depois
    interno_saida['origem'] = 'Interno'

    colunas_interno = ['data', 'placa', 'km', 'litros', 'valor', 'origem']
    interno_saida = interno_saida[[col for col in colunas_interno if col in interno_saida.columns]]

    # Remove registros sem placa ou placa inválida
    for df in [externo, interno_saida]:
        df.dropna(subset=['placa'], inplace=True)
        df = df[df['placa'].str.strip().str.upper() != '-']

    # Junta os dois
    df = pd.concat([externo, interno_saida], ignore_index=True)

    # Conversões e limpeza
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['litros'] = pd.to_numeric(df['litros'], errors='coerce')
    df['km'] = pd.to_numeric(df['km'], errors='coerce')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')

    # Remove linhas sem litros
    df = df.dropna(subset=['litros'])

    return df


def calcular_valor_medio_interno(interno_raw):
    interno = interno_raw.copy()
    interno.columns = interno.columns.str.strip().str.lower()

    # Seleciona apenas entradas
    entradas = interno[interno['tipo'].str.lower().str.strip() == 'entrada'].copy()

    # Corrige nomes
    entradas = entradas.rename(columns={
        "data": "data",
        "quantidade de litros": "litros",
        "valor pago": "valor"
    })

    entradas['valor'] = pd.to_numeric(entradas['valor'], errors='coerce')
    entradas['litros'] = pd.to_numeric(entradas['litros'], errors='coerce')

    total_litros = entradas['litros'].sum()
    total_valor = entradas['valor'].sum()

    preco_medio = total_valor / total_litros if total_litros > 0 else 0
    return round(preco_medio, 2)


def aplicar_valor_interno(df, preco_medio):
    # Preenche valores faltantes no interno
    df['valor'] = df.apply(
        lambda row: row['valor'] if pd.notnull(row['valor']) else round(row['litros'] * preco_medio, 2),
        axis=1
    )
    return df


def gerar_indicadores(df):
    indicadores = {}
    indicadores['Total de litros'] = round(df['litros'].sum(), 2)
    indicadores['Custo total'] = round(df['valor'].sum(), 2)
    indicadores['Preço médio'] = round(df['valor'].sum() / df['litros'].sum(), 2) if df['litros'].sum() > 0 else 0
    return indicadores


def preparar_estoque_tanque(interno_raw):
    interno = interno_raw.copy()
    interno.columns = interno.columns.str.strip().str.lower()

    # Entradas no tanque
    entradas = interno[interno['tipo'].str.lower().str.strip() == 'entrada'].copy()
    entradas = entradas.rename(columns={
        "data": "data",
        "quantidade de litros": "litros",
        "valor pago": "valor"
    })

    entradas['data'] = pd.to_datetime(entradas['data'], errors='coerce')
    entradas['litros'] = pd.to_numeric(entradas['litros'], errors='coerce')
    entradas['valor'] = pd.to_numeric(entradas['valor'], errors='coerce')

    entradas = entradas.dropna(subset=['data', 'litros'])

    return entradas[['data', 'litros', 'valor']]
