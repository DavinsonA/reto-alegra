"""Vistas para operar: revisión mensual del MRR (CFO) y semanal del funnel (CRO), en regla 3-30-300."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import brand as B
from common import COR, MOVES, SRC_SYN, SRC_TX, WINDOW_START
from common import load as _load
from common import synthetic as _synthetic
from finora import funnel as F
from finora.xmr import xmr

LABEL = {"new": "Nuevos", "expansion": "Expansión", "price_uplift": "Subida de precio", "reactivation": "Reactivación",
         "contraction": "Contracción", "churn": "Churn"}
OWNER = {"new": "Marketing y Ventas", "expansion": "CS", "reactivation": "CS y Cobranza", "contraction": "CS y Finanzas",
         "churn": "CS y Cobranza"}
ACTION = {
    "new": "revisar mezcla de canales y ticket de entrada del mes",
    "expansion": "identificar qué cuentas expandieron (uso o plan) y si es repetible",
    "reactivation": "confirmar si son retornos reales o pagos de mora tardíos",
    "contraction": "separar downgrade real de descuento; revisar las cuentas con mayor caída",
    "churn": "separar churn voluntario de mora no recuperada; contactar las cuentas grandes",
}


def _mes(m: str) -> str:
    y, mo = m.split("-")
    return f"{B.MESES[int(mo) - 1]} {y}"


def _status_chip(sig: dict, bad_when: str, unit: str = "meses") -> tuple[str, str | None]:
    """Texto y tipo de chip: el color expresa juicio (bueno/malo), la palabra dice qué pasó."""
    if not sig["signal"]:
        return "Dentro de lo normal", None
    up = sig["direction"] == "arriba"
    bad = (up and bad_when == "up") or (not up and bad_when == "down")
    if sig["reason"] == "8 puntos seguidos del mismo lado":
        text = f"Señal: 8 {unit} seguidos {'sobre' if up else 'bajo'} la media"
    elif sig["reason"] == "3 de 4 puntos cerca del límite":
        text = f"Señal: 3 de 4 {unit} cerca del límite {'alto' if up else 'bajo'}"
    else:
        text = f"Señal: {'por encima' if up else 'por debajo'} del rango normal"
    return text, ("down" if bad else "up")


def _status_line(parts: list[str], kind: str = "") -> None:
    st.markdown(f'<div class="da-status {kind}">{" · ".join(parts)}</div>', unsafe_allow_html=True)


def _footer(source: str) -> None:
    st.markdown(f'<div class="da-foot">{source}</div>', unsafe_allow_html=True)


def _rules_table(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Métrica", "Dueño", "Regla de alerta", "Acción"])


def _page_header(title: str, purpose: str, ratio: tuple[int, int] = (3, 1)):
    left, right = st.columns(list(ratio), vertical_alignment="bottom")
    left.header(title, anchor=False)
    left.caption(purpose)
    return right


def _band(fig: go.Figure, xs, x_: pd.DataFrame, scale: float = 1.0, mark=None, **kw) -> None:
    t = B.theme()
    fig.add_scatter(x=xs, y=x_["ucl"] * scale, mode="lines", line=dict(color=t.line_strong, width=1),
                    hoverinfo="skip", showlegend=False, **kw)
    fig.add_scatter(x=xs, y=x_["lcl"] * scale, mode="lines", line=dict(color=t.line_strong, width=1),
                    fill="tonexty", fillcolor=t.band, hoverinfo="skip", showlegend=False, **kw)
    fig.add_scatter(x=xs, y=x_["value"] * scale, mode=mark or "lines", line=dict(color=t.viz[0]),
                    marker=dict(size=6, color=t.viz[0], line=dict(color=t.surface, width=1.5)),
                    showlegend=False, hovertemplate="%{x}: %{y:.2f}<extra></extra>", **kw)
    flags = x_["signal"].fillna(False).astype(bool)
    if flags.any():
        fig.add_scatter(x=[x for x, f_ in zip(xs, flags) if f_], y=x_.loc[flags, "value"] * scale, mode="markers",
                        marker=dict(color=t.negative, size=8, symbol="diamond", line=dict(color=t.surface, width=1.5)),
                        showlegend=False, hovertemplate="Señal · %{x}: %{y:.2f}<extra></extra>", **kw)


# ---------------------------------------------------------------------------------------------------- mensual
def monthly_review(T: B.Theme, compact: bool = False) -> None:
    b = _load("bridge_monthly")
    b = b[b["scenario"] == COR]
    piv = b.pivot_table(index="month", columns="movement", values="amount_cop").reindex(columns=MOVES).fillna(0)
    mrr = b.groupby("month")["mrr_close"].first()
    cnt = _load("movement_counts_monthly")
    cnt = cnt[cnt["scenario"] == COR].pivot_table(index="month", columns="movement", values="customers").reindex(
        columns=MOVES).fillna(0)
    months = [m for m in piv.index if m >= WINDOW_START]
    N_GAP = 2
    pending_months = months[-N_GAP:]
    stt = _load("status_monthly")
    pend = stt[stt["status"] == "delinquent_open"].set_index("month")
    upl = _load("price_uplift_monthly")
    up_pend = upl[upl["uplift_conf"] == "pending"].set_index("month")
    nm = _load("nonmrr_cash_monthly")
    pp_pend = nm[nm["extra_kind"] == "prepaid_pending"].set_index("month")

    if compact:
        m = months[-1]
    else:
        filters = _page_header("Revisión mensual del MRR",
                               "Para: CFO y RevOps · Decide: si el cambio del mes es señal o ruido, y quién investiga · "
                               "Cadencia: mensual, en el cierre")
        m = filters.selectbox("Mes de cierre", months[::-1], format_func=_mes)
    pending = m in pending_months
    uplift_pending = m in up_pend.index
    i = months.index(m)
    prev, yago = (months[i - 1] if i > 0 else None), (months[i - 12] if i >= 12 else None)

    w = piv.loc[months]
    series = {
        "net": mrr.loc[months] - mrr.shift(1).loc[months],
        "new": w["new"], "expansion": w["expansion"], "reactivation": w["reactivation"],
        "contraction": -w["contraction"], "churn": (-w["churn"]).where(~w.index.isin(pending_months)),
        "new_count": cnt.reindex(months)["new"].fillna(0),
    }
    X = {k: xmr(v.dropna(), baseline=18).reindex(months) for k, v in series.items()}
    X["churn"]["signal"] = X["churn"]["signal"].fillna(False).astype(bool)

    def sig(k):
        return X[k].loc[m].to_dict()

    def vs(s):
        parts = []
        if prev is not None:
            parts.append(f"vs. {B.mm(s.loc[prev]) if abs(s.loc[prev]) > 1000 else B.es(s.loc[prev], 0)} en {_mes(prev)}")
        if yago is not None:
            parts.append(f"{B.mm(s.loc[yago]) if abs(s.loc[yago]) > 1000 else B.es(s.loc[yago], 0)} hace 12 meses")
        return " · ".join(parts)

    mrr_w = mrr.loc[months]
    mora = float(pend.loc[m, "mrr_cop"]) if m in pend.index else 0.0
    mora_n = int(pend.loc[m, "customers"]) if m in pend.index else 0
    mora_pct = mora / mrr_w.loc[m]
    flagged = [k for k in ["new", "expansion", "reactivation", "contraction", "churn"] if bool(X[k].loc[m, "signal"])]
    prior = months[max(0, i - 12):i]

    def avg12(k):
        ms = [p_ for p_ in prior if not (k == "churn" and p_ in pending_months)] or [m]
        return w.loc[ms, k].mean()

    react_high = "reactivation" not in flagged and w.loc[m, "reactivation"] > 2 * max(avg12("reactivation"), 1)
    owners = [OWNER[k] for k in flagged] + (["Cobranza"] if pending and mora > 0 else []) + (["CS y Cobranza"] if react_high else [])
    owners = list(dict.fromkeys(owners))

    if not compact:
        parts = [f"<b>{len(flagged)} {'señal' if len(flagged) == 1 else 'señales'}</b>" if flagged else "<b>Sin señales</b>: variación rutinaria"]
        if pending:
            parts.append(f"mora {B.pct(mora_pct, 1)} del MRR" + (" <b>(regla activa, más de 3 %)</b>" if mora_pct > 0.03 else ""))
        parts.append("dueños: " + ", ".join(owners) if owners else "nada que investigar este mes")
        _status_line(parts)

    chips = {k: _status_chip(sig(k), bad) for k, bad in [("net", "down"), ("new_count", "down")]}
    chips["churn"] = ("", None) if pending else _status_chip(sig("churn"), "up")
    items = [
        dict(overline=f"MRR de cierre · {_mes(m)}", value=B.mm(mrr_w.loc[m]), pastel=True,
             delta=(f"{'+' if mrr_w.loc[m] >= mrr.shift(1).loc[m] else ''}"
                    f"{B.es((mrr_w.loc[m] / mrr.shift(1).loc[m] - 1) * 100, 1)} % vs. mes anterior"),
             delta_kind="up" if mrr_w.loc[m] >= mrr.shift(1).loc[m] else "down", foot=vs(mrr_w)),
        dict(overline="MRR neto nuevo del mes", value=B.mm(series["net"].loc[m], sign=True),
             delta=chips["net"][0], delta_kind=chips["net"][1], foot=vs(series["net"])),
        (dict(overline="Churn del mes · en confirmación", value=B.mm(mora), delta=f"{mora_n} clientes en mora",
              foot=f"se confirma o se recupera en los próximos {N_GAP} meses")
         if pending else
         dict(overline="Churn del mes", value=B.mm(-series["churn"].loc[m]), delta=chips["churn"][0],
              delta_kind=chips["churn"][1], foot=f"{int(cnt.loc[m, 'churn'])} clientes · {vs(-series['churn'])}")),
        dict(overline="Clientes nuevos", value=B.es(series["new_count"].loc[m], 0), delta=chips["new_count"][0],
             delta_kind=chips["new_count"][1], foot=f"{B.mm(w.loc[m, 'new'])} de MRR nuevo · {vs(series['new_count'])}"),
    ]
    B.kpi_row(items[:3] if compact else items, compact=True)

    cust_moves = [("new", "Nuevos"), ("expansion", "Expans."), ("reactivation", "Reactiv."),
                  ("contraction", "Contrac."), ("churn", "Churn")]
    cust = sum(w.loc[m, k] for k, _ in cust_moves)
    price = w.loc[m, "price_uplift"]

    pos = w.loc[m, ["new", "expansion", "price_uplift", "reactivation"]]
    neg = w.loc[m, ["contraction", "churn"]]
    lines = [f"<b>Qué cambió:</b> el MRR {'subió' if series['net'].loc[m] >= 0 else 'bajó'} "
             f"{B.mm(abs(series['net'].loc[m]))} en {_mes(m)}: cliente {B.mm(cust, sign=True)}, pricing {B.mm(price, sign=True)}, "
             f"descuentos sin dato. Lo que más sumó: {LABEL[pos.idxmax()].lower()} ({B.mm(pos.max(), sign=True)}); lo que más "
             f"restó: {LABEL[neg.idxmin()].lower()} ({B.mm(neg.min())})."]
    conf = []
    if pending:
        conf.append(f"{B.mm(mora)} de MRR está en mora sin confirmar ({mora_n} clientes); se conoce en {N_GAP} cierres")
    if uplift_pending:
        conf.append(f"subidas de precio por {B.mm(up_pend.loc[m, 'amount_cop'])} en {int(up_pend.loc[m, 'events'])} clientes, "
                    "si el alza se mantiene el mes siguiente")
    if m in pp_pend.index:
        conf.append(f"{B.mm(pp_pend.loc[m, 'amount_cop'])} de caja en {int(pp_pend.loc[m, 'events'])} pagos grandes que pueden "
                    "ser prepagos")
    if conf:
        lines.append("<b>En confirmación:</b> " + "; ".join(conf) + ". <b>Qué hacemos:</b> Cobranza gestiona la mora antes "
                     "de que se confirme como churn.")
    acts = []
    for k in flagged:
        r_ = X[k].loc[m]
        acts.append(f"<b>{LABEL[k]}:</b> {r_['reason']}, {r_['direction']} de lo normal (rango {B.mm(r_['lcl'])} a "
                    f"{B.mm(r_['ucl'])}). {OWNER[k]}: {ACTION[k]}.")
    if react_high:
        acts.append(f"<b>Reactivación alta:</b> {B.mm(w.loc[m, 'reactivation'])} en {int(cnt.loc[m, 'reactivation'])} clientes "
                    f"(promedio de 12 meses: {B.mm(avg12('reactivation'))}). {OWNER['reactivation']}: {ACTION['reactivation']}.")
    lines.append(("<b>Señales y acción:</b> " + " ".join(acts)) if acts else
                 "<b>Señales:</b> ningún movimiento salió de su rango normal; es variación rutinaria. Nada que investigar.")

    x, base, y, color, text = [], [], [], [], []
    cum, ghost = 0.0, None
    for k, lab in cust_moves:
        v = w.loc[m, k] / 1e6
        if k == "churn" and pending:
            ghost = (len(x), cum, mora / 1e6)
            x.append(lab); base.append(cum); y.append(0.0); color.append(T.viz[2]); text.append("")
            continue
        x.append(lab); base.append(cum); y.append(v); color.append(T.viz[0] if v >= 0 else T.viz[2])
        text.append(B.es(v, 2)); cum += v
    x.append("Cliente"); base.append(0.0); y.append(cum); color.append(T.line_strong); text.append(B.es(cum, 2))
    x.append("Precio"); base.append(cum); y.append(price / 1e6); color.append(T.viz[1]); text.append(B.es(price / 1e6, 2))
    price_top = cum + max(price / 1e6, 0)
    cum += price / 1e6
    x.append("Neto"); base.append(0.0); y.append(cum); color.append(T.line_strong); text.append(B.es(cum, 2))
    fig = go.Figure(go.Bar(x=x, y=y, base=base, marker_color=color, text=text, textposition="outside",
                           textfont=dict(family=B.FONT_MONO, size=11, color=T.ink), cliponaxis=False,
                           hovertemplate="%{x}: %{y:.2f} MM<extra></extra>"))
    if ghost:
        j, top, pv = ghost
        fig.add_shape(type="rect", x0=j - 0.4, x1=j + 0.4, y0=top - pv, y1=top,
                      line=dict(color=T.viz[2], width=1.5, dash="dot"), fillcolor="rgba(0,0,0,0)")
        fig.add_annotation(x=j, y=top - pv, yshift=-14, showarrow=False, text=f"en confirmación<br>{B.es(pv, 1)} en mora",
                           font=dict(family=B.FONT_MONO, size=10, color=T.muted))
    if uplift_pending:
        fig.add_annotation(x=x.index("Precio"), y=price_top, yshift=26, showarrow=False, text="en confirmación",
                           font=dict(family=B.FONT_MONO, size=10, color=T.muted))
    fig.update_xaxes(tickangle=0)
    rows = []
    for k in MOVES:
        n = int(cnt.loc[m, k]) if m in cnt.index else 0
        if k == "churn" and pending:
            rows.append((LABEL[k], "en confirmación", f"{mora_n} en mora", B.es(avg12(k) / 1e6, 2)))
        elif k == "price_uplift" and uplift_pending:
            rows.append((LABEL[k], f"{B.es(w.loc[m, k] / 1e6, 2)} · en confirmación", B.es(n, 0), B.es(avg12(k) / 1e6, 2)))
        else:
            rows.append((LABEL[k], B.es(w.loc[m, k] / 1e6, 2), B.es(n, 0), B.es(avg12(k) / 1e6, 2)))
    tbl = pd.DataFrame(rows, columns=["Movimiento", "MM COP", "Clientes", "Promedio 12 m (MM)"])

    c1, c2 = (st.container(), st.container()) if compact else st.columns([7, 5], gap="medium")
    with c1:
        B.chart_frame(f"bridge_{m}", "",
                      f"De {B.mm(mrr.shift(1).loc[m])} a {B.mm(mrr_w.loc[m])}: cliente {B.mm(cust, sign=True)}, "
                      f"pricing {B.mm(price, sign=True)}, descuentos sin dato",
                      "Millones de COP · verde azulado = cliente suma, durazno = resta, violeta = pricing, gris = subtotal y "
                      "neto" + (" · churn punteado = en confirmación" if pending else ""),
                      fig, tbl, None, 300, ysuffix=" MM", month_ticks=False)
    with c2:
        B.callout("".join(f"<p>{x_}</p>" for x_ in lines), cols=2 if compact else 1)
    if compact:
        return

    with st.expander("Señal o ruido por movimiento · 4 gráficos XmR"):
        st.markdown('<div class="da-sub">Banda = rango normal (media ± 2,66 × rango móvil, fijado con los primeros 18 meses) · '
                    'rombo = señal · círculo = churn en confirmación · contracción y churn en positivo</div>',
                    unsafe_allow_html=True)
        cols = st.columns(4, gap="small")
        for j, (k, bad) in enumerate([("new", "down"), ("expansion", "down"), ("contraction", "up"), ("churn", "up")]):
            x_ = X[k]
            f = go.Figure()
            _band(f, months, x_, 1 / 1e6)
            if k == "churn":
                pm = [p_ for p_ in pending_months if p_ in pend.index]
                f.add_scatter(x=pm, y=[pend.loc[p_, "mrr_cop"] / 1e6 for p_ in pm], mode="markers",
                              marker=dict(color=T.surface, size=8, symbol="circle", line=dict(color=T.viz[2], width=2)),
                              showlegend=False, hovertemplate="En confirmación · %{x}: %{y:.2f} MM en mora<extra></extra>")
            f.add_vline(x=m, line_color=T.ink, line_width=1, opacity=0.35)
            state = "En confirmación" if (k == "churn" and pending) else _status_chip(sig(k), bad)[0]
            with cols[j]:
                B.chart_frame(f"xmr_{k}", "", LABEL[k], f"{state} · MM COP por mes", f, None, None, 200,
                              ysuffix=" MM", month_ticks="year", plain=True)

    with st.expander("Eficiencia del S&M · CAC variable y magic number"):
        st.markdown('<div class="da-sub">Cuánto ingreso nuevo compra cada peso de Sales & Marketing · unidades del enunciado, '
                    'pendientes de confirmar con Finanzas · fuente: S&M_spend.csv</div>', unsafe_allow_html=True)
        sm = _load("sm_monthly").set_index("month")
        eff = _load("sm_efficiency_quarterly")
        eff = eff[eff["complete"] & (eff["quarter"] >= "2022Q2")]
        var = sm[["PaidMedia", "PublicidadNoWeb", "Freelance", "Travel"]].sum(axis=1).reindex(months)
        cac3 = (var.rolling(3).sum() / series["new_count"].rolling(3).sum()).dropna()
        Xc = xmr(cac3, baseline=18).reindex(months)
        e1, e2 = st.columns(2, gap="small")
        with e1:
            f = go.Figure()
            _band(f, months, Xc, 1 / 1e6)
            f.add_vline(x=m, line_color=T.ink, line_width=1, opacity=0.35)
            state_c = _status_chip(Xc.loc[m].to_dict(), "up")[0] if pd.notna(Xc.loc[m, "value"]) else "Sin dato"
            B.chart_frame("cac_var", "", "CAC variable, 3 meses móviles",
                          f"{state_c} · MM por cliente nuevo · solo rubros de adquisición", f,
                          Xc.assign(month=months)[["month", "value", "center", "lcl", "ucl", "signal"]], None, 220,
                          ysuffix=" MM", month_ticks="year", plain=True)
        with e2:
            f = go.Figure(go.Bar(x=[B.quarter_label(q) for q in eff["quarter"]], y=eff["magic_number"], marker_color=T.viz[0],
                                 hovertemplate="%{x}: %{y:.2f}<extra></extra>"))
            f.add_hline(y=0.75, line_color=T.ink, line_width=1)
            f.add_hline(y=0.5, line_color=T.line_strong, line_width=1, line_dash="dot")
            last_q = eff.iloc[-1]
            B.chart_frame("magic_q", "", "Magic number, trimestre cerrado",
                          f"{B.es(last_q['magic_number'], 2)} en {B.quarter_label(last_q['quarter']).replace('<br>', ' ')} · "
                          "líneas: 0,75 escalar · 0,5 revisar", f, eff[["quarter", "magic_number"]].round(2), None, 220,
                          month_ticks=False, plain=True)

    with st.expander("Dueños, reglas de alerta y acciones"):
        B.text_frame("rules_cfo", "", "Cada métrica tiene dueño, regla de alerta y acción",
                     "Se revisa en el cierre mensual; si no hay señal, se dice «nada que investigar» y se sigue",
                     _rules_table([
                         ("MRR nuevo", "Marketing + Ventas", "Señal abajo o 3 meses bajo la línea central",
                          "Revisar mezcla de canal y ticket de entrada"),
                         ("Expansión", "Customer Success", "Señal abajo", "Revisar adopción y upgrades; campañas de expansión"),
                         ("Reactivación", "CS + Cobranza", "Más del doble del promedio de 12 meses",
                          "Confirmar si son retornos reales o pagos de mora tardíos"),
                         ("Contracción", "CS + Finanzas", "Señal arriba", "Separar downgrade de descuento; revisar cuentas grandes"),
                         ("Churn", "CS + Cobranza", "Señal arriba", "Separar voluntario de mora; plan de recuperación"),
                         ("MRR en mora", "Cobranza", "Más de 3 % del MRR", "Gestión de cobro antes de confirmar churn (N = 2 meses)"),
                         ("Descuentos (nuevo)", "Finanzas + Deal desk", "Price realization < 95 %",
                          "Revisar aprobaciones y vencimientos"),
                         ("Eficiencia del S&M (nuevo)", "CFO + CRO", "Magic number < 0,5 dos trimestres seguidos, o CAC variable en señal arriba",
                          "No escalar canales; revisar mezcla de gasto y confirmar unidades"),
                     ]))
    _footer(f"{SRC_TX} · Señal = XmR (Wheeler): punto fuera de los límites, 8 seguidos del mismo lado o 3 de 4 cerca de un "
            "límite; los meses en confirmación no entran en los límites")


# ---------------------------------------------------------------------------------------------------- semanal
METRICS = [
    ("leads", "Leads nuevos", "Volumen", "", 1, None),
    ("high_fit", "Mezcla de alto ajuste (pequeña y mediana)", "Entrada controlable", " %", 100, "down"),
    ("speed_p50", "Speed-to-lead P50", "Entrada controlable", " h", 1, "up"),
    ("sla_1h", "Leads contactados en menos de 1 hora", "Entrada controlable", " %", 100, "down"),
    ("work_to_eng", "Working a Engaged en 30 días", "Entrada controlable", " %", 100, "down"),
    ("sql_to_won", "SQL a Won en 60 días", "Entrada controlable", " %", 100, "down"),
    ("new_customers", "Clientes nuevos", "Salida", "", 1, "down"),
    ("new_mrr", "MRR nuevo", "Salida", " MM", 1e-6, "down"),
]
SHORT = {"high_fit": "Mezcla de alto ajuste", "sla_1h": "Contactados en < 1 hora", "work_to_eng": "Working a Engaged",
         "sql_to_won": "SQL a Won", "speed_p50": "Speed-to-lead P50"}
GRID = ["speed_p50", "sla_1h", "work_to_eng", "sql_to_won"]


def _fmt(v, suffix, scale):
    if pd.isna(v):
        return "en maduración"
    d = 1 if suffix in (" %", " h", " MM") else 0
    return f"{B.es(v * scale, d)}{suffix.replace(' ', chr(160))}"


def _mini612(T: B.Theme, k: str, wk: pd.DataFrame, mo: pd.DataFrame, suf: str, sc: float) -> go.Figure:
    xw, xm = xmr(wk[k].dropna(), baseline=26), xmr(mo[k].dropna(), baseline=12)
    last6, last12 = xw.tail(6), xm.tail(12)
    f = make_subplots(rows=1, cols=2, column_widths=[0.4, 0.6], shared_yaxes=suf in (" %", " h"),
                      horizontal_spacing=0.08, subplot_titles=("6 semanas", "12 meses"))
    for col_, xx in ((1, last6), (2, last12)):
        _band(f, list(xx.index), xx, sc, mark="lines+markers", row=1, col=col_)
    ends6 = [last6.index[-1]]
    ends12 = [last12.index[j] for j in (len(last12) // 2, len(last12) - 1)]
    f.update_xaxes(tickvals=ends6, ticktext=[f"{d.day} {B.MESES[d.month - 1]}" for d in ends6], row=1, col=1, tickangle=0)
    f.update_xaxes(tickvals=ends12, ticktext=[B.MESES[d.month - 1] for d in ends12], row=1, col=2, tickangle=0)
    f.update_annotations(font=dict(family=B.FONT_SANS, size=11, color=T.muted))
    if suf not in (" %", " h"):
        f.update_yaxes(side="right", row=1, col=2)
    return f


def weekly_review(T: B.Theme, channel_colors: dict, compact: bool = False) -> None:
    if not compact:
        _page_header("Revisión semanal del funnel",
                     "Para: CRO, líderes SDR y AE · Decide: qué entrada se salió de lo normal y quién actúa · "
                     "Cadencia: semanal, 30 minutos · formato fijo 6-12 (6 semanas | 12 meses)", ratio=(5, 1))
    leads, ev = _synthetic()
    as_of = pd.Timestamp("2024-10-31")
    r = F.reach_table(leads, ev)
    wk = F.period_metrics(r, as_of, "W")
    mo = F.period_metrics(r, as_of, "M")
    week = wk.index[-1]

    state = {}
    for k, name_, kind, suf, sc, bad in METRICS:
        s = wk[k].dropna()
        x_ = xmr(s, baseline=26)
        last = x_.iloc[-1]
        state[k] = dict(value=s.iloc[-1], when=s.index[-1], center=last["center"], signal=bool(last["signal"]),
                        direction=last["direction"], reason=last["reason"], bad=bad)
    name = {k: n for k, n, *_ in METRICS}
    meta = {k: (suf, sc) for k, _, _, suf, sc, _ in METRICS}
    sig_k = [k for k, *_ in METRICS if state[k]["signal"]]
    pre = ["high_fit", "speed_p50", "sla_1h", "work_to_eng"]
    hot = [k for k in pre if state[k]["signal"]]
    stl = F.stalled(r, ev, as_of)
    by_owner = stl.pivot_table(index="owner", columns="stage", values="lead_id", aggfunc="count", fill_value=0)
    by_owner["Total"] = by_owner.sum(axis=1)
    rw = r[r["path"] == "sdr_full"].assign(cohort=lambda d: d["created_at"].dt.to_period("W"))
    mature = sorted(c for c in rw["cohort"].unique() if c.end_time + pd.Timedelta(days=30) <= as_of)
    kt = F.kitagawa(rw, "New", "Engaged", 30, mature[-18:-6], mature[-6:])
    mix_pp, rate_pp = kt["mix_effect"].sum() * 100, kt["rate_effect"].sum() * 100

    _status_line(["<b>Datos sintéticos</b>: prototipo del formato con dos problemas plantados, no hallazgos de Finora"], "warn")
    if hot and not state["sql_to_won"]["signal"]:
        resumen = f"<b>{len(hot)} entradas en señal</b>, todas antes de SQL · post-SQL normal"
    elif state["sql_to_won"]["signal"]:
        resumen = "<b>Post-SQL en señal</b>: revisar los deals de Demo y Proposal con el líder AE"
    else:
        resumen = "<b>Sin señales</b>: nada que ver aquí"
    _status_line([f"Semana del {week.day} de {B.MESES[week.month - 1]} de {week.year}", resumen,
                  f"{B.es(len(stl), 0)} leads estancados"])

    def chip(k):
        return _status_chip(state[k], state[k]["bad"], unit="semanas")

    kpis = []
    for k, pastel in (("leads", False), ("high_fit", False), ("new_customers", False), ("new_mrr", True)):
        c_ = chip(k)
        kpis.append(dict(overline=name[k], value=_fmt(state[k]["value"], *meta[k]), delta=c_[0], delta_kind=c_[1],
                         foot=f"lo normal: {_fmt(state[k]['center'], *meta[k])} · semanal", pastel=pastel))
    B.kpi_row(kpis[:3] if compact else kpis, compact=True)

    def word(k):
        st_ = state[k]
        return "normal" if not st_["signal"] else ("SEÑAL ▲" if st_["direction"] == "arriba" else "SEÑAL ▼")

    def node(k, label=None):
        st_ = state[k]
        color = T.line_strong if not st_["signal"] else T.negative
        return (f'{k} [label="{label or SHORT.get(k, name[k])}\\n{_fmt(st_["value"], *meta[k])}\\n{word(k)}", color="{color}", '
                f'penwidth={2 if st_["signal"] else 1}];')

    lead = "tasa" if abs(rate_pp) >= abs(mix_pp) else "mezcla"
    parts = []
    if sig_k:
        parts.append("<p><b>Qué cambió:</b></p><ul>" + "".join(
            f"<li>{SHORT.get(k, name[k])}: {_fmt(state[k]['value'], *meta[k])} (lo normal, "
            f"{_fmt(state[k]['center'], *meta[k])}) · {state[k]['reason']}</li>" for k in sig_k) + "</ul>")
    else:
        parts.append("<p><b>Qué cambió:</b> ninguna entrada salió de su rango normal.</p>")
    parts.append(f"<p><b>Por qué:</b> New a Engaged (SDR) movió {B.es(mix_pp + rate_pp, 1)} pp en 6 semanas frente a las 12 "
                 f"previas, {B.es(mix_pp, 1)} por mezcla de canal y {B.es(rate_pp, 1)} por tasa: casi todo es {lead}. ")
    if "speed_p50" in sig_k and "sql_to_won" not in sig_k:
        parts[-1] += ("El volumen subió y el primer contacto se demoró; la conversión cae antes de SQL mientras post-SQL "
                      "sigue estable. Apunta a <b>capacidad SDR</b>, no al AE.</p>"
                      "<p><b>Qué hacemos:</b> ruteo y primer contacto automático para leads de bajo ajuste, SLA de 1 hora "
                      "para los de alto ajuste, y revisar la meta de Paid Social por SQL, no por leads.</p>")
    else:
        parts[-1] += "</p><p><b>Qué hacemos:</b> cada dueño revisa su entrada; sin señal, nada que ver aquí.</p>"

    c1, c2 = (st.container(), st.container()) if compact else st.columns([7, 5], gap="medium")
    with c1:
        with st.container(border=True, key="frame_tree"):
            st.markdown('<div class="da-h3">De las entradas que el equipo controla al MRR nuevo</div><div class="da-sub">'
                        'Última semana con dato · en rojo, lo que salió de su rango normal (XmR)</div>', unsafe_allow_html=True)
            st.graphviz_chart(f"""
            digraph G {{ rankdir=LR; bgcolor="transparent"; nodesep=0.25; ranksep=0.6;
              node [shape=box, style=rounded, fontname="IBM Plex Sans", fontsize=11, fontcolor="{T.ink}", color="{T.line_strong}"];
              edge [color="{T.muted}", arrowsize=0.6];
              {node("new_mrr", "MRR nuevo (salida)")} {node("new_customers")}
              tk [label="Ticket de entrada\\n{B.es(wk['ticket'].dropna().iloc[-1] / 1e3, 0)} mil COP"];
              {node("leads")}
              conv [label="Conversión New a Won\\npor camino"];
              {node("speed_p50")} {node("sla_1h")} {node("high_fit", "Mezcla de alto ajuste")} {node("work_to_eng")} {node("sql_to_won")}
              new_customers -> new_mrr; tk -> new_mrr; leads -> new_customers; conv -> new_customers;
              speed_p50 -> conv; sla_1h -> conv; high_fit -> conv; work_to_eng -> conv; sql_to_won -> conv;
            }}""")
    with c2:
        B.callout("".join(parts), cols=2 if compact else 1)
    if compact:
        return

    st.markdown('<div class="da-h3" style="margin-top:8px">Formato 6-12 · las cuatro entradas que el equipo controla</div>'
                '<div class="da-sub">Siempre las mismas, en el mismo orden: 6 semanas a la izquierda, 12 meses a la derecha · '
                'banda = rango normal · rombo = señal · las tasas esperan su ventana de maduración (30 o 60 días)</div>',
                unsafe_allow_html=True)
    cols = st.columns(4, gap="small")
    for col, k in zip(cols, GRID):
        suf, sc = meta[k]
        st_ = state[k]
        status = "Normal" if not st_["signal"] else f"Señal {'▲' if st_['direction'] == 'arriba' else '▼'}"
        with col:
            B.chart_frame(f"612_{k}", "", SHORT.get(k, name[k]),
                          f"{status} · última: {_fmt(st_['value'], suf, sc)} · normal: {_fmt(st_['center'], suf, sc)}",
                          _mini612(T, k, wk, mo, suf, sc), None, None, 190, ysuffix=suf, month_ticks=False, plain=True)

    c3, c4 = st.columns([5, 7], gap="medium")
    with c3:
        B.table_frame("stalled", "", f"{B.es(len(stl), 0)} leads abiertos superan el P90 histórico de su etapa y camino",
                      "Los 5 dueños con más leads estancados · P90 = lo que tardan en avanzar los leads que sí avanzan",
                      by_owner.sort_values("Total", ascending=False).head(5).reset_index(names="Dueño"))
        with st.expander("Todos los dueños"):
            st.dataframe(by_owner.sort_values("Total", ascending=False).reset_index(names="Dueño"), hide_index=True,
                         width="stretch")
    with c4:
        with st.expander("Dueños, reglas de alerta y acciones"):
            B.text_frame("rules_cro", "", "Cada entrada tiene dueño, regla de alerta y acción",
                         "Se revisa cada semana en el mismo formato; sin señal, «nada que ver aquí»", _rules_table([
                             ("Speed-to-lead P50 y SLA de 1 hora", "Líder SDR", "Señal arriba en P50, o SLA < 60 %",
                              "Ruteo automático, primer contacto con IA, ajustar capacidad"),
                             ("Mezcla de alto ajuste", "Marketing", "Señal abajo",
                              "Revisar segmentación y metas por canal (SQL, no leads)"),
                             ("Working a Engaged", "Líder SDR", "Señal abajo", "Cruzar con speed-to-lead dentro del canal; coaching"),
                             ("SQL a Won", "Líder AE", "Señal abajo", "Revisión de deals en Demo y Proposal; criterios de SQL"),
                             ("Clientes nuevos y MRR nuevo", "CRO", "Señal abajo", "Descomponer por entrada antes de actuar"),
                         ]))
        with st.expander("Volumen y salida en formato 6-12 · leads, mezcla y clientes nuevos"):
            cols2 = st.columns(3, gap="small")
            for col, k in zip(cols2, ["leads", "high_fit", "new_customers"]):
                suf, sc = meta[k]
                with col:
                    B.chart_frame(f"612_{k}", "", SHORT.get(k, name[k]), f"última: {_fmt(state[k]['value'], suf, sc)}",
                                  _mini612(T, k, wk, mo, suf, sc), None, None, 170, ysuffix=suf, month_ticks=False, plain=True)
        with st.expander("Mezcla frente a tasa por canal · New a Engaged (SDR)"):
            st.dataframe((kt * 100).round(2).reset_index(names="Canal"), hide_index=True, width="stretch")
    _footer(f"{SRC_SYN} · Señal = XmR (Wheeler) con línea base de 26 semanas")
