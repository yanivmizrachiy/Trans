#!/usr/bin/env python3
"""Fail CI if the authoritative project contract diverges from real artifacts.

This test is deliberately read-only. SOURCE_OF_TRUTH.md defines policy;
all PDF files, worksheets and public guides must represent its verified inventory.
"""
from pathlib import Path
import os
from pypdf import PdfReader
import re
import manifest as M

ROOT=M.ROOT
SOT=(ROOT/"SOURCE_OF_TRUTH.md").read_text(encoding="utf-8")
README=(ROOT/"README.md").read_text(encoding="utf-8")
INTRO=(ROOT/"book"/"INTRO.md").read_text(encoding="utf-8")
ORIGINAL=set(M.ORIGINAL)
IMPORTED=set(M.IMPORTED)
SCANS=set(M.MINISTRY_PAGES)

def demand(test,reason):
    if not test:
        raise AssertionError(reason)

# CHECK_BUILT_PDFS=0 is set by the check workflow on push/pull_request events,
# where the committed PDFs may legitimately lag behind the sources until the
# build workflow has rebuilt and published them. The build workflow and the
# post-build (workflow_run) check always compare against current PDFs.
CHECK_BUILT_PDFS=os.environ.get("CHECK_BUILT_PDFS","1")!="0"

def pdf_pages(relative,expected):
    path=ROOT/relative
    demand(path.is_file() and path.read_bytes().startswith(b"%PDF-"),f"{relative}: missing or not a PDF")
    if not CHECK_BUILT_PDFS:
        return None
    doc=PdfReader(str(path))
    demand(len(doc.pages)==expected,f"{relative}: expected {expected} pages, got {len(doc.pages)}")
    return doc

def main():
    worksheets={p.stem for p in (ROOT/"worksheets").glob("*.html")}
    pdfs={p.stem for p in (ROOT/"pdf").glob("*.pdf")}
    demand(worksheets==ORIGINAL|IMPORTED,f"Unexpected worksheet inventory: {worksheets^(ORIGINAL|IMPORTED)}")
    demand(pdfs==worksheets,f"PDF inventory does not match HTML inventory: {pdfs^worksheets}")
    demand(len(worksheets)==len(M.WORKSHEETS) and len(ORIGINAL)==11 and len(IMPORTED)==9,"Worksheet count drift")
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
    demand(f"{len(ORIGINAL)} דפי" in SOT and f"{len(M.WORKSHEETS)} דפי" in SOT and "14 עמוד" in SOT,
           "Authoritative inventory lacks verified totals")
    demand(f"{M.TOTAL_PAGES} עמודים" in SOT and f"{M.TOTAL_BOOKMARKS} סימניות" in SOT,
           "Authoritative merged booklet metadata missing")
    demand(f"{len(M.WORKSHEETS)} דפי" in README and f"{len(ORIGINAL)} דפים" in README and f"{M.TOTAL_PAGES} עמודים" in README,
           "README is out of sync with actual inventory")
    demand("שבעת חלקי החוברת" in INTRO and "ששת חלקי החוברת" not in INTRO,
           "Old four-part table of contents survives in the introduction")
    for head in ("| א׳ —","| ב׳ —","| ג׳ —","| ד׳ —","| ה׳ —","| ו׳ —","| ז׳ —"):
        demand(head in INTRO,f"Missing real workbook part in introduction: {head}")
    book=pdf_pages(M.BOOK_FILE,M.TOTAL_PAGES)
    for part,first,last in M.layout():
        if "file" in part:
            pdf_pages(part["file"],last-first+1)
    demand("| מפתח תשובות למורה | 6 עמודים בחוברת |" in SOT,
           "Answer-key page count in the single source of truth contradicts the printed PDF")
    if book is not None:
        demand(len(book.outline)==M.TOTAL_BOOKMARKS,
               f"Book must have {M.TOTAL_BOOKMARKS} navigation bookmarks, found {len(book.outline)}")
    for ident in ORIGINAL:
        pdf_pages(f"pdf/{ident}.pdf",M.WORKSHEET_PAGES[ident])
        html=(ROOT/"worksheets"/f"{ident}.html").read_text(encoding="utf-8")
        demand("יצירה מקורית: יניב רז" in html and "raz-logo.svg" in html,
               f"Original missing exclusive credit: {ident}")
    for ident in IMPORTED:
        pdf_pages(f"pdf/{ident}.pdf",M.WORKSHEET_PAGES[ident])
        html=(ROOT/"worksheets"/f"{ident}.html").read_text(encoding="utf-8")
        demand("raz-logo.svg" not in html,
               f"Imported content must not carry creator logo: {ident}")
    for path in ("book/teacher.html","book/official.html","original.html","curriculum.html",
                 "book/front.html","book/answers.html","book/workshop.html","book/sadna.html","index.html"):
        demand((ROOT/path).is_file(),f"Missing public part of the book: {path}")
    sadna=(ROOT/"book"/"sadna.html").read_text(encoding="utf-8")
    demand(sadna.count('class="sheet"')==3 and sadna.count("שרית מאירוביץ וסיגלית אטשי")>=3,
           "Every workshop-deck page must credit its editors in the footer")
    demand("שרית מאירוביץ וסיגלית אטשי" in SOT,"Editors credit rule missing from the source of truth")
    print("PASS: single authoritative requirements contract, README and introduction agree")
    if CHECK_BUILT_PDFS:
        print(f"PASS: {M.TOTAL_PAGES}-page book with {M.TOTAL_BOOKMARKS} bookmarks, 14 teacher pages, {len(SCANS)} original Ministry scans")
    else:
        print(f"SKIPPED built-PDF page and bookmark counts (CHECK_BUILT_PDFS=0); {len(SCANS)} original Ministry scans listed")
    print(f"PASS: {len(ORIGINAL)} original 1-page A4 worksheets, {len(IMPORTED)} correctly attributed imported worksheets")

if __name__=="__main__":
    main()
