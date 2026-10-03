"""Vistas para OPERAR (no solo para explicar): revisión mensual del MRR (CFO) y semanal del funnel (CRO)."""
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


def _mes(m: str) -> str:
    y, mo = m.split("-")
    return f"{B.MESES[int(mo) - 1]} {y}"


def _status_chip(sig: dict, bad_when: str) -> tuple[str, str | None]:
    """Texto y tipo de chip: el color expresa juicio (bueno/malo), la palabra dice qué pasó."""
    if not sig["signal"]:
        return "Dentro de lo normal", None
    up = sig["direction"] == "arriba"
    bad = (up and bad_when == "up") or (not up and bad_when == "down")
    if sig["reason"] == "8 puntos seguidos del mismo lado":
        text = f"Señal: 8 meses seguidos {'sobre' if up else 'bajo'} la media"
    elif sig["reason"] == "3 de 4 puntos cerca del límite":
        text = f"Señal: 3 de 4 meses cerca del límite {'alto' if up else 'bajo'}"
    else:
        text = f"Señal: {'por encima' if up else 'por debajo'} del rango normal"
    return text, ("down" if bad else "up")


def _rules_table(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Métrica", "Dueño", "Regla de alerta", "Acción"])


def _page_header(title: str, purpose: str, ratio: tuple[int, int] = (3, 1)):
    """Encabezado de página tipo BI: título y propósito a la izquierda; devuelve la columna derecha (filtros)."""
    left, right = st.columns(list(ratio), vertical_alignment="bottom")
    left.header(title, anchor=False)
    left.caption(purpose)
    return right


def monthly_review(T: B.Theme) -> None:
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
    chips = {k: _status_chip(sig(k), bad) for k, bad in [("net", "down"), ("new_count", "down")]}
    chips["churn"] = ("", None) if pending else _status_chip(sig("churn"), "up")
    new_foot = f"{B.mm(w.loc[m, 'new'])} de MRR nuevo · {vs(series['new_count'])}"
    if (sig("new_count")["reason"] == "8 puntos seguidos del mismo lado" and yago is not None
            and series["new_count"].loc[yago] > series["new_count"].loc[m]):
        new_foot += " · la señal es la racha, no el nivel: hace 12 meses fue un pico aislado"
    B.kpi_row([
        dict(overline=f"MRR de cierre · {_mes(m)}", value=B.mm(mrr_w.loc[m]), pastel=True,
             delta=(f"{'+' if mrr_w.loc[m] >= mrr.shift(1).loc[m] else ''}"
                    f"{B.es((mrr_w.loc[m] / mrr.shift(1).loc[m] - 1) * 100, 1)} % vs. mes anterior"),
             delta_kind="up" if mrr_w.loc[m] >= mrr.shift(1).loc[m] else "down",
             foot=vs(mrr_w)),
        dict(overline="MRR neto nuevo del mes", value=B.mm(series["net"].loc[m], sign=True),
             delta=chips["net"][0], delta_kind=chips["net"][1], foot=vs(series["net"])),
        (dict(overline="Churn del mes · en confirmación", value=B.mm(pend.loc[m, "mrr_cop"] if m in pend.index else 0),
              delta=f"{int(pend.loc[m, 'customers']) if m in pend.index else 0} clientes en mora",
              foot=f"MRR en mora: se confirma como churn o se recupera en los próximos {N_GAP} meses")
         if pending else
         dict(overline="Churn del mes", value=B.mm(-series["churn"].loc[m]),
              delta=chips["churn"][0], delta_kind=chips["churn"][1],
              foot=f"{int(cnt.loc[m, 'churn'])} clientes · {vs(-series['churn'])}")),
        dict(overline="Clientes nuevos", value=B.es(series["new_count"].loc[m], 0),
             delta=chips["new_count"][0], delta_kind=chips["new_count"][1], foot=new_foot),
    ], compact=True)

    cust_moves = [("new", "Nuevos"), ("expansion", "Expans."), ("reactivation", "Reactiv."),
                  ("contraction", "Contrac."), ("churn", "Churn")]
    cust = sum(w.loc[m, k] for k, _ in cust_moves)
    price = w.loc[m, "price_uplift"]
    reading = st.container()
    c1, c2 = st.columns([7, 5], gap="medium")
    with c1:
        x, base, y, color, text = [], [], [], [], []
        cum, ghost = 0.0, None
        for k, lab in cust_moves:
            v = w.loc[m, k] / 1e6
            if k == "churn" and pending:
                pv = (pend.loc[m, "mrr_cop"] if m in pend.index else 0) / 1e6
                ghost = (len(x), cum, pv)
                x.append(lab); base.append(cum); y.append(0.0); color.append(T.viz[2]); text.append("")
                continue
            x.append(lab); base.append(cum); y.append(v); color.append(T.viz[0] if v >= 0 else T.viz[2])
            text.append(B.es(v, 2)); cum += v
        x.append("Cliente"); base.append(0.0); y.append(cum); color.append(T.line_strong); text.append(B.es(cum, 2))
        x.append("Precio"); base.append(cum); y.append(price / 1e6); color.append(T.viz[1])
        text.append(B.es(price / 1e6, 2))
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
        tbl = pd.DataFrame({"Barra": x, "MM COP": [round(v, 2) for v in y]})
        B.chart_frame(f"bridge_{m}", "",
                      f"De {B.mm(mrr.shift(1).loc[m])} a {B.mm(mrr_w.loc[m])}: cliente {B.mm(cust, sign=True)}, "
                      f"pricing {B.mm(price, sign=True)}, descuentos sin dato",
                      "Millones de COP · verde azulado = cliente suma, durazno = resta, violeta = pricing, "
                      "gris = subtotal y neto" + (" · churn punteado = en confirmación" if pending else ""),
                      fig, tbl, SRC_TX, 300, ysuffix=" MM", month_ticks=False)
    with c2:
        prior = months[max(0, i - 12):i]
        def avg12(k):
            ms = [p_ for p_ in prior if not (k == "churn" and p_ in pending_months)] or [m]
            return w.loc[ms, k].mean() / 1e6
        rows = []
        for k in MOVES:
            n = int(cnt.loc[m, k]) if m in cnt.index else 0
            if k == "churn" and pending:
                rows.append((LABEL[k], "en confirmación", f"{int(pend.loc[m, 'customers']) if m in pend.index else 0} en mora",
                             B.es(avg12(k), 2)))
            elif k == "price_uplift" and uplift_pending:
                rows.append((LABEL[k], f"{B.es(w.loc[m, k] / 1e6, 2)} · en confirmación", B.es(n, 0), B.es(avg12(k), 2)))
            else:
                rows.append((LABEL[k], B.es(w.loc[m, k] / 1e6, 2), B.es(n, 0), B.es(avg12(k), 2)))
        B.text_frame("mvtable", "", "Movimientos del mes", "Millones de COP y clientes · vs. promedio de 12 meses",
                     pd.DataFrame(rows, columns=["Movimiento", "MM COP", "Clientes", "Prom. 12 m"]),
                     right=("MM COP", "Clientes", "Prom. 12 m"),
                     note=(f"Cliente: <b>{B.mm(cust, sign=True)}</b> · pricing: <b>{B.mm(price, sign=True)}</b> · "
                           "descuentos: <b>sin dato</b> (instrumentar). Prom. 12 m: los 12 meses anteriores; el churn "
                           "excluye los meses aún sin confirmar."))
    with reading:
        actions = {
            "new": "Marketing y Ventas: revisar mezcla de canales y ticket de entrada del mes.",
            "expansion": "CS: identificar qué cuentas expandieron (uso o plan) y si es repetible.",
            "reactivation": "CS y Cobranza: confirmar si son retornos reales o pagos de mora tardíos.",
            "contraction": "CS y Finanzas: separar downgrade real de descuento; revisar las cuentas con mayor caída.",
            "churn": "CS y Cobranza: separar churn voluntario de mora no recuperada; contactar las cuentas grandes.",
        }
        pos = w.loc[m, ["new", "expansion", "price_uplift", "reactivation"]]
        neg = w.loc[m, ["contraction", "churn"]]
        lines = [f"<b>Qué cambió:</b> el MRR {'subió' if series['net'].loc[m] >= 0 else 'bajó'} "
                 f"{B.mm(abs(series['net'].loc[m]))} en {_mes(m)}. Lo que más sumó: {LABEL[pos.idxmax()].lower()} "
                 f"({B.mm(pos.max(), sign=True)}); lo que más restó: {LABEL[neg.idxmin()].lower()} ({B.mm(neg.min())})."]
        flagged = [(k, X[k].loc[m]) for k in ["new", "expansion", "reactivation", "contraction", "churn"]
                   if bool(X[k].loc[m, "signal"])]
        react, react_avg = w.loc[m, "reactivation"], avg12("reactivation") * 1e6
        if "reactivation" not in [k for k, _ in flagged] and react > 2 * max(react_avg, 1):
            lines.append(f"<b>Reactivación alta:</b> {B.mm(react)} en {int(cnt.loc[m, 'reactivation'])} clientes "
                         f"(promedio de 12 meses: {B.mm(react_avg)}). <b>Qué hacemos:</b> {actions['reactivation']}")
        if pending:
            lines.append(f"<b>Churn en confirmación:</b> {B.mm(pend.loc[m, 'mrr_cop'] if m in pend.index else 0)} de "
                         f"MRR está en mora sin confirmar; se conoce en los próximos {N_GAP} cierres. "
                         "<b>Qué hacemos:</b> Cobranza gestiona esas cuentas antes de que se confirme.")
        if uplift_pending:
            lines.append(f"<b>Subidas de precio en confirmación:</b> {B.mm(up_pend.loc[m, 'amount_cop'])} en "
                         f"{int(up_pend.loc[m, 'events'])} clientes; se confirman si el alza se mantiene el mes siguiente.")
        if m in pp_pend.index:
            lines.append(f"<b>Prepago en confirmación:</b> {B.mm(pp_pend.loc[m, 'amount_cop'])} de caja en "
                         f"{int(pp_pend.loc[m, 'events'])} pagos grandes que pueden ser prepagos; solo se reconoce como "
                         "MRR el nivel anterior de cada cliente.")
        if flagged:
            for k, r_ in flagged:
                lines.append(f"<b>Señal en {LABEL[k].lower()}:</b> {r_['reason']}, {r_['direction']} de lo normal "
                             f"(rango habitual {B.mm(r_['lcl'])} a {B.mm(r_['ucl'])}). <b>Qué hacemos:</b> {actions[k]}")
        else:
            lines.append("<b>Por qué:</b> ningún movimiento salió de su rango normal; es variación rutinaria. "
                         "<b>Qué hacemos:</b> nada que investigar este mes.")
        B.callout("".join(f"<p>{x_}</p>" for x_ in lines), cols=2)

    st.markdown('<div class="da-h3" style="margin-top:8px">¿Señal o ruido?</div><div class="da-sub">Banda = rango '
                'normal · rombo = señal · círculo = churn en confirmación · contracción y churn en positivo. Solo se '
                f'investiga lo que sale de la banda o forma una racha.</div><div class="da-source" '
                f'style="margin-bottom:8px">{SRC_TX}</div>', unsafe_allow_html=True)
    cols = st.columns(4, gap="small")
    for j, (k, bad) in enumerate([("new", "down"), ("expansion", "down"), ("contraction", "up"), ("churn", "up")]):
        x_ = X[k]
        f = go.Figure()
        f.add_scatter(x=months, y=x_["ucl"] / 1e6, mode="lines", line=dict(color=T.line_strong, width=1),
                      hoverinfo="skip")
        f.add_scatter(x=months, y=x_["lcl"] / 1e6, mode="lines", line=dict(color=T.line_strong, width=1), fill="tonexty",
                      fillcolor=T.band, hoverinfo="skip")
        f.add_scatter(x=months, y=x_["value"] / 1e6, mode="lines", line=dict(color=T.viz[0]),
                      hovertemplate="%{x}: %{y:.2f} MM<extra></extra>")
        s_ = x_[x_["signal"]]
        if len(s_):
            f.add_scatter(x=[mm_ for mm_, f_ in zip(months, x_["signal"]) if f_], y=s_["value"] / 1e6, mode="markers",
                          marker=dict(color=T.negative, size=8, symbol="diamond", line=dict(color=T.surface, width=2)),
                          hovertemplate="Señal · %{x}: %{y:.2f} MM<extra></extra>")
        if k == "churn":
            pm = [p_ for p_ in pending_months if p_ in pend.index]
            f.add_scatter(x=pm, y=[pend.loc[p_, "mrr_cop"] / 1e6 for p_ in pm], mode="markers",
                          marker=dict(color=T.surface, size=8, symbol="circle", line=dict(color=T.viz[2], width=2)),
                          hovertemplate="En confirmación · %{x}: %{y:.2f} MM en mora<extra></extra>")
        f.add_vline(x=m, line_color=T.ink, line_width=1, opacity=0.35)
        f.update_layout(showlegend=False)
        state = "En confirmación" if (k == "churn" and pending) else _status_chip(sig(k), bad)[0]
        with cols[j]:
            B.chart_frame(f"xmr_{k}", "", LABEL[k], f"{state} · MM COP por mes",
                          f, x_.assign(month=months)[["month", "value", "center", "lcl", "ucl", "signal", "reason"]],
                          None, 210, ysuffix=" MM", month_ticks="year")

    st.markdown('<div class="da-h3" style="margin-top:8px">Eficiencia del S&M</div><div class="da-sub">Cuánto ingreso nuevo '
                'compra cada peso de Sales & Marketing · unidades del enunciado, pendientes de confirmar con Finanzas</div>'
                '<div class="da-source" style="margin-bottom:8px">Fuente: S&M_spend.csv y Transactions.csv (agregado)</div>',
                unsafe_allow_html=True)
    sm = _load("sm_monthly").set_index("month")
    eff = _load("sm_efficiency_quarterly")
    eff = eff[eff["complete"] & (eff["quarter"] >= "2022Q2")]
    var = sm[["PaidMedia", "PublicidadNoWeb", "Freelance", "Travel"]].sum(axis=1).reindex(months)
    cac3 = (var.rolling(3).sum() / series["new_count"].rolling(3).sum()).dropna()
    Xc = xmr(cac3, baseline=18).reindex(months)
    e1, e2, e3 = st.columns(3, gap="small")
    with e1:
        f = go.Figure(go.Bar(x=months, y=sm["sm_total_cop"].reindex(months) / 1e6, marker_color=T.viz[1],
                             hovertemplate="%{x}: %{y:.0f} MM<extra></extra>"))
        f.add_vline(x=m, line_color=T.ink, line_width=1, opacity=0.35)
        B.chart_frame("sm_mes", "", "S&M del mes", f"{B.mm(sm.loc[m, 'sm_total_cop'], 0)} en {_mes(m)} · MM COP",
                      f, None, None, 210, ysuffix=" MM", month_ticks="year")
    with e2:
        f = go.Figure()
        f.add_scatter(x=months, y=Xc["ucl"] / 1e6, mode="lines", line=dict(color=T.line_strong, width=1), hoverinfo="skip")
        f.add_scatter(x=months, y=Xc["lcl"] / 1e6, mode="lines", line=dict(color=T.line_strong, width=1), fill="tonexty",
                      fillcolor=T.band, hoverinfo="skip")
        f.add_scatter(x=months, y=Xc["value"] / 1e6, mode="lines", line=dict(color=T.viz[0]),
                      hovertemplate="%{x}: %{y:.2f} MM<extra></extra>")
        f.add_vline(x=m, line_color=T.ink, line_width=1, opacity=0.35)
        f.update_layout(showlegend=False)
        state_c = _status_chip(Xc.loc[m].to_dict(), "up")[0] if pd.notna(Xc.loc[m, "value"]) else "Sin dato"
        B.chart_frame("cac_var", "", "CAC variable, 3 meses móviles", f"{state_c} · MM por cliente nuevo · solo rubros de adquisición",
                      f, Xc.assign(month=months)[["month", "value", "center", "lcl", "ucl", "signal"]], None, 210,
                      ysuffix=" MM", month_ticks="year")
    with e3:
        f = go.Figure(go.Bar(x=[B.quarter_label(q) for q in eff["quarter"]], y=eff["magic_number"], marker_color=T.viz[0],
                             hovertemplate="%{x}: %{y:.2f}<extra></extra>"))
        f.add_hline(y=0.75, line_color=T.ink, line_width=1)
        f.add_hline(y=0.5, line_color=T.line_strong, line_width=1, line_dash="dot")
        last_q = eff.iloc[-1]
        B.chart_frame("magic_q", "", "Magic number, trimestre cerrado",
                      f"{B.es(last_q['magic_number'], 2)} en {B.quarter_label(last_q['quarter']).replace('<br>', ' ')} · "
                      "líneas: 0,75 escalar · 0,5 revisar", f, eff[["quarter", "magic_number"]].round(2), None, 210, month_ticks=False)

    with st.expander("Dueños, reglas de alerta y acciones"):
        st.markdown('<div class="da-sub">Cómo se calcula la banda: límites naturales del proceso (XmR) = media ± 2,66 × '
                    'rango móvil promedio, fijados con los primeros 18 meses de la ventana. Señal = un punto fuera de los '
                    'límites, 8 seguidos del mismo lado de la media o 3 de 4 cerca de un límite (reglas de Wheeler y '
                    'Western Electric). Los meses en confirmación no entran en el cálculo de los límites.</div>',
                    unsafe_allow_html=True)
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
                     ]), SRC_TX)


METRICS = [
    ("leads", "Leads nuevos", "Volumen", "", 1, None),
    ("high_fit", "Mezcla de alto ajuste (pequeña y mediana)", "Entrada controlable", " %", 100, "down"),
    ("speed_p50", "Speed-to-lead P50", "Entrada controlable", " h", 1, "up"),
    ("sla_1h", "Leads contactados en menos de 1 hora", "Entrada controlable", " %", 100, "down"),
    ("work_to_eng", "Working a Engaged en 30 días", "Entrada controlable", " %", 100, "down"),
    ("sql_to_won", "SQL a Won en 60 días", "Entrada controlable", " %", 100, "down"),
    ("new_customers", "Clientes nuevos", "Salida", "", 1, "down"),
]
SHORT = {"high_fit": "Mezcla de alto ajuste", "sla_1h": "Contactados en < 1 hora",
         "work_to_eng": "Working a Engaged", "sql_to_won": "SQL a Won"}


def _fmt(v, suffix, scale):
    if pd.isna(v):
        return "en maduración"
    d = 1 if suffix in (" %", " h") else 0
    return f"{B.es(v * scale, d)}{suffix.replace(' ', chr(160))}"


def weekly_review(T: B.Theme, channel_colors: dict) -> None:
    filters = _page_header("Revisión semanal del funnel",
                           "Para: CRO, líderes SDR y AE · Decide: qué entrada se salió de lo normal y quién actúa · "
                           "Cadencia: semanal, 30 minutos · formato fijo 6-12 (6 semanas | 12 meses)", ratio=(2, 1))
    with filters:
        B.callout("<b>Datos sintéticos:</b> prototipo del formato con dos problemas plantados. No son hallazgos de "
                  "Finora.", kind="warn")
    leads, ev = _synthetic()
    as_of = pd.Timestamp("2024-10-31")
    r = F.reach_table(leads, ev)
    wk = F.period_metrics(r, as_of, "W")
    mo = F.period_metrics(r, as_of, "M")
    week = wk.index[-1]

    state = {}
    for k, name, kind, suf, sc, bad in METRICS:
        s = wk[k].dropna()
        x_ = xmr(s, baseline=26)
        last = x_.iloc[-1]
        state[k] = dict(value=s.iloc[-1], when=s.index[-1], center=last["center"], signal=bool(last["signal"]),
                        direction=last["direction"], reason=last["reason"], bad=bad)

    def word(k):
        st_ = state[k]
        if not st_["signal"]:
            return "normal"
        return "SEÑAL ▲" if st_["direction"] == "arriba" else "SEÑAL ▼"

    sig_k = [k for k, *_ in METRICS if state[k]["signal"]]
    name = {k: n for k, n, *_ in METRICS}
    meta = {k: (suf, sc) for k, _, _, suf, sc, _ in METRICS}

    c1, c2 = st.columns([5, 7], gap="medium")
    with c1:
        parts = [f"<p><b>Semana del {week.day} de {B.MESES[week.month - 1]} de {week.year} · qué cambió</b></p>"]
        if sig_k:
            parts.append("<ul>" + "".join(
                f"<li><b>{name[k]}:</b> {_fmt(state[k]['value'], *meta[k])} · lo normal, "
                f"{_fmt(state[k]['center'], *meta[k])} · {state[k]['reason']}</li>" for k in sig_k) + "</ul>")
        normal = [name[k] for k, *_ in METRICS if not state[k]["signal"]]
        if normal:
            parts.append(f"<p><b>Dentro de lo normal:</b> {', '.join(normal)}.</p>")
        if "speed_p50" in sig_k and "sql_to_won" not in sig_k:
            parts.append("<p><b>Por qué (hipótesis principal):</b> el volumen subió y el primer contacto se demoró; la "
                         "conversión cae antes de SQL mientras post-SQL sigue estable. Apunta a <b>capacidad SDR</b>, no "
                         "al AE.</p><p><b>Qué hacemos:</b> ruteo y primer contacto automático para leads de bajo ajuste, "
                         "SLA de 1 hora para los de alto ajuste, y revisar la meta de Paid Social por SQL, no por "
                         "leads.</p>")
        B.callout("".join(parts))
    with c2:
        def node(k, label=None):
            st_ = state[k]
            color = T.line_strong if not st_["signal"] else T.negative
            val = _fmt(st_["value"], *meta[k])
            return (f'{k} [label="{label or name[k]}\\n{val}\\n{word(k)}", color="{color}", '
                    f'penwidth={2 if st_["signal"] else 1}];')
        ticket = wk["ticket"].dropna()
        with st.container(border=True, key="frame_tree"):
            st.markdown('<div class="da-h3">De las entradas que el equipo controla al MRR nuevo</div><div class="da-sub">'
                        'Última semana con dato · en rojo, lo que salió de su rango normal (XmR)</div>',
                        unsafe_allow_html=True)
            st.graphviz_chart(f"""
            digraph G {{ rankdir=LR; bgcolor="transparent"; nodesep=0.25; ranksep=0.6;
              node [shape=box, style=rounded, fontname="IBM Plex Sans", fontsize=11, fontcolor="{T.ink}", color="{T.line_strong}"];
              edge [color="{T.muted}", arrowsize=0.6];
              out [label="MRR nuevo (salida)\\n{B.mm(wk['new_mrr'].dropna().iloc[-1])}\\nsemanal", color="{T.viz[0]}", penwidth=2];
              {node("new_customers")}
              tk [label="Ticket de entrada\\n{B.es(ticket.iloc[-1] / 1e3, 0)} mil COP"];
              {node("leads")}
              conv [label="Conversión New a Won\\npor camino"];
              {node("speed_p50")} {node("sla_1h")} {node("high_fit", "Mezcla de alto ajuste")} {node("work_to_eng")} {node("sql_to_won")}
              new_customers -> out; tk -> out; leads -> new_customers; conv -> new_customers;
              speed_p50 -> conv; sla_1h -> conv; high_fit -> conv; work_to_eng -> conv; sql_to_won -> conv;
            }}""")
            pre = ["high_fit", "speed_p50", "sla_1h", "work_to_eng"]
            hot = [k for k in pre if state[k]["signal"]]
            if hot and not state["sql_to_won"]["signal"]:
                reading = (f"<b>Lectura:</b> {len(hot)} entradas en señal, todas antes de SQL; post-SQL normal. "
                           "Apunta a capacidad SDR, no al AE.")
            elif state["sql_to_won"]["signal"]:
                reading = "<b>Lectura:</b> post-SQL en señal: revisar los deals de Demo y Proposal con el líder AE."
            else:
                reading = "<b>Lectura:</b> ninguna entrada salió de su rango normal; nada que ver aquí."
            st.markdown(f'<div class="hs-body" style="font:400 14px/22px var(--font-sans);margin:6px 0 2px">{reading}</div>'
                        f'<div class="da-source">{SRC_SYN}</div>', unsafe_allow_html=True)

    st.markdown('<div class="da-h3" style="margin-top:8px">Formato 6-12: últimas 6 semanas | últimos 12 meses</div>'
                '<div class="da-sub">Formato fijo de la Weekly Business Review de Amazon: siempre las mismas métricas, en '
                'el mismo orden. Izquierda, 6 semanas; derecha, 12 meses. Banda = rango normal (XmR); rombo = señal. Las '
                'tasas esperan su ventana de maduración (30 o 60 días).</div>'
                f'<div class="da-source" style="margin-bottom:8px">{SRC_SYN}</div>',
                unsafe_allow_html=True)
    slots = list(METRICS) + [None]
    rw = r[r["path"] == "sdr_full"].assign(cohort=lambda d: d["created_at"].dt.to_period("W"))
    mature = sorted(c for c in rw["cohort"].unique() if c.end_time + pd.Timedelta(days=30) <= as_of)
    kt = F.kitagawa(rw, "New", "Engaged", 30, mature[-18:-6], mature[-6:])
    mix_pp, rate_pp = kt["mix_effect"].sum() * 100, kt["rate_effect"].sum() * 100
    for row in range(0, len(slots), 4):
        cols = st.columns(4, gap="small")
        for col, item in zip(cols, slots[row:row + 4]):
            with col:
                if item is None:
                    fk = go.Figure(go.Bar(x=["Mezcla", "Tasa"], y=[mix_pp, rate_pp], marker_color=[T.viz[0], T.viz[1]],
                                          text=[f"{B.es(v, 1)} pp" for v in (mix_pp, rate_pp)], textposition="outside",
                                          textfont=dict(family=B.FONT_MONO, size=11, color=T.ink), cliponaxis=False,
                                          hovertemplate="%{x}: %{y:.2f} pp<extra></extra>"))
                    lim = max(abs(mix_pp), abs(rate_pp), 0.5) * 1.6
                    fk.update_yaxes(range=[-lim, lim], ticksuffix=" pp")
                    lead = "tasa" if abs(rate_pp) >= abs(mix_pp) else "mezcla"
                    B.chart_frame("612_mix", "Diagnóstico", "¿Mezcla o tasa?",
                                  f"New a Engaged (SDR): {B.es(mix_pp + rate_pp, 1)} pp, sobre todo por {lead} · "
                                  "6 semanas vs. las 12 previas",
                                  fk, (kt * 100).round(2).reset_index(names="Canal"), None, 190, month_ticks=False)
                    continue
                k, nm, kind, suf, sc, bad = item
                xw, xm = xmr(wk[k].dropna(), baseline=26), xmr(mo[k].dropna(), baseline=12)
                last6, last12 = xw.tail(6), xm.tail(12)
                f = make_subplots(rows=1, cols=2, column_widths=[0.4, 0.6], shared_yaxes=suf in (" %", " h"),
                                  horizontal_spacing=0.08, subplot_titles=("6 semanas", "12 meses"))
                for col_, xx in ((1, last6), (2, last12)):
                    xs = list(xx.index)
                    f.add_scatter(x=xs, y=xx["ucl"] * sc, mode="lines", line=dict(color=T.line_strong, width=1),
                                  hoverinfo="skip", showlegend=False, row=1, col=col_)
                    f.add_scatter(x=xs, y=xx["lcl"] * sc, mode="lines", line=dict(color=T.line_strong, width=1),
                                  fill="tonexty", fillcolor=T.band, hoverinfo="skip", showlegend=False, row=1, col=col_)
                    f.add_scatter(x=xs, y=xx["value"] * sc, mode="lines+markers", line=dict(color=T.viz[0]),
                                  marker=dict(size=6, color=T.viz[0], line=dict(color=T.surface, width=1.5)),
                                  showlegend=False, hovertemplate="%{x|%d %b %Y}: %{y:.1f}<extra></extra>", row=1, col=col_)
                    sg = xx[xx["signal"]]
                    if len(sg):
                        f.add_scatter(x=list(sg.index), y=sg["value"] * sc, mode="markers", showlegend=False,
                                      marker=dict(color=T.negative, size=9, symbol="diamond",
                                                  line=dict(color=T.surface, width=1.5)),
                                      hovertemplate="Señal · %{x|%d %b %Y}: %{y:.1f}<extra></extra>", row=1, col=col_)
                ends6 = [last6.index[-1]]
                ends12 = [last12.index[j] for j in (len(last12) // 2, len(last12) - 1)]
                f.update_xaxes(tickvals=ends6, ticktext=[f"{d.day} {B.MESES[d.month - 1]}" for d in ends6], row=1, col=1,
                               tickangle=0)
                f.update_xaxes(tickvals=ends12, ticktext=[B.MESES[d.month - 1] for d in ends12], row=1, col=2,
                               tickangle=0)
                f.update_annotations(font=dict(family=B.FONT_SANS, size=11, color=T.muted))
                if suf not in (" %", " h"):
                    f.update_yaxes(side="right", row=1, col=2)
                st_ = state[k]
                status = "Normal" if not st_["signal"] else f"Señal {'▲' if st_['direction'] == 'arriba' else '▼'}"
                B.chart_frame(f"612_{k}", kind, SHORT.get(k, nm),
                              f"{status} · última: {_fmt(st_['value'], suf, sc)} · normal: {_fmt(st_['center'], suf, sc)}",
                              f, pd.concat([last6.assign(vista="semana"), last12.assign(vista="mes")]).reset_index(
                                  names="periodo")[["vista", "periodo", "value", "center", "lcl", "ucl", "signal"]].assign(
                                  periodo=lambda d: d["periodo"].dt.date),
                              None, 190, ysuffix=suf, month_ticks=False)

    stl = F.stalled(r, ev, as_of)
    by_owner = stl.pivot_table(index="owner", columns="stage", values="lead_id", aggfunc="count", fill_value=0)
    by_owner["Total"] = by_owner.sum(axis=1)
    c3, c4 = st.columns([5, 7], gap="medium")
    with c3:
        B.table_frame("stalled", "", f"{B.es(len(stl), 0)} leads abiertos superan el P90 histórico de su etapa y camino",
                      "P90 = lo que tardan en avanzar los leads que sí avanzan · leads estancados por dueño y etapa: la "
                      "lista que cada SDR y AE limpia esta semana",
                      by_owner.sort_values("Total", ascending=False).reset_index(names="Dueño"), SRC_SYN)
    with c4:
        B.text_frame("rules_cro", "", "Cada entrada tiene dueño, regla de alerta y acción",
                     "Se revisa cada semana en el mismo formato; sin señal, «nada que ver aquí»", _rules_table([
                         ("Speed-to-lead P50 y SLA de 1 hora", "Líder SDR", "Señal arriba en P50, o SLA < 60 %",
                          "Ruteo automático, primer contacto con IA, ajustar capacidad"),
                         ("Mezcla de alto ajuste", "Marketing", "Señal abajo",
                          "Revisar segmentación y metas por canal (SQL, no leads)"),
                         ("Working a Engaged", "Líder SDR", "Señal abajo", "Cruzar con speed-to-lead dentro del canal; coaching"),
                         ("SQL a Won", "Líder AE", "Señal abajo", "Revisión de deals en Demo y Proposal; criterios de SQL"),
                         ("Clientes nuevos y MRR nuevo", "CRO", "Señal abajo", "Descomponer por entrada antes de actuar"),
                     ]), SRC_SYN)
