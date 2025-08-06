import pandas as pd

def carregar_dados(arquivo):
    xls = pd.ExcelFile(arquivo)
    
    # Carregar abas
    externo = pd.read_excel(xls, "Abastecimento Externo")
    interno = pd.read_excel(xls, "Abastecimento Interno")
    
    # Padronizar nomes de colunas
    externo = externo.rename(columns={
        'Data': 'data',
        'Placa': 'placa',
        'KM Atual': 'km',
        'Quantidade de litros': 'litros',
        'Valor Total': 'valor'
    })

    externo['origem'] = 'Externo'

    # Abastecimentos internos só com "Saída"
    interno = interno[interno['Tipo'].str.lower() == 'saída'].copy()
    interno = interno.rename(columns={
        'Data': 'data',
        'Placa': 'placa',
        'KM Atual': 'km',
        'Quantidade de litros': 'litros',
        'Valor Total': 'valor'
    })

    interno['origem'] = 'Interno'

    return externo, interno
