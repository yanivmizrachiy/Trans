#!/usr/bin/env python3
"""Fail if any consumer of the inventory disagrees with data/manifest.json.

The manifest is the one technical place that lists worksheet ids, their
order in the booklet, the Ministry scans and the booklet parts. Everything
derived from it (page ranges, totals, bookmark count) is compared here with:

- the files on disk (HTML <-> PDF, scans, booklet part PDFs);
- the homepage catalog, the originals catalog and the official viewer;
- the printed table of contents (book/front.html) and the introduction;
- README.md and SOURCE_OF_TRUTH.md totals;
- the built PDFs: page counts of every part and of the merged booklet,
  and the number of bookmarks.

A new worksheet that is added to only one of these places, a duplicate id,
a wrong order or a stale page number stops the build here.
"""
from pathlib import Path
import os
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest as M  # noqa: E402
from pypdf import PdfReader  # noqa: E402

ROOT = M.ROOT


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def demand(test, reason):
    if not test:
        raise AssertionError(reason)


def check_files():
    M.validate()
    html_ids = {p.stem for p in (ROOT / "worksheets").glob("*.html")}
    pdf_ids = {p.stem for p in (ROOT / "pdf").glob("*.pdf")}
    demand(html_ids == set(M.WORKSHEETS), f"worksheets/ differs from manifest: {html_ids ^ set(M.WORKSHEETS)}")
    demand(pdf_ids == set(M.WORKSHEETS), f"pdf/ differs from manifest: {pdf_ids ^ set(M.WORKSHEETS)}")
    scans = {p.name for p in (ROOT / M.DATA["ministry"]["source_dir"]).glob("*.webp")}
    expected = {M.ministry_file(n).name for n in M.MINISTRY_PAGES}
    demand(scans == expected, f"sources/ministry differs from manifest: {scans ^ expected}")


def check_catalogs():
    index = read("index.html")
    catalog = [a or b for a, b in re.findall(r'^\[(?:([0-9]+)|"([a-z0-9-]+)"),', index, re.M)]
    demand(len(catalog) == len(set(catalog)), "Homepage catalog repeats a worksheet id")
    demand(set(catalog) == set(M.WORKSHEETS), f"Homepage catalog differs from manifest: {set(catalog) ^ set(M.WORKSHEETS)}")
    original = read("original.html")
    for ident in M.ORIGINAL:
        demand(f"worksheets/{ident}.html" in original and f"pdf/{ident}.pdf" in original,
               f"original.html must link HTML and PDF of {ident}")
    for ident in M.IMPORTED:
        demand(f"worksheets/{ident}.html" not in original, f"original.html must not list imported sheet {ident}")
    official = read("book/official.html")
    for page in M.MINISTRY_PAGES:
        demand(f"../{M.DATA['ministry']['source_dir']}/{M.ministry_file(page).name}" in official,
               f"book/official.html does not show Ministry page {page}")
    demand(official.count('class="scan"') == len(M.MINISTRY_PAGES),
           "book/official.html scan count differs from manifest")


def check_table_of_contents():
    front = read("book/front.html")
    intro = read("book/INTRO.md")
    for part, first, last in M.layout():
        if "part" not in part:
            continue
        rng = f"{first}–{last}"
        demand(f'<span class="pg">{rng}</span>' in front,
               f"book/front.html table of contents lacks pages {rng} for part {part['part']}")
        demand(re.search(rf"^\| {re.escape(part['part'])} — [^|]*\| {rng} \|", intro, re.M),
               f"book/INTRO.md part table lacks '{part['part']} … | {rng} |'")
    demand(f"{M.TOTAL_PAGES} עמודים" in front or f"{M.TOTAL_PAGES}" in front, "front.html total pages")


def check_documents():
    readme = read("README.md")
    sot = read("SOURCE_OF_TRUTH.md")
    index = read("index.html")
    teacher = read("teacher.html")
    booklet = (f"{M.TOTAL_PAGES} עמודים", f"{M.TOTAL_BOOKMARKS} סימניות")
    for text, name in ((readme, "README.md"), (sot, "SOURCE_OF_TRUTH.md"), (index, "index.html"), (teacher, "teacher.html")):
        for token in booklet:
            demand(token in text, f"{name} does not state '{token}' (manifest-derived)")
    for text, name in ((readme, "README.md"), (sot, "SOURCE_OF_TRUTH.md"), (teacher, "teacher.html")):
        demand(f"{len(M.WORKSHEETS)} דפי" in text, f"{name} does not state the {len(M.WORKSHEETS)}-worksheet total")
    demand(f"{len(M.ORIGINAL)} דפי עבודה מקוריים" in index and f"{len(M.IMPORTED)} דפים ממקורות קודמים" in index,
           "index.html source filters must show the manifest's original/imported counts")
    demand(f"{len(M.ORIGINAL)} דפי" in readme and f"{len(M.ORIGINAL)} דפים" in readme, "README originals count")
    demand(f"| **סה״כ דפי עבודה** | **{len(M.WORKSHEETS)} דפי HTML ו־{len(M.WORKSHEETS)} PDF** |" in sot,
           "SOURCE_OF_TRUTH inventory table total differs from manifest")
    demand(f"**{M.TOTAL_PAGES} עמודים, {M.TOTAL_BOOKMARKS} סימניות PDF**" in sot,
           "SOURCE_OF_TRUTH booklet row differs from manifest")
    pattern = "; ".join(rf"{first}–{last} [^;]*" for _, first, last in M.layout())
    demand(re.search(r"\*\*מספור מאומת בחוברת " + str(M.TOTAL_PAGES) + r" עמודים:\*\* " + pattern, sot),
           "SOURCE_OF_TRUTH page numbering sentence differs from the manifest layout")


def check_pdfs():
    for part, first, last in M.layout():
        if "file" in part:
            count = len(PdfReader(str(ROOT / part["file"])).pages)
            demand(count == last - first + 1, f"{part['file']} has {count} pages, manifest layout expects {last - first + 1}")
    for ident in M.WORKSHEETS:
        count = len(PdfReader(str(ROOT / "pdf" / f"{ident}.pdf")).pages)
        demand(count == M.WORKSHEET_PAGES[ident], f"pdf/{ident}.pdf has {count} pages, manifest says {M.WORKSHEET_PAGES[ident]}")
    book = PdfReader(str(ROOT / M.BOOK_FILE))
    demand(len(book.pages) == M.TOTAL_PAGES, f"{M.BOOK_FILE} has {len(book.pages)} pages, manifest derives {M.TOTAL_PAGES}")
    demand(len(book.outline) == M.TOTAL_BOOKMARKS, f"{M.BOOK_FILE} has {len(book.outline)} bookmarks, manifest derives {M.TOTAL_BOOKMARKS}")
    def flatten(items):
        for item in items:
            if isinstance(item, list):
                yield from flatten(item)
            else:
                yield item.title
    titles = list(flatten(book.outline))
    for ident in M.WORKSHEETS:
        demand(any(M.TITLES[ident] in t for t in titles), f"Booklet bookmark missing for {ident} ({M.TITLES[ident]})")


def main():
    check_files()
    check_catalogs()
    check_table_of_contents()
    check_documents()
    if os.environ.get("CHECK_BUILT_PDFS", "1") == "0":
        # Set by the check workflow on push/pull_request, where committed PDFs
        # may lag behind the sources until the build workflow republishes them.
        print("SKIPPED built-PDF checks (CHECK_BUILT_PDFS=0); the build workflow checks fresh PDFs")
    else:
        check_pdfs()
    built = "built PDFs" if os.environ.get("CHECK_BUILT_PDFS", "1") != "0" else "PDF file names"
    print(f"PASS: manifest agrees with files, catalogs, contents, README, SOURCE_OF_TRUTH and {built} "
          f"({len(M.WORKSHEETS)} worksheets, {len(M.MINISTRY_PAGES)} scans, {M.TOTAL_PAGES} pages, {M.TOTAL_BOOKMARKS} bookmarks)")


if __name__ == "__main__":
    main()
