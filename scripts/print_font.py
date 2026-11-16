"""Enforce real Hebrew font loading before PDF printing, never silently use fallback."""
from playwright.sync_api import Page

FONT_FAMILY = "Assistant"
HEBREW_SAMPLE = "טרנספורמציות וסיבוב א׳ ב׳"


def require_book_font(page: Page) -> None:
    result = page.evaluate("""async sample => {
      await document.fonts.load('400 13.5px "Assistant"', sample);
      await document.fonts.load('700 20px "Assistant"', sample);
      await document.fonts.ready;
      return [...document.fonts]
        .filter(face => face.family.replace(/["']/g, "").trim() === "Assistant")
        .map(face => ({weight: face.weight, status: face.status}));
    }""", HEBREW_SAMPLE)
    if not result or not any(face["status"] == "loaded" for face in result):
        raise RuntimeError(
            f"Hebrew font {FONT_FAMILY!r} was not loaded; refusing to generate a fallback-font PDF: {result}"
        )
