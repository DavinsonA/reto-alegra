"""Piezas compartidas por las tres apps (historia, demo, tablero): datos agregados, constantes y navegación."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import brand as B
from finora.figures import load_figures
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

FIGURES = load_figures(DATA / "key_figures.csv")
N_TESTS = FIGURES["n_pruebas"]

APPS = {"historia": "Historia ejecutiva", "demo": "Demo y proceso con IA", "tablero": "Tablero operativo"}
REPO = "https://github.com/DavinsonA/reto-alegra/blob/main"
LINKS = {"historia": "https://finora-historia.streamlit.app/", "demo": "https://finora-demo.streamlit.app/", "tablero": "https://finora-tablero.streamlit.app/"}


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv")


def fig_num(name: str) -> float:
    """Valor numérico de una cifra clave (vienen formateadas en español: 44.348 · −18,0)."""
    return float(FIGURES[name].replace(".", "").replace(",", ".").replace("−", "-"))


@st.cache_data
def synthetic():
    return generate(target_ticket=fig_num("ticket_2024"))


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
           & (rc["cohort"] >= "2022Q2")]
    return float(r["mrr_sum"].sum() / r["start_sum"].sum())


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


SENS_COLS = {"new_cop": "Nuevos", "expansion_cop": "Expansión", "price_uplift_cop": "Precio",
             "reactivation_cop": "Reactivación", "contraction_cop": "Contracción", "churn_cop": "Churn"}


def rule_sensitivity() -> tuple[pd.DataFrame, bool]:
    """Sensibilidad una regla a la vez (MM COP y NRR %) y si alguna variante cambia el signo o el orden de magnitud."""
    s = load("rule_sensitivity")
    cor = s[s["escenario"] != "Modelo actual (caja)"]
    base = cor.iloc[0]
    stable = True
    for c in SENS_COLS:
        if c == "price_uplift_cop":
            continue
        ratio = cor[c] / base[c]
        stable &= bool(((ratio > 0) & (ratio.abs().between(0.1, 10))).all())
    view = s[["escenario", "ajuste", *SENS_COLS]].rename(columns={"escenario": "Escenario", "ajuste": "Ajuste", **SENS_COLS})
    for c in SENS_COLS.values():
        view[c] = (view[c] / 1e6).map(lambda v: B.es(v, 1))
    view["NRR 12 m, altas 2023"] = (s["nrr12_2023"] * 100).map(lambda v: f"{B.es(v, 1)} %")
    return view, stable


SENS_NUM = (*SENS_COLS.values(), "NRR 12 m, altas 2023")


def half_cut() -> pd.DataFrame:
    return load("half_cut_monthly").query("month >= @WINDOW_START")


def delinquent_open_last() -> float:
    stt = load("status_monthly")
    return float(stt[(stt["month"] == stt["month"].max()) & (stt["status"] == "delinquent_open")]["mrr_cop"].sum())


def nonmrr_cash() -> pd.Series:
    nm = load("nonmrr_cash_monthly")
    return nm[nm["month"] >= WINDOW_START].groupby("extra_kind")["amount_cop"].sum().sort_values()


_BI_CSS = """<style>
.block-container { max-width:none !important; padding:0.75rem 2rem 2rem !important; }
.da-bar-name { font:600 20px/26px var(--font-display); color:var(--ink); }
.da-bar-sub, .da-bar-meta { font:400 13px/20px var(--font-sans); color:var(--ink-muted); }
.da-bar-meta { text-align:right; }
.da-bar-rule { border-top:1px solid var(--line-strong); margin:4px 0 16px; }
.stApp { background-image:none !important; }
.da-status { font:500 15px/24px var(--font-sans); color:var(--ink); margin:-4px 0 12px; padding:6px 12px; border-left:3px solid var(--line-strong); }
.da-status.warn { border-left-color:var(--warning); background:var(--warning-soft); }
.da-foot { font:400 12px/16px var(--font-mono); color:var(--ink-muted); margin:20px 0 0; border-top:1px solid var(--line); padding-top:8px; }
[class*="st-key-mini"] { border-top:1px solid var(--line-strong); padding:8px 0 0; }
</style>"""


def _keep_section(sections: list[str]) -> None:
    """El selector de páginas no queda vacío si se vuelve a hacer clic en la página activa."""
    if st.session_state.get("sec") is None:
        st.session_state["sec"] = st.session_state.get("sec_last", sections[0])


def page(app: str, sections: list[str], blurb: str, top_nav: bool = False) -> tuple[B.Theme, str]:
    """Configura la página con la marca y devuelve (tema, sección elegida)."""
    st.set_page_config(page_title=f"Finora · {APPS[app]}", layout="wide",
                       initial_sidebar_state="collapsed" if top_nav else "auto")
    t = B.inject()
    B.identity()
    st.sidebar.caption(f"Reto Business Analytics · Finora  \n**{APPS[app]}** · {blurb}")
    if "sec" not in st.session_state:
        qs = st.query_params.get("s", "0")
        st.session_state["sec"] = sections[int(qs)] if qs.isdigit() and int(qs) < len(sections) else sections[0]
    if top_nav:
        st.markdown(_BI_CSS, unsafe_allow_html=True)
        c1, c2, c3 = st.columns([3, 4, 3], vertical_alignment="center")
        c1.markdown(f'<div class="da-bar-name">Finora · {APPS[app]}</div>'
                    f'<div class="da-bar-sub">Davinson Arteaga · {blurb}</div>', unsafe_allow_html=True)
        with c2:
            section = st.segmented_control("Página", sections, key="sec", label_visibility="collapsed",
                                           on_change=_keep_section, args=(sections,))
        others = " · ".join(f'<a href="{LINKS[k]}">{APPS[k]}</a>' for k in APPS if k != app)
        c3.markdown(f'<div class="da-bar-meta">Datos reales agregados · corte oct-2024<br>{others}</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="da-bar-rule"></div>', unsafe_allow_html=True)
        section = section or st.session_state.get("sec_last", sections[0])
        st.session_state["sec_last"] = section
    else:
        section = st.sidebar.radio("Sección", sections, key="sec", label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption("Datos reales **agregados**, sin detalle por cliente. Montos en COP; 1 MM = 1 millón.")
    st.sidebar.caption("El funnel usa datos **sintéticos**, rotulados como tales.")
    st.sidebar.caption("Otras vistas: " + " · ".join(f"[{APPS[k]}]({LINKS[k]})" for k in APPS if k != app))
    return t, section
