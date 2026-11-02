#!/usr/bin/env python3
"""Build the genuine complete transformation booklet from verified printed source files."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter
from markdown import markdown
from urllib.parse import unquote, urlsplit, urljoin
import re
import tempfile
import manifest as M

ROOT=M.ROOT
BOOK=ROOT/"book"
PDF=ROOT/"pdf"
# Worksheet order, titles and page counts come from data/manifest.json.
WORKSHEETS_ORIGINAL=tuple((i,M.TITLES[i]) for i in M.ORIGINAL)
WORKSHEETS_ADDITIONAL=tuple((i,M.TITLES[i]) for i in M.IMPORTED)
PAGES=M.WORKSHEET_PAGES
PART=M.PARTS
def part_title(key):
    part=PART[key][0]
    return f"חלק {part['part']} — {part['label']}"
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

# Markdown guides in docs/ link to each other by their source file names.
# Inside book/ the same documents exist only as rendered HTML, so every
# cross-reference must be rewritten to the rendered neighbour or the link
# breaks on the public site (book/ANSWER_KEY.md never existed).
RENDERED_DOCS={"ANSWER_KEY.md":"answers.html","PRESENTATION_2026-10-21.md":"workshop.html"}
HREF=re.compile(r'href="([^"]*)"')

def rewrite_book_links(html, target_html):
    def swap(match):
        link=match.group(1)
        url=urlsplit(link)
        if url.scheme or url.netloc or not url.path:
            return match.group(0)
        name=Path(unquote(url.path)).name
        if name in RENDERED_DOCS:
            return 'href="./'+RENDERED_DOCS[name]+('#'+url.fragment if url.fragment else '')+'"'
        return match.group(0)
    html=HREF.sub(swap,html)
    for match in HREF.finditer(html):
        url=urlsplit(match.group(1))
        if url.scheme or url.netloc or not url.path:
            continue
        target=(target_html.parent/unquote(url.path)).resolve()
        if not target.is_file():
            raise RuntimeError(f"{target_html.name}: relative link to missing file {match.group(1)}")
    return html

def is_relative(link):
    url=urlsplit(link)
    return not url.scheme and not url.netloc and bool(url.path)

def absolute_links(html, base_url):
    """Resolve every relative href against the page's public URL.

    Used only for the copy that is printed to PDF: Chromium otherwise stores
    relative links as file:// URIs of the build machine, which are dead in the
    published booklet. The served HTML keeps its relative links."""
    return HREF.sub(lambda m: m.group(0) if not is_relative(m.group(1)) else 'href="'+urljoin(base_url,m.group(1))+'"', html)

def pdf_link_uris(path):
    uris=[]
    for page in PdfReader(str(path)).pages:
        for annot in page.get("/Annots") or []:
            action=annot.get_object().get("/A")
            if action is not None and action.get("/URI"):
                uris.append(str(action["/URI"]))
    return uris

def check_pdf_links(target_pdf, page_html, base_url):
    expected={urljoin(base_url,link) for link in HREF.findall(page_html) if is_relative(link)}
    uris=set(pdf_link_uris(target_pdf))
    dead=sorted(u for u in uris if not u.startswith(("https://","http://","mailto:")))
    if dead:
        raise RuntimeError(f"{target_pdf.name}: links that only work on the build machine: {dead}")
    missing=sorted(expected-uris)
    if missing:
        raise RuntimeError(f"{target_pdf.name}: relative links were not published as absolute URLs: {missing}")

def render_markdown(browser, source, target_html, target_pdf, label):
    content=source.read_text(encoding="utf-8")
    if not content.strip().startswith("#"):
        raise RuntimeError(f"Cannot render unstructured {source}")
    html=rewrite_book_links(markdown(content,extensions=["tables","fenced_code","sane_lists"]),target_html)
    page_html="<html lang='he' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+label+"</title><style>"+CSS+"</style></head><body>"+html+"</body></html>"
    target_html.write_text(page_html,encoding="utf-8",newline="\n")
    public_url=M.BASE_URL.rstrip("/")+"/book/"+target_html.name
    tab=browser.new_page(viewport={"width":1100,"height":1500})
    errors=[]
    tab.on("pageerror",lambda e:errors.append(str(e)))
    with tempfile.TemporaryDirectory() as temp:
        print_html=Path(temp)/target_html.name
        print_html.write_text(absolute_links(page_html,public_url),encoding="utf-8",newline="\n")
        tab.goto(print_html.as_uri(),wait_until="load")
        tab.emulate_media(media="print")
        tab.pdf(path=str(target_pdf),format="A4",print_background=True,margin={"top":"14mm","right":"14mm","bottom":"16mm","left":"14mm"})
    tab.close()
    if errors:
        raise RuntimeError(f"Browser errors while rendering {label}: {errors}")
    check_pdf_links(target_pdf,page_html,public_url)
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

SADNA_CREDIT=M.SADNA_CREDIT
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
    if check["count"]!=M.part_pages(PART["sadna"][0]) or check["fail"] or errors:
        raise RuntimeError(f"Workshop deck pages invalid: {check}, errors: {errors}")
    tab.pdf(path=str(dest),format="A4",print_background=True,prefer_css_page_size=True,margin={"top":"0","right":"0","bottom":"0","left":"0"})
    tab.close()
    return validate_pdf(dest,M.part_pages(PART["sadna"][0]))

def build():
    validate_pdf(BOOK/"teacher.pdf",M.part_pages(PART["teacher"][0]))
    validate_pdf(BOOK/"official.pdf",M.part_pages(PART["official"][0]))
    for ident,_ in WORKSHEETS_ORIGINAL+WORKSHEETS_ADDITIONAL:
        validate_pdf(PDF/(ident+".pdf"),PAGES[ident])
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
    append(BOOK/"front.pdf",PART["front"][0]["label"],M.part_pages(PART["front"][0]))
    append(BOOK/"teacher.pdf",part_title("teacher"),M.part_pages(PART["teacher"][0]))
    append(BOOK/"official.pdf",part_title("official"),M.part_pages(PART["official"][0]))
    for ident,title in WORKSHEETS_ORIGINAL:
        append(PDF/(ident+".pdf"),f"חלק {PART['original'][0]['part']} — "+title,PAGES[ident])
    for ident,title in WORKSHEETS_ADDITIONAL:
        append(PDF/(ident+".pdf"),f"חלק {PART['imported'][0]['part']} — "+title,PAGES[ident])
    append(BOOK/"workshop.pdf",part_title("workshop"),workshop)
    append(BOOK/"sadna.pdf",part_title("sadna"),sadna)
    append(BOOK/"answers.pdf",part_title("answers"),answers)
    writer.add_metadata({"/Title":"טרנספורמציות — חוברת הוראה מלאה",
                         "/Subject":"חפיפת צורות, הזזה, סיבוב ושיקוף — מקורות, תרגול מקורי ומפתח תשובות",
                         "/Author":"מאגר הוראה במתמטיקה — Trans"})
    dest=BOOK/"transformations-complete.pdf"
    with dest.open("wb") as f:writer.write(f)
    verify=PdfReader(str(dest))
    target_pages=M.TOTAL_PAGES
    if len(verify.pages)!=target_pages:
        raise RuntimeError(f"Book missing pages: {len(verify.pages)} expected {target_pages} (data/manifest.json)")
    if len(verify.outline)!=M.TOTAL_BOOKMARKS:
        raise RuntimeError(f"Book PDF has {len(verify.outline)} bookmarks, manifest derives {M.TOTAL_BOOKMARKS}")
    # Every file-backed part must start and end exactly where the manifest layout says.
    spans={label:(start,end) for label,start,end in sections}
    for part,first,last in M.layout():
        if "file" not in part: continue
        label=part["label"] if part["key"]=="front" else part_title(part["key"])
        if spans.get(label)!=(first,last):
            raise RuntimeError(f"Part {part['key']} occupies {spans.get(label)} but data/manifest.json derives {(first,last)}")
    if dest.stat().st_size<1_000_000:
        raise RuntimeError("Merged booklet too small for the manifest scans and worksheets")
    for name,start,end in sections:print(f"Pages {start:02d}–{end:02d}: {name}")
    print(f"PASS: complete single PDF {len(verify.pages)} pages, {len(sections)} bookmarked sections, {dest.stat().st_size} bytes")

if __name__=="__main__":build()
