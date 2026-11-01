#!/usr/bin/env python3
"""Independently verify actual public HTTP resources against tracked GitHub bytes.

Runs on a GitHub-hosted runner (not on Vercel and not against localhost).
Only prints PASS if the public endpoint serves the exact published bytes.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import os
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://transformations-math.vercel.app"
ORIGINAL = (
    "orig-rectangles", "orig-translation", "orig-reflection",
    "orig-rotation", "orig-composition", "orig-symmetry",
    "orig-conveyor", "orig-mirror-route", "orig-center-p",
    "orig-symbol-turn", "orig-robot-grid",
)
OTHER = ("349", "350", "351", "352", "385", "549", "rectangles", "true-false", "triangle")
ROUTES = (
    "index.html", "original.html", "curriculum.html", "teacher.html", "explore.html",
    "book/teacher.html", "book/official.html", "book/front.html",
    "book/teacher.pdf", "book/official.pdf", "book/transformations-complete.pdf",
    "assets/raz-logo.svg", "assets/original-grid.js", "assets/original.css",
    *tuple("worksheets/"+s+".html" for s in ORIGINAL+OTHER),
    *tuple("pdf/"+s+".pdf" for s in ORIGINAL+OTHER),
    *tuple("sources/ministry/"+p.name for p in sorted((ROOT/"sources"/"ministry").glob("*.webp"))),
)
assert len(ROUTES)==len(set(ROUTES)), "Duplicate public asset route"

def audit_route(path):
    source = ROOT / path
    if not source.is_file():
        raise RuntimeError(f"Missing tracked resource {path}")
    original=source.read_bytes()
    expected_hash=sha256(original).hexdigest()
    url=BASE+"/"+path
    last_error=None
    for attempt in range(5):
        try:
            req=Request(url, headers={
                "User-Agent":"Trans-public-smoke/1.0 (GitHub Actions independent check)",
                "Accept":"*/*",
                "Accept-Encoding":"identity",
                "Cache-Control":"no-cache",
            })
            with urlopen(req,timeout=20) as response:
                status=response.status
                served=response.read()
                mimetype=response.headers.get("Content-Type","")
            if status!=200:
                last_error=f"HTTP {status}"
            elif sha256(served).hexdigest()!=expected_hash:
                last_error=f"BYTE MISMATCH local={len(original)} remote={len(served)}"
            elif path.endswith(".pdf") and not served.startswith(b"%PDF-"):
                last_error="PDF signature missing"
            elif path.endswith(".html") and "text/html" not in mimetype.lower():
                last_error=f"Wrong HTML type {mimetype}"
            else:
                return (path,len(served))
        except (HTTPError,URLError,TimeoutError,OSError) as exc:
            last_error=str(exc)
        if attempt<4:
            time.sleep(5+attempt*5)
    raise RuntimeError(f"Public route failed: {path}: {last_error}")

def main():
    start=time.monotonic()
    ok=[]
    problems=[]
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures={executor.submit(audit_route,r):r for r in ROUTES}
        for future in as_completed(futures):
            name=futures[future]
            try:
                ok.append(future.result())
            except Exception as exc:
                problems.append(f"{name}: {exc}")
    for name,size in sorted(ok):
        print(f"PASS {name} ({size} bytes)")
    for error in problems:
        print("FAIL",error)
    if problems:
        raise SystemExit(f"FAIL: {len(problems)} of {len(ROUTES)} public URLs did not exactly match deployed GitHub files")
    print(f"PASS: {len(ROUTES)} public HTTP resources all returned 200 with SHA256 identical to GitHub; duration={time.monotonic()-start:.1f}s")

if __name__=="__main__":
    main()
