"""Métricas del funnel propuesto (Caso 1)."""
from __future__ import annotations

import numpy as np
import pandas as pd

STAGES = ["New", "Working", "Engaged", "SQL", "Demo", "Proposal", "Won"]


def reach_table(leads: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Una fila por lead, con el timestamp de llegada a cada etapa (NaT si no llegó)."""
    first = events.groupby(["lead_id", "stage"])["ts"].min().unstack()
    first = first.reindex(columns=STAGES)
    r = leads.set_index("lead_id").join(first)
    r["cohort"] = r["created_at"].dt.to_period("M")
    return r


def cohort_conversion(r: pd.DataFrame, frm: str, to: str, window_days: int, as_of: pd.Timestamp,
                      by: str | None = None) -> pd.DataFrame:
    """% de leads de la cohorte que, habiendo llegado a `frm`, llegan a `to` en ≤ window_days."""
    base = r[r[frm].notna()].copy()
    base["hit"] = (base[to] - base[frm]).dt.total_seconds() / 86400 <= window_days
    base["mature"] = base[frm] + pd.Timedelta(days=window_days) <= as_of
    keys = ["cohort"] + ([by] if by else [])
    g = base.groupby(keys).agg(n=("hit", "size"), conv=("hit", "mean"), mature=("mature", "min")).reset_index()
    return g


def snapshot_vs_cohort(r: pd.DataFrame, as_of: pd.Timestamp, window_days: int = 90) -> pd.DataFrame:
    """La métrica 'snapshot' (Won del mes / New del mes) vs la conversión real por cohorte."""
    won_m = r[r["Won"].notna()].groupby(r["Won"].dt.to_period("M")).size()
    new_m = r.groupby("cohort").size()
    snap = (won_m / new_m).rename("snapshot")
    coh = cohort_conversion(r, "New", "Won", window_days, as_of).set_index("cohort")
    out = pd.concat([snap, coh["conv"].rename("cohort"), coh["mature"]], axis=1)
    return out.reset_index(names="month")


def kitagawa(r: pd.DataFrame, frm: str, to: str, window_days: int, base_months, recent_months,
             segment: str = "channel") -> pd.DataFrame:
    """Δ conversión entre dos periodos = efecto mezcla + efecto tasa, por segmento (Kitagawa 1955)."""
    def period(months):
        d = r[r["cohort"].isin(months) & r[frm].notna()].copy()
        d["hit"] = (d[to] - d[frm]).dt.total_seconds() / 86400 <= window_days
        g = d.groupby(segment)["hit"].agg(["size", "mean"])
        return g["size"] / g["size"].sum(), g["mean"]
    w0, r0 = period(base_months)
    w1, r1 = period(recent_months)
    idx = w0.index.union(w1.index)
    w0, w1, r0, r1 = (s.reindex(idx).fillna(0) for s in (w0, w1, r0, r1))
    return pd.DataFrame({
        "share_base": w0, "share_recent": w1, "conv_base": r0, "conv_recent": r1,
        "mix_effect": (w1 - w0) * (r0 + r1) / 2,
        "rate_effect": (r1 - r0) * (w0 + w1) / 2,
    })


def speed_to_lead(r: pd.DataFrame) -> pd.DataFrame:
    d = r[r["speed_to_lead_h"].notna()]
    return d.groupby("cohort")["speed_to_lead_h"].agg(
        p50="median", p90=lambda s: s.quantile(0.9), sla_1h=lambda s: (s <= 1).mean()).reset_index()


def conversion_by_speed(r: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    """Working → Engaged según tiempo al primer contacto, DENTRO de cada canal (evita confundir con mezcla)."""
    d = r[r["Working"].notna() & r["speed_to_lead_h"].notna()].copy()
    d["speed_bucket"] = pd.cut(d["speed_to_lead_h"], [0, 1, 4, 24, 72, np.inf],
                               labels=["<1 h", "1–4 h", "4–24 h", "1–3 días", ">3 días"])
    d["hit"] = (d["Engaged"] - d["Working"]).dt.total_seconds() / 86400 <= window_days
    return d.groupby(["channel", "speed_bucket"], observed=True)["hit"].agg(["size", "mean"]).reset_index()


def p_chart(r: pd.DataFrame, frm: str, to: str, window_days: int, as_of: pd.Timestamp,
            base_weeks: int = 26) -> pd.DataFrame:
    """Gráfico de control p semanal: alerta solo si la tasa sale de p̄ ± 3σ (σ binomial por tamaño)."""
    d = r[r[frm].notna()].copy()
    d = d[d[frm] + pd.Timedelta(days=window_days) <= as_of]
    d["week"] = d[frm].dt.to_period("W").dt.start_time
    d["hit"] = (d[to] - d[frm]).dt.total_seconds() / 86400 <= window_days
    g = d.groupby("week")["hit"].agg(n="size", p="mean").reset_index()
    pbar = (g["p"] * g["n"]).head(base_weeks).sum() / g["n"].head(base_weeks).sum()
    g["center"] = pbar
    g["ucl"] = pbar + 3 * np.sqrt(pbar * (1 - pbar) / g["n"])
    g["lcl"] = (pbar - 3 * np.sqrt(pbar * (1 - pbar) / g["n"])).clip(lower=0)
    g["out_of_limits"] = (g["p"] < g["lcl"]) | (g["p"] > g["ucl"])
    side = np.sign(g["p"] - pbar)
    run = side.groupby((side != side.shift()).cumsum()).cumcount() + 1
    g["shift"] = (run >= 8) & (side != 0)
    g["alert"] = g["out_of_limits"] | g["shift"]
    return g


def period_metrics(r: pd.DataFrame, as_of: pd.Timestamp, freq: str = "W") -> pd.DataFrame:
    """Entradas y salidas del funnel por semana ('W') o mes ('M'), solo con periodos maduros para cada tasa."""
    def per(ts):
        return ts.dt.to_period(freq).dt.start_time

    created = per(r["created_at"])
    out = r.groupby(created).agg(leads=("created_at", "size"),
                                 high_fit=("company_size", lambda s: (s != "micro").mean()))
    sdr = r[r["speed_to_lead_h"].notna()]
    s2l = sdr.groupby(per(sdr["created_at"]))["speed_to_lead_h"].agg(
        speed_p50="median", sla_1h=lambda s: (s <= 1).mean())
    w = r[r["Working"].notna() & (r["Working"] + pd.Timedelta(days=30) <= as_of)]
    w2e = w.groupby(per(w["Working"])).apply(
        lambda d: ((d["Engaged"] - d["Working"]).dt.total_seconds() / 86400 <= 30).mean(), include_groups=False)
    q = r[r["SQL"].notna() & (r["SQL"] + pd.Timedelta(days=60) <= as_of)]
    s2w = q.groupby(per(q["SQL"])).apply(
        lambda d: ((d["Won"] - d["SQL"]).dt.total_seconds() / 86400 <= 60).mean(), include_groups=False)
    won = r[r["Won"].notna()]
    wn = won.groupby(per(won["Won"])).agg(new_customers=("Won", "size"), new_mrr=("mrr_cop", "sum"))
    out = out.join(s2l).join(w2e.rename("work_to_eng")).join(s2w.rename("sql_to_won")).join(wn)
    out["ticket"] = out["new_mrr"] / out["new_customers"]
    last_full = as_of.to_period(freq).start_time
    return out[out.index < last_full]


def stalled(r: pd.DataFrame, events: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Leads abiertos cuyo tiempo en la etapa actual supera el P90 histórico de su etapa y camino."""
    last = events.sort_values("ts").groupby("lead_id").tail(1).set_index("lead_id")
    last = last[~last["stage"].isin(["Won", "Lost"])]
    last["days_in_stage"] = (as_of - last["ts"]).dt.total_seconds() / 86400
    last = last.join(r[["channel", "path", "company_size"]])
    rows = []
    for path, g in r.groupby("path"):
        for i, s in enumerate(STAGES[:-1]):
            nxt = r.loc[g.index, STAGES[i + 1:]].min(axis=1)
            dur = ((nxt - g[s]).dt.total_seconds() / 86400).dropna()
            if len(dur) >= 30:
                rows.append((path, s, dur.quantile(0.9)))
    p90 = pd.DataFrame(rows, columns=["path", "stage", "p90_stage"])
    last = last.reset_index().merge(p90, on=["path", "stage"], how="left").set_index("lead_id")
    out = last[(last["days_in_stage"] > last["p90_stage"]) & (last["days_in_stage"] <= 120)].reset_index()
    ae = out["stage"].isin(["SQL", "Demo", "Proposal"])
    out["owner"] = np.where(ae, "AE " + (out["lead_id"] % 4 + 1).astype(str), "SDR " + (out["lead_id"] % 8 + 1).astype(str))
    return out
