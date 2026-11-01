#!/usr/bin/env python3
"""Derive the public teacher-answer accordions from docs/ANSWER_KEY.md.

Writing is an explicit maintenance action. CI uses --check and fails if a
teacher-facing solution differs from the canonical teacher answer key.
"""
from pathlib import Path
from html import escape
import re
import sys
from test_math import ROOT, SOURCE

ANSWER=ROOT/"docs"/"ANSWER_KEY.md"
TEACHER=ROOT/"teacher.html"
HEAD=re.compile(r"^### [^\n]*\x60(orig-[a-z-]+)\x60[^\n]*$",re.M)
BULLET=re.compile(r"^- \*\*(.*?)\*\*(.*)$",re.M)
CHUNKS=re.compile(r"(\x60[^\x60]*\x60|\*\*[^*]*\*\*)")
ORIGINALS=tuple(SOURCE)

def inline(source):
    out=[]
    for part in CHUNKS.split(source):
        if part.startswith(chr(96)) and part.endswith(chr(96)):
            out.append('<code dir="ltr">'+escape(part[1:-1])+"</code>")
        elif part.startswith("**") and part.endswith("**"):
            out.append("<strong>"+escape(part[2:-2])+"</strong>")
        else:
            out.append(escape(part))
    return "".join(out)

def answer_sections(markdown):
    matches=list(HEAD.finditer(markdown))
    results={}
    for i,match in enumerate(matches):
        ident=match.group(1)
        if ident not in ORIGINALS:continue
        ending=matches[i+1].start() if i+1<len(matches) else len(markdown)
        section=markdown[match.end():ending]
        section=re.split(r"^## ",section,1,flags=re.M)[0]
        bullets=BULLET.findall(section)
        if len(bullets)!=3:
            raise ValueError(f"{ident}: expected three answer bullets; found {len(bullets)}")
        if ident in results:
            raise ValueError(f"Duplicate original {ident}")
        results[ident]="".join("<li>"+inline("**"+title+"**"+body)+"</li>" for title,body in bullets)
    if set(results)!=set(ORIGINALS):
        raise ValueError(f"Answer key inventory mismatch: {set(ORIGINALS)^set(results)}")
    return results

def expected_html(teacher,sections):
    updated=teacher
    for ident,answer_items in sections.items():
        regex=re.compile(
            r"(<details><summary>[^<]*<code(?: [^>]*)?>"
            +re.escape(ident)
            +r"</code></summary><ul>)(.*?)(</ul></details>)",
            re.S,
        )
        match=list(regex.finditer(updated))
        if len(match)!=1:
            raise ValueError(f"Teacher HTML does not have exactly one {ident} answer accordion")
        updated=regex.sub(lambda m:m.group(1)+answer_items+m.group(3),updated,count=1)
    return updated

def main():
    markdown=ANSWER.read_text(encoding="utf-8")
    actual=TEACHER.read_text(encoding="utf-8")
    result=expected_html(actual,answer_sections(markdown))
    if "--write" in sys.argv:
        if actual!=result:
            TEACHER.write_text(result,encoding="utf-8")
            print("UPDATED public teacher.html: 11 groups and 33 source-derived answer levels")
        else:
            print("PASS: teacher.html already matches all canonical answer bullets")
        return
    if actual!=result:
        print("FAIL: teacher.html disagrees with docs/ANSWER_KEY.md. Run python scripts/sync_teacher_answers.py --write")
        raise SystemExit(1)
    print("PASS: all 33 public teacher answers match canonical key, including intermediate/final images")

if __name__=="__main__":
    main()
