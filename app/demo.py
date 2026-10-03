"""Finora · demo y proceso con IA (video 2)."""
from __future__ import annotations

import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path[:0] = [str(APP.parent), str(APP)]

import fresh

fresh.reload_project_modules()

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import brand as B
import common as C
from common import (ACT, COR, MOVE_LABELS, MOVES, SRC_SYN, SRC_TX, WINDOW_START, bridge_totals, load,
                    mrr_series, nrr12, synthetic)
from finora import funnel as F
from finora.funnel_synth import CHANNELS
from finora.two_layer import two_layer_movements

S_IA = "Proceso · cómo trabajé con IA"
S_CFO = "Caso CFO · ¿por qué cambió el MRR?"
S_CRO = "Caso CRO · el funnel"
S_DM = "Fundamentos · modelo de datos propuesto"
S_SM = "Fundamentos · S&M y eficiencia"
S_DQ = "Fundamentos · calidad de datos y supuestos"
SECTIONS = [S_IA, S_CFO, S_CRO, S_DM, S_SM, S_DQ]

T, section = C.page("demo", SECTIONS, "cómo lo resolví y con qué evidencia")
MOVE_COLORS = dict(zip(MOVES, T.viz))
MODEL_COLORS = {COR: T.viz[0], ACT: T.viz[1]}
CHANNEL_COLORS = dict(zip(CHANNELS, T.viz))
ta, tc = bridge_totals(ACT), bridge_totals(COR)
ny = C.new_by_year()

if section == S_IA:
    st.title("Cómo trabajé con IA: preparar, explorar, proponer, revisar y comunicar")
    B.tags([("lavender", ["Claude Code", "Claude con búsqueda web", "skills: davinson-brand, dataviz, avoid-ai-design, grill-me"]),
            ("mint", ["Python", "pandas", "SQL", "DuckDB", "Jupyter"]), ("peach", ["Streamlit", "Plotly"]),
            ("", ["pytest", "Playwright", "Git", "GitHub Actions"])])
    ERRORS = pd.DataFrame([
        ("El motor leía un upgrade real (el cliente duplica su plan y se queda) como un pago agrupado",
         "Revisión de la regla contra series reales", "Condición «el monto alto no se mantiene» y una prueba nueva"),
        ("Prepagos anuales contados como «nuevo + churn»",
         "Prueba de robustez: el MRR al 3.er mes no cuadraba con el del 1.er mes",
         f"Regla de prepago y 2 pruebas · el churn corregido pasó de {C.FIGURES['churn_sin_prepagos']} a "
         f"{C.FIGURES['cor_churn']} MM"),
        (f"{C.FIGURES['caja_prepaid_pending_n']} pagos grandes al final de la serie leídos como MRR; uno aparecía como una "
         "reactivación de 1,1 MM de un cliente que paga cada 12 a 14 meses",
         "Revisión del tablero: reactivación de oct-2024 diez veces mayor que el ticket promedio",
         f"Prepago en confirmación (censura a la derecha) y una prueba · el MRR de oct-2024 pasó de 97,6 a "
         f"{C.FIGURES['mrr_fin']} MM"),
        (f"{C.FIGURES['precio_pend_n']} subidas de precio del último mes dadas por confirmadas sin mes siguiente",
         "Lectura del código: la persistencia se suponía cuando no había mes siguiente",
         "Quedan «en confirmación», igual que el churn final, con una prueba"),
        ("La sensibilidad que apagaba las puestas al día con tolerancia 0 no las apagaba",
         "Prueba: los montos de los datos son múltiplos exactos", "Interruptor explícito de la regla y una prueba"),
        ("Un reemplazo automático dejó sin nombre una sección de esta demo",
         "Revisión visual de la barra lateral", "Se restauró y una prueba falla si una sección queda sin nombre"),
        ("Churn en 0 «dentro de lo normal» en los 2 últimos meses, que aún no se pueden confirmar",
         "Revisión visual del tablero mensual", "Se muestran «en confirmación», con el MRR en mora y su acción"),
        ("Dos cifras distintas para las bajadas a la mitad (87 y 40,9 MM frente a 85 y 39,1 MM)",
         "Revisión cruzada entre la app y HALLAZGOS.md", "Una sola definición de ventana: 85 eventos y 40,8 MM"),
        ("El gráfico de control del funnel casi no alertaba",
         "Prueba con problemas plantados a propósito", "Regla de rachas de 8 semanas: detecta el cambio de nivel"),
        ("Una paleta de colores que no pasaba la prueba de daltonismo",
         "Script de validación de la paleta", "Cambio de colores, validado en modo claro y oscuro"),
        ("El NRR de las altas de 2022 salía distinto en la app (53 %) y en HALLAZGOS.md (50 %)",
         "Revisión visual de la historia ejecutiva", "La app incluía altas de ene–mar 2022, fuera de la ventana; se unificó"),
        ("Una prueba mía mal planteada (esperaba churn con solo 2 meses en 0 al final)",
         "La prueba falló contra el motor", "Corregí la prueba, no el motor: con N = 2 es mora abierta"),
    ], columns=["Error", "Cómo lo detecté", "Corrección"])
    B.kpi_row([
        dict(overline="Pruebas automáticas", value=str(C.N_TESTS), pastel=True, foot="motor, dos capas, SQL, XmR, S&M, documentos y las 3 apps"),
        dict(overline="Doble cálculo", value="SQL = Python", foot="puente del modelo actual y casos de dos capas, por dos vías"),
        dict(overline="Revisión manual", value="11 clientes", foot="series reales leídas una a una"),
        dict(overline="Errores atrapados", value=str(len(ERRORS)), foot="antes de llegar a una cifra final"),
    ])
    B.text_frame("ia_steps", "", "Cinco fases: en cada una, qué hizo la IA y qué hice yo",
                 "La IA acelera la investigación, la exploración y el código; las preguntas, las reglas y la verificación son mías",
                 pd.DataFrame([
                     ("1 · Preparar con Claude Code",
                      "Resumió el enunciado, investigó buenas prácticas con 58 fuentes y dejó la documentación de trabajo "
                      "(contexto del reto y bitácora AI_LOG)",
                      "Ronda inicial de preguntas: unidades de los CSV, plazo en días calendario, repositorio público o privado, "
                      "funnel sin datos, Streamlit en vez de Power BI, prototipo sintético rotulado",
                      "research/reto-tecnico.md · AI_LOG.md · skills de marca, visualización, revisión de diseño y grill-me (interrogar el plan)"),
                     ("2 · Explorar en notebooks",
                      "Perfiló los 3 CSV y escribió 5 notebooks, del perfilado a las conclusiones, guardados con sus salidas",
                      "Leí a mano las series de 11 clientes y formulé los patrones: mora y puestas al día, retroactivo "
                      "1 + k·p, bajadas a la mitad; fijé el supuesto cero (0 = no se cobró)",
                      "notebooks/01 a 05 · cada uno recalcula sus cifras y falla si no coinciden con key_figures.csv"),
                     ("3 · Proponer por caso",
                      "Propuso alternativas y la práctica de mercado (ChartMogul, dbt, Stripe) y escribió el motor de MRR, el "
                      "modelo de dos capas, el diseño del funnel y las métricas de eficiencia del S&M",
                      "Decidí las reglas (mora N = 2, prepagos, precio aparte, dos capas), prioricé al CFO porque el funnel "
                      "hereda el error del MRR, y dejé escrito lo que no se puede concluir",
                      "Casos con respuesta conocida: las 3 preguntas del CFO, mora, prepagos y bordes"),
                     ("4 · Revisar el modelo",
                      "Escribió el puente del modelo actual y los casos de dos capas en SQL (DuckDB) y la sensibilidad por regla",
                      "Exigí SQL = Python, apagué cada regla una a la vez y pedí a otra sesión de Claude, con la skill grill-me, una "
                      "revisión como evaluador exigente",
                      f"{C.N_TESTS} pruebas · 10 variantes sin cambio de signo · {len(ERRORS)} errores atrapados"),
                     ("5 · Comunicar",
                      "Tres apps en Streamlit con Plotly, marca propia y capturas automáticas con Playwright",
                      "Definí qué decisión apoya cada vista y revisé cada pantalla renderizada",
                      "Prueba automática de cada vista · paleta validada para daltonismo · apps despiertas con GitHub Actions"),
                 ], columns=["Fase", "Qué hizo la IA", "Qué decidí o revisé yo", "Evidencia"]))
    B.text_frame("ia_refs", "", "Lo que dijeron las referencias y qué decidí con cada una",
                 "De la investigación previa (58 fuentes) a las reglas del modelo; donde me aparto del mercado, queda documentado",
                 pd.DataFrame([
                     ("ChartMogul · movimientos de MRR y mora",
                      "Aplicar un descuento es contracción y su fin, expansión; las suscripciones en mora siguen en el MRR hasta cancelarse",
                      "Adopto la mora tolerada (N = 2). Me aparto en descuentos: su fin va en la capa de pricing"),
                     ("dbt · MRR playbook",
                      "Malla de fechas con lag() para capturar churn y reactivación",
                      "La malla cliente × mes del CSV se usa tal cual; un 0 es «no se cobró»"),
                     ("Stripe, Baremetrics, ProfitWell",
                      "No hay un estándar: cada herramienta resta los descuentos de forma distinta",
                      "Net MRR como cifra oficial; list MRR y descuentos como capa analítica"),
                     ("Austin Yang · SaaSHero",
                      "La conversión de foto mezcla cohortes y cae mecánicamente cuando sube el volumen",
                      "Conversión por cohorte de creación con ventana fija; cohortes inmaduras aparte"),
                     ("Kitagawa · Das Gupta",
                      "Δ de una tasa = efecto mezcla + efecto tasa",
                      "Mezcla vs. tasa por industria (datos reales) y por canal (diseño del funnel)"),
                     ("HBR · Oldroyd et al., 2011",
                      "Contactar en la primera hora: casi 7 veces más probabilidad de calificar el lead",
                      "Speed-to-lead y SLA de 1 hora como entrada controlable del CRO"),
                     ("Winning by Design · bowtie",
                      "Volumen, conversión y tiempo por etapa; una sola fuente de verdad",
                      "Tres caminos (self-serve, directo a SQL, SDR) sobre un modelo de eventos"),
                     ("Commoncog · WBR de Amazon y Wheeler",
                      "Dueños, formato fijo 6-12, límites XmR y «nada que ver aquí»",
                      "Revisión mensual y semanal con señal frente a ruido, dueño, regla y acción"),
                     ("Stephen Few",
                      "Monitorear de un vistazo; un número sin contexto no dice nada",
                      "4 KPI por fila con vs. mes anterior y hace 12 meses, y estado con palabra"),
                     ("Scale Venture Partners · a16z",
                      "Magic number: 0,75 para escalar; el CAC combinado no dice qué canal funciona",
                      "Magic number y payback por cohorte como métricas nuevas; sin conclusión por canal"),
                 ], columns=["Fuente", "Qué dice", "Qué decidí"]))
    B.text_frame("ia_errors", "", f"{len(ERRORS)} errores atrapados antes de llegar a una cifra final",
                 "Errores de la IA y míos, cómo los detecté y qué cambió", ERRORS)
    c1, c2 = st.columns(2, gap="medium")
    c1.subheader("Reglas que seguí")
    c1.markdown("- Las reglas de negocio las decido yo y quedan escritas como supuestos.\n"
                "- Ninguna cifra sale del chat: sale de código con prueba, y los notebooks la recalculan.\n"
                "- Lo crítico se calcula dos veces, por dos vías.\n"
                "- Cada pantalla se renderiza y se mira antes de darla por buena.")
    c2.subheader("Datos")
    c2.markdown("- Las apps públicas solo usan tablas agregadas; el exportador falla si alguna trae `customer_id`.\n"
                "- Los CSV originales no están en el repositorio.\n"
                "- El funnel es sintético y está rotulado en cada gráfico.")
    st.caption("Bitácora completa (AI_LOG.md), investigación (research/reto-tecnico.md), notebooks, código y pruebas en el repositorio.")

elif section == S_CFO:
    st.title("¿Por qué cambió nuestro MRR?")
    st.caption("Modelo actual (caja) vs. modelo corregido · abril 2022 a octubre 2024 · millones de COP")
    scen = st.selectbox("Regla del modelo corregido", [COR, "Corregido (N=1)", "Corregido (N=3)",
                                                       "Corregido sin separar precio", "Corregido, mora final = churn"],
                        help="N = meses en 0 que se toleran como mora antes de declarar churn. Sirve para ver cuánto "
                             "dependen las conclusiones de cada regla.")
    tcs = bridge_totals(scen)
    B.kpi_row([
        dict(overline="Cambio neto del MRR", value=B.mm(tcs.sum(), sign=True), pastel=True,
             foot=f"igual en ambos modelos ({B.mm(ta.sum(), sign=True)} en el actual)"),
        dict(overline="Churn", value=B.mm(tcs["churn"]), delta=f"{B.es(ta['churn'] / tcs['churn'], 1)}×",
             foot=f"vs. {B.mm(ta['churn'])} en el modelo actual"),
        dict(overline="Reactivación", value=B.mm(tcs["reactivation"], sign=True),
             delta=f"{B.es(ta['reactivation'] / tcs['reactivation'], 0)}×",
             foot=f"vs. {B.mm(ta['reactivation'], sign=True)} en el modelo actual"),
        dict(overline="Contracción", value=B.mm(tcs["contraction"]), delta=f"{B.es(ta['contraction'] / tcs['contraction'], 1)}×",
             foot=f"vs. {B.mm(ta['contraction'])} en el modelo actual"),
    ])

    fig = go.Figure()
    labels = [MOVE_LABELS[m] for m in MOVES]
    for name, tot in ((scen, tcs), (ACT, ta)):
        fig.add_bar(y=labels, x=[tot.get(m, 0) / 1e6 for m in MOVES], orientation="h", name=name,
                    marker_color=MODEL_COLORS.get(name, T.viz[0]),
                    hovertemplate="%{y}<br>" + name + ": %{x:.1f} MM<extra></extra>")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=T.line, ticksuffix=" MM")
    tbl = pd.DataFrame({"Movimiento": labels, scen: [round(tcs.get(m, 0) / 1e6, 1) for m in MOVES],
                        ACT: [round(ta.get(m, 0) / 1e6, 1) for m in MOVES]})
    B.chart_frame("bridge_cmp", "",
                  f"El MRR final cuadra, pero el modelo actual exagera el churn {B.es(ta['churn'] / tcs['churn'], 1)}× "
                  f"y la reactivación {B.es(ta['reactivation'] / tcs['reactivation'], 0)}×",
                  "Movimientos de MRR acumulados por tipo · millones de COP · abr-2022 a oct-2024", fig, tbl, SRC_TX, 400)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        nm = C.nonmrr_cash()
        kinds = {"arrears": "Mora y puestas al día", "lump": "Pagos agrupados", "spike": "Picos puntuales",
                 "prepaid_pending": "Prepago en confirmación",
                 "prepaid": "Prepagos multi-mes", "retro": "Retroactivo de precio"}
        f2 = go.Figure(go.Bar(y=[kinds.get(k, k) for k in nm.index], x=nm.values / 1e6, orientation="h",
                              marker_color=T.viz[0], hovertemplate="%{y}: %{x:.1f} MM<extra></extra>"))
        f2.update_xaxes(showgrid=True, gridcolor=T.line, ticksuffix=" MM")
        f2.update_yaxes(showgrid=False)
        B.chart_frame("nonmrr", "",
                      f"{B.mm(nm.sum(), 0)} de caja no son MRR y el modelo actual los lee como movimientos",
                      "Caja cobrada que no corresponde al MRR del mes, por tipo · millones de COP",
                      f2, pd.DataFrame({"Tipo": [kinds.get(k, k) for k in nm.index], "MM COP": (nm.values / 1e6).round(1)}),
                      SRC_TX, 320)
    with c2:
        f3 = go.Figure()
        for name in (scen, ACT):
            s = mrr_series(name) / 1e6
            f3.add_scatter(x=s.index, y=s.values, name=name, mode="lines", line=dict(color=MODEL_COLORS.get(name, T.viz[0])),
                           hovertemplate="%{x}<br>" + name + ": %{y:.1f} MM<extra></extra>")
        f3.update_layout(hovermode="x unified")
        mrr_tbl = pd.DataFrame({"Mes": mrr_series(ACT).index, ACT: (mrr_series(ACT) / 1e6).round(1).values,
                                scen: (mrr_series(scen) / 1e6).round(1).values})
        B.chart_frame("mrr_lines", "", "Las dos curvas llegan al mismo punto: el total no delata el error",
                      "MRR mensual por modelo · millones de COP · ene-2022 a oct-2024", f3, mrr_tbl, SRC_TX, 320,
                      ysuffix=" MM")

    b = load("bridge_monthly")
    b = b[(b["scenario"] == scen) & (b["month"] >= WINDOW_START)]
    f4 = go.Figure()
    for m in MOVES:
        s = b[b["movement"] == m]
        f4.add_bar(x=s["month"], y=s["amount_cop"] / 1e6, name=MOVE_LABELS[m], marker_color=MOVE_COLORS[m],
                   hovertemplate="%{x}<br>" + MOVE_LABELS[m] + ": %{y:.2f} MM<extra></extra>")
    f4.update_layout(barmode="relative")
    piv = b.pivot_table(index="month", columns="movement", values="amount_cop").reindex(columns=MOVES) / 1e6
    piv.columns = [MOVE_LABELS[c] for c in piv.columns]
    B.chart_frame("bridge_monthly", "",
                  "El crecimiento viene de clientes nuevos y expansión; las subidas de precio pesan poco",
                  f"Movimientos de MRR por mes ({scen}) · millones de COP", f4, piv.round(2).reset_index(names="Mes"),
                  SRC_TX, 400, ysuffix=" MM")

    st.subheader("¿Cuánto es comportamiento del cliente y cuánto pricing o descuentos?")
    hc = C.half_cut()
    at_risk = C.delinquent_open_last()
    cust = sum(tcs.get(m, 0) for m in C.CUSTOMER_MOVES)
    B.kpi_row([
        dict(overline="Comportamiento del cliente", value=B.mm(cust, sign=True), pastel=True,
             foot="nuevos + expansión + reactivación − contracción − churn"),
        dict(overline="Pricing · subidas de precio", value=B.mm(tcs.get("price_uplift", 0), sign=True),
             foot=f"{B.es(tcs.get('price_uplift', 0) / tcs.sum() * 100, 0)} % del cambio neto"),
        dict(overline="Descuentos", value="Sin dato", delta=f"cota ilustrativa {B.mm(hc['foregone_cop'].sum())}",
             foot=f"techo si las {int(hc['events'].sum())} bajadas al 50 % fueran descuentos; no es una estimación"),
        dict(overline="MRR en mora sin confirmar", value=B.mm(at_risk), foot="al cierre de oct-2024"),
    ])
    B.callout(f"Hay <b>{int(hc['events'].sum())} bajadas exactas a la mitad</b>. Pueden ser un descuento (decisión "
              f"comercial) o un downgrade (comportamiento del cliente), y con <i>cliente + mes + monto</i> no hay forma "
              f"de saberlo. Su <b>cota superior ilustrativa</b> es {B.mm(hc['foregone_cop'].sum())} acumulados: lo que "
              "Finora habría dejado de capturar si todas fueran descuentos que se mantuvieron. No es una estimación; esa "
              "incertidumbre es el argumento para pasar al modelo de dos capas.")

    rc = load("retention_cohorts")
    cc1, cc2 = st.columns(2)
    model_r = cc1.radio("Modelo", [COR, ACT], horizontal=True)
    metric = cc2.radio("Métrica", ["nrr", "grr", "logo_retention"], horizontal=True,
                       format_func={"nrr": "NRR", "grr": "GRR", "logo_retention": "Retención de clientes"}.get)
    h = rc[(rc["model"] == model_r) & (rc["cohort"] >= "2022Q2") & (rc["age"] <= 18)]
    hp = h.pivot(index="cohort", columns="age", values=metric) * 100
    lo, hi = 40, 120
    mid = (100 - lo) / (hi - lo)
    pos = [0, mid / 3, 2 * mid / 3, mid, mid + (1 - mid) / 3, mid + 2 * (1 - mid) / 3, 1]
    scale = [[p_, c] for p_, c in zip(pos, T.div)]
    f5 = go.Figure(go.Heatmap(z=hp.values, x=hp.columns, y=hp.index, zmin=lo, zmax=hi, colorscale=scale, xgap=2, ygap=2,
                              hovertemplate="Cohorte %{y} · mes %{x}<br>%{z:.0f} %<extra></extra>",
                              colorbar=dict(ticksuffix=" %", outlinewidth=0,
                                            tickfont=dict(family=B.FONT_MONO, size=11, color=T.muted))))
    f5.update_yaxes(autorange="reversed", showgrid=False)
    f5.update_xaxes(title_text="Meses desde el alta")
    B.chart_frame("heatmap", "",
                  f"Las altas de 2023 retienen {B.pct(nrr12(COR, '2023'))} de su MRR a 12 meses, no {B.pct(nrr12(ACT, '2023'))}",
                  f"{ {'nrr': 'NRR', 'grr': 'GRR', 'logo_retention': 'Retención de clientes'}[metric] } por cohorte trimestral "
                  f"de alta y meses de antigüedad · {model_r} · neutro = 100 %, durazno = pierde, azul = crece", f5, hp.round(1).rename(columns=lambda c: f"Mes {c}").reset_index(), SRC_TX, 420)

    sens, stable = C.rule_sensitivity()
    B.text_frame("sens", "", ("Ninguna regla cambia el signo ni el orden de magnitud" if stable else
                               "Alguna regla cambia el signo o el orden de magnitud: revisar"),
                  "Cada regla del modelo corregido apagada o llevada a su extremo, una a la vez · movimientos acumulados "
                  "abr-2022 a oct-2024 en millones de COP · detalle y archivo en Fundamentos · calidad de datos",
                  sens.drop(columns=["Ajuste"]), "Fuente: app/data/rule_sensitivity.csv", right=C.SENS_NUM)

    st.subheader("Simulador · las 3 preguntas del CFO")
    cases = {
        "Pagaba 100, ahora 80 por un descuento": (100, 100, 0, 20, False),
        "Pagaba 100, ahora 80 por un downgrade": (100, 80, 0, 0, False),
        "Creció de 100 a 130 con descuento de 30 y sigue pagando 100": (100, 130, 0, 30, False),
        "Se acaba el descuento y paga 130": (130, 130, 30, 0, False),
        "Churn con descuento vigente": (100, 0, 20, 0, False),
        "Subida de precio de catálogo de 5 %": (100, 105, 0, 0, True),
    }
    with st.container(border=True, key="frame_sim"):
        pick = st.selectbox("Caso", list(cases))
        l0, l1, d0, d1, rep = cases[pick]
        cc = st.columns(5)
        l0 = cc[0].number_input("Lista mes anterior", value=float(l0), step=5.0)
        l1 = cc[1].number_input("Lista mes actual", value=float(l1), step=5.0)
        d0 = cc[2].number_input("Descuento mes anterior", value=float(d0), step=5.0)
        d1 = cc[3].number_input("Descuento mes actual", value=float(d1), step=5.0)
        rep = cc[4].checkbox("Repricing de catálogo", value=rep)
        p0, p1 = l0 - d0, l1 - d1
        read = ("sin cambio, y la expansión queda escondida" if p1 == p0 and l1 != l0 else
                "churn" if p1 == 0 and p0 > 0 else "expansión" if p1 > p0 else "contracción" if p1 < p0 else "sin cambio")
        mv = two_layer_movements([l0, l1], [d0, d1], repricing=[False, rep])
        s1, s2 = st.columns(2, gap="medium")
        s1.markdown(f'<div class="da-overline">Modelo actual · solo ve lo pagado</div>'
                    f'<div class="da-h3">{B.es(p0, 0)} a {B.es(p1, 0)}: {read} ({B.es(p1 - p0, 0)})</div>',
                    unsafe_allow_html=True)
        s2.markdown('<div class="da-overline">Modelo de dos capas</div>', unsafe_allow_html=True)
        if mv.empty:
            s2.markdown("Sin movimientos")
        else:
            s2.dataframe(pd.DataFrame({"Capa": mv["layer"].map({"customer": "Cliente", "pricing": "Pricing y descuentos"}),
                                       "Movimiento": mv["movement"], "Monto": mv["amount"].map(lambda v: B.es(v, 0))}),
                         hide_index=True, width="stretch")
        st.markdown('<div class="da-source">Regla: el cliente creció el mes en que hizo el upgrade, no el mes en que se '
                    'venció el descuento · mismo resultado en Python y en SQL</div>', unsafe_allow_html=True)

elif section == S_CRO:
    st.title("Más leads, pero no más ventas: ¿dónde se pierde el crecimiento?")
    tab_real, tab_design, tab_proto = st.tabs(["Datos reales (clientes ganados)", "Diseño del funnel",
                                               "Prototipo con datos sintéticos"])
    with tab_real:
        B.kpi_row([
            dict(overline="Clientes nuevos por mes · 2024", value=B.es(ny.loc["2024", "per_month"], 0), pastel=True,
                 delta=f"+{B.es((ny.loc['2024', 'per_month'] / ny.loc['2022', 'per_month'] - 1) * 100, 0)} %", delta_kind="up",
                 foot=f"vs. {B.es(ny.loc['2022', 'per_month'], 0)} en 2022"),
            dict(overline="MRR nuevo por mes · 2024", value=B.mm(ny.loc["2024", "mrr_per_month"]),
                 delta=f"+{B.es((ny.loc['2024', 'mrr_per_month'] / ny.loc['2022', 'mrr_per_month'] - 1) * 100, 0)} %",
                 delta_kind="up", foot=f"vs. {B.mm(ny.loc['2022', 'mrr_per_month'])} en 2022"),
            dict(overline="MRR al 3.er mes por cliente", value=f"{B.es(ny.loc['2024', 'm3_ticket'] / 1e3, 0)} mil",
                 delta=f"−{B.es((1 - ny.loc['2024', 'm3_ticket'] / ny.loc['2022', 'm3_ticket']) * 100, 0)} %", delta_kind="down",
                 foot=f"vs. {B.es(ny.loc['2022', 'm3_ticket'] / 1e3, 0)} mil COP en 2022"),
        ])
        nc = load("new_customers_monthly")
        m = nc[nc["month"] >= WINDOW_START].groupby("month").agg(n=("new_customers", "sum"), mrr=("new_mrr_cop", "sum"))
        m = m.rolling(3).mean().dropna()
        idx = m / m.loc[(m.index >= "2022-06") & (m.index <= "2022-12")].mean() * 100
        f = go.Figure()
        for col, name, color in (("n", "Clientes nuevos", T.viz[0]), ("mrr", "MRR nuevo", T.viz[1])):
            f.add_scatter(x=idx.index, y=idx[col], name=name, mode="lines", line=dict(color=color),
                          hovertemplate="%{x}<br>" + name + ": %{y:.0f}<extra></extra>")
        f.add_hline(y=100, line_color=T.line_strong, line_width=1)
        f.update_layout(hovermode="x unified", showlegend=True)
        B.end_labels(f)
        B.chart_frame("idx", "Datos reales", "Ganamos el doble de clientes, pero el MRR nuevo crece la mitad",
                      "Clientes nuevos y MRR nuevo, índice 2S-2022 = 100, media móvil de 3 meses", f,
                      idx.round(0).reset_index(names="Mes").rename(columns={"n": "Clientes nuevos", "mrr": "MRR nuevo"}),
                      SRC_TX, 360, right=120)
        kt = C.ticket_kitagawa()
        mix, rate, r0, r1 = kt["mix"], kt["rate"], kt["ticket0"], kt["ticket1"]
        order = rate.sort_values(ascending=False).index
        f2 = go.Figure()
        f2.add_bar(y=order, x=rate[order].values, orientation="h", name="Dentro de la industria (cambia su ticket)",
                   marker_color=T.viz[0], hovertemplate="%{y}<br>Dentro de la industria: %{x:,.0f} COP<extra></extra>")
        f2.add_bar(y=order, x=mix[order].values, orientation="h", name="Mezcla (cambia el peso de la industria)",
                   marker_color=T.viz[1], hovertemplate="%{y}<br>Mezcla: %{x:,.0f} COP<extra></extra>")
        f2.update_yaxes(showgrid=False)
        f2.update_xaxes(showgrid=True, gridcolor=T.line, ticksuffix=" COP")
        share_in = rate.sum() / (mix.sum() + rate.sum())
        B.chart_frame("kit_ind", "Datos reales",
                      f"El {B.es(share_in * 100, 0)} % de la caída del ticket ocurre dentro de cada industria; Retail cae más",
                      f"Descomposición mezcla/tasa (Kitagawa) del ticket de entrada 2022 a 2024 · COP · total "
                      f"{B.es(mix.sum() + rate.sum(), 0)}",
                      f2, pd.DataFrame({"Industria": mix.index, "Ticket 2022": r0.round(0).values, "Ticket 2024": r1.round(0).values,
                                        "Efecto mezcla": mix.round(0).values, "Efecto dentro": rate.round(0).values}),
                      SRC_TX, 360)
        B.callout("Lo que <b>no</b> se puede concluir con estos datos: si la caída se debe al canal (más self-serve), al "
                  "plan o tamaño del cliente, o a descuentos de entrada. Hace falta el funnel por eventos.")
    with tab_design:
        st.subheader("1 · Tres caminos, no una escalera")
        st.markdown("- **Self-serve:** signup, uso y pago sin ventas. No es una fuga del funnel SDR: es otro camino.\n"
                    "- **Directo a SQL:** referidos, contadores-partners y solicitudes de demo.\n"
                    "- **Recorrido SDR completo:** New, Working, Engaged, SQL, Demo, Proposal y Won.\n\n"
                    "Se mide el **alcance de etapa** (si llegó alguna vez a X) y el **camino**, no la posición actual. "
                    "Los saltos no reciben tiempo en etapas que no vivieron, los retrocesos cuentan como señal de calidad "
                    "del traspaso y los ciclos reciclados abren una instancia nueva.")
        st.subheader("2 · Conversión por cohorte, no por foto")
        st.markdown("Ganados del mes ÷ nuevos del mes mezcla poblaciones distintas y **cae mecánicamente cuando sube el "
                    "volumen**. Se mide el porcentaje de leads **creados en el mes M** que llegan a la etapa X en un máximo "
                    "de W días; las cohortes que aún no cumplen W quedan marcadas como inmaduras.")
        B.text_frame("metrics", "", "Ocho métricas que hoy no existen",
                      "Definición y para qué sirve cada una", pd.DataFrame([
                          ("Conversión por cohorte y camino", "Leads de la cohorte que llegan a X en W días", "Dónde se pierde, sin sesgo de volumen"),
                          ("Mezcla vs. tasa (Kitagawa)", "Δ conversión = Σ Δpeso·tasa + Σ Δtasa·peso", "Canal o ejecución"),
                          ("Speed-to-lead P50/P90 y SLA de 1 hora", "Primer contacto − creación", "Capacidad SDR y ruteo"),
                          ("Conversión por velocidad dentro del canal", "Working a Engaged por tramo de demora", "Si la demora cuesta ventas"),
                          ("Tiempo en etapa y estancados", "Distribución con censura; > P90 = estancado", "Limpieza de pipeline"),
                          ("Win rate post-SQL por cohorte", "SQL a Won en 60 días", "Si el problema es del AE"),
                          ("Calidad del lead (ICP fit)", "Score firmográfico validado contra el win rate", "Criterio MQL/SQL"),
                          ("MRR a 3 meses por lead", "Valor, no solo conteo", "Optimizar por ingresos"),
                      ], columns=["Métrica", "Definición", "Para qué"]))
        B.text_frame("hyp", "", "Cada hipótesis tiene una prueba y una decisión asociada",
                      "Qué la confirmaría, qué datos hacen falta y qué decisión habilita", pd.DataFrame([
                          ("Demanda o mezcla de canal", "Domina el efecto mezcla; crecen canales de baja conversión",
                           "Canal y fuente por lead, gasto por canal", "Reasignar gasto; metas por conversión"),
                          ("Calidad del lead", "Cae la tasa dentro del mismo canal; sube la descalificación por no fit",
                           "Industria, tamaño, motivos de descalificación", "Endurecer criterios MQL/PQL"),
                          ("Velocidad o capacidad", "Speed-to-lead empeora con el volumen; la conversión cae con la demora dentro del canal",
                           "Creación, primer contacto, owner, carga por SDR", "SLA, ruteo, headcount, primer contacto con IA"),
                          ("Conversión post-SQL", "Cae SQL a Won o se alarga el ciclo",
                           "Eventos Demo y Proposal, montos, motivos de pérdida, AE", "Coaching, criterios de SQL, propuesta"),
                          ("Canibalización self-serve", "Leads que compraban solos ahora entran al funnel asistido",
                           "Camino y eventos de producto", "Reglas de traspaso entre PLG y ventas"),
                      ], columns=["Hipótesis", "Qué la confirmaría", "Datos necesarios", "Decisión"]))
        st.subheader("3 · Modelo de eventos (fuente única de verdad)")
        st.code("dim_lead(lead_id, created_at, channel, source, path, industry, company_size, icp_fit_score)\n"
                "fct_lead_stage_event(lead_id, funnel_instance_id, from_stage, to_stage, ts, owner_id, is_skip)\n"
                "fct_lead_activity(lead_id, ts, type, owner_id)      -- speed-to-lead\n"
                "fct_product_event(account_id, ts, event)           -- señales PQL\n"
                "bridge_lead_customer(lead_id, customer_id)         -- conecta el funnel con el MRR",
                language="sql")
    with tab_proto:
        B.callout("<b>Datos sintéticos.</b> Ilustran el diseño y prueban que el tablero detecta dos problemas plantados "
                  "a propósito: más volumen de un canal de bajo ajuste desde marzo de 2024 y SDR saturados. "
                  "<b>No son hallazgos de Finora.</b>", kind="warn")
        leads, ev = synthetic()
        as_of = pd.Timestamp("2024-10-31")
        r = F.reach_table(leads, ev)
        v = r.groupby(["cohort", "channel"]).size().unstack(fill_value=0).reindex(columns=list(CHANNELS))
        f = go.Figure()
        for ch in v.columns:
            f.add_bar(x=v.index.astype(str), y=v[ch], name=ch, marker_color=CHANNEL_COLORS[ch],
                      hovertemplate="%{x}<br>" + ch + ": %{y}<extra></extra>")
        f.update_layout(barmode="stack")
        tot_m = v.sum(axis=1)
        pre = (v.index < pd.Period("2024-03", "M")) & (v.index >= pd.Period("2023-07", "M"))
        post_ = v.index >= pd.Period("2024-03", "M")
        vol_up = tot_m[post_].mean() / tot_m[pre].mean() - 1
        ps_share = (v.loc[post_, "Paid Social"].mean() - v.loc[pre, "Paid Social"].mean()) / (
            tot_m[post_].mean() - tot_m[pre].mean())
        B.chart_frame("syn_vol", "Datos sintéticos",
                      f"New crece {B.es(vol_up * 100, 0)} % desde marzo; Paid Social explica el {B.es(ps_share * 100, 0)} %",
                      "Leads nuevos por mes y canal", f, v.reset_index(names="Mes").astype({"Mes": str}), SRC_SYN, 360)
        sdr = r[r["path"] == "sdr_full"]
        kt = F.kitagawa(sdr, "New", "SQL", 45, pd.period_range("2023-07", "2023-12", freq="M"),
                        pd.period_range("2024-04", "2024-08", freq="M"))
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            f2 = go.Figure()
            f2.add_bar(x=kt.index, y=kt["mix_effect"] * 100, name="Efecto mezcla", marker_color=T.viz[0])
            f2.add_bar(x=kt.index, y=kt["rate_effect"] * 100, name="Efecto tasa", marker_color=T.viz[1])
            B.chart_frame("syn_kit", "Datos sintéticos",
                          f"New a SQL cae {B.es(-(kt.mix_effect.sum() + kt.rate_effect.sum()) * 100, 1)} pp: "
                          f"{B.es(-kt.mix_effect.sum() * 100, 1)} por mezcla y {B.es(-kt.rate_effect.sum() * 100, 1)} por tasa",
                          "Descomposición por canal, camino SDR · puntos porcentuales · 2S-2023 vs. abr–ago 2024", f2,
                          (kt * 100).round(2).reset_index(names="Canal"), SRC_SYN, 340, ysuffix=" pp")
        with c2:
            s2l = F.speed_to_lead(r)
            p50_0 = s2l.loc[s2l["cohort"] < pd.Period("2024-03", "M"), "p50"].mean()
            p50_1 = s2l["p50"].tail(3).mean()
            f3 = go.Figure()
            for col, name, color in (("p50", "P50", T.viz[0]), ("p90", "P90", T.viz[1])):
                f3.add_scatter(x=s2l["cohort"].astype(str), y=s2l[col], name=name, mode="lines", line=dict(color=color),
                               hovertemplate="%{x}<br>" + name + ": %{y:.1f} h<extra></extra>")
            f3.update_layout(hovermode="x unified")
            B.end_labels(f3)
            B.chart_frame("syn_s2l", "Datos sintéticos",
                          f"El primer contacto pasó de {B.es(p50_0, 1)} a {B.es(p50_1, 1)} horas cuando subió el volumen",
                          "Speed-to-lead mensual · horas", f3, s2l.astype({"cohort": str}).round(2), SRC_SYN, 340,
                          ysuffix=" h", right=60)
        c3, c4 = st.columns(2, gap="medium")
        with c3:
            cs = F.conversion_by_speed(r)
            cs = cs[cs["size"] >= 50]
            f4 = go.Figure()
            for ch in ["Paid Social", "Paid Search", "Outbound"]:
                s = cs[cs["channel"] == ch]
                f4.add_scatter(x=s["speed_bucket"].astype(str), y=s["mean"] * 100, name=ch, mode="lines+markers",
                               line=dict(color=CHANNEL_COLORS[ch]), marker=dict(size=8, line=dict(color=T.surface, width=2)),
                               hovertemplate=ch + " · %{x}: %{y:.1f} %<extra></extra>")
            B.chart_frame("syn_speed", "Datos sintéticos", "Dentro de cada canal, más demora es menos conversión",
                          "Working a Engaged en 30 días según tiempo al primer contacto · %", f4,
                          cs.assign(mean=lambda d: (d["mean"] * 100).round(1)).rename(
                              columns={"channel": "Canal", "speed_bucket": "Demora", "size": "Leads", "mean": "Conversión %"}),
                          SRC_SYN, 340, ysuffix=" %")
        with c4:
            pc = F.p_chart(r, "Working", "Engaged", 30, as_of)
            pc = pc[pc["n"] >= 0.5 * pc["n"].median()]
            f5 = go.Figure()
            f5.add_scatter(x=pc["week"], y=pc["ucl"] * 100, name="Límite superior", mode="lines",
                           line=dict(color=T.line_strong, width=1), showlegend=False, hoverinfo="skip")
            f5.add_scatter(x=pc["week"], y=pc["lcl"] * 100, name="Banda de control", mode="lines", fill="tonexty",
                           fillcolor=T.band, line=dict(color=T.line_strong, width=1), hoverinfo="skip")
            f5.add_scatter(x=pc["week"], y=pc["p"] * 100, name="Tasa semanal", mode="lines", line=dict(color=T.viz[0]),
                           hovertemplate="%{x|%d %b %Y}: %{y:.1f} %<extra></extra>")
            al = pc[pc["alert"]]
            f5.add_scatter(x=al["week"], y=al["p"] * 100, name="Alerta: fuera de banda o racha de 8 semanas",
                           mode="markers", marker=dict(color=T.negative, size=9, symbol="triangle-down",
                                                       line=dict(color=T.surface, width=2)),
                           hovertemplate="Alerta · %{x|%d %b %Y}: %{y:.1f} %<extra></extra>")
            B.chart_frame("syn_p", "Datos sintéticos",
                          f"El control estadístico avisa del cambio de nivel ({int(pc['alert'].sum())} semanas en alerta)",
                          "Working a Engaged semanal, banda p̄ ± 3σ y regla de rachas · %", f5,
                          pc[["week", "n", "p", "center", "lcl", "ucl", "alert"]].assign(
                              week=lambda d: d["week"].dt.date).round(3), SRC_SYN, 340, ysuffix=" %")
        post = F.cohort_conversion(r, "SQL", "Won", 60, as_of)
        post = post[post["mature"]]
        f6 = go.Figure(go.Scatter(x=post["cohort"].astype(str), y=post["conv"] * 100, name="SQL a Won en 60 días",
                                  mode="lines", line=dict(color=T.viz[0]),
                                  hovertemplate="%{x}: %{y:.1f} %<extra></extra>"))
        f6.update_yaxes(range=[0, max(40, post["conv"].max() * 160)])
        B.chart_frame("syn_post", "Datos sintéticos", "Post-SQL estable: la hipótesis del AE queda descartada",
                      "Conversión SQL a Won en 60 días por cohorte madura · %", f6,
                      post.assign(conv=lambda d: (d["conv"] * 100).round(1)).astype({"cohort": str}), SRC_SYN, 280, ysuffix=" %")
        st.subheader("Lectura para el CRO (lo que el tablero diría con datos reales)")
        st.markdown(f"- **Qué cambió:** New creció {B.es(vol_up * 100, 0)} % desde marzo, sobre todo por Paid Social.\n"
                    "- **Dónde se concentra:** New a SQL cae en parte por **mezcla** (más Paid Social, que convierte menos) "
                    "y en parte por **tasa** (todos los canales convierten menos).\n"
                    f"- **Por qué:** el primer contacto pasó de {B.es(p50_0, 1)} a {B.es(p50_1, 1)} horas y la conversión "
                    "cae con la demora **dentro "
                    "del mismo canal**: es **capacidad SDR**. Post-SQL está estable: no es problema del AE.\n"
                    "- **Qué hacer:** ruteo y primer contacto automático, con IA, para leads de bajo ajuste; SLA de 1 hora "
                    "para los de alto ajuste; medir Paid Social por SQL y MRR a 3 meses, no por leads; revisión semanal "
                    "con las alertas del control estadístico.")
        stl = F.stalled(r, ev, as_of)
        st.caption(f"Lista operativa: {B.es(len(stl), 0)} leads abiertos superan el P90 histórico de su etapa y camino, y se "
                   "reparten por owner en la operación diaria.")

elif section == S_DM:
    st.title("Modelo de datos propuesto: valor de la suscripción ≠ precio pagado")
    st.markdown("**net MRR = list MRR − discount MRR.** La lista es comportamiento del cliente; el descuento es una "
                "decisión comercial; **la caja vive aparte** (mora, prepagos y cargos únicos no son MRR).")
    with st.container(border=True, key="frame_erd"):
        st.markdown('<div class="da-h3">El MRR se deriva del contrato '
                    'y se concilia contra la factura</div>', unsafe_allow_html=True)
        st.graphviz_chart(f"""
        digraph G {{ rankdir=TB; bgcolor="transparent"; pad=0.3; nodesep=0.5; ranksep=0.45;
          node [shape=record, fontname="IBM Plex Mono", fontsize=13, color="{T.line_strong}", fontcolor="{T.ink}", style=rounded];
          edge [color="{T.muted}", fontname="IBM Plex Sans", fontsize=12, fontcolor="{T.muted}"];
          plan [label="{{dim_plan|plan_id\\lbilling_interval_m\\llist_price_cop\\lvalid_from · valid_to\\l}}"];
          sub [label="{{fct_subscription_version (SCD2)|subscription_id · customer_id\\lplan_id · quantity\\llist_mrr_cop\\lchange_reason\\lvalid_from · valid_to\\l}}"];
          disc [label="{{dim_discount|discount_id\\ltype · value\\lduration_type · months\\lreason · approved_by\\l}}"];
          asg [label="{{fct_discount_assignment|subscription_id · discount_id\\lstart_month\\lscheduled_end · actual_end\\lend_reason · owner_sales_rep\\l}}"];
          inv [label="{{fct_invoice (caja)|period_start · period_end\\lrecurring · discount · one_time\\lamount_paid · status\\l}}"];
          mrr [label="{{fct_mrr_customer_month|customer_id · month\\llist_mrr_cop\\ldiscount_mrr_cop\\lnet_mrr_cop (oficial)\\lbilling_status\\l}}", color="{T.viz[0]}", penwidth=2];
          plan -> sub [label="precio de lista"]; sub -> asg [label="recibe"]; disc -> asg;
          sub -> mrr [label="list_mrr"]; asg -> mrr [label="discount_mrr"]; inv -> mrr [label="concilia, no define", style=dashed];
        }}""")
        st.markdown(f'<div class="da-source">DDL: <a href="{C.REPO}/sql/02_modelo_dos_capas_ddl.sql">'
                    f'sql/02_modelo_dos_capas_ddl.sql</a> · clasificación: <a href="{C.REPO}/sql/03_movimientos_dos_capas.sql">'
                    'sql/03_movimientos_dos_capas.sql</a></div>', unsafe_allow_html=True)
    B.text_frame("rules", "", "Inicio y fin de un descuento nunca se leen como contracción o expansión",
                  "Cómo se clasifica cada evento y en qué capa", pd.DataFrame([
                      ("Cliente nuevo", "Cliente", "new", "+ lista"),
                      ("Upgrade, más uso o módulos", "Cliente", "expansion", "+ a precio de lista"),
                      ("Downgrade, menos uso", "Cliente", "contraction", "− a precio de lista"),
                      ("Cancela", "Cliente", "churn", "− lista (vista ejecutiva: churn neto)"),
                      ("Vuelve tras churn confirmado", "Cliente", "reactivation", "+"),
                      ("Subida de precio de catálogo", "Pricing", "repricing", "+ (decisión Finora)"),
                      ("Inicia un descuento", "Pricing", "discount_start", "− · no es contracción"),
                      ("Termina un descuento", "Pricing", "discount_end", "+ · no es expansión"),
                      ("Mora, puesta al día, prepago, retroactivo", "Caja", "(no es MRR)", "0"),
                  ], columns=["Evento", "Capa", "Movimiento", "Efecto en el neto"]))
    B.text_frame("dict", "", "Siete métricas nuevas para responder al CFO cada mes",
                  "Definición y decisión que habilita cada una", pd.DataFrame([
                      ("List MRR", "Valor de la suscripción a precio de catálogo", "Crecimiento real del negocio subyacente"),
                      ("Discount leakage", "List MRR − Net MRR", "Cuánto no capturamos por decisiones comerciales"),
                      ("Price realization", "Net ÷ List por segmento, canal, comercial y motivo", "Política de descuentos y aprobaciones"),
                      ("Discount-end pipeline", "MRR que vuelve por descuentos que vencen en 1 a 6 meses", "Proyección; preparar a CS"),
                      ("Churn al vencer el descuento", "Bajas en el mes del vencimiento vs. línea base", "Si el descuento retiene o solo posterga"),
                      ("NRR y GRR a lista y netos", "Las dos versiones lado a lado", "Si la brecha crece, se compra crecimiento con descuentos"),
                      ("MRR en mora", "Net MRR de clientes past_due", "Churn involuntario y política de cobro"),
                  ], columns=["Métrica", "Definición", "Decisión que habilita"]))

elif section == S_SM:
    st.title("S&M y eficiencia comercial")
    B.callout("Lectura con cautela: el S&M incluye nómina y equipo, no hay atribución por canal ni separación entre "
              "self-serve y ventas, y las unidades vienen del enunciado. <b>Validar con Finanzas antes de concluir.</b>",
              kind="warn")
    sm = load("sm_monthly")
    sm["Otros"] = sm[["Travel", "Freelance", "SoftwareTools"]].sum(axis=1)
    items = ["PaidMedia", "PublicidadNoWeb", "Team", "PayrollExpenses", "Otros"]
    f = go.Figure()
    for i, it in enumerate(items):
        f.add_bar(x=sm["month"], y=sm[it] / 1e6, name=it, marker_color=T.viz[i],
                  hovertemplate="%{x}<br>" + it + ": %{y:.1f} MM<extra></extra>")
    f.update_layout(barmode="relative")
    B.chart_frame("sm", "", "El S&M se recortó a la mitad en el segundo semestre de 2023",
                  "Gasto de Sales & Marketing por rubro · millones de COP · Otros = viajes, freelance y software",
                  f, (sm[["month"] + items].set_index("month") / 1e6).round(1).reset_index(), "Fuente: S&M_spend.csv · corte oct-2024",
                  380, ysuffix=" MM")
    F_ = C.FIGURES
    eff = load("sm_efficiency_quarterly")
    eff = eff[eff["complete"] & (eff["quarter"] >= "2022Q2")]
    pb = load("cohort_payback_quarterly")
    pb = pb[pb["mature"] & (pb["cohort"] >= "2022Q2")]
    B.kpi_row([
        dict(overline="Magic number trimestral", value=f"0,{int(F_['magic_min']):02d} a 0,{int(F_['magic_max']):02d}", pastel=True,
             foot=f"{F_['magic_min']} a {F_['magic_max']} centavos de ARR nuevo por peso de S&M del trimestre anterior · referencia: 0,75"),
        dict(overline="Payback realizado a 24 meses", value=f"{F_['pb24_min']} a {F_['pb24_max']} %",
             foot=f"del S&M del trimestre devuelto por sus cohortes ({F_['pb24_n']} cohortes con 24 meses) · mercado: 100 % en 8 a 16 meses"),
        dict(overline="CAC variable", value=f"{F_['cac_var_min']} a {F_['cac_var_max']}",
             foot=f"solo rubros de adquisición ({F_['sm_var_pct']} % del S&M) · MM por cliente nuevo y trimestre"),
        dict(overline="Si las unidades fueran 10× menores", value=f"{F_['magic_x10_min']} a {F_['magic_x10_max']}",
             foot="el magic number quedaría en rango normal: la pregunta de unidades decide la lectura"),
    ])
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        f2 = go.Figure()
        f2.add_bar(x=[B.quarter_label(q) for q in eff["quarter"]], y=eff["magic_number"], name="Magic number",
                   marker_color=T.viz[0], hovertemplate="%{x}: %{y:.2f}<extra></extra>")
        f2.add_hline(y=0.75, line_color=T.ink, line_width=1, annotation_text="0,75 · escalar", annotation_position="top left")
        f2.add_hline(y=0.5, line_color=T.line_strong, line_width=1, line_dash="dot", annotation_text="0,5 · revisar",
                     annotation_position="bottom left")
        B.chart_frame("magic", "", "Cada peso de S&M devuelve centavos de ARR nuevo; el mercado exige 0,75",
                      "Magic number = ΔARR del trimestre ÷ S&M del trimestre anterior · trimestres completos", f2,
                      eff[["quarter", "sm_cop", "delta_arr_cop", "magic_number", "magic_number_new_only"]].assign(
                          sm_cop=lambda d: (d["sm_cop"] / 1e6).round(0), delta_arr_cop=lambda d: (d["delta_arr_cop"] / 1e6).round(0)).round(2),
                      "Fuente: S&M_spend.csv y Transactions.csv (agregado)", 320, month_ticks=False)
    with c2:
        f3 = go.Figure()
        cohorts = sorted(pb["cohort"].unique())
        full = set(pb.loc[pb["age"] == 24, "cohort"])
        for k, coh in enumerate(cohorts):
            s = pb[pb["cohort"] == coh]
            f3.add_scatter(x=s["age"], y=s["recovered"] * 100, name=coh, mode="lines", showlegend=coh in full,
                           line=dict(color=T.seq[min(k + 1, len(T.seq) - 1)]), hovertemplate=coh + " · mes %{x}: %{y:.0f} %<extra></extra>")
        B.end_labels(f3)
        f3.update_layout(showlegend=False)
        f3.update_xaxes(title_text="Meses desde el alta")
        B.chart_frame("payback_real", "", f"Ninguna cohorte ha devuelto su S&M; a 24 meses, entre {F_['pb24_min']} y {F_['pb24_max']} %",
                      "MRR acumulado de la cohorte ÷ S&M del trimestre en que entró, en % (100 = recuperado) · una línea por cohorte · solo edades maduras", f3,
                      pb.pivot(index="cohort", columns="age", values="recovered").mul(100).round(0)
                      .rename(columns=lambda c: f"Mes {c}").reset_index(),
                      "Fuente: S&M_spend.csv y Transactions.csv (agregado)", 320, ysuffix=" %", month_ticks=False)
    cac = load("cac_quarterly")
    cac = cac[cac["quarter"] >= "2022Q2"].merge(eff[["quarter", "cac_variable_cop"]], on="quarter")
    f4 = go.Figure()
    f4.add_bar(x=[B.quarter_label(q) for q in cac["quarter"]], y=cac["cac_cop"] / 1e6, name="CAC combinado (todo el S&M)",
               marker_color=T.viz[1], hovertemplate="%{x}: %{y:.1f} MM<extra></extra>")
    f4.add_bar(x=[B.quarter_label(q) for q in cac["quarter"]], y=cac["cac_variable_cop"] / 1e6, name="CAC variable (solo adquisición)",
               marker_color=T.viz[0], hovertemplate="%{x}: %{y:.1f} MM<extra></extra>")
    B.chart_frame("cac", "", "Tras el recorte de 2S-2023, el costo por cliente nuevo bajó y las altas subieron",
                  "CAC por trimestre · millones de COP por cliente nuevo · variable = PaidMedia, PublicidadNoWeb, Freelance y Travel", f4,
                  cac[["quarter", "new_customers"]].assign(combinado_MM=(cac["cac_cop"] / 1e6).round(2),
                                                           variable_MM=(cac["cac_variable_cop"] / 1e6).round(2)),
                  "Fuente: S&M_spend.csv y Transactions.csv (agregado)", 320, ysuffix=" MM", month_ticks=False)
    st.markdown(f"- **El recorte de 2S-2023 es el experimento natural que estos datos permiten:** el S&M cayó a la mitad, "
                f"los clientes nuevos subieron y las cohortes posteriores devuelven a 9 meses el {F_['pb9_post']} % de su S&M, "
                f"contra {F_['pb9_pre']} % las anteriores ({F_['pb9_x']} veces más por peso). No hay evidencia agregada de que "
                f"más gasto traiga más clientes (correlación en diferencias {F_['corr_dif']}).\n"
                f"- **Lectura condicional:** con las unidades del enunciado, el magic number ({F_['magic_min']} a {F_['magic_max']} "
                "centavos) y el payback realizado dicen que Finora gasta varias veces más de lo que un SaaS justifica. Si las "
                f"unidades estuvieran infladas 10 veces, el magic number quedaría entre {F_['magic_x10_min']} y "
                f"{F_['magic_x10_max']}, en rango normal. **Las dos respuestas cambian decisiones; por eso confirmar las "
                "unidades con Finanzas es una decisión pendiente, no una nota al pie.**\n"
                "- Lo que no haría: un modelo de rezagos (adstock) por rubro. Con 31 puntos mensuales y 7 rubros colineales, "
                "ningún rubro de adquisición correlaciona con las altas en niveles ni en diferencias; modelarlo más no lo cambia.")

else:
    st.title("Calidad de datos, supuestos y lo que no se puede concluir")
    dq = load("data_quality")
    B.text_frame("dq", "", f"{len(dq)} hallazgos de calidad y cómo se trató cada uno",
                  "Magnitud medida en los datos y regla aplicada", dq.rename(
                      columns={"hallazgo": "Hallazgo", "magnitud": "Magnitud", "tratamiento": "Tratamiento"}), SRC_TX)
    c1, c2 = st.columns(2, gap="medium")
    c1.subheader("Supuestos")
    c1.markdown("- **Supuesto cero: un 0 en `Transactions` es «no se cobró», no «no se facturó».** Si significara «sin "
                "servicio», el modelo de caja tendría razón y la mora no existiría.\n"
                "- `Transactions` es caja cobrada en el mes, no MRR. Montos × 10.000 = COP.\n"
                "- Mora tolerada de **N = 2 meses**; sensibilidad con N = 1 y 3 en la tabla de abajo.\n"
                "- Un hueco pagado completo después significa que el cliente siguió activo.\n"
                "- Subida de precio: patrón de retroactivo (confianza alta) o alza persistente de 2 % a 10 % (media).\n"
                "- Prepago: pago de 200 mil COP o más seguido de 6 o más meses en 0, repartido en min(12, meses cubiertos).\n"
                "- Lo que pasa en el último mes queda en confirmación: churn en mora, subidas de precio y pagos grandes "
                "que pueden ser prepagos.\n"
                "- Enero a marzo de 2022 es periodo de arranque (clientes que ya existían).")
    c2.subheader("Lo que no se puede concluir")
    c2.markdown("- Si una baja de monto es un descuento o un downgrade.\n"
                "- Cualquier hipótesis del funnel real: no hay etapas, canal ni tiempos.\n"
                "- Causalidad entre S&M y altas, eficiencia por canal y margen bruto.")
    sens, stable = C.rule_sensitivity()
    B.text_frame("sens_dq", "", ("Sensibilidad por regla: ninguna cambia el signo ni el orden de magnitud" if stable else
                                  "Sensibilidad por regla: alguna cambia el signo o el orden de magnitud"),
                  "Cada regla apagada o llevada a su extremo, una a la vez · movimientos acumulados abr-2022 a oct-2024 en "
                  "millones de COP y NRR a 12 meses de las altas de 2023", sens,
                  "Fuente: app/data/rule_sensitivity.csv (generado por pipeline.py) · reglas en finora/mrr.py",
                  right=C.SENS_NUM)
    st.markdown(f"Archivo completo: [rule_sensitivity.csv]({C.REPO}/app/data/rule_sensitivity.csv) · reglas: "
                f"[finora/mrr.py]({C.REPO}/finora/mrr.py)")
    st.subheader("Información que hizo falta")
    st.markdown("- **CFO:** precio de lista y plan por cliente-mes; tabla de descuentos con inicio, fin, motivo y "
                "aprobador; intervalo de facturación; estado de la suscripción y fecha de cancelación; facturas con "
                "cargos únicos y mora; margen bruto.\n"
                "- **CRO:** eventos de etapa con timestamp; canal y fuente; owner; primer contacto; motivos de "
                "descalificación y pérdida; eventos de producto; enlace lead-cliente; gasto por canal; capacidad SDR y AE.")
