import pandas as pd

def carregar_dados(xls):
    """Carrega as duas abas principais da planilha"""
    externo = pd.read_excel(xls, sheet_name='Abastecimento Externo')
    interno = pd.read_excel(xls, sheet_name='Abastecimento Interno')
    return externo, interno

def preparar_dados(externo_raw, interno_raw):
    """Limpa, filtra e padroniza os dados de abastecimento"""

    # 🔷 Abastecimento Externo
    externo = externo_raw.copy()
    externo = externo.rename(columns={
        'Data': 'data',
        'Placa': 'placa',
        'Quantidade de litros': 'litros',
        'Valor Unitario': 'valor_unitario',
        'Valor Total': 'valor_total',
        'KM Atual': 'km_atual'
    })
    externo['origem'] = 'Externo'
    externo = externo[['data', 'placa', 'litros', 'valor_unitario', 'valor_total', 'km_atual', 'origem']]
    externo = externo.dropna(subset=['placa', 'litros'])

    # 🔶 Abastecimento Interno (somente "Saída")
    interno = interno_raw.copy()
    interno = interno[interno['Tipo'].str.lower() == 'saída'].copy()
    interno = interno.rename(columns={
        'Data': 'data',
        'Placa': 'placa',
        'Quantidade de litros': 'litros',
        'Valor Unitario': 'valor_unitario',
        'Valor Total': 'valor_total',
        'KM Atual': 'km_atual'
    })
    interno['origem'] = 'Interno'
    interno = interno[['data', 'placa', 'litros', 'valor_unitario', 'valor_total', 'km_atual', 'origem']]
    interno = interno.dropna(subset=['placa', 'litros'])

    # 🚫 Remover placas inválidas
    placas_invalidas = ['-', 'correção']
    externo = externo[~externo['placa'].str.lower().isin(placas_invalidas)]
    interno = interno[~interno['placa'].str.lower().isin(placas_invalidas)]

    # 🔄 Unificar
    df = pd.concat([externo, interno], ignore_index=True)
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['ano_mes'] = df['data'].dt.to_period('M')
    df = df.dropna(subset=['data', 'litros', 'valor_unitario'])
    df = df.sort_values(by=['placa', 'data'])

    return df

def calcular_consumo(df):
    """Calcula km rodado e consumo médio por veículo"""
    df = df.copy()
    df['km_anterior'] = df.groupby('placa')['km_atual'].shift(1)
    df['km_rodado'] = df['km_atual'] - df['km_anterior']
    df['km_litro'] = df['km_rodado'] / df['litros']
    return df

def calcular_indicadores_resumo(df):
    """Indicadores agregados para o painel principal"""
    total_litros = df['litros'].sum()
    total_valor = df['valor_total'].sum()
    valor_medio = df['valor_unitario'].mean()
    total_abastecimentos = df.shape[0]
    interno_pct = (df['origem'] == 'Interno').mean()

    return {
        'total_litros': total_litros,
        'total_valor': total_valor,
        'valor_medio': valor_medio,
        'total_abastecimentos': total_abastecimentos,
        'pct_interno': interno_pct
    }

def calcular_ranking_eficiencia(df):
    """Ranking de consumo médio por placa"""
    df_valid = df.dropna(subset=['km_litro', 'km_rodado'])
    ranking = (
        df_valid.groupby('placa')
        .agg({
            'km_rodado': 'sum',
            'litros': 'sum'
        })
        .assign(km_litro=lambda x: x['km_rodado'] / x['litros'])
        .sort_values(by='km_litro', ascending=False)
        .reset_index()
    )
    return ranking

def preparar_estoque_tanque(interno_raw):
    """Dados de entrada de diesel no tanque (Tipo == Entrada)"""
    entrada = interno_raw.copy()
    entrada = entrada[entrada['Tipo'].str.lower() == 'entrada']
    entrada = entrada.rename(columns={
        'Data': 'data',
        'Quantidade de litros': 'litros',
        'Medidor do tanque atual': 'medidor',
        'Soma do medidor + litros': 'soma_medidor'
    })
    entrada['data'] = pd.to_datetime(entrada['data'], errors='coerce')
    entrada = entrada.dropna(subset=['data', 'litros'])
    entrada = entrada.sort_values(by='data')
    return entrada
