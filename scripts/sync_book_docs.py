#!/usr/bin/env python3
"""Regenerate (or check) every text block that is derived from data/manifest.json.

Derived blocks live between markers inside hand-written files, so the
surrounding prose stays editable while the inventory-driven parts are never
typed by hand:

- book/INTRO.md        <!-- chapters:start --> … <!-- chapters:end --> chapter table

Usage: python scripts/sync_book_docs.py --check   (exit 1 and list stale files)
       python scripts/sync_book_docs.py --write   (rewrite the blocks in place)
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest as M  # noqa: E402

ROOT = M.ROOT


def chapters_table():
    lines = ["| נושא | עמודים בחוברת | תכולה |", "|---|---:|---|"]
    for chapter, first, last in M.layout():
        if chapter["key"] == "front":
            continue
        lines.append(f"| {chapter['label']} | {first}–{last} | {M.chapter_summary(chapter)} |")
    return "\n".join(lines)


def replace_between(text, start, end, body, name):
    pattern = re.compile(re.escape(start) + r"[\s\S]*?" + re.escape(end))
    if not pattern.search(text):
        raise AssertionError(f"{name}: markers {start!r} … {end!r} missing")
    return pattern.sub(lambda _: start + "\n" + body + "\n" + end, text, count=1)


def targets():
    """{relative path: function(current text) -> text with fresh derived blocks}"""
    return {
        "book/INTRO.md": lambda t: replace_between(t, "<!-- chapters:start -->", "<!-- chapters:end -->", chapters_table(), "book/INTRO.md"),
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
        print(f"PASS: chapter table matches data/manifest.json "
              f"({len(M.CONTENT_CHAPTERS)} chapters, {M.TOTAL_PAGES} pages)")
