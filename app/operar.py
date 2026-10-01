"""Vistas para OPERAR (no solo para explicar): revisión mensual del MRR (CFO) y semanal del funnel (CRO).

Diseño en docs/diseno_dashboard.md:
- una decisión, un público y una cadencia por vista;
- contexto en cada KPI (vs. periodo anterior, vs. hace 12 meses) y estado señal/rutina;
- XmR para separar la señal del ruido;
- formato fijo semana a semana (6-12 de la WBR de Amazon);
- dueño, regla y acción por métrica.
"""
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
    return f"Señal: {'más alto' if up else 'más bajo'} de lo normal", ("down" if bad else "up")


def _rules_table(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Métrica", "Dueño", "Regla de alerta", "Acción"])


# =====================================================================================
def monthly_review(T: B.Theme) -> None:
    st.title("Revisión mensual del MRR")
    st.caption("Para: CFO y RevOps · Decide: si el cambio del mes es señal o ruido, y quién investiga · "
               "Cadencia: mensual, en el cierre")
    b = _load("bridge_monthly")
    b = b[b["scenario"] == COR]
    piv = b.pivot_table(index="month", columns="movement", values="amount_cop").reindex(columns=MOVES).fillna(0)
    mrr = b.groupby("month")["mrr_close"].first()
    cnt = _load("movement_counts_monthly")
    cnt = cnt[cnt["scenario"] == COR].pivot_table(index="month", columns="movement", values="customers").reindex(
        columns=MOVES).fillna(0)
    months = [m for m in piv.index if m >= WINDOW_START]
    N_GAP = 2                                              # regla de mora del modelo corregido
    pending_months = months[-N_GAP:]                       # su churn aún no se puede confirmar
    stt = _load("status_monthly")
    pend = stt[stt["status"] == "delinquent_open"].set_index("month")
    m = st.selectbox("Mes de cierre", months[::-1], format_func=_mes)
    pending = m in pending_months
    i = months.index(m)
    prev, yago = (months[i - 1] if i > 0 else None), (months[i - 12] if i >= 12 else None)

    # series del periodo y su comportamiento (línea base: primeros 18 meses de la ventana)
    w = piv.loc[months]
    series = {
        "net": mrr.loc[months] - mrr.shift(1).loc[months],
        "new": w["new"], "expansion": w["expansion"],
        "contraction": -w["contraction"], "churn": (-w["churn"]).where(~w.index.isin(pending_months)),
        "new_count": cnt.reindex(months)["new"].fillna(0),
    }
    X = {k: xmr(v.dropna(), baseline=18).reindex(months) for k, v in series.items()}
    X["churn"]["signal"] = X["churn"]["signal"].fillna(False).astype(bool)

    def sig(k):
        return X[k].loc[m].to_dict()

    def vs(s, label_prev=True):
        parts = []
        if prev is not None:
            parts.append(f"vs. {B.mm(s.loc[prev]) if abs(s.loc[prev]) > 1000 else B.es(s.loc[prev], 0)} en {_mes(prev)}")
        if yago is not None:
            parts.append(f"{B.mm(s.loc[yago]) if abs(s.loc[yago]) > 1000 else B.es(s.loc[yago], 0)} hace 12 meses")
        return " · ".join(parts)

    mrr_w = mrr.loc[months]
    chips = {k: _status_chip(sig(k), bad) for k, bad in [("net", "down"), ("new_count", "down")]}
    chips["churn"] = ("", None) if pending else _status_chip(sig("churn"), "up")
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
             delta=chips["new_count"][0], delta_kind=chips["new_count"][1],
             foot=f"{B.mm(w.loc[m, 'new'])} de MRR nuevo · {vs(series['new_count'])}"),
    ])

    # Qué cambió · por qué · qué hacemos (generado a partir de las señales del mes)
    actions = {
        "new": "Marketing y Ventas: revisar mezcla de canales y ticket de entrada del mes.",
        "expansion": "CS: identificar qué cuentas expandieron (uso o plan) y si es repetible.",
        "contraction": "CS y Finanzas: separar downgrade real de descuento; revisar las cuentas con mayor caída.",
        "churn": "CS y Cobranza: separar churn voluntario de mora no recuperada; contactar las cuentas grandes.",
        "net": "Finanzas: descomponer el neto por movimiento antes de concluir.",
    }
    pos = w.loc[m, ["new", "expansion", "price_uplift", "reactivation"]]
    neg = w.loc[m, ["contraction", "churn"]]
    lines = [f"<b>Qué cambió:</b> el MRR {'subió' if series['net'].loc[m] >= 0 else 'bajó'} "
             f"{B.mm(abs(series['net'].loc[m]))} en {_mes(m)}. Lo que más sumó: {LABEL[pos.idxmax()].lower()} "
             f"({B.mm(pos.max(), sign=True)}); lo que más restó: {LABEL[neg.idxmin()].lower()} ({B.mm(neg.min())})."]
    flagged = [(k, X[k].loc[m]) for k in ["new", "expansion", "contraction", "churn"] if bool(X[k].loc[m, "signal"])]
    if pending:
        lines.append(f"<b>Churn en confirmación:</b> {B.mm(pend.loc[m, 'mrr_cop'] if m in pend.index else 0)} de MRR "
                     f"está en mora sin confirmar. Con la regla de {N_GAP} meses, el churn de {_mes(m)} se conoce en el "
                     f"cierre de {_mes(months[-1]) if m != months[-1] else 'los próximos meses'}. <b>Qué hacemos:</b> "
                     "Cobranza gestiona esas cuentas antes de que se confirme.")
    if flagged:
        for k, r_ in flagged:
            lines.append(f"<b>Señal en {LABEL[k].lower()}:</b> {r_['reason']}, {r_['direction']} de lo normal "
                         f"(rango habitual {B.mm(r_['lcl'])} a {B.mm(r_['ucl'])}). <b>Qué hacemos:</b> {actions[k]}")
    else:
        lines.append("<b>Por qué:</b> ningún movimiento salió de su rango normal; es variación rutinaria. "
                     "<b>Qué hacemos:</b> nada que investigar este mes.")
    B.callout("<br>".join(lines))

    # Puente del mes (solo variaciones: las barras parten de cero, sin ejes truncados)
    c1, c2 = st.columns([11, 9], gap="medium")
    with c1:
        labels = ["Nuevos", "Expansión", "Precio", "Reactiv.", "Contracc.", "Churn", "Neto"]
        vals = [w.loc[m, k] / 1e6 for k in MOVES]
        fig = go.Figure(go.Waterfall(
            x=labels, y=vals + [sum(vals)], measure=["relative"] * len(MOVES) + ["total"],
            increasing=dict(marker=dict(color=T.div[5])), decreasing=dict(marker=dict(color=T.div[1])),
            totals=dict(marker=dict(color=T.line_strong)), connector=dict(line=dict(color=T.line, width=1)),
            text=[B.es(v, 2) for v in vals + [sum(vals)]], textposition="outside",
            textfont=dict(family=B.FONT_MONO, size=11, color=T.ink),
            hovertemplate="%{x}: %{y:.2f} MM<extra></extra>"))
        fig.update_xaxes(tickangle=0)
        tbl = pd.DataFrame({"Movimiento": [LABEL[k] for k in MOVES], "MM COP": [round(w.loc[m, k] / 1e6, 2) for k in MOVES],
                            "Clientes": [int(cnt.loc[m, k]) if m in cnt.index else 0 for k in MOVES]})
        B.chart_frame(f"bridge_{m}", "",
                      f"De {B.mm(mrr.shift(1).loc[m])} a {B.mm(mrr_w.loc[m])}: así se explica el cambio",
                      "Movimientos del mes en millones de COP · azul suma, durazno resta, gris = cambio neto",
                      fig, tbl, SRC_TX, 340, ysuffix=" MM", month_ticks=False)
    with c2:
        with st.container(border=True, key="frame_mvtable"):
            st.markdown('<div class="da-h3">Movimientos del mes</div>'
                        '<div class="da-sub">Monto en millones de COP y clientes por tipo · comparado con el promedio de '
                        '12 meses</div>', unsafe_allow_html=True)
            avg12 = w.loc[months[max(0, i - 12):i]].mean() if i > 0 else w.loc[[m]].mean()
            st.dataframe(B.es_table(pd.DataFrame({
                "Movimiento": [LABEL[k] for k in MOVES],
                "MM COP": [w.loc[m, k] / 1e6 for k in MOVES],
                "Clientes": [int(cnt.loc[m, k]) if m in cnt.index else 0 for k in MOVES],
                "Prom. 12 m": [avg12[k] / 1e6 for k in MOVES]}), decimals=2), hide_index=True, width="stretch")
            cust = sum(w.loc[m, k] for k in ["new", "expansion", "reactivation", "contraction", "churn"])
            st.markdown(f'<div class="da-sub" style="margin-top:8px">Comportamiento del cliente: <b>{B.mm(cust, sign=True)}</b> · '
                        f'pricing: <b>{B.mm(w.loc[m, "price_uplift"], sign=True)}</b> · descuentos: <b>sin dato</b> '
                        '(instrumentar)</div>', unsafe_allow_html=True)

    # ¿Señal o ruido? XmR por movimiento
    st.subheader("¿Señal o ruido?")
    st.caption("Límites naturales del proceso (media ± 2,66 × rango móvil) sobre los primeros 18 meses. "
               "Solo se investiga lo que sale de la banda o forma una racha.")
    st.markdown(f'<div class="da-source">{SRC_TX} · aplica a los 4 gráficos</div>', unsafe_allow_html=True)
    cols = st.columns(2, gap="medium")
    for j, (k, bad) in enumerate([("new", "down"), ("expansion", "down"), ("contraction", "up"), ("churn", "up")]):
        x_ = X[k]
        f = go.Figure()
        f.add_scatter(x=months, y=x_["ucl"] / 1e6, mode="lines", line=dict(color=T.line_strong, width=1),
                      hoverinfo="skip", showlegend=False)
        f.add_scatter(x=months, y=x_["lcl"] / 1e6, mode="lines", line=dict(color=T.line_strong, width=1), fill="tonexty",
                      fillcolor=T.band, name="Rango normal", hoverinfo="skip")
        f.add_scatter(x=months, y=x_["value"] / 1e6, mode="lines", name=LABEL[k], line=dict(color=T.viz[0]),
                      hovertemplate="%{x}: %{y:.2f} MM<extra></extra>")
        s_ = x_[x_["signal"]]
        if len(s_):
            f.add_scatter(x=[mm_ for mm_, f_ in zip(months, x_["signal"]) if f_], y=s_["value"] / 1e6, mode="markers",
                          name="Señal", marker=dict(color=T.negative, size=9, symbol="diamond",
                                                    line=dict(color=T.surface, width=2)),
                          hovertemplate="Señal · %{x}: %{y:.2f} MM<extra></extra>")
        if k == "churn":
            pm = [p_ for p_ in pending_months if p_ in pend.index]
            f.add_scatter(x=pm, y=[pend.loc[p_, "mrr_cop"] / 1e6 for p_ in pm], mode="markers",
                          name="En confirmación (MRR en mora)",
                          marker=dict(color=T.surface, size=9, symbol="circle", line=dict(color=T.viz[0], width=2)),
                          hovertemplate="En confirmación · %{x}: %{y:.2f} MM en mora<extra></extra>")
        f.add_vline(x=m, line_color=T.ink, line_width=1, opacity=0.35)
        state = "en confirmación" if (k == "churn" and pending) else _status_chip(sig(k), bad)[0]
        with cols[j % 2]:
            B.chart_frame(f"xmr_{k}", "", f"{LABEL[k]} en {_mes(m)}: {state.lower()}",
                          f"MRR por mes, millones de COP{' (en positivo)' if k in ('contraction', 'churn') else ''}",
                          f, x_.assign(month=months)[["month", "value", "center", "lcl", "ucl", "signal", "reason"]],
                          None, 260, ysuffix=" MM")

    B.text_frame("rules_cfo", "", "Cada métrica tiene dueño, regla de alerta y acción",
                  "Se revisa en el cierre mensual; si no hay señal, se dice «nada que investigar» y se sigue", _rules_table([
                      ("MRR nuevo", "Marketing + Ventas", "Señal abajo o 3 meses bajo la línea central", "Revisar mezcla de canal y ticket de entrada"),
                      ("Expansión", "Customer Success", "Señal abajo", "Revisar adopción y upgrades; campañas de expansión"),
                      ("Contracción", "CS + Finanzas", "Señal arriba", "Separar downgrade de descuento; revisar cuentas grandes"),
                      ("Churn", "CS + Cobranza", "Señal arriba", "Separar voluntario de mora; plan de recuperación"),
                      ("MRR en mora", "Cobranza", "Más de 3 % del MRR", "Gestión de cobro antes de confirmar churn (N = 2 meses)"),
                      ("Descuentos (nuevo)", "Finanzas + Deal desk", "Price realization < 95 %", "Revisar aprobaciones y vencimientos"),
                  ]), SRC_TX)


# =====================================================================================
METRICS = [  # clave, nombre, tipo, sufijo, escala, malo cuando
    ("leads", "Leads nuevos", "Volumen", "", 1, None),
    ("high_fit", "Mezcla de alto ajuste (pequeña y mediana)", "Entrada controlable", " %", 100, "down"),
    ("speed_p50", "Speed-to-lead P50", "Entrada controlable", " h", 1, "up"),
    ("sla_1h", "Leads contactados en menos de 1 hora", "Entrada controlable", " %", 100, "down"),
    ("work_to_eng", "Working a Engaged en 30 días", "Entrada controlable", " %", 100, "down"),
    ("sql_to_won", "SQL a Won en 60 días", "Entrada controlable", " %", 100, "down"),
    ("new_customers", "Clientes nuevos", "Salida", "", 1, "down"),
]


def _fmt(v, suffix, scale):
    if pd.isna(v):
        return "en maduración"
    d = 1 if suffix in (" %", " h") else 0
    return f"{B.es(v * scale, d)}{suffix}"


def weekly_review(T: B.Theme, channel_colors: dict) -> None:
    st.title("Revisión semanal del funnel")
    st.caption("Para: CRO, líderes SDR y AE · Decide: qué entrada se salió de lo normal y quién actúa · "
               "Cadencia: semanal, 30 minutos · formato fijo 6-12 (6 semanas | 12 meses)")
    B.callout("<b>Datos sintéticos.</b> Esta vista es el prototipo de la revisión semanal que operaría el CRO con los "
              "eventos del CRM. Prueba que el formato detecta los dos problemas plantados (más volumen de un canal de "
              "bajo ajuste y SDR saturados). <b>No son hallazgos de Finora.</b>", kind="warn")
    leads, ev = _synthetic()
    as_of = pd.Timestamp("2024-10-31")
    r = F.reach_table(leads, ev)
    wk = F.period_metrics(r, as_of, "W")
    mo = F.period_metrics(r, as_of, "M")
    week = wk.index[-1]

    # estado de cada métrica en su última semana con dato
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

    # Qué cambió · por qué · qué hacemos
    sig_k = [k for k, *_ in METRICS if state[k]["signal"]]
    name = {k: n for k, n, *_ in METRICS}
    meta = {k: (suf, sc) for k, _, _, suf, sc, _ in METRICS}
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
                     "conversión cae antes de SQL mientras post-SQL sigue estable. Apunta a <b>capacidad SDR</b>, no al "
                     "AE.</p><p><b>Qué hacemos:</b> ruteo y primer contacto automático para leads de bajo ajuste, SLA de "
                     "1 hora para los de alto ajuste, y revisar la meta de Paid Social por SQL, no por leads.</p>")
    B.callout("".join(parts))

    # Árbol de métricas: de las entradas controlables a la salida
    def node(k, label=None):
        st_ = state[k]
        color = T.line_strong if not st_["signal"] else T.negative
        val = _fmt(st_["value"], *meta[k])
        return f'{k} [label="{label or name[k]}\\n{val}\\n{word(k)}", color="{color}", penwidth={2 if st_["signal"] else 1}];'
    ticket = wk["ticket"].dropna()
    with st.container(border=True, key="frame_tree"):
        st.markdown('<div class="da-h3">De las entradas que el equipo '
                    'controla al MRR nuevo</div><div class="da-sub">Última semana con dato · en rojo, lo que salió de '
                    'su rango normal (XmR)</div>', unsafe_allow_html=True)
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
        st.markdown(f'<div class="da-source">{SRC_SYN}</div>', unsafe_allow_html=True)

    # Formato 6-12: mismas métricas, mismo orden, cada semana
    st.subheader("Formato 6-12: últimas 6 semanas | últimos 12 meses")
    st.caption("Formato fijo de la Weekly Business Review de Amazon: siempre las mismas métricas, en el mismo orden. "
               "Banda = rango normal (XmR); rombo = señal.")
    st.markdown(f'<div class="da-source">{SRC_SYN} · aplica a los 7 gráficos</div>', unsafe_allow_html=True)
    for k, nm, kind, suf, sc, bad in METRICS:
        sw = wk[k].dropna()
        sm = mo[k].dropna()
        xw, xm = xmr(sw, baseline=26), xmr(sm, baseline=12)
        last6, last12 = xw.tail(6), xm.tail(12)
        f = make_subplots(rows=1, cols=2, column_widths=[0.4, 0.6], shared_yaxes=suf in (" %", " h"),
                          horizontal_spacing=0.06,
                          subplot_titles=("Últimas 6 semanas", "Últimos 12 meses"))
        for col_, xx in ((1, last6), (2, last12)):
            xs = list(xx.index)
            f.add_scatter(x=xs, y=xx["ucl"] * sc, mode="lines", line=dict(color=T.line_strong, width=1), hoverinfo="skip",
                          showlegend=False, row=1, col=col_)
            f.add_scatter(x=xs, y=xx["lcl"] * sc, mode="lines", line=dict(color=T.line_strong, width=1), fill="tonexty",
                          fillcolor=T.band, hoverinfo="skip", showlegend=False, row=1, col=col_)
            f.add_scatter(x=xs, y=xx["value"] * sc, mode="lines+markers+text", line=dict(color=T.viz[0]),
                          marker=dict(size=7, color=T.viz[0], line=dict(color=T.surface, width=2)),
                          text=[_fmt(v, suf, sc) for v in xx["value"]] if col_ == 1 else None,
                          textposition="top center", textfont=dict(family=B.FONT_MONO, size=10, color=T.ink),
                          showlegend=False, hovertemplate="%{x|%d %b %Y}: %{y:.1f}<extra></extra>", row=1, col=col_)
            sg = xx[xx["signal"]]
            if len(sg):
                f.add_scatter(x=list(sg.index), y=sg["value"] * sc, mode="markers", showlegend=False,
                              marker=dict(color=T.negative, size=11, symbol="diamond", line=dict(color=T.surface, width=2)),
                              hovertemplate="Señal · %{x|%d %b %Y}: %{y:.1f}<extra></extra>", row=1, col=col_)
        f.update_xaxes(tickvals=list(last6.index), ticktext=[f"{d.day} {B.MESES[d.month - 1]}" for d in last6.index],
                       row=1, col=1)
        f.update_xaxes(tickvals=list(last12.index), ticktext=[B.MESES[d.month - 1] for d in last12.index], row=1, col=2)
        f.update_annotations(font=dict(family=B.FONT_SANS, size=12, color=T.muted))
        st_ = state[k]
        verdict = ("dentro de lo normal" if not st_["signal"] else
                   f"señal, {'más alto' if st_['direction'] == 'arriba' else 'más bajo'} de lo normal ({st_['reason']})")
        B.chart_frame(f"612_{k}", kind, f"{nm}: {verdict}",
                      f"Última semana con dato: {_fmt(st_['value'], suf, sc)} · lo normal: {_fmt(st_['center'], suf, sc)}"
                      + (" · las tasas esperan su ventana de maduración" if k in ("work_to_eng", "sql_to_won") else ""),
                      f, pd.concat([last6.assign(vista="semana"), last12.assign(vista="mes")]).reset_index(names="periodo")[
                          ["vista", "periodo", "value", "center", "lcl", "ucl", "signal"]].assign(
                          periodo=lambda d: d["periodo"].dt.date),
                      None, 250, ysuffix=suf, month_ticks=False)

    # Lista operativa: estancados por dueño
    stl = F.stalled(r, ev, as_of)
    by_owner = stl.pivot_table(index="owner", columns="stage", values="lead_id", aggfunc="count", fill_value=0)
    by_owner["Total"] = by_owner.sum(axis=1)
    B.table_frame("stalled", "", f"{B.es(len(stl), 0)} leads abiertos superan el P90 de tiempo en su etapa",
                  "Leads estancados por dueño y etapa: la lista que cada SDR y AE limpia esta semana",
                  by_owner.sort_values("Total", ascending=False).reset_index(names="Dueño"), SRC_SYN)

    B.text_frame("rules_cro", "", "Cada entrada tiene dueño, regla de alerta y acción",
                  "Se revisa cada semana en el mismo formato; sin señal, «nada que ver aquí»", _rules_table([
                      ("Speed-to-lead P50 y SLA de 1 hora", "Líder SDR", "Señal arriba en P50, o SLA < 60 %",
                       "Ruteo automático, primer contacto con IA, ajustar capacidad"),
                      ("Mezcla de alto ajuste", "Marketing", "Señal abajo", "Revisar segmentación y metas por canal (SQL, no leads)"),
                      ("Working a Engaged", "Líder SDR", "Señal abajo", "Cruzar con speed-to-lead dentro del canal; coaching"),
                      ("SQL a Won", "Líder AE", "Señal abajo", "Revisión de deals en Demo y Proposal; criterios de SQL"),
                      ("Clientes nuevos y MRR nuevo", "CRO", "Señal abajo", "Descomponer por entrada antes de actuar"),
                  ]), SRC_SYN)
