"""Evita mezclar versiones de código tras un redespliegue."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = (ROOT / "app", ROOT / "finora")
ORDER = ("finora.", "brand", "common", "operar")


def _rank(name: str) -> int:
    return next((i for i, p in enumerate(ORDER) if name == p or name.startswith(p)), len(ORDER))


def reload_project_modules() -> None:
    mods = []
    for name, mod in list(sys.modules.items()):
        path = getattr(mod, "__file__", None)
        if not path or name in (__name__, "__main__"):
            continue
        try:
            if any(Path(path).resolve().is_relative_to(d) for d in DIRS):
                mods.append((name, mod))
        except (OSError, ValueError):
            continue
    for name, mod in sorted(mods, key=lambda nm: _rank(nm[0])):
        importlib.reload(mod)
