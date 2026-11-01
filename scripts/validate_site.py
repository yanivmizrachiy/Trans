#!/usr/bin/env python3
"""Check worksheet catalog, PDFs, relative links and creator credit."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import re

R=Path(__file__).resolve().parents[1]
OWN={"orig-rectangles","orig-translation","orig-reflection","orig-rotation","orig-composition","orig-symmetry"}
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
    assert len(names)==15, ("worksheet count",len(names))
    assert {p.stem for p in pdfs}==names, "PDF inventory mismatch"
    index=(R/"index.html").read_text()
    catalog=set(re.findall(r'^\[(?:([0-9]+)|"([a-z0-9-]+)"),',index,re.M))
    assert {a or b for a,b in catalog}==names,"Homepage catalog mismatch"
    build=(R/"scripts/build_pdfs.py").read_text()
    ids=set(re.findall(r'"([a-z0-9-]+)"',build.split("IDS =",1)[1].split("\n",1)[0]))
    assert ids==names,"PDF generator inventory mismatch"
    for p in [R/"index.html",R/"teacher.html",R/"explore.html",*pages]:
        html=p.read_text()
        h=Links();h.feed(html)
        for link in h.urls:
            url=urlsplit(link)
            if url.scheme or url.netloc or not url.path: continue
            local=(p.parent/unquote(url.path)).resolve()
            assert (R==local or R in local.parents) and local.is_file(),(p.name,link)
        if p.parent.name=="worksheets":
            own=p.stem in OWN
            assert ("raz-logo.svg" in html)==own,(p.name,"incorrect logo")
            assert ("יצירה מקורית: יניב רז" in html)==own,(p.name,"incorrect credit")
            if own: assert (html.count('class="level"') + html.count("class='level'"))==3,p.name
    for p in pdfs:
        data=p.read_bytes()
        assert len(data)>3500 and data.startswith(b"%PDF-") and b"%%EOF" in data[-4096:],p.name
    assert "שאלות מתוך תוכנית הלימודים" in index
    print(f"PASS: {len(pages)} worksheets, {len(pdfs)} PDFs, {len(OWN)} author-only originals")
if __name__=="__main__":main()
