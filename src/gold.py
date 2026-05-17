import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "pipeline.duckdb"


def run():
    con = duckdb.connect(str(DB_PATH))

    con.execute("""
        CREATE OR REPLACE VIEW fato AS
            SELECT * FROM silver_fato_contratos WHERE _is_valid = true;
        CREATE OR REPLACE VIEW dim_produto AS
            SELECT * FROM silver_dim_produto;
        CREATE OR REPLACE VIEW dim_localidade AS
            SELECT * FROM silver_dim_localidade;
    """)

    queries = {
        "carteira_banco_mes": """
            SELECT ano_mes, bank,
                COUNT(*) AS contratos,
                SUM(financed_amount) AS total_financiado,
                SUM(outstanding_balance) AS saldo_total
            FROM fato
            GROUP BY ano_mes, bank
            ORDER BY ano_mes, bank
        """,
        "produtos_mais_vendidos": """
            SELECT f.bank, p.product_name, p.category,
                COUNT(*) AS contratos,
                SUM(f.financed_amount) AS total_financiado,
                SUM(f.outstanding_balance) AS saldo_total,
                SUM(f.delinquent_amount_30p) AS saldo_inadimplente,
                ROUND(SUM(f.delinquent_amount_30p) / NULLIF(SUM(f.outstanding_balance), 0), 4) AS indice_inadimplencia,
                ROUND(AVG(f.risk_score), 4) AS risk_score_medio
            FROM fato f
            JOIN dim_produto p ON f.product_id = p.product_id
            GROUP BY f.bank, p.product_name, p.category
            ORDER BY contratos DESC, total_financiado DESC
        """,
        "inadimplencia_localidade": """
            SELECT l.location_name, l.macro_region, l.risk_factor_region, f.bank,
                COUNT(*) AS contratos,
                SUM(f.outstanding_balance) AS saldo_total,
                SUM(f.delinquent_amount_30p) AS saldo_inadimplente,
                ROUND(SUM(f.delinquent_amount_30p) / NULLIF(SUM(f.outstanding_balance), 0), 4) AS indice_inadimplencia
            FROM fato f
            JOIN dim_localidade l ON f.location_id = l.location_id
            GROUP BY l.location_name, l.macro_region, l.risk_factor_region, f.bank
            ORDER BY indice_inadimplencia DESC
        """,
        "share_mercado": """
            SELECT p.category,
                SUM(CASE WHEN f.bank = 'Banco Shield' THEN 1 ELSE 0 END) AS contratos_shield,
                SUM(CASE WHEN f.bank = 'Hidra' THEN 1 ELSE 0 END) AS contratos_hidra,
                COUNT(*) AS contratos_total,
                ROUND(SUM(CASE WHEN f.bank = 'Banco Shield' THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS share_shield,
                ROUND(SUM(CASE WHEN f.bank = 'Hidra' THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS share_hidra,
                SUM(CASE WHEN f.bank = 'Banco Shield' THEN f.financed_amount ELSE 0 END) AS financiado_shield,
                SUM(CASE WHEN f.bank = 'Hidra' THEN f.financed_amount ELSE 0 END) AS financiado_hidra,
                CASE WHEN SUM(f.financed_amount) = 0 THEN NULL
                     ELSE ROUND(SUM(CASE WHEN f.bank = 'Banco Shield' THEN f.financed_amount ELSE 0 END) /
                          SUM(f.financed_amount), 4) END AS share_valor_shield
            FROM fato f
            JOIN dim_produto p ON f.product_id = p.product_id
            GROUP BY p.category
            ORDER BY contratos_total DESC
        """,
        "ataque_vulneravel": """
            WITH base AS (
                SELECT
                    l.location_name, p.product_name, p.category,
                    COUNT(*) AS contratos_total,
                    SUM(CASE WHEN f.bank = 'Hidra' THEN 1 ELSE 0 END) AS contratos_hidra,
                    SUM(CASE WHEN f.bank = 'Banco Shield' THEN 1 ELSE 0 END) AS contratos_shield,
                    ROUND(SUM(CASE WHEN f.bank = 'Hidra' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS share_hidra,
                    ROUND(AVG(CASE WHEN f.bank = 'Hidra' THEN f.risk_score END), 4) AS risk_hidra,
                    ROUND(SUM(CASE WHEN f.bank = 'Hidra' THEN f.delinquent_amount_30p ELSE 0 END) /
                          NULLIF(SUM(CASE WHEN f.bank = 'Hidra' THEN f.outstanding_balance ELSE 0 END), 0), 4) AS inad_hidra,
                    SUM(f.outstanding_balance) AS saldo_total
                FROM fato f
                JOIN dim_produto p ON f.product_id = p.product_id
                JOIN dim_localidade l ON f.location_id = l.location_id
                GROUP BY l.location_name, p.product_name, p.category
                HAVING contratos_total >= 5 AND contratos_hidra > 0
            )
            SELECT *,
                ROUND(
                    (COALESCE(risk_hidra, 0) * 0.5) +
                    (COALESCE(inad_hidra, 0) * 10 * 0.3) +
                    (share_hidra * 0.2)
                , 4) AS score_vulnerabilidade
            FROM base
            ORDER BY score_vulnerabilidade DESC
            LIMIT 5
        """,
        "ataque_recuperar": """
            WITH base AS (
                SELECT
                    l.location_name, p.product_name, p.category,
                    COUNT(*) AS contratos_total,
                    SUM(CASE WHEN f.bank = 'Hidra' THEN 1 ELSE 0 END) AS contratos_hidra,
                    SUM(CASE WHEN f.bank = 'Banco Shield' THEN 1 ELSE 0 END) AS contratos_shield,
                    ROUND(SUM(CASE WHEN f.bank = 'Hidra' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS share_hidra,
                    ROUND(SUM(CASE WHEN f.bank = 'Banco Shield' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS share_shield,
                    SUM(f.outstanding_balance) AS saldo_total
                FROM fato f
                JOIN dim_produto p ON f.product_id = p.product_id
                JOIN dim_localidade l ON f.location_id = l.location_id
                GROUP BY l.location_name, p.product_name, p.category
                HAVING contratos_total >= 5 AND contratos_hidra > 0 AND contratos_shield > 0
            )
            SELECT *,
                ROUND(
                    (share_hidra * 0.6) +
                    ((1 - share_shield) * 0.4)
                , 4) AS score_recuperacao
            FROM base
            ORDER BY score_recuperacao DESC
            LIMIT 5
        """,
        "atencao_balance": """
            SELECT contract_id, bank, ano_mes, product_id, location_id,
                financed_amount, outstanding_balance,
                ROUND(outstanding_balance - financed_amount, 2) AS diferenca,
                dpd
            FROM fato
            WHERE outstanding_balance > financed_amount AND financed_amount > 0
            ORDER BY diferenca DESC
        """,
        "qualidade_dados": """
            SELECT bank, COUNT(*) AS total,
                SUM(CASE WHEN _err_contract_id_dup THEN 1 ELSE 0 END) AS err_id_duplicado,
                SUM(CASE WHEN _err_bank_domain THEN 1 ELSE 0 END) AS err_bank_invalido,
                SUM(CASE WHEN _err_ano_mes_domain THEN 1 ELSE 0 END) AS err_periodo_invalido,
                SUM(CASE WHEN _err_product_id_fk THEN 1 ELSE 0 END) AS err_produto_fk,
                SUM(CASE WHEN _err_location_id_fk THEN 1 ELSE 0 END) AS err_localidade_fk,
                SUM(CASE WHEN _err_financed_amount_negative OR _err_outstanding_balance_negative THEN 1 ELSE 0 END) AS err_valor_negativo,
                SUM(CASE WHEN _err_delinquent_30p THEN 1 ELSE 0 END) AS err_delinquent_30p,
                SUM(CASE WHEN _err_risk_score_domain THEN 1 ELSE 0 END) AS err_risk_score,
                ROUND(SUM(CASE WHEN NOT _is_valid THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS pct_invalido
            FROM silver_fato_contratos
            GROUP BY bank
            ORDER BY total DESC
        """,
    }

    csv_dir = Path("data/gold")
    csv_dir.mkdir(parents=True, exist_ok=True)

    for name, sql in queries.items():
        df = con.execute(sql).df()
        con.execute(f"CREATE OR REPLACE TABLE gold_{name} AS SELECT * FROM df")
        df.to_csv(csv_dir / f"{name}.csv", index=False)
        print(f"[gold] {name}: {len(df)} linhas -> gold_{name} | {name}.csv")

    con.close()


if __name__ == "__main__":
    run()
