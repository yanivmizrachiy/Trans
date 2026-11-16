#!/usr/bin/env python3
"""Report the fonts actually used in the built, printed PDF.

This is deliberately an audit, not an automatic font replacement: changing
the font can change geometry, Hebrew line wraps and official question wording.
"""
from collections import Counter
from pathlib import Path
import pymupdf as fitz
import manifest as M


def main():
    path = Path(M.ROOT) / M.BOOK_FILE
    usages = Counter()
    font_objects = {}
    pages_without_text = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, 1):
            found_text = False
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if not span["text"].strip():
                            continue
                        found_text = True
                        usages[(span["font"], round(span["size"], 1))] += len(span["text"])
            if not found_text:
                pages_without_text.append(i)
            for record in page.get_fonts(full=True):
                xref, ext, subtype, basefont = record[:4]
                if xref not in font_objects:
                    font_objects[xref] = (ext, subtype, basefont)

        print(f"PDF typography audit: {len(doc)} A4 pages, {len(font_objects)} font objects")
        for (family, size), chars in usages.most_common(25):
            print(f"  {family} | {size}pt | {chars} extracted characters")
        missing = []
        for xref, (_, _, name) in sorted(font_objects.items()):
            try:
                _, _, _, data = doc.extract_font(xref)
            except Exception as error:
                print(f"  FONT {xref} {name}: could not inspect ({error})")
                missing.append(name)
                continue
            if not data:
                missing.append(name)
            print(f"  FONT {xref} {name}: {'embedded' if data else 'not embedded or base-14'}"
                  f" ({len(data)} bytes)")
        print(f"NOTICE: PDF fonts requiring manual verification: {sorted(set(missing))}")
        if pages_without_text:
            raise AssertionError(f"Pages with no extractable text: {pages_without_text}")
        if not usages:
            raise AssertionError("No extractable PDF text")
    print("PASS: PDF font inventory generated; no automatic typographic approval claimed")


if __name__ == "__main__":
    main()
