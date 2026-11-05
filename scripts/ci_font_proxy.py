#!/usr/bin/env python3
"""Print worksheets with the text widths of the build server.

The runner sets Arial as Liberation Sans, whose Hebrew is about 6-8% wider than Windows Arial, so a
sheet that fits one page locally can run onto a second page on CI (worksheet 385 did).
Google Fonts Arimo stands in for it: its word widths match the runner within about 0.4%, and it is
slightly pessimistic for a line that sits right at the limit.

Usage: python scripts/ci_font_proxy.py [stem ...] [--out DIR]
Prints each sheet's page count against data/manifest.json and the room left on it, and saves the
PDF and a PNG of every page in DIR (a new temporary folder by default). Needs network for the font.
"""
import argparse
import sys
import tempfile
from pathlib import Path
import fitz
from playwright.sync_api import sync_playwright
from manifest import WORKSHEETS, WORKSHEET_PAGES

ROOT = Path(__file__).resolve().parents[1]
FONT = "https://fonts.googleapis.com/css2?family=Arimo:ital,wght@0,400;0,500;0,600;0,700;1,400;1,700&display=block"
INIT = """document.addEventListener('DOMContentLoaded', () => {
  const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = '%s'; document.head.appendChild(l);
  const s = document.createElement('style'); s.textContent = '*{font-family:Arimo,sans-serif!important}'; document.head.appendChild(s);
});""" % FONT
ROOM = """() => {
  if (window.fitSheets) window.fitSheets(); if (window.drawPlanes) window.drawPlanes();
  if (window.snapSquares) window.snapSquares(); if (window.draw385) window.draw385();
  const q = document.querySelector('main.a4-page .question-block');
  if (q) {  // imported sheets: the space the question boxes leave free
    const kids = [...q.children], gap = parseFloat(getComputedStyle(q).rowGap) || 0;
    const used = kids.reduce((s, k) => s + k.getBoundingClientRect().height, 0) + gap * (kids.length - 1);
    return 'free ' + Math.round(q.getBoundingClientRect().height - used) + 'px';
  }
  // original sheets stretch their writing space to the footer; the build needs at least 27px of it
  const areas = [...document.querySelectorAll('.lines, .squares')].map(e => e.getBoundingClientRect().height);
  return areas.length ? 'shortest writing space ' + Math.round(Math.min(...areas)) + 'px' : '';
}"""

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stems", nargs="*", default=WORKSHEETS)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out = args.out or Path(tempfile.mkdtemp(prefix="ci-font-proxy-"))
    out.mkdir(parents=True, exist_ok=True)
    wrong = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            for stem in args.stems:
                page = browser.new_page(viewport={"width": 1250, "height": 1650}, device_scale_factor=1)
                try:
                    page.add_init_script(INIT)
                    page.goto((ROOT / "worksheets" / f"{stem}.html").as_uri(), wait_until="load", timeout=60000)
                    page.evaluate("async () => { await document.fonts.load('400 15px Arimo', 'א'); await document.fonts.load('700 15px Arimo', 'א'); }")
                    if stem.startswith("orig-"):
                        page.wait_for_function('() => Array.from(document.querySelectorAll("svg[data-shape]")).every(s => !!s.querySelector("polygon"))', timeout=15000)
                    page.set_viewport_size({"width": 794, "height": 1123})  # the printed A4 width, as in build_pdfs.py
                    page.emulate_media(media="print")
                    room = page.evaluate(ROOM)
                    page.evaluate("async () => { await document.fonts.ready; }")
                    page.pdf(path=str(out / f"{stem}.pdf"), format="A4", print_background=True,
                             prefer_css_page_size=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
                finally:
                    page.close()
                doc = fitz.open(out / f"{stem}.pdf")
                for n, sheet in enumerate(doc, 1):
                    sheet.get_pixmap(matrix=fitz.Matrix(1.6, 1.6)).save(out / f"{stem}-{n}.png")
                expected = WORKSHEET_PAGES.get(stem)
                ok = doc.page_count == expected
                if not ok:
                    wrong.append(stem)
                print(f"{stem}: {doc.page_count} page(s), manifest {expected}{'' if ok else '  <-- DIFFERS'}  {room}")
        finally:
            browser.close()
    print(f"PDFs and PNGs in {out}")
    return 1 if wrong else 0

if __name__ == "__main__":
    sys.exit(main())
