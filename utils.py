import pandas as pd

def carregar_dados(arquivo):
    xls = pd.ExcelFile(arquivo)
    externo = pd.read_excel(xls, "Abastecimento Externo")
    interno = pd.read_excel(xls, "Abastecimento Interno")
    return externo, interno

def preparar_dados(externo, interno):
    # Padronização das colunas
    externo = externo.rename(columns={
        'DATA': 'data',
        'PLACA': 'placa',
        'KM ATUAL': 'km',
        'CONSUMO': 'litros',
        'VALOR PAGO': 'valor',
        'DESCRIÇÃO DO ABASTECIMENTO': 'descricao',
        'DESCRIÇÃO DESPESA': 'combustivel',
    })

    interno = interno.rename(columns={
        'Data': 'data',
        'Placa': 'placa',
        'KM Atual': 'km',
        'Quantidade de litros': 'litros',
        'Tipo': 'tipo',
        'Descrição Despesa': 'combustivel',
    })

    # Remover linhas de entrada do reservatório no interno
    interno['tipo'] = interno['tipo'].astype(str).str.lower().str.strip()
    interno_saida = interno[interno['tipo'] == 'saída']

    # Acrescentar campos que o externo tem
    interno_saida['valor'] = None
    interno_saida['origem'] = 'Interno'
    externo['origem'] = 'Externo'

    # Normalizar campos
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')
    interno_saida['data'] = pd.to_datetime(interno_saida['data'], errors='coerce')

    externo = externo[['data', 'placa', 'km', 'litros', 'valor', 'origem', 'combustivel']]
    interno_saida = interno_saida[['data', 'placa', 'km', 'litros', 'valor', 'origem', 'combustivel']]

    df_base = pd.concat([externo, interno_saida], ignore_index=True)
    df_base = df_base.dropna(subset=['data', 'placa', 'litros'])

    df_base['combustivel'] = df_base['combustivel'].astype(str).str.upper().str.strip()
    df_base['mes'] = df_base['data'].dt.to_period("M").dt.to_timestamp()
    df_base['valor'] = pd.to_numeric(df_base['valor'], errors='coerce')
    df_base['litros'] = pd.to_numeric(df_base['litros'], errors='coerce')
    df_base['km'] = pd.to_numeric(df_base['km'], errors='coerce')
    df_base = df_base[df_base['placa'].str.strip().str.upper() != '-']

    return df_base

def calcular_consumo(df):
    consumo = df.copy()
    consumo = consumo.sort_values(by=['placa', 'data'])

    consumo['km_anterior'] = consumo.groupby('placa')['km'].shift(1)
    consumo['km_rodado'] = consumo['km'] - consumo['km_anterior']
    consumo['km_litro'] = consumo['km_rodado'] / consumo['litros']
    consumo = consumo[consumo['km_rodado'] > 0]

    return consumo

def calcular_preco_medio_interno(interno):
    interno['tipo'] = interno['tipo'].astype(str).str.lower().str.strip()
    entradas = interno[interno['tipo'] == 'entrada']
    entradas['valor unitario'] = entradas['Custo Total'] / entradas['Quantidade de litros']
    return entradas['valor unitario'].mean()
