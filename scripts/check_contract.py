#!/usr/bin/env python3
"""Fail if the source of truth, the printed teacher pages or the attribution rules drift."""
import re
import manifest as M

ROOT = M.ROOT
SOT = (ROOT / "SOURCE_OF_TRUTH.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
CREDIT = 'יניב רז - מדריך מחוזי חט"ב בעיר ירושלים'
RETIRED = "הדף נערך"


def demand(test, reason):
    if not test:
        raise AssertionError(reason)


def main():
    demand("SOURCE_OF_TRUTH.md" in README and len(README) < 1500, "README only points to the source of truth")
    for marker in ("## דרישות", "## החלטות", "## עובדות"):
        demand(marker in SOT, f"SOURCE_OF_TRUTH.md lacks {marker}")
    teacher = (ROOT / "book" / "teacher.html").read_text(encoding="utf-8")
    summaries = re.findall(r'<article class="sheet" id="summary-(\d+)">([\s\S]*?)</article>', teacher)
    demand([int(n) for n, _ in summaries] == list(range(1, M.DATA["teacher"]["summaries"] + 1)),
           "Teacher summaries must be numbered in order and match the manifest")
    for n, body in summaries:
        header = re.search(r'<header class="head">(.*?)</header>', body, re.S).group(1)
        demand('class="sub"' not in header, f"Teacher summary {n}: the header holds the topic name only")
    for ident in M.ORIGINAL:
        html = (ROOT / "worksheets" / f"{ident}.html").read_text(encoding="utf-8")
        demand(CREDIT in html and "../assets/logo.png" in html, f"Original worksheet lost its credit: {ident}")
    for ident in M.IMPORTED:
        html = (ROOT / "worksheets" / f"{ident}.html").read_text(encoding="utf-8")
        demand(RETIRED not in html and html.count(CREDIT) == M.WORKSHEET_PAGES[ident] and html.count("assets/logo.png") == M.WORKSHEET_PAGES[ident],
               f"Imported worksheet has one shared footer per page: {ident}")
    official = (ROOT / "book" / "official.html").read_text(encoding="utf-8")
    demand(RETIRED not in official and CREDIT in official, "Curriculum pages carry the shared footer and no editing credit")
    sadna = (ROOT / "book" / "sadna.html").read_text(encoding="utf-8")
    demand(sadna.count(M.SADNA_CREDIT) == M.component_pages("sadna"), "Every teacher-lab page carries its author credit")
    print("PASS: source of truth, teacher pages and attribution agree")


if __name__ == "__main__":
    main()
