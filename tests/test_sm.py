"""Eficiencia del S&M: las tablas agregadas se reconstruyen desde los otros agregados."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "data"


def test_magic_number_se_reconstruye_desde_puente_y_sm():
    eff = pd.read_csv(DATA / "sm_efficiency_quarterly.csv").set_index("quarter")
    sm = pd.read_csv(DATA / "sm_monthly.csv")
    b = pd.read_csv(DATA / "bridge_monthly.csv")
    b = b[b["scenario"] == "Corregido (N=2)"].groupby("month")["mrr_close"].first()
    def q(s):
        return pd.PeriodIndex(s, freq="M").asfreq("Q").astype(str)

    smq = sm.groupby(q(sm["month"]))["sm_total_cop"].sum()
    arr = b.groupby(q(b.index)).last() * 12
    magic = (arr - arr.shift(1)) / smq.shift(1)
    ok = eff.index[eff["complete"]][1:]
    assert np.allclose(eff.loc[ok, "magic_number"], magic.loc[ok])
    assert (eff.loc[ok, "magic_number"] < 0.5).all()


def test_payback_por_cohorte_acumula_y_no_llega_al_100():
    pb = pd.read_csv(DATA / "cohort_payback_quarterly.csv")
    rc = pd.read_csv(DATA / "retention_cohorts.csv")
    rc = rc[rc["model"] == "Corregido (N=2)"].sort_values(["cohort", "age"])
    cum = rc.groupby("cohort")["mrr_sum"].cumsum().to_numpy()
    assert np.allclose(pb.sort_values(["cohort", "age"])["cum_mrr_cop"], cum)
    assert (pb.groupby("cohort")["recovered"].diff().dropna() >= 0).all()
    assert (pb.loc[pb["mature"], "recovered"] < 1).all()
