"""Perfilado inicial de los 3 CSV del reto (Finora). Solo lectura: no transforma datos."""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

# ---------- Transactions ----------
tx = pd.read_csv(DATA / "Transactions.csv", encoding="utf-8-sig")
print("=== Transactions raw")
print(tx.dtypes, "\nrows:", len(tx))
print(tx.head())
tx["month"] = pd.to_datetime(tx["month"], format="%m/%d/%Y")
print("month range:", tx["month"].min().date(), "->", tx["month"].max().date())
print("month is month-end:", (tx["month"] == tx["month"] + pd.offsets.MonthEnd(0)).all())
print("distinct IDs:", tx["ID"].nunique(), " min/max ID:", tx["ID"].min(), tx["ID"].max())
print("distinct months:", tx["month"].nunique())
dups = tx.duplicated(["ID", "month"], keep=False)
print("duplicated (ID,month) rows:", dups.sum())
print("nulls:\n", tx.isna().sum())
print("amount describe:\n", tx["amount"].describe())
print("zeros:", (tx["amount"] == 0).sum(), " negatives:", (tx["amount"] < 0).sum())
rows_per_id = tx.groupby("ID").size()
print("rows per ID describe:\n", rows_per_id.describe())

# does each ID start at its first month and run to the end (dense)?
g = tx.groupby("ID")["month"].agg(["min", "max", "count"])
g["span"] = (g["max"].dt.year - g["min"].dt.year) * 12 + (g["max"].dt.month - g["min"].dt.month) + 1
print("IDs with holes in the row spine (span != count):", (g["span"] != g["count"]).sum())
print("first-month distribution (top):\n", g["min"].dt.to_period("M").value_counts().sort_index().head(40))
print("last row month distribution:\n", g["max"].dt.to_period("M").value_counts().sort_index())

# first row amount > 0 ?
first = tx.sort_values(["ID", "month"]).groupby("ID").head(1)
print("first row amount == 0:", (first["amount"] == 0).sum())

# monthly totals
m = tx.groupby("month").agg(total=("amount", "sum"), paying=("amount", lambda s: (s > 0).sum()),
                            rows=("amount", "size"))
print("=== monthly totals\n", m.to_string())

# amount granularity / decimals
dec = tx.loc[tx["amount"] > 0, "amount"]
print("share of positive amounts that are 'round' to 1 decimal:",
      np.isclose(dec * 10, np.round(dec * 10)).mean().round(3))
print("top positive amounts:\n", dec.round(4).value_counts().head(20))

# per-customer changes among consecutive positive months
s = tx.sort_values(["ID", "month"]).copy()
s["prev"] = s.groupby("ID")["amount"].shift()
both = s[(s["amount"] > 0) & (s["prev"] > 0)]
ratio = both["amount"] / both["prev"]
print("consecutive positive months:", len(both),
      " unchanged:", np.isclose(ratio, 1).mean().round(3))
print("ratio quantiles (changed only):\n", ratio[~np.isclose(ratio, 1)].quantile([.01, .05, .25, .5, .75, .95, .99]))
print("ratio value counts (changed, rounded):\n", ratio[~np.isclose(ratio, 1)].round(3).value_counts().head(25))

# gaps: zero months between positive months
def gap_lengths(a):
    out, run, seen_pos = [], 0, False
    for v in a:
        if v > 0:
            if seen_pos and run > 0:
                out.append(run)
            run, seen_pos = 0, True
        else:
            if seen_pos:
                run += 1
    return out
gaps = s.groupby("ID")["amount"].apply(lambda a: gap_lengths(a.values))
all_gaps = [x for lst in gaps for x in lst]
print("internal zero-gaps (0s between positives):", len(all_gaps),
      " customers with >=1 gap:", (gaps.str.len() > 0).sum())
print("gap length distribution:\n", pd.Series(all_gaps).value_counts().sort_index())

# trailing zeros (churned to end)
def trailing_zeros(a):
    n = 0
    for v in a[::-1]:
        if v == 0:
            n += 1
        else:
            break
    return n
tz = s.groupby("ID")["amount"].apply(lambda a: trailing_zeros(a.values))
print("customers ending in zeros:", (tz > 0).sum(), " all-zero customers:", (s.groupby('ID')['amount'].max() == 0).sum())

# spikes: amount >= 6x customer median of positive months
med = s[s["amount"] > 0].groupby("ID")["amount"].median().rename("med")
s = s.join(med, on="ID")
spk = s[(s["amount"] > 0) & (s["amount"] >= 6 * s["med"])]
print("spike rows (>=6x customer median):", len(spk), " customers:", spk["ID"].nunique())
print(spk.head(10))

# ---------- Industry ----------
ind = pd.read_csv(DATA / "Industry.csv", encoding="utf-8-sig")
print("=== Industry raw:", ind.shape)
print(ind.head())
print("nulls:\n", ind.isna().sum())
print("dup IDs:", ind["ID"].duplicated().sum())
print(ind["Industria"].value_counts(dropna=False))
ind["ID_num"] = pd.to_numeric(ind["ID"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
tx_ids, ind_ids = set(tx["ID"]), set(ind["ID_num"].dropna().astype(int))
print("tx IDs w/o industry:", len(tx_ids - ind_ids), " industry IDs w/o tx:", len(ind_ids - tx_ids))

# ---------- S&M ----------
sm = pd.read_csv(DATA / "S&M_spend.csv", encoding="utf-8-sig")
print("=== S&M raw:", sm.shape)
for c in sm.columns[1:]:
    sm[c] = pd.to_numeric(sm[c].astype(str).str.replace("$", "", regex=False), errors="coerce")
sm["total"] = sm.iloc[:, 1:].sum(axis=1)
print(sm.to_string())
print("negatives per column:\n", (sm.iloc[:, 1:] < 0).sum())
