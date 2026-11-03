"""Crop the bottom of chosen pages into one strip. Usage: python -P bottoms.py <pdf> <out.png> <mm-from-bottom> <pages...>"""
import sys
import fitz
from PIL import Image, ImageDraw

d = fitz.open(sys.argv[1]); mm = 72 / 25.4; h = float(sys.argv[3])
tiles = []
for n in map(int, sys.argv[4:]):
    r = d[n - 1].rect
    pix = d[n - 1].get_pixmap(dpi=110, clip=fitz.Rect(0, r.height - h * mm, r.width, r.height), alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ImageDraw.Draw(im).text((4, 2), str(n), fill="red")
    tiles.append(im)
strip = Image.new("RGB", (max(t.width for t in tiles), sum(t.height + 6 for t in tiles)), "#999")
y = 0
for t in tiles:
    strip.paste(t, (0, y)); y += t.height + 6
strip.save(sys.argv[2])
