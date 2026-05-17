from src.silver import engine


def run(dim_banco, dim_produto, dim_localidade) -> object:
    return engine.process(
        "fato_contratos",
        fk_frames={
            "dim_banco":     dim_banco,
            "dim_produto":   dim_produto,
            "dim_localidade": dim_localidade,
        },
    )
