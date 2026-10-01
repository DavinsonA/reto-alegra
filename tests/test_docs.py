"""Los documentos se generan desde una sola tabla de cifras: ninguno puede quedar desactualizado."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finora.figures import TOKEN, load_figures, render_docs  # noqa: E402


def test_documentos_coinciden_con_las_cifras():
    figs = load_figures()
    for name, text in render_docs(figs, write=False).items():
        assert (ROOT / name).read_text(encoding="utf-8") == text, f"{name} desactualizado: corre python pipeline.py"


def test_ninguna_plantilla_queda_con_marcadores():
    for name, text in render_docs(load_figures(), write=False).items():
        assert not TOKEN.search(text), name


def test_numero_de_pruebas_coincide_con_pytest():
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], capture_output=True, text=True,
                         cwd=ROOT).stdout
    collected = re.search(r"(\d+) tests? collected", out).group(1)
    assert load_figures()["n_pruebas"] == collected, "corre python pipeline.py para actualizar el número de pruebas"
