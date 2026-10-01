"""Evita mezclar versiones de código tras un redespliegue.

Streamlit (también en Community Cloud) vuelve a ejecutar el script principal cuando cambia el código, pero puede
conservar en memoria la versión vieja de los módulos importados. Así pasó en la demo publicada: el script nuevo pedía
`common.FIGURES` a un `common` viejo y fallaba con AttributeError. Cada app llama a `reload_project_modules()` antes de
importar sus módulos: recarga los del proyecto que ya estén en memoria, dependencias primero.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = (ROOT / "app", ROOT / "finora")                     # solo el código de las apps y el motor
ORDER = ("finora.", "brand", "common", "operar")          # primero lo que no depende de nada del proyecto


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
