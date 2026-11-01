#!/usr/bin/env python3
"""Single technical inventory for build and QA scripts.

Reads data/manifest.json and derives everything the scripts used to hard-code:
worksheet ids and order, Ministry page list, booklet part order, page ranges,
total pages and bookmark count. SOURCE_OF_TRUTH.md remains the only place for
requirements and decisions; this module only exposes the inventory that the
published files must match.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "manifest.json"
DATA = json.loads(PATH.read_text(encoding="utf-8"))

ORIGINAL = tuple(w["id"] for w in DATA["worksheets"]["original"])
IMPORTED = tuple(w["id"] for w in DATA["worksheets"]["imported"])
WORKSHEETS = ORIGINAL + IMPORTED
TITLES = {w["id"]: w["title"] for group in DATA["worksheets"].values() for w in group}
WORKSHEET_PAGES = {w["id"]: w["pages"] for group in DATA["worksheets"].values() for w in group}
MINISTRY_PAGES = tuple(DATA["ministry"]["pages"])
BASE_URL = DATA["site"]["base_url"]
ROOT_PAGES = tuple(DATA["site"]["root_pages"])
BOOK_FILE = DATA["book"]["file"]
SADNA_CREDIT = next(p["credit"] for p in DATA["book"]["parts"] if p["key"] == "sadna")


def ministry_file(page):
    return ROOT / DATA["ministry"]["source_dir"] / DATA["ministry"]["file_pattern"].format(page=page)


def part_pages(part):
    """Number of A4 pages a booklet part contributes."""
    pages = part["pages"]
    if pages == "ministry":
        return len(MINISTRY_PAGES)
    if pages == "worksheets.original":
        return sum(WORKSHEET_PAGES[i] for i in ORIGINAL)
    if pages == "worksheets.imported":
        return sum(WORKSHEET_PAGES[i] for i in IMPORTED)
    return int(pages)


def part_bookmarks(part):
    """Bookmarks a part adds: one per worksheet, otherwise one per part."""
    if part["pages"] == "worksheets.original":
        return len(ORIGINAL)
    if part["pages"] == "worksheets.imported":
        return len(IMPORTED)
    return 1


def layout():
    """Ordered list of (part, first_page, last_page) for the merged booklet."""
    out = []
    page = 1
    for part in DATA["book"]["parts"]:
        count = part_pages(part)
        out.append((part, page, page + count - 1))
        page += count
    return out


PARTS = {part["key"]: (part, first, last) for part, first, last in layout()}
TOTAL_PAGES = sum(part_pages(p) for p in DATA["book"]["parts"])
TOTAL_BOOKMARKS = sum(part_bookmarks(p) for p in DATA["book"]["parts"])


def page_range(key):
    """'17–24' style range as printed in the table of contents."""
    _, first, last = PARTS[key]
    return f"{first}–{last}"


def validate():
    """Internal consistency: unique ids, every worksheet has HTML and PDF, files named in parts exist."""
    ids = list(WORKSHEETS)
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise AssertionError(f"Duplicate worksheet id in manifest: {sorted(duplicates)}")
    for ident in ids:
        for rel in (f"worksheets/{ident}.html", f"pdf/{ident}.pdf"):
            if not (ROOT / rel).is_file():
                raise AssertionError(f"Manifest lists {ident} but {rel} is missing")
    for page in MINISTRY_PAGES:
        if not ministry_file(page).is_file():
            raise AssertionError(f"Manifest lists Ministry page {page} but its scan is missing")
    for part in DATA["book"]["parts"]:
        if "file" in part and not (ROOT / part["file"]).is_file():
            raise AssertionError(f"Booklet part {part['key']} names missing file {part['file']}")
    keys = [p["key"] for p in DATA["book"]["parts"]]
    if len(set(keys)) != len(keys):
        raise AssertionError("Duplicate booklet part key")
    return True


if __name__ == "__main__":
    validate()
    for part, first, last in layout():
        print(f"{first:02d}–{last:02d}  {part.get('part','  ')}  {part['label']}")
    print(f"{len(ORIGINAL)} original + {len(IMPORTED)} imported = {len(WORKSHEETS)} worksheets; "
          f"{len(MINISTRY_PAGES)} Ministry scans; booklet {TOTAL_PAGES} pages, {TOTAL_BOOKMARKS} bookmarks")
