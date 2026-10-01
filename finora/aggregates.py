"""Tablas **agregadas** para la demo pública (sin detalle por cliente).

Todo lo que sale de aquí se agrega por mes, industria, cohorte o escenario. Ninguna tabla tiene customer_id.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from finora.mrr import ALL_MOVES, Rules, bridge, build_customer_month

WINDOW_START = pd.Period("2022-04", "M")

SCENARIOS = {
    "Corregido (N=2)": Rules(),
    "Corregido (N=1)": Rules(gap_tolerance=1),
    "Corregido (N=3)": Rules(gap_tolerance=3),
    "Corregido sin separar precio": Rules(detect_pricing=False),
    "Corregido, mora final = churn": Rules(trailing_policy="churn"),
}


INF = float("inf")
# Sensibilidad: una regla a la vez, apagada o llevada a su extremo (escenario, regla, ajuste, reglas)
RULE_SCENARIOS = [
    ("Base: corregido (N = 2)", "—", "reglas por defecto", Rules()),
    ("Mora tolerada N = 1", "Tolerancia de mora", "gap_tolerance = 1", Rules(gap_tolerance=1)),
    ("Mora tolerada N = 3", "Tolerancia de mora", "gap_tolerance = 3", Rules(gap_tolerance=3)),
    ("Mora final = churn", "Mora abierta al cierre", "trailing_policy = churn", Rules(trailing_policy="churn")),
    ("Sin separar subidas de precio", "Subidas de precio", "detect_pricing = False", Rules(detect_pricing=False)),
    ("Sin retroactivos", "Retroactivo de una subida", "retro_max_k = 0", Rules(retro_max_k=0)),
    ("Sin prepagos", "Prepagos multi-mes", "prepay_min_amount = ∞", Rules(prepay_min_amount=INF)),
    ("Sin puestas al día", "Puestas al día y pagos agrupados", "detect_catchup = False", Rules(detect_catchup=False)),
    ("Sin picos", "Picos puntuales", "spike_factor = ∞", Rules(spike_factor=INF)),
    ("Uso variable: nadie", "Clientes de uso variable", "usage_distinct_amounts = ∞", Rules(usage_distinct_amounts=10**9)),
    ("Uso variable: todos", "Clientes de uso variable", "usage_distinct_amounts = 1", Rules(usage_distinct_amounts=1)),
]
SENS_MOVES = ["new", "expansion", "price_uplift", "reactivation", "contraction", "churn"]


def nrr_12m(cm: pd.DataFrame, year: int, col: str = "mrr_cop") -> float:
    """NRR a 12 meses de las altas de un año, ponderado por MRR inicial (misma definición que retention_cohorts)."""
    first = cm.loc[cm["mv"] == "new", ["customer_id", "month"]].rename(columns={"month": "cohort_month"})
    c = cm.merge(first[first["cohort_month"].dt.year == year], on="customer_id")
    age = (c["month"] - c["first_paid_month"]).apply(lambda d: d.n)
    start = c[age == 0].set_index("customer_id")[col]
    end = c[age == 12].set_index("customer_id")[col]
    ids = end.index
    return float(end.sum() / start.reindex(ids).sum())


def rule_sensitivity(tx: pd.DataFrame) -> pd.DataFrame:
    """Movimientos acumulados de la ventana y NRR a 12 meses (altas 2023) con cada regla apagada, una a la vez."""
    rows = []
    base = build_customer_month(tx, Rules())
    act = bridge(base, "actual")
    tot = act.loc[act.index >= WINDOW_START, [m for m in SENS_MOVES if m in act.columns]].sum()
    rows.append(("Modelo actual (caja)", "Referencia", "caja = MRR", *[tot.get(m, 0.0) for m in SENS_MOVES],
                 nrr_12m(base, 2023, "mrr_actual_cop")))
    for name, rule, how, rules in RULE_SCENARIOS:
        cm = base if name.startswith("Base") else build_customer_month(tx, rules)
        br = bridge(cm, "corrected")
        tot = br.loc[br.index >= WINDOW_START, [m for m in SENS_MOVES if m in br.columns]].sum()
        rows.append((name, rule, how, *[tot.get(m, 0.0) for m in SENS_MOVES], nrr_12m(cm, 2023)))
    return pd.DataFrame(rows, columns=["escenario", "regla", "ajuste", *[f"{m}_cop" for m in SENS_MOVES], "nrr12_2023"])


def _long_bridge(br: pd.DataFrame, scenario: str) -> pd.DataFrame:
    moves = [c for c in ALL_MOVES if c in br.columns]
    long = br[moves].reset_index().melt(id_vars="month", var_name="movement", value_name="amount_cop")
    long = long.merge(br[["mrr_open", "mrr_close"]].reset_index(), on="month")
    long["scenario"] = scenario
    return long


def export_app_data(tx: pd.DataFrame, ind: pd.DataFrame, sm: pd.DataFrame, out_dir: Path) -> dict[str, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tables: dict[str, pd.DataFrame] = {}

    # --- puentes por escenario (incluye el modelo actual)
    base = build_customer_month(tx, Rules()).merge(ind, on="customer_id", how="left")
    parts = [_long_bridge(bridge(base, "actual"), "Modelo actual (caja)"),
             _long_bridge(bridge(base, "corrected"), "Corregido (N=2)")]
    for name, rules in SCENARIOS.items():
        if name == "Corregido (N=2)":
            continue
        parts.append(_long_bridge(bridge(build_customer_month(tx, rules), "corrected"), name))
    tables["bridge_monthly"] = pd.concat(parts, ignore_index=True)

    cm = base
    cm["age"] = (cm["month"] - cm["first_paid_month"]).apply(lambda d: d.n)

    # --- clientes por movimiento y mes (ambos modelos) y clientes activos: monto + clientes, como ChartMogul
    cnt = []
    for col, label in (("mv", "Corregido (N=2)"), ("mv_actual", "Modelo actual (caja)")):
        c_ = cm[cm[col].isin(ALL_MOVES)].groupby(["month", col])["customer_id"].nunique().reset_index()
        cnt.append(c_.rename(columns={col: "movement", "customer_id": "customers"}).assign(scenario=label))
    tables["movement_counts_monthly"] = pd.concat(cnt, ignore_index=True)
    tables["active_customers_monthly"] = cm.groupby("month").agg(
        active_customers=("mrr_cop", lambda s: int((s > 0).sum())),
        paying_customers=("cash_cop", lambda s: int((s > 0).sum()))).reset_index()

    # --- caja que no es MRR, por tipo y mes
    nonmrr = cm[cm["extra_kind"] != ""].groupby(["month", "extra_kind"]).agg(
        events=("extra_cop", "size"), amount_cop=("extra_cop", "sum")).reset_index()
    tables["nonmrr_cash_monthly"] = nonmrr

    # --- estado de la base por mes (clientes y MRR)
    st = cm[cm["status"] != "pre"].groupby(["month", "status"]).agg(
        customers=("customer_id", "nunique"), mrr_cop=("mrr_cop", "sum")).reset_index()
    tables["status_monthly"] = st

    # --- MRR por industria y mes (ambos modelos)
    tables["mrr_by_industry_monthly"] = cm.groupby(["month", "industry"]).agg(
        mrr_cop=("mrr_cop", "sum"), mrr_actual_cop=("mrr_actual_cop", "sum"),
        paying_customers=("cash_cop", lambda s: int((s > 0).sum()))).reset_index()

    # --- subidas de precio por mes y confianza
    up = cm[cm["mv"] == "price_uplift"]
    tables["price_uplift_monthly"] = up.groupby(["month", "uplift_conf"]).agg(
        events=("delta", "size"), amount_cop=("delta", "sum")).reset_index()

    # --- bajadas exactas a la mitad: eventos y cota superior de fuga acumulada por mes
    leak_rows = []
    for _, g in cm[cm["customer_id"].isin(cm.loc[cm["half_cut"], "customer_id"])].groupby("customer_id"):
        lv, hc, months = g["mrr_cop"].to_numpy(), g["half_cut"].to_numpy(), g["month"].to_numpy()
        for t in np.where(hc)[0]:
            j = t
            while j < len(lv) and lv[j] > 0 and np.isclose(lv[j], lv[t]):
                leak_rows.append((months[j], lv[t - 1] - lv[t], j == t))
                j += 1
    leak = pd.DataFrame(leak_rows, columns=["month", "foregone_cop", "is_event"])
    tables["half_cut_monthly"] = leak.groupby("month").agg(
        events=("is_event", "sum"), foregone_cop=("foregone_cop", "sum")).reset_index()

    # --- clientes nuevos por mes e industria (modelo corregido) + MRR al 3er mes
    new = cm[cm["mv"] == "new"][["customer_id", "month", "industry", "delta"]]
    m3 = cm[cm["age"] == 2][["customer_id", "mrr_cop"]].rename(columns={"mrr_cop": "mrr_m3_cop"})
    new = new.merge(m3, on="customer_id", how="left")
    tables["new_customers_monthly"] = new.groupby(["month", "industry"]).agg(
        new_customers=("customer_id", "nunique"), new_mrr_cop=("delta", "sum"),
        mrr_m3_sum_cop=("mrr_m3_cop", "sum"), with_m3=("mrr_m3_cop", "count")).reset_index()

    # --- retención por cohorte trimestral y edad (ambos modelos)
    first_q = cm.loc[cm["mv"] == "new"].assign(cohort=lambda d: d["month"].dt.asfreq("Q"))[["customer_id", "cohort"]]
    c = cm.merge(first_q, on="customer_id")
    rows = []
    for col, label in (("mrr_actual_cop", "Modelo actual (caja)"), ("mrr_cop", "Corregido (N=2)")):
        start = c[c["age"] == 0].set_index("customer_id")[col]
        cc = c[(c["age"] >= 0) & (c["age"] <= 24)].copy()
        cc["start"] = cc["customer_id"].map(start)
        g = cc.groupby(["cohort", "age"]).agg(
            n=("customer_id", "nunique"), start_sum=("start", "sum"), mrr_sum=(col, "sum"),
            gross_sum=(col, lambda s: np.minimum(s, cc.loc[s.index, "start"]).sum()),
            active=(col, lambda s: int((s > 0).sum()))).reset_index()
        g["model"] = label
        rows.append(g)
    ret = pd.concat(rows, ignore_index=True)
    ret["nrr"] = ret["mrr_sum"] / ret["start_sum"]
    ret["grr"] = ret["gross_sum"] / ret["start_sum"]
    ret["logo_retention"] = ret["active"] / ret["n"]
    tables["retention_cohorts"] = ret      # sumas agregadas por cohorte: permiten reagregar NRR/GRR ponderado por MRR

    # --- S&M mensual (ya es agregado de la empresa) y CAC trimestral
    tables["sm_monthly"] = sm.copy()
    q = sm.assign(q=sm["month"].dt.asfreq("Q")).groupby("q")["sm_total_cop"].sum()
    nq = cm[cm["mv"] == "new"].assign(q=lambda d: d["month"].dt.asfreq("Q")).groupby("q").agg(
        new_customers=("customer_id", "nunique"), new_mrr_cop=("delta", "sum"))
    cac = pd.DataFrame({"sm_cop": q}).join(nq, how="inner").reset_index().rename(columns={"index": "quarter", "q": "quarter"})
    cac["cac_cop"] = cac["sm_cop"] / cac["new_customers"]
    cac["payback_months_no_margin"] = cac["cac_cop"] / (cac["new_mrr_cop"] / cac["new_customers"])
    tables["cac_quarterly"] = cac

    # --- sensibilidad: una regla a la vez
    tables["rule_sensitivity"] = rule_sensitivity(tx)

    # --- calidad de datos (tabla de tratamiento)
    w = cm[cm["month"] >= WINDOW_START]
    dq = [
        ("Malla cliente × mes completa (0 = no pagó)", f"{cm['customer_id'].nunique()} clientes × {cm['month'].nunique()} meses", "Se usa como malla de fechas"),
        ("Meses en mora tolerada (vuelve a pagar)", f"{(w['status'] == 'gap').sum()} meses-cliente", "Cliente activo; MRR = monto recurrente"),
        ("…de los cuales se pagaron después", f"{w['gap_paid'].sum()} meses-cliente", "La puesta al día es cobro de mora, no MRR"),
        ("Pagos de puesta al día (k × monto)", f"{(w['extra_kind'] == 'arrears').sum()} pagos", "El exceso sale del MRR"),
        ("Retroactivo en subidas de precio", f"{(w['extra_kind'] == 'retro').sum()} pagos", "Subida = pricing; retroactivo = cargo único"),
        ("Prepagos multi-mes (p. ej., anual)", f"{(w['extra_kind'] == 'prepaid').sum()} pagos", "Se reparten en min(12, meses cubiertos)"),
        ("Pago grande al final de la serie (¿prepago?)", f"{(w['extra_kind'] == 'prepaid_pending').sum()} pagos", "Prepago en confirmación: se reconoce el nivel anterior"),
        ("Subidas de precio en el último mes", f"{(cm['uplift_conf'] == 'pending').sum()} clientes", "En confirmación: falta el mes siguiente"),
        ("Picos y pagos agrupados", f"{w['extra_kind'].isin(['spike', 'lump']).sum()} pagos", "Nivel recurrente local; el exceso se aísla"),
        ("Bajadas exactas a la mitad", f"{w['half_cut'].sum()} eventos", "Contracción marcada como ambigua (¿descuento?)"),
        ("Mora abierta al cierre (sin confirmar)", f"{(cm.loc[cm['month'] == cm['month'].max(), 'status'] == 'delinquent_open').sum()} clientes", "Sigue activa y marcada; sensibilidad = churn"),
        ("Clientes activos al inicio (ene-2022)", f"{(cm.loc[cm['month'] == cm['month'].min(), 'cash_cop'] > 0).sum()} clientes", "Base de apertura; ventana desde abr-2022"),
        ("PayrollExpenses negativo", f"{(sm['PayrollExpenses'] < 0).sum()} meses", "Se mantiene (ajuste contable) y se reporta"),
        ("Cobertura de Industry", "100%", "—"),
    ]
    tables["data_quality"] = pd.DataFrame(dq, columns=["hallazgo", "magnitud", "tratamiento"])

    for name, df in tables.items():
        df = df.copy()
        for col in df.columns:
            if isinstance(df[col].dtype, pd.PeriodDtype):
                df[col] = df[col].astype(str)
        assert "customer_id" not in df.columns, f"{name} tiene detalle por cliente"
        df.to_csv(out_dir / f"{name}.csv", index=False)
    return tables
