#!/usr/bin/env python3
"""Build and validate printable A4 PDFs for actual transformation worksheets."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from manifest import WORKSHEETS, WORKSHEET_PAGES

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "worksheets"
DEST = ROOT / "pdf"
IDS = WORKSHEETS  # data/manifest.json is the only inventory of worksheet ids

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            for stem in IDS:
                source = SOURCE / (stem + ".html")
                if not source.exists():
                    raise FileNotFoundError(str(source))
                page = browser.new_page(viewport={"width": 1250, "height": 1650}, device_scale_factor=1)
                try:
                    page_errors = []
                    page.on("pageerror", lambda err: page_errors.append(str(err)))
                    page.goto(source.as_uri(), wait_until="load", timeout=60000)
                    if stem.startswith("orig-"):
                        page.wait_for_function(
                            '() => Array.from(document.querySelectorAll("svg[data-shape]")).every(s => !!s.querySelector("polygon"))',
                            timeout=15000
                        )
                    if stem.startswith("orig-"):
                        ok = page.evaluate("""() => {
                          const img = document.querySelector('img.ws-logo[alt="יחידת מתמטיקה — מחוז ירושלים והעיר ירושלים"]');
                          const credit = document.querySelector('.ws-foot .ws-credit strong');
                          const line = document.querySelector('.ws-foot .ws-footline');
                          const graph = document.querySelector('svg[data-shape] polygon');
                          const sheet = document.querySelector('article.sheet');
                          return !!(img && img.complete && img.naturalWidth > 0 && credit && line && line.getBoundingClientRect().width > 0.9 * sheet.querySelector('.ws-foot').getBoundingClientRect().width &&
                                    graph && sheet && getComputedStyle(document.documentElement).direction === 'rtl');
                        }""")
                        if not ok:
                            raise RuntimeError(f"Failed visible logo, geometry drawing, or RTL check: {stem}")
                        if page_errors:
                            raise RuntimeError(f"JavaScript errors in original worksheet {stem}: {page_errors}")
                    page.evaluate("""async () => {
                      if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) {
                        await Promise.race([
                           window.MathJax.startup.promise,
                           new Promise(resolve => setTimeout(resolve, 8000))
                        ]);
                      }
                      await document.fonts.ready;
                    }""")
                    target = DEST / (stem + ".pdf")
                    page.pdf(path=str(target), format="A4", print_background=True,
                             prefer_css_page_size=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
                    reader = PdfReader(str(target))
                    if len(reader.pages) != WORKSHEET_PAGES[stem]:
                        raise RuntimeError(f"Worksheet {stem} must print on exactly {WORKSHEET_PAGES[stem]} A4 page(s); got {len(reader.pages)}")
                    if not reader.pages or target.stat().st_size < 3500:
                        raise RuntimeError("Empty or invalid PDF: " + str(target))
                    print(f"{stem}: {len(reader.pages)} pages, {target.stat().st_size} bytes")
                finally:
                    page.close()
        finally:
            browser.close()

if __name__ == "__main__":
    main()
