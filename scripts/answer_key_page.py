#!/usr/bin/env python3
"""Printed layout of the teacher answer key.

docs/ANSWER_KEY.md stays the one source of the answers, and the answer tests read it.
For print, its worksheet sections follow the booklet pages, each opens with a header
holding its booklet page, and every answer is a row: the question badge on the right,
the answer beside it. Coordinates are set as left-to-right mathematics in the text font.
"""
import re
from markdown import markdown
import manifest as M

HEAD=""
FONTS=()

STYLE="""
*{box-sizing:border-box}
html{direction:rtl}
body{margin:0;font-family:Arial,"Noto Sans Hebrew",sans-serif;font-size:12.5px;line-height:1.42;color:#10202e;
  -webkit-print-color-adjust:exact;print-color-adjust:exact}
.guide{border:1.5px solid #c9d6e2;background:#eef3f9;border-radius:8px;padding:7px 12px 8px;margin:0 0 11px}
.guide h2{margin:0 0 3px;font-family:Arial,"Noto Sans Hebrew",sans-serif;font-weight:600;font-size:14px;color:#0b3a75}
.guide .lead-line{margin:0 0 4px;font-weight:600}
.guide ul{margin:0;padding:0;list-style:none;columns:2;column-gap:9mm}
.guide li{break-inside:avoid;margin:0 0 3px;padding-right:12px;position:relative}
.guide li::before{content:"";position:absolute;right:0;top:.55em;width:6px;height:6px;border-radius:50%;background:#0b3a75}
.guide .eval{margin:5px 0 0;padding-top:5px;border-top:1px solid #c9d6e2}
.cols{columns:2;column-gap:8mm;column-rule:1px solid #c9d6e2}
.ans{margin:0 0 9px}
.ans>h2{display:flex;align-items:center;gap:7px;margin:0 0 4px;padding:0 0 3px;border-bottom:2px solid #0b3a75;
  font-family:Arial,"Noto Sans Hebrew",sans-serif;font-weight:600;font-size:14.5px;line-height:1.25;color:#0b3a75;break-after:avoid;break-inside:avoid}
.ans>h2 .pg{flex:none;background:#0b3a75;color:#fff;border-radius:5px;padding:1px 7px 2px;font-size:12px;font-weight:600;letter-spacing:.2px}
.given{margin:0 0 3px;padding:3px 8px;background:#eef3f9;border-right:3px solid #0b3a75;border-radius:0 4px 4px 0;font-size:12px;break-inside:avoid}
.sub{margin:5px 0 1px;font-family:Arial,"Noto Sans Hebrew",sans-serif;font-weight:600;font-size:12.5px;color:#0b3a75;break-after:avoid}
.row{display:flex;align-items:flex-start;gap:6px;padding:3px 0 3.5px;border-bottom:1px solid #c9d6e2;break-inside:avoid}
.row:last-child{border-bottom:0}
.q{flex:none;min-width:19px;height:19px;margin-top:1px;padding:0 4px;border-radius:10px;background:#eef3f9;color:#0b3a75;
  font-family:Arial,"Noto Sans Hebrew",sans-serif;font-weight:700;font-size:11px;line-height:19px;text-align:center}
.a{flex:1;min-width:0}
.lead{font-weight:700;color:#0b3a75}
.v{display:inline-block;margin-left:5px;padding:0 6px;border-radius:4px;font-weight:800;font-size:11.5px;line-height:1.5}
.v.ok{background:#dcf2e3;color:#14632f}
.v.no{background:#fbe1e1;color:#9b1c1c}
.m{direction:ltr;unicode-bidi:isolate;white-space:nowrap;font-weight:600;color:#0b3a75}
strong{font-weight:700}
@media screen{body{max-width:1040px;margin:0 auto;padding:26px 22px}}
@media screen and (max-width:800px){.cols,.guide ul{columns:1}body{padding:16px 14px}}
"""

SHEET=re.compile(r"^#{2,3} (?P<title>.+?) — `(?P<id>[a-z0-9-]+)`\s*$")
RAZ=re.compile(r"^### עמוד (?P<id>\d+) — (?P<title>.+?)\s*$")
POINT=re.compile(r"(?:[A-Z][₀-₉]*[′″']*)?\((?:[−-]?\d+(?:\.\d+)?|[xy]),\s*(?:[−-]?\d+(?:\.\d+)?|[xy])\)"
                 r"|\b[xy]\s*=\s*[−-]?\d+|(?:[A-Z][′″'])+")

def iso(text):
    return "<bdi class='m' dir='ltr'>"+text.replace("-","−").replace("'","′")+"</bdi>"

def code(escaped):
    # a list of points breaks between its points, never inside one
    parts=re.split(r"(?<=\)),\s*|,\s+",escaped)
    return ", ".join(iso(p) for p in parts)

def inline(text):
    out=markdown(text).strip()
    out=re.sub(r"^<p>(.*)</p>$",r"\1",out,flags=re.S)
    out=re.sub(r"<code>(.*?)</code>",lambda m:code(m.group(1)),out)
    pieces=re.split(r"(<bdi[^>]*>.*?</bdi>|<[^>]+>)",out)
    return "".join(p if i%2 else POINT.sub(lambda m:iso(m.group(0)),p) for i,p in enumerate(pieces))

def row(body,badge=None,lead=None,verdict=None):
    q=f"<span class='q'>{badge}</span>" if badge else ""
    v=f"<span class='v {'ok' if verdict=='נכון' else 'no'}'>{verdict}</span>" if verdict else ""
    lead=f"<span class='lead'>{lead}</span> " if lead else ""
    return f"<div class='row'>{q}<div class='a'>{v}{lead}{body}</div></div>"

def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]

def table_rows(lines):
    head=cells(lines[0])
    body=[cells(l) for l in lines[2:]]
    if head==["סעיף","תשובה מדויקת"]:
        out=[]
        for c in body:
            m=re.match(r"([א-ת])\.\s*(.+)",c[0])
            if not m:raise ValueError(f"Answer-key row without a part letter: {c[0]}")
            out.append(row(inline(c[1]),m.group(1),inline(m.group(2))))
        return out
    if head==["תחנה","ההעתקה","תמונת הקודקודים"]:
        return [row(inline(c[2]),c[0],inline(c[1])) for c in body]
    raise ValueError(f"Unknown answer-key table: {head}")

def list_row(line):
    m=re.match(r"(\d+)\.\s+\*\*(נכון|לא נכון)\*\*\s*—\s*(.+)",line)
    if m:return row(inline(m.group(3)),m.group(1),verdict=m.group(2))
    m=re.match(r"- \*\*שאלה (\d+):\*\*\s*(.+)",line)
    if m:return row(inline(m.group(2)),m.group(1))
    m=re.match(r"- \*\*([א-ת])\. (.+?):\*\*\s*(.+)",line)
    if m:return row(inline(m.group(3)),m.group(1),inline(m.group(2)))
    m=re.match(r"- \*\*(.+?)\*\*\s*(.+)",line)
    if m:return row(inline(m.group(2)),lead=inline(m.group(1)))
    raise ValueError(f"Unknown answer-key line: {line}")

def follow_up(text):
    """The follow-up paragraph of the station sheet ('א. … ב. … ג. … ד. …') becomes four lettered rows."""
    parts=re.split(r"(?:^|\s)([א-ד])\. ",text)
    letters,bodies=parts[1::2],parts[2::2]
    if letters!=["א","ב","ג","ד"] or parts[0].strip():
        raise ValueError(f"Follow-up answers must be lettered א–ד: {letters}")
    return "<p class='sub'>משימות המשך</p>"+"".join(row(inline(b.strip()),l) for l,b in zip(letters,bodies))

def parse(content):
    title=None; sheets=[]; guide=[]; current=None
    for line in content.splitlines():
        if line.startswith("# "):
            title=line[2:].strip(); current=guide; continue
        m=SHEET.match(line) or RAZ.match(line)
        if m:
            current=[]; sheets.append((m.group("id"),m.group("title"),current)); continue
        if line.startswith("## קריטריונים"):
            current=guide; continue
        if line.startswith("#"):
            current=None; continue   # group headings carry no answers of their own
        if current is None:
            if line.strip():raise ValueError(f"Answer-key text outside a worksheet section: {line}")
            continue
        current.append(line)
    return title,sheets,guide

def body_html(lines,guide_out):
    out=[]; table=[]
    def flush():
        if table:
            out.extend(table_rows(table)); table.clear()
    for raw in lines:
        line=raw.strip()
        if line.startswith("|"):
            table.append(line); continue
        flush()
        if not line:continue
        if line.startswith("**הנחיית הערכה:**"):
            guide_out.append(f"<p class='eval'>{inline(line)}</p>")
        elif line.startswith("**משימות המשך — תשובות למורה:**"):
            out.append(follow_up(line.split(":**",1)[1].strip()))
        elif line.startswith(("נתון","מקור")):
            out.append(f"<p class='given'>{inline(line)}</p>")
        elif line.startswith("- ") or re.match(r"\d+\. ",line):
            out.append(list_row(line))
        else:
            raise ValueError(f"Unknown answer-key paragraph: {line}")
    flush()
    return "".join(out)

def page_span(ident,pages):
    first,last=pages[ident]
    return f"עמ׳ {first}" if first==last else f"עמ׳ {first}–{last}"

def page_body(content):
    title,sheets,guide=parse(content)
    if not title:raise ValueError("The answer key needs a top-level title")
    pages={}
    for n,_,item,_ in M.page_map():
        if item[0]=="w":
            first,_=pages.get(item[1],(n,n)); pages[item[1]]=(first,n)
    ids=[s[0] for s in sheets]
    if sorted(ids)!=sorted(M.WORKSHEETS) or len(set(ids))!=len(ids):
        raise ValueError(f"Answer key must hold one section per worksheet: {sorted(set(ids)^set(M.WORKSHEETS))}")
    extra=[]
    sections=[]
    for ident,name,lines in sorted(sheets,key=lambda s:pages[s[0]]):
        sections.append(f"<section class='ans' id='ans-{ident}'><h2><span class='pg'>{page_span(ident,pages)}</span>"
                        f"<span>{inline(name)}</span></h2>{body_html(lines,extra)}</section>")
    lead=[l.strip() for l in guide if l.strip() and not l.strip().startswith("- ")]
    items=[l.strip()[2:] for l in guide if l.strip().startswith("- ")]
    return ("<section class='guide'><h2>קריטריונים לתשובה טובה</h2>"
            +"".join(f"<p class='lead-line'>{inline(l)}</p>" for l in lead)
            +"<ul>"+"".join(f"<li>{inline(i)}</li>" for i in items)+"</ul>"+"".join(extra)+"</section>"
            "<main class='cols'>"+"".join(sections)+"</main>")
