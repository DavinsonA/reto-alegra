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
/* la historia se graba a 1440 × 900: cada paso cabe sin desplazarse */
.block-container {{ padding-top:1.25rem !important; padding-bottom:1rem !important; }}
.da-row {{ padding:10px 0 !important; }}
.da-q {{ font-size:20px !important; line-height:26px !important; margin:4px 0 6px !important; }}
.da-stop-k {{ font-size:26px !important; line-height:30px !important; margin-top:6px !important; }}
.da-stop-t {{ margin-top:6px !important; }}
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

F_ = C.FIGURES          # las tres cifras de la historia salen de la misma tabla que la nota y los hallazgos

# =====================================================================================
if i == 0:
    st.title(f"El MRR creció {F_['crec_mrr']} %, pero hoy no sabemos explicar por qué")
    s = mrr.loc["2022-03":] / 1e6
    f = go.Figure(go.Scatter(x=s.index, y=s.values, name="MRR", mode="lines", line=dict(color=T.viz[0]),
                             hovertemplate="%{x}: %{y:.1f} MM<extra></extra>"))
    B.chart_frame("h_mrr", "", f"De {F_['mrr_ini']} a {F_['mrr_fin']} MM entre marzo de 2022 y octubre de 2024",
                  "MRR mensual del modelo corregido · millones de COP", f, None, SRC_TX, 190, ysuffix=" MM")
    split([
        ("Pregunta del CFO", "¿Cuánto del cambio es el cliente y cuánto pricing o descuentos?",
         "Vienen descuentos temporales. Con el modelo actual (cliente + mes + monto pagado), un descuento y un "
         "downgrade se ven iguales."),
        ("Pregunta del CRO", "Más leads, pero no más clientes: ¿dónde se pierde el crecimiento?",
         "Marketing dice que trae más demanda; Ventas, que bajó la calidad; otros, que atendemos lento o que el "
         "problema está después de SQL."),
    ])
    st.markdown('<div class="hs-note"><b>Con qué contamos:</b> caja por cliente y mes, industria y gasto de S&M; no hay '
                'precio de lista, registro de descuentos ni eventos del funnel.<br><b>Una advertencia antes de decidir:</b> '
                f'con las unidades del enunciado, el S&M duplica el MRR ({F_["sm_vs_mrr"]} veces). Antes de cualquier '
                'decisión de inversión hay que confirmarlas con Finanzas.</div>', unsafe_allow_html=True)

# =====================================================================================
elif i == 1:
    st.title(f"El modelo de caja exagera el churn {F_['x_churn']} veces")
    fig = go.Figure()
    labels = [MOVE_LABELS[m] for m in MOVES]
    for key, tot in ((COR, tc), (ACT, ta)):
        fig.add_bar(y=labels, x=[tot.get(m, 0) / 1e6 for m in MOVES], orientation="h", name=NAME[key],
                    marker_color=MODEL_COLORS[key], hovertemplate="%{y}<br>" + NAME[key] + ": %{x:.1f} MM<extra></extra>")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=T.line, ticksuffix=" MM")
    B.chart_frame("h_bridge", "",
                  f"El total cuadra, el porqué no: churn {F_['cor_churn']} MM real contra {F_['act_churn']} MM en caja",
                  "Movimientos de MRR acumulados por tipo · millones de COP · abr-2022 a oct-2024", fig, None, SRC_TX, 340)
    B.callout("<b>Por qué:</b> la caja que no es MRR (mora y puestas al día, prepagos de varios meses, pagos agrupados y "
              "retroactivos de precio) se lee como churn, reactivación y expansión. La conclusión se sostiene al cambiar "
              f"cada regla del modelo, una a la vez: el churn queda entre {F_['sens_xchurn_min']} y "
              f"{F_['sens_xchurn_max']} veces exagerado.")

# =====================================================================================
elif i == 2:
    st.title(f"Ganamos el doble de clientes, pero entran {F_['caida_m3']} % más pequeños")
    idx = pd.DataFrame({"Clientes nuevos por mes": ny["per_month"] / ny.loc["2022", "per_month"] * 100,
                        "Ingreso por cliente nuevo (3.er mes)": ny["m3_ticket"] / ny.loc["2022", "m3_ticket"] * 100})
    f = go.Figure()
    for col, color in zip(idx.columns, T.viz[:2]):
        f.add_bar(x=[f"{y}" for y in idx.index], y=idx[col], name=col, marker_color=color,
                  text=[B.es(v, 0) for v in idx[col]], textposition="outside",
                  textfont=dict(family=B.FONT_MONO, size=12, color=T.ink),
                  hovertemplate="%{x} · " + col + ": %{y:.0f}<extra></extra>")
    f.update_yaxes(range=[0, idx.values.max() * 1.18])
    B.chart_frame("h_idx", "", "Más clientes cada año, y cada uno trae menos ingreso",
                  "Promedio de cada año, índice 2022 = 100 · 2022 desde abril, 2024 hasta octubre", f, None, SRC_TX, 320,
                  month_ticks=False)
    B.callout("<b>Lo que estos datos no dicen:</b> si la caída viene del canal (más self-serve), del plan o tamaño del "
              "cliente, o de descuentos de entrada. Ninguna de las explicaciones del equipo (demanda, calidad, velocidad, "
              "post-SQL) se puede confirmar ni descartar sin eventos del funnel.")

# =====================================================================================
elif i == 3:
    st.title("Con el modelo actual, Finora invertiría en el lugar equivocado")
    B.text_frame("h_impl", "", "Cada lectura del modelo actual empuja una decisión distinta",
                 "Lo que dice hoy el modelo de caja frente a lo que muestran los datos corregidos", pd.DataFrame([
                     ("Retención", "Perdemos mucho MRR por churn", "El churn real es varias veces menor, y las "
                      "cohortes conservan la mayor parte de su ingreso", "Sobreinvertir en retención"),
                     ("Descuentos", "Cuando vence un descuento, el MRR «crece»",
                      "Es una decisión de pricing, no expansión del cliente",
                      "Premiar descuentos como crecimiento y no saber cuánto cuestan"),
                     ("Cobranza", "Un cliente que no paga es churn", "Parte de ese MRR está en mora y se puede cobrar",
                      "Dar por perdidas cuentas que se pueden cobrar"),
                     ("Ventas", "Más leads es más demanda: más SDR o más presupuesto",
                      "Entran clientes más pequeños en todas las industrias, y no sabemos por qué",
                      "Contratar o recortar canales a ciegas"),
                 ], columns=["Tema", "El modelo actual dice", "Los datos muestran", "Riesgo de decidir con el actual"]))

# =====================================================================================
elif i == 4:
    st.title("El fin de un descuento no es expansión: hay que medir el MRR en dos capas")
    mv = two_layer_movements([100, 130, 130], [0, 30, 0])          # el motor de dos capas, no texto escrito a mano
    names = {"expansion": "Expansión", "contraction": "Contracción", "discount_start": "Inicio de descuento",
             "discount_end": "Fin de descuento"}

    def moves(t: int, layer: str) -> str:
        r = mv[(mv["t"] == t) & (mv["layer"] == layer)]
        return ", ".join(f"{names.get(m, m)} {'+' if a > 0 else ''}{B.es(a, 0)}"
                         for m, a in zip(r["movement"], r["amount"])) or "—"

    B.text_frame("h_case", "", "Un cliente sube de plan con un descuento que vence al mes siguiente",
                 "Plan de 100 a 130 con un descuento de 30 · el modelo actual ve la expansión un mes tarde y en el lugar "
                 "equivocado",
                 pd.DataFrame({"Mes": ["1 · upgrade con descuento", "2 · vence el descuento"],
                               "Paga": ["100 a 100", "100 a 130"],
                               "Modelo actual": ["Sin cambio: la expansión queda escondida", "Expansión +30"],
                               "Dos capas · cliente": [moves(1, "customer"), moves(2, "customer")],
                               "Dos capas · pricing": [moves(1, "pricing"), moves(2, "pricing")]}),
                 "Mismo resultado en Python y en SQL · sql/03_movimientos_dos_capas.sql")
    rows([
        ("Medir el MRR en dos capas", "<b>Neto = lista − descuento.</b> Cada descuento se registra con inicio, fin, motivo "
         "y aprobador.", "Responde al CFO: cuánto es cliente y cuánto pricing o descuentos"),
        ("Separar la caja del MRR", "La mora no es churn hasta confirmarse (2 meses sin pago); Cobranza actúa antes.",
         "Responde al CFO"),
        ("Medir el funnel por eventos", "Conversión por cohorte y camino, y tiempo al primer contacto.", "Responde al CRO"),
    ])
    B.callout("<b>Lo que no decidiría todavía:</b> contratar SDR, recortar canales o mover el S&M sin el funnel por "
              "eventos.", kind="warn")

# =====================================================================================
else:
    st.title("En 90 días, cada cierre puede separar lo que hace el cliente de lo que decide Finora")
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
    tablero = f'<a href="{C.LINKS["tablero"]}">tablero operativo</a>' if C.LINKS["tablero"] else "tablero operativo"
    split([
        ("Cómo se opera · CFO, mensual en el cierre", "¿El cambio del mes es señal o ruido?",
         f"Puente en dos capas, rango normal de cada movimiento, lo que está en confirmación, y dueño y acción por "
         f"métrica. Datos reales, en el {tablero}."),
        ("Cómo se opera · CRO, semanal en 30 minutos", "¿Qué entrada se salió de lo normal?",
         f"Mismo formato cada semana (6 semanas y 12 meses), árbol de métricas y leads estancados por dueño. Prototipo "
         f"sintético en el {tablero} hasta tener los eventos."),
    ])
    B.callout("<p><b>Lo que pido hoy</b></p><ul><li>Registrar desde ya todo descuento nuevo con motivo, vigencia y "
              "aprobador.</li><li>Acceso a los datos de facturación y a los eventos del CRM.</li><li>Validar con Finanzas "
              "las unidades y el alcance del S&M.</li></ul>")
pager()
