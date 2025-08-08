import pandas as pd

def carregar_dados(arquivo):
    """
    Carrega as abas 'Abastecimento Externo' e 'Abastecimento Interno' do Excel.
    """
    xls = pd.ExcelFile(arquivo)
    externo = pd.read_excel(xls, "Abastecimento Externo")
    interno = pd.read_excel(xls, "Abastecimento Interno")
    return externo, interno

def preparar_dados(externo_raw, interno_raw):
    # Normaliza nomes das colunas para minúsculas e sem espaços extras
    externo = externo_raw.copy()
    interno = interno_raw.copy()
    externo.columns = externo.columns.str.strip().str.lower()
    interno.columns = interno.columns.str.strip().str.lower()

    # Renomeia as colunas principais para o padrão do app
    externo = externo.rename(columns={
        "data": "data",
        "placa": "placa",
        "km atual": "km",
        "quantidade de litros": "litros",
        "valor total": "valor"
    })

    externo['origem'] = 'Externo'
    colunas_externo = ['data', 'placa', 'km', 'litros', 'valor', 'origem']
    externo = externo[[col for col in colunas_externo if col in externo.columns]]

    interno = interno.rename(columns={
        "data": "data",
        "tipo": "tipo",
        "placa": "placa",
        "km atual": "km",
        "quantidade de litros": "litros"
    })

    # Filtra somente as linhas de tipo "saída" no interno
    interno_saida = interno[interno['tipo'].str.lower().str.strip() == 'saída'].copy()
    interno_saida['valor'] = None  # ainda não temos valor no interno
    interno_saida['origem'] = 'Interno'
    colunas_interno = ['data', 'placa', 'km', 'litros', 'valor', 'origem']
    interno_saida = interno_saida[[col for col in colunas_interno if col in interno_saida.columns]]

    # Remove placas inválidas
    externo = externo[~externo['placa'].str.upper().isin(['-', '', 'CORREÇÃO'])]
    interno_saida = interno_saida[~interno_saida['placa'].str.upper().isin(['-', '', 'CORREÇÃO'])]

    # Concatena os dataframes
    df = pd.concat([externo, interno_saida], ignore_index=True)

    # Conversão dos tipos de dados
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['litros'] = pd.to_numeric(df['litros'], errors='coerce')
    df['km'] = pd.to_numeric(df['km'], errors='coerce')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')

    # Remove linhas com dados essenciais ausentes
    df = df.dropna(subset=['data', 'placa', 'litros', 'km'])

    return df

def calcular_consumo(df):
    """
    Calcula km rodado e consumo km/l por abastecimento e por veículo.
    """
    df = df.sort_values(['placa', 'data']).copy()
    df['km_anterior'] = df.groupby('placa')['km'].shift(1)
    df['km_rodado'] = df['km'] - df['km_anterior']

    # Remove dados inválidos (km rodado negativo ou zero e litros <= 0)
    df = df[(df['km_rodado'] > 0) & (df['litros'] > 0)]

    df['consumo_km_l'] = df['km_rodado'] / df['litros']
    return df

def calcular_indicadores_resumo(df):
    total_litros = df['litros'].sum()
    total_valor = df['valor'].sum()
    valor_medio = total_valor / total_litros if total_litros > 0 else 0
    pct_interno = (df['origem'] == 'Interno').mean()
    return {
        'total_litros': total_litros,
        'total_valor': total_valor,
        'valor_medio': valor_medio,
        'pct_interno': pct_interno
    }

def calcular_ranking_eficiencia(df):
    consumo = df.groupby('placa').agg({
        'km_rodado': 'sum',
        'litros': 'sum'
    }).reset_index()
    consumo['km_litro'] = consumo['km_rodado'] / consumo['litros']
    consumo = consumo.sort_values(by='km_litro', ascending=False)
    return consumo

def preparar_estoque_tanque(interno_raw):
    interno = interno_raw.copy()
    interno.columns = interno.columns.str.strip().str.lower()
    # Filtra entradas no tanque (tipo == "entrada")
    entradas = interno[interno['tipo'].str.lower().str.strip() == 'entrada'].copy()

    entradas = entradas.rename(columns={
        "data": "data",
        "quantidade de litros": "litros",
        "medidor do tanque atual": "medidor",
        "soma do medidor + litros": "soma_medidor"
    })

    entradas['data'] = pd.to_datetime(entradas['data'], errors='coerce')
    entradas['litros'] = pd.to_numeric(entradas['litros'], errors='coerce')
    entradas['medidor'] = pd.to_numeric(entradas['medidor'], errors='coerce')
    entradas['soma_medidor'] = pd.to_numeric(entradas['soma_medidor'], errors='coerce')

    entradas = entradas.dropna(subset=['data'])
    return entradas[['data', 'litros', 'medidor', 'soma_medidor']]
