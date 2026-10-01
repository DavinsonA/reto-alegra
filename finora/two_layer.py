"""Modelo propuesto para el CFO: MRR en dos capas.

    net_mrr = list_mrr − discount_mrr

- **Capa cliente** (sobre `list_mrr`, el valor de la suscripción): new, expansion, contraction, churn,
  reactivation y, aparte, `repricing` cuando cambia el precio de catálogo (decisión de Finora).
- **Capa pricing** (sobre `discount_mrr`, el descuento vigente): discount_start, discount_change, discount_end.
  El inicio de un descuento **no** es contracción y su fin **no** es expansión.
- Si el cliente hace churn con un descuento vigente, el descuento liberado se registra como
  `discount_release_on_churn`; en la vista ejecutiva se suma al churn (churn neto = −net_mrr previo).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def two_layer_movements(list_mrr, discount_mrr, repricing=None) -> pd.DataFrame:
    """Movimientos mes a mes (t ≥ 1) de un cliente en el modelo de dos capas.

    list_mrr, discount_mrr: series mensuales (discount_mrr ≥ 0, en la misma moneda).
    repricing: booleano por mes; True si el cambio de lista de ese mes es una subida o bajada de catálogo.
    """
    L = np.asarray(list_mrr, dtype=float)
    D = np.asarray(discount_mrr, dtype=float)
    R = np.zeros(len(L), dtype=bool) if repricing is None else np.asarray(repricing, dtype=bool)
    rows = []
    ever = L[0] > 0
    for t in range(1, len(L)):
        lp, lc, dp, dc = L[t - 1], L[t], D[t - 1], D[t]
        # capa cliente (valor de la suscripción a precio de lista)
        if lp == 0 and lc > 0:
            rows.append((t, "customer", "reactivation" if ever else "new", lc))
        elif lp > 0 and lc == 0:
            rows.append((t, "customer", "churn", -lp))
        elif lc != lp:
            kind = "repricing" if R[t] else ("expansion" if lc > lp else "contraction")
            rows.append((t, "pricing" if R[t] else "customer", kind, lc - lp))
        # capa pricing (descuentos)
        if dc != dp:
            if lp > 0 and lc == 0:
                rows.append((t, "pricing", "discount_release_on_churn", dp))
            elif dp == 0:
                rows.append((t, "pricing", "discount_start", -dc))
            elif dc == 0:
                rows.append((t, "pricing", "discount_end", dp))
            else:
                rows.append((t, "pricing", "discount_change", -(dc - dp)))
        ever = ever or lc > 0
    out = pd.DataFrame(rows, columns=["t", "layer", "movement", "amount"])
    # verificación: la suma de movimientos explica exactamente el cambio de net MRR
    net = L - D
    for t in range(1, len(L)):
        got = out.loc[out["t"] == t, "amount"].sum()
        assert abs(got - (net[t] - net[t - 1])) < 1e-9, f"no concilia en t={t}"
    return out


def executive_view(mov: pd.DataFrame) -> pd.DataFrame:
    """Agrupa para el CFO: el descuento liberado por churn se suma al churn (churn neto)."""
    m = mov.copy()
    m.loc[m["movement"] == "discount_release_on_churn", ["layer", "movement"]] = ["customer", "churn"]
    return m.groupby(["layer", "movement"], as_index=False)["amount"].sum()
