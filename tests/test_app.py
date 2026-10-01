"""Smoke test de las tres apps: cada sección se ejecuta sin errores (Streamlit AppTest, sin navegador)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1] / "app"
N_SECTIONS = {"historia": 6, "demo": 6, "tablero": 2}
CASES = [(app, i) for app, n in N_SECTIONS.items() for i in range(n)]


def _open(app: str, section: int | None = None) -> AppTest:
    at = AppTest.from_file(str(APP_DIR / f"{app}.py"), default_timeout=180)
    at.run()
    if section is not None:
        radio = at.sidebar.radio[0]
        radio.set_value(radio.options[section]).run()
    return at


def test_numero_de_secciones():
    for app, n in N_SECTIONS.items():
        assert len(_open(app).sidebar.radio[0].options) == n, app


@pytest.mark.parametrize("app,section", CASES)
def test_seccion_sin_errores(app, section):
    at = _open(app, section)
    assert not at.exception, [e.message for e in at.exception]


def test_historia_avanza_con_botones():
    at = _open("historia")
    options = list(at.sidebar.radio[0].options)
    for expected in options[1:]:
        at.button(key="next").click().run()
        assert not at.exception, [e.message for e in at.exception]
        assert at.sidebar.radio[0].value == expected
    at.button(key="prev").click().run()
    assert at.sidebar.radio[0].value == options[-2]


def test_simulador_cfo_todos_los_casos():
    options = [s for s in _open("demo", 1).selectbox if s.label == "Caso"][0].options
    for opt in options:
        # cada caso cambia los valores por defecto de los inputs: se vuelve a cargar la app limpia
        at = _open("demo", 1)
        [s for s in at.selectbox if s.label == "Caso"][0].set_value(opt).run()
        assert not at.exception, (opt, [e.message for e in at.exception])


def test_revision_mensual_todos_los_meses_recientes():
    sb = [s for s in _open("tablero", 0).selectbox if s.label == "Mes de cierre"][0]
    for opt in list(sb.options)[:6]:
        at = _open("tablero", 0)
        [s for s in at.selectbox if s.label == "Mes de cierre"][0].set_value(opt).run()
        assert not at.exception, (opt, [e.message for e in at.exception])
