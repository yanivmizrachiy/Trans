"""Save pages of jerusalem2.vercel.app/chativat-beynayim/tochnit-limudim/<slug>/ into <dir>/<slug>/page.html. Usage: python -I fetch.py <dir> <slug>..."""
import sys, urllib.request
from pathlib import Path

base = "https://jerusalem2.vercel.app/chativat-beynayim/tochnit-limudim/"
for slug in sys.argv[2:]:
    out = Path(sys.argv[1]) / slug; out.mkdir(parents=True, exist_ok=True)
    data = urllib.request.urlopen(base + slug + "/", timeout=60).read()
    (out / "page.html").write_bytes(data); print(slug, len(data))
