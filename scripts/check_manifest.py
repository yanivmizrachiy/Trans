#!/usr/bin/env python3
"""Fail if any consumer of the inventory disagrees with data/manifest.json.

The manifest is the one technical place that lists worksheet ids, the
Ministry scans, the file-backed booklet components and the reading
sequence (topic chapters). Everything derived from it (page ranges, totals,
bookmark count, the HTML reading order) is compared here with:

- the files on disk (HTML <-> PDF, scans, booklet component PDFs);
- the homepage catalog, the originals catalog and the official viewer;
- the printed table of contents (book/front.html), the introduction and
  the continuous reading page (book/complete.html), all regenerated from the
  manifest by scripts/sync_book_docs.py;
- README.md and SOURCE_OF_TRUTH.md totals;
- the built PDFs: page counts of every component and of the merged booklet,
  the page order (every page traced back to its source page), bookmark
  titles, targets and count, and page orientation.

A new worksheet that is added to only one of these places, a duplicate id,
a wrong order or a stale page number stops the build here.
"""
from pathlib import Path
import json
import os
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest as M  # noqa: E402
import sync_book_docs  # noqa: E402
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


def check_derived_blocks():
    """Table of contents, chapter table and the HTML reading sequence are generated, never typed."""
    stale = sync_book_docs.check()
    demand(not stale, f"Derived blocks differ from the manifest: {stale} (python scripts/sync_book_docs.py --write)")
    front = read("book/front.html")
    for chapter, first, last in M.layout():
        if "part" not in chapter:
            continue
        demand(f'<span class="pg">{first}–{last}</span>' in front,
               f"book/front.html table of contents lacks pages {first}–{last} for part {chapter['part']}")
    demand(f"{M.TOTAL_PAGES} עמודים" in front and f"{M.TOTAL_BOOKMARKS} סימניות" in front,
           "front.html must state the manifest-derived page and bookmark totals")
    intro = read("book/INTRO.md")
    for chapter, first, last in M.layout():
        if "part" in chapter:
            demand(re.search(rf"^\| {re.escape(chapter['part'])} — [^|]*\| {first}–{last} \|", intro, re.M),
                   f"book/INTRO.md part table lacks '{chapter['part']} … | {first}–{last} |'")


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
    demand(f"{len(M.ORIGINAL)} דפי עבודה מקוריים" in index and f"{len(M.IMPORTED)} דפים נוספים" in index,
           "index.html source filters must show the manifest's original/imported counts")
    demand(f"{len(M.ORIGINAL)} דפי" in readme and f"{len(M.ORIGINAL)} דפים" in readme, "README originals count")
    demand(f"| **סה״כ דפי עבודה** | **{len(M.WORKSHEETS)} דפי HTML ו־{len(M.WORKSHEETS)} PDF** |" in sot,
           "SOURCE_OF_TRUTH inventory table total differs from manifest")
    demand(f"**{M.TOTAL_PAGES} עמודים, {M.TOTAL_BOOKMARKS} סימניות PDF**" in sot,
           "SOURCE_OF_TRUTH booklet row differs from manifest")
    demand(M.numbering_sentence() in sot,
           "SOURCE_OF_TRUTH page numbering sentence differs from the manifest layout: expected\n" + M.numbering_sentence())


def check_continuous_book():
    """The public reading page must contain the complete inventory in one vertical flow,
    in exactly the manifest's order (the same order as the printed booklet)."""
    html = read(M.BOOK_HTML)
    line = next((row for row in html.splitlines() if row.startswith("const ORDER=")), None)
    demand(line is not None and line.endswith(";"), "Continuous booklet lacks a machine-readable reading sequence")
    sequence = json.loads(line[len("const ORDER="):-1])
    demand(sequence == M.reading_sequence(),
           f"{M.BOOK_HTML} reading order differs from the manifest's printed order")
    chapters = next((row for row in html.splitlines() if row.startswith("const CHAPTERS=")), None)
    demand(chapters is not None and json.loads(chapters[len("const CHAPTERS="):-1]) == M.html_chapters(),
           f"{M.BOOK_HTML} chapter headings differ from the manifest chapters")
    demand(M.MINISTRY_HEADING in html and "overflow-x:hidden" in html,
           "Reading flow must label original Ministry scans and avoid horizontal scrolling")
    demand("id=\"loading\"" in html and "new DOMParser" in html,
           "Teacher summaries must be loaded into the same continuous document")
    demand(f"summaries.size!=={M.SUMMARY_COUNT}" in html, "Continuous page must insist on every teacher summary")


def flatten(items):
    for item in items:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item


def page_fingerprint(page):
    """Something cheap that identifies a page's content: the set of image object
    names plus the page text without whitespace (text extraction order is stable
    for one and the same page, whitespace is not)."""
    resources = page.get("/Resources") or {}
    images = tuple(sorted(str(k) for k in (resources.get("/XObject") or {}).keys()))
    text = re.sub(r"\s+", "", page.extract_text() or "")
    return images, text


def same_page(got, want, number):
    """A booklet page equals its source page, except that the running page number
    stamped on it may add that number (and only that number) to the text.
    On a short page the stamp used to change the first 400 characters."""
    got_images, got_text = page_fingerprint(got)
    want_images, want_text = page_fingerprint(want)
    if got_images != want_images:
        return False
    if got_text == want_text:
        return True
    stamp, start = str(number), 0
    while (at := got_text.find(stamp, start)) >= 0:
        if got_text[:at] + got_text[at + len(stamp):] == want_text:
            return True
        start = at + 1
    return False


def check_pdfs():
    for key, component in M.COMPONENTS.items():
        count = len(PdfReader(str(ROOT / component["file"])).pages)
        demand(count == M.component_pages(key), f"{component['file']} has {count} pages, manifest says {M.component_pages(key)}")
    for ident in M.WORKSHEETS:
        count = len(PdfReader(str(ROOT / "pdf" / f"{ident}.pdf")).pages)
        demand(count == M.WORKSHEET_PAGES[ident], f"pdf/{ident}.pdf has {count} pages, manifest says {M.WORKSHEET_PAGES[ident]}")
    book = PdfReader(str(ROOT / M.BOOK_FILE))
    demand(len(book.pages) == M.TOTAL_PAGES, f"{M.BOOK_FILE} has {len(book.pages)} pages, manifest derives {M.TOTAL_PAGES}")
    bookmarks = list(flatten(book.outline))
    demand(len(bookmarks) == M.TOTAL_BOOKMARKS, f"{M.BOOK_FILE} has {len(bookmarks)} bookmarks, manifest derives {M.TOTAL_BOOKMARKS}")
    summaries = M.summary_titles()
    expected = []
    for chapter, first, _ in M.layout():
        expected.append((M.chapter_title(chapter), first))
        page = first
        for item in chapter["items"]:
            if len(chapter["items"]) > 1:
                expected.append((M.item_title(item, summaries), page))
            page += M.item_pages(item)
    actual = [(b.title, book.get_destination_page_number(b) + 1) for b in bookmarks]
    demand(actual == expected, "Booklet bookmarks (titles, order or target pages) differ from the manifest sequence")
    for ident in M.WORKSHEETS:
        demand(any(M.TITLES[ident] in t for t, _ in actual), f"Booklet bookmark missing for {ident} ({M.TITLES[ident]})")
    # Every booklet page must be the page the manifest says, taken from its source PDF.
    readers = {}
    for number, chapter, item, offset in M.page_map():
        kind, ident = item
        if kind == "s":
            source, index = "book/teacher.pdf", ident - 1
        elif kind == "m":
            source, index = "book/official.pdf", M.MINISTRY_PAGES.index(ident)
        elif kind == "w":
            source, index = f"pdf/{ident}.pdf", offset
        else:
            source, index = M.COMPONENTS[ident]["file"], offset
        readers.setdefault(source, PdfReader(str(ROOT / source)))
        got = book.pages[number - 1]
        want = readers[source].pages[index]
        demand(same_page(got, want, number),
               f"Booklet page {number} is not {source} page {index + 1} ({item})")
        landscape = float(got.mediabox.width) > float(got.mediabox.height)
        demand(landscape == (kind == "m"), f"Booklet page {number}: unexpected orientation for {item}")
    # Links inside the published PDFs must work for a reader, not only on the build machine.
    for pdf in [c["file"] for c in M.COMPONENTS.values()] + [M.BOOK_FILE]:
        for page in PdfReader(str(ROOT / pdf)).pages:
            for annot in page.get("/Annots") or []:
                action = annot.get_object().get("/A")
                uri = str(action["/URI"]) if action is not None and action.get("/URI") else ""
                demand(not uri or uri.startswith(("https://", "http://", "mailto:")),
                       f"{pdf} contains a link that only resolves on the build machine: {uri}")


def main():
    check_files()
    check_catalogs()
    check_derived_blocks()
    check_documents()
    check_continuous_book()
    if os.environ.get("CHECK_BUILT_PDFS", "1") == "0":
        # Set by the check workflow on push/pull_request, where committed PDFs
        # may lag behind the sources until the build workflow republishes them.
        print("SKIPPED built-PDF checks (CHECK_BUILT_PDFS=0); the build workflow checks fresh PDFs")
    else:
        check_pdfs()
    built = "built PDFs (page order traced to source pages)" if os.environ.get("CHECK_BUILT_PDFS", "1") != "0" else "PDF file names"
    print(f"PASS: manifest agrees with files, catalogs, contents, reading order, README, SOURCE_OF_TRUTH and {built} "
          f"({len(M.WORKSHEETS)} worksheets, {len(M.MINISTRY_PAGES)} scans, {len(M.CHAPTERS)} chapters, "
          f"{M.TOTAL_PAGES} pages, {M.TOTAL_BOOKMARKS} bookmarks)")


if __name__ == "__main__":
    main()
