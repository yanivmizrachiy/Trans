"""Pages whose bottom 32 mm lacks the booklet footer (credit text + logo). Usage: python -P footcheck.py <pdf>"""
import sys
import fitz

d = fitz.open(sys.argv[1]); mm = 72 / 25.4
bad = []
for i, p in enumerate(d, 1):
    r = p.rect; zone = fitz.Rect(0, r.height - 32 * mm, r.width, r.height)
    text = p.get_text("text", clip=zone)
    logo = any(fitz.Rect(b["bbox"]).intersects(zone) for b in p.get_text("dict")["blocks"] if b["type"] == 1)
    if not ("קריספין" in text and "יניב רז" in text and logo):
        bad.append((i, "קריספין" in text, "יניב רז" in text, logo))
print("pages without the full footer:", bad or "none")
