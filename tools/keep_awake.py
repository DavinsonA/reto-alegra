"""Abre las apps publicadas con un navegador real y despierta las dormidas. Uso: python tools/keep_awake.py"""
import ast
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
LINKS = ast.literal_eval(re.search(r"^LINKS = (\{.*\})", (ROOT / "app" / "common.py").read_text(encoding="utf-8"),
                                   re.M).group(1))
WAKE = "button:has-text('Yes, get this app back up')"


def visit(page, url: str) -> tuple[bool, bool]:
    """Abre la app y espera a que renderice. Devuelve (renderizó, hubo que despertarla)."""
    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    woke = False
    for _ in range(40):
        page.wait_for_timeout(5000)
        for fr in page.frames:
            try:
                if fr.locator(WAKE).count():
                    fr.locator(WAKE).first.click()
                    woke = True
                if fr.locator('[data-testid="stSidebar"]').count():
                    return True, woke
            except Exception:
                pass
    return False, woke


def main() -> int:
    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.environ.get("PW_CHANNEL") or None)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for name, url in LINKS.items():
            ok, woke = visit(page, url)
            print(f"{name}: {'renderizó' if ok else 'NO renderizó'}{' (estaba dormida)' if woke else ''} · {url}")
            if not ok:
                failed.append(name)
        browser.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
