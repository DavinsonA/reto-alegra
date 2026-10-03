"""El prototipo sintético detecta los problemas plantados, descarta post-SQL y queda en magnitudes plausibles."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finora import funnel as F
from finora.funnel_synth import generate
from finora.xmr import xmr

AS_OF = pd.Timestamp("2024-10-31")


@pytest.fixture(scope="module")
def data():
    leads, ev = generate(target_ticket=45_000)
    r = F.reach_table(leads, ev)
    return leads, ev, r, F.period_metrics(r, AS_OF, "W")


def _last(wk, k):
    return xmr(wk[k].dropna(), baseline=26).iloc[-1]


def test_detecta_capacidad_sdr_y_descarta_post_sql(data):
    *_, wk = data
    assert _last(wk, "speed_p50")["signal"] and _last(wk, "speed_p50")["direction"] == "arriba"
    assert _last(wk, "sla_1h")["signal"] and _last(wk, "sla_1h")["direction"] == "abajo"
    assert _last(wk, "work_to_eng")["signal"] and _last(wk, "work_to_eng")["direction"] == "abajo"
    assert not _last(wk, "sql_to_won")["signal"]


def test_magnitudes_plausibles(data):
    leads, ev, r, wk = data
    sla, p50 = wk["sla_1h"].dropna(), wk["speed_p50"].dropna()
    assert 0.20 <= sla.head(26).mean() <= 0.35 and 0.05 <= sla.tail(4).mean() <= 0.12
    assert 1.5 <= p50.head(26).median() <= 2.5 and 4 <= p50.tail(4).median() <= 7
    weeks_of_volume = len(F.stalled(r, ev, AS_OF)) / wk["leads"].tail(4).mean()
    assert 1 <= weeks_of_volume <= 2.5


def test_ticket_alineado_con_el_real(data):
    leads, *_ = data
    assert leads["mrr_cop"].mean() == pytest.approx(45_000)
