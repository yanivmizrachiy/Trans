#!/usr/bin/env python3
"""Single technical inventory for build and QA scripts.

Reads data/manifest.json and derives everything the scripts used to hard-code:
worksheet ids and order, Ministry page list, the booklet's reading sequence
(the same for book/complete.html and book/transformations-complete.pdf), the
topic chapters, page ranges, total pages and bookmark count.
SOURCE_OF_TRUTH.md remains the only place for requirements and decisions;
this module only exposes the inventory that the published files must match.

Sequence items are two-element lists exactly as written in the manifest:
  ["s", n]   numbered teacher summary n (one page of book/teacher.pdf)
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
MINISTRY_HEADING = DATA["ministry"]["heading"]
BASE_URL = DATA["site"]["base_url"]
ROOT_PAGES = tuple(DATA["site"]["root_pages"])
BOOK_FILE = DATA["book"]["file"]
BOOK_HTML = DATA["book"]["html"]
COMPONENTS = DATA["book"]["components"]
CHAPTERS = DATA["book"]["chapters"]
SUMMARY_COUNT = int(DATA["teacher"]["summaries"])
SADNA_CREDIT = COMPONENTS["sadna"]["credit"]


def ministry_file(page):
    return ROOT / DATA["ministry"]["source_dir"] / DATA["ministry"]["file_pattern"].format(page=page)


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


def print_sequence():
    """Every item of the merged PDF, in reading order (includes the cover)."""
    return [list(item) for chapter in CHAPTERS for item in chapter["items"]]


def chapter_pages(chapter):
    return sum(item_pages(item) for item in chapter["items"])


def chapter_title(chapter):
    return chapter["label"]


def chapter_summary(chapter):
    """Short derived description of a chapter's contents for the table of contents."""
    counts = {"s": 0, "m": [], "w": 0, "c": []}
    for kind, ident in chapter["items"]:
        if kind == "s":
            counts["s"] += 1
        elif kind == "m":
            counts["m"].append(ident)
        elif kind == "w":
            counts["w"] += 1
        else:
            counts["c"].append(COMPONENTS[ident]["label"])
    bits = []
    if counts["s"]:
        bits.append("סיכום אחד למורה" if counts["s"] == 1 else f"{counts['s']} סיכומים למורה")
    if counts["m"]:
        pages = ", ".join(str(p) for p in counts["m"])
        bits.append(f"{MINISTRY_HEADING} — עמוד {pages}" if len(counts["m"]) == 1
                    else f"{MINISTRY_HEADING} — עמודים {pages}")
    if counts["w"]:
        bits.append("דף עבודה אחד" if counts["w"] == 1 else f"{counts['w']} דפי עבודה")
    bits.extend(counts["c"])
    return " · ".join(bits)


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


CHAPTER_RANGES = {chapter["key"]: (first, last) for chapter, first, last in layout()}
TOTAL_PAGES = sum(chapter_pages(c) for c in CHAPTERS)
TOTAL_BOOKMARKS = sum(1 + len(item_bookmarks(c)) for c in CHAPTERS)
# Chapters carry no part letters; the booklet has no cover page.
CONTENT_CHAPTERS = list(CHAPTERS)


def page_range(key):
    """'17–24' style range as printed in the table of contents."""
    first, last = CHAPTER_RANGES[key]
    return f"{first}–{last}"


def summary_titles():
    """Titles of the numbered teacher summaries, read from book/teacher.html."""
    html = (ROOT / DATA["teacher"]["html"]).read_text(encoding="utf-8")
    found = {}
    for number, body in re.findall(r'<article class="sheet" id="summary-(\d+)">([\s\S]*?)</article>', html):
        heading = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", body)
        found[int(number)] = re.sub(r"<[^>]+>", "", heading.group(1)).strip() if heading else ""
    if sorted(found) != list(range(1, SUMMARY_COUNT + 1)) or not all(found.values()):
        raise AssertionError(f"{DATA['teacher']['html']} does not contain summaries 1–{SUMMARY_COUNT} with headings")
    return found


def item_title(item, summaries=None):
    """Bookmark / heading text of one sequence item."""
    kind, ident = item
    if kind == "s":
        summaries = summaries or summary_titles()
        return f"סיכום {ident} — {summaries[ident]}"
    if kind == "m":
        return f"{MINISTRY_HEADING} — עמוד {ident}"
    if kind == "w":
        return TITLES[ident]
    return COMPONENTS[ident]["label"]





def validate():
    """Internal consistency: unique ids, every worksheet has HTML and PDF, files named in parts exist,
    and the reading sequence lists every summary, Ministry page, worksheet and component exactly once."""
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
    for key, component in COMPONENTS.items():
        for rel in (component["file"], component["html"]):
            if not (ROOT / rel).is_file():
                raise AssertionError(f"Booklet component {key} names missing file {rel}")
    keys = [c["key"] for c in CHAPTERS]
    if len(set(keys)) != len(keys):
        raise AssertionError("Duplicate booklet chapter key")
    sequence = print_sequence()
    if any(not (isinstance(i, list) and len(i) == 2) for i in sequence):
        raise AssertionError("Malformed sequence item in manifest chapters")
    expected = {
        "s": set(range(1, SUMMARY_COUNT + 1)),
        "m": set(MINISTRY_PAGES),
        "w": set(WORKSHEETS),
        # teacher and official are consumed page by page through s/m items, never whole.
        "c": {k for k in COMPONENTS if k not in ("teacher", "official")},
    }
    for kind, wanted in expected.items():
        listed = [ident for k, ident in sequence if k == kind]
        if len(listed) != len(wanted) or set(listed) != wanted:
            raise AssertionError(f"Reading sequence lists {kind!r} items {sorted(map(str, listed))}, "
                                 f"manifest inventory is {sorted(map(str, wanted))}")
    if sequence[-1] != ["c", "answers"]:
        raise AssertionError("Teacher solutions must close the booklet")
    if component_pages("teacher") != SUMMARY_COUNT:
        raise AssertionError("teacher component pages differ from the summary count")
    return True


if __name__ == "__main__":
    validate()
    for chapter, first, last in layout():
        print(f"{first:02d}–{last:02d}  {chapter['label']}  [{chapter_summary(chapter)}]")
    print(f"{len(ORIGINAL)} original + {len(IMPORTED)} imported = {len(WORKSHEETS)} worksheets; "
          f"{len(MINISTRY_PAGES)} Ministry scans; {SUMMARY_COUNT} teacher summaries; "
          f"booklet {TOTAL_PAGES} pages, {TOTAL_BOOKMARKS} bookmarks, {len(CHAPTERS)} chapters")
