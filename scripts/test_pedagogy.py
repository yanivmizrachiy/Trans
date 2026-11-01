#!/usr/bin/env python3
"""Independent educational QA: original level coverage, answer keys, duplicate prompts and source isolation."""
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=("orig-rectangles","orig-translation","orig-reflection","orig-rotation",
          "orig-composition","orig-symmetry","orig-conveyor","orig-mirror-route",
          "orig-center-p","orig-symbol-turn","orig-robot-grid")

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
        if len(p.levels)!=3:raise AssertionError(f"{ident}: expected three distinct difficulty levels")
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
        if len(answers)<3:raise AssertionError(f"{ident}: all three levels must have answers")
        if sheet.count("יצירה מקורית: יניב רז")!=1 or sheet.count("raz-logo.svg")!=1:
            raise AssertionError(f"{ident}: exactly one creator credit and logo required")
    for i,(a,ai,x) in enumerate(seen):
        xx=shingles(x)
        if not xx:raise AssertionError(f"Text parsing failed for {a}")
        for b,bi,y in seen[i+1:]:
            yy=shingles(y)
            score=len(xx&yy)/max(1,len(xx|yy))
            if score>0.82:raise AssertionError(f"Near-duplicate prompt: {a}/{ai} and {b}/{bi} ({score:.2%})")
    other=("349","350","351","352","385","549","rectangles","true-false","triangle")
    for ident in other:
        raw=(ROOT/"worksheets"/f"{ident}.html").read_text(encoding="utf-8")
        if "raz-logo.svg" in raw or "יצירה מקורית: יניב רז" in raw:
            raise AssertionError(f"{ident}: other creators' content was falsely credited")
    print(f"PASS: {len(ORIGINAL)} original worksheets, {len(seen)} graded problems, 11 complete answer-key sections, no near-duplicates, exclusive branding")

if __name__=="__main__":main()
