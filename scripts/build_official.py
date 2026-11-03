#!/usr/bin/env python3
"""Lay out eleven source-identical photographed Ministry curriculum pages as portrait A4 booklet pages.

Each scan is checked against its verified Git-blob hash and shown unchanged. A landscape scan
upright on a portrait page would print at 71% of its size, so it is turned a quarter turn (a
lossless pixel rotation: Chromium misplaces images inside CSS-rotated boxes) and printed at 85%,
beside the heading SOURCE_OF_TRUTH requires, turned with it. The portrait page keeps the
booklet's logo footer, and its page number is stamped in the margin when the booklet is merged
(SOURCE_OF_TRUTH §כג.14).
"""
from io import BytesIO
from hashlib import sha1
from pathlib import Path
import tempfile
from PIL import Image
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
import manifest as M

ROOT=M.ROOT
OUTPUT=ROOT/"book"/"official.pdf"
SOURCE=ROOT/"sources"/"ministry"
EXPECTED={
    34:"377b09e09884ed04aa4c99d84939f2716efcdb97",
    35:"efb77cc1256084dd2aa5091eacc0571dfa717eff",
    36:"14d2bcecc484ae36702700ae1981a49756999bb5",
    37:"70ca411667fc2d5efe4f2ad20343eedc30f5e8df",
    38:"a27437f83c1d43dbe3c10e96024f24be1fa5194a",
    48:"c5b86e870f6e89c7ea4602757e6423e76a172eee",
    50:"af7f4b3e92b4935678b4047ffb3e0bed10b5de3b",
    51:"ad5bebbe078981e49236c94f81412ef4491fe311",
    88:"0cf1fa8b687d28c6645df386355d25f08d05e4b4",
    89:"9dcda99f7f171e2e8f381fe4cb925af2eebf0e0f",
    91:"6947bf786be3d0eae082ecbfb87bf016797f30c2",
}

CSS="""@page{size:A4;margin:0}*{box-sizing:border-box}html,body{margin:0;background:#fff}
body{font-family:Arial,"Noto Sans Hebrew",sans-serif;color:#153949}
.sheet{width:210mm;height:297mm;padding-top:20mm;display:flex;flex-direction:column;overflow:hidden;break-after:page;page-break-after:always}
.sheet:last-child{break-after:auto;page-break-after:auto}
.area{flex:1;display:flex;align-items:center;direction:ltr;padding:0 7mm 0 8mm;gap:4mm}
.strip{position:relative;width:13mm;height:252mm;flex:none}
.strip .head{position:absolute;left:50%;top:50%;width:252mm;transform:translate(-50%,-50%) rotate(-90deg);direction:rtl;display:flex;align-items:baseline;gap:14px;border-bottom:2px solid #087971;padding:0 4mm 6px}
.series{color:#087971;font-size:22px;font-weight:900;line-height:1.25}
.sub{color:#5e7480;font-size:13px}
.scan{margin:0;flex:none}
.scan img{display:block;width:178mm;height:auto}
.page-foot{margin:0}"""

def sheet(page,scan,logo):
    return ('<article class="sheet"><div class="area"><div class="strip"><header class="head">'
            f'<div class="series">{M.MINISTRY_HEADING}</div><div class="sub">משרד החינוך · עדכון גאומטריה ז׳ · עמוד {page}</div></header></div>'
            f'<figure class="scan"><img src="{scan}" alt="תוכנית הלימודים בגאומטריה לכיתה ז׳, עמוד {page}"></figure></div>'
            '<footer class="page-foot"><div class="ws-footline" aria-hidden="true"></div><div class="ws-brand">'
            f'<img class="ws-logo" src="{logo}" alt="יחידת מתמטיקה — מחוז ירושלים והעיר ירושלים" width="64" height="64">'
            '<p class="ws-credit"><strong>יחידת המתמטיקה · מחוז ירושלים והעיר ירושלים</strong>'
            '<span>הדרכה במחוז ירושלים והעיר ירושלים - מנח״י, בהובלת איילת קריספין</span></p></div></footer></article>')

def main():
    if set(EXPECTED)!=set(M.MINISTRY_PAGES):
        raise RuntimeError(f"Verified scan hashes cover {sorted(EXPECTED)} but data/manifest.json lists {list(M.MINISTRY_PAGES)}")
    sheets=[]
    temp=tempfile.TemporaryDirectory()
    for n in M.MINISTRY_PAGES:
        src=SOURCE/f"grade7-p{n:03}.webp"
        data=src.read_bytes()
        gitsha=sha1(b"blob "+str(len(data)).encode()+bytes([0])+data).hexdigest()
        if gitsha!=EXPECTED[n]:
            raise RuntimeError(f"Ministry page {n} changed from its original verified source")
        with Image.open(BytesIO(data)) as img:
            if img.width < 1200 or img.height < 800:
                raise RuntimeError(f"Low resolution source page {n}")
            turned=Path(temp.name)/f"grade7-p{n:03}.png"
            img.convert("RGB").transpose(Image.Transpose.ROTATE_90).save(turned)
        sheets.append(sheet(n,turned.as_uri(),(ROOT/"assets"/"logo.png").as_uri()))
    html=('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>שאלות מתוך תוכנית הלימודים</title>'
          f'<link rel="stylesheet" href="{(ROOT/"assets"/"page-foot.css").as_uri()}"><style>{CSS}</style></head><body>'+"".join(sheets)+"</body></html>")
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            tab=browser.new_page(viewport={"width":794,"height":1123})
            errors=[]
            tab.on("pageerror",lambda e:errors.append(str(e)))
            if True:
                page=Path(temp.name)/"official-print.html"
                page.write_text(html,encoding="utf-8")
                tab.goto(page.as_uri(),wait_until="load")
                tab.emulate_media(media="print")
                bad=tab.evaluate("""() => [...document.querySelectorAll('article.sheet')].flatMap((s,i) => {
                  const img=s.querySelector('.scan img'), logo=s.querySelector('.ws-logo'), f=s.querySelector('.page-foot');
                  const e=[];
                  if(!img.complete||img.naturalHeight<1200)e.push([i+1,'scan not loaded']);
                  if(!logo.complete||!logo.naturalWidth)e.push([i+1,'logo not loaded']);
                  if(s.scrollHeight>s.clientHeight+1)e.push([i+1,'overflow']);
                  if(Math.abs(f.getBoundingClientRect().bottom-s.getBoundingClientRect().bottom)>2)e.push([i+1,'footer must close the page']);
                  const r=img.getBoundingClientRect();
                  if(r.bottom>f.getBoundingClientRect().top-4||r.top<s.getBoundingClientRect().top+76)e.push([i+1,'scan outside its panel']);
                  if(r.height<900)e.push([i+1,'scan printed too small',Math.round(r.height)]);
                  return e;})""")
                if bad or errors:
                    raise RuntimeError(f"Ministry pages layout failed: {bad} {errors}")
                tab.pdf(path=str(OUTPUT),format="A4",print_background=True,prefer_css_page_size=True,
                        margin={"top":"0","right":"0","bottom":"0","left":"0"})
            tab.close()
        finally:
            browser.close()
            temp.cleanup()
    pdf=PdfReader(str(OUTPUT))
    if len(pdf.pages)!=len(EXPECTED): raise RuntimeError("Original page count mismatch")
    for i,page in enumerate(pdf.pages):
        if not (588<float(page.mediabox.width)<604 and 834<float(page.mediabox.height)<850):
            raise RuntimeError(f"Ministry page {i+1} is not portrait A4")
    if OUTPUT.stat().st_size<90000:raise RuntimeError("Official PDF unexpectedly small")
    print(f"PASS: {len(EXPECTED)} unchanged ministry source pages, Git-blob hashes verified, portrait A4 pages with logo footer ({OUTPUT.stat().st_size} bytes)")

if __name__=="__main__":main()
