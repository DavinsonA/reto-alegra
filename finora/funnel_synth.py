"""Generador de datos SINTÉTICOS del funnel de Finora (no hay datos reales del funnel en el reto)."""
from __future__ import annotations

import numpy as np
import pandas as pd

STAGES = ["New", "Working", "Engaged", "SQL", "Demo", "Proposal", "Won"]
CHANNELS = {
    "Paid Social": (260, (0.70, 0.25, 0.05), "sdr_full"),
    "Paid Search": (300, (0.45, 0.40, 0.15), "sdr_full"),
    "Outbound":    (180, (0.30, 0.45, 0.25), "sdr_full"),
    "Contadores (partners)": (90, (0.35, 0.45, 0.20), "direct_sql"),
    "Referidos":   (60, (0.30, 0.45, 0.25), "direct_sql"),
    "Producto (self-serve)": (420, (0.65, 0.30, 0.05), "self_serve"),
}
FIT = {"micro": 0.55, "pequeña": 1.0, "mediana": 1.35}
TICKET = {"micro": 25_000, "pequeña": 55_000, "mediana": 140_000}
SDR_CAPACITY = 700


S2L_SIGMA = 1.2
LOST_P = 0.98


def generate(start="2023-01-01", end="2024-10-31", seed=42, target_ticket: float | None = None
             ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`target_ticket`: si se da (p. ej., el ticket de entrada real), el MRR de los ganados se escala a ese promedio."""
    rng = np.random.default_rng(seed)
    as_of = pd.Timestamp(end)
    months = pd.period_range(start, end, freq="M")
    leads, events = [], []
    lead_id = 0
    for m in months:
        surge = m >= pd.Period("2024-03", "M")
        vol = {ch: base * (2.6 if (ch == "Paid Social" and surge) else 1.0) * (1 + 0.004 * (m - months[0]).n)
               for ch, (base, _, _) in CHANNELS.items()}
        sdr_load = sum(v for ch, v in vol.items() if CHANNELS[ch][2] == "sdr_full") / SDR_CAPACITY
        for ch, (_, size_mix, path) in CHANNELS.items():
            n = rng.poisson(vol[ch])
            sizes = rng.choice(["micro", "pequeña", "mediana"], size=n, p=size_mix)
            days = rng.integers(0, m.days_in_month, size=n)
            for size, d in zip(sizes, days):
                lead_id += 1
                created = m.start_time + pd.Timedelta(days=int(d), hours=int(rng.integers(7, 19)))
                fit = FIT[size]
                lv = dict(lead_id=lead_id, created_at=created, channel=ch, path=path, company_size=size,
                          speed_to_lead_h=np.nan, mrr_cop=np.nan)
                ts = created
                ev = [("New", ts)]
                if path == "self_serve":
                    if rng.random() < 0.07 * fit:
                        ts = ts + pd.Timedelta(days=float(rng.lognormal(np.log(14), 0.4)))
                        ev.append(("Won", ts))
                elif path == "direct_sql":
                    ts = ts + pd.Timedelta(days=float(rng.lognormal(np.log(2), 0.5)))
                    ev.append(("SQL", ts))
                    ev += _post_sql(rng, ts, fit)
                else:
                    med_h = 1.6 * max(sdr_load, 0.6) ** 2.1
                    s2l = float(rng.lognormal(np.log(med_h), S2L_SIGMA))
                    lv["speed_to_lead_h"] = s2l
                    if rng.random() < 0.92:
                        ts = ts + pd.Timedelta(hours=s2l)
                        ev.append(("Working", ts))
                        speed_mult = 1.0 if s2l <= 1 else 0.75 if s2l <= 4 else 0.6 if s2l <= 24 else 0.45
                        if rng.random() < min(0.95, 0.42 * fit * speed_mult):
                            ts = ts + pd.Timedelta(days=float(rng.lognormal(np.log(4), 0.6)))
                            ev.append(("Engaged", ts))
                            if rng.random() < min(0.95, 0.45 * fit):
                                ts = ts + pd.Timedelta(days=float(rng.lognormal(np.log(6), 0.7)))
                                ev.append(("SQL", ts))
                                ev += _post_sql(rng, ts, fit)
                if ev[-1][0] == "Won":
                    lv["mrr_cop"] = TICKET[size] * float(rng.lognormal(0, 0.25))
                elif rng.random() < LOST_P:
                    ev.append(("Lost", ev[-1][1] + pd.Timedelta(days=float(rng.lognormal(np.log(18), 0.6)))))
                ev = [(s, t) for s, t in ev if t <= as_of]
                leads.append(lv)
                events += [(lead_id, s, t) for s, t in ev]
    leads_df = pd.DataFrame(leads)
    events_df = pd.DataFrame(events, columns=["lead_id", "stage", "ts"])
    if target_ticket:
        leads_df["mrr_cop"] *= target_ticket / leads_df["mrr_cop"].mean()
    return leads_df, events_df


def _post_sql(rng, ts, fit):
    """Etapas de Account Executive. Estable en el tiempo (no hay problema plantado post-SQL)."""
    ev = []
    if rng.random() < 0.72:
        ts = ts + pd.Timedelta(days=float(rng.lognormal(np.log(5), 0.6)))
        ev.append(("Demo", ts))
        if rng.random() < 0.62:
            ts = ts + pd.Timedelta(days=float(rng.lognormal(np.log(7), 0.6)))
            ev.append(("Proposal", ts))
            if rng.random() < min(0.95, 0.48 * min(fit, 1.2)):
                ts = ts + pd.Timedelta(days=float(rng.lognormal(np.log(10), 0.6)))
                ev.append(("Won", ts))
    return ev
