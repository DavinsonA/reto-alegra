"""Validación cruzada: el SQL (DuckDB) y el motor en Python deben dar el mismo resultado."""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finora.load import load_transactions
from finora.mrr import bridge, build_customer_month
from finora.two_layer import two_layer_movements


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(f"SET file_search_path = '{ROOT.as_posix()}'")
    for f in ("01_modelo_actual.sql", "02_modelo_dos_capas_ddl.sql", "03_movimientos_dos_capas.sql"):
        c.execute((ROOT / "sql" / f).read_text(encoding="utf-8"))
    return c


def test_sql_modelo_actual_concilia(con):
    chk = con.execute("SELECT MAX(ABS(check_cop)) FROM rpt_bridge_actual WHERE mrr_open IS NOT NULL").fetchone()[0]
    assert chk < 1e-3


def test_sql_y_python_dan_el_mismo_puente_actual(con):
    sql = con.execute("SELECT * FROM rpt_bridge_actual ORDER BY month").df()
    sql["month"] = pd.PeriodIndex(pd.to_datetime(sql["month"]), freq="M")
    py = bridge(build_customer_month(load_transactions()), "actual")
    for mv in ("new", "expansion", "contraction", "churn", "reactivation"):
        a = sql.set_index("month")[mv].iloc[1:]
        b = py[mv].reindex(a.index).fillna(0)
        assert np.allclose(a.to_numpy(), b.to_numpy(), atol=1e-3), mv


CFO_CASES = {
    1: (100, 100, 0, 20),
    2: (100, 80, 0, 0),
    3: (100, 130, 0, 30),
    4: (130, 130, 30, 0),
    5: (100, 0, 20, 0),
}


def test_sql_dos_capas_igual_a_python_en_los_casos_del_cfo(con):
    rows = []
    for cid, (l1, l2, d1, d2) in CFO_CASES.items():
        rows += [(cid, "2025-01-01", l1, d1, l1 - d1, "current"), (cid, "2025-02-01", l2, d2, l2 - d2, "current")]
    con.execute("DELETE FROM fct_mrr_customer_month")
    con.executemany("INSERT INTO fct_mrr_customer_month VALUES (?, ?, ?, ?, ?, ?)", rows)
    sql = con.execute("SELECT customer_id, layer, movement, amount_cop FROM v_two_layer_movements").df()
    for cid, (l1, l2, d1, d2) in CFO_CASES.items():
        py = two_layer_movements([l1, l2], [d1, d2])
        got = {(r.layer, r.movement): float(r.amount_cop) for r in sql[sql["customer_id"] == cid].itertuples()}
        exp = {(r.layer, r.movement): float(r.amount) for r in py.itertuples()}
        assert got == exp, (cid, got, exp)
    net = con.execute("SELECT SUM(net_change_cop) FROM v_bridge_two_layer").fetchone()[0]
    assert float(net) == sum((l2 - d2) - (l1 - d1) for l1, l2, d1, d2 in CFO_CASES.values())
