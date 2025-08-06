if arquivo:
    externo_raw, interno_raw = carregar_dados(arquivo)
    preco_medio_interno = calcular_preco_medio_interno(interno_raw)

    df_base = preparar_dados(externo_raw, interno_raw)
    df_base = aplicar_valor_interno(df_base, preco_medio_interno)
    df_base = calcular_consumo(df_base)

    # Filtrar por período
    st.sidebar.header("📅 Período")
    min_data = df_base['data'].min()
    max_data = df_base['data'].max()
    data_inicio, data_fim = st.sidebar.date_input("Selecione o intervalo", [min_data, max_data])
    df_base = df_base[(df_base['data'] >= pd.to_datetime(data_inicio)) & (df_base['data'] <= pd.to_datetime(data_fim))]

    # Demais filtros e abas seguem como antes...
