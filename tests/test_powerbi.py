"""El reporte Power BI (PBIR) solo referencia tablas, columnas y medidas que existen en el modelo (TMDL), y el modelo lee app/data."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard"
MODEL = DASH / "equivalent_dashboard.SemanticModel" / "definition"
REPORT = DASH / "equivalent_dashboard.Report" / "definition"


def _model_fields() -> set[tuple[str, str]]:
    fields = set()
    for f in (MODEL / "tables").glob("*.tmdl"):
        text = f.read_text(encoding="utf-8")
        table = re.search(r"^table (?:'([^']+)'|(\S+))", text, re.M)
        name = table.group(1) or table.group(2)
        for m in re.finditer(r"^\t(?:column|measure) (?:'([^']+)'|([^\s=]+))", text, re.M):
            fields.add((name, m.group(1) or m.group(2)))
        for m in re.finditer(r'DATATABLE\((.*?)\{\{', text, re.S):
            for col in re.findall(r'"([^"]+)",\s*(?:INTEGER|STRING|DOUBLE|BOOLEAN|DATETIME|CURRENCY)', m.group(1)):
                fields.add((name, col))
    return fields


def _report_refs():
    for f in REPORT.rglob("visual.json"):
        v = json.loads(f.read_text(encoding="utf-8"))
        for role in v["visual"].get("query", {}).get("queryState", {}).values():
            for p in role["projections"]:
                body = next(iter(p["field"].values()))
                yield f.name, body["Expression"]["SourceRef"]["Entity"], body["Property"]
        for flt in v.get("filterConfig", {}).get("filters", []):
            body = next(iter(flt["field"].values()))
            yield f.name, body["Expression"]["SourceRef"]["Entity"], body["Property"]


def test_cada_visual_referencia_campos_del_modelo():
    fields = _model_fields()
    missing = {(e, p) for _, e, p in _report_refs() if (e, p) not in fields}
    assert not missing, f"referencias sin campo en el modelo: {sorted(missing)}"


def test_el_modelo_lee_las_tablas_agregadas_publicadas():
    for f in (MODEL / "tables").glob("*.tmdl"):
        for csv in re.findall(r'RutaDatos & "\\\\([a-z_]+\.csv)"', f.read_text(encoding="utf-8")):
            assert (ROOT / "app" / "data" / csv).exists(), csv


def test_las_dos_paginas_existen():
    pages = json.loads((REPORT / "pages" / "pages.json").read_text(encoding="utf-8"))
    names = [json.loads((REPORT / "pages" / p / "page.json").read_text(encoding="utf-8"))["displayName"] for p in pages["pageOrder"]]
    assert names == ["Mensual del MRR · CFO", "Semanal del funnel · CRO"]
