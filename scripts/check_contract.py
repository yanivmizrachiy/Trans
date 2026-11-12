#!/usr/bin/env python3
"""Fail if the source of truth, the printed teacher pages or the shared footer drift.

The footer rule (SOURCE_OF_TRUTH.md, requirements 13-14) is checked here and only here:
every printed page carries both footer lines from data/manifest.json and the logo,
and no page carries the retired editing credit.
"""
import re
import manifest as M

ROOT = M.ROOT
demand = M.demand
RETIRED = "הדף נערך"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def check_footer(rel, pages):
    html = read(rel)
    demand(RETIRED not in html, f"{rel}: the editing credit is retired")
    for line in (M.FOOTER_CREDIT, M.FOOTER_DISTRICT, "assets/logo.png"):
        demand(html.count(line) == pages, f"{rel}: expected {line!r} once on each of its {pages} page(s), found {html.count(line)}")


def main():
    readme = read("README.md")
    sot = read("SOURCE_OF_TRUTH.md")
    demand("SOURCE_OF_TRUTH.md" in readme and len(readme) < 1500, "README only points to the source of truth")
    for marker in ("## דרישות", "## החלטות", "## עובדות"):
        demand(marker in sot, f"SOURCE_OF_TRUTH.md lacks {marker}")
    for line in (M.FOOTER_CREDIT, M.FOOTER_DISTRICT):
        demand(f"„{line}”" in sot, f"data/manifest.json footer line differs from SOURCE_OF_TRUTH.md requirement 14: {line}")

    teacher = read(M.TEACHER_HTML)
    summaries = re.findall(r'<article class="sheet" id="summary-(\d+)">([\s\S]*?)</article>', teacher)
    demand([int(n) for n, _ in summaries] == list(range(1, M.SUMMARY_COUNT + 1)),
           "Teacher summaries must be numbered in order and match the manifest")
    for n, body in summaries:
        header = re.search(r'<header class="head">(.*?)</header>', body, re.S)
        demand(header is not None and 'class="sub"' not in header.group(1),
               f"Teacher summary {n}: the header holds the topic name only")

    for ident in M.WORKSHEETS:
        check_footer(f"worksheets/{ident}.html", M.WORKSHEET_PAGES[ident])
    for key in ("teacher", "krispin-video", "sadna"):
        check_footer(M.COMPONENTS[key]["html"], M.component_pages(key))
    # book/official.html writes one footer template that its script repeats on every page.
    check_footer(M.COMPONENTS["official"]["html"], 1)
    print("PASS: source of truth, teacher pages and the shared footer agree")


if __name__ == "__main__":
    main()
