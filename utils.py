import pandas as pd

def carregar_dados(xls):
    externo = pd.read_excel(xls, "Abastecimento Externo")
    interno = pd.read_excel(xls, "Abastecimento Interno")

    # Externo
    externo = externo.rename(columns={
        "DATA": "data",
        "PLACA": "placa",
        "POSTO": "posto",
        "KM ATUAL": "km_atual",
        "CONSUMO": "litros",
        "CUSTO TOTAL": "valor_pago",
        "DESCRIÇÃO DO ABASTECIMENTO": "descricao_despesa"
    })
    externo['origem'] = 'Externo'

    # Interno (filtrar apenas saídas)
    interno = interno[interno["Tipo"].str.lower().str.strip() == "saída"].copy()
    interno = interno.rename(columns={
        "Data": "data",
        "Placa": "placa",
        "KM Atual": "km_atual",
        "Quantidade de litros": "litros",
        "Descrição Despesa": "descricao_despesa"
    })
    interno['origem'] = 'Interno'

    # Valor pago interno: será preenchido com NaN (não disponível)
    interno['valor_pago'] = None

    # Unir dados
    df = pd.concat([externo, interno], ignore_index=True)

    # Padronizar datas e tipos
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['litros'] = pd.to_numeric(df['litros'], errors='coerce')
    df['valor_pago'] = pd.to_numeric(df['valor_pago'], errors='coerce')
    df['descricao_despesa'] = df['descricao_despesa'].str.upper().str.strip()

    # Classificar combustível
  def classificar_combustivel(x):
    x = str(x).lower()
    if 'gasolina' in x:
        return 'Gasolina Comum'
    elif 'arla' in x:
        return 'Arla'
    elif 'diesel' in x or 'óleo' in x:
        return 'Diesel Comum'
    else:
        return 'Outros'


    df['combustivel'] = df['descricao_despesa'].apply(classificar_combustivel)
    df.dropna(subset=['data', 'litros'], inplace=True)
    return df


def calcular_indicadores_resumo(df):
    total_litros = df['litros'].sum()
    total_valor = df['valor_pago'].sum(min_count=1)  # ignora NaN ao somar
    valor_medio = total_valor / total_litros if total_litros > 0 else 0

    litros_interno = df[df['origem'] == 'Interno']['litros'].sum()
    pct_interno = litros_interno / total_litros if total_litros > 0 else 0

    return {
        'total_litros': total_litros,
        'total_valor': total_valor,
        'valor_medio': valor_medio,
        'pct_interno': pct_interno
    }


def preparar_dados_tendencia(df):
    df['ano_mes'] = df['data'].dt.to_period("M").astype(str)
    tendencia = df.groupby(['ano_mes', 'origem'])['litros'].sum().reset_index()
    return tendencia


def calcular_consumo_medio(df):
    consumo = df.dropna(subset=["placa", "km_atual"]).copy()
    consumo = consumo.sort_values(["placa", "data"])

    consumo['km_rodado'] = consumo.groupby('placa')['km_atual'].diff()
    consumo['litros_consumidos'] = consumo['litros']

    consumo = consumo[consumo['km_rodado'] > 0]
    consumo['km_por_litro'] = consumo['km_rodado'] / consumo['litros_consumidos']
    consumo = consumo.dropna(subset=['km_por_litro'])

    return consumo
