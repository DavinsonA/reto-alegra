"""Smoke test de las tres apps: cada sección se ejecuta sin errores (Streamlit AppTest, sin navegador)."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1] / "app"
N_SECTIONS = {"historia": 6, "demo": 6, "tablero": 2}
CASES = [(app, i) for app, n in N_SECTIONS.items() for i in range(n)]


def _nav(at: AppTest):
    """Selector de sección: radio en la barra lateral (historia, demo) o páginas arriba (tablero, estilo BI)."""
    return at.radio(key="sec") if any(r.key == "sec" for r in at.radio) else at.segmented_control(key="sec")


def _open(app: str, section: int | None = None) -> AppTest:
    at = AppTest.from_file(str(APP_DIR / f"{app}.py"), default_timeout=180)
    at.run()
    if section is not None:
        nav = _nav(at)
        nav.set_value(nav.options[section]).run()
    return at


def test_numero_de_secciones():
    for app, n in N_SECTIONS.items():
        options = _nav(_open(app)).options
        assert len(options) == n, app
        assert all(o.strip() for o in options), f"{app}: hay una sección sin nombre"


@pytest.mark.parametrize("app,section", CASES)
def test_seccion_sin_errores(app, section):
    at = _open(app, section)
    assert not at.exception, [e.message for e in at.exception]


def test_historia_avanza_con_botones():
    at = _open("historia")
    options = list(_nav(at).options)
    for expected in options[1:]:
        at.button(key="next").click().run()
        assert not at.exception, [e.message for e in at.exception]
        assert _nav(at).value == expected
    at.button(key="prev").click().run()
    assert _nav(at).value == options[-2]


def test_simulador_cfo_todos_los_casos():
    options = [s for s in _open("demo", 1).selectbox if s.label == "Caso"][0].options
    for opt in options:
        at = _open("demo", 1)
        [s for s in at.selectbox if s.label == "Caso"][0].set_value(opt).run()
        assert not at.exception, (opt, [e.message for e in at.exception])


def test_revision_mensual_todos_los_meses_recientes():
    sb = [s for s in _open("tablero", 0).selectbox if s.label == "Mes de cierre"][0]
    for opt in list(sb.options)[:6]:
        at = _open("tablero", 0)
        [s for s in at.selectbox if s.label == "Mes de cierre"][0].set_value(opt).run()
        assert not at.exception, (opt, [e.message for e in at.exception])


def test_tablero_no_queda_sin_pagina():
    """Volver a hacer clic en la página activa no deja el tablero vacío."""
    at = _open("tablero", 1)
    activa = _nav(at).value
    _nav(at).set_value(None).run()
    assert not at.exception, [e.message for e in at.exception]
    assert _nav(at).value == activa


def _texts(at: AppTest) -> str:
    return " ".join([m.value for m in at.markdown] + [t.value for t in at.title] + [c.value for c in at.caption])


def test_las_cifras_de_la_nota_aparecen_igual_en_las_apps():
    """Las cifras clave de NOTA_CORTA y HALLAZGOS (app/data/key_figures.csv) son las que muestran las apps."""
    sys.path.insert(0, str(APP_DIR.parent))
    from finora.figures import load_figures
    f = load_figures()
    checks = {
        ("historia", 0): [f"{f['crec_mrr']} %", f"De {f['mrr_ini']} a {f['mrr_fin']} MM", f"entre {f['magic_min']} y {f['magic_max']} centavos"],
        ("historia", 1): [f"exagera el churn {f['x_churn']} veces", f"churn {f['cor_churn']} MM real contra {f['act_churn']} MM",
                          f"entre {f['sens_xchurn_min']} y {f['sens_xchurn_max']} veces",
                          f"de {f['cambio_neto']} MM de crecimiento, {f['cliente']} MM es comportamiento del cliente y "
                          f"{f['cor_price']} MM son subidas de precio"],
        ("historia", 2): [f"entran {f['caida_m3']} % más pequeños"],
        ("historia", 3): [f"conserva el {f['nrr_act_2023']} % de su ingreso", f"Conserva el {f['nrr_cor_2023']} %"],
        ("demo", 1): [f"{f['cor_churn']} MM", f"{f['cliente']} MM", f"{f['cor_price']} MM", f"{f['half_techo']} MM",
                      f"retienen {f['nrr_cor_2023']} % de su MRR a 12 meses, no {f['nrr_act_2023']} %"],
        ("tablero", 0): [f"{f['mrr_fin']} MM", f"{f['mora_abierta']} MM de MRR está en mora",
                         f"{f['precio_pend']} MM en {f['precio_pend_n']} clientes"],
    }
    for (app, section), expected in checks.items():
        text = _texts(_open(app, section))
        for s in expected:
            assert s in text, f"{app} · sección {section}: falta «{s}»"
