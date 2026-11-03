"""Visible text of a saved HTML page. Usage: python -I j2text.py <page.html> <out.txt>"""
import html, re, sys

raw = open(sys.argv[1], encoding="utf-8").read()
print("hebrew letters in raw:", len(re.findall("[א-ת]", raw)), "| escaped hebrew:", raw.count(chr(92) + "u05"), "| scripts:", raw.count("<script"))
body = re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", raw)
text = html.unescape(re.sub(r"(?s)<[^>]+>", "\n", body))
lines = [l.strip() for l in text.splitlines() if l.strip()]
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(lines))
print("visible lines:", len(lines))
