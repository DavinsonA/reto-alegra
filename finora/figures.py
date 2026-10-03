"""Cifras clave: la ÚNICA fuente de los números que citan README, HALLAZGOS y NOTA_CORTA."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

WINDOW_START = pd.Period("2022-04", "M")
MM = 1e6
ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "docs" / "plantillas"
DOCS = {"README.md": "README.md", "HALLAZGOS.md": "HALLAZGOS.md", "NOTA_CORTA.md": "NOTA_CORTA.md"}


def es(x: float, d: int = 1) -> str:
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def mm(x: float, d: int = 1, sign: bool = False) -> str:
    return f"{'+' if sign and x > 0 else ''}{es(x / MM, d)}"


def pct(x: float, d: int = 0) -> str:
    return es(x * 100, d)


def _internal_gaps(cm: pd.DataFrame) -> tuple[int, int]:
    """Huecos internos (meses en 0 entre dos pagos) y clientes con al menos uno."""
    n, cust = 0, 0
    for _, g in cm.groupby("customer_id"):
        paid = (g["cash_cop"].to_numpy() > 0).astype(int)
        idx = np.flatnonzero(paid)
        if len(idx) < 2:
            continue
        inner = paid[idx[0]: idx[-1] + 1]
        runs = np.diff(np.r_[0, (inner == 0).astype(int), 0])
        k = int((runs == 1).sum())
        n += k
        cust += k > 0
    return n, cust


def key_figures(cm: pd.DataFrame, tables: dict[str, pd.DataFrame], sm: pd.DataFrame, n_tests: int) -> dict[str, str]:
    from finora.mrr import bridge

    f: dict[str, str] = {}
    br_c, br_a = bridge(cm, "corrected"), bridge(cm, "actual")
    w = lambda br: br.loc[br.index >= WINDOW_START]
    tc, ta = w(br_c).sum(), w(br_a).sum()
    m0, m1 = br_c.loc[pd.Period("2022-03", "M"), "mrr_close"], br_c["mrr_close"].iloc[-1]
    f.update(mrr_ini=mm(m0), mrr_fin=mm(m1), cambio_neto=mm(m1 - m0, sign=True), crec_mrr=pct(m1 / m0 - 1),
             mrr_fin_actual=mm(br_a["mrr_close"].iloc[-1]), mes_corte="oct-2024")
    for k in ("new", "expansion", "contraction", "churn", "reactivation"):
        f[f"cor_{k}"] = mm(tc[k], sign=True)
        f[f"act_{k}"] = mm(ta[k], sign=True)
        f[f"x_{k}"] = es(ta[k] / tc[k], 1)
    f["cor_price"] = mm(tc["price_uplift"], sign=True)
    cust = sum(tc[k] for k in ("new", "expansion", "reactivation", "contraction", "churn"))
    f.update(cliente=mm(cust, sign=True), precio_pct=pct(tc["price_uplift"] / (m1 - m0)))
    up = cm[cm["mv"] == "price_uplift"]
    pend = up[up["uplift_conf"] == "pending"]
    f.update(precio_pend=mm(pend["delta"].sum()), precio_pend_n=es(len(pend), 0),
             precio_pend_pct=pct((pend["delta"] / (pend["mrr_cop"] - pend["delta"])).median(), 1))

    wc = cm[cm["month"] >= WINDOW_START]
    for kind in ("arrears", "lump", "spike", "prepaid", "retro", "prepaid_pending"):
        sel = wc[wc["extra_kind"] == kind]
        f[f"caja_{kind}"] = mm(sel["extra_cop"].sum())
        f[f"caja_{kind}_n"] = es(len(sel), 0)
    f["caja_prepaid_clientes"] = es(wc.loc[wc["extra_kind"] == "prepaid", "customer_id"].nunique(), 0)
    f["caja_no_mrr"] = mm(wc["extra_cop"].sum())

    s = tables["rule_sensitivity"]
    cor = s[s["escenario"] != "Modelo actual (caja)"]
    act = s[s["escenario"] == "Modelo actual (caja)"].iloc[0]
    f.update(sens_churn_min=mm(cor["churn_cop"].max()), sens_churn_max=mm(cor["churn_cop"].min()),
             sens_xchurn_min=es(act["churn_cop"] / cor["churn_cop"].min(), 1),
             sens_xchurn_max=es(act["churn_cop"] / cor["churn_cop"].max(), 1),
             sens_react_min=mm(cor["reactivation_cop"].min()), sens_react_max=mm(cor["reactivation_cop"].max()),
             sens_nrr_min=pct(cor["nrr12_2023"].min()), sens_nrr_max=pct(cor["nrr12_2023"].max()),
             sens_n=es(len(cor) - 1, 0))
    sp = s[s["escenario"] == "Sin prepagos"].iloc[0]
    f.update(churn_sin_prepagos=mm(sp["churn_cop"]))
    sc = s[s["escenario"] == "Sin puestas al día"].iloc[0]
    f.update(sin_catchup_contr=mm(sc["contraction_cop"]), sin_catchup_exp=mm(sc["expansion_cop"], sign=True))

    rc = tables["retention_cohorts"]
    for model, tag in (("Corregido (N=2)", "cor"), ("Modelo actual (caja)", "act")):
        for y in ("2022", "2023"):
            r = rc[(rc["model"] == model) & rc["cohort"].str.startswith(y) & (rc["age"] == 12) & (rc["cohort"] >= "2022Q2")]
            f[f"nrr_{tag}_{y}"] = pct(r["mrr_sum"].sum() / r["start_sum"].sum())
            f[f"grr_{tag}_{y}"] = pct(r["gross_sum"].sum() / r["start_sum"].sum())
            f[f"logo_{tag}_{y}"] = pct(r["active"].sum() / r["n"].sum())

    hc = tables["half_cut_monthly"]
    hc = hc[hc["month"] >= str(WINDOW_START)]
    half = wc[wc["half_cut"]]
    f.update(half_n=es(int(hc["events"].sum()), 0), half_clientes=es(half["customer_id"].nunique(), 0),
             half_contr=mm(half["delta"].sum()), half_techo=mm(hc["foregone_cop"].sum()))

    gap = wc[wc["status"] == "gap"]
    last = cm[cm["month"] == cm["month"].max()]
    open_ = last.loc[last["status"] == "delinquent_open", "mrr_cop"].sum()
    f.update(mora_impaga=mm(gap.loc[~gap["gap_paid"], "mrr_cop"].sum()), mora_impaga_n=es(int((~gap["gap_paid"]).sum()), 0),
             mora_pagada=mm(gap.loc[gap["gap_paid"], "mrr_cop"].sum()), mora_abierta=mm(open_),
             mora_abierta_pct=pct(open_ / m1, 1), mora_abierta_clientes=es(int((last["status"] == "delinquent_open").sum()), 0))

    nc = tables["new_customers_monthly"]
    nc = nc[nc["month"] >= str(WINDOW_START)].assign(year=lambda d: d["month"].str[:4])
    g = nc.groupby("year").agg(n=("new_customers", "sum"), mrr=("new_mrr_cop", "sum"), m3=("mrr_m3_sum_cop", "sum"),
                               w=("with_m3", "sum"), months=("month", "nunique"))
    for y in ("2022", "2023", "2024"):
        f[f"nuevos_mes_{y}"] = es(g.loc[y, "n"] / g.loc[y, "months"], 1)
        f[f"mrr_nuevo_mes_{y}"] = mm(g.loc[y, "mrr"] / g.loc[y, "months"])
        f[f"ticket_{y}"] = es(g.loc[y, "mrr"] / g.loc[y, "n"], 0)
        f[f"m3_{y}"] = es(g.loc[y, "m3"] / g.loc[y, "w"], 0)
    pm, mpm = g["n"] / g["months"], g["mrr"] / g["months"]
    f.update(crec_nuevos=pct(pm["2024"] / pm["2022"] - 1), crec_mrr_nuevo=pct(mpm["2024"] / mpm["2022"] - 1),
             caida_ticket=pct(1 - (g.loc["2024", "mrr"] / g.loc["2024", "n"]) / (g.loc["2022", "mrr"] / g.loc["2022", "n"])),
             caida_m3=pct(1 - (g.loc["2024", "m3"] / g.loc["2024", "w"]) / (g.loc["2022", "m3"] / g.loc["2022", "w"])))
    first = cm[(cm["mv"] == "new") & (cm["month"] >= WINDOW_START)].assign(year=lambda d: d["month"].dt.year)
    age = (cm["month"] - cm["first_paid_month"]).apply(lambda d: d.n)
    m3 = cm[(age == 2) & cm["customer_id"].isin(first["customer_id"])].merge(first[["customer_id", "year"]], on="customer_id")
    med = m3.groupby("year")["mrr_cop"].median()
    f.update(m3_med_2022=es(med[2022], 0), m3_med_2024=es(med[2024], 0), caida_m3_med=pct(1 - med[2024] / med[2022]))
    drops = [float(f[k].replace("−", "-").replace(",", ".")) for k in ("caida_ticket", "caida_m3", "caida_m3_med")]
    f.update(caida_min=es(min(drops), 0), caida_max=es(max(drops), 0))
    seg = nc.groupby(["year", "industry"]).agg(n=("new_customers", "sum"), mrr=("new_mrr_cop", "sum"))
    seg["ticket"] = seg["mrr"] / seg["n"]
    share = seg["n"] / seg.groupby(level=0)["n"].transform("sum")
    w0, w1, r0, r1 = share.loc["2022"], share.loc["2024"], seg["ticket"].loc["2022"], seg["ticket"].loc["2024"]
    mix, rate = (w1 - w0) * (r0 + r1) / 2, (r1 - r0) * (w0 + w1) / 2
    f.update(kit_dentro=pct(rate.sum() / (mix.sum() + rate.sum())), kit_total=es(mix.sum() + rate.sum(), 0),
             retail_t0=es(r0["Retail"] / 1e3, 1), retail_t1=es(r1["Retail"] / 1e3, 1),
             retail_caida=pct(1 - r1["Retail"] / r0["Retail"]), retail_s0=pct(w0["Retail"], 1), retail_s1=pct(w1["Retail"], 1))

    sm_m = sm.set_index("month")["sm_total_cop"]
    f.update(sm_mes=es(sm_m.loc[sm_m.index >= pd.Period("2024-01", "M")].mean() / MM, 0),
             sm_vs_mrr=es(sm_m.loc[sm_m.index >= pd.Period("2024-01", "M")].mean() / m1, 1))
    cac = tables["cac_quarterly"]
    cac = cac[cac["quarter"].astype(str) >= "2022Q2"]
    f.update(cac_min=mm(cac["cac_cop"].min()), cac_max=mm(cac["cac_cop"].max()),
             payback_min=es(cac["payback_months_no_margin"].min(), 0), payback_max=es(cac["payback_months_no_margin"].max(), 0))
    newm = cm[cm["mv"] == "new"].groupby("month")["customer_id"].nunique()
    j = pd.concat([sm_m.rename("sm"), newm.rename("n")], axis=1).dropna()
    j = j[j.index >= WINDOW_START]
    f.update(corr_niveles=es(j["sm"].corr(j["n"]), 2), corr_dif=es(j["sm"].diff().corr(j["n"].diff()), 2))

    gaps, gap_cust = _internal_gaps(cm)
    n_cust = cm["customer_id"].nunique()
    f.update(clientes=es(n_cust, 0), meses=es(cm["month"].nunique(), 0), huecos=es(gaps, 0), huecos_clientes=es(gap_cust, 0),
             huecos_pct=pct(gap_cust / n_cust), base_inicial=es(int((cm.loc[cm["month"] == cm["month"].min(), "cash_cop"] > 0).sum()), 0),
             payroll_neg=es(int((sm["PayrollExpenses"] < 0).sum()), 0), n_pruebas=es(n_tests, 0))
    return f


TOKEN = re.compile(r"\{\{(\w+)\}\}")


def render(text: str, figures: dict[str, str]) -> str:
    missing = sorted({t for t in TOKEN.findall(text) if t not in figures})
    if missing:
        raise KeyError(f"cifras sin definir en la plantilla: {missing}")
    return TOKEN.sub(lambda m: figures[m.group(1)], text)


def load_figures(path: Path = ROOT / "app" / "data" / "key_figures.csv") -> dict[str, str]:
    d = pd.read_csv(path, dtype=str, keep_default_na=False)
    return dict(zip(d["cifra"], d["valor"]))


def render_docs(figures: dict[str, str], write: bool = True) -> dict[str, str]:
    out = {}
    for tpl, target in DOCS.items():
        text = render((TEMPLATES / tpl).read_text(encoding="utf-8"), figures)
        out[target] = text
        if write:
            (ROOT / target).write_text(text, encoding="utf-8", newline="\n")
    return out
