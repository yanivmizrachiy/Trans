"""Natural (zoom 1) block heights of one teacher summary and the room it has. Usage: python blocks.py <repo> <summary> [proxy]"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

repo, n, proxy = Path(sys.argv[1]), int(sys.argv[2]), len(sys.argv) > 3
PROXY = open(Path(__file__).with_name("teacher_render.py"), encoding="utf-8").read().split('PROXY = """')[1].split('"""')[0]
JS = """n => { const s=document.getElementById('summary-'+n), m=s.querySelector('.content'), f=s.querySelector('.page-foot');
  m.style.zoom=1; m.querySelectorAll('[data-spread]').forEach(e=>{e.style.paddingTop='';});
  const px=96/25.4, kids=[...m.children].map(k=>{const r=k.getBoundingClientRect(), cs=getComputedStyle(k);
    return [k.tagName+(k.className?'.'+k.className:''), +((r.height+parseFloat(cs.marginTop)+parseFloat(cs.marginBottom))/px).toFixed(1)];});
  const room=(f.getBoundingClientRect().top-12-m.getBoundingClientRect().top)/px;
  return {room:+room.toFixed(1), used:+kids.reduce((a,k)=>a+k[1],0).toFixed(1), kids}; }"""
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    try:
        t = b.new_page(viewport={"width": 1200, "height": 1600})
        t.goto((repo / "book" / "teacher.html").as_uri(), wait_until="load", timeout=60000)
        if proxy:
            t.evaluate(PROXY)
        t.emulate_media(media="print"); t.evaluate("async () => { await document.fonts.ready; }")
        r = t.evaluate(JS, n)
    finally:
        b.close()
print("room mm", r["room"], "used at zoom 1 mm", r["used"], "-> fit zoom about", round(r["room"] / r["used"], 2))
for k in r["kids"]:
    print("  ", *k)
