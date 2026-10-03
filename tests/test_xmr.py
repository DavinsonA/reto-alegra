"""Pruebas del gráfico de comportamiento del proceso (XmR)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finora.xmr import xmr


def test_limites_con_constante_2_66():
    s = pd.Series([10, 12, 11, 13, 12, 11])
    r = xmr(s)
    mr_bar = np.mean([2, 1, 2, 1, 1])
    assert r["center"].iloc[0] == pytest.approx(s.mean())
    assert r["ucl"].iloc[0] == pytest.approx(s.mean() + 2.66 * mr_bar)


def test_variacion_rutinaria_no_genera_senal():
    rng = np.random.default_rng(0)
    s = pd.Series(100 + rng.normal(0, 1, 30))
    assert not xmr(s, baseline=20)["rule1"].any()


def test_punto_fuera_de_limites_es_senal():
    s = pd.Series([10, 11, 10, 11, 10, 11, 10, 11, 10, 30])
    r = xmr(s, baseline=9)
    assert r["rule1"].iloc[-1] and r["direction"].iloc[-1] == "arriba"


def test_cambio_de_nivel_por_racha_de_8():
    s = pd.Series([10, 11, 9, 10, 11, 9, 10, 11, 9, 10] + [10.6] * 8)
    r = xmr(s, baseline=10)
    assert r["rule2"].iloc[-1] and not r["rule1"].iloc[-1]
