import pandas as pd

def carregar_dados(arquivo):
    xls = pd.ExcelFile(arquivo)
    externo = pd.read_excel(xls, "Abastecimento Externo")
    interno = pd.read_excel(xls, "Abastecimento Interno")
    return externo, interno

def preparar_dados(externo, interno):
    externo = externo.rename(columns={
        "DATA": "data", "PLACA": "placa", "KM ATUAL": "km", "CONSUMO": "litros", "CUSTO TOTAL": "valor"
    })
    interno = interno.rename(columns={
        "Data": "data", "Placa": "placa", "KM Atual": "km", "Quantidade de litros": "litros"
    })
    externo['origem'] = 'Externo'
    interno['origem'] = 'Interno'
    externo = externo[['data', 'placa', 'km', 'litros', 'valor', 'origem']]
    interno = interno[['data', 'placa', 'km', 'litros', 'origem']]
    return pd.concat([externo, interno], ignore_index=True)

def calcular_consumo(df):
    df = df.sort_values(by=['placa', 'data'])
    df['km_anterior'] = df.groupby('placa')['km'].shift(1)
    df['km_rodado'] = df['km'] - df['km_anterior']
    df['km_litro'] = df['km_rodado'] / df['litros']
    return df

def calcular_indicadores_resumo(df):
    total_litros = df['litros'].sum()
    total_valor = df['valor'].sum() if 'valor' in df.columns else 0
    valor_medio = total_valor / total_litros if total_litros > 0 else 0
    pct_interno = len(df[df['origem'] == 'Interno']) / len(df) if len(df) > 0 else 0
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
    return consumo.sort_values(by='km_litro', ascending=False)

def preparar_estoque_tanque(df):
    df_tanque = df[df['Placa'] == '-'].copy()
    df_tanque['data'] = pd.to_datetime(df_tanque['Data'], errors='coerce')
    df_tanque['litros'] = pd.to_numeric(df_tanque['Quantidade de litros'], errors='coerce')
    df_tanque['medidor'] = pd.to_numeric(df_tanque['Medidor do tanque atual'], errors='coerce')
    df_tanque['soma_medidor'] = pd.to_numeric(df_tanque['Soma do medidor + litros'], errors='coerce')
    return df_tanque[['data', 'litros', 'medidor', 'soma_medidor']]
