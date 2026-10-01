"""Finora · tablero operativo: las dos revisiones recurrentes, para seguir usándolas después del reto.

- Revisión mensual del MRR (CFO, en el cierre): datos reales agregados.
- Revisión semanal del funnel (CRO, 30 minutos): prototipo con datos sintéticos hasta tener eventos del CRM.
Ejecutar:  streamlit run app/tablero.py
"""
from __future__ import annotations

import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path[:0] = [str(APP.parent), str(APP)]

import common as C  # noqa: E402
import operar as O  # noqa: E402
from finora.funnel_synth import CHANNELS  # noqa: E402

S_MON = "Revisión mensual del MRR · CFO"
S_WEEK = "Revisión semanal del funnel · CRO"
SECTIONS = [S_MON, S_WEEK]

T, section = C.page("tablero", SECTIONS, "para operar cada mes y cada semana", top_nav=True)

if section == S_MON:
    O.monthly_review(T)
else:
    O.weekly_review(T, dict(zip(CHANNELS, T.viz)))
