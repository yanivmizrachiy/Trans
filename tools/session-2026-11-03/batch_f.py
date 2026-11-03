"""Batch F (03.11.2026): the page number is white on a solid dark-blue disc (option B). Run from the repo root."""
import io

def rd(p):
    return io.open(p, encoding="utf-8", newline="").read()

def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="").write(s)

def sub1(s, a, b, where=""):
    k = s.count(a)
    assert k == 1, (where, a[:90], k)
    return s.replace(a, b)

p = "scripts/build_complete.py"; s = rd(p)
s = sub1(s, """# The page number: a thin dark-blue circle whose left edge sits on the 14 mm text margin and
# whose centre is 12 mm below the top edge, inside every printer's printable area
# (SOURCE_OF_TRUTH §כג.9, §כג.10, §כג.14). FOLIO_ZONE (mm from the top-left corner) is the
# circle plus 1.5 mm, and must be blank on every page before it is stamped.
FOLIO_X,FOLIO_Y,FOLIO_R=17.7,12.0,3.7
""", """# The page number: white on a solid disc in the dark blue of the footer line. The disc's left
# edge sits on the 14 mm text margin and its centre is 12 mm below the top edge, inside every
# printer's printable area (SOURCE_OF_TRUTH §כג.9, §כג.10, §כג.14, §כג.22). FOLIO_ZONE (mm from
# the top-left corner) is the disc plus 1.5 mm, and must be blank on every page before it is stamped.
FOLIO_X,FOLIO_Y,FOLIO_R=17.9,12.0,3.9
""", where=p)
s = sub1(s, """    number, in the top-left corner inside a thin dark-blue circle.\"\"\"""",
         """    number, white on a solid dark-blue disc in the top-left corner.\"\"\"""", where=p)
s = sub1(s, """        canvas.setStrokeColorRGB(11/255,42/255,74/255)
        canvas.setFillColorRGB(1,1,1)
        canvas.setLineWidth(0.9)
        canvas.circle(x,y,FOLIO_R*mm,stroke=1,fill=1)
        canvas.setFillColorRGB(11/255,42/255,74/255)
        canvas.setFont("Helvetica-Bold",9.5)
        canvas.drawCentredString(x,y-3.3,str(n))
""", """        canvas.setFillColorRGB(11/255,58/255,117/255)
        canvas.circle(x,y,FOLIO_R*mm,stroke=0,fill=1)
        canvas.setFillColorRGB(1,1,1)
        canvas.setFont("Helvetica-Bold",10)
        canvas.drawCentredString(x,y-3.5,str(n))
""", where=p)
wr(p, s)

p = "scripts/visual_audit.py"; s = rd(p)
s = sub1(s, """        # The only page number is stamped in the top-left corner of every page (its circle is
        # centred 17.7 mm from the left and 12 mm from the top), and no other text sits there.""",
         """        # The only page number is stamped in the top-left corner of every page (its disc is
        # centred 17.9 mm from the left and 12 mm from the top), and no other text sits there.""", where=p)
s = sub1(s, """        if not any(full):
            raise RuntimeError(f"Page {n}: the dark-blue line above the footer must cross the whole page")
""", """        if not any(full):
            raise RuntimeError(f"Page {n}: the dark-blue line above the footer must cross the whole page")
        # The number is white on a solid dark-blue disc (SOURCE_OF_TRUTH §כג.22): a ring 3.2 mm from
        # the centre, outside the digits and inside the disc's 3.9 mm radius, is dark blue all round.
        cx,cy,half=17.9*mm,12.0*mm,4.5*mm
        zoom=4
        disc=page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),clip=fitz.Rect(cx-half,cy-half,cx+half,cy+half),alpha=False)
        disc_img=Image.frombytes("RGB",(disc.width,disc.height),disc.samples)
        ring=[disc_img.getpixel((int((half+3.2*mm*cos)*zoom),int((half+3.2*mm*sin)*zoom)))
              for cos,sin in ((1,0),(.7071,.7071),(0,1),(-.7071,.7071),(-1,0),(-.7071,-.7071),(0,-1),(.7071,-.7071))]
        if not all(dark_blue(c) for c in ring):
            raise RuntimeError(f"Page {n}: the page number must sit on a solid dark-blue disc, ring colours {ring}")
""", where=p)
wr(p, s)

p = "SOURCE_OF_TRUTH.md"; s = rd(p)
s = s.rstrip("\n") + "\n\n" + """### כג.22 — מספר העמוד: לבן, בתוך עיגול מלא בכחול כהה (03.11.2026)

**דברי המשתמש (מילה במילה):**

- „תן לי אפשרויות לעיצוב של המיספור”
- „B, עיגול מלא”

**ההחלטות:**

- הוצגו שבע אפשרויות (A–G) על עמודים 1, 13 ו־44 של החוברת. כל אחת נבדקה מול כל 70 העמודים, ואף אחת לא נוגעת בתוכן. נבחרה B.
- מספר העמוד מודפס עכשיו בלבן (Helvetica Bold, 10 נקודות) בתוך עיגול מלא בכחול כהה `#0b3a75`, הצבע של הקו שמעל הכותרת התחתית.
- רדיוס העיגול 3.9 מ״מ. הקצה השמאלי שלו נשאר על קו השוליים, 14 מ״מ מהשמאל, ולכן מרכזו 17.9 מ״מ מהשמאל ו־12 מ״מ מלמעלה. זה מחליף את העיגול הדק שבסעיף §כג.14.
- **אכיפה:** `build_complete.py` עדיין נכשל אם עמוד מדפיס משהו בתחום העיגול ועוד 1.5 מ״מ סביבו. `visual_audit.py` בודק שבפינה יש רק המספר, ושטבעת סביב הספרות, 3.2 מ״מ מהמרכז, כחולה כהה בכל 70 העמודים.
- **המספרים:** 70 עמודים ו־57 סימניות, ללא שינוי.
"""
wr(p, s)
print("batch F patched")
