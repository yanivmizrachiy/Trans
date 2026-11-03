"""Batch G (03.11.2026): no "מהסרטון" labels, sub lines on pages 2, 12 and 13, page 34 rebuilt. Run from the repo root."""
import io
import re

def rd(p):
    return io.open(p, encoding="utf-8", newline="").read()

def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="").write(s)

def sub1(s, a, b, where="", count=1):
    k = s.count(a)
    assert k == count, (where, a[:90], k)
    return s.replace(a, b)

# ---------------------------------------------------------------- video pages
p = "book/krispin-video.html"; s = rd(p)
s = sub1(s, '<span class="tag v">מהסרטון</span>', "", p, count=10)
s = sub1(s, ".tag.v{background:#e3ebfb;color:#1f4aa8}", "", p)
s = sub1(s, "<h1>המחשה לטרנספורמציות בגזרי נייר</h1></div></header>",
         '<h1>המחשה לטרנספורמציות בגזרי נייר</h1><div class="sub">עקרונות 4 ו־5: מהמישור החופשי אל הצירים, והתאמה לכיתה</div></div></header>', p)
s = sub1(s, "<h1>טעויות צפויות, אבחון והתאמה לכיתה</h1></div></header>",
         '<h1>טעויות צפויות, אבחון והתאמה לכיתה</h1><div class="sub">כרטיס יציאה בארבע שאלות, התאמה לכל תלמיד, והמסר שבסוף ההמחשה</div></div></header>', p)
assert "מהסרטון" not in s
wr(p, s)

# ---------------------------------------------------------------- teacher summaries
p = "book/teacher.html"; s = rd(p)
s = sub1(s, "<h1>חפיפת צורות במישור — תמונה כוללת</h1></div></header>",
         '<h1>חפיפת צורות במישור — תמונה כוללת</h1><div class="sub">מה לומדים ביחידה, מה נשמר בכל העתקה, ואיך עובדים עם הסיכומים</div></div></header>', p)
s = sub1(s, ".hero-card{padding:24px;", ".hero-card{padding:17px 22px;", p)
s = sub1(s, "<strong>מהסרטון של איילת קריספין:</strong>", "<strong>בהמחשה של איילת קריספין:</strong>", p)
s = sub1(s, "הישר הוא „מראה”, והיוצרת אומרת „פשוט לסובב”.", "הישר הוא „מראה”, ואיילת קריספין אומרת „פשוט לסובב”.", p)
s = sub1(s, "לפי היוצרת, העיקר הוא איך שואלים ואיך מכוונים.", "לפי איילת קריספין, העיקר הוא איך שואלים ואיך מכוונים.", p)

S11_CSS = (
    "#summary-11 .case{display:grid;grid-template-columns:auto 1fr;gap:12px;align-items:center;background:#f1f6f6;border-radius:10px;padding:7px 12px;margin:0 0 9px}"
    "#summary-11 .case svg{width:38mm;height:auto;display:block}#summary-11 .case p{margin:2px 0;line-height:1.5}"
    "#summary-11 table.verbs{margin:0;font-size:12.5px;line-height:1.42}#summary-11 .verbs th{font-size:13px;padding:5px 8px}"
    "#summary-11 .verbs td{padding:5px 8px}#summary-11 .verbs td:first-child{width:38%}#summary-11 .verbs td:nth-child(2){width:33%}"
    "#summary-11 .verb{font-size:15px;font-weight:900;color:#0b5962;margin-inline-end:4px}"
    "#summary-11 td.err{color:#7a3a17}#summary-11 .pg{font-size:11px;color:#086b69;white-space:nowrap}"
    "#summary-11 .count{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:3px 0 2px}"
    "#summary-11 figure{margin:0;text-align:center}#summary-11 figure svg{height:24mm;width:auto;max-width:100%}"
    "#summary-11 figcaption{font-size:12.5px;font-weight:bold;color:#17515d}"
    "@media screen and (max-width:820px){#summary-11 .case,#summary-11 .count{grid-template-columns:1fr}#summary-11 .case svg{margin:auto}}\n"
)
s = sub1(s, "\n</style>", "\n" + S11_CSS + "</style>", p)

def grid(x0, x1, y0, y1, step):
    xs = "".join(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}"/>' for x in range(x0, x1 + 1, step))
    ys = "".join(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>' for y in range(y0, y1 + 1, step))
    return xs + ys

# The case: A(-5,3), B(-1,3), C(-5,1) moved 3 right and 4 down; one unit is 16 px, the origin sits at (112,80).
CASE_SVG = (
    '<svg viewBox="0 0 176 160" role="img" aria-label="המשולש ABC ותמונתו A′B′C′ לאחר הזזה 3 ימינה ו־4 למטה">'
    '<defs><marker id="s11-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0L10,5L0,10z" fill="#6f858c"/></marker></defs>'
    f'<g stroke="#dce8e7" stroke-width="1">{grid(16, 160, 16, 144, 16)}</g>'
    '<g stroke="#5e7480" stroke-width="1.4"><line x1="8" y1="80" x2="170" y2="80"/><line x1="112" y1="8" x2="112" y2="154"/></g>'
    '<g font-size="10" fill="#5e7480" font-family="Arial,sans-serif"><text x="164" y="92">x</text><text x="116" y="14">y</text>'
    '<text x="102" y="91">0</text><text x="125" y="91">1</text><text x="115" y="68">1</text></g>'
    '<polygon points="32,32 96,32 32,64" fill="#f7c6d3" stroke="#c2185b" stroke-width="2" stroke-linejoin="round"/>'
    '<polygon points="80,96 144,96 80,128" fill="#fde9a8" stroke="#b98900" stroke-width="2" stroke-linejoin="round"/>'
    '<g stroke="#6f858c" stroke-width="1.3" stroke-dasharray="3 2" marker-end="url(#s11-arrow)">'
    '<line x1="32" y1="32" x2="77" y2="92"/><line x1="96" y1="32" x2="141" y2="92"/><line x1="32" y1="64" x2="77" y2="124"/></g>'
    '<g font-size="11" font-weight="bold" fill="#0b3546" font-family="Arial,sans-serif" direction="ltr">'
    '<text x="20" y="30">A</text><text x="99" y="29">B</text><text x="20" y="70">C</text>'
    '<text x="64" y="94">A′</text><text x="147" y="94">B′</text><text x="64" y="136">C′</text></g></svg>'
)

def panel(body, label):
    return (f'<svg viewBox="0 0 150 110" role="img" aria-label="{label}">'
            f'<g stroke="#e1ebea" stroke-width="1">{grid(5, 145, 5, 105, 10)}</g>{body}'
            '<circle cx="75" cy="55" r="3.2" fill="#0b3546"/>'
            '<text x="79" y="50" font-size="11" font-weight="bold" fill="#0b3546" font-family="Arial,sans-serif" '
            'stroke="#fff" stroke-width="3" paint-order="stroke">P</text></svg>')

WIDE = ('<g fill="#087971" fill-opacity=".12" stroke="#087971" stroke-width="1.6">'
        '<rect x="75" y="35" width="30" height="20"/><rect x="45" y="35" width="30" height="20"/>'
        '<rect x="75" y="55" width="30" height="20"/><rect x="45" y="55" width="30" height="20"/></g>')
TALL = ('<g fill="none" stroke="#d9822b" stroke-width="1.6" stroke-dasharray="4 2">'
        '<rect x="75" y="25" width="20" height="30"/><rect x="55" y="25" width="20" height="30"/>'
        '<rect x="75" y="55" width="20" height="30"/><rect x="55" y="55" width="20" height="30"/></g>')
TURNED = ('<g fill="#087971" fill-opacity=".07" stroke="#087971" stroke-width="1.3">'
          + "".join(f'<rect x="75" y="35" width="30" height="20" transform="rotate({a} 75 55)"/>' for a in (15, 75, 135, 195, 255, 315))
          + "</g>")

S11 = (
    '<article class="sheet" id="summary-11"><header class="head"><div><div class="series">טרנספורמציות - סיכומים למורה</div>'
    '<h1>ניסוחי השאלות בתוכנית</h1><div class="sub">איך מתרגמים את הפעלים לעבודה ולבדיקה?</div></div></header><main class="content">'
    f'<div class="case">{CASE_SVG}<div>'
    '<p><strong>המקרה:</strong> השאלה מעמ׳ 48 בתוכנית, על המשולש ABC שקודקודיו <span class="math">A(−5,3)</span>, '
    '<span class="math">B(−1,3)</span> ו־<span class="math">C(−5,1)</span>. נעמה מזיזה אותו 3 יחידות ימינה ו־4 יחידות למטה.</p>'
    '<p>כל אחד מששת הניסוחים שואל על אותו מקרה, וכל אחד דורש תשובה אחרת. לפני השיעור מסמנים את הפועל בשאלה, '
    'ומחליטים מה ייחשב תשובה מלאה.</p></div></div>'
    '<table class="verbs"><tr><th>הניסוח</th><th>תשובה מלאה</th><th>טעות שכיחה</th></tr>'
    '<tr><td><span class="verb">זהו</span>„איזו העתקה הפכה את ABC ל־A′B′C′?”</td>'
    '<td>הזזה. המנח וסדר הקודקודים נשמרו.</td>'
    '<td class="err">„שיקוף, כי עבר אל מתחת לציר x.” אבל A נשאר מעל C.</td></tr>'
    '<tr><td><span class="verb">סרטטו</span>„סרטטו את המשולש שנעמה תקבל.” <span class="pg">עמ׳ 48</span></td>'
    '<td>כל קודקוד זז 3 ימינה ו־4 למטה, והאורכים נשמרים.</td>'
    '<td class="err">מזיזים קודקוד אחד, ואת השאר משלימים בעין.</td></tr>'
    '<tr><td><span class="verb">מצאו</span>„מצאו את שיעורי A′, B′ ו־C′.”</td>'
    '<td><span class="math">A′(−2,−1)</span>, <span class="math">B′(2,−1)</span>, <span class="math">C′(−2,−3)</span>.</td>'
    '<td class="err">מחליפים בין הצעדים ומקבלים <span class="math">A′(−1,0)</span>.</td></tr>'
    '<tr><td><span class="verb">חשבו</span>„חשבו את שטח A′B′C′.”</td>'
    '<td>בסיס 4 וגובה 2: שטח 4 יחידות ריבועיות.</td>'
    '<td class="err">גובה „−2”, כי המשולש מתחת לציר x.</td></tr>'
    '<tr><td><span class="verb">נמקו</span>„נעמה טענה: ״שטח המשולש החדש שמתקבל שווה לשטח המשולש הנתון״. האם נעמה צודקת? נמקו.” <span class="pg">עמ׳ 48</span></td>'
    '<td>כן. הזזה שומרת על אורכים ועל זוויות, ולכן השטחים שווים. גם חישוב שני השטחים הוא נימוק.</td>'
    '<td class="err">„כן, כי רואים שזה אותו משולש.”</td></tr>'
    '<tr><td><span class="verb">האם תמיד?</span>„האם כל שני משולשים שווי שטח חופפים?” <span class="pg">כמו בעמ׳ 91</span></td>'
    '<td>לא. משולש שבסיסו 8 וגובהו 1 שטחו 4, ואינו חופף ל־ABC.</td>'
    '<td class="err">דוגמה אחת שמתאימה מוצגת כהוכחה ל„תמיד”.</td></tr></table>'
    '<h3>תנאי הכרחי לשאלה טובה: לכתוב מה מותר</h3>'
    '<p>בעמ׳ 34 בתוכנית: „סרטטו מלבן חופף למלבן הנתון שאחד מקודקודיו הוא בנקודה <span class="math">(2,−1)</span>”. '
    'מספר התשובות תלוי במה שמותר. כך, למלבן 3×2 שאחד מקודקודיו בנקודה P:</p>'
    '<div class="count">'
    f'<figure>{panel(WIDE, "ארבעה מלבנים, רק בהזזה")}<figcaption>רק הזזה: 4 מלבנים</figcaption></figure>'
    f'<figure>{panel(WIDE + TALL, "שמונה מלבנים שצלעותיהם מקבילות לצירים")}<figcaption>צלעות מקבילות לצירים: 8 מלבנים</figcaption></figure>'
    f'<figure>{panel(TURNED, "מלבנים מסובבים סביב P בזוויות שונות")}<figcaption>סיבוב בכל זווית: אינסוף מלבנים</figcaption></figure>'
    '</div>'
    '<p class="micro-teach" data-summary="11">לאורך כל ההמחשה של איילת קריספין חוזרות שלוש שאלות: „מה קיבלנו? מה השתנה? איך היא ביחס לצורה המקורית?”. '
    'הוסיפו להן „סרטטו”, „מצאו שיעורים” ו„נמקו”, כדי לזהות אם הקושי בביצוע, בקריאה או בהסבר.</p></main>'
    '<footer class="source page-foot"><p class="src"><strong>אסמכתה:</strong> עדכון גאומטריה ז׳, עמ׳ 34, 48 ו־91.</p>'
)
old = re.search(r'<article class="sheet" id="summary-11">.*?<footer class="source page-foot"><p class="src">.*?</p>', s, re.S).group(0)
s = sub1(s, old, S11, p)
s = sub1(s, "<strong>מהסרטון:</strong> ", "", p, count=9)
assert "מהסרטון" not in s
wr(p, s)
print("batch G patched")
