from src.silver import engine, fato_contratos


def run():
    df_banco      = engine.process("dim_banco")
    df_produto    = engine.process("dim_produto")
    df_localidade = engine.process("dim_localidade")
    fato_contratos.run(df_banco, df_produto, df_localidade)
