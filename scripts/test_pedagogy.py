#!/usr/bin/env python3
"""Independent educational QA: original level coverage, answer keys, duplicate prompts and source isolation."""
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import re
import sys
import manifest as M

ROOT=M.ROOT
ORIGINAL=M.ORIGINAL

class Levels(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.levels=[]
        self.active=False
    def handle_starttag(self,tag,attrs):
        if tag=="section" and "level" in dict(attrs).get("class","").split():
            if self.active: raise AssertionError("Nested question level")
            self.active=True
            self.levels.append([])
    def handle_data(self,data):
        if self.active:self.levels[-1].append(data)
    def handle_endtag(self,tag):
        if tag=="section" and self.active:self.active=False

def words(text):
    s=re.sub(r"[-−]?\d+","N",text)
    return re.findall(r"[\u0590-\u05ff]{2,}|[A-Za-z]+",s)

def shingles(s):
    x=words(s)
    return set(zip(x,x[1:],x[2:]))

def main():
    key=(ROOT/"docs"/"ANSWER_KEY.md").read_text(encoding="utf-8")
    seen=[]
    for ident in ORIGINAL:
        sheet=(ROOT/"worksheets"/f"{ident}.html").read_text(encoding="utf-8")
        p=Levels();p.feed(sheet)
        if len(p.levels)!=3:raise AssertionError(f"{ident}: expected three distinct questions")
        texts=[" ".join(z).strip() for z in p.levels]
        if any(len(t)<65 for t in texts):raise AssertionError(f"{ident}: truncated or empty problem")
        if len({re.sub(r"\d+","0",t) for t in texts})!=3:
            raise AssertionError(f"{ident}: duplicated level with changed numbers")
        for i,t in enumerate(texts):
            seen.append((ident,i+1,t))
        pattern=r"^### [^\n]*`"+re.escape(ident)+r"`"
        ms=list(re.finditer(pattern,key,re.M))
        if len(ms)!=1:raise AssertionError(f"{ident}: expected exactly one teacher answer-key section")
        content=key[ms[0].end():]
        cut=re.search(r"^### |^## ",content,re.M)
        if cut:content=content[:cut.start()]
        answers=re.findall(r"^- \*\*[^\n]+",content,re.M)
        if len(answers)<3:raise AssertionError(f"{ident}: all three questions must have answers")
        pages=M.WORKSHEET_PAGES[ident]
        if sheet.count('יניב רז - מדריך מחוזי חט"ב בעיר ירושלים')!=pages or sheet.count("../assets/logo.png")!=pages:
            raise AssertionError(f"{ident}: one district credit and logo footer on each of its {pages} printed page(s)")
        if re.search(r"רמה [אבג]׳|רמה מקבילה|שלוש רמות|מדורג",sheet):
            raise AssertionError(f"{ident}: level labels are not shown to students")
    for i,(a,ai,x) in enumerate(seen):
        xx=shingles(x)
        if not xx:raise AssertionError(f"Text parsing failed for {a}")
        for b,bi,y in seen[i+1:]:
            yy=shingles(y)
            score=len(xx&yy)/max(1,len(xx|yy))
            if score>0.82:raise AssertionError(f"Near-duplicate prompt: {a}/{ai} and {b}/{bi} ({score:.2%})")
    rotation=(ROOT/"worksheets"/"orig-rotation.html").read_text(encoding="utf-8")
    if "מהמשולש המקורי ABC (לא מתמונת שאלה 2)" not in rotation or "A″, B″, C″" not in rotation:
        raise AssertionError("Rotation comparison must explicitly use the original triangle and distinguish the second image")
    other=M.IMPORTED
    for ident in other:
        raw=(ROOT/"worksheets"/f"{ident}.html").read_text(encoding="utf-8")
        if "הדף נערך" in raw:
            raise AssertionError(f"{ident}: other creators' content was falsely credited")
        # Every printed page carries the booklet's logo footer,
        # with the shared wording, not an editing credit.
        if raw.count('class="ws-footline"')!=M.WORKSHEET_PAGES[ident] or raw.count("assets/logo.png")!=M.WORKSHEET_PAGES[ident]:
            raise AssertionError(f"{ident}: every printed page needs exactly one logo footer")
        if "תאריך:" in raw or "שם התלמיד" in raw:
            raise AssertionError(f"{ident}: worksheets carry no name or date line")
    # Material once derived from an external slide deck was rewritten;
    # the deck's file name, date and editors must not creep back into public files.
    public=["worksheets/rectangles.html","worksheets/true-false.html","worksheets/triangle.html",
            "docs/TEACHER_WORKSHOP.md","index.html","book/teacher.html","book/krispin-video.html","book/sadna.html","book/official.html",
            "book/complete.html","README.md","data/manifest.json"]
    remnants=("PRESENTATION_2026","21.10.2026","מצגת ההשתלמות","מצגת קהילת","סיכום מצגת","סיכום השתלמות")
    for rel in public:
        text=(ROOT/rel).read_text(encoding="utf-8")
        for token in remnants:
            if token in text:raise AssertionError(f"{rel}: remnant of the replaced slide deck: {token!r}")
    if "עידן אחוון" in (ROOT/"docs"/"TEACHER_WORKSHOP.md").read_text(encoding="utf-8"):
        raise AssertionError("docs/TEACHER_WORKSHOP.md must be original, not a deck summary")
    # The printed booklet carries no meta notes about itself or its sources.
    booklet=["book/teacher.html","book/sadna.html","book/krispin-video.html",
             "docs/TEACHER_WORKSHOP.md","docs/ANSWER_KEY.md",*(f"worksheets/{i}.html" for i in M.WORKSHEETS)]
    meta=("חוברת הוראה אחת","חוברת מאוחדת","העמודים הרשמיים","נכתב לחוברת","נכתבו עבור החוברת","נכתב במיוחד",
          "אינו העתק","אינו ציטוט","אינם ציטוט","נוסחו מחדש","בהשראת","ייחוס","SOURCE_OF_TRUTH","תוכן עניינים")
    for rel in booklet:
        text=(ROOT/rel).read_text(encoding="utf-8")
        for token in meta:
            if token in text:raise AssertionError(f"{rel}: meta wording in the booklet: {token!r}")
    # Ayelet Krispin's exact title, as in the district repositories (jerusalem RULES.md).
    video=(ROOT/"book"/"krispin-video.html").read_text(encoding="utf-8")
    if "איילת קריספין, מתכללת את תחום המתמטיקה במחוז ירושלים והעיר ירושלים - מנח״י" not in video:
        raise AssertionError("book/krispin-video.html: Ayelet Krispin's title must be stated exactly")
    # A4 print booklet, not online pages: no "open full size" links.
    for path in sorted((ROOT/"book").glob("*.html")):
        if "בגודל מלא" in path.read_text(encoding="utf-8"):
            raise AssertionError(f"book/{path.name}: full-size link in the print booklet")
    print(f"PASS: {len(ORIGINAL)} original worksheets, {len(seen)} problems, 11 complete answer-key sections, no near-duplicates")

if __name__=="__main__":main()
