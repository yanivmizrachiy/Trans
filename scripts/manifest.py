#!/usr/bin/env python3
"""Single technical inventory for the build and QA scripts.

Reads data/manifest.json and derives what the scripts need: worksheet ids and
titles, the Ministry pages, the shared footer, the booklet's reading sequence,
page ranges, total pages and bookmarks. SOURCE_OF_TRUTH.md remains the only
place for requirements and decisions; this module only exposes the inventory
that the published files must match.

Sequence items are two-element lists exactly as written in the manifest:
  ["s", n]   teacher summary n (page n of book/teacher.pdf)
  ["m", p]   Ministry source page p (one page of book/official.pdf)
  ["w", id]  worksheet id (pdf/<id>.pdf, one or more pages)
  ["c", key] file-backed component (book/<key>.pdf, all of its pages)
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "manifest.json"
DATA = json.loads(PATH.read_text(encoding="utf-8"))

ORIGINAL = tuple(w["id"] for w in DATA["worksheets"]["original"])
IMPORTED = tuple(w["id"] for w in DATA["worksheets"]["imported"])
WORKSHEETS = ORIGINAL + IMPORTED
TITLES = {w["id"]: w["title"] for group in DATA["worksheets"].values() for w in group}
WORKSHEET_PAGES = {w["id"]: w["pages"] for group in DATA["worksheets"].values() for w in group}
WORKSHEET_SOURCE = {w["id"]: w.get("source", "original") for group in DATA["worksheets"].values() for w in group}
MINISTRY_PAGES = tuple(DATA["ministry"]["pages"])
MINISTRY_DIR = ROOT / DATA["ministry"]["source_dir"]
MINISTRY_HEADING = DATA["ministry"]["heading"]
BASE_URL = DATA["site"]["base_url"]
ROOT_PAGES = tuple(DATA["site"]["root_pages"])
FOOTER_CREDIT = DATA["footer"]["credit"]
FOOTER_DISTRICT = DATA["footer"]["district"]
BOOK_FILE = DATA["book"]["file"]
BOOK_HTML = DATA["book"]["html"]
COMPONENTS = DATA["book"]["components"]
CHAPTERS = DATA["book"]["chapters"]
TEACHER_HTML = COMPONENTS["teacher"]["html"]
SUMMARY_COUNT = int(COMPONENTS["teacher"]["pages"])


def demand(test, reason):
    """Assertion that survives `python -O`."""
    if not test:
        raise AssertionError(reason)


def flatten(outline):
    """Every bookmark of a pypdf outline, nested ones included, in order."""
    for item in outline:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item


def ministry_file(page):
    return MINISTRY_DIR / DATA["ministry"]["file_pattern"].format(page=page)


def component_pages(key):
    """Number of A4 pages a file-backed component contributes."""
    pages = COMPONENTS[key]["pages"]
    if pages == "ministry":
        return len(MINISTRY_PAGES)
    return int(pages)


def item_pages(item):
    kind, ident = item
    if kind in ("s", "m"):
        return 1
    if kind == "w":
        return WORKSHEET_PAGES[ident]
    if kind == "c":
        return component_pages(ident)
    raise ValueError(f"Unknown sequence item {item!r}")


def item_source(item):
    """(part PDF relative to ROOT, zero-based page indices) that one sequence item takes."""
    kind, ident = item
    if kind == "s":
        return COMPONENTS["teacher"]["file"], [ident - 1]
    if kind == "m":
        return COMPONENTS["official"]["file"], [MINISTRY_PAGES.index(ident)]
    if kind == "w":
        return f"pdf/{ident}.pdf", list(range(WORKSHEET_PAGES[ident]))
    return COMPONENTS[ident]["file"], list(range(component_pages(ident)))


def sequence():
    """Every item of the booklet, in reading order."""
    return [list(item) for chapter in CHAPTERS for item in chapter["items"]]


def chapter_pages(chapter):
    return sum(item_pages(item) for item in chapter["items"])


def layout():
    """Ordered list of (chapter, first_page, last_page) for the merged booklet."""
    out = []
    page = 1
    for chapter in CHAPTERS:
        count = chapter_pages(chapter)
        out.append((chapter, page, page + count - 1))
        page += count
    return out


def page_map():
    """Ordered list of (page_number, chapter, item, page_within_item) for every booklet page."""
    out = []
    page = 1
    for chapter in CHAPTERS:
        for item in chapter["items"]:
            for k in range(item_pages(item)):
                out.append((page, chapter, list(item), k))
                page += 1
    return out


def item_bookmarks(chapter):
    """Items that get their own nested bookmark: every item of a chapter with more than one item."""
    return list(chapter["items"]) if len(chapter["items"]) > 1 else []


TOTAL_PAGES = sum(chapter_pages(c) for c in CHAPTERS)
TOTAL_BOOKMARKS = sum(1 + len(item_bookmarks(c)) for c in CHAPTERS)


def summary_titles():
    """Titles of the numbered teacher summaries, read from book/teacher.html."""
    html = (ROOT / TEACHER_HTML).read_text(encoding="utf-8")
    found = {}
    for number, body in re.findall(r'<article class="sheet" id="summary-(\d+)">([\s\S]*?)</article>', html):
        heading = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", body)
        found[int(number)] = re.sub(r"<[^>]+>", "", heading.group(1)).strip() if heading else ""
    if sorted(found) != list(range(1, SUMMARY_COUNT + 1)) or not all(found.values()):
        raise AssertionError(f"{TEACHER_HTML} does not contain summaries 1–{SUMMARY_COUNT} with headings")
    return found


def item_title(item, summaries=None):
    """Bookmark text of one sequence item."""
    kind, ident = item
    if kind == "s":
        summaries = summaries or summary_titles()
        return f"סיכום {ident} — {summaries[ident]}"
    if kind == "m":
        return f"{MINISTRY_HEADING} — עמוד {ident}"
    if kind == "w":
        return TITLES[ident]
    return COMPONENTS[ident]["label"]


def bookmarks():
    """(title, first page) of every booklet bookmark, in outline order."""
    summaries = summary_titles()
    out = []
    for chapter, first, _ in layout():
        out.append((chapter["label"], first))
        page = first
        for item in chapter["items"]:
            if len(chapter["items"]) > 1:
                out.append((item_title(item, summaries), page))
            page += item_pages(item)
    return out


def validate():
    """Internal consistency: unique ids, every worksheet has HTML, files named in components exist,
    and the reading sequence lists every summary, Ministry page, worksheet and component exactly once."""
    ids = list(WORKSHEETS)
    duplicates = {i for i in ids if ids.count(i) > 1}
    demand(not duplicates, f"Duplicate worksheet id in manifest: {sorted(duplicates)}")
    for ident in ids:
        demand((ROOT / f"worksheets/{ident}.html").is_file(), f"Manifest lists {ident} but worksheets/{ident}.html is missing")
    for page in MINISTRY_PAGES:
        demand(ministry_file(page).is_file(), f"Manifest lists Ministry page {page} but its scan is missing")
    for key, component in COMPONENTS.items():
        rel = component.get("source") or component["html"]
        demand((ROOT / rel).is_file(), f"Booklet component {key} names missing file {rel}")
    keys = [c["key"] for c in CHAPTERS]
    demand(len(set(keys)) == len(keys), "Duplicate booklet chapter key")
    items = sequence()
    demand(all(isinstance(i, list) and len(i) == 2 for i in items), "Malformed sequence item in manifest chapters")
    expected = {
        "s": set(range(1, SUMMARY_COUNT + 1)),
        "m": set(MINISTRY_PAGES),
        "w": set(WORKSHEETS),
        # teacher and official are consumed page by page through s/m items, never whole.
        "c": {k for k in COMPONENTS if k not in ("teacher", "official")},
    }
    for kind, wanted in expected.items():
        listed = [ident for k, ident in items if k == kind]
        demand(len(listed) == len(wanted) and set(listed) == wanted,
               f"Reading sequence lists {kind!r} items {sorted(map(str, listed))}, "
               f"manifest inventory is {sorted(map(str, wanted))}")
    demand(items[-1] == ["c", "answers"], "The answer key must close the booklet")
    return True


if __name__ == "__main__":
    validate()
    for chapter, first, last in layout():
        print(f"{first:02d}–{last:02d}  {chapter['label']}")
    print(f"{len(ORIGINAL)} original + {len(IMPORTED)} imported = {len(WORKSHEETS)} worksheets; "
          f"{len(MINISTRY_PAGES)} Ministry scans; {SUMMARY_COUNT} teacher summaries; "
          f"booklet {TOTAL_PAGES} pages, {TOTAL_BOOKMARKS} bookmarks, {len(CHAPTERS)} chapters")
