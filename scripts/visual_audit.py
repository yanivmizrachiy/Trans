#!/usr/bin/env python3
"""Independently render and audit every page of the completed PDF.

Chromium generates the individual documents. PyMuPDF is a second,
independent PDF renderer used to find blank pages, bad page geometry,
missing text/scans, and to preserve contact sheets for human inspection.
Every page is portrait A4 and carries the running page number; which pages
are Ministry scans is derived from the manifest's reading sequence.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
import fitz
import manifest as M

ROOT=M.ROOT
SOURCE=ROOT/M.BOOK_FILE
DEST=ROOT/"qa"/"previews"
EXPECTED=M.TOTAL_PAGES
PAGE_MAP={n:(chapter,item) for n,chapter,item,_ in M.page_map()}

def samples():
    """Contact sheets whose page numbers come from the manifest layout."""
    openers=[first for chapter,first,_ in M.layout()]
    scans=[n for n,(_,item) in PAGE_MAP.items() if item[0]=="m"]
    worksheets=[n for n,(_,item) in PAGE_MAP.items() if item[0]=="w"]
    summaries=[n for n,(_,item) in PAGE_MAP.items() if item[0]=="s"]
    closing=[n for n,(_,item) in PAGE_MAP.items() if item[0]=="c"]
    return [
        ("chapter-openers",openers[:10]),
        ("ministry-source-pages",scans),
        ("worksheets-in-topic-order",worksheets[:10]),
        ("teacher-summaries",summaries[:10]),
        ("teacher-lab-and-solutions",closing[:10]),
    ]

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(SOURCE)
    if len(doc)!=EXPECTED:raise RuntimeError(f"Expected {EXPECTED} pages (data/manifest.json); got {len(doc)}")
    stats=[]
    for i,page in enumerate(doc):
        n=i+1
        chapter,item=PAGE_MAP[n]
        is_official=item[0]=="m"
        width,height=page.rect.width,page.rect.height
        if not (height>width and abs(width-595.28)<5 and abs(height-841.89)<5):
            raise RuntimeError(f"Book page {n}: A4 portrait page size missing")
        pic=page.get_pixmap(matrix=fitz.Matrix(.38,.38),alpha=False)
        image=Image.frombytes("RGB",(pic.width,pic.height),pic.samples)
        gray=ImageOps.grayscale(image)
        hist=gray.histogram()
        occupied=sum(hist[:245])/max(1,sum(hist))
        if occupied<.005:
            raise RuntimeError(f"Possible blank or near-blank page {n}: ink={occupied:.3%}")
        if is_official and not page.get_images(full=True):
            raise RuntimeError(f"Official page {n}: original image missing")
        extracted=page.get_text().strip()
        if len(extracted)<65:
            raise RuntimeError(f"Text page {n}: extracted text suspiciously short ({len(extracted)} chars)")
        # The only page number is stamped in the top-left corner of every page (its circle is
        # centred 17.7 mm from the left and 12 mm from the top), and no other text sits there.
        corner=fitz.Rect(0,0,26*72/25.4,19*72/25.4)
        words=[w[4] for w in page.get_text("words",clip=corner)]
        if words!=[str(n)]:
            raise RuntimeError(f"Page {n}: top-left corner must hold only the page number, found {words}")
        # The footer closes every page: a dark-blue line across the whole width and, below it,
        # the district logo centred on the page (SOURCE_OF_TRUTH §כג.16).
        mm=72/25.4
        logos=[r for r in (fitz.Rect(info["bbox"]) for info in page.get_image_info())
               if r.y1>height-30*mm and 8*mm<r.width<16*mm]
        if not logos:
            raise RuntimeError(f"Page {n}: the logo footer is missing")
        logo=max(logos,key=lambda r:r.y1)
        if abs((logo.x0+logo.x1)/2-width/2)>1.5*mm:
            raise RuntimeError(f"Page {n}: the footer logo must be centred on the page")
        band=page.get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(0,logo.y0-9*mm,width,logo.y0),alpha=False)
        strip=Image.frombytes("RGB",(band.width,band.height),band.samples)
        dark_blue=lambda c:c[2]>=80 and c[2]-c[0]>=45 and c[0]<=80 and c[1]<=110
        full=[sum(1 for x in range(0,strip.width,3) if dark_blue(strip.getpixel((x,y))))*3>=.96*strip.width
              for y in range(strip.height)]
        if not any(full):
            raise RuntimeError(f"Page {n}: the dark-blue line above the footer must cross the whole page")
        stats.append((n,round(occupied,4)))

    for label,numbers in samples():
        cellw,cellh=(900,1300) if label=="ministry-source-pages" else (450,650)
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
    print(f"PASS: {len(doc)} independently rendered portrait A4 pages; no blank pages, missing scans or footers, missing text or missing page numbers")
    print("Ink-coverage range:",min(x[1] for x in stats),max(x[1] for x in stats))

if __name__=="__main__":main()
