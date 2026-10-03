"""Finora · tablero operativo: las dos revisiones recurrentes, para seguir usándolas después del reto."""
from __future__ import annotations

import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path[:0] = [str(APP.parent), str(APP)]

import fresh

fresh.reload_project_modules()

import common as C
import operar as O
from finora.funnel_synth import CHANNELS

S_MON = "Mensual del MRR · CFO"
S_WEEK = "Semanal del funnel · CRO"
SECTIONS = [S_MON, S_WEEK]

T, section = C.page("tablero", SECTIONS, "para operar cada mes y cada semana", top_nav=True)

if section == S_MON:
    O.monthly_review(T)
else:
    O.weekly_review(T, dict(zip(CHANNELS, T.viz)))
