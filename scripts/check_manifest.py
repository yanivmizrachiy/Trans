#!/usr/bin/env python3
"""Fail if any consumer of the inventory disagrees with data/manifest.json.

The manifest is the one technical place that lists worksheet ids, the
Ministry scans, the file-backed booklet components and the reading
sequence (topic chapters). Everything derived from it (page ranges, totals,
bookmark count, the HTML reading order) is compared here with:

- the files on disk (HTML <-> PDF, scans, booklet component PDFs);
- the curriculum pages in book/official.html;
- the continuous reading page (book/complete.html);
- the built PDFs: page counts of every component and of the merged booklet,
  the page order (every page traced back to its source page), bookmark
  titles, targets and count, and page orientation.

A new worksheet that is added to only one of these places, a duplicate id,
a wrong order or a stale page number stops the build here.
"""
from pathlib import Path
import os
import re

from pypdf import PdfReader
import manifest as M

ROOT = M.ROOT
demand = M.demand


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def check_files():
    M.validate()
    html_ids = {p.stem for p in (ROOT / "worksheets").glob("*.html")}
    demand(html_ids == set(M.WORKSHEETS), f"worksheets/ differs from manifest: {html_ids ^ set(M.WORKSHEETS)}")
    scans = {p.name for p in M.MINISTRY_DIR.glob("*.webp")}
    expected = {M.ministry_file(n).name for n in M.MINISTRY_PAGES}
    demand(scans == expected, f"sources/ministry differs from manifest: {scans ^ expected}")


def check_curriculum_pages():
    official = read("book/official.html")
    pages = re.findall(r'<article class="qpage" id="p(\d+)">', official)
    demand([int(n) for n in pages] == list(M.MINISTRY_PAGES), f"book/official.html pages {pages} differ from the manifest")


def check_continuous_book():
    """The public reading page shows the printed booklet PDF itself, page after page,
    so its order and content are the booklet's by construction; it adds no captions."""
    html = read(M.BOOK_HTML)
    pdf_name = Path(M.BOOK_FILE).name
    demand(f'const PDF="{pdf_name}";' in html, f"{M.BOOK_HTML} must render {M.BOOK_FILE}")
    demand("background:#c2185b" in html, f"{M.BOOK_HTML} pages must sit back to back with a burgundy divider")
    demand("100vw" not in html, f"{M.BOOK_HTML}: the divider is only as wide as the page")
    for tag in ("<h1", "<h2", "<header", "<footer", "<nav", "<figcaption"):
        demand(tag not in html, f"{M.BOOK_HTML} must not add captions or headings ({tag})")

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
    bookmarks = list(M.flatten(book.outline))
    demand(len(bookmarks) == M.TOTAL_BOOKMARKS, f"{M.BOOK_FILE} has {len(bookmarks)} bookmarks, manifest derives {M.TOTAL_BOOKMARKS}")
    actual = [(b.title, book.get_destination_page_number(b) + 1) for b in bookmarks]
    demand(actual == M.bookmarks(), "Booklet bookmarks (titles, order or target pages) differ from the manifest sequence")
    for ident in M.WORKSHEETS:
        demand(any(M.TITLES[ident] in t for t, _ in actual), f"Booklet bookmark missing for {ident} ({M.TITLES[ident]})")
    # Every booklet page must be the page the manifest says, taken from its source PDF.
    readers = {}
    for number, chapter, item, offset in M.page_map():
        source, indices = M.item_source(item)
        index = indices[offset]
        readers.setdefault(source, PdfReader(str(ROOT / source)))
        got = book.pages[number - 1]
        want = readers[source].pages[index]
        demand(same_page(got, want, number),
               f"Booklet page {number} is not {source} page {index + 1} ({item})")
        demand(float(got.mediabox.width) < float(got.mediabox.height), f"Booklet page {number}: not portrait A4 ({item})")
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
    check_curriculum_pages()
    check_continuous_book()
    # The check workflow sets CHECK_BUILT_PDFS=0: build outputs are not in Git,
    # and the build workflow runs this script again after building them.
    if os.environ.get("CHECK_BUILT_PDFS", "1") == "0":
        print("SKIPPED built-PDF checks (CHECK_BUILT_PDFS=0); the build workflow checks fresh PDFs")
        built = "the sources"
    else:
        check_pdfs()
        built = "the built PDFs (page order traced to source pages)"
    print(f"PASS: manifest agrees with {built} "
          f"({len(M.WORKSHEETS)} worksheets, {len(M.MINISTRY_PAGES)} curriculum pages, {len(M.CHAPTERS)} chapters, "
          f"{M.TOTAL_PAGES} pages, {M.TOTAL_BOOKMARKS} bookmarks)")


if __name__ == "__main__":
    main()
