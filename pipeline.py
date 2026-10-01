"""Pipeline reproducible del reto: carga → modelos de MRR → tablas de salida para el análisis y la demo.

Uso:  python pipeline.py          (escribe en outputs/ e imprime el resumen)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from finora.load import load_industry, load_sm_spend, load_transactions
from finora.mrr import ALL_MOVES, Rules, bridge, build_customer_month

OUT = Path(__file__).resolve().parent / "outputs"
WINDOW_START = pd.Period("2022-04", "M")   # ene–mar 2022 = periodo de arranque (censura a la izquierda)
MM = 1e6


def window_totals(br: pd.DataFrame) -> pd.Series:
    w = br.loc[br.index >= WINDOW_START, [c for c in ALL_MOVES if c in br.columns]]
    return w.sum()


def rule_impact(tx: pd.DataFrame) -> pd.DataFrame:
    """Cuánto cambia el puente según cada regla (sensibilidad): actual vs corregido con N=1/2/3 y sin pricing."""
    rows = {}
    rows["Modelo actual (caja)"] = window_totals(bridge(build_customer_month(tx, Rules()), "actual"))
    for n in (1, 2, 3):
        rows[f"Corregido N={n}"] = window_totals(bridge(build_customer_month(tx, Rules(gap_tolerance=n)), "corrected"))
    rows["Corregido N=2 sin separar precio"] = window_totals(
        bridge(build_customer_month(tx, Rules(detect_pricing=False)), "corrected"))
    rows["Corregido N=2, mora final = churn"] = window_totals(
        bridge(build_customer_month(tx, Rules(trailing_policy="churn")), "corrected"))
    return (pd.DataFrame(rows).T.reindex(columns=ALL_MOVES).fillna(0) / MM).round(1)


def kitagawa(w0: pd.Series, r0: pd.Series, w1: pd.Series, r1: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Descomposición de Kitagawa: Δ(Σ w·r) = efecto mezcla + efecto tasa (por segmento)."""
    idx = w0.index.union(w1.index)
    w0, w1, r0, r1 = (s.reindex(idx).fillna(0) for s in (w0, w1, r0, r1))
    mix = (w1 - w0) * (r0 + r1) / 2
    rate = (r1 - r0) * (w0 + w1) / 2
    return mix, rate


def main() -> None:
    OUT.mkdir(exist_ok=True)
    tx = load_transactions()
    ind = load_industry()
    sm = load_sm_spend()
    cm = build_customer_month(tx, Rules()).merge(ind, on="customer_id", how="left")
    cm.assign(month=cm["month"].astype(str)).to_csv(OUT / "customer_month.csv", index=False)

    br_c, br_a = bridge(cm, "corrected"), bridge(cm, "actual")
    for name, br in (("bridge_corrected", br_c), ("bridge_actual", br_a)):
        br.reset_index().assign(month=lambda d: d["month"].astype(str)).to_csv(OUT / f"{name}.csv", index=False)

    print("=== MRR (millones COP)")
    for m in (pd.Period("2022-03", "M"), pd.Period("2023-10", "M"), pd.Period("2024-10", "M")):
        print(f"{m}: actual={br_a.loc[m, 'mrr_close'] / MM:.1f}  corregido={br_c.loc[m, 'mrr_close'] / MM:.1f}")

    print("\n=== Puente acumulado abr-2022 → oct-2024 (millones COP)")
    tot = pd.DataFrame({"actual": window_totals(br_a), "corregido": window_totals(br_c)}).fillna(0) / MM
    print(tot.round(1).to_string())
    net_change = (br_c.loc[pd.Period("2024-10", "M"), "mrr_close"] - br_c.loc[pd.Period("2022-03", "M"), "mrr_close"]) / MM
    print(f"cambio neto corregido: {net_change:.1f}")

    impact = rule_impact(tx)
    impact.to_csv(OUT / "rule_impact.csv")
    print("\n=== Sensibilidad por regla (millones COP, acumulado de la ventana)\n", impact.to_string())

    w = cm[cm["month"] >= WINDOW_START]
    print("\n=== Clasificación de la caja que no es MRR (millones COP, ventana)")
    print((w.groupby("extra_kind")["extra_cop"].agg(["count", "sum"]).assign(sum=lambda d: d["sum"] / MM)).round(2))
    print("meses-cliente en mora tolerada:", (w["status"] == "gap").sum(),
          "| pagados después:", (w["gap_paid"]).sum(),
          "| MRR reconocido sin caja en esos meses (MM):", round(w.loc[w["status"] == "gap", "mrr_cop"].sum() / MM, 1))
    print("mora abierta al cierre (oct-2024):", (cm[cm["month"] == cm["month"].max()]["status"] == "delinquent_open").sum())

    up = w[w["mv"] == "price_uplift"]
    print("\n=== Subidas de precio: eventos y monto (MM) por confianza y año")
    print(up.groupby([up["month"].dt.year, "uplift_conf"])["delta"].agg(["count", "sum"]).assign(
        sum=lambda d: (d["sum"] / MM).round(2)))

    half = w[w["half_cut"]]
    print(f"\n=== Bajadas exactas a la mitad (¿descuento o downgrade?): {len(half)} eventos, "
          f"{half['customer_id'].nunique()} clientes, {half['delta'].sum() / MM:.1f} MM de 'contracción'")
    contr = w.loc[w["mv"] == "contraction", "delta"].sum() / MM
    print(f"contracción total corregida: {contr:.1f} MM → si las bajadas a la mitad fueran descuentos, "
          f"la contracción por comportamiento sería {contr - half['delta'].sum() / MM:.1f} MM")

    # ----- Caso 1: lado Won del funnel: nuevos clientes, ticket de entrada, industria
    first = cm[(cm["mv"] == "new") & (cm["month"] >= WINDOW_START)].copy()
    first["year"] = first["month"].dt.year
    months_in_year = {2022: 9, 2023: 12, 2024: 10}
    nc = first.groupby("year").agg(new_customers=("customer_id", "nunique"), new_mrr=("delta", "sum"))
    nc["per_month"] = nc["new_customers"] / nc.index.map(months_in_year)
    nc["new_mrr_per_month_MM"] = nc["new_mrr"] / nc.index.map(months_in_year) / MM
    nc["avg_entry_ticket_COP"] = nc["new_mrr"] / nc["new_customers"]
    print("\n=== Nuevos clientes por año (corregido)\n", nc.round(1).to_string())
    seg = first.groupby(["year", "industry"]).agg(n=("customer_id", "nunique"), mrr=("delta", "sum"))
    seg["ticket"] = seg["mrr"] / seg["n"]
    share = seg["n"] / seg.groupby(level=0)["n"].transform("sum")
    mix, rate = kitagawa(share.loc[2022], seg["ticket"].loc[2022], share.loc[2024], seg["ticket"].loc[2024])
    k = pd.DataFrame({"share_2022": share.loc[2022], "share_2024": share.loc[2024],
                      "ticket_2022": seg["ticket"].loc[2022], "ticket_2024": seg["ticket"].loc[2024],
                      "mix_effect": mix, "rate_effect": rate}).round(3)
    print("\n=== Kitagawa del ticket de entrada promedio 2022 → 2024 (COP)\n", k.to_string())
    print(f"Δ ticket promedio = {(mix.sum() + rate.sum()):.0f} COP  (mezcla {mix.sum():.0f}, dentro de industria {rate.sum():.0f})")
    k.to_csv(OUT / "kitagawa_entry_ticket.csv")

    # ----- Robustez: ticket al 3er mes (descarta descuentos de bienvenida en el primer pago)
    cm["age"] = (cm["month"] - cm["first_paid_month"]).apply(lambda d: d.n)
    m3 = cm[(cm["age"] == 2) & cm["customer_id"].isin(first["customer_id"])].merge(
        first[["customer_id", "year"]], on="customer_id")
    print("\n=== MRR promedio al 3er mes por año de alta (COP; incluye a los que ya se fueron con 0)")
    print(m3.groupby("year")["mrr_cop"].agg(["count", "mean", "median"]).round(0).to_string())

    # ----- Retención por cohorte a 12 meses (NRR y GRR), actual vs corregido
    rows = []
    for mrr_col, label in (("mrr_actual_cop", "actual"), ("mrr_cop", "corregido")):
        for cy, g in first.groupby("year"):
            ids = g["customer_id"]
            d = cm[cm["customer_id"].isin(ids)]
            start = d[d["age"] == 0].set_index("customer_id")[mrr_col]
            m12 = d[d["age"] == 12].set_index("customer_id")[mrr_col]
            ok = start.index.intersection(m12.index)
            if len(ok) == 0:
                continue
            s, e = start[ok], m12[ok]
            rows.append((label, cy, len(ok), (e.sum() / s.sum()), (np.minimum(e, s).sum() / s.sum()),
                         (e > 0).mean()))
    ret = pd.DataFrame(rows, columns=["modelo", "cohorte", "clientes", "NRR_12m", "GRR_12m", "logo_ret_12m"])
    print("\n=== Retención a 12 meses por cohorte de alta\n", ret.round(3).to_string(index=False))
    ret.to_csv(OUT / "retention_12m.csv", index=False)

    # ----- Revenue no capturado / en riesgo (lo que se puede medir hoy)
    gap = w[w["status"] == "gap"]
    unpaid = gap.loc[~gap["gap_paid"], "mrr_cop"].sum() / MM
    print(f"\n=== MRR reconocido en meses de mora nunca pagados: {unpaid:.1f} MM "
          f"({(~gap['gap_paid']).sum()} meses-cliente)  | pagados después: {gap.loc[gap['gap_paid'], 'mrr_cop'].sum() / MM:.1f} MM")
    last = cm[cm["month"] == cm["month"].max()]
    print(f"MRR en mora abierta al cierre (oct-2024): {last.loc[last['status'] == 'delinquent_open', 'mrr_cop'].sum() / MM:.1f} MM "
          f"de {last['mrr_cop'].sum() / MM:.1f} MM")
    # fuga acumulada si las bajadas a la mitad fueran descuentos (cota superior): meses que se mantuvo la rebaja
    leak = 0.0
    for cid, g in cm[cm["customer_id"].isin(cm.loc[cm["half_cut"], "customer_id"])].groupby("customer_id"):
        lv, hc = g["mrr_cop"].to_numpy(), g["half_cut"].to_numpy()
        months = g["month"].to_numpy()
        for t in np.where(hc)[0]:
            j = t
            while j < len(lv) and lv[j] > 0 and np.isclose(lv[j], lv[t]):
                if months[j] >= WINDOW_START:
                    leak += lv[t - 1] - lv[t]
                j += 1
    print(f"Cota superior de 'revenue no capturado' si las bajadas a la mitad fueran descuentos: {leak / MM:.1f} MM acumulados")

    # ----- S&M y CAC (combinado, con advertencias)
    q = sm.assign(q=sm["month"].dt.asfreq("Q")).groupby("q")["sm_total_cop"].sum()
    nq = first.assign(q=first["month"].dt.asfreq("Q")).groupby("q").agg(n=("customer_id", "nunique"), mrr=("delta", "sum"))
    cac = pd.DataFrame({"sm_MM": q / MM}).join(nq, how="inner")
    cac["CAC_MM"] = cac["sm_MM"] / cac["n"]
    cac["payback_months_no_margin"] = cac["CAC_MM"] * MM / (cac["mrr"] / cac["n"])
    print("\n=== CAC combinado por trimestre (S&M total / clientes nuevos)\n", cac.round(2).to_string())
    cac.to_csv(OUT / "cac_quarterly.csv")

    # ----- Tablas agregadas para la demo pública (sin detalle por cliente)
    from finora.aggregates import export_app_data
    export_app_data(tx, ind, sm, Path(__file__).resolve().parent / "app" / "data")
    print("\nTablas agregadas para la demo escritas en app/data/")


if __name__ == "__main__":
    main()
