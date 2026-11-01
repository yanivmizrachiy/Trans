#!/usr/bin/env python3
"""Build the genuine complete transformation booklet from verified printed source files."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter
from markdown import markdown

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/"book"
PDF=ROOT/"pdf"
WORKSHEETS_ORIGINAL=(
    ("orig-rectangles","פארק המרצפות"),
    ("orig-conveyor","מכונת המיון"),
    ("orig-mirror-route","מסדרון השערים"),
    ("orig-center-p","מערכת המעקב"),
    ("orig-symbol-turn","שלט הכיוון"),
    ("orig-robot-grid","הרובוט בגינה"),
    ("orig-translation","שליח הקואורדינטות"),
    ("orig-reflection","מוזאון המראות"),
    ("orig-rotation","תחנת הרוח"),
    ("orig-composition","מעבדת סדר הפעולות"),
    ("orig-symmetry","סמל העיר"),
)
WORKSHEETS_ADDITIONAL=(
    ("349","עמוד 349 — חפיפה והזזה"),
    ("350","עמוד 350 — סיבוב"),
    ("351","עמוד 351 — רצף פעולות"),
    ("352","עמוד 352 — סיבוב וסימטרייה"),
    ("385","עמוד 385 — שיקוף ושטח"),
    ("549","עמוד 549 — הזזה במערכת צירים"),
    ("rectangles","חקר מלבנים — עיבוד מן המצגת"),
    ("true-false","נכון / לא נכון — עיבוד מן המצגת"),
    ("triangle","טרנספורמציות משולשים — עיבוד מן המצגת"),
)
CSS = """
@page{size:A4;margin:14mm 14mm 16mm}
*{box-sizing:border-box}
html{direction:rtl}
body{font-family:Arial,"Noto Sans Hebrew",sans-serif;color:#183e4c;font-size:12.5px;line-height:1.65;margin:0}
h1{font-size:24px;color:#0b3546;margin:0 0 16px;border-bottom:2px solid #087970;padding-bottom:8px}
h2{font-size:18px;color:#076b69;margin:17px 0 8px;break-after:avoid}
h3{font-size:15px;color:#164e59;margin:14px 0 7px;break-after:avoid}
p,li{margin-bottom:6px;orphans:3;widows:3}
ol,ul{padding-right:24px}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:11.5px}
td,th{padding:6px 8px;border:1px solid #c9dcdf;text-align:right;vertical-align:top}
th{background:#e7f3f1}
tr{break-inside:avoid}
pre{white-space:pre-wrap;overflow-wrap:anywhere}
code{direction:ltr;unicode-bidi:isolate;display:inline-block;font-size:.94em;background:#f3f7f6;padding:0 3px}
a{color:#006e69;overflow-wrap:anywhere}
blockquote{border-right:3px solid #078276;padding-right:12px;margin-right:0;color:#435e69}
"""
def validate_pdf(path, expected=None):
    path=Path(path)
    if not path.is_file() or path.stat().st_size<3500:
        raise RuntimeError(f"Missing or empty PDF: {path}")
    doc=PdfReader(str(path))
    if expected is not None and len(doc.pages)!=expected:
        raise RuntimeError(f"Unexpected pages in {path}: {len(doc.pages)} rather than {expected}")
    if len(doc.pages)==0:
        raise RuntimeError(f"Zero pages in {path}")
    return len(doc.pages)

def render_markdown(browser, source, target_html, target_pdf, label):
    content=source.read_text(encoding="utf-8")
    if not content.strip().startswith("#"):
        raise RuntimeError(f"Cannot render unstructured {source}")
    html=markdown(content,extensions=["tables","fenced_code","sane_lists"])
    page_html="<html lang='he' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+label+"</title><style>"+CSS+"</style></head><body>"+html+"</body></html>"
    target_html.write_text(page_html,encoding="utf-8")
    tab=browser.new_page(viewport={"width":1100,"height":1500})
    errors=[]
    tab.on("pageerror",lambda e:errors.append(str(e)))
    tab.goto(target_html.as_uri(),wait_until="load")
    tab.emulate_media(media="print")
    tab.pdf(path=str(target_pdf),format="A4",print_background=True,margin={"top":"14mm","right":"14mm","bottom":"16mm","left":"14mm"})
    tab.close()
    if errors:
        raise RuntimeError(f"Browser errors while rendering {label}: {errors}")
    return validate_pdf(target_pdf)

def render_front(browser):
    path=BOOK/"front.html"
    dest=BOOK/"front.pdf"
    tab=browser.new_page(viewport={"width":1250,"height":1700})
    errors=[]
    tab.on("pageerror",lambda e:errors.append(str(e)))
    tab.goto(path.as_uri(),wait_until="load")
    tab.emulate_media(media="print")
    check=tab.evaluate("""() => {
      const pages=Array.from(document.querySelectorAll('section.page'));
      return {count:pages.length,fail:pages.flatMap((p,i)=>{
        const f=p.querySelector('.foot'), b=p.getBoundingClientRect(), z=f.getBoundingClientRect();
        let e=[]; if(p.scrollHeight>p.clientHeight+2)e.push([i+1,'overflow']);
        if(z.bottom>b.bottom-6)e.push([i+1,'footer outside page']);
        return e;
      })};
    }""")
    if check["count"]!=2 or check["fail"] or errors:
        raise RuntimeError(f"Cover layout invalid: {check}, errors: {errors}")
    tab.pdf(path=str(dest),format="A4",print_background=True,prefer_css_page_size=True,margin={"top":"0","right":"0","bottom":"0","left":"0"})
    tab.close()
    return validate_pdf(dest,2)

SADNA_CREDIT="שרית מאירוביץ וסיגלית אטשי"
def render_sadna(browser):
    """Workshop deck pages; every page must credit the deck's editors in its footer."""
    path=BOOK/"sadna.html"
    dest=BOOK/"sadna.pdf"
    tab=browser.new_page(viewport={"width":1250,"height":1700})
    errors=[]
    tab.on("pageerror",lambda e:errors.append(str(e)))
    tab.goto(path.as_uri(),wait_until="load")
    tab.emulate_media(media="print")
    check=tab.evaluate("""(credit) => {
      const pages=Array.from(document.querySelectorAll('article.sheet'));
      return {count:pages.length,fail:pages.flatMap((p,i)=>{
        const f=p.querySelector('.credit'), m=p.querySelector('.content'); let e=[];
        if(!f||!f.textContent.includes(credit))return [[i+1,'missing editors credit']];
        const b=p.getBoundingClientRect(), z=f.getBoundingClientRect();
        if(p.scrollHeight>p.clientHeight+2)e.push([i+1,'overflow']);
        if(m.getBoundingClientRect().bottom>z.top-2)e.push([i+1,'footer overlap']);
        if(z.bottom>b.bottom-6)e.push([i+1,'footer outside page']);
        return e;
      })};
    }""",SADNA_CREDIT)
    if check["count"]!=3 or check["fail"] or errors:
        raise RuntimeError(f"Workshop deck pages invalid: {check}, errors: {errors}")
    tab.pdf(path=str(dest),format="A4",print_background=True,prefer_css_page_size=True,margin={"top":"0","right":"0","bottom":"0","left":"0"})
    tab.close()
    return validate_pdf(dest,3)

def build():
    validate_pdf(BOOK/"teacher.pdf",14)
    validate_pdf(BOOK/"official.pdf",8)
    for ident,_ in WORKSHEETS_ORIGINAL:
        validate_pdf(PDF/(ident+".pdf"),1)
    for ident,_ in WORKSHEETS_ADDITIONAL:
        validate_pdf(PDF/(ident+".pdf"),2 if ident=="triangle" else 1)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            front=render_front(browser)
            sadna=render_sadna(browser)
            workshop=render_markdown(browser,ROOT/"docs"/"PRESENTATION_2026-10-21.md",
                                     BOOK/"workshop.html",BOOK/"workshop.pdf","סיכום מצגת קהילת המורים")
            answers=render_markdown(browser,ROOT/"docs"/"ANSWER_KEY.md",
                                    BOOK/"answers.html",BOOK/"answers.pdf","מפתח תשובות למורה")
        finally:
            browser.close()
    if workshop<1 or answers<2:
        raise RuntimeError(f"Workshop or answers document appears too short: {workshop}, {answers}")
    writer=PdfWriter()
    sections=[]
    def append(path,label,expected=None):
        first=len(writer.pages)+1
        actual=validate_pdf(path,expected)
        writer.append(str(path),outline_item=label,import_outline=False)
        sections.append((label,first,first+actual-1))
    append(BOOK/"front.pdf","שער ותוכן עניינים",2)
    append(BOOK/"teacher.pdf","חלק א׳ — סיכומים למורה",14)
    append(BOOK/"official.pdf","חלק ב׳ — שאלות מתוך תוכנית הלימודים (מקור ללא שינוי)",8)
    for ident,title in WORKSHEETS_ORIGINAL:
        append(PDF/(ident+".pdf"),"חלק ג׳ — "+title,1)
    for ident,title in WORKSHEETS_ADDITIONAL:
        append(PDF/(ident+".pdf"),"חלק ד׳ — "+title,2 if ident=="triangle" else 1)
    append(BOOK/"workshop.pdf","חלק ה׳ — סיכום מצגת ההשתלמות",workshop)
    append(BOOK/"sadna.pdf","חלק ו׳ — סדנה: צורות חופפות וטרנספורמציות (שרית מאירוביץ וסיגלית אטשי)",sadna)
    append(BOOK/"answers.pdf","חלק ז׳ — מפתח תשובות למורה",answers)
    writer.add_metadata({"/Title":"טרנספורמציות — חוברת הוראה מלאה",
                         "/Subject":"חפיפת צורות, הזזה, סיבוב ושיקוף — מקורות, תרגול מקורי ומפתח תשובות",
                         "/Author":"מאגר הוראה במתמטיקה — Trans"})
    dest=BOOK/"transformations-complete.pdf"
    with dest.open("wb") as f:writer.write(f)
    verify=PdfReader(str(dest))
    target_pages=2+14+8+11+10+workshop+sadna+answers
    if len(verify.pages)!=target_pages:
        raise RuntimeError(f"Book missing pages: {len(verify.pages)} expected {target_pages}")
    if len(verify.outline)<8:
        raise RuntimeError("Book PDF does not contain navigation bookmarks")
    if dest.stat().st_size<1_000_000:
        raise RuntimeError("Merged booklet too small for 8 authentic scans and 20 worksheets")
    for name,start,end in sections:print(f"Pages {start:02d}–{end:02d}: {name}")
    print(f"PASS: complete single PDF {len(verify.pages)} pages, {len(sections)} bookmarked sections, {dest.stat().st_size} bytes")

if __name__=="__main__":build()
