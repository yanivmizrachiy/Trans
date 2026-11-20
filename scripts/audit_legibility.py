#!/usr/bin/env python3
"""Fail when a figure label in the booklet can be read on the wrong spot.

Works on the built PDF, so it sees exactly what is printed:
  1. two short labels (vertex letters, axis numbers) that overlap each other;
  2. a short label printed over a vertex dot, which hides the dot or pairs it with the wrong letter.
Run after build_complete.py. Pass a PDF path to audit another file.
"""
import sys
import pymupdf as fitz
import manifest as M

SHORT = 3          # vertex letters (A, A′, P₁) and axis numbers (−4, 12)
DOT_MIN, DOT_MAX = 3, 4.5   # pt: vertex dots are 1.5 mm across (4.25 pt); dotted-grid points are smaller


def is_label(text):
    """Recognize a meaningful short figure label, not PDF bidi/punctuation fragments.

    Hebrew PDF extraction can expose RLM/LRM and quote marks as standalone
    one-character spans. Those are not labels and must not cause false overlap
    failures. Actual letter/number labels remain subject to both checks below.
    """
    t = text.strip()
    return bool(t and len(t) <= SHORT and any(ch.isalnum() for ch in t))


def spans(page):
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for s in line["spans"]:
                t = s["text"].strip()
                if is_label(t):
                    r = fitz.Rect(s["bbox"])
                    # the glyph box is taller than the ink: keep the middle 60 % of its height
                    pad = r.height * .2
                    box = fitz.Rect(r.x0 + .3, r.y0 + pad, r.x1 - .3, r.y1 - pad)
                    # a label with a white halo is printed twice (halo, then ink) at the same spot
                    # (sometimes glyph by glyph, so 'A' + '′' under 'A′'): one label, not two
                    if not any((t in u or u in t) and not (box & b).is_empty
                               and (box & b).get_area() > .4 * min(box.get_area(), b.get_area()) for u, b in out):
                        out.append((t, box))
    return out


def dots(page):
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if d.get("fill") and DOT_MIN <= r.width <= DOT_MAX and r.height <= DOT_MAX and abs(r.width - r.height) < .4 \
                and any(item[0] == "c" for item in d["items"]):
            out.append(fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    return out


def audit(path):
    problems = []
    doc = fitz.open(path)
    for n in range(1, len(doc) + 1):
        page = doc[n - 1]
        labels = spans(page)
        for i, (a, ra) in enumerate(labels):
            for b, rb in labels[i + 1:]:
                inter = ra & rb
                if not inter.is_empty and inter.get_area() > .15 * min(ra.get_area(), rb.get_area()):
                    problems.append(f"page {n}: labels '{a}' and '{b}' overlap")
            for p in dots(page):
                # the dot is 1.5 mm across: a label box that reaches within 1 pt of its centre covers it
                if fitz.Rect(ra.x0 - 1, ra.y0 - 1, ra.x1 + 1, ra.y1 + 1).contains(p):
                    problems.append(f"page {n}: label '{a}' covers a vertex dot at ({p.x:.0f},{p.y:.0f})")
    return problems


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else M.ROOT / M.BOOK_FILE
    problems = audit(path)
    if problems:
        print("\n".join(problems))
        raise SystemExit(f"FAIL: {len(problems)} figure label problems")
    print(f"PASS: no overlapping figure labels and no label over a vertex dot in {path}")


if __name__ == "__main__":
    main()
