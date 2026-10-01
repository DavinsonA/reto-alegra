"""Exploración de patrones en Transactions: descuentos temporales, subidas de precio, pagos de recuperación, altas/bajas."""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)

tx = pd.read_csv(DATA / "Transactions.csv", encoding="utf-8-sig")
tx["month"] = pd.to_datetime(tx["month"], format="%m/%d/%Y").dt.to_period("M")
tx = tx.sort_values(["ID", "month"]).reset_index(drop=True)
tx["prev"] = tx.groupby("ID")["amount"].shift()
tx["next"] = tx.groupby("ID")["amount"].shift(-1)

# ---------- 1. Change events between consecutive positive months, by calendar month ----------
pos = tx[(tx["amount"] > 0) & (tx["prev"] > 0)].copy()
pos["ratio"] = pos["amount"] / pos["prev"]
pos["kind"] = np.select(
    [np.isclose(pos["ratio"], 1), np.isclose(pos["ratio"], 0.5), np.isclose(pos["ratio"], 2.0),
     pos["ratio"].between(1.02, 1.12), pos["ratio"].between(0.9, 0.98)],
    ["same", "x0.5", "x2", "+2..12%", "-2..10%"], default="other")
print("=== change kinds by calendar month")
print(pd.crosstab(pos["month"], pos["kind"]).to_string())

# ---------- 2. Price-increase hypothesis: what ratios happen in which months ----------
inc = pos[pos["kind"] == "+2..12%"]
print("\n=== +2..12% ratios: top months and ratio by month")
print(inc.groupby("month")["ratio"].agg(["count", "median", "min", "max"]).sort_values("count", ascending=False).head(15))

# ---------- 3. Temporary 50% discount detection: x0.5 followed later by x2 back to same level ----------
episodes = []
for cid, g in tx.groupby("ID"):
    a = g["amount"].values
    months = g["month"].values
    i = 1
    while i < len(a):
        if a[i - 1] > 0 and a[i] > 0 and np.isclose(a[i] / a[i - 1], 0.5):
            base = a[i - 1]
            j = i
            while j < len(a) and a[j] > 0 and np.isclose(a[j], a[i]):
                j += 1
            end_kind = ("restored" if j < len(a) and a[j] > 0 and np.isclose(a[j], base)
                        else "zero" if j < len(a) and a[j] == 0
                        else "other_change" if j < len(a)
                        else "open_at_end")
            episodes.append((cid, str(months[i]), j - i, end_kind, base))
            i = j
        else:
            i += 1
ep = pd.DataFrame(episodes, columns=["ID", "start", "months_discounted", "end", "base_amount"])
print("\n=== 50% discount-like episodes:", len(ep), " customers:", ep["ID"].nunique())
print(ep["end"].value_counts())
print("duration distribution (months):\n", ep["months_discounted"].value_counts().sort_index())
print("start month distribution:\n", ep["start"].value_counts().sort_index().to_string())

# ---------- 4. Does the first payment start already discounted? (new at half price, later x2) ----------
first_pos = tx[tx["amount"] > 0].groupby("ID").head(1).set_index("ID")["month"]
starts_half = []
for cid, g in tx.groupby("ID"):
    a = g["amount"].values
    k = np.argmax(a > 0)
    # first block of identical amounts, then a x2 jump
    j = k
    while j < len(a) and a[j] > 0 and np.isclose(a[j], a[k]):
        j += 1
    if j < len(a) and a[j] > 0 and np.isclose(a[j] / a[k], 2.0):
        starts_half.append((cid, str(g["month"].values[k]), j - k))
sh = pd.DataFrame(starts_half, columns=["ID", "first_month", "months_at_half"])
print("\n=== customers whose first block later doubles exactly (possible intro discount):", len(sh))
print(sh["months_at_half"].value_counts().sort_index())
print(sh["first_month"].value_counts().sort_index().to_string())

# ---------- 5. Catch-up payments after zero-gaps ----------
rows = []
for cid, g in tx.groupby("ID"):
    a = g["amount"].values
    last_pos = None
    run = 0
    for i, v in enumerate(a):
        if v > 0:
            if last_pos is not None and run > 0:
                rows.append((cid, str(g["month"].values[i]), run, v / last_pos))
            last_pos, run = v, 0
        elif last_pos is not None:
            run += 1
cu = pd.DataFrame(rows, columns=["ID", "month_back", "gap_len", "ratio_vs_last"])
cu["ratio_round"] = cu["ratio_vs_last"].round(2)
print("\n=== payment after a gap: ratio vs last paid amount, by gap length")
print(cu.groupby("gap_len")["ratio_vs_last"].describe()[["count", "50%", "mean"]].head(10))
cu["catchup_exact"] = np.isclose(cu["ratio_vs_last"], cu["gap_len"] + 1)
print("share where payment == (gap+1) x last amount (catch-up):",
      cu["catchup_exact"].mean().round(3), "n=", cu["catchup_exact"].sum())
print(cu[cu["gap_len"] == 1]["ratio_round"].value_counts().head(10))

# ---------- 6. Sample of spikes for manual review ----------
med = tx[tx["amount"] > 0].groupby("ID")["amount"].median().rename("med")
t2 = tx.join(med, on="ID")
spk = t2[(t2["amount"] > 0) & (t2["amount"] >= 6 * t2["med"])]
for cid in spk["ID"].unique()[:6]:
    g = tx[tx["ID"] == cid]
    print(f"\nID {cid}:", " ".join(f"{m}:{v:g}" for m, v in zip(g["month"].astype(str), g["amount"].round(2))))

# ---------- 7. Base x 1.05 hypothesis ----------
p = tx[tx["amount"] > 0].copy()
p["year"] = p["month"].dt.year
for y, gy in p.groupby("year"):
    vc = gy["amount"].round(4).value_counts().head(8)
    print(f"\n{y} top amounts:", dict(vc))

# ---------- 8. New, churn, reactivation counts (naive: any zero month = inactive) ----------
tx["active"] = tx["amount"] > 0
tx["prev_active"] = tx.groupby("ID")["active"].shift(fill_value=False)
tx["ever_before"] = tx.groupby("ID")["active"].cumsum().shift(fill_value=0) > 0
tx.loc[tx.groupby("ID").head(1).index, "ever_before"] = False
naive = tx.assign(
    new=(tx["active"] & ~tx["prev_active"] & ~tx["ever_before"]),
    react=(tx["active"] & ~tx["prev_active"] & tx["ever_before"]),
    churn=(~tx["active"] & tx["prev_active"]),
).groupby("month")[["new", "react", "churn"]].sum()
print("\n=== naive monthly movements (1 zero month = churn)\n", naive.to_string())
