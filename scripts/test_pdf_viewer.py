#!/usr/bin/env python3
"""Browser-level regression check for the live PDF reading surface (not a screenshot mock).

Runs against the freshly built booklet over local HTTP, not the production
deployment. It checks the actual PDF.js module, worker and first-page canvas.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright
import manifest as M


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    root = Path(M.ROOT)
    assert (root / M.BOOK_FILE).exists(), "Build the canonical PDF before testing its viewer"
    handler = partial(QuietHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/{M.BOOK_HTML}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                page = browser.new_page(viewport={"width": 1100, "height": 850}, device_scale_factor=1)
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_function(
                    "() => document.querySelector('#page-1 canvas') || document.querySelector('#book iframe')",
                    timeout=60000,
                )
                assert not page.locator("#book iframe").count(), "PDF.js failed; native PDF fallback was displayed"
                actual = page.locator("#book .page").count()
                assert actual == M.TOTAL_PAGES, f"Viewer shows {actual} pages instead of {M.TOTAL_PAGES}"
                old_width = page.locator("#page-1 canvas").evaluate("(c) => c.width")
                assert old_width > 700, f"Desktop canvas is unexpectedly low resolution: {old_width}"

                page.set_viewport_size({"width": 390, "height": 780})
                page.wait_for_function(
                    "(before) => { const c = document.querySelector('#page-1 canvas'); return c && c.width < before && c.width >= 350; }",
                    arg=old_width,
                    timeout=30000,
                )
                assert not errors, f"Viewer JavaScript errors: {errors}"
                assert not page.locator("#book iframe").count(), "Viewer fell back while resizing"
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Horizontal scrolling"
                assert page.locator(".bar a[download]").count() == 1, "Must show one download button"
                print(f"PASS: PDF.js rendered {actual} A4 pages, desktop + mobile redraw, no horizontal scroll")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
