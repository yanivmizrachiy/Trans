#!/usr/bin/env python3
"""Check that nothing printed links to a missing file, that no filler text is left and that the PDFs are real."""
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import re
import manifest as M

R = M.ROOT
BANNED = re.compile(r"(?i)\b(?:demo|mock|dummy|lorem ipsum|coming soon|javascript:void)\b|(?<![\u0590-\u05ff])דמו(?![\u0590-\u05ff])|בקרוב|בהקמה|בהכנה")
RETIRED = ("קל · מקביל", "קל מקביל אתגר", "מהדורה רציפה", "מבנה החוברת", "ותפקידי החוברת", "בגודל מלא", "הסבר פשוט", "שם התלמיד", "window.print")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self.urls.extend(d[k] for k in ("href", "src") if d.get(k))


def main():
    pages = [R / "index.html", *sorted((R / "book").glob("*.html")), *sorted((R / "worksheets").glob("*.html"))]
    for p in pages:
        html = p.read_text(encoding="utf-8")
        assert BANNED.search(html) is None, (p.name, "filler or unfinished text")
        for word in RETIRED:
            assert word not in html, (p.name, "retired wording", word)
        assert not re.search(r"href\s*=\s*['\"](?:#|javascript:|\s*)['\"]", html, re.I), (p.name, "empty link")
        assert "razpages" not in html and "MathJax" not in html, (p.name, "pages load nothing from other repositories")
        links = Links(); links.feed(html)
        for link in links.urls:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            local = (p.parent / unquote(url.path)).resolve()
            assert (R == local or R in local.parents) and local.is_file(), (p.name, "broken link", link)
        if p.parent.name == "worksheets":
            assert "raz-logo.svg" not in html, (p.name, "retired logo")
            if p.stem in M.ORIGINAL:
                assert html.count('class="level"') + html.count("class='level'") == 3, p.name
    for p in [*(R / "pdf").glob("*.pdf"), *(R / "book").glob("*.pdf")]:
        data = p.read_bytes()
        assert len(data) > 3500 and data.startswith(b"%PDF-") and b"%%EOF" in data[-4096:], p.name
    assert "book/complete.html" in (R / "index.html").read_text(encoding="utf-8"), "The site opens on the booklet"
    print(f"PASS: {len(pages)} pages, links, wording and PDFs")


if __name__ == "__main__":
    main()
