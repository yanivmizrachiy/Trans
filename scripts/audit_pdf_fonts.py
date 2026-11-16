#!/usr/bin/env python3
"""Report the fonts actually used in the built, printed PDF.

This is deliberately an audit, not an automatic font replacement: changing
the font can change geometry, Hebrew line wraps and official question wording.
"""
from collections import Counter
from pathlib import Path
import re
import pymupdf as fitz
import manifest as M


def main():
    path = Path(M.ROOT) / M.BOOK_FILE
    usages = Counter()
    hebrew_by_font = Counter()
    noto_embedded = set()
    first_page_noto = False
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
                        hebrew_letters = len(re.findall(r"[\u05d0-\u05ea]", span["text"]))
                        if hebrew_letters:
                            hebrew_by_font[span["font"]] += hebrew_letters
                            if i == 1 and "NotoSansHebrew" in span["font"]:
                                first_page_noto = True
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
            if data and "NotoSansHebrew" in name:
                noto_embedded.add(name)
            print(f"  FONT {xref} {name}: {'embedded' if data else 'not embedded or base-14'}"
                  f" ({len(data)} bytes)")
        print(f"NOTICE: PDF fonts requiring manual verification: {sorted(set(missing))}")
        if pages_without_text:
            raise AssertionError(f"Pages with no extractable text: {pages_without_text}")
        if not usages:
            raise AssertionError("No extractable PDF text")
        if not noto_embedded:
            raise AssertionError("No real Noto Sans Hebrew font embedded in the generated PDF")
        total_hebrew = sum(hebrew_by_font.values())
        noto_hebrew = sum(count for family, count in hebrew_by_font.items()
                          if "NotoSansHebrew" in family)
        print(f"Hebrew glyph coverage: {noto_hebrew}/{total_hebrew} in Noto Sans Hebrew")
        if total_hebrew < 100 or noto_hebrew * 2 < total_hebrew:
            raise AssertionError(
                f"Noto Sans Hebrew is not rendering the majority of Hebrew letters: "
                f"{noto_hebrew}/{total_hebrew}"
            )
        if not first_page_noto:
            raise AssertionError("The teacher summary on page 1 is not using the canonical Hebrew font")
    print("PASS: PDF font inventory generated; no automatic typographic approval claimed")


if __name__ == "__main__":
    main()
