#!/usr/bin/env python3
"""Fail CI if the authoritative project contract diverges from real artifacts.

This test is deliberately read-only. SOURCE_OF_TRUTH.md defines policy;
all PDF files, worksheets and public guides must represent its verified inventory.
"""
from pathlib import Path
from pypdf import PdfReader
import re

ROOT=Path(__file__).resolve().parents[1]
SOT=(ROOT/"SOURCE_OF_TRUTH.md").read_text(encoding="utf-8")
README=(ROOT/"README.md").read_text(encoding="utf-8")
INTRO=(ROOT/"book"/"INTRO.md").read_text(encoding="utf-8")
ORIGINAL={
    "orig-rectangles","orig-translation","orig-reflection","orig-rotation",
    "orig-composition","orig-symmetry","orig-conveyor","orig-mirror-route",
    "orig-center-p","orig-symbol-turn","orig-robot-grid"
}
IMPORTED={"349","350","351","352","385","549","rectangles","true-false","triangle"}
SCANS={34,35,36,37,38,50,51}

def demand(test,reason):
    if not test:
        raise AssertionError(reason)

def pdf_pages(relative,expected):
    doc=PdfReader(str(ROOT/relative))
    demand(len(doc.pages)==expected,f"{relative}: expected {expected} pages, got {len(doc.pages)}")
    return doc

def main():
    worksheets={p.stem for p in (ROOT/"worksheets").glob("*.html")}
    pdfs={p.stem for p in (ROOT/"pdf").glob("*.pdf")}
    demand(worksheets==ORIGINAL|IMPORTED,f"Unexpected worksheet inventory: {worksheets^(ORIGINAL|IMPORTED)}")
    demand(pdfs==worksheets,f"PDF inventory does not match HTML inventory: {pdfs^worksheets}")
    demand(len(worksheets)==20 and len(ORIGINAL)==11 and len(IMPORTED)==9,"Worksheet count drift")
    source_paths={f"grade7-p{x:03}.webp" for x in SCANS}
    demand({p.name for p in (ROOT/"sources"/"ministry").glob("*.webp")}==source_paths,
           "Unverified or missing Ministry source page")
    for rel in ("README.md","book/INTRO.md"):
        demand((ROOT/rel).is_file(),f"Missing public guide: {rel}")
    demand(README.count("SOURCE_OF_TRUTH.md")>=1,"README must point to sole source of truth")
    demand("## 4. מבנה" not in SOT,"Old source-of-truth format detected")
    for marker in ("## א. המטרה","## ב. גבולות","## ג. רישום המקורות",
                   "## ד. מלאי התוצרים","## ה. בקרות","## ו. שלבי העבודה",
                   "## ז. הפערים"):
        demand(marker in SOT,f"Missing single authoritative section: {marker}")
    demand(SOT.count("## ו. שלבי העבודה")==1,"More than one current stage tracker")
    demand("11 דפי" in SOT and "20 דפי" in SOT and "14 עמוד" in SOT,
           "Authoritative inventory lacks verified totals")
    demand("50 עמודים" in SOT and "25 סימניות" in SOT,
           "Authoritative merged booklet metadata missing")
    demand("20 דפי" in README and "11 דפים" in README and "50 עמודים" in README,
           "README is out of sync with actual inventory")
    demand("ששת חלקי החוברת" in INTRO and "ארבעת חלקי החוברת" not in INTRO,
           "Old four-part table of contents survives in the introduction")
    for head in ("| א׳ —","| ב׳ —","| ג׳ —","| ד׳ —","| ה׳ —","| ו׳ —"):
        demand(head in INTRO,f"Missing real workbook part in introduction: {head}")
    book=pdf_pages("book/transformations-complete.pdf",50)
    pdf_pages("book/teacher.pdf",14)
    pdf_pages("book/official.pdf",7)
    demand(len(book.outline)==25,
           f"Book must have 25 navigation bookmarks, found {len(book.outline)}")
    for ident in ORIGINAL:
        pdf_pages(f"pdf/{ident}.pdf",1)
        html=(ROOT/"worksheets"/f"{ident}.html").read_text(encoding="utf-8")
        demand("יצירה מקורית: יניב רז" in html and "raz-logo.svg" in html,
               f"Original missing exclusive credit: {ident}")
    for ident in IMPORTED:
        pdf_pages(f"pdf/{ident}.pdf",2 if ident=="triangle" else 1)
        html=(ROOT/"worksheets"/f"{ident}.html").read_text(encoding="utf-8")
        demand("raz-logo.svg" not in html,
               f"Imported content must not carry creator logo: {ident}")
    for path in ("book/teacher.html","book/official.html","original.html","curriculum.html",
                 "book/front.html","book/answers.html","book/workshop.html","index.html"):
        demand((ROOT/path).is_file(),f"Missing public part of the book: {path}")
    print("PASS: single authoritative requirements contract, README and introduction agree")
    print("PASS: 50-page book with 25 bookmarks, 14 teacher pages, 7 original Ministry scans")
    print("PASS: 11 original 1-page A4 worksheets, 9 correctly attributed imported worksheets")

if __name__=="__main__":
    main()
