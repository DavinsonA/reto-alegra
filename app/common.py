"""Piezas compartidas por las tres apps (historia, demo, tablero): datos agregados, constantes y navegación.

Las tres leen las mismas tablas de app/data/ (sin detalle por cliente), así que una cifra se corrige en un solo lugar.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import brand as B
from finora.funnel_synth import generate

DATA = Path(__file__).resolve().parent / "data"
WINDOW_START = "2022-04"
ACT, COR = "Modelo actual (caja)", "Corregido (N=2)"
SRC_TX = "Fuente: Transactions.csv (agregado) · corte oct-2024"
SRC_SYN = "Fuente: datos SINTÉTICOS generados con semilla fija · ilustran el diseño"

MOVES = ["new", "expansion", "price_uplift", "reactivation", "contraction", "churn"]
MOVE_LABELS = {"new": "Nuevos", "expansion": "Expansión (cliente)", "price_uplift": "Subida de precio (Finora)",
               "reactivation": "Reactivación", "contraction": "Contracción", "churn": "Churn"}
CUSTOMER_MOVES = ["new", "expansion", "reactivation", "contraction", "churn"]
N_TESTS = 48                     # pruebas automáticas del repositorio (pytest); actualizar si cambian

APPS = {"historia": "Historia ejecutiva", "demo": "Demo y proceso con IA", "tablero": "Tablero operativo"}
# Enlaces públicos de cada app: se llenan al publicar en Streamlit Community Cloud
LINKS = {"historia": "https://finora-historia.streamlit.app/", "demo": "https://finora-demo.streamlit.app/", "tablero": "https://finora-tablero.streamlit.app/"}


# ---------- datos ----------
@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv")


@st.cache_data
def synthetic():
    return generate()


def bridge_totals(scenario: str) -> pd.Series:
    b = load("bridge_monthly")
    b = b[(b["scenario"] == scenario) & (b["month"] >= WINDOW_START)]
    return b.groupby("movement")["amount_cop"].sum()


def mrr_series(scenario: str) -> pd.Series:
    b = load("bridge_monthly")
    return b[b["scenario"] == scenario].groupby("month")["mrr_close"].first()


def new_by_year() -> pd.DataFrame:
    nc = load("new_customers_monthly")
    nc = nc[nc["month"] >= WINDOW_START].assign(year=lambda d: d["month"].str[:4])
    g = nc.groupby("year").agg(n=("new_customers", "sum"), mrr=("new_mrr_cop", "sum"),
                               m3=("mrr_m3_sum_cop", "sum"), w=("with_m3", "sum"), months=("month", "nunique"))
    g["per_month"] = g["n"] / g["months"]
    g["mrr_per_month"] = g["mrr"] / g["months"]
    g["m3_ticket"] = g["m3"] / g["w"]
    return g


def nrr12(model: str, year: str) -> float:
    rc = load("retention_cohorts")
    r = rc[(rc["model"] == model) & (rc["cohort"].str.startswith(year)) & (rc["age"] == 12)
           & (rc["cohort"] >= "2022Q2")]                      # misma ventana que el resto: altas desde abr-2022
    return float(r["mrr_sum"].sum() / r["start_sum"].sum())     # ponderado por MRR inicial


def ticket_kitagawa(y0: str = "2022", y1: str = "2024") -> pd.DataFrame:
    """Descomposición mezcla/tasa del ticket de entrada por industria entre dos años (COP por cliente)."""
    nc = load("new_customers_monthly")
    nc = nc[nc["month"] >= WINDOW_START].assign(year=lambda d: d["month"].str[:4])
    g = nc.groupby(["year", "industry"]).agg(n=("new_customers", "sum"), mrr=("new_mrr_cop", "sum"))
    g["ticket"] = g["mrr"] / g["n"]
    share = g["n"] / g.groupby(level=0)["n"].transform("sum")
    w0, w1, r0, r1 = share.loc[y0], share.loc[y1], g["ticket"].loc[y0], g["ticket"].loc[y1]
    return pd.DataFrame({"ticket0": r0, "ticket1": r1, "mix": (w1 - w0) * (r0 + r1) / 2,
                         "rate": (r1 - r0) * (w0 + w1) / 2})


def half_cut() -> pd.DataFrame:
    return load("half_cut_monthly").query("month >= @WINDOW_START")


def delinquent_open_last() -> float:
    stt = load("status_monthly")
    return float(stt[(stt["month"] == stt["month"].max()) & (stt["status"] == "delinquent_open")]["mrr_cop"].sum())


def nonmrr_cash() -> pd.Series:
    nm = load("nonmrr_cash_monthly")
    return nm[nm["month"] >= WINDOW_START].groupby("extra_kind")["amount_cop"].sum().sort_values()


# ---------- página y navegación ----------
def page(app: str, sections: list[str], blurb: str) -> tuple[B.Theme, str]:
    """Configura la página con la marca y devuelve (tema, sección elegida). `?s=2` abre la sección 2."""
    st.set_page_config(page_title=f"Finora · {APPS[app]}", layout="wide")
    t = B.inject()
    B.identity()
    st.sidebar.caption(f"Reto Business Analytics · Finora  \n**{APPS[app]}** · {blurb}")
    if "sec" not in st.session_state:
        qs = st.query_params.get("s", "0")
        st.session_state["sec"] = sections[int(qs)] if qs.isdigit() and int(qs) < len(sections) else sections[0]
    section = st.sidebar.radio("Sección", sections, key="sec", label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption("Datos reales **agregados**, sin detalle por cliente. Montos en COP; 1 MM = 1 millón.")
    st.sidebar.caption("El funnel usa datos **sintéticos**, rotulados como tales.")
    others = [f"[{APPS[k]}]({LINKS[k]})" for k in APPS if k != app and LINKS[k]]
    if others:
        st.sidebar.caption("Otras vistas: " + " · ".join(others))
    return t, section


def link(app: str, label: str | None = None) -> str:
    """Enlace markdown a otra app; si aún no está publicada, solo el nombre."""
    return f"[{label or APPS[app]}]({LINKS[app]})" if LINKS[app] else f"**{label or APPS[app]}**"
