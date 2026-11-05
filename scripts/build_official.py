#!/usr/bin/env python3
"""Print book/official.html, the curriculum questions redrawn as A4 pages, to book/official.pdf.

The questions are edited in book/official.html and their figures are drawn by assets/figures.js.
One printed page per Ministry page in data/manifest.json. The photographed source pages stay in
sources/ministry/ as the reference for the wording and the figures.
"""
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
import manifest as M

SOURCE = M.ROOT / "book" / "official.html"
OUTPUT = M.ROOT / "book" / "official.pdf"

AUDIT = """() => [...document.querySelectorAll('.qpage')].flatMap(p => {
  const e = [], box = p.getBoundingClientRect(), foot = p.querySelector('.page-foot'), logo = p.querySelector('.ws-logo');
  if (p.scrollHeight > p.clientHeight + 1 || p.scrollWidth > p.clientWidth + 1) e.push([p.id, 'page overflow']);
  const body = p.querySelector('.qbody');
  if (body.scrollHeight > body.clientHeight + 1) e.push([p.id, 'content runs into the footer', body.scrollHeight - body.clientHeight]);
  if (!foot || Math.abs(foot.getBoundingClientRect().bottom - box.bottom) > 2) e.push([p.id, 'footer must close the page']);
  if (!logo || !logo.complete || !logo.naturalWidth) e.push([p.id, 'logo not loaded']);
  p.querySelectorAll('svg[data-fig]').forEach(s => { if (!s.childElementCount) e.push([p.id, 'empty figure']); });
  return e;
})"""


def main():
    pages = list(M.MINISTRY_PAGES)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            tab = browser.new_page(viewport={"width": 794, "height": 1123})
            tab.set_default_timeout(60000)
            errors = []
            tab.on("pageerror", lambda e: errors.append(str(e)))
            tab.goto(SOURCE.as_uri(), wait_until="load")
            tab.emulate_media(media="print")
            ids = tab.evaluate("() => [...document.querySelectorAll('.qpage')].map(p => p.id)")
            if ids != [f"p{n}" for n in pages]:
                raise RuntimeError(f"book/official.html pages {ids} differ from data/manifest.json {pages}")
            bad = tab.evaluate(AUDIT)
            if bad or errors:
                raise RuntimeError(f"Curriculum pages failed: {bad} {errors}")
            tab.pdf(path=str(OUTPUT), format="A4", print_background=True, prefer_css_page_size=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        finally:
            browser.close()
    pdf = PdfReader(str(OUTPUT))
    if len(pdf.pages) != len(pages):
        raise RuntimeError(f"Curriculum PDF has {len(pdf.pages)} pages, expected {len(pages)}")
    for i, page in enumerate(pdf.pages):
        if not (588 < float(page.mediabox.width) < 604 and 834 < float(page.mediabox.height) < 850):
            raise RuntimeError(f"Curriculum page {i + 1} is not portrait A4")
    print(f"PASS: {len(pages)} curriculum pages printed as portrait A4 ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
