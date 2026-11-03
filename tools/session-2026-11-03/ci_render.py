"""Print a razpage worksheet with Arimo standing in for the runner's Liberation Sans (CI proxy).
Usage: python ci_render.py <stem> <outdir> [proxy|local]"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import fitz
stem, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(exist_ok=True)
mode = sys.argv[3] if len(sys.argv) > 3 else "proxy"
src = Path(__file__).resolve().parents[2] / "worksheets" / f"{stem}.html"
PROXY = """() => new Promise(res => {
  const l=document.createElement('link'); l.rel='stylesheet';
  l.href='https://fonts.googleapis.com/css2?family=Arimo:ital,wght@0,400;0,500;0,700;1,400;1,700&display=block';
  l.onload=()=>{ const s=document.createElement('style'); s.textContent='*{font-family:Arimo,sans-serif!important}';
    document.head.appendChild(s); document.fonts.load('700 15px Arimo','אבג').then(()=>document.fonts.load('400 15px Arimo','אבג')).then(res); };
  document.head.appendChild(l); })"""
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    try:
        pg = b.new_page(viewport={"width": 794, "height": 1123})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(src.as_uri(), wait_until="load", timeout=60000)
        if mode == "proxy":
            pg.evaluate(PROXY)
            pg.evaluate("() => window.draw385 && window.draw385()")
        pg.emulate_media(media="print")
        pg.evaluate("async () => { await document.fonts.ready; }")
        info = pg.evaluate("""() => { const q=document.querySelector('main.a4-page .question-block'); if(!q) return null;
              const kids=[...q.children]; const gap=parseFloat(getComputedStyle(q).rowGap)||0;
              const used=kids.reduce((s,k)=>s+k.getBoundingClientRect().height,0)+gap*(kids.length-1);
              const m=document.querySelector('main.a4-page');
              return {free:Math.round(q.getBoundingClientRect().height-used), scroll:m.scrollHeight, client:m.clientHeight,
                      kids:kids.map(k=>Math.round(k.getBoundingClientRect().height)),
                      fonts:[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family+' '+f.weight).slice(0,8)}; }""")
        pg.pdf(path=str(out / f"{stem}.pdf"), format="A4", print_background=True, prefer_css_page_size=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    finally:
        b.close()
d = fitz.open(out / f"{stem}.pdf")
for i, page in enumerate(d, 1):
    page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6)).save(out / f"{stem}-{i}.png")
print(stem, mode, "pages", len(d), info, "errors", errs)
