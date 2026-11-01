#!/usr/bin/env python3
"""Build and validate printable A4 PDFs for actual transformation worksheets."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "worksheets"
DEST = ROOT / "pdf"
IDS = ("349", "350", "351", "352", "385", "549", "rectangles", "true-false", "triangle", "orig-rectangles", "orig-translation", "orig-reflection", "orig-rotation", "orig-composition", "orig-symmetry")

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
                    page.goto(source.as_uri(), wait_until="load", timeout=60000)
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
                    if not reader.pages or target.stat().st_size < 3500:
                        raise RuntimeError("Empty or invalid PDF: " + str(target))
                    print(f"{stem}: {len(reader.pages)} pages, {target.stat().st_size} bytes")
                finally:
                    page.close()
        finally:
            browser.close()

if __name__ == "__main__":
    main()
