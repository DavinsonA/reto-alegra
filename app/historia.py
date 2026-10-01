"""Finora · historia ejecutiva (video 1, para CEO, CFO y CRO).

Situación, hallazgos, implicación, decisión y acción: una idea por pantalla, con botones para avanzar.
Todas las cifras salen de las mismas tablas agregadas que usan la demo y el tablero.
Dirección visual: claridad suiza dentro de la marca. Bordes sin sombra, pocas cajas; lo que es una lista ordenada
se dibuja como filas numeradas y lo que es tiempo, como un riel.
Ejecutar:  streamlit run app/historia.py
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path[:0] = [str(APP.parent), str(APP)]

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import brand as B  # noqa: E402
import common as C  # noqa: E402
from common import ACT, COR, MOVE_LABELS, MOVES, SRC_TX  # noqa: E402
from finora.two_layer import two_layer_movements  # noqa: E402

SCREENS = ["1 · Situación", "2 · Hallazgo del MRR", "3 · Hallazgo de ventas", "4 · Implicación", "5 · Decisión",
           "6 · Acción"]
T, section = C.page("historia", SCREENS, "para CEO, CFO y CRO")
NAME = {COR: "Modelo corregido", ACT: "Modelo actual (caja)"}   # sin jerga de reglas para un público ejecutivo
MODEL_COLORS = {COR: T.viz[0], ACT: T.viz[1]}
i = SCREENS.index(section)

st.markdown(f"""<style>
.hs-steps {{ display:flex; gap:6px; margin:0 0 6px; }}
.hs-steps span {{ flex:1; height:4px; border-radius:999px; background:{T.line}; }}
.hs-steps span.on {{ background:{T.viz[0]}; }}
.hs-note {{ font:400 15px/24px var(--font-sans); color:var(--ink-muted); max-width:78ch; margin:0 0 8px; }}
.hs-note b {{ color:var(--ink); }}
</style>""", unsafe_allow_html=True)


def steps() -> None:
    bars = "".join(f'<span class="{"on" if j <= i else ""}"></span>' for j in range(len(SCREENS)))
    st.markdown(f'<div class="hs-steps">{bars}</div><div class="da-overline">Paso {i + 1} de {len(SCREENS)} · '
                f'{html.escape(section.split("· ", 1)[1])}</div>', unsafe_allow_html=True)


def split(items: list[tuple[str, str, str]]) -> None:
    """Dos columnas separadas por una regla: (quién, pregunta o idea, cuerpo en HTML)."""
    cols = "".join(f'<div><div class="da-q-who">{html.escape(w)}</div><div class="da-q">{html.escape(q)}</div>'
                   f'<div class="da-q-b">{b}</div></div>' for w, q, b in items)
    st.markdown(f'<div class="da-split">{cols}</div>', unsafe_allow_html=True)


def rows(items: list[tuple[str, str, str]]) -> None:
    """Lista ordenada con líneas finas: (título, cuerpo en HTML, nota)."""
    out = "".join(f'<div class="da-row"><div class="da-row-n">{n}</div><div class="da-row-t">{html.escape(t)}</div>'
                  f'<div class="da-row-b">{b}<small>{html.escape(s)}</small></div></div>'
                  for n, (t, b, s) in enumerate(items, start=1))
    st.markdown(f'<div class="da-rows">{out}</div>', unsafe_allow_html=True)


def rail(items: list[tuple[str, str, str, str]]) -> None:
    """Riel de tiempo: (plazo, dueño, título, cuerpo en HTML)."""
    out = "".join(f'<div class="da-stop"><div class="da-stop-k">{html.escape(k)}</div><div class="da-stop-o">'
                  f'{html.escape(o)}</div><div class="da-stop-t">{html.escape(t)}</div><div class="da-stop-b">{b}</div></div>'
                  for k, o, t, b in items)
    st.markdown(f'<div class="da-rail" style="--n:{len(items)}">{out}</div>', unsafe_allow_html=True)


def go_to(j: int) -> None:
    st.session_state["sec"] = SCREENS[j]


def pager() -> None:
    st.write("")
    c1, _, c2 = st.columns([2, 3, 3])
    if i > 0:
        c1.button("Anterior", key="prev", on_click=go_to, args=(i - 1,), width="stretch")
    if i < len(SCREENS) - 1:
        c2.button(f"Siguiente: {SCREENS[i + 1].split('· ', 1)[1]}", key="next", type="primary", on_click=go_to,
                  args=(i + 1,), width="stretch")


ta, tc = C.bridge_totals(ACT), C.bridge_totals(COR)
ny = C.new_by_year()
hc = C.half_cut()
mrr = C.mrr_series(COR)
cust = sum(tc.get(m, 0) for m in C.CUSTOMER_MOVES)
steps()

# =====================================================================================
if i == 0:
    m0, m1 = mrr.loc["2022-03"], mrr.iloc[-1]
    st.title(f"El MRR pasó de {B.es(m0 / 1e6)} a {B.mm(m1)}, pero hoy no sabemos explicar por qué")
    s = mrr.loc["2022-03":] / 1e6
    f = go.Figure(go.Scatter(x=s.index, y=s.values, name="MRR", mode="lines", line=dict(color=T.viz[0]),
                             hovertemplate="%{x}: %{y:.1f} MM<extra></extra>"))
    B.chart_frame("h_mrr", "", f"El MRR creció {B.es((m1 / m0 - 1) * 100, 0)} % desde marzo de 2022",
                  "MRR mensual del modelo corregido · millones de COP · mar-2022 a oct-2024", f,
                  s.round(1).reset_index().set_axis(["Mes", "MRR (MM)"], axis=1), SRC_TX, 280, ysuffix=" MM")
    split([
        ("Pregunta del CFO", "¿Cuánto del cambio es el cliente y cuánto pricing o descuentos?",
         "Vienen descuentos temporales. Con el modelo actual (cliente + mes + monto pagado), un descuento y un "
         "downgrade se ven iguales."),
        ("Pregunta del CRO", "Más leads, pero no más clientes: ¿dónde se pierde el crecimiento?",
         "Marketing dice que trae más demanda; Ventas, que bajó la calidad; otros, que atendemos lento o que el "
         "problema está después de SQL."),
    ])
    st.markdown('<div class="hs-note"><b>Con qué contamos:</b> caja por cliente y mes, industria y gasto de S&M. No hay '
                'precio de lista, registro de descuentos ni eventos del funnel; lo que falta también es parte de la '
                'respuesta.</div>', unsafe_allow_html=True)

# =====================================================================================
elif i == 1:
    st.title("El total cuadra, pero el modelo actual explica mal por qué cambió el MRR")
    B.kpi_row([
        dict(overline="Comportamiento del cliente", value=B.mm(cust, sign=True), pastel=True,
             foot="nuevos + expansión + reactivación − contracción − churn"),
        dict(overline="Subidas de precio", value=B.mm(tc.get("price_uplift", 0), sign=True),
             foot=f"{B.es(tc.get('price_uplift', 0) / tc.sum() * 100, 0)} % del cambio neto · decisión de Finora"),
        dict(overline="Descuentos", value="Sin dato", delta=f"0 a {B.mm(hc['foregone_cop'].sum())}",
             foot=f"{int(hc['events'].sum())} bajadas exactas a la mitad: ¿descuento o downgrade?"),
        dict(overline="Churn real", value=B.mm(tc["churn"]), delta=f"{B.es(ta['churn'] / tc['churn'], 1)}× exagerado",
             foot=f"vs. {B.mm(ta['churn'])} en el modelo actual"),
    ])
    fig = go.Figure()
    labels = [MOVE_LABELS[m] for m in MOVES]
    for key, tot in ((COR, tc), (ACT, ta)):
        fig.add_bar(y=labels, x=[tot.get(m, 0) / 1e6 for m in MOVES], orientation="h", name=NAME[key],
                    marker_color=MODEL_COLORS[key], hovertemplate="%{y}<br>" + NAME[key] + ": %{x:.1f} MM<extra></extra>")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=T.line, ticksuffix=" MM")
    B.chart_frame("h_bridge", "",
                  f"El modelo actual exagera el churn {B.es(ta['churn'] / tc['churn'], 1)}× y la reactivación "
                  f"{B.es(ta['reactivation'] / tc['reactivation'], 0)}×",
                  "Movimientos de MRR acumulados por tipo · millones de COP · abr-2022 a oct-2024", fig,
                  pd.DataFrame({"Movimiento": labels, NAME[COR]: [round(tc.get(m, 0) / 1e6, 1) for m in MOVES],
                                NAME[ACT]: [round(ta.get(m, 0) / 1e6, 1) for m in MOVES]}), SRC_TX, 360)
    B.callout(f"<b>Por qué:</b> {B.mm(C.nonmrr_cash().sum())} de caja no son MRR: mora y puestas al día, prepagos de "
              "varios meses, pagos agrupados y retroactivos de precio. El modelo actual los lee como churn, reactivación "
              "y expansión. La conclusión se sostiene con cualquier regla de mora entre 1 y 3 meses.")

# =====================================================================================
elif i == 2:
    st.title("Ganamos el doble de clientes, pero entran más pequeños")
    kt = C.ticket_kitagawa()
    share_in = kt["rate"].sum() / (kt["mix"].sum() + kt["rate"].sum())
    B.kpi_row([
        dict(overline="Clientes nuevos por mes · 2024", value=B.es(ny.loc["2024", "per_month"], 0), pastel=True,
             delta=f"+{B.es((ny.loc['2024', 'per_month'] / ny.loc['2022', 'per_month'] - 1) * 100, 0)} %", delta_kind="up",
             foot=f"vs. {B.es(ny.loc['2022', 'per_month'], 0)} en 2022"),
        dict(overline="MRR nuevo por mes · 2024", value=B.mm(ny.loc["2024", "mrr_per_month"]),
             delta=f"+{B.es((ny.loc['2024', 'mrr_per_month'] / ny.loc['2022', 'mrr_per_month'] - 1) * 100, 0)} %",
             delta_kind="up", foot=f"vs. {B.mm(ny.loc['2022', 'mrr_per_month'])} en 2022"),
        dict(overline="Ingreso mensual por cliente nuevo", value=f"{B.es(ny.loc['2024', 'm3_ticket'] / 1e3, 0)} mil",
             delta=f"−{B.es((1 - ny.loc['2024', 'm3_ticket'] / ny.loc['2022', 'm3_ticket']) * 100, 0)} %", delta_kind="down",
             foot=f"en su 3.er mes · vs. {B.es(ny.loc['2022', 'm3_ticket'] / 1e3, 0)} mil COP en 2022"),
    ])
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        idx = pd.DataFrame({"Clientes nuevos por mes": ny["per_month"] / ny.loc["2022", "per_month"] * 100,
                            "MRR nuevo por mes": ny["mrr_per_month"] / ny.loc["2022", "mrr_per_month"] * 100})
        f = go.Figure()
        for col, color in zip(idx.columns, T.viz[:2]):
            f.add_bar(x=[f"{y}" for y in idx.index], y=idx[col], name=col, marker_color=color,
                      text=[B.es(v, 0) for v in idx[col]], textposition="outside",
                      textfont=dict(family=B.FONT_MONO, size=12, color=T.ink),
                      hovertemplate="%{x} · " + col + ": %{y:.0f}<extra></extra>")
        f.update_yaxes(range=[0, idx.values.max() * 1.18])
        B.chart_frame("h_idx", "",
                      f"Los clientes nuevos se duplicaron; el MRR nuevo creció "
                      f"{B.es(idx.loc['2024', 'MRR nuevo por mes'] - 100, 0)} %",
                      "Promedio mensual de cada año, índice 2022 = 100 · 2022 desde abril, 2024 hasta octubre", f,
                      idx.round(0).reset_index(names="Año"), SRC_TX, 340, month_ticks=False)
    with c2:
        k2 = kt.sort_values("rate", ascending=False)
        f2 = go.Figure()
        f2.add_bar(y=k2.index, x=k2["rate"], orientation="h", name="Dentro de la industria", marker_color=T.viz[0],
                   hovertemplate="%{y}<br>Dentro de la industria: %{x:,.0f} COP<extra></extra>")
        f2.add_bar(y=k2.index, x=k2["mix"], orientation="h", name="Mezcla de industrias", marker_color=T.viz[1],
                   hovertemplate="%{y}<br>Mezcla: %{x:,.0f} COP<extra></extra>")
        f2.update_yaxes(showgrid=False)
        f2.update_xaxes(showgrid=True, gridcolor=T.line, ticksuffix=" COP")
        B.chart_frame("h_kit", "",
                      f"El {B.es(share_in * 100, 0)} % de la caída del ticket ocurre dentro de cada industria; "
                      "Retail, la mayor",
                      "Aporte de cada industria al cambio del ticket de entrada 2022 a 2024 · COP por cliente", f2,
                      kt.round(0).reset_index(names="Industria").rename(columns={
                          "ticket0": "Ticket 2022", "ticket1": "Ticket 2024", "mix": "Efecto mezcla",
                          "rate": "Efecto dentro"}), SRC_TX, 340)
    B.callout("<b>Lo que estos datos no dicen:</b> si la caída viene del canal (más self-serve), del plan o tamaño del "
              "cliente, o de descuentos de entrada. Ninguna de las explicaciones del equipo (demanda, calidad, velocidad, "
              "post-SQL) se puede confirmar ni descartar sin eventos del funnel.")

# =====================================================================================
elif i == 3:
    st.title("Con el modelo actual, Finora invertiría en el lugar equivocado")
    B.text_frame("h_impl", "", "Cada lectura del modelo actual empuja una decisión distinta",
                 "Lo que dice hoy el modelo de caja frente a lo que muestran los datos corregidos", pd.DataFrame([
                     ("Retención", f"Perdemos {B.mm(-ta['churn'])} por churn; cada cohorte conserva "
                                   f"{B.pct(C.nrr12(ACT, '2023'))} de su ingreso a 12 meses",
                      f"El churn real es {B.mm(-tc['churn'])}; la cohorte conserva {B.pct(C.nrr12(COR, '2023'))}",
                      "Sobreinvertir en retención"),
                     ("Descuentos", "Cuando vence un descuento, el MRR «crece»",
                      "Es una decisión de pricing, no expansión del cliente",
                      f"Premiar descuentos como crecimiento; no saber su costo (hasta {B.mm(hc['foregone_cop'].sum())})"),
                     ("Cobranza", "Un cliente que no paga es churn",
                      f"{B.mm(C.delinquent_open_last())} del MRR de oct-2024 está en mora sin confirmar",
                      "Dar por perdidas cuentas que se pueden cobrar"),
                     ("Ventas", "Más leads es más demanda: más SDR o más presupuesto",
                      "Entran clientes más pequeños en todas las industrias, y no sabemos por qué",
                      "Contratar o recortar canales a ciegas"),
                 ], columns=["Tema", "El modelo actual dice", "Los datos muestran", "Riesgo de decidir con el actual"]))
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        years = ["2022", "2023"]
        f = go.Figure()
        for key in (COR, ACT):
            f.add_bar(x=[f"Altas {y}" for y in years], y=[C.nrr12(key, y) * 100 for y in years], name=NAME[key],
                      marker_color=MODEL_COLORS[key], text=[B.pct(C.nrr12(key, y)) for y in years],
                      textposition="outside", textfont=dict(family=B.FONT_MONO, size=12, color=T.ink),
                      hovertemplate="%{x} · " + NAME[key] + ": %{y:.0f} %<extra></extra>")
        f.update_yaxes(range=[0, 110])
        B.chart_frame("h_nrr", "", "Cada cohorte conserva más ingreso del que muestra el modelo actual",
                      "Ingreso que conserva cada año de altas a los 12 meses (NRR), ponderado por MRR inicial · %", f,
                      pd.DataFrame({"Cohorte": years, NAME[COR]: [round(C.nrr12(COR, y) * 100, 1) for y in years],
                                    NAME[ACT]: [round(C.nrr12(ACT, y) * 100, 1) for y in years]}), SRC_TX, 300,
                      ysuffix=" %")
    with c2:
        B.callout("<b>Pregunta abierta para Finanzas: el S&M equivale a unas 2 veces el MRR.</b> Con las unidades del "
                  "enunciado, el gasto mensual de S&M es cerca de 200 MM y el MRR, 98 MM. O la eficiencia comercial es "
                  "el problema principal, o hay que revisar las unidades. Lo valido antes de concluir.")

# =====================================================================================
elif i == 4:
    st.title("Tres decisiones: MRR en dos capas, caja aparte y funnel por eventos")
    rows([
        ("Medir el MRR en dos capas",
         "<b>Neto = lista − descuento.</b> Cada descuento se registra con inicio, fin, motivo y aprobador. Así se "
         "responde cada mes cuánto es cliente y cuánto pricing o descuentos.", "Responde al CFO"),
        ("Separar la caja del MRR",
         "La mora no es churn hasta confirmarse: 2 meses sin pago, y la conclusión se sostiene con 1 o 3. Cobranza ve "
         "el MRR en mora y actúa antes.", "Responde al CFO"),
        ("Medir el funnel por eventos y caminos",
         "Self-serve, directo a SQL y recorrido SDR, con conversión por cohorte y tiempo al primer contacto. Así se "
         "prueba cada hipótesis del equipo.", "Responde al CRO"),
    ])
    mv = two_layer_movements([100, 130, 130], [0, 30, 0])          # el motor de dos capas, no texto escrito a mano
    names = {"expansion": "Expansión", "contraction": "Contracción", "discount_start": "Inicio de descuento",
             "discount_end": "Fin de descuento"}

    def moves(t: int, layer: str) -> str:
        r = mv[(mv["t"] == t) & (mv["layer"] == layer)]
        return ", ".join(f"{names.get(m, m)} {'+' if a > 0 else ''}{B.es(a, 0)}"
                         for m, a in zip(r["movement"], r["amount"])) or "—"

    B.text_frame("h_case", "", "Ejemplo de la decisión 1: el fin de un descuento no es expansión",
                 "Un cliente pasa de un plan de 100 a uno de 130 con un descuento de 30; al mes siguiente vence el descuento",
                 pd.DataFrame({"Mes": ["1 · upgrade con descuento", "2 · vence el descuento"],
                               "Paga": ["100 a 100", "100 a 130"],
                               "Modelo actual": ["Sin cambio: la expansión queda escondida", "Expansión +30"],
                               "Dos capas · cliente": [moves(1, "customer"), moves(2, "customer")],
                               "Dos capas · pricing": [moves(1, "pricing"), moves(2, "pricing")]}),
                 "Mismo resultado en Python y en SQL · sql/03_movimientos_dos_capas.sql")
    B.callout("<b>Lo que no decidiría todavía:</b> contratar SDR, recortar canales o mover el presupuesto de S&M. "
              "Primero el funnel por eventos y la validación de las unidades del S&M con Finanzas.", kind="warn")

# =====================================================================================
else:
    st.title("Plan a 90 días, con dueño y una revisión fija desde el primer mes")
    rail([
        ("30 días", "Finanzas y BI", "Publicar el MRR corregido y registrar descuentos",
         "Todo descuento nuevo se registra con motivo, vigencia y aprobador <b>antes</b> de lanzarlo. Arranca la "
         "revisión mensual del MRR."),
        ("60 días", "BI y Facturación", "Precio de lista y motivo de cada cambio",
         "List MRR y motivo del cambio desde facturación. Puente en dos capas, retención a lista y neta, y costo de los "
         "descuentos en la revisión del CFO."),
        ("90 días", "RevOps y CRO", "Funnel por eventos en el CRM",
         "Etapas con fecha y hora, canal, camino y dueño. Arranca la revisión semanal de 30 minutos con alertas "
         "estadísticas."),
    ])
    st.subheader("Cómo se opera")
    split([
        ("CFO · mensual, en el cierre", "¿El cambio del mes es señal o ruido?",
         "Puente del mes, rango normal de cada movimiento, churn en confirmación, y dueño y acción por métrica. Datos "
         "reales."),
        ("CRO · semanal, 30 minutos", "¿Qué entrada se salió de lo normal?",
         "Mismo formato cada semana (6 semanas y 12 meses), árbol de métricas y leads estancados por dueño. Prototipo "
         "con datos sintéticos hasta tener los eventos."),
    ])
    st.markdown(f"Las dos revisiones están en el {C.link('tablero', 'tablero operativo')}.")
    B.callout("<p><b>Lo que pido hoy</b></p><ul><li>Registrar desde ya todo descuento nuevo con motivo, vigencia y "
              "aprobador.</li><li>Acceso a los datos de facturación y a los eventos del CRM.</li><li>Validar con Finanzas "
              "las unidades y el alcance del S&M.</li></ul>")
pager()
