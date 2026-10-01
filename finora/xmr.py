"""Gráfico de comportamiento del proceso (XmR, Wheeler/Shewhart): separa la variación rutinaria de la señal.

Límites naturales = media ± 2,66 × rango móvil promedio (2,66 = 3 / d2, d2 = 1,128 para n = 2), calculados
sobre una línea base. Reglas de señal (Wheeler):
  1. un punto fuera de los límites naturales;
  2. 8 puntos seguidos del mismo lado de la línea central (cambio de nivel);
  3. 3 de 4 puntos seguidos más cerca de un mismo límite que de la línea central.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def xmr(values: pd.Series, baseline: int | None = None) -> pd.DataFrame:
    """Devuelve, por punto: centro, límites, señal y motivo. `baseline` = n.º de puntos para fijar los límites."""
    x = pd.Series(values, dtype=float).reset_index(drop=True)
    base = x.iloc[:baseline] if baseline else x
    center = base.mean()
    mr_bar = base.diff().abs().mean()
    ucl, lcl = center + 2.66 * mr_bar, center - 2.66 * mr_bar
    out = pd.DataFrame({"value": x, "center": center, "ucl": ucl, "lcl": lcl})
    out["rule1"] = (x > ucl) | (x < lcl)
    side = np.sign(x - center)
    run = side.groupby((side != side.shift()).cumsum()).cumcount() + 1
    out["rule2"] = (run >= 8) & (side != 0)
    near_up = x > center + (ucl - center) / 2
    near_dn = x < center - (center - lcl) / 2
    out["rule3"] = (near_up.rolling(4, min_periods=4).sum() >= 3) | (near_dn.rolling(4, min_periods=4).sum() >= 3)
    out["signal"] = out[["rule1", "rule2", "rule3"]].any(axis=1)
    out["direction"] = np.where(out["signal"], np.where(x >= center, "arriba", "abajo"), "")
    out["reason"] = np.select(
        [out["rule1"], out["rule2"], out["rule3"]],
        ["fuera de los límites", "8 puntos seguidos del mismo lado", "3 de 4 puntos cerca del límite"], default="")
    out.index = values.index
    return out
