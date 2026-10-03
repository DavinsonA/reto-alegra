"""Pruebas del motor de MRR: casos sintéticos con la respuesta conocida y conciliación con los datos reales."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finora.load import load_transactions
from finora.mrr import Rules, bridge, build_customer_month, classify, infer_customer


def run(cash, rules=Rules()):
    cash = np.asarray(cash, dtype=float)
    inf = infer_customer(cash, rules)
    mv, delta = classify(inf["level"], inf["uplift"])
    return inf, list(mv), delta


def test_constante_sin_movimientos():
    _, mv, _ = run([6.3] * 6)
    assert mv == ["opening"] + ["none"] * 5


def test_hueco_de_un_mes_con_puesta_al_dia_no_es_churn():
    inf, mv, _ = run([6.3, 6.3, 0, 12.6, 6.3])
    assert "churn" not in mv and "reactivation" not in mv
    assert inf["status"][2] == "gap" and inf["gap_paid"][2]
    assert inf["extra_kind"][3] == "arrears" and inf["extra"][3] == pytest.approx(6.3)
    mv_actual, _ = classify(np.array([6.3, 6.3, 0, 12.6, 6.3]))
    assert list(mv_actual)[2:4] == ["churn", "reactivation"]


def test_hueco_largo_pagado_completo_no_es_churn():
    cash = [12.6] + [0] * 7 + [100.8, 12.6]
    inf, mv, _ = run(cash)
    assert "churn" not in mv and all(inf["status"][1:8] == "gap")


def test_hueco_mayor_a_N_sin_pago_es_churn_y_reactivacion():
    _, mv, _ = run([5, 5, 0, 0, 0, 5, 5], Rules(gap_tolerance=2))
    assert mv[2] == "churn" and mv[5] == "reactivation"


def test_subida_de_precio_con_retroactivo():
    inf, mv, delta = run([8.4, 8.4, 10.232, 8.858, 8.858])
    assert mv[2] == "price_uplift" and inf["uplift"][2] == "high"
    assert delta[2] == pytest.approx(0.458)
    assert inf["extra_kind"][2] == "retro" and inf["extra"][2] == pytest.approx(1.374)
    assert mv[3] == "none"


def test_alza_persistente_moderada_es_precio_de_confianza_media():
    inf, mv, _ = run([10, 10, 10.5, 10.5])
    assert mv[2] == "price_uplift" and inf["uplift"][2] == "medium"


def test_alza_grande_es_expansion():
    _, mv, _ = run([10, 10, 13, 13])
    assert mv[2] == "expansion"


def test_duplicar_y_mantener_es_expansion_no_pago_agrupado():
    inf, mv, _ = run([5, 5, 10, 10, 10])
    assert mv[2] == "expansion" and list(inf["extra_kind"]) == [""] * 5


def test_bajada_a_la_mitad_es_contraccion_ambigua():
    _, mv, _ = run([10, 10, 5, 5])
    assert mv[2] == "contraction"


def test_mora_abierta_al_final_se_mantiene_marcada():
    inf, mv, _ = run([5, 5, 5, 0])
    assert inf["status"][3] == "delinquent_open" and "churn" not in mv
    _, mv2, _ = run([5, 5, 5, 0], Rules(trailing_policy="churn"))
    assert mv2[3] == "churn"


def test_prepago_anual_se_reparte_en_12_meses_y_luego_churn():
    r = Rules(prepay_min_amount=20)
    cash = [0, 94.5] + [0] * 15
    inf, mv, _ = run(cash, r)
    assert inf["level"][1:13] == pytest.approx([94.5 / 12] * 12)
    assert all(inf["status"][2:13] == "prepaid")
    assert mv[1] == "new" and mv[13] == "churn" and mv.count("churn") == 1


def test_prepago_anual_renovado_no_es_churn():
    r = Rules(prepay_min_amount=20)
    cash = [80.36] + [0] * 11 + [76.34] + [0] * 11
    _, mv, _ = run(cash, r)
    assert "churn" not in mv and "reactivation" not in mv and mv[12] == "contraction"


def test_ceros_largos_al_final_son_churn():
    _, mv, _ = run([5, 5, 0, 0, 0])
    assert mv[2] == "churn"


def test_subida_en_el_ultimo_mes_queda_en_confirmacion():
    inf, mv, _ = run([10, 10, 10, 10.85])
    assert mv[3] == "price_uplift" and inf["uplift"][3] == "pending"
    inf2, _, _ = run([10, 10, 10.85, 10.85])
    assert inf2["uplift"][2] == "medium"


def test_pago_grande_al_final_es_prepago_en_confirmacion():
    r = Rules(prepay_min_amount=20)
    inf, mv, _ = run([5, 5, 5, 0, 0, 0, 40], r)
    assert mv[6] == "reactivation" and inf["level"][6] == pytest.approx(5)
    assert inf["extra_kind"][6] == "prepaid_pending" and inf["extra"][6] == pytest.approx(35)
    inf2, mv2, _ = run([0, 96, 0, 0], r)
    assert mv2[1] == "new" and inf2["level"][1] == pytest.approx(8)
    assert list(inf2["status"][2:]) == ["prepaid", "prepaid"] and "churn" not in mv2


def test_sin_puestas_al_dia_el_pago_doble_es_expansion_y_contraccion():
    _, mv, _ = run([6.3, 6.3, 0, 12.6, 6.3], Rules(detect_catchup=False))
    assert mv[3:5] == ["expansion", "contraction"]
    inf, _, _ = run([6.3, 6.3, 0, 12.6, 6.3], Rules(rel_tol=0))
    assert inf["extra_kind"][3] == "arrears"


@pytest.fixture(scope="module")
def cm():
    return build_customer_month(load_transactions())


def test_datos_reales_conciliacion_del_puente(cm):
    for model in ("corrected", "actual"):
        br = bridge(cm, model).iloc[1:]
        assert br["check"].abs().max() < 1e-6, model


def test_datos_reales_caja_igual_a_mrr_mas_extra_en_meses_pagados(cm):
    paid = cm[cm["cash_cop"] > 0]
    assert np.allclose(paid["cash_cop"], paid["mrr_cop"] + paid["extra_cop"])


def test_datos_reales_sin_mrr_negativo(cm):
    assert (cm["mrr_cop"] >= 0).all()
