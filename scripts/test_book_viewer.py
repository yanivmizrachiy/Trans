#!/usr/bin/env python3
"""End-to-end browser smoke test for the real continuous PDF preview."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    httpd = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        partial(SilentHandler, directory=str(ROOT)),
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_port}/book/complete.html"
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                page = browser.new_page(viewport={"width": 930, "height": 900}, device_scale_factor=2)
                page.on("pageerror", lambda err: errors.append(str(err)))
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector("#page-1 canvas", timeout=90000)
                before = page.evaluate("""() => {
                  const slot=document.getElementById("page-1"), c=slot.querySelector("canvas");
                  return {width: slot.clientWidth, pixels: c.width};
                }""")
                if before["pixels"] < before["width"] * 1.9:
                    raise AssertionError(f"Initial PDF preview not rendered at screen pixel density: {before}")

                page.set_viewport_size({"width":425, "height":900})
                page.wait_for_function("""() => {
                  const slot=document.getElementById("page-1"), c=slot?.querySelector("canvas");
                  return c && slot.clientWidth<=425 && Math.abs(c.width-slot.clientWidth*2)<4;
                }""", timeout=45000)
                after = page.evaluate("""() => {
                  const slot=document.getElementById("page-1");
                  return {width: slot.clientWidth, pixels: slot.querySelector("canvas").width,
                          overflow: document.documentElement.scrollWidth>innerWidth+1};
                }""")
                if after["overflow"] or errors:
                    raise AssertionError(f"Mobile overflow or browser errors: {after}, {errors}")
                print(f"PASS: PDF preview rendered at 2x pixels and redrew after resize: {before} -> {after}")
                page.close()
            finally:
                browser.close()
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    main()
