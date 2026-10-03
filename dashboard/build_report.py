"""Genera las páginas PBIR del tablero (equivalent_dashboard.Report) a partir del modelo: mensual (CFO) y semanal (CRO)."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "equivalent_dashboard.Report"
DEF = REPORT / "definition"
PAGES = DEF / "pages"
VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

VIZ = ["#009786", "#8670c0", "#ba673f", "#2b88c0", "#b4608a", "#a28218"]
INK, MUTED, LINE, LINE_STRONG, SURFACE, BG = "#11151A", "#50585B", "#E3E7EC", "#8A9299", "#FFFFFF", "#FAFBFC"
MINT, NEG = "#9ce0d9", "#8F3A14"
FONT = "Segoe UI"


def vid(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:20]


def lit(v) -> dict:
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


def color(hex_: str) -> dict:
    return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hex_}'"}}}}}


def col(entity: str, prop: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def mea(entity: str, prop: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def proj(field: dict, entity: str, prop: str, **extra) -> dict:
    return {"field": field, "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop, **extra}


def P(entity: str, prop: str, measure: bool = True, **extra) -> dict:
    return proj(mea(entity, prop) if measure else col(entity, prop), entity, prop, **extra)


def cat_filter(entity: str, prop: str, values: list[str], name: str) -> dict:
    return {"name": vid(name), "field": col(entity, prop), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}}],
                                                       "Values": [[{"Literal": {"Value": f"'{v}'"}}] for v in values]}}}]}}


def date_filter(entity: str, prop: str, since: str, name: str) -> dict:
    return {"name": vid(name), "field": col(entity, prop), "type": "Advanced",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": {"Comparison": {"ComparisonKind": 2,
                                                               "Left": {"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}},
                                                               "Right": {"Literal": {"Value": f"datetime'{since}T00:00:00'"}}}}}]}}


def bool_filter(entity: str, prop: str, name: str) -> dict:
    return {"name": vid(name), "field": col(entity, prop), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": prop}}],
                                                       "Values": [[{"Literal": {"Value": "true"}}]]}}}]}}


def container(title: str | None = None, subtitle: str | None = None, border: bool = True, bg: str = SURFACE) -> dict:
    out = {
        "background": [{"properties": {"show": lit(True), "color": color(bg), "transparency": lit(0)}}],
        "border": [{"properties": {"show": lit(border), "color": color(LINE), "radius": lit(12)}}],
        "dropShadow": [{"properties": {"show": lit(False)}}],
        "title": [{"properties": {"show": lit(title is not None), "text": lit(title or ""), "fontSize": lit(13),
                                  "fontFamily": lit(FONT), "bold": lit(True), "fontColor": color(INK)}}],
        "subTitle": [{"properties": {"show": lit(subtitle is not None), "text": lit(subtitle or ""), "fontSize": lit(10),
                                     "fontFamily": lit(FONT), "fontColor": color(MUTED)}}],
        "padding": [{"properties": {"top": lit(12), "bottom": lit(12), "left": lit(16), "right": lit(16)}}],
    }
    return out


class Page:
    def __init__(self, name: str, display: str, width: int = 1920, height: int = 1080):
        self.name, self.display, self.width, self.height = name, display, width, height
        self.visuals: list[dict] = []
        self.interactions: list[dict] = []
        self.z = 0

    def add(self, key: str, vtype: str, x: int, y: int, w: int, h: int, query: dict | None = None,
            objects: dict | None = None, vco: dict | None = None, filters: list[dict] | None = None,
            sort: dict | None = None) -> dict:
        self.z += 100
        visual: dict = {"visualType": vtype, "drillFilterOtherVisuals": True}
        if query is not None:
            visual["query"] = {"queryState": query}
            if sort:
                visual["query"]["sortDefinition"] = sort
        if objects:
            visual["objects"] = objects
        visual["visualContainerObjects"] = vco or container(border=False, bg=BG)
        v = {"$schema": VC_SCHEMA, "name": vid(f"{self.name}:{key}"),
             "position": {"x": x, "y": y, "z": self.z, "width": w, "height": h, "tabOrder": self.z},
             "visual": visual}
        if filters:
            v["filterConfig"] = {"filters": filters}
        self.visuals.append(v)
        return v

    def text(self, key, x, y, w, h, runs: list[tuple[str, int, bool, str]]):
        paragraphs = [{"textRuns": [{"value": t, "textStyle": {"fontSize": f"{s}pt", "fontWeight": "bold" if b else "normal",
                                                               "fontFamily": FONT, "color": c}}]} for t, s, b, c in runs]
        return self.add(key, "textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
                        vco=container(border=False, bg=BG))

    def card(self, key, x, y, w, h, entity, measure, size=28, title=None, subtitle=None, bg=SURFACE, border=True,
             align="left", filters=None, wrap=False, color_=INK, font=FONT):
        objects = {
            "labels": [{"properties": {"fontSize": lit(size), "fontFamily": lit(font), "color": color(color_),
                                       "wordWrap": lit(wrap), "alignment": lit(align), "labelDisplayUnits": lit(1),
                                       "labelPrecision": lit(1)}}],
            "categoryLabels": [{"properties": {"show": lit(False)}}],
        }
        return self.add(key, "card", x, y, w, h, query={"Values": {"projections": [P(entity, measure)]}},
                        objects=objects, vco=container(title, subtitle, border, bg), filters=filters)

    def write(self):
        folder = PAGES / self.name
        if folder.exists():
            shutil.rmtree(folder)
        (folder / "visuals").mkdir(parents=True)
        page = {"$schema": PAGE_SCHEMA, "name": self.name, "displayName": self.display, "displayOption": "FitToWidth",
                "height": self.height, "width": self.width,
                "objects": {"background": [{"properties": {"color": color(BG), "transparency": lit(0)}}]}}
        if self.interactions:
            page["visualInteractions"] = self.interactions
        (folder / "page.json").write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")
        for v in self.visuals:
            d = folder / "visuals" / v["name"]
            d.mkdir()
            (d / "visual.json").write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")


def xmr_lines(page: Page, key, x, y, w, h, entity, cat_entity, cat_prop, measures: list[str], title, subtitle,
              filters):
    objects = {
        "legend": [{"properties": {"show": lit(False)}}],
        "categoryAxis": [{"properties": {"showAxisTitle": lit(False), "fontSize": lit(9), "fontFamily": lit(font_mono())}}],
        "valueAxis": [{"properties": {"showAxisTitle": lit(False), "fontSize": lit(9), "gridlineColor": color(LINE)}}],
        "dataPoint": [
            {"properties": {"fill": color(VIZ[0])}, "selector": {"metadata": f"{entity}.{measures[0]}"}},
            {"properties": {"fill": color(LINE_STRONG)}, "selector": {"metadata": f"{entity}.{measures[1]}"}},
            {"properties": {"fill": color(LINE_STRONG)}, "selector": {"metadata": f"{entity}.{measures[2]}"}},
            {"properties": {"fill": color(LINE_STRONG)}, "selector": {"metadata": f"{entity}.{measures[3]}"}},
            {"properties": {"fill": color(NEG)}, "selector": {"metadata": f"{entity}.{measures[4]}"}},
        ],
        "lineStyles": [
            {"properties": {"strokeWidth": lit(2)}, "selector": {"metadata": f"{entity}.{measures[0]}"}},
            {"properties": {"strokeWidth": lit(1), "lineStyle": lit("dashed")}, "selector": {"metadata": f"{entity}.{measures[1]}"}},
            {"properties": {"strokeWidth": lit(1), "lineStyle": lit("dotted")}, "selector": {"metadata": f"{entity}.{measures[2]}"}},
            {"properties": {"strokeWidth": lit(1), "lineStyle": lit("dotted")}, "selector": {"metadata": f"{entity}.{measures[3]}"}},
            {"properties": {"strokeWidth": lit(0), "showMarker": lit(True), "markerShape": lit("diamond"), "markerSize": lit(6)},
             "selector": {"metadata": f"{entity}.{measures[4]}"}},
        ],
    }
    query = {"Category": {"projections": [P(cat_entity, cat_prop, measure=False, active=True)]},
             "Y": {"projections": [P(entity, m, displayName=d) for m, d in zip(measures, ["valor", "centro", "LCL", "UCL", "señal"])]}}
    return page.add(key, "lineChart", x, y, w, h, query=query, objects=objects,
                    vco=container(title, subtitle, border=True), filters=filters)


def font_mono():
    return "Consolas"


# ------------------------------------------------------------------------------------------------ mensual
def mensual(name: str) -> Page:
    pg = Page(name, "Mensual del MRR · CFO", 1920, 1900)
    pg.text("titulo", 24, 12, 1300, 60, [("Revisión mensual del MRR", 18, True, INK)])
    pg.text("proposito", 24, 56, 1500, 44,
            [("Para: CFO y RevOps · Decide: si el cambio del mes es señal o ruido, y quién investiga · Cadencia: mensual, en el cierre",
              10, False, MUTED)])
    pg.add("mes", "slicer", 1520, 20, 376, 64,
           query={"Values": {"projections": [P("Calendario", "Mes", measure=False)]}},
           objects={"general": [{"properties": {"orientation": lit(1), "filter": {"filter": {
                        "Version": 2, "From": [{"Name": "c", "Entity": "Calendario", "Type": 0}],
                        "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "Mes"}}],
                                                        "Values": [[{"Literal": {"Value": "'oct. 2024'"}}]]}}}]}}}}],
                    "data": [{"properties": {"mode": lit("Dropdown")}}],
                    "selection": [{"properties": {"singleSelect": lit(True), "selectAllCheckboxEnabled": lit(False)}}],
                    "header": [{"properties": {"show": lit(True), "text": lit("Mes de cierre"), "fontSize": lit(10), "fontColor": color(MUTED)}}]},
           vco=container(border=False, bg=BG))
    pg.card("estado", 24, 100, 1872, 52, "Puente", "Línea de estado", size=13, bg=BG, border=False, wrap=True)

    kx = [24, 492, 960, 1428]
    kw = 444
    kpis = [("KPI cierre título", "MRR cierre", "KPI cierre pie", MINT),
            (None, "MRR neto nuevo", "KPI neto pie", SURFACE),
            ("KPI churn título", "KPI churn valor", "KPI churn pie", SURFACE),
            (None, "Clientes nuevos", "KPI nuevos pie", SURFACE)]
    static_titles = {1: "MRR NETO NUEVO DEL MES", 3: "CLIENTES NUEVOS"}
    for i, (tmeasure, vmeasure, foot, bg) in enumerate(kpis):
        x = kx[i]
        pg.add(f"kpibg{i}", "shape", x, 160, kw, 150,
               objects={"shape": [{"properties": {"tileShape": lit("rectangle")}}],
                        "fill": [{"properties": {"show": lit(True), "fillColor": color(bg), "transparency": lit(0)}}],
                        "outline": [{"properties": {"show": lit(True), "lineColor": color(LINE), "weight": lit(1)}}],
                        "rotation": [{"properties": {"shapeAngle": lit(0)}}]},
               vco=container(border=False, bg=bg))
        if tmeasure:
            pg.card(f"kpit{i}", x + 16, 168, kw - 32, 32, "Puente", tmeasure, size=10, bg=bg, border=False, color_=MUTED, font=font_mono())
        else:
            pg.text(f"kpit{i}", x + 16, 168, kw - 32, 32, [(static_titles[i], 10, False, MUTED)])
        pg.card(f"kpiv{i}", x + 16, 198, kw - 32, 60, "Puente", vmeasure, size=30, bg=bg, border=False)
        pg.card(f"kpif{i}", x + 16, 258, kw - 32, 48, "Puente", foot, size=10, bg=bg, border=False, wrap=True, color_=MUTED)

    pg.card("puente_titulo", 24, 326, 1100, 36, "Puente", "Puente título", size=13, bg=BG, border=False)
    pg.add("puente", "waterfallChart", 24, 362, 1100, 440,
           query={"Category": {"projections": [P("Puente", "Movimiento", measure=False, active=True)]},
                  "Y": {"projections": [P("Puente", "Movimiento MM")]}},
           objects={"legend": [{"properties": {"show": lit(False)}}],
                    "categoryAxis": [{"properties": {"fontSize": lit(10), "fontFamily": lit(font_mono()), "showAxisTitle": lit(False)}}],
                    "valueAxis": [{"properties": {"fontSize": lit(10), "showAxisTitle": lit(False), "gridlineColor": color(LINE)}}],
                    "labels": [{"properties": {"show": lit(True), "fontSize": lit(10), "fontFamily": lit(font_mono()), "color": color(INK)}}],
                    "sentimentColors": [{"properties": {"increaseFill": color(VIZ[0]), "decreaseFill": color(VIZ[2]), "totalFill": color(LINE_STRONG)}}],
                    "general": [{"properties": {"maxBreakdowns": lit(6)}}]},
           vco=container("Puente del mes en dos capas", "Millones de COP · verde azulado = suma, durazno = resta, gris = neto · churn de los dos últimos meses en confirmación (no se dibuja)"),
           filters=[cat_filter("Puente", "scenario", ["Corregido (N=2)"], "puente_scen")],
           sort={"sort": [{"field": col("Puente", "Movimiento"), "direction": "Ascending"}], "isDefaultSort": False})
    pg.card("lectura", 1148, 326, 748, 476, "Puente", "Lectura del mes", size=12, bg="#F1F3F6", border=False, wrap=True,
            title="Qué cambió · en confirmación · señales y acción")

    slicer_name = vid(f"{name}:mes")

    def no_filter(v):
        pg.interactions.append({"source": slicer_name, "target": v["name"], "type": "NoFilter"})

    pg.text("h_xmr", 24, 822, 1500, 44, [("Señal o ruido por movimiento · banda = rango normal (media ± 2,66 × rango móvil, fijada con los primeros 18 meses) · rombo = señal", 11, True, INK)])
    for i, (metric, label) in enumerate([("new", "Nuevos"), ("expansion", "Expansión"), ("contraction", "Contracción"), ("churn", "Churn")]):
        no_filter(xmr_lines(pg, f"xmr_{metric}", kx[i], 870, kw, 300, "Puente", "Calendario", "Mes",
                            ["Valor XmR", "Centro XmR", "LCL XmR", "UCL XmR", "Señal XmR (punto)"], label, "MM COP por mes",
                            [cat_filter("XmR", "metric", [metric], f"f_{metric}")]))

    pg.text("h_sm", 24, 1190, 1500, 44, [("Eficiencia del S&M · unidades del enunciado, pendientes de confirmar con Finanzas · fuente: S&M_spend.csv", 11, True, INK)])
    no_filter(xmr_lines(pg, "xmr_cac", 24, 1238, 912, 320, "Puente", "Calendario", "Mes",
                        ["Valor XmR", "Centro XmR", "LCL XmR", "UCL XmR", "Señal XmR (punto)"], "CAC variable, 3 meses móviles",
                        "MM por cliente nuevo · solo rubros de adquisición", [cat_filter("XmR", "metric", ["cac3_variable"], "f_cac")]))
    no_filter(pg.add("magic", "clusteredColumnChart", 960, 1238, 936, 320,
           query={"Category": {"projections": [P("EficienciaSM", "quarter", measure=False, active=True)]},
                  "Y": {"projections": [P("Puente", "Magic number")]}},
           objects={"legend": [{"properties": {"show": lit(False)}}],
                    "dataPoint": [{"properties": {"fill": color(VIZ[0])}}],
                    "categoryAxis": [{"properties": {"fontSize": lit(9), "fontFamily": lit(font_mono()), "showAxisTitle": lit(False)}}],
                    "valueAxis": [{"properties": {"fontSize": lit(9), "showAxisTitle": lit(False), "gridlineColor": color(LINE)}}],
                    "y1AxisReferenceLine": [{"properties": {"show": lit(True), "value": lit(0.75), "lineColor": color(INK), "displayName": lit("0,75 · escalar"), "dataLabelShow": lit(True)}, "selector": {"id": "ref1"}},
                                            {"properties": {"show": lit(True), "value": lit(0.5), "lineColor": color(LINE_STRONG), "style": lit("dotted"), "displayName": lit("0,5 · revisar"), "dataLabelShow": lit(True)}, "selector": {"id": "ref2"}}]},
           vco=container("Magic number por trimestre cerrado", "ΔARR del trimestre ÷ S&M del trimestre anterior · líneas: 0,75 escalar, 0,5 revisar"),
           filters=[bool_filter("EficienciaSM", "complete", "f_complete")]))

    pg.add("reglas", "tableEx", 24, 1582, 1872, 300,
           query={"Values": {"projections": [P("Reglas", "Métrica", measure=False), P("Reglas", "Dueño", measure=False),
                                              P("Reglas", "Regla de alerta", measure=False), P("Reglas", "Acción", measure=False)]}},
           objects={"grid": [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True), "gridHorizontalColor": color(LINE), "rowPadding": lit(6)}}],
                    "columnHeaders": [{"properties": {"fontSize": lit(9), "fontFamily": lit(font_mono()), "fontColor": color(MUTED), "backColor": color(SURFACE)}}],
                    "values": [{"properties": {"fontSize": lit(10), "fontFamily": lit(FONT), "fontColor": color(INK), "backColor": color(SURFACE), "backColorSecondary": color(SURFACE)}}],
                    "total": [{"properties": {"totals": lit(False)}}]},
           vco=container("Dueños, reglas de alerta y acciones", "Se revisa en el cierre mensual; si no hay señal, se dice «nada que investigar» y se sigue"),
           sort={"sort": [{"field": col("Reglas", "Orden"), "direction": "Ascending"}], "isDefaultSort": False})
    return pg


# ------------------------------------------------------------------------------------------------ semanal
GRID = [("speed_p50", "Speed-to-lead P50", "2024-09-09"), ("sla_1h", "Contactados en < 1 hora", "2024-09-09"),
        ("work_to_eng", "Working a Engaged", "2024-08-26"), ("sql_to_won", "SQL a Won", "2024-07-22")]
KPIS = [("leads", "LEADS NUEVOS"), ("high_fit", "MEZCLA DE ALTO AJUSTE"), ("new_customers", "CLIENTES NUEVOS"), ("new_mrr", "MRR NUEVO (MM)")]


def semanal(name: str) -> Page:
    pg = Page(name, "Semanal del funnel · CRO", 1920, 1700)
    pg.text("titulo", 24, 12, 1300, 60, [("Revisión semanal del funnel", 18, True, INK)])
    pg.text("proposito", 24, 56, 1700, 44,
            [("Para: CRO, líderes SDR y AE · Decide: qué entrada se salió de lo normal y quién actúa · Cadencia: semanal, 30 minutos · formato fijo 6-12",
              10, False, MUTED)])
    v = pg.text("aviso_t", 24, 96, 1872, 44, [("Datos sintéticos: prototipo del formato con dos problemas plantados, no hallazgos de Finora", 11, True, "#6B5300")])
    v["visual"]["visualContainerObjects"] = container(border=False, bg="#FBF3D5")
    pg.card("estado", 24, 136, 1872, 48, "FunnelXmR", "Línea de estado semanal", size=13, bg=BG, border=False, wrap=True)

    kx = [24, 492, 960, 1428]
    kw = 444
    for i, (metric, title) in enumerate(KPIS):
        x = kx[i]
        bg = MINT if metric == "new_mrr" else SURFACE
        pg.add(f"kpibg{i}", "shape", x, 192, kw, 140,
               objects={"shape": [{"properties": {"tileShape": lit("rectangle")}}],
                        "fill": [{"properties": {"show": lit(True), "fillColor": color(bg), "transparency": lit(0)}}],
                        "outline": [{"properties": {"show": lit(True), "lineColor": color(LINE), "weight": lit(1)}}]},
               vco=container(border=False, bg=bg))
        pg.text(f"kpit{i}", x + 16, 198, kw - 32, 32, [(title, 10, False, MUTED)])
        f = [cat_filter("FunnelXmR", "metric", [metric], f"k_{metric}")]
        pg.card(f"kpiv{i}", x + 16, 226, kw - 32, 56, "FunnelXmR", "F KPI valor", size=30, bg=bg, border=False, filters=f)
        pg.card(f"kpif{i}", x + 16, 282, kw - 32, 44, "FunnelXmR", "F KPI pie", size=10, bg=bg, border=False, wrap=True, color_=MUTED, filters=f)

    pg.add("entradas", "tableEx", 24, 348, 1100, 330,
           query={"Values": {"projections": [P("FunnelXmR", "Métrica", measure=False), P("FunnelXmR", "F valor última semana", displayName="Última semana"),
                                              P("FunnelXmR", "F centro última semana", displayName="Lo normal"),
                                              P("FunnelXmR", "F estado última semana", displayName="Estado")]}},
           objects={"grid": [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True), "gridHorizontalColor": color(LINE), "rowPadding": lit(8)}}],
                    "columnHeaders": [{"properties": {"fontSize": lit(9), "fontFamily": lit(font_mono()), "fontColor": color(MUTED), "backColor": color(SURFACE)}}],
                    "values": [{"properties": {"fontSize": lit(11), "fontFamily": lit(FONT), "fontColor": color(INK), "backColor": color(SURFACE), "backColorSecondary": color(SURFACE)}}],
                    "total": [{"properties": {"totals": lit(False)}}]},
           vco=container("De las entradas que el equipo controla al MRR nuevo", "Última semana con dato · en señal, lo que salió de su rango normal (XmR)"),
           filters=[cat_filter("FunnelXmR", "freq", ["W"], "e_freq"),
                    cat_filter("FunnelXmR", "metric", ["speed_p50", "sla_1h", "high_fit", "work_to_eng", "sql_to_won", "leads", "new_customers"], "e_metric")],
           sort={"sort": [{"field": col("FunnelXmR", "Métrica"), "direction": "Ascending"}], "isDefaultSort": False})
    pg.card("lectura", 1148, 348, 748, 330, "FunnelXmR", "Lectura semanal", size=12, bg="#F1F3F6", border=False, wrap=True,
            title="Qué cambió · por qué · qué hacemos")

    pg.text("h_612", 24, 696, 1700, 44, [("Formato 6-12 · las cuatro entradas que el equipo controla · 6 semanas a la izquierda, 12 meses a la derecha · banda = rango normal · rombo = señal", 11, True, INK)])
    for i, (metric, label, since) in enumerate(GRID):
        x = kx[i]
        xmr_lines(pg, f"w6_{metric}", x, 744, 190, 300, "FunnelXmR", "FunnelXmR", "period",
                  ["F valor", "F centro", "F LCL", "F UCL", "F señal (punto)"], label, "6 semanas",
                  [cat_filter("FunnelXmR", "metric", [metric], f"w6m_{metric}"), cat_filter("FunnelXmR", "freq", ["W"], f"w6f_{metric}"),
                   date_filter("FunnelXmR", "period", since, f"w6d_{metric}")])
        xmr_lines(pg, f"m12_{metric}", x + 196, 744, kw - 196, 300, "FunnelXmR", "FunnelXmR", "period",
                  ["F valor", "F centro", "F LCL", "F UCL", "F señal (punto)"], " ", "12 meses",
                  [cat_filter("FunnelXmR", "metric", [metric], f"m12m_{metric}"), cat_filter("FunnelXmR", "freq", ["M"], f"m12f_{metric}"),
                   date_filter("FunnelXmR", "period", "2023-10-01", f"m12d_{metric}")])

    pg.add("estancados", "tableEx", 24, 1068, 912, 360,
           query={"Values": {"projections": [P("FunnelEstancados", "owner", measure=False, displayName="Dueño"), P("FunnelEstancados", "New", measure=False),
                                              P("FunnelEstancados", "Working", measure=False), P("FunnelEstancados", "Engaged", measure=False),
                                              P("FunnelEstancados", "SQL", measure=False), P("FunnelEstancados", "Demo", measure=False),
                                              P("FunnelEstancados", "Proposal", measure=False), P("FunnelEstancados", "total", measure=False, displayName="Total")]}},
           objects={"grid": [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True), "gridHorizontalColor": color(LINE), "rowPadding": lit(6)}}],
                    "columnHeaders": [{"properties": {"fontSize": lit(9), "fontFamily": lit(font_mono()), "fontColor": color(MUTED), "backColor": color(SURFACE)}}],
                    "values": [{"properties": {"fontSize": lit(10), "fontFamily": lit(FONT), "fontColor": color(INK), "backColor": color(SURFACE), "backColorSecondary": color(SURFACE)}}],
                    "total": [{"properties": {"totals": lit(False)}}]},
           vco=container("Leads abiertos que superan el P90 histórico de su etapa y camino", "Por dueño y etapa · la lista que cada SDR y AE limpia esta semana"),
           sort={"sort": [{"field": col("FunnelEstancados", "total"), "direction": "Descending"}], "isDefaultSort": False})
    pg.add("mezcla", "tableEx", 960, 1068, 936, 360,
           query={"Values": {"projections": [P("FunnelMezcla", "channel", measure=False, displayName="Canal"),
                                              P("FunnelMezcla", "share_base", measure=False, displayName="Peso antes"), P("FunnelMezcla", "share_recent", measure=False, displayName="Peso ahora"),
                                              P("FunnelMezcla", "conv_base", measure=False, displayName="Conv. antes"), P("FunnelMezcla", "conv_recent", measure=False, displayName="Conv. ahora"),
                                              P("FunnelMezcla", "mix_effect", measure=False, displayName="Efecto mezcla"), P("FunnelMezcla", "rate_effect", measure=False, displayName="Efecto tasa")]}},
           objects={"grid": [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True), "gridHorizontalColor": color(LINE), "rowPadding": lit(6)}}],
                    "columnHeaders": [{"properties": {"fontSize": lit(9), "fontFamily": lit(font_mono()), "fontColor": color(MUTED), "backColor": color(SURFACE)}}],
                    "values": [{"properties": {"fontSize": lit(10), "fontFamily": lit(FONT), "fontColor": color(INK), "backColor": color(SURFACE), "backColorSecondary": color(SURFACE)}}],
                    "total": [{"properties": {"totals": lit(False)}}]},
           vco=container("Mezcla frente a tasa por canal · New a Engaged (SDR)", "6 semanas maduras frente a las 12 previas · descomposición de Kitagawa"))
    pg.text("fuente", 24, 1444, 1800, 30, [("Fuente: datos SINTÉTICOS generados con semilla fija · ilustran el diseño · Señal = XmR (Wheeler) con línea base de 26 semanas", 9, False, MUTED)])
    return pg


def theme() -> dict:
    return {"name": "Finora", "dataColors": VIZ, "background": BG, "foreground": INK, "tableAccent": VIZ[0],
            "textClasses": {"callout": {"fontSize": 28, "fontFace": FONT, "color": INK},
                            "title": {"fontSize": 13, "fontFace": FONT, "color": INK},
                            "header": {"fontSize": 12, "fontFace": FONT, "color": INK},
                            "label": {"fontSize": 10, "fontFace": FONT, "color": MUTED}},
            "visualStyles": {"*": {"*": {"background": [{"show": True, "color": {"solid": {"color": SURFACE}}, "transparency": 0}],
                                         "border": [{"show": True, "color": {"solid": {"color": LINE}}, "radius": 12}],
                                         "dropShadow": [{"show": False}],
                                         "title": [{"fontFamily": FONT, "fontSize": 13, "bold": True, "fontColor": {"solid": {"color": INK}}}]}}}}


def main():
    mensual_id = "959de01244783a2a96d5"
    semanal_id = vid("page:semanal")
    for folder in PAGES.iterdir():
        if folder.is_dir():
            shutil.rmtree(folder)
    mensual(mensual_id).write()
    semanal(semanal_id).write()
    (PAGES / "pages.json").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [mensual_id, semanal_id], "activePageName": mensual_id}, indent=2), encoding="utf-8")
    res = REPORT / "StaticResources" / "RegisteredResources"
    res.mkdir(parents=True, exist_ok=True)
    (res / "Finora.json").write_text(json.dumps(theme(), ensure_ascii=False, indent=2), encoding="utf-8")
    rep = json.loads((DEF / "report.json").read_text(encoding="utf-8"))
    rep["themeCollection"]["customTheme"] = {"name": "Finora", "type": "RegisteredResources",
                                              "reportVersionAtImport": rep["themeCollection"]["baseTheme"]["reportVersionAtImport"]}
    pkgs = [p for p in rep.get("resourcePackages", []) if p.get("type") != "RegisteredResources"]
    pkgs.append({"name": "RegisteredResources", "type": "RegisteredResources",
                 "items": [{"name": "Finora", "path": "Finora.json", "type": "CustomTheme"}]})
    rep["resourcePackages"] = pkgs
    (DEF / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(1 for _ in PAGES.rglob("visual.json"))
    print(f"páginas: 2 · visuales: {n}")


if __name__ == "__main__":
    main()
