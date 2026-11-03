"""Crop the top-left corner of chosen pages into one strip. Usage: python -P corners.py <pdf> <out.png> <pages...>"""
import sys
import fitz
from PIL import Image

d = fitz.open(sys.argv[1]); mm = 72 / 25.4
tiles = []
for n in map(int, sys.argv[3:]):
    pix = d[n - 1].get_pixmap(dpi=220, clip=fitz.Rect(0, 0, 60 * mm, 26 * mm), alpha=False)
    tiles.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
strip = Image.new("RGB", (max(t.width for t in tiles), sum(t.height + 8 for t in tiles)), "#999")
y = 0
for t in tiles:
    strip.paste(t, (0, y)); y += t.height + 8
strip.save(sys.argv[2])
