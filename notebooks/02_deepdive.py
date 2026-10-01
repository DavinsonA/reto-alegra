"""Segunda exploración: mezcla de planes, ARPA por cohorte, bajadas pequeñas de 2024, impacto de los pagos atrasados,
S&M vs altas, industria. Solo lectura."""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)

tx = pd.read_csv(DATA / "Transactions.csv", encoding="utf-8-sig")
tx["month"] = pd.to_datetime(tx["month"], format="%m/%d/%Y").dt.to_period("M")
tx = tx.sort_values(["ID", "month"]).reset_index(drop=True)
ind = pd.read_csv(DATA / "Industry.csv", encoding="utf-8-sig").dropna()
ind["ID"] = ind["ID"].str.extract(r"(\d+)")[0].astype(int)
tx = tx.merge(ind, on="ID", how="left")

# ---------- A. first paid amount (entry price point) by cohort year ----------
first = tx[tx["amount"] > 0].groupby("ID").head(1)
first = first.assign(cohort=first["month"], cy=first["month"].dt.year)
first["amt_bucket"] = pd.cut(first["amount"], [0, 1, 2.5, 4.5, 6.5, 9, 13, 1e9],
                             labels=["<=1", "1-2.5", "2.5-4.5", "4.5-6.5", "6.5-9", "9-13", ">13"])
print("=== entry amount bucket by cohort year (excl. 2022-01 left-censored)")
f2 = first[first["cohort"] > pd.Period("2022-01", "M")]
print(pd.crosstab(f2["cy"], f2["amt_bucket"], normalize="index").round(3))
print("median first amount by cohort quarter:\n",
      f2.groupby(f2["cohort"].dt.asfreq("Q"))["amount"].agg(["count", "median", "mean"]).round(2).to_string())

# ---------- B. small decreases (-2..10%) in 2024: what happens around them ----------
tx["prev"] = tx.groupby("ID")["amount"].shift()
tx["prev2"] = tx.groupby("ID")["amount"].shift(2)
tx["next"] = tx.groupby("ID")["amount"].shift(-1)
dec = tx[(tx["amount"] > 0) & (tx["prev"] > 0) & (tx["amount"] / tx["prev"]).between(0.9, 0.98)
         & (tx["month"] >= pd.Period("2024-06", "M"))].copy()
dec["r"] = (dec["amount"] / dec["prev"]).round(3)
dec["r_prev"] = (dec["prev"] / dec["prev2"]).round(3)
dec["r_next"] = (dec["next"] / dec["amount"]).round(3)
print("\n=== 2024-06+ small decreases: n=", len(dec))
print("ratio:", dict(dec["r"].value_counts().head(8)))
print("previous step ratio:", dict(dec["r_prev"].value_counts().head(8)))
print("next step ratio:", dict(dec["r_next"].value_counts().head(8)))
for cid in dec["ID"].unique()[:5]:
    g = tx[tx["ID"] == cid]
    print(f"ID {cid}:", " ".join(f"{m}:{v:g}" for m, v in zip(g["month"].astype(str), g["amount"].round(3))))

# ---------- C. price increases: are they at customer anniversary? ----------
inc = tx[(tx["amount"] > 0) & (tx["prev"] > 0) & (tx["amount"] / tx["prev"]).between(1.02, 1.12)].copy()
fm = first.set_index("ID")["cohort"]
inc["months_since_first"] = (inc["month"] - inc["ID"].map(fm)).apply(lambda d: d.n)
print("\n=== +2..12% increases: months since first payment mod 12")
print((inc["months_since_first"] % 12).value_counts().sort_index().to_dict())
print("increase ratio by year:", inc.groupby(inc["month"].dt.year)["amount"].count().to_dict())
print(inc.assign(r=(inc["amount"] / inc["prev"]).round(3)).groupby(inc["month"].dt.year)["r"].median().to_dict())

# ---------- D. payment-timing impact on a naive cash-based MRR model ----------
# naive: any month with 0 after positive = churn; positive after 0 = reactivation; amount>prev = expansion
s = tx.copy()
s["prev"] = s.groupby("ID")["amount"].shift(fill_value=0)
s["seen"] = s.groupby("ID")["amount"].transform(lambda a: (a > 0).cumsum().shift(fill_value=0) > 0)
s["mv"] = np.select(
    [(s["amount"] > 0) & (s["prev"] == 0) & ~s["seen"],
     (s["amount"] > 0) & (s["prev"] == 0) & s["seen"],
     (s["amount"] == 0) & (s["prev"] > 0),
     (s["amount"] > s["prev"]) & (s["prev"] > 0),
     (s["amount"] < s["prev"]) & (s["amount"] > 0)],
    ["new", "reactivation", "churn", "expansion", "contraction"], default="flat")
s["delta"] = s["amount"] - s["prev"]
naive = s[s["month"] > pd.Period("2022-01", "M")].pivot_table(index="month", columns="mv", values="delta",
                                                              aggfunc="sum", fill_value=0)
print("\n=== naive MRR bridge (cash-based) — 2024 rows")
print(naive.loc[naive.index >= pd.Period("2024-01", "M")].round(1).to_string())
tot = naive.sum()
print("totals over period:", tot.round(1).to_dict())
# how much 'churn' is followed by return within 1-2 months?
s["next1"] = s.groupby("ID")["amount"].shift(-1)
s["next2"] = s.groupby("ID")["amount"].shift(-2)
ch = s[s["mv"] == "churn"]
back1 = (ch["next1"] > 0).mean()
back2 = ((ch["next1"] > 0) | (ch["next2"] > 0)).mean()
print(f"naive churn events: {len(ch)}; back next month: {back1:.1%}; back within 2 months: {back2:.1%}")

# ---------- E. S&M vs new customers (lags) ----------
sm = pd.read_csv(DATA / "S&M_spend.csv", encoding="utf-8-sig")
for c in sm.columns[1:]:
    sm[c] = pd.to_numeric(sm[c].astype(str).str.replace("$", "", regex=False), errors="coerce")
sm["month"] = pd.PeriodIndex(sm["Month"], freq="M")
sm["sm_total"] = sm.iloc[:, 1:8].sum(axis=1)
newc = f2.groupby("cohort").size().rename("new_customers")
new_mrr = f2.groupby("cohort")["amount"].sum().rename("new_first_amount")
d = sm.set_index("month")[["sm_total", "PaidMedia"]].join(newc).join(new_mrr).fillna(0)
d = d[d.index >= pd.Period("2022-04", "M")]   # skip left-censored start
print("\n=== S&M vs new customers (from 2022-04)")
for k in range(0, 4):
    print(f"lag {k}: corr(sm_t-k, new_t) = {d['sm_total'].shift(k).corr(d['new_customers']):.2f} | "
          f"diff-corr = {d['sm_total'].diff().shift(k).corr(d['new_customers'].diff()):.2f}")
q = d.groupby(d.index.asfreq("Q")).sum()
q["CAC_blended"] = q["sm_total"] / q["new_customers"]
print(q.round(3).to_string())

# ---------- F. industry ----------
last = tx[tx["month"] == tx["month"].max()]
print("\n=== Industry: customers paying in last month, MRR share, ARPA")
gi = last[last["amount"] > 0].groupby("Industria")["amount"].agg(["count", "sum", "mean"])
gi["mrr_share"] = gi["sum"] / gi["sum"].sum()
print(gi.round(3).sort_values("sum", ascending=False).to_string())
