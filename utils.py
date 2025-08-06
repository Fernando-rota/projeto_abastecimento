def preparar_dados(externo, interno):
    externo = externo.rename(columns={
        'data': 'data',
        'placa': 'placa',
        'km': 'km',
        'litros': 'litros',
        'valor': 'valor',
        'origem': 'origem'
    })

    interno = interno.rename(columns={
        'data': 'data',
        'placa': 'placa',
        'km': 'km',
        'litros': 'litros',
        'valor': 'valor',
        'origem': 'origem'
    })

    df = pd.concat([externo, interno], ignore_index=True)

    # Conversões e limpeza
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['litros'] = pd.to_numeric(df['litros'], errors='coerce')
    df['km'] = pd.to_numeric(df['km'], errors='coerce')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    df = df.dropna(subset=['data', 'placa'])

    # Remove placas inválidas
    df = df[~df['placa'].str.upper().isin(['-', '', 'CORREÇÃO'])]

    return df
