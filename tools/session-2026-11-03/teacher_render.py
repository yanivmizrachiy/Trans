"""Print book/teacher.html like build_teacher.py, report free space per sheet, save PNGs.
Usage: python teacher_render.py <repo> <outdir> local|proxy [summary numbers to save...]
proxy: Arimo stands in for the runner's Liberation Sans (Hebrew 6-8% wider than Windows Arial)."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import fitz

repo, out, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
save = [int(a) for a in sys.argv[4:]]
out.mkdir(parents=True, exist_ok=True)
PROXY = """() => new Promise(res => {
  const l=document.createElement('link'); l.rel='stylesheet';
  l.href='https://fonts.googleapis.com/css2?family=Arimo:ital,wght@0,400;0,500;0,700;1,400;1,700&display=block';
  l.onload=()=>{ const s=document.createElement('style'); s.textContent='*{font-family:Arimo,sans-serif!important}';
    document.head.appendChild(s); document.fonts.load('700 15px Arimo','אבג').then(()=>document.fonts.load('400 15px Arimo','אבג')).then(res); };
  document.head.appendChild(l); })"""
CHECK = """() => Array.from(document.querySelectorAll('article.sheet')).map((s,i)=>{
  const a=s.getBoundingClientRect(), m=s.querySelector('.content').getBoundingClientRect(), f=s.querySelector('.source').getBoundingClientRect();
  const px=96/25.4, main=s.querySelector('.content'), kids=[...main.children];
  const last=Math.max(...kids.map(k=>k.getBoundingClientRect().bottom+parseFloat(getComputedStyle(k).marginBottom)));
  return [i+1, +((f.top-last)/px).toFixed(1), s.scrollHeight-s.clientHeight, Math.round(f.bottom-a.bottom), s.dataset.fit];
})"""
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    try:
        tab = b.new_page(viewport={"width": 1200, "height": 1600})
        tab.on("pageerror", lambda e: errors.append(str(e)))
        tab.goto((repo / "book" / "teacher.html").as_uri(), wait_until="load", timeout=60000)
        if mode == "proxy":
            tab.evaluate(PROXY)
        tab.emulate_media(media="print")
        tab.evaluate("async () => { await document.fonts.ready; }")
        tab.evaluate("() => window.fitSheets && window.fitSheets()")
        rows = tab.evaluate(CHECK)
        pdf = out / f"teacher-{mode}.pdf"
        tab.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    finally:
        b.close()
print("summary, free mm (last block to footer), sheet overflow px, footer-vs-page px, zoom")
for r in rows:
    print(*r, "  <-- FOOTER OVERLAP" if r[1] < 0.6 else "")
d = fitz.open(pdf); print("pdf pages", len(d), "errors", errors)
for n in save:
    d[n - 1].get_pixmap(dpi=80).save(out / f"s{n:02d}-{mode}.png")
