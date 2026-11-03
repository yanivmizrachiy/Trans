"""Print book/krispin-video.html like build_complete.render_video and save PNGs.
Usage: python video_render.py <repo> <outdir> local|proxy [pages...]
proxy: Arimo stands in for the runner's Liberation Sans (Hebrew about 6% wider than Windows Arial)."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import fitz

repo, out, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
pages = [int(a) for a in sys.argv[4:]] or [1, 5, 6, 7]
out.mkdir(parents=True, exist_ok=True)
PROXY = """() => new Promise(res => {
  const l=document.createElement('link'); l.rel='stylesheet';
  l.href='https://fonts.googleapis.com/css2?family=Arimo:ital,wght@0,400;0,500;0,700;1,400;1,700&display=block';
  l.onload=()=>{ const s=document.createElement('style'); s.textContent='*{font-family:Arimo,sans-serif!important}';
    document.head.appendChild(s); document.fonts.load('700 15px Arimo','אבג').then(()=>document.fonts.load('400 15px Arimo','אבג')).then(res); };
  document.head.appendChild(l); })"""
CHECK = """() => {
  const pages=Array.from(document.querySelectorAll('article.sheet'));
  return {count:pages.length,fail:pages.flatMap((p,i)=>{
    const f=p.querySelector('.source'), m=p.querySelector('.content'); let e=[];
    const b=p.getBoundingClientRect(), z=f.getBoundingClientRect();
    if(p.scrollHeight>p.clientHeight+2)e.push([i+1,'overflow',p.scrollHeight-p.clientHeight]);
    if(m.getBoundingClientRect().bottom>z.top-2)e.push([i+1,'footer overlap']);
    if(z.bottom>b.bottom+1)e.push([i+1,'footer outside page']);
    return e;
  }), slack:pages.map(p=>{const m=p.querySelector('.content'); const kids=[...m.children];
    const used=kids.reduce((s,k)=>{const r=k.getBoundingClientRect(); const cs=getComputedStyle(k); return s+r.height+parseFloat(cs.marginTop)+parseFloat(cs.marginBottom);},0);
    return Math.round(m.getBoundingClientRect().height-used);})};
}"""
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    try:
        tab = b.new_page(viewport={"width": 1250, "height": 1700})
        tab.on("pageerror", lambda e: errors.append(str(e)))
        tab.goto((repo / "book" / "krispin-video.html").as_uri(), wait_until="load", timeout=60000)
        if mode == "proxy":
            tab.evaluate(PROXY)
        tab.emulate_media(media="print")
        tab.evaluate("async () => { await document.fonts.ready; }")
        res = tab.evaluate(CHECK)
        tab.pdf(path=str(out / f"video-{mode}.pdf"), format="A4", print_background=True, prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    finally:
        b.close()
d = fitz.open(out / f"video-{mode}.pdf")
for n in pages:
    d[n - 1].get_pixmap(dpi=110).save(out / f"v{mode}-{n:02d}.png")
print(mode, "pdf pages", len(d), "articles", res["count"], "fail", res["fail"], "free px per page", res["slack"], "errors", errors)
