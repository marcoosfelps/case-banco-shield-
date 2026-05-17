import duckdb
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
DB_PATH = BASE_DIR / "data" / "pipeline.duckdb"


def _load_raw(filename: str) -> pd.DataFrame:
    path = RAW_DIR / filename
    if not path.exists():
        fallback = Path(filename)
        if not fallback.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path} nem {fallback}")
        print(f"[bronze] AVISO: {filename} não encontrado em {RAW_DIR}, usando fallback: {fallback}")
        path = fallback
    df = pd.read_csv(path, dtype=str)
    df["_source_file"] = filename
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    return df


def run():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB_PATH)) as con:
        for filename, table in [
            ("fato_contratos.csv", "fato_contratos"),
            ("dim_produto.csv", "dim_produto"),
            ("dim_localidade.csv", "dim_localidade"),
            ("dim_banco.csv", "dim_banco"),
        ]:
            df = _load_raw(filename)
            con.execute(f"CREATE OR REPLACE TABLE bronze_{table} AS SELECT * FROM df")
            print(f"[bronze] {table}: {len(df)} linhas -> bronze_{table}")


if __name__ == "__main__":
    run()
