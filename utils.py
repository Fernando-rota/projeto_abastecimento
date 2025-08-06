import pandas as pd

def carregar_dados(arquivo):
    xls = pd.ExcelFile(arquivo)
    externo = pd.read_excel(xls, "Abastecimento Externo")
    interno = pd.read_excel(xls, "Abastecimento Interno")
    return externo, interno

def preparar_dados(externo_raw, interno_raw):
    externo = externo_raw.copy()
    interno = interno_raw.copy()
    
    externo.columns = externo.columns.str.strip().str.lower()
    interno.columns = interno.columns.str.strip().str.lower()
    
    externo['combustivel'] = externo['descrição despesa'].str.upper()
    interno['combustivel'] = interno['descrição despesa'].str.upper()
    
    mapa_combustivel = {
        'DIESEL COMUM': 'Diesel Comum',
        'GASOLINA COMUM': 'Gasolina Comum',
        'ARLA': 'Arla',
    }
    
    externo['combustivel'] = externo['combustivel'].map(mapa_combustivel).fillna('Outro')
    interno['combustivel'] = interno['combustivel'].map(mapa_combustivel).fillna('Outro')
    
    externo = externo.rename(columns={
        "data": "data",
        "placa": "placa",
        "km atual": "km",
        "quantidade de litros": "litros",
        "valor total": "valor"
    })
    externo['origem'] = 'Externo'
    externo = externo[['data', 'placa', 'km', 'litros', 'valor', 'origem', 'combustivel']]
    
    interno = interno.rename(columns={
        "data": "data",
        "tipo": "tipo",
        "placa": "placa",
        "km atual": "km",
        "quantidade de litros": "litros",
        "valor total": "valor"
    })
    interno_saida = interno[interno['tipo'].str.lower().str.strip() == 'saída'].copy()
    interno_saida['origem'] = 'Interno'
    interno_saida = interno_saida[['data', 'placa', 'km', 'litros', 'valor', 'origem', 'combustivel']]
    
    externo = externo[~externo['placa'].str.upper().isin(['-', '', 'CORREÇÃO'])]
    interno_saida = interno_saida[~interno_saida['placa'].str.upper().isin(['-', '', 'CORREÇÃO'])]
    
    df = pd.concat([externo, interno_saida], ignore_index=True)
    
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['litros'] = pd.to_numeric(df['litros'], errors='coerce')
    df['km'] = pd.to_numeric(df['km'], errors='coerce')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    
    df = df.dropna(subset=['data', 'placa', 'litros', 'km'])
    
    return df

def calcular_preco_medio_interno(interno_raw):
    interno = interno_raw.copy()
    interno.columns = interno.columns.str.strip().str.lower()
    entradas = interno[interno['tipo'].str.lower().str.strip() == 'entrada'].copy()
    
    entradas['valor total'] = pd.to_numeric(entradas.get('valor total', 0), errors='coerce')
    entradas['quantidade de litros'] = pd.to_numeric(entradas.get('quantidade de litros', 0), errors='coerce')
    
    total_valor = entradas['valor total'].sum()
    total_litros = entradas['quantidade de litros'].sum()
    preco_medio = total_valor / total_litros if total_litros > 0 else 0
    return preco_medio

def aplicar_valor_interno(df, preco_medio_interno):
    df.loc[(df['origem'] == 'Interno') & (df['valor'].isna()), 'valor'] = \
        df['litros'] * preco_medio_interno
    return df

def calcular_consumo(df):
    df = df.sort_values(['placa', 'data']).copy()
    df['km_anterior'] = df.groupby('placa')['km'].shift(1)
    df['km_rodado'] = df['km'] - df['km_anterior']

    df = df[(df['km_rodado'] > 0) & (df['litros'] > 0)]
    df['consumo_km_l'] = df['km_rodado'] / df['litros']
    return df

def calcular_indicadores_resumo(df):
    total_litros = df['litros'].sum()
    total_valor = df['valor'].sum()
    valor_medio = total_valor / total_litros if total_litros > 0 else 0
    pct_interno = (df['origem'] == 'Interno').mean()
    custo_por_km = total_valor / df['km_rodado'].sum() if df['km_rodado'].sum() > 0 else 0
    return {
        'total_litros': total_litros,
        'total_valor': total_valor,
        'valor_medio': valor_medio,
        'pct_interno': pct_interno,
        'custo_por_km': custo_por_km
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
