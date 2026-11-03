#!/usr/bin/env python3
"""Check worksheet catalog, PDFs, relative links and creator credit."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import re
import manifest as M

R=M.ROOT
OWN=set(M.ORIGINAL)
class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        self.urls.extend(d[k] for k in ("href","src") if d.get(k))
def main():
    pages=list((R/"worksheets").glob("*.html"))
    names={p.stem for p in pages}
    pdfs=list((R/"pdf").glob("*.pdf"))
    assert names==set(M.WORKSHEETS), ("worksheet inventory differs from data/manifest.json",names^set(M.WORKSHEETS))
    assert {p.stem for p in pdfs}==names, "PDF inventory mismatch"
    index=(R/"index.html").read_text(encoding="utf-8")
    catalog=set(re.findall(r'^\[(?:([0-9]+)|"([a-z0-9-]+)"),',index,re.M))
    assert {a or b for a,b in catalog}==names,"Homepage catalog mismatch"
    assert "from manifest import" in (R/"scripts/build_pdfs.py").read_text(encoding="utf-8"),"PDF generator must take its inventory from the manifest"
    banned=re.compile(r"(?i)\b(?:demo|mock|dummy|lorem ipsum|coming soon|javascript:void)\b|(?<![\u0590-\u05ff])דמו(?![\u0590-\u05ff])|בקרוב|בהקמה|בהכנה")
    content_pages=[R/"index.html",R/"teacher.html",R/"explore.html",R/"curriculum.html",R/"original.html",R/"book"/"teacher.html",R/"book"/"official.html",R/"book"/"sadna.html",R/"book"/"krispin-video.html",*pages]
    # Every HTML file in book/ is a public URL (and most are bound into the
    # booklet PDF), so rendered guides such as workshop.html and answers.html
    # must pass the same relative-link check as the hand-written pages.
    book_pages=sorted((R/"book").glob("*.html"))
    assert len(book_pages)>=6, ("book HTML inventory", [b.name for b in book_pages])
    for p in content_pages+[b for b in book_pages if b not in content_pages]:
        html=p.read_text(encoding="utf-8")
        if p in content_pages:
            assert banned.search(html) is None, (p.name,"Demo or unfinished placeholder content is prohibited")
        assert not re.search(r"href\s*=\s*['\"](?:#|javascript:|\s*)['\"]", html, re.I), (p.name, "Fake or empty link")
        h=Links();h.feed(html)
        for link in h.urls:
            url=urlsplit(link)
            if url.scheme or url.netloc or not url.path: continue
            local=(p.parent/unquote(url.path)).resolve()
            assert (R==local or R in local.parents) and local.is_file(),(p.name,"broken relative link",link)
            assert not local.suffix==".md" or p.parent.name!="book",(p.name,"book pages must link to rendered HTML, not Markdown",link)
        if p.parent.name=="worksheets":
            own=p.stem in OWN
            assert "../assets/logo.png" in html,(p.name,"every printed worksheet page carries the logo footer (SOURCE_OF_TRUTH §כג.14)")
            assert ("הדף נערך ע״י יניב רז · מדריך מחוזי חט״ב בעיר ירושלים" in html)==own,(p.name,"incorrect credit")
            assert "raz-logo.svg" not in html and "יצירה מקורית: יניב רז" not in html,(p.name,"retired creator logo/credit")
            if own: assert (html.count('class="level"') + html.count("class='level'"))==3,p.name
    for p in pdfs:
        data=p.read_bytes()
        assert len(data)>3500 and data.startswith(b"%PDF-") and b"%%EOF" in data[-4096:],p.name
    complete=(R/"book"/"transformations-complete.pdf")
    packed=complete.read_bytes()
    assert len(packed)>1_000_000 and packed.startswith(b"%PDF-") and b"%%EOF" in packed[-4096:], "Merged book must be a real complete PDF"
    assert "book/transformations-complete.pdf" in index, "Homepage must link to the whole real booklet"
    official_source=(R/"book"/"official.html").read_text(encoding="utf-8")
    assert "הדף נערך ע״י יניב רז · מדריך מחוזי חט״ב בעיר ירושלים" not in official_source and "assets/logo.png" not in official_source, "Ministry page must have no author credit"
    for page_number in M.MINISTRY_PAGES:
        source_name=M.ministry_file(page_number).name
        assert (R/"sources"/"ministry"/source_name).is_file(),("Missing exact ministry source scan",source_name)
        assert f"../sources/ministry/{source_name}" in official_source,("Official source viewer missing scan",source_name)
    for path_pdf in (R/"book"/"teacher.pdf",R/"book"/"official.pdf"):
        blob=path_pdf.read_bytes()
        assert len(blob)>30000 and blob.startswith(b"%PDF-") and b"%%EOF" in blob[-4096:],("Missing or invalid booklet PDF",path_pdf)
    teacher_summary=(R/"book"/"teacher.html").read_text(encoding="utf-8")
    teacher_intro=(R/"book"/"INTRO.md").read_text(encoding="utf-8")
    assert "שאלה 13, עמ׳ 48" in teacher_summary and "<td>48</td>" in teacher_summary, "Teacher summary must explain the authentic grade-7 page 48 translation and area-preservation item"
    assert "| 48, שאלה 13 |" in teacher_intro, "Book teacher introduction must map the newly verified Ministry example"
    official=(R/"curriculum.html").read_text(encoding="utf-8")
    authored=(R/"original.html").read_text(encoding="utf-8")
    assert official.count('class="entry"')==9, "Official examples must stay in the dedicated nine-entry source catalog (pages 34–38, 48, 50–51, 88–89, 91)"
    for page in M.MINISTRY_PAGES:
        assert f"עמוד {page}" in official or f"{page}" in official, f"curriculum.html does not reference Ministry page {page} from the manifest"
    assert "הדף נערך ע״י יניב רז · מדריך מחוזי חט״ב בעיר ירושלים" not in official, "Official questions must never carry creator attribution"
    assert "assets/logo.png" not in official, "Official questions must never display the worksheet logo"
    for ident in OWN:
        assert f"worksheets/{ident}.html" in authored, ("Original worksheet absent from own catalog",ident)
        assert f"pdf/{ident}.pdf" in authored, ("Original PDF absent from own catalog",ident)
        assert f"worksheets/{ident}.html" not in official, ("Original worksheet mixed into official source page",ident)
    for ident in names-OWN:
        assert f"worksheets/{ident}.html" not in authored, ("Imported worksheet falsely attributed as newly original",ident)
    assert 'data-group="original"' in index and 'data-group="additional"' in index, "Homepage source filters missing"
    assert "שאלות מתוך תוכנית הלימודים" in index
    print(f"PASS: {len(pages)} worksheets, {len(pdfs)} PDFs, {len(OWN)} author-only originals")
if __name__=="__main__":main()
