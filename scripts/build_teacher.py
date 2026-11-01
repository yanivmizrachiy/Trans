#!/usr/bin/env python3
"""Build numbered, sourced A4 teacher summaries with strict overflow and PDF checks."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "book" / "teacher.html"
OUTPUT = ROOT / "book" / "teacher.pdf"
EXPECTED = 14

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(str(SOURCE))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": 1200, "height": 1600})
            js_errors = []
            page.on("pageerror", lambda e: js_errors.append(str(e)))
            page.goto(SOURCE.as_uri(), wait_until="load", timeout=60000)
            page.emulate_media(media="print")
            page.evaluate("document.fonts.ready")
            inspection = page.evaluate("""() => {
                const sheets = Array.from(document.querySelectorAll("article.sheet"));
                const issues = [];
                for (const [i,s] of sheets.entries()) {
                    const a=s.getBoundingClientRect(), main=s.querySelector(".content").getBoundingClientRect(),
                      foot=s.querySelector(".source").getBoundingClientRect();
                    if (main.bottom > foot.top - 2) issues.push([i+1,"footer overlap",Math.round(main.bottom-foot.top)]);
                    if (foot.bottom > a.bottom - 10) issues.push([i+1,"foot out of paper",Math.round(foot.bottom-a.bottom)]);
                    if (s.scrollHeight > s.clientHeight + 2) issues.push([i+1,"overflow",s.scrollHeight-s.clientHeight]);
                    if (!s.querySelector(".source").textContent.includes("אסמכתה")) issues.push([i+1,"missing source"]);
                }
                return {count:sheets.length,issues:issues};
            }""")
            if inspection["count"] != EXPECTED or inspection["issues"] or js_errors:
                raise RuntimeError(f"Teacher page layout failed: {inspection}, errors={js_errors}")
            page.pdf(path=str(OUTPUT), format="A4", print_background=True,
                     prefer_css_page_size=True,
                     margin={"top":"0","right":"0","bottom":"0","left":"0"})
            page.close()
        finally:
            browser.close()
    reader = PdfReader(str(OUTPUT))
    if len(reader.pages) != EXPECTED:
        raise RuntimeError(f"Expected {EXPECTED} numbered A4 teacher pages, got {len(reader.pages)}")
    sizes = [(float(pg.mediabox.width), float(pg.mediabox.height)) for pg in reader.pages]
    if any(not (588<=w<=604 and 834<=h<=850) for w,h in sizes):
        raise RuntimeError(f"Teacher pages are not A4 portrait: {sizes}")
    if OUTPUT.stat().st_size < 20000:
        raise RuntimeError("Unexpectedly empty teacher summary PDF")
    print(f"PASS: {EXPECTED} numbered RTL A4 summary pages, no overflow, each with source footer; {OUTPUT.stat().st_size} bytes")

if __name__=="__main__":main()
