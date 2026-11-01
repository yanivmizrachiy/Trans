#!/usr/bin/env python3
"""Independently render and audit all 51 pages of the completed PDF.

Chromium generates the individual documents. PyMuPDF is a second,
independent PDF renderer used to find blank pages, bad page geometry,
missing text/scans, and to preserve contact sheets for human inspection.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import fitz

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"book"/"transformations-complete.pdf"
DEST=ROOT/"qa"/"previews"
EXPECTED=51
SAMPLES=[
    ("teacher-and-source",[1,2,3,10,16,17]),
    ("official-and-original",[18,24,25,30,35,36]),
    ("additional-and-solutions",[42,44,45,46,48,51])
]

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(SOURCE)
    if len(doc)!=EXPECTED:raise RuntimeError(f"Expected 51 pages; got {len(doc)}")
    stats=[]
    for i,page in enumerate(doc):
        n=i+1
        is_official=17<=n<=24
        width,height=page.rect.width,page.rect.height
        if is_official and not (width>height and abs(width-841.89)<5):
            raise RuntimeError(f"Original ministry page {n}: A4 landscape orientation missing")
        if not is_official and not (height>width and abs(width-595.28)<5):
            raise RuntimeError(f"Book page {n}: A4 portrait orientation missing")
        pic=page.get_pixmap(matrix=fitz.Matrix(.38,.38),alpha=False)
        image=Image.frombytes("RGB",(pic.width,pic.height),pic.samples)
        gray=ImageOps.grayscale(image)
        hist=gray.histogram()
        occupied=sum(hist[:245])/max(1,sum(hist))
        if occupied<.005:
            raise RuntimeError(f"Possible blank or near-blank page {n}: ink={occupied:.3%}")
        if is_official:
            if not page.get_images(full=True):
                raise RuntimeError(f"Official page {n}: original image missing")
        else:
            extracted=page.get_text().strip()
            if len(extracted)<65:
                raise RuntimeError(f"Text page {n}: extracted text suspiciously short ({len(extracted)} chars)")
        stats.append((n,round(occupied,4)))

    for label,numbers in SAMPLES:
        cellw,cellh=450,650
        cols=2
        rows=(len(numbers)+cols-1)//cols
        panel=Image.new("RGB",(cols*cellw,rows*cellh),(231,238,240))
        draw=ImageDraw.Draw(panel)
        for j,num in enumerate(numbers):
            page=doc[num-1]
            pix=page.get_pixmap(matrix=fitz.Matrix(1.1,1.1),alpha=False)
            raw=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
            raw.thumbnail((cellw-28,cellh-53),Image.Resampling.LANCZOS)
            ox=(j%cols)*cellw+(cellw-raw.width)//2
            oy=(j//cols)*cellh+32+(cellh-42-raw.height)//2
            panel.paste(raw,(ox,oy))
            draw.text(((j%cols)*cellw+12,(j//cols)*cellh+9),f"PDF page {num}",fill=(16,57,65))
        target=DEST/(label+".jpg")
        panel.save(target,quality=88,optimize=True,progressive=True)
        print(f"Preview {target.relative_to(ROOT)}: {target.stat().st_size} bytes")
    print(f"PASS: {len(doc)} independently rendered pages; no blank pages, missing image scans, bad A4 orientation or missing text")
    print("Ink-coverage range:",min(x[1] for x in stats),max(x[1] for x in stats))

if __name__=="__main__":main()
