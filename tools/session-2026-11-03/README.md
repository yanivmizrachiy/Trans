# Session tools, 2026-11-03

These are the helper scripts from the session that produced PRs #53, #54 and #55. They are kept here at the owner's request ("save everything"). The site, the build and the checks do not use them.

SOURCE_OF_TRUTH §כג.21, §כג.22 and §כג.24 record what they were used for.

Run them with `PYTHONIOENCODING=utf-8`. Use `python -P` (or `python -I -X utf8`) for anything that reads a downloaded file, and keep downloads in their own empty folder.

## Booklet layout

| Script | What it does |
|---|---|
| `teacher_render.py <repo> <outdir> local\|proxy [summaries]` | Prints `book/teacher.html` the way `build_teacher.py` does. Re-runs `window.fitSheets()` and reports, for each summary: free space above the footer, overflow, and the page-fit zoom. Saves PNGs of the chosen summaries. |
| `blocks.py <repo> <summary> [proxy]` | Gives the natural (zoom 1) height of each block of one summary, and the room the page has for them. |
| `video_render.py <repo> <outdir> local\|proxy [pages]` | Prints `book/krispin-video.html` the way `build_complete.render_video` does, and reports free space per page. |
| `ci_render.py <stem> <outdir> [proxy or local]` | Prints `worksheets/<stem>.html`, in proxy mode unless told otherwise, and reports overflow. |

All four accept a `proxy` mode, which swaps in Google Fonts Arimo as a stand-in for Liberation Sans, the font the build runner uses for Arial. Arimo matches CI word widths within 0.3%, but it wraps lines that sit right at the limit, so its overflow results are pessimistic.

## Checking a built or published booklet PDF

| Script | What it checks |
|---|---|
| `live_check.py <pdf> <outdir>` | Pages, bookmarks, one look for the series line, the page 6 figures, and the solid page-number disc on every page. |
| `footcheck.py <pdf>` | Pages whose bottom 32 mm lacks the footer credit or logo. Ministry and imported pages carry no "הדף נערך ע״י" line by design. |
| `sizes.py <pdf> <repo>` | The page size of every page in mm, with its page-map item. |
| `corners.py <pdf> <out.png> <pages>` | Crops the page-number corner of each listed page into one strip. |
| `bottoms.py <pdf> <out.png> <mm> <pages>` | Crops the bottom of each listed page into one strip. |

## jerusalem2 comparison

| Script | What it does |
|---|---|
| `fetch.py <dir> <slug>...` | Saves `jerusalem2.vercel.app/chativat-beynayim/tochnit-limudim/<slug>/` pages. |
| `j2text.py <page.html> <out.txt>` | Extracts the visible text of a saved page. |
| `j2links.py <page.html> <word>...` | Lists the links whose text contains one of the words. |

## Patch scripts

| Script | What it did |
|---|---|
| `batch_f.py` | Made PR #54, the white number on a solid dark-blue disc. |
| `batch_g.py` | Made the draft PR #55: removed the "מהסרטון" labels, added sub lines on pages 2, 12 and 13, and rebuilt page 34. It expects the files as they were on `main` at `090fff0`. |
