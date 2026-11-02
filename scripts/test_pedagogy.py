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
        if sheet.count("הדף נערך ע״י יניב רז · מדריך מחוזי חט״ב בעיר ירושלים")!=1 or sheet.count("../assets/logo.png")!=1:
            raise AssertionError(f"{ident}: exactly one district credit and logo required")
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
        if "assets/logo.png" in raw or "הדף נערך ע״י יניב רז · מדריך מחוזי חט״ב בעיר ירושלים" in raw:
            raise AssertionError(f"{ident}: other creators' content was falsely credited")
    # Material once derived from an external slide deck was rewritten (SOURCE_OF_TRUTH §כ.8);
    # the deck's file name, date and editors must not creep back into public files.
    public=["worksheets/rectangles.html","worksheets/true-false.html","worksheets/triangle.html",
            "docs/TEACHER_WORKSHOP.md","teacher.html","index.html","book/front.html","book/INTRO.md",
            "book/complete.html","README.md","data/manifest.json"]
    remnants=("PRESENTATION_2026","21.10.2026","מצגת ההשתלמות","מצגת קהילת","סיכום מצגת","סיכום השתלמות")
    for rel in public:
        text=(ROOT/rel).read_text(encoding="utf-8")
        for token in remnants:
            if token in text:raise AssertionError(f"{rel}: remnant of the replaced slide deck: {token!r}")
    if "עידן אחוון" in (ROOT/"docs"/"TEACHER_WORKSHOP.md").read_text(encoding="utf-8"):
        raise AssertionError("docs/TEACHER_WORKSHOP.md must be original, not a deck summary")
    for ident in ("rectangles","true-false","triangle"):
        if "דף מקורי שנכתב לחוברת" not in (ROOT/"worksheets"/f"{ident}.html").read_text(encoding="utf-8"):
            raise AssertionError(f"{ident}: rewritten sheet must declare that it was written for this booklet")
    print(f"PASS: {len(ORIGINAL)} original worksheets, {len(seen)} problems, 11 complete answer-key sections, no near-duplicates, district branding only on originals")

if __name__=="__main__":main()
