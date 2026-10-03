"""Carga de las 3 fuentes del reto y conversión a COP (unidades del enunciado)."""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
AMOUNT_TO_COP = 10_000
SM_TO_COP = 100_000_000


def load_transactions(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    tx = pd.read_csv(data_dir / "Transactions.csv", encoding="utf-8-sig")
    tx = tx.rename(columns={"ID": "customer_id", "amount": "amount_raw"})
    tx["month"] = pd.to_datetime(tx["month"], format="%m/%d/%Y").dt.to_period("M")
    tx["cash_cop"] = tx["amount_raw"] * AMOUNT_TO_COP
    return tx.sort_values(["customer_id", "month"]).reset_index(drop=True)


def load_industry(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    ind = pd.read_csv(data_dir / "Industry.csv", encoding="utf-8-sig").dropna(how="all")
    ind["customer_id"] = ind["ID"].str.extract(r"(\d+)")[0].astype(int)
    return ind.rename(columns={"Industria": "industry"})[["customer_id", "industry"]]


def load_sm_spend(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    sm = pd.read_csv(data_dir / "S&M_spend.csv", encoding="utf-8-sig")
    items = [c for c in sm.columns if c != "Month"]
    for c in items:
        sm[c] = pd.to_numeric(sm[c].astype(str).str.replace("$", "", regex=False), errors="raise") * SM_TO_COP
    sm["month"] = pd.PeriodIndex(sm["Month"], freq="M")
    sm["sm_total_cop"] = sm[items].sum(axis=1)
    return sm.drop(columns="Month")
