#!/usr/bin/env python3
"""Real mobile-browser end-to-end checks on the publicly deployed transformation site.

Exercises UI interactions, mathematics in the live explorer, local PDF navigation,
image loading, right-to-left rendering, responsive overflow, and browser exceptions.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os

BASE="https://transformations-math.vercel.app"
OUT=Path("qa")/"public-browser"
OUT.mkdir(parents=True,exist_ok=True)
JS_ERRORS=[]

def require(test,message):
    if not test:raise AssertionError(message)

def check_page(page,path,required=None):
    response=page.goto(BASE+path,wait_until="networkidle",timeout=45000)
    require(response is not None and response.status==200,f"{path}: HTTP not 200")
    page.wait_for_timeout(200)
    metrics=page.evaluate("""() => ({
        width:innerWidth,
        scrollWidth:document.documentElement.scrollWidth,
        direction:getComputedStyle(document.documentElement).direction,
        lang:document.documentElement.lang
    })""")
    require(metrics["direction"]=="rtl",f"{path}: wrong RTL direction: {metrics}")
    require(metrics["scrollWidth"] <= metrics["width"]+2,
            f"{path}: horizontal overflow on mobile: {metrics}")
    if required:require(page.locator(required).count()>0,f"{path}: missing {required}")
    print(f"PASS MOBILE {path} width={metrics['width']} scrollWidth={metrics['scrollWidth']}")
    return response

def check_main(page):
    check_page(page,"/", "#cards")
    page.wait_for_function("document.querySelectorAll('#cards .card').length === 11")
    require(page.locator("#cards .card").count()==11,"Homepage must display 11 originals")
    page.locator("#search").fill("מראות")
    require(page.locator("#cards .card").count()==1,"Search must filter by actual worksheet title")
    page.locator("#search").fill("")
    page.locator('[data-topic="סיבוב"]').click()
    require(0<page.locator("#cards .card").count()<11,"Rotation topic filter must work")
    page.locator('[data-group="additional"]').click()
    require(0<page.locator("#cards .card").count()<=9,"Imported group must work")
    page.locator('[data-group="original"]').click()
    page.locator('[data-topic="הכול"]').click()
    page.locator("#cards .card").first.locator("button").first.click()
    require(page.locator("#viewer").evaluate("(el)=>el.open"),"Live preview did not open")
    require("worksheets/" in page.locator("#frame").get_attribute("src"),"Preview iframe does not navigate to real worksheet")
    page.locator("#close").click()
    require(not page.locator("#viewer").evaluate("(el)=>el.open"),"Preview cannot close")
    page.screenshot(path=str(OUT/"home-mobile.png"),full_page=True)
    print("PASS: live search, topic filter, source filter, modal preview and close")

def check_explorer(page):
    check_page(page,"/explore.html","#plot")
    page.locator("#predict").click()
    require(page.locator("#points tr").count()==3,"Explorer must output three transformed points")
    first=page.locator("#points tr").first.inner_text()
    require("(4, 3)" in first, f"Translation A(1,1)+ (3,2) incorrect: {first}")
    page.locator("#kind").select_option("rotate")
    page.locator("#predict").click()
    first=page.locator("#points tr").first.inner_text()
    require("(-1, 1)" in first, f"90-degree rotation about origin incorrect: {first}")
    page.locator("#kind").select_option("mirrorX")
    page.locator("#predict").click()
    second=page.locator("#points tr").nth(1).inner_text()
    require("(-2, 1)" in second,f"Reflection of B(4,1) in x=1 incorrect: {second}")
    page.locator("#reset").click()
    require(page.locator("#kind").input_value()=="move","Reset did not restore translation")
    page.screenshot(path=str(OUT/"explore-mobile.png"),full_page=True)
    print("PASS: real interactive translation, 90-degree rotation, reflection and reset")

def check_sources(page):
    check_page(page,"/original.html",".card")
    require(page.locator(".card").count()==11,"Author-owned catalog has wrong count")
    page.screenshot(path=str(OUT/"original-mobile.png"),full_page=True)
    check_page(page,"/curriculum.html",".entry")
    expected_entries=Path("curriculum.html").read_text(encoding="utf-8").count('class="entry"')
    require(page.locator(".entry").count()==expected_entries,f"Ministry source map must show the {expected_entries} question groups committed in curriculum.html")
    check_page(page,"/book/official.html",".scan")
    require(page.locator(".scan").count()==len(list((Path("sources")/"ministry").glob("*.webp"))),"Unaltered Ministry viewer missing source scans")
    visible=page.locator(".scan img").evaluate_all(
        "(imgs)=>imgs.map(i=>({ok:i.complete&&i.naturalWidth>=1200,width:i.naturalWidth}))")
    require(all(item["ok"] for item in visible),f"Original official scans failed to load: {visible}")
    page.screenshot(path=str(OUT/"official-mobile.png"),full_page=False)
    check_page(page,"/teacher.html","#original-answers")
    require(page.locator("#original-answers details").count()==11,"Teacher key does not cover eleven originals")
    page.locator("#original-answers details").first.locator("summary").click()
    require(page.locator("#original-answers details").first.evaluate("(d)=>d.open"),"Teacher answer key accordion not functional")
    page.screenshot(path=str(OUT/"teacher-mobile.png"),full_page=False)
    check_page(page,"/worksheets/orig-rectangles.html",".sheet")
    require(page.locator("svg[data-shape] polygon").count()==1,"Worksheet coordinate diagram was not generated")
    page.screenshot(path=str(OUT/"original-worksheet-mobile.png"),full_page=True)
    print("PASS: all source sections, image loading, answer disclosure, and real diagram rendering")


def check_compact_viewports(page):
    """Catch 320–430 CSS-pixel regressions that a single 390px smoke test misses."""
    for width in (320,360,430):
        page.set_viewport_size({"width":width,"height":740})
        check_page(page,"/","#cards")
        nav=page.locator(".top nav a").evaluate_all("""els => els.map(el => {
            const r=el.getBoundingClientRect();
            return {width:r.width,height:r.height,left:r.left,right:r.right};
        })""")
        require(len(nav)==4 and all(
            item["height"]>=44 and item["left"]>=-1 and item["right"]<=width+1 for item in nav),
            f"{width}px: home navigation links must be visible with 44px touch targets: {nav}")
        require(page.locator("#cards .card").count()==11,
                f"{width}px: all original worksheet cards must remain available")
        page.locator("#cards .card").first.locator("button").first.click()
        require(page.locator("#viewer").evaluate("(d)=>d.open"),
                f"{width}px: worksheet preview failed to open")
        title=page.locator("#vtitle").bounding_box()
        header=page.locator("#viewer .vtop").bounding_box()
        frame=page.locator("#frame").bounding_box()
        require(title and header and frame and frame["height"]>250
                and frame["y"]>=header["y"]+header["height"]-2,
                f"{width}px: preview iframe must start below its two-row mobile toolbar")
        for selector in ("#vopen","#close"):
            rect=page.locator(selector).bounding_box()
            require(rect and rect["height"]>=44 and rect["x"]>=-1
                    and rect["x"]+rect["width"]<=width+1,
                    f"{width}px: preview action clipped or too small: {selector} {rect}")
        page.locator("#close").click()
        for route,selector in (
            ("/original.html",".card"),
            ("/curriculum.html",".entry"),
            ("/teacher.html","#original-answers"),
            ("/explore.html","#plot"),
            ("/worksheets/orig-rotation.html",".sheet"),
        ):
            check_page(page,route,selector)
        # The plot scales to the viewport by default and can be enlarged
        # without expanding the page's document width.
        check_page(page,"/explore.html","#plot")
        zoom=page.locator("#zoom-plot")
        require(zoom.is_visible(),f"{width}px: missing usable graph zoom button")
        zoom.click()
        require(zoom.get_attribute("aria-pressed")=="true",
                f"{width}px: graph zoom does not toggle")
        chart_width=page.locator("#plot").evaluate("(el)=>el.getBoundingClientRect().width")
        require(chart_width>=600,f"{width}px: graph enlargement is not readable")
        screen_width=page.evaluate("document.documentElement.scrollWidth")
        require(screen_width<=width+2,
                f"{width}px: zoomed chart must scroll internally, not expand the page: "
                f"document={screen_width}, viewport={width}, "
                f"graph={page.locator('.graph').evaluate('e=>e.getBoundingClientRect().width')}, "
                f"scroller={page.locator('.plot-window').evaluate('e=>e.getBoundingClientRect().width')}")
        zoom.click()
        require(zoom.get_attribute("aria-pressed")=="false",
                f"{width}px: graph does not restore fit-to-width layout")
        if width==320:
            page.screenshot(path=str(OUT/"explore-320-mobile.png"),full_page=False)
    page.set_viewport_size({"width":390,"height":844})
    print("PASS: 320/360/430px touch targets, preview toolbar, graph zoom and six content routes")

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            context=browser.new_context(viewport={"width":390,"height":844},
                device_scale_factor=1,locale="he-IL",is_mobile=True,has_touch=True)
            page=context.new_page()
            page.on("pageerror",lambda exc:JS_ERRORS.append(str(exc)))
            check_main(page)
            check_explorer(page)
            check_sources(page)
            check_compact_viewports(page)
            require(not JS_ERRORS,f"Browser JavaScript exceptions: {JS_ERRORS}")
            context.close()
        finally:
            browser.close()
    groups=Path("curriculum.html").read_text(encoding="utf-8").count('class="entry"')
    scans=len(list((Path("sources")/"ministry").glob("*.webp")))
    print(f"PASS: public site mobile browser end-to-end, 11 original cards, {groups} curriculum groups, {scans} official scans, 11 keys; screenshots: {OUT}")
if __name__=="__main__":
    main()
