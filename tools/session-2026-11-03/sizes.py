"""Page sizes (mm) and the page-map item of each page. Usage: python -P sizes.py <pdf> <repo>"""
import sys
import fitz

d = fitz.open(sys.argv[1]); mm = 72 / 25.4
sys.path.insert(0, sys.argv[2] + "/scripts")
import manifest as M
PAGE_MAP = {n: (chapter, item) for n, chapter, item, _ in M.page_map()}
for i, p in enumerate(d, 1):
    w, h = p.rect.width / mm, p.rect.height / mm
    flag = "" if abs(w - 210) < 1 and abs(h - 297) < 1 else "  <-- not A4"
    print(i, f"{w:.1f}x{h:.1f}", PAGE_MAP.get(i), flag)
