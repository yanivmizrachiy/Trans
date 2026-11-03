"""Check the published booklet. Usage: python -I live_check.py <pdf> <outdir>
Pages, bookmarks, one look for the series line, page 6's figures, the solid page-number disc."""
import sys
from pathlib import Path
import fitz
from PIL import Image

pdf, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(exist_ok=True)
d = fitz.open(pdf); mm = 72 / 25.4
print("pages", len(d), "bookmarks", len(d.get_toc()))
series = {}
for i, p in enumerate(d, 1):
    for b in p.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            w = set("".join(s["text"] for s in l["spans"]).replace("-", " ").split())
            if {"טרנספורמציות", "סיכומים", "למורה"} <= w:
                series.setdefault(i, set()).update((s["font"], round(s["size"], 1), s["color"]) for s in l["spans"] if s["text"].strip())
print("series line on", len(series), "pages:", sorted(series), "distinct looks:", len({frozenset(v) for v in series.values()}))
t6 = d[5].get_text()
print("page 6 figures:", all(k in t6 for k in ("שתי הדרכים מסתיימות באותו מקום", "הלב מחליק ונשאר באותו כיוון", "ימינה, ואז למעלה")))
dark_blue = lambda c: c[2] >= 80 and c[2] - c[0] >= 45 and c[0] <= 80 and c[1] <= 110
bad = []
for i, p in enumerate(d, 1):
    cx, cy, half, z = 17.9 * mm, 12 * mm, 4.5 * mm, 4
    pix = p.get_pixmap(matrix=fitz.Matrix(z, z), clip=fitz.Rect(cx - half, cy - half, cx + half, cy + half), alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ring = [im.getpixel((int((half + 3.2 * mm * c) * z), int((half + 3.2 * mm * s) * z)))
            for c, s in ((1, 0), (.7071, .7071), (0, 1), (-.7071, .7071), (-1, 0), (-.7071, -.7071), (0, -1), (.7071, -.7071))]
    words = [w[4] for w in p.get_text("words", clip=fitz.Rect(0, 0, 26 * mm, 19 * mm))]
    if not all(dark_blue(c) for c in ring) or words != [str(i)]:
        bad.append(i)
print("pages without the solid disc number:", bad or "none")
for n in (6, 13, 44, 59):
    d[n - 1].get_pixmap(dpi=60).save(out / f"live-{n:02d}.png")
