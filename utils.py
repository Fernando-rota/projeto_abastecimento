import pandas as pd

def carregar_dados(caminho_arquivo):
    xls = pd.ExcelFile(caminho_arquivo)
    externo = pd.read_excel(xls, "Abastecimento Externo")
    interno = pd.read_excel(xls, "Abastecimento Interno")
    compras = pd.read_excel(xls, "Combustível")  # aba de entrada de diesel

    # Padronizar colunas
    externo.columns = externo.columns.str.lower().str.strip()
    interno.columns = interno.columns.str.lower().str.strip()
    compras.columns = compras.columns.str.lower().str.strip()

    return externo, interno, compras


def preparar_dados(externo, interno, compras):
    # Renomear colunas principais
    if 'data' not in externo.columns and 'data do abastecimento' in externo.columns:
        externo.rename(columns={'data do abastecimento': 'data'}, inplace=True)
    if 'data' not in interno.columns and 'data do abastecimento' in interno.columns:
        interno.rename(columns={'data do abastecimento': 'data'}, inplace=True)
    if 'emissao' in compras.columns:
        compras.rename(columns={'emissao': 'data'}, inplace=True)

    # Converter para datetime
    externo['data'] = pd.to_datetime(externo['data'], errors='coerce')
    interno['data'] = pd.to_datetime(interno['data'], errors='coerce')
    compras['data'] = pd.to_datetime(compras['data'], errors='coerce')

    # Corrigir nomes
    if 'quantidade de litros' in externo.columns:
        externo.rename(columns={'quantidade de litros': 'litros'}, inplace=True)
    if 'quantidade de litros' in interno.columns:
        interno.rename(columns={'quantidade de litros': 'litros'}, inplace=True)
    if 'quantidade' in compras.columns:
        compras.rename(columns={'quantidade': 'litros'}, inplace=True)
    if 'valor pago' not in externo.columns and 'custo total' in externo.columns:
        externo.rename(columns={'custo total': 'valor pago'}, inplace=True)

    # Corrigir tipos de combustível
    externo['combustivel'] = externo['descricao despesa'].str.upper().str.extract(r'(DIESEL COMUM|GASOLINA COMUM|ARLA)', expand=False).fillna('OUTRO')
    interno['combustivel'] = interno['descricao despesa'].str.upper().str.extract(r'(DIESEL COMUM|GASOLINA COMUM|ARLA)', expand=False).fillna('OUTRO')
    compras['combustivel'] = compras['descricao despesa'].str.upper().str.extract(r'(DIESEL COMUM|GASOLINA COMUM|ARLA)', expand=False).fillna('OUTRO')

    # Tag origem
    externo['origem'] = 'Externo'
    interno['origem'] = 'Interno'

    # Unificar placas e remover entradas '-'
    externo['placa'] = externo['placa'].astype(str).str.strip().str.upper()
    interno['placa'] = interno['placa'].astype(str).str.strip().str.upper()
    compras['placa'] = compras.get('placa', '-')
    compras['placa'] = compras['placa'].astype(str).str.strip().str.upper()

    return externo, interno, compras


def calcular_consumo(externo, interno):
    # Agrupar por placa
    consumo_ext = externo.groupby('placa')['litros'].sum().reset_index(name='litros_externo')
    consumo_int = interno[~(interno['placa'].isin(['-', 'CORREÇÃO']))].groupby('placa')['litros'].sum().reset_index(name='litros_interno')

    # Juntar dados
    df = pd.merge(consumo_ext, consumo_int, on='placa', how='outer').fillna(0)
    df['total'] = df['litros_externo'] + df['litros_interno']
    df['% externo'] = (df['litros_externo'] / df['total'] * 100).round(1)
    df['% interno'] = (df['litros_interno'] / df['total'] * 100).round(1)

    return df


def calcular_preco_medio(compras):
    # Considerar apenas entradas de diesel (placa == '-')
    diesel = compras[
        (compras['placa'] == '-') &
        (compras['combustivel'] == 'DIESEL COMUM')
    ]

    if 'valor pago' in diesel.columns:
        diesel = diesel[diesel['litros'] > 0]
        diesel['preco_litro'] = diesel['valor pago'] / diesel['litros']
        preco_medio = diesel['preco_litro'].mean()
    else:
        preco_medio = 0.0

    return round(preco_medio, 3)
