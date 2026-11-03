#!/usr/bin/env python3
"""Build the complete transformation booklet from verified printed source files.

The booklet follows the reading sequence of data/manifest.json (book.chapters):
one continuous order by mathematical topic, identical to book/complete.html.
Pages are taken one by one from the already verified part PDFs (teacher
summaries, Ministry scans, worksheets, teacher lab, workshop and answer key),
so the public part files stay exactly what they are and only their order in
the merged booklet is decided here.
"""
from io import BytesIO
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter
from markdown import markdown
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from urllib.parse import unquote, urlsplit, urljoin
import re
import tempfile
import manifest as M

ROOT=M.ROOT
BOOK=ROOT/"book"
PDF=ROOT/"pdf"
PAGES=M.WORKSHEET_PAGES
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

SADNA_CREDIT=M.SADNA_CREDIT
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
    check=tab.evaluate("""(credit) => {
      const pages=Array.from(document.querySelectorAll('article.sheet'));
      return {count:pages.length,fail:pages.flatMap((p,i)=>{
        const f=p.querySelector('.credit'), m=p.querySelector('.content'); let e=[];
        if(!f||!f.textContent.includes(credit))return [[i+1,'missing original lesson credit']];
        const b=p.getBoundingClientRect(), z=f.getBoundingClientRect();
        if(p.scrollHeight>p.clientHeight+2)e.push([i+1,'overflow']);
        if(m.getBoundingClientRect().bottom>z.top-2)e.push([i+1,'footer overlap']);
        if(z.bottom>b.bottom-6)e.push([i+1,'footer outside page']);
        return e;
      })};
    }""",SADNA_CREDIT)
    if check["count"]!=expected or check["fail"] or errors:
        raise RuntimeError(f"Original teacher-lab pages invalid: {check}, errors: {errors}")
    tab.pdf(path=str(dest),format="A4",print_background=True,prefer_css_page_size=True,margin={"top":"0","right":"0","bottom":"0","left":"0"})
    tab.close()
    return validate_pdf(dest,expected)

def render_video(browser):
    """Six A4 teacher pages summarising the watched transformations video."""
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

def source_pages(item):
    """(pdf path, zero-based page indices) that one sequence item takes from a part PDF."""
    kind,ident=item
    if kind=="s":
        return BOOK/"teacher.pdf",[ident-1]
    if kind=="m":
        return BOOK/"official.pdf",[M.MINISTRY_PAGES.index(ident)]
    if kind=="w":
        return PDF/f"{ident}.pdf",list(range(PAGES[ident]))
    return ROOT/M.COMPONENTS[ident]["file"],list(range(M.component_pages(ident)))

def number_stamps(numbers):
    """A PDF with one portrait A4 page per requested number: the booklet's only page
    number, in the top-left corner inside a thin dark-blue circle (SOURCE_OF_TRUTH §כג.9, §כג.10).
    The Ministry scans are never stamped."""
    buffer=BytesIO()
    canvas=Canvas(buffer,pagesize=A4)
    width,height=A4
    x,y=14*mm,height-6*mm
    for n in numbers:
        canvas.setStrokeColorRGB(11/255,42/255,74/255)
        canvas.setFillColorRGB(1,1,1)
        canvas.setLineWidth(0.9)
        canvas.circle(x,y,3.7*mm,stroke=1,fill=1)
        canvas.setFillColorRGB(11/255,42/255,74/255)
        canvas.setFont("Helvetica-Bold",9.5)
        canvas.drawCentredString(x,y-3.3,str(n))
        canvas.showPage()
    canvas.save()
    buffer.seek(0)
    return PdfReader(buffer)

def flatten(outline):
    for item in outline:
        if isinstance(item,list):
            yield from flatten(item)
        else:
            yield item

def build():
    M.validate()
    import sync_book_docs
    stale=sync_book_docs.check()
    if stale:
        raise RuntimeError("Derived booklet blocks are stale: "+", ".join(stale)+" (run python scripts/sync_book_docs.py --write)")
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
                                     BOOK/"workshop.html",BOOK/"workshop.pdf",M.COMPONENTS["workshop"]["label"])
            answers=render_markdown(browser,ROOT/M.COMPONENTS["answers"]["source"],
                                    BOOK/"answers.html",BOOK/"answers.pdf","מפתח תשובות למורה")
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
            path,indices=source_pages(item)
            item_first[tuple(item)]=len(writer.pages)
            for index in indices:
                page=reader(path).pages[index]
                box=page.mediabox
                landscape=float(box.width)>float(box.height)
                if landscape!=(item[0]=="m"):
                    raise RuntimeError(f"Page orientation of {path.name}#{index+1} does not fit item {item}")
                writer.add_page(page)
                placed.append((len(writer.pages),list(item)))
        if (chapter_first+1,len(writer.pages))!=(first,last):
            raise RuntimeError(f"Chapter {chapter['key']} occupies {(chapter_first+1,len(writer.pages))}, manifest derives {(first,last)}")
        parent=writer.add_outline_item(M.chapter_title(chapter),chapter_first)
        for item in M.item_bookmarks(chapter):
            writer.add_outline_item(M.item_title(item,summaries),item_first[tuple(item)],parent=parent)
    # One running page number at the top of every portrait page; the pages carry no
    # numbers of their own and the Ministry scans stay untouched.
    numbered=[n for n,item in placed if item[0]!="m"]
    stamps=number_stamps(numbered)
    for k,n in enumerate(numbered):
        writer.pages[n-1].merge_page(stamps.pages[k])
    writer.add_metadata({"/Title":"טרנספורמציות — חוברת הוראה מלאה",
                         "/Subject":"חפיפת צורות, הזזה, סיבוב ושיקוף — סיכומים למורה, שאלות מתוך תוכנית הלימודים, דפי עבודה ומפתח תשובות, לפי נושא",
                         "/Author":"מאגר הוראה במתמטיקה — Trans"})
    dest=ROOT/M.BOOK_FILE
    with dest.open("wb") as f:writer.write(f)
    verify=PdfReader(str(dest))
    if len(verify.pages)!=M.TOTAL_PAGES:
        raise RuntimeError(f"Book missing pages: {len(verify.pages)} expected {M.TOTAL_PAGES} (data/manifest.json)")
    bookmarks=list(flatten(verify.outline))
    if len(bookmarks)!=M.TOTAL_BOOKMARKS:
        raise RuntimeError(f"Book PDF has {len(bookmarks)} bookmarks, manifest derives {M.TOTAL_BOOKMARKS}")
    expected_titles=[]
    for chapter in M.CHAPTERS:
        expected_titles.append(M.chapter_title(chapter))
        expected_titles.extend(M.item_title(i,summaries) for i in M.item_bookmarks(chapter))
    if [b.title for b in bookmarks]!=expected_titles:
        raise RuntimeError("Bookmark titles or order differ from the manifest sequence")
    for bookmark,(chapter_or_item,first) in zip(bookmarks,_expected_targets()):
        if verify.get_destination_page_number(bookmark)!=first-1:
            raise RuntimeError(f"Bookmark {bookmark.title!r} points at page {verify.get_destination_page_number(bookmark)+1}, expected {first}")
    expected_map=[(n,item) for n,_,item,_ in M.page_map()]
    if placed!=expected_map:
        raise RuntimeError("Placed pages differ from manifest page map")
    if dest.stat().st_size<1_000_000:
        raise RuntimeError("Merged booklet too small for the manifest scans and worksheets")
    for chapter,first,last in M.layout():
        print(f"Pages {first:02d}–{last:02d}: {M.chapter_title(chapter)}")
    print(f"PASS: complete single PDF {len(verify.pages)} pages, {len(M.CHAPTERS)} chapters, {len(bookmarks)} bookmarks, "
          f"{len(numbered)} numbered pages, {dest.stat().st_size} bytes")

def _expected_targets():
    """(label owner, first page) for every bookmark in manifest order."""
    out=[]
    for chapter,first,_ in M.layout():
        out.append((chapter,first))
        page=first
        for item in chapter["items"]:
            if len(chapter["items"])>1:
                out.append((item,page))
            page+=M.item_pages(item)
    return out

if __name__=="__main__":build()
