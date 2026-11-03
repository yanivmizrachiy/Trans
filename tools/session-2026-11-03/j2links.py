"""Links of a saved HTML page whose text matches a word. Usage: python -I j2links.py <page.html> <word>..."""
import html, re, sys

raw = open(sys.argv[1], encoding="utf-8").read()
seen = set()
for href, inner in re.findall(r'(?is)<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>', raw):
    text = " ".join(html.unescape(re.sub(r"(?s)<[^>]+>", " ", inner)).split())
    if any(w in text for w in sys.argv[2:]) and (href, text) not in seen:
        seen.add((href, text)); print(href, "|", text[:90])
