#!/usr/bin/env python3
"""Regenerate (or check) every text block that is derived from data/manifest.json.

Derived blocks live between markers inside hand-written files, so the
surrounding prose stays editable while the inventory-driven parts are never
typed by hand:

- book/front.html      <!-- toc:start --> … <!-- toc:end -->       printed table of contents
- book/INTRO.md        <!-- chapters:start --> … <!-- chapters:end --> chapter table
- book/complete.html   the `const ORDER=` and `const CHAPTERS=` lines   reading sequence

Usage: python scripts/sync_book_docs.py --check   (exit 1 and list stale files)
       python scripts/sync_book_docs.py --write   (rewrite the blocks in place)
"""
from pathlib import Path
import json
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest as M  # noqa: E402

ROOT = M.ROOT


def toc_block():
    rows = []
    for chapter, first, last in M.layout():
        if "part" not in chapter:
            continue
        rows.append(f'<div class="navrow"><div><strong>{M.chapter_title(chapter)}</strong>'
                    f'<small>{M.chapter_summary(chapter)}</small></div><span class="pg">{first}–{last}</span></div>')
    rows.append(f'<p class="total">סך הכול {M.TOTAL_PAGES} עמודים ו־{M.TOTAL_BOOKMARKS} סימניות ניווט; '
                f'עמודים 1–2 הם השער ותוכן העניינים. כל עמוד נושא מספר רץ, מלבד צילומי המקור שנשמרים ללא תוספת.</p>')
    return "\n".join(rows)


def chapters_table():
    lines = ["| חלק | עמודים בחוברת | תכולה |", "|---|---:|---|"]
    for chapter, first, last in M.layout():
        if "part" not in chapter:
            continue
        lines.append(f"| {chapter['part']} — {chapter['label']} | {first}–{last} | {M.chapter_summary(chapter)} |")
    return "\n".join(lines)


def order_line():
    return "const ORDER=" + json.dumps(M.reading_sequence(), ensure_ascii=False, separators=(",", ":")) + ";"


def chapters_line():
    return "const CHAPTERS=" + json.dumps(M.html_chapters(), ensure_ascii=False, separators=(",", ":")) + ";"


def replace_between(text, start, end, body, name):
    pattern = re.compile(re.escape(start) + r"[\s\S]*?" + re.escape(end))
    if not pattern.search(text):
        raise AssertionError(f"{name}: markers {start!r} … {end!r} missing")
    return pattern.sub(lambda _: start + "\n" + body + "\n" + end, text, count=1)


def replace_line(text, prefix, line, name):
    pattern = re.compile(r"^" + re.escape(prefix) + r"[^\n]*$", re.M)
    if len(pattern.findall(text)) != 1:
        raise AssertionError(f"{name}: expected exactly one line starting with {prefix!r}")
    return pattern.sub(lambda _: line, text, count=1)


def targets():
    """{relative path: function(current text) -> text with fresh derived blocks}"""
    return {
        "book/front.html": lambda t: replace_between(t, "<!-- toc:start -->", "<!-- toc:end -->", toc_block(), "book/front.html"),
        "book/INTRO.md": lambda t: replace_between(t, "<!-- chapters:start -->", "<!-- chapters:end -->", chapters_table(), "book/INTRO.md"),
        M.BOOK_HTML: lambda t: replace_line(replace_line(t, "const ORDER=", order_line(), M.BOOK_HTML),
                                            "const CHAPTERS=", chapters_line(), M.BOOK_HTML),
    }


def check():
    """Names of files whose derived blocks differ from the manifest."""
    stale = []
    for rel, refresh in targets().items():
        current = (ROOT / rel).read_text(encoding="utf-8")
        if refresh(current) != current:
            stale.append(rel)
    return stale


def write():
    changed = []
    for rel, refresh in targets().items():
        path = ROOT / rel
        current = path.read_text(encoding="utf-8")
        fresh = refresh(current)
        if fresh != current:
            path.write_text(fresh, encoding="utf-8", newline="\n")
            changed.append(rel)
    return changed


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode == "--write":
        changed = write()
        print("Rewrote: " + (", ".join(changed) if changed else "nothing (already current)"))
    else:
        stale = check()
        if stale:
            print("STALE derived blocks: " + ", ".join(stale) + " — run python scripts/sync_book_docs.py --write")
            sys.exit(1)
        print(f"PASS: table of contents, chapter table and reading sequence match data/manifest.json "
              f"({len(M.LETTERED_CHAPTERS)} lettered chapters, {M.TOTAL_PAGES} pages)")
