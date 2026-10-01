"""Dos modelos de MRR sobre el histórico cliente + mes + monto pagado.

- Modelo **actual** (el de Finora hoy): el MRR es la caja del mes. Un mes en 0 es churn, volver a pagar es
  reactivación y cualquier alza es expansión.
- Modelo **corregido**: infiere el MRR recurrente separando lo que es **calendario de pagos** (mora, pagos de
  puesta al día), **cargos únicos** (retroactivos de una subida de precio, picos) y **decisiones de pricing**
  (subidas de precio) del **comportamiento del cliente** (new, expansión/contracción por uso o plan, churn,
  reactivación).

Las reglas son explícitas y parametrizables (`Rules`) para poder mostrar la sensibilidad de cada decisión.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

CUSTOMER_MOVES = ["new", "expansion", "contraction", "churn", "reactivation"]
PRICING_MOVES = ["price_uplift"]
ALL_MOVES = CUSTOMER_MOVES[:3] + PRICING_MOVES + CUSTOMER_MOVES[3:]


@dataclass(frozen=True)
class Rules:
    gap_tolerance: int = 2            # meses en 0 tolerados como mora antes de declarar churn (N)
    uplift_min: float = 0.02          # rango de alza que se lee como subida de precio (confianza media)
    uplift_max: float = 0.10
    retro_max_k: int = 6              # máximo múltiplo k en el patrón de retroactivo L -> L(1+k·p) -> L(1+p)
    rel_tol: float = 0.03             # tolerancia relativa para "múltiplo exacto" de un pago
    spike_factor: float = 2.5         # un pago > factor × nivel local es un cargo puntual (no recurrente)
    usage_distinct_amounts: int = 7   # clientes con >= N montos distintos se tratan como de uso variable
    trailing_policy: str = "carry"    # mora abierta al final de la serie: 'carry' (sigue activa, marcada) o 'churn'
    detect_pricing: bool = True       # False = no separar subidas de precio (para medir el efecto de la regla)
    prepay_min_amount: float = 200_000  # prepago: pago >= este monto (misma unidad que la caja) seguido de...
    prepay_min_zeros: int = 6           # ...al menos estos meses en 0; se reparte en min(12, ceros + 1) meses
    detect_catchup: bool = True         # False = no reconocer puestas al día ni pagos agrupados (sensibilidad)


def _is_multiple(x: float, ref: float, tol: float) -> int:
    """Devuelve k si x ≈ k·ref (k entero ≥ 2) con tolerancia relativa; si no, 0."""
    if ref <= 0:
        return 0
    k = round(x / ref)
    if k >= 2 and abs(x - k * ref) <= tol * x:
        return int(k)
    return 0


def infer_customer(cash: np.ndarray, rules: Rules = Rules()) -> dict[str, np.ndarray]:
    """Infiere el MRR recurrente de un cliente a partir de su serie de caja mensual."""
    T = len(cash)
    level = np.zeros(T)
    extra = np.zeros(T)                       # caja que NO es MRR del mes (mora cobrada, retroactivo, pico)
    extra_kind = np.array([""] * T, dtype=object)
    uplift = np.array([""] * T, dtype=object)  # '', 'high' (retroactivo), 'medium' (alza persistente), 'pending' (último mes)
    covered = np.zeros(T, dtype=bool)          # el pago de este mes cubre el hueco anterior (mora pagada)
    pos = cash > 0
    usage_like = len(np.unique(np.round(cash[pos], 3))) >= rules.usage_distinct_amounts

    # --- 1. Nivel recurrente de los meses con pago -------------------------------------------------
    last_level = 0.0
    zeros_before = 0
    seen_payment = False
    prepaid = np.zeros(T, dtype=bool)          # meses en 0 cubiertos por un prepago
    t = 0
    while t < T:
        c = cash[t]
        if c <= 0:
            if seen_payment and not prepaid[t]:
                zeros_before += 1
            t += 1
            continue
        nxt = cash[t + 1] if t + 1 < T else 0.0
        lvl, kind = c, ""

        # 0) prepago multi-mes (p. ej., plan anual): pago grande seguido de muchos meses en 0
        z = 0
        while t + 1 + z < T and cash[t + 1 + z] <= 0:
            z += 1
        if (c >= rules.prepay_min_amount and z >= rules.prepay_min_zeros
                and (last_level == 0 or c >= 3 * last_level)):
            m = min(12, z + 1)
            lvl, kind = c / m, "prepaid"
            level[t + 1: t + m] = lvl
            prepaid[t + 1: t + m] = True
            level[t], extra[t], extra_kind[t] = lvl, c - lvl, kind
            last_level, seen_payment, zeros_before = lvl, True, 0
            t += 1
            continue

        # 0b) el mismo pago grande cerca del final de la serie: los meses en 0 que confirmarían el prepago
        #     todavía no existen (censura a la derecha). Se reconoce el nivel anterior (o c/12 si es nuevo) y el
        #     resto queda como caja en confirmación, igual que el churn de los últimos meses.
        if (t + 1 + z == T and z < rules.prepay_min_zeros and c >= rules.prepay_min_amount
                and (last_level == 0 or c >= 3 * last_level)):
            lvl = last_level if last_level > 0 else c / 12
            level[t + 1:] = lvl
            prepaid[t + 1:] = True
            level[t], extra[t], extra_kind[t] = lvl, c - lvl, "prepaid_pending"
            last_level, seen_payment, zeros_before = lvl, True, 0
            t += 1
            continue

        # a) pago de puesta al día o pago agrupado: c ≈ k × nivel, y el monto alto NO se mantiene.
        #    Si el monto alto se mantiene el mes siguiente, es una expansión real, no un pago agrupado.
        high_persists = nxt > 0 and abs(nxt / c - 1) <= rules.rel_tol
        jumped = zeros_before > 0 or not seen_payment or (last_level > 0 and c >= 1.8 * last_level)
        candidates = []
        if nxt > 0 and jumped:
            candidates.append(nxt)                  # vuelve al nivel normal el mes siguiente
        if last_level > 0 and not high_persists and (zeros_before > 0 or abs(nxt / last_level - 1) <= rules.rel_tol):
            candidates.append(last_level)           # pago al nivel anterior (puesta al día o pago doble aislado)
        for ref in (candidates if rules.detect_catchup else []):
            k = _is_multiple(c, ref, rules.rel_tol)
            if k:
                lvl, kind = ref, ("arrears" if (zeros_before > 0 or not seen_payment) else "lump")
                if zeros_before > 0 and k >= zeros_before + 1:
                    covered[t] = True
                break

        # b) retroactivo de una subida de precio: L -> L(1+k·p) -> L(1+p)
        if (rules.detect_pricing and not kind and last_level > 0 and zeros_before == 0
                and nxt > 0 and c > nxt):
            p = nxt / last_level - 1
            if 0.01 <= p <= 0.15:
                k_r = (c / last_level - 1) / p
                if 2 <= round(k_r) <= rules.retro_max_k and abs(k_r - round(k_r)) < 0.05:
                    lvl, kind = nxt, "retro"
                    uplift[t] = "high"

        # c) pico puntual (no recurrente) en clientes de suscripción estable
        if not kind and not usage_like and not (nxt > 0 and abs(nxt / c - 1) <= 0.25):
            window = cash[max(0, t - 6): t + 7]
            window = np.delete(window, min(t, 6))
            window = window[window > 0]
            if len(window) >= 2:
                local = float(np.median(window))
                if c > rules.spike_factor * local:
                    lvl = last_level if last_level > 0 and abs(last_level / local - 1) <= 0.25 else local
                    kind = "arrears" if zeros_before > 0 else "spike"

        level[t] = lvl
        extra[t] = c - lvl
        extra_kind[t] = kind
        last_level = lvl
        seen_payment = True
        zeros_before = 0
        t += 1

    # --- 2. Estado de los meses en 0: antes del primer pago, mora tolerada o churn ----------------
    status = np.where(pos, "active", "").astype(object)
    status[prepaid] = "prepaid"
    gap_paid = np.zeros(T, dtype=bool)
    covered_month = pos | prepaid               # meses con servicio pagado (directo o por prepago)
    t = 0
    while t < T:
        if covered_month[t]:
            t += 1
            continue
        s = t
        while t < T and not covered_month[t]:
            t += 1
        e = t - 1                                   # corrida de ceros [s, e]
        g = e - s + 1
        before = level[s - 1] if s > 0 and pos[: s].any() else 0.0
        if not pos[: s].any():
            status[s: e + 1] = "pre"                # todavía no es cliente
        elif e == T - 1:                            # ceros al final de la serie (censura a la derecha)
            if g <= rules.gap_tolerance and rules.trailing_policy == "carry":
                status[s: e + 1] = "delinquent_open"
                level[s: e + 1] = before
            else:
                status[s: e + 1] = "churned"
        else:                                       # hueco interno: vuelve a pagar en e + 1
            if covered[e + 1] or g <= rules.gap_tolerance:
                status[s: e + 1] = "gap"
                level[s: e + 1] = before
                gap_paid[s: e + 1] = covered[e + 1]
            else:
                status[s: e + 1] = "churned"

    # --- 3. Subidas de precio de confianza media: alza persistente de +2% a +10% -----------------
    if rules.detect_pricing and not usage_like:
        for t in range(1, T):
            if uplift[t] or level[t - 1] <= 0 or level[t] <= 0:
                continue
            r = level[t] / level[t - 1] - 1
            if not rules.uplift_min <= r < rules.uplift_max:
                continue
            if t == T - 1:
                uplift[t] = "pending"                # sin mes siguiente: en confirmación, como el churn final
            elif abs(level[t + 1] / level[t] - 1) < 0.005:
                uplift[t] = "medium"

    return dict(level=level, extra=extra, extra_kind=extra_kind, uplift=uplift, status=status,
                gap_paid=gap_paid, usage_like=np.full(T, usage_like))


def classify(series: np.ndarray, uplift: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Clasifica el cambio mes a mes de una serie de MRR. Devuelve (movimiento, delta)."""
    T = len(series)
    mv = np.array(["none"] * T, dtype=object)
    delta = np.zeros(T)
    ever = series[0] > 0
    mv[0] = "opening" if series[0] > 0 else "none"
    for t in range(1, T):
        prev, cur = series[t - 1], series[t]
        delta[t] = cur - prev
        if prev == 0 and cur > 0:
            mv[t] = "reactivation" if ever else "new"
        elif prev > 0 and cur == 0:
            mv[t] = "churn"
        elif cur > prev:
            mv[t] = "price_uplift" if (uplift is not None and uplift[t]) else "expansion"
        elif cur < prev:
            mv[t] = "contraction"
        ever = ever or cur > 0
    return mv, delta


def build_customer_month(tx: pd.DataFrame, rules: Rules = Rules()) -> pd.DataFrame:
    """Tabla cliente-mes con ambos modelos. `tx` = load_transactions() (columnas customer_id, month, cash_cop)."""
    out = []
    for cid, g in tx.groupby("customer_id", sort=True):
        cash = g["cash_cop"].to_numpy(dtype=float)
        inf = infer_customer(cash, rules)
        mv_cur, d_cur = classify(cash)
        mv_new, d_new = classify(inf["level"], inf["uplift"])
        ratio = np.divide(inf["level"], np.r_[np.nan, inf["level"][:-1]],
                          out=np.full(len(cash), np.nan), where=np.r_[False, inf["level"][:-1] > 0])
        out.append(pd.DataFrame({
            "customer_id": cid, "month": g["month"].to_numpy(), "cash_cop": cash,
            "mrr_actual_cop": cash, "mv_actual": mv_cur, "delta_actual": d_cur,
            "mrr_cop": inf["level"], "mv": mv_new, "delta": d_new,
            "uplift_conf": inf["uplift"], "status": inf["status"], "gap_paid": inf["gap_paid"],
            "extra_cop": inf["extra"], "extra_kind": inf["extra_kind"], "usage_like": inf["usage_like"],
            "half_cut": (mv_new == "contraction") & np.isclose(ratio, 0.5, atol=0.005),
        }))
    cm = pd.concat(out, ignore_index=True)
    first_pay = cm[cm["cash_cop"] > 0].groupby("customer_id")["month"].min().rename("first_paid_month")
    cm = cm.merge(first_pay, on="customer_id", how="left")
    start = cm["month"].min()
    # Censura a la izquierda: quien paga por primera vez en los primeros N meses pudo ser un cliente en mora
    cm["left_censored"] = (cm["first_paid_month"] - start).apply(lambda d: d.n) <= rules.gap_tolerance
    return cm


def bridge(cm: pd.DataFrame, model: str = "corrected") -> pd.DataFrame:
    """Puente mensual de MRR (mes × movimiento) y verificación de conciliación."""
    mv_col, d_col, mrr_col = (("mv", "delta", "mrr_cop") if model == "corrected"
                              else ("mv_actual", "delta_actual", "mrr_actual_cop"))
    br = cm.pivot_table(index="month", columns=mv_col, values=d_col, aggfunc="sum", fill_value=0.0)
    br = br.reindex(columns=[c for c in ALL_MOVES if c in br.columns] or ALL_MOVES, fill_value=0.0)
    mrr = cm.groupby("month")[mrr_col].sum()
    br.insert(0, "mrr_open", mrr.shift(1))
    br["mrr_close"] = mrr
    br["check"] = br["mrr_open"] + br[[c for c in ALL_MOVES if c in br.columns]].sum(axis=1) - br["mrr_close"]
    return br
