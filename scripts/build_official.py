#!/usr/bin/env python3
"""Assemble seven source-identical photographed ministry curriculum pages into an unmodified-page PDF."""
from pathlib import Path
from io import BytesIO
from hashlib import sha1
from PIL import Image
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"book"/"official.pdf"
SOURCE=ROOT/"sources"/"ministry"
EXPECTED={
    34:"377b09e09884ed04aa4c99d84939f2716efcdb97",
    35:"efb77cc1256084dd2aa5091eacc0571dfa717eff",
    36:"14d2bcecc484ae36702700ae1981a49756999bb5",
    37:"70ca411667fc2d5efe4f2ad20343eedc30f5e8df",
    38:"a27437f83c1d43dbe3c10e96024f24be1fa5194a",
    50:"af7f4b3e92b4935678b4047ffb3e0bed10b5de3b",
    51:"ad5bebbe078981e49236c94f81412ef4491fe311",
}

def main():
    w,h=landscape(A4)
    canvas=Canvas(str(OUTPUT),pagesize=(w,h),pageCompression=1)
    for n, expected_sha in EXPECTED.items():
        src=SOURCE/f"grade7-p{n:03}.webp"
        data=src.read_bytes()
        gitsha=sha1(b"blob "+str(len(data)).encode()+b"\\x00"+data).hexdigest()
        if gitsha!=expected_sha:
            raise RuntimeError(f"Ministry page {n} changed from its original verified source")
        with Image.open(BytesIO(data)) as img:
            rgb=img.convert("RGB")
            if rgb.width < 1200 or rgb.height < 800:
                raise RuntimeError(f"Low resolution source page {n}")
            scale=min(w/rgb.width,h/rgb.height)
            cw,ch=rgb.width*scale,rgb.height*scale
            canvas.drawImage(ImageReader(rgb),(w-cw)/2,(h-ch)/2,width=cw,height=ch,preserveAspectRatio=True)
        canvas.showPage()
    canvas.save()
    pdf=PdfReader(str(OUTPUT))
    if len(pdf.pages)!=len(EXPECTED): raise RuntimeError("Original page count mismatch")
    for i,page in enumerate(pdf.pages):
        if not (830<float(page.mediabox.width)<850 and 580<float(page.mediabox.height)<610):
            raise RuntimeError(f"Wrong original orientation for page {i+1}")
    if OUTPUT.stat().st_size<90000:raise RuntimeError("Official PDF unexpectedly small")
    print(f"PASS: {len(EXPECTED)} unchanged ministry source pages, Git-blob hashes verified, landscape A4 PDF ({OUTPUT.stat().st_size} bytes)")

if __name__=="__main__":main()
