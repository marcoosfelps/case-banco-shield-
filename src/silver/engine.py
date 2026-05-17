import json
import re
import duckdb
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "pipeline.duckdb"
RULES_PATH = Path(__file__).parent.parent.parent / "config" / "rules.json"

_rules_cache = None

# Mapeamento regex -> nome canÃ´nico para normalizaÃ§Ã£o de grafias invÃ¡lidas
BANK_REGEX_MAP = [
    (re.compile(r"hydra", re.IGNORECASE), "Hidra"),
    (re.compile(r"hidra", re.IGNORECASE), "Hidra"),
    (re.compile(r"banco\s*s\.?h\.?i\.?e\.?l\.?d\.?", re.IGNORECASE), "Banco Shield"),
    (re.compile(r"banco\s*shield", re.IGNORECASE), "Banco Shield"),
]

def _normalize_bank(value: str) -> str:
    for pattern, canonical in BANK_REGEX_MAP:
        if pattern.fullmatch(value.strip()):
            return canonical
    return value


def _load_rules() -> dict:
    global _rules_cache
    if _rules_cache is None:
        with open(RULES_PATH, encoding="utf-8") as f:
            _rules_cache = json.load(f)
    return _rules_cache


def process(table: str, fk_frames: dict = None) -> pd.DataFrame:
    rules = _load_rules()[table]
    con = duckdb.connect(str(DB_PATH))
    df = con.execute(f"SELECT * FROM bronze_{table}").df()
    con.close()

    # 0. NormalizaÃ§Ã£o por regex (antes de qualquer validaÃ§Ã£o)
    for col, ref_table in rules.get("foreign_keys", {}).items():
        if ref_table == "dim_banco" and col in df.columns:
            original = df[col].copy()
            df[col] = df[col].astype(str).apply(_normalize_bank)
            fixed = (df[col] != original) & original.notna()
            if fixed.any():
                df[f"_fixed_{col}"] = fixed
                print(f"[silver] {table}.{col}: {fixed.sum()} grafias corrigidas por regex")

    # 1. NormalizaÃ§Ã£o textual
    for col in rules.get("normalize_text", []):
        if col in df.columns:
            original = df[col].copy()
            df[col] = df[col].astype(str).str.strip().str.title()
            fixed = (df[col] != original) & original.notna()
            if fixed.any():
                df[f"_fixed_{col}"] = fixed

    # 2. Cast de tipos
    for col, dtype in rules.get("cast", {}).items():
        if col not in df.columns:
            continue
        if dtype in ("int64", "float64", "Int64"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if dtype in ("int64", "Int64"):
                df[col] = df[col].astype("Int64")
        else:
            df[col] = df[col].astype(dtype)

    # 3. Campos obrigatÃ³rios
    for col in rules.get("required_fields", []):
        if col in df.columns:
            df[f"_err_{col}_null"] = df[col].isna()

    # 4. Unicidade
    for col in rules.get("unique_fields", []):
        if col in df.columns:
            df[f"_err_{col}_dup"] = df.duplicated(col, keep=False)

    # 5. Chaves estrangeiras
    for col, ref_table in rules.get("foreign_keys", {}).items():
        if fk_frames and ref_table in fk_frames:
            ref_df = fk_frames[ref_table]
            # FK de texto: compara contra bank_name; FK numÃ©rica: compara contra col
            ref_col = "bank_name" if ref_table == "dim_banco" else col
            valid_ids = set(ref_df[ref_col].dropna())
            df[f"_err_{col}_fk"] = ~df[col].isin(valid_ids)

    # 6. Regras de domÃ­nio
    for col, rule in rules.get("domain_rules", {}).items():
        if col not in df.columns:
            continue
        if rule["type"] == "enum":
            df[f"_err_{col}_domain"] = ~df[col].isin(rule["values"])
        elif rule["type"] == "range":
            df[f"_err_{col}_domain"] = ~df[col].between(rule["min"], rule["max"])

    # 7. Campos nÃ£o-negativos
    for col in rules.get("non_negative_fields", []):
        if col in df.columns:
            df[f"_err_{col}_negative"] = df[col] < 0

    # 8. Regras cruzadas
    for rule in rules.get("cross_field_rules", []):
        df[rule["flag"]] = df.eval(rule["condition"])

    # 9. Flag consolidada
    err_cols = [c for c in df.columns if c.startswith("_err_")]
    df["_is_valid"] = ~df[err_cols].any(axis=1) if err_cols else True

    con2 = duckdb.connect(str(DB_PATH))
    con2.execute(f"CREATE OR REPLACE TABLE silver_{table} AS SELECT * FROM df")
    con2.close()

    total = len(df)
    invalid = (~df["_is_valid"]).sum()
    print(f"[silver] {table}: {total} linhas | {invalid} invalidas ({invalid/total:.1%})")

    return df


