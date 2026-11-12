#!/usr/bin/env python3
"""Build the complete transformation booklet from verified printed source files.

The booklet follows the reading sequence of data/manifest.json (book.chapters);
book/complete.html shows this PDF itself. Pages are taken one by one from the
already verified part PDFs (teacher summaries, video summary, teacher lab,
workshop, worksheets, curriculum pages and answer key), so each part keeps its
own layout and only its place in the merged booklet is decided here.
"""
from io import BytesIO
import fitz
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter
from markdown import markdown
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from urllib.parse import unquote, urlsplit, urljoin
import hashlib
import re
import tempfile
import manifest as M
import answer_key_page

ROOT=M.ROOT
BOOK=ROOT/"book"
PDF=ROOT/"pdf"
PAGES=M.WORKSHEET_PAGES
CSS = """
*{box-sizing:border-box}
html{direction:rtl}
body{font-family:Arial,"Noto Sans Hebrew",sans-serif;color:#10202e;font-size:12.5px;line-height:1.65;margin:0}
body>h1{display:none}
h2{font-size:16px;font-weight:800;color:#0b3a75;margin:14px 0 6px;padding-bottom:3px;border-bottom:1px solid #c9d6e2;break-after:avoid}
h3{font-size:15px;color:#0b3a75;margin:14px 0 7px;break-after:avoid}
p,li{margin-bottom:6px;orphans:3;widows:3}
ol,ul{padding-right:24px}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:11.5px}
td,th{padding:6px 8px;border:1px solid #cfdbe6;text-align:right;vertical-align:top}
th{background:#eef3f9;color:#0b3a75}
tr{break-inside:avoid}
pre{white-space:pre-wrap;overflow-wrap:anywhere}
code{direction:ltr;unicode-bidi:isolate;display:inline-block;font-family:inherit;font-size:.94em;background:#eef3f9;padding:0 3px}
a{color:#0b3a75;overflow-wrap:anywhere}
blockquote{border-right:3px solid #0b3a75;padding-right:12px;margin-right:0;color:#536f79}
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
RENDERED_DOCS={"ANSWER_KEY.md":"answers.html","TEACHER_WORKSHOP.md":"workshop.html"}
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

# Flowing teacher texts: the top margin holds the booklet's header and the bottom margin its
# logo footer; both are laid over every page.
MD_MARGIN={"top":"25mm","right":"15mm","bottom":"27mm","left":"15mm"}
SERIES="טרנספורמציות - סיכומים למורה"
FOOT_OVERLAY=None
def foot_overlay(browser):
    """One transparent A4 page holding only the shared footer, to lay over flowing pages."""
    global FOOT_OVERLAY
    if FOOT_OVERLAY is None:
        logo=(ROOT/"assets"/"logo.png").as_uri()
        html=("<!doctype html><html lang='he' dir='rtl'><head><meta charset='utf-8'>"
              f"<link rel='stylesheet' href='{(ROOT/'assets'/'page-foot.css').as_uri()}'>"
              "<style>@page{size:A4;margin:0}html,body{margin:0;background:transparent}"
              "body{font-family:Arial,'Noto Sans Hebrew',sans-serif}.page-foot{position:fixed;left:0;right:0;bottom:0}"
              ".page-foot .ws-footline{height:0;background:none;border-top:2px solid #14296e}</style></head><body>"
              "<footer class='page-foot'><div class='ws-footline'></div><div class='ws-brand'>"
              f"<img class='ws-logo' src='{logo}' alt='' width='64' height='64'><p class='ws-credit'>"
              f"<strong>{M.FOOTER_CREDIT}</strong><span>{M.FOOTER_DISTRICT}</span></p></div></footer></body></html>")
        tab=browser.new_page()
        with tempfile.TemporaryDirectory() as temp:
            page=Path(temp)/"foot.html"
            page.write_text(html,encoding="utf-8")
            tab.goto(page.as_uri(),wait_until="load")
            if not tab.evaluate("() => document.querySelector('img').naturalWidth > 0"):
                raise RuntimeError("Footer logo did not load")
            data=tab.pdf(format="A4",print_background=False,prefer_css_page_size=True,margin={"top":"0","right":"0","bottom":"0","left":"0"})
        tab.close()
        FOOT_OVERLAY=PdfReader(BytesIO(data)).pages[0]
    return FOOT_OVERLAY

def head_overlay(browser, title):
    """One transparent A4 page holding only the booklet's header, to lay over flowing pages."""
    html=("<!doctype html><html lang='he' dir='rtl'><head><meta charset='utf-8'>"
          f"<link rel='stylesheet' href='{(ROOT/'assets'/'book.css').as_uri()}'>"
          "<style>@page{size:A4;margin:0}html,body{margin:0;background:transparent}"
          "body{font-family:Arial,'Noto Sans Hebrew',sans-serif;padding:8mm 15mm 0}</style></head><body>"
          f"<header class='head'><div><h1>{title}</h1><p class='series'>{SERIES}</p></div></header></body></html>")
    tab=browser.new_page()
    with tempfile.TemporaryDirectory() as temp:
        page=Path(temp)/"head.html"
        page.write_text(html,encoding="utf-8")
        tab.goto(page.as_uri(),wait_until="load")
        data=tab.pdf(format="A4",print_background=False,prefer_css_page_size=True,margin={"top":"0","right":"0","bottom":"0","left":"0"})
    tab.close()
    return PdfReader(BytesIO(data)).pages[0]

# Keeps the Markdown pages at the size of the rest of the book: 12.5 px x 1.08 = 13.5 px.
MAX_DOC_ZOOM=1.08

def render_markdown(browser, source, target_html, target_pdf, label, pages, to_html=None, style=CSS, head="", fonts=()):
    """Render a Markdown text onto exactly `pages` A4 pages, at the largest zoom up to MAX_DOC_ZOOM that fits,
    so the pages are filled rather than left half empty. (CSS zoom lays the right-to-left text
    out again; Chromium's print scale would cut it off at the right edge.) `to_html` replaces the
    plain Markdown conversion with a dedicated layout; `fonts` are web fonts that must load."""
    content=source.read_text(encoding="utf-8")
    if not content.strip().startswith("#"):
        raise RuntimeError(f"Cannot render unstructured {source}")
    body=to_html(content) if to_html else markdown(content,extensions=["tables","fenced_code","sane_lists"])
    html=rewrite_book_links(body,target_html)
    page_html="<html lang='he' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+label+"</title>"+head+"<style>@page{size:A4}"+style+"</style></head><body>"+html+"</body></html>"
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
        if fonts:
            missing=tab.evaluate("""async (families) => {
              await document.fonts.ready;
              const loaded=new Set([...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family.replace(/["']/g,'')));
              return families.filter(f=>!loaded.has(f));
            }""",list(fonts))
            if missing:
                raise RuntimeError(f"{label}: web fonts did not load: {missing}")
        def fits(z):
            tab.evaluate("z => { document.body.style.zoom = z; }",z)
            data=tab.pdf(format="A4",print_background=True,prefer_css_page_size=True,margin=MD_MARGIN)
            return data if len(PdfReader(BytesIO(data)).pages)<=pages else None
        fitted=None
        for step in range(19):
            scale=round(MAX_DOC_ZOOM-0.025*step,3)
            fitted=fits(scale)
            if fitted:
                break
        if fitted is None:
            raise RuntimeError(f"{label} does not fit on {pages} A4 pages even at scale 0.85")
        # then in finer steps up to the next coarse step, so the last page is filled too
        for fine in (0.02,0.015,0.01,0.005):
            bigger=round(scale+fine,3)
            if bigger<=MAX_DOC_ZOOM:
                data=fits(bigger)
                if data:
                    fitted,scale=data,bigger
                    break
    tab.close()
    writer=PdfWriter(clone_from=PdfReader(BytesIO(fitted)))
    head=head_overlay(browser,label)
    for page in writer.pages:
        page.merge_page(foot_overlay(browser))
        page.merge_page(head)
    with target_pdf.open("wb") as f:
        writer.write(f)
    print(f"{target_pdf.name}: zoom {scale}")
    if errors:
        raise RuntimeError(f"Browser errors while rendering {label}: {errors}")
    check_pdf_links(target_pdf,page_html,public_url)
    return validate_pdf(target_pdf)

def render_sadna(browser):
    """Three independent, originally authored teacher investigations."""
    path=BOOK/"sadna.html"
    dest=BOOK/"sadna.pdf"
    expected=M.component_pages("sadna")
    tab=browser.new_page(viewport={"width":1250,"height":1700})
    errors=[]
    tab.on("pageerror",lambda e:errors.append(str(e)))
    tab.goto(path.as_uri(),wait_until="load")
    tab.emulate_media(media="print")
    tab.evaluate("() => window.fitSheets && window.fitSheets()")
    check=tab.evaluate("""(credit) => {
      const pages=Array.from(document.querySelectorAll('article.sheet'));
      return {count:pages.length,fail:pages.flatMap((p,i)=>{
        const f=p.querySelector('.credit'), m=p.querySelector('.content'); let e=[];
        if(!f||!f.textContent.includes(credit))return [[i+1,'missing original lesson credit']];
        const logo=f.querySelector('img.ws-logo');
        if(!logo||!logo.complete||!logo.naturalWidth)e.push([i+1,'footer logo missing']);
        const b=p.getBoundingClientRect(), z=f.getBoundingClientRect();
        if(p.scrollHeight>p.clientHeight+2)e.push([i+1,'overflow']);
        if(m.getBoundingClientRect().bottom>z.top-2)e.push([i+1,'footer overlap']);
        if(Math.abs(z.bottom-b.bottom)>2)e.push([i+1,'footer must close the page']);
        return e;
      })};
    }""",M.FOOTER_CREDIT)
    if check["count"]!=expected or check["fail"] or errors:
        raise RuntimeError(f"Original teacher-lab pages invalid: {check}, errors: {errors}")
    tab.pdf(path=str(dest),format="A4",print_background=True,prefer_css_page_size=True,margin={"top":"0","right":"0","bottom":"0","left":"0"})
    tab.close()
    return validate_pdf(dest,expected)

def render_video(browser):
    """A4 teacher pages summarising the watched transformations video."""
    path=BOOK/"krispin-video.html"
    dest=BOOK/"krispin-video.pdf"
    expected=M.component_pages("krispin-video")
    tab=browser.new_page(viewport={"width":1250,"height":1700})
    errors=[]
    tab.on("pageerror",lambda e:errors.append(str(e)))
    tab.goto(path.as_uri(),wait_until="load")
    tab.emulate_media(media="print")
    check=tab.evaluate("""() => {
      const pages=Array.from(document.querySelectorAll('article.sheet'));
      return {count:pages.length,fail:pages.flatMap((p,i)=>{
        const f=p.querySelector('.source'), m=p.querySelector('.content'); let e=[];
        if(!f||!f.textContent.includes('איילת קריספין'))return [[i+1,'missing video source credit']];
        const b=p.getBoundingClientRect(), z=f.getBoundingClientRect();
        if(p.scrollHeight>p.clientHeight+2)e.push([i+1,'overflow']);
        if(m.getBoundingClientRect().bottom>z.top-2)e.push([i+1,'footer overlap']);
        if(z.bottom>b.bottom+1)e.push([i+1,'footer outside page']);
        return e;
      })};
    }""")
    if check["count"]!=expected or check["fail"] or errors:
        raise RuntimeError(f"Video summary pages invalid: {check}, errors: {errors}")
    tab.pdf(path=str(dest),format="A4",print_background=True,prefer_css_page_size=True,margin={"top":"0","right":"0","bottom":"0","left":"0"})
    tab.close()
    return validate_pdf(dest,expected)

# The page number: white on a solid dark-blue (#0b3a75) disc. The disc's left
# edge sits on the 14 mm text margin and its centre is 12 mm below the top edge, inside every
# printer's printable area. FOLIO_ZONE (mm from
# the top-left corner) is the disc plus 1.5 mm, and must be blank on every page before it is stamped.
FOLIO_X,FOLIO_Y,FOLIO_R=17.9,12.0,3.9
FOLIO_ZONE=(FOLIO_X-FOLIO_R-1.5,FOLIO_Y-FOLIO_R-1.5,FOLIO_X+FOLIO_R+1.5,FOLIO_Y+FOLIO_R+1.5)

def folio_clear(path,index,cache={}):
    """True when nothing is printed where the page number goes."""
    if path not in cache:
        cache[path]=fitz.open(str(path))
    pt=72/25.4
    x0,y0,x1,y1=FOLIO_ZONE
    pix=cache[path][index].get_pixmap(clip=fitz.Rect(x0*pt,y0*pt,x1*pt,y1*pt),dpi=150,alpha=False)
    return min(pix.samples)>=235

def number_stamps(numbers):
    """A PDF with one portrait A4 page per requested number: the booklet's only page
    number, white on a solid dark-blue disc in the top-left corner."""
    buffer=BytesIO()
    canvas=Canvas(buffer,pagesize=A4)
    width,height=A4
    x,y=FOLIO_X*mm,height-FOLIO_Y*mm
    for n in numbers:
        canvas.setFillColorRGB(11/255,58/255,117/255)
        canvas.circle(x,y,FOLIO_R*mm,stroke=0,fill=1)
        canvas.setFillColorRGB(1,1,1)
        canvas.setFont("Helvetica-Bold",10)
        canvas.drawCentredString(x,y-3.5,str(n))
        canvas.showPage()
    canvas.save()
    buffer.seek(0)
    return PdfReader(buffer)

# The booklet is read on phones: a regression in deduplication must stop the build.
MAX_BOOK_BYTES=6_000_000

def check_packed(path):
    """Fail when the published booklet stores one image twice or grows past MAX_BOOK_BYTES."""
    seen={}
    with fitz.open(str(path)) as doc:
        for xref in range(1,doc.xref_length()):
            if doc.xref_is_stream(xref) and doc.xref_get_key(xref,"Subtype")[1]=="/Image":
                digest=hashlib.sha256(doc.xref_stream_raw(xref)).hexdigest()
                if digest in seen:
                    raise RuntimeError(f"{path.name}: image objects {seen[digest]} and {xref} are identical copies")
                seen[digest]=xref
    size=path.stat().st_size
    if size>MAX_BOOK_BYTES:
        raise RuntimeError(f"{path.name} is {size} bytes, more than {MAX_BOOK_BYTES}")

def build():
    M.validate()
    validate_pdf(BOOK/"teacher.pdf",M.component_pages("teacher"))
    validate_pdf(BOOK/"official.pdf",M.component_pages("official"))
    for ident in M.WORKSHEETS:
        validate_pdf(PDF/(ident+".pdf"),PAGES[ident])
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            render_sadna(browser)
            render_video(browser)
            workshop=render_markdown(browser,ROOT/M.COMPONENTS["workshop"]["source"],
                                     BOOK/"workshop.html",BOOK/"workshop.pdf",M.COMPONENTS["workshop"]["label"],
                                     M.component_pages("workshop"))
            answers=render_markdown(browser,ROOT/M.COMPONENTS["answers"]["source"],
                                    BOOK/"answers.html",BOOK/"answers.pdf","מפתח תשובות למורה",
                                    M.component_pages("answers"),to_html=answer_key_page.page_body,
                                    style=answer_key_page.STYLE,head=answer_key_page.HEAD,fonts=answer_key_page.FONTS)
        finally:
            browser.close()
    for key,count in (("workshop",workshop),("answers",answers)):
        if count!=M.component_pages(key):
            raise RuntimeError(f"book/{key}.pdf rendered {count} pages but data/manifest.json says {M.component_pages(key)}")
    summaries=M.summary_titles()
    readers={}
    def reader(path):
        if path not in readers:
            readers[path]=PdfReader(str(path))
        return readers[path]
    writer=PdfWriter()
    placed=[]            # (page_number, item) for every placed page
    for chapter,first,last in M.layout():
        chapter_first=len(writer.pages)
        item_first={}
        for item in chapter["items"]:
            rel,indices=M.item_source(item)
            path=ROOT/rel
            item_first[tuple(item)]=len(writer.pages)
            for index in indices:
                page=reader(path).pages[index]
                box=page.mediabox
                if float(box.width)>float(box.height):
                    raise RuntimeError(f"{path.name}#{index+1} ({item}) is not a portrait A4 page")
                if not folio_clear(path,index):
                    raise RuntimeError(f"{path.name}#{index+1} ({item}) prints where the page number goes {FOLIO_ZONE} mm")
                writer.add_page(page)
                placed.append((len(writer.pages),list(item)))
        if (chapter_first+1,len(writer.pages))!=(first,last):
            raise RuntimeError(f"Chapter {chapter['key']} occupies {(chapter_first+1,len(writer.pages))}, manifest derives {(first,last)}")
        parent=writer.add_outline_item(chapter["label"],chapter_first)
        for item in M.item_bookmarks(chapter):
            writer.add_outline_item(M.item_title(item,summaries),item_first[tuple(item)],parent=parent)
    # One running page number on every page, the Ministry pages included: it sits in the
    # page margin, outside the unchanged scan, and the pages carry no numbers of their own.
    numbered=[n for n,item in placed]
    stamps=number_stamps(numbered)
    for k,n in enumerate(numbered):
        writer.pages[n-1].merge_page(stamps.pages[k])
    writer.add_metadata({"/Title":"טרנספורמציות — חוברת הוראה מלאה",
                         "/Subject":"חפיפת צורות, הזזה, סיבוב ושיקוף — סיכומים למורה, דפי עבודה, שאלות מתוך תוכנית הלימודים ומפתח תשובות",
                         "/Author":"מאגר הוראה במתמטיקה — Trans"})
    dest=ROOT/M.BOOK_FILE
    merged=BytesIO()
    writer.write(merged)
    # Every part PDF embeds its own copy of the footer logo and fonts. MuPDF merges identical
    # objects (garbage=4) and packs the rest into object streams; pypdf's own deduplication
    # left 26 copies of the logo in CI builds and doubled the download.
    with fitz.open(stream=merged.getvalue(),filetype="pdf") as packed:
        packed.save(str(dest),garbage=4,deflate=True,use_objstms=1)
    check_packed(dest)
    verify=PdfReader(str(dest))
    if len(verify.pages)!=M.TOTAL_PAGES:
        raise RuntimeError(f"Book missing pages: {len(verify.pages)} expected {M.TOTAL_PAGES} (data/manifest.json)")
    bookmarks=list(M.flatten(verify.outline))
    actual=[(b.title,verify.get_destination_page_number(b)+1) for b in bookmarks]
    if actual!=M.bookmarks():
        raise RuntimeError(f"Bookmarks (titles, order or target pages) differ from the manifest sequence: {actual}")
    expected_map=[(n,item) for n,_,item,_ in M.page_map()]
    if placed!=expected_map:
        raise RuntimeError("Placed pages differ from manifest page map")
    if dest.stat().st_size<1_000_000:
        raise RuntimeError("Merged booklet too small for the manifest scans and worksheets")
    for chapter,first,last in M.layout():
        print(f"Pages {first:02d}–{last:02d}: {chapter['label']}")
    print(f"PASS: complete single PDF {len(verify.pages)} pages, {len(M.CHAPTERS)} chapters, {len(bookmarks)} bookmarks, "
          f"{len(numbered)} numbered pages, {dest.stat().st_size} bytes")

if __name__=="__main__":build()
