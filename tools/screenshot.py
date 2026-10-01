"""Capturas de las apps para revisión visual (usa el Chrome instalado vía Playwright).

Uso: python tools/screenshot.py <salida> <puerto> [secciones...]   (la app debe correr en http://localhost:<puerto>)
Modo del sistema emulado: variable de entorno SHOT_SCHEME=light|dark (por defecto light).
Si una sección tiene pestañas, también captura cada pestaña.
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("screens")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8501
SECTIONS = [int(s) for s in sys.argv[3:]] or list(range(6))
OUT.mkdir(parents=True, exist_ok=True)


def settle(page):
    page.wait_for_selector('[data-testid="stSidebar"]', timeout=60_000)
    page.wait_for_timeout(1500)
    try:                                                   # esperar a que terminen de dibujarse los gráficos
        page.wait_for_function("document.querySelectorAll('[data-testid=\"stSkeleton\"]').length === 0", timeout=20_000)
    except Exception:
        pass
    page.wait_for_timeout(2500)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    scheme = os.environ.get("SHOT_SCHEME", "light")
    page = browser.new_page(viewport={"width": 1440, "height": int(os.environ.get("SHOT_HEIGHT", 4200))}, device_scale_factor=1, color_scheme=scheme)
    for s in SECTIONS:
        page.goto(f"http://localhost:{PORT}/?s={s}", wait_until="networkidle")
        settle(page)
        page.screenshot(path=str(OUT / f"{scheme}_{PORT}_s{s}.png"), full_page=True)
        for i, tab in enumerate(page.get_by_role("tab").all()[1:], start=1):
            tab.click()
            page.wait_for_timeout(4000)
            page.screenshot(path=str(OUT / f"{scheme}_{PORT}_s{s}_tab{i}.png"), full_page=True)
        print("ok", PORT, s)
    browser.close()
