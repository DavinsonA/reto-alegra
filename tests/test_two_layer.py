"""Los 3 casos del CFO (más 2 bordes) resueltos con el modelo de dos capas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finora.two_layer import executive_view, two_layer_movements  # noqa: E402


def moves(mov):
    return {(r.layer, r.movement): r.amount for r in mov.itertuples()}


def test_cfo_1a_pagaba_100_ahora_80_por_descuento():
    m = moves(two_layer_movements([100, 100], [0, 20]))
    assert m == {("pricing", "discount_start"): -20}          # NO es contracción


def test_cfo_1b_pagaba_100_ahora_80_por_downgrade():
    m = moves(two_layer_movements([100, 80], [0, 0]))
    assert m == {("customer", "contraction"): -20}


def test_cfo_2_expansion_escondida_por_descuento():
    m = moves(two_layer_movements([100, 130], [0, 30]))
    assert m == {("customer", "expansion"): 30, ("pricing", "discount_start"): -30}   # neto 0


def test_cfo_3_fin_del_descuento_no_es_expansion():
    m = moves(two_layer_movements([130, 130], [30, 0]))
    assert m == {("pricing", "discount_end"): 30}             # NO es expansión


def test_churn_con_descuento_vigente_es_churn_neto_en_vista_ejecutiva():
    mov = two_layer_movements([100, 0], [20, 0])
    ex = executive_view(mov).set_index("movement")["amount"]
    assert ex["churn"] == -80                                  # pierde lo que realmente pagaba


def test_new_con_descuento_de_bienvenida():
    m = moves(two_layer_movements([0, 100], [0, 25]))
    assert m == {("customer", "new"): 100, ("pricing", "discount_start"): -25}


def test_repricing_de_catalogo_no_es_expansion():
    m = moves(two_layer_movements([100, 105], [0, 0], repricing=[False, True]))
    assert m == {("pricing", "repricing"): 5}
