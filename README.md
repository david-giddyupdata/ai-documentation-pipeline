# AI documentation pipeline: a worked example

**This is an example from a real project, not software that runs unmodified.** It is the set of scripts an AI agent
(Claude Code) and I used to update a 317-page training manual for Quick Sight (AWS), a business-intelligence product
whose screens had changed. It won't run on your computer as it is: it needs the course manual, the per-exercise step
scripts and a Quick Sight account, none of which are published. Read it to see how the parts fit together, then
borrow the ideas.

By David Baldwin, GiddyUp Data LLC. Part of the takeaway from the talk "Move Beyond the Chatbot" (October 2026).
**New to AI agents?** Start with the starter kit,
[ai-workspace-blueprints](https://github.com/david-giddyupdata/ai-workspace-blueprints): it sets up a workspace in
about 15 minutes with no programming. The other worked example is
[ai-video-pipeline](https://github.com/david-giddyupdata/ai-video-pipeline).

## What it did

- Drove a real browser through each exercise, the way a student would, and captured screenshots at double resolution
  with the position of every on-screen element saved alongside.
- Annotated those screenshots in my own style (rounded boxes, arrows, numbered circles, torn edges), with the marks
  computed from the saved positions rather than placed by hand.
- Rebuilt a **draft** Word manual from a **master** copy that is never edited, so a change is a re-run, not a
  re-edit. 244 pictures re-render in about 20 seconds; 317 pages rebuild in about 35.
- Rendered the draft to PDF and checked every page: blank pages, step numbering, picture sizes, contact sheets.
- Built a review page that shows only what changed since my last review.
- Ran an "AI student" with only screenshots, a mouse and a keyboard through the whole manual overnight, and turned
  what it reported into a findings list for me to rule on.

## Ground rules the agent worked under

These are the habits that made the pipeline safe to hand over. They matter more than the code.

- **Never write the master.** Every build starts by copying the master to a draft and applying the changes in order.
  I merge into the master myself.
- **Word must be closed when building.** If the draft is locked, the build stops and says so. The agent never
  stops Word itself.
- **I sign in myself.** The agent never types a password.
- **A separate browser.** Chrome with its own profile on its own debugging port, never my everyday browser. Another
  automation uses Edge on a different port; the agent never touches it.
- **Screenshots must look like a student's.** Work in a copy trimmed to the exercise's starting state, so no
  finished later work shows.
- **Match my style.** The style guide and my review rules are in `steering/style.md`; the agent applies them without
  being asked, and adds a rule there whenever I give a new one.
- **Deletions need my OK, by name.** Before deleting anything in the product, the agent confirms the object by name
  and waits.

## The files

All scripts are in `automation/`, in their original layout, because they import each other and find files by
relative path.

| File | Its job |
|---|---|
| `automation/build.py` | One command: build the draft, render it with Word, scan the step numbers, and make contact sheets of the exercises that changed since the last build |
| `automation/make_draft.py` | Copies the master to the draft and applies each exercise's changes in order. Its list names per-exercise scripts that are course material and not published |
| `automation/build_lib.py` | The editing library: rebuild an exercise's instruction table, replace text by style, swap pictures, fix numbering, and the layout passes (picture sizes, spacing, page breaks) |
| `automation/units.py` | Splits a Word document into exercises and finds each exercise's PDF pages |
| `automation/review_pack.py` | A review page: master and draft side by side, changes only, per exercise |
| `automation/review_new.py` | A review page showing only what changed since my last review, with "at your last review" and "now" side by side |
| `automation/start_browser.ps1` | Starts the agent's own Chrome on its own profile and debugging port |
| `automation/qs.py` | Browser helpers: connect to that Chrome, capture a screenshot with every element's position, peek at the screen |
| `automation/annotate.py` | Snagit-style annotation from those positions: crop, box, arrow, numbered callout, cut, tear, combine |
| `automation/_work/common.py` | Shared helpers the step scripts import (find a control, open a menu, drag a field). Set `<ANALYSIS_ID>` to your own analysis |
| `automation/_work/render.ps1` | Renders the draft to PDF in its own Word process and always closes it |
| `automation/_work/scan_numbers.py` | Reads the rendered step numbers so the build can check them |
| `automation/_work/pdf_page.py` | Renders one PDF page, or zooms into part of one, to see what students see |
| `automation/_work/ocr_find.py` | Reads the text inside every picture in a Word file and lists matches |
| `automation/_work/student_walk.py` | The AI student: its instructions, its safety rules, and the run list |
| `automation/_work/student_server.py` | The student's only tools: a small local server that can screenshot, click, drag, type and scroll in the agent's browser |
| `automation/_work/student_extract.py` | Pulls the student's findings out of each run, masking any course passwords |
| `automation/_work/student_report.py` | Turns the findings into a review page |
| `steering/style.md` | The manual's style guide and "David's Review Rules": my corrections, turned into rules the agent applies every time |

## What it needs, and what it costs

Windows (Word is driven through COM, a Windows-only automation interface), Python 3, Microsoft Word, Google Chrome,
Playwright, python-docx, PyMuPDF, Pillow and Tesseract OCR. Set the `TESSERACT_CMD` environment variable if Tesseract
isn't installed in its default folder. `start_browser.ps1` takes an optional `-StartUrl` for your own region's
sign-in page. Prices as of October 2026; check before you buy.

| Tool | What it's for | Cost | Free alternative |
|---|---|---|---|
| Claude Code (in VS Code) | The agent that wrote and ran these scripts | A paid Claude plan: Pro about $20 a month, Max $100 or $200 | Other agent tools; the practices are tool-neutral |
| python-docx | Rebuilds the draft from a never-edited master; edits by style; layout passes | Free (MIT) | n/a |
| Microsoft Word (through COM) | Renders the draft to PDF for checking | Part of Microsoft 365 | LibreOffice in headless mode (not tested with these scripts) |
| PyMuPDF | Renders and checks pages: blank pages, numbering, contact sheets | Free (AGPL-3.0; see below) | n/a |
| Pillow | Annotation: boxes, arrows, numbered circles, torn edges, cuts | Free | n/a |
| Tesseract OCR, pytesseract | Reads text in images during the build | Free (Apache-2.0) | n/a |
| Playwright (Python) | Connects to the agent's own Chrome | Free (Apache-2.0) | n/a |
| Chrome, own profile and debugging port | The browser the manual is walked and captured in | Free | Edge |
| AWS CLI | Listing and deleting objects by name in the product being documented | Free tool; your AWS account costs apply | n/a |
| The product you document (mine: Quick Sight) | What the manual teaches | Your own account's costs | Any product you document |

**PyMuPDF is AGPL-3.0** (or a commercial licence). It isn't included here. If you distribute software that bundles
it, or offer it as a network service, the AGPL applies to you.

## What is not here

The course manual, the per-exercise step and annotation scripts, the screenshots, the review pages, the session
notes and the AI student's run records. They are course material, show account details, or both.

## Safety

- **Keys never go in files or chats.** Nothing here contains a key. Placeholders in angle brackets, such as
  `<ANALYSIS_ID>`, mark values I removed.
- **The agent drives its own browser, and I sign in.** The scripts connect to a separate Chrome profile on its own
  debugging port, never an everyday browser.
- **I run my agent with its permission prompts off.** Don't copy that. Keep the prompts on, and on a company
  computer start from the stricter settings in the starter kit's `use/settings/`.
- **Prompt injection is not solved.** An agent that reads a web page can be misled by hidden instructions in it. The
  AI student's tools are limited to screenshots, clicks and typing in one browser for that reason, which reduces the
  damage but doesn't prevent it.

## License and contact

MIT License, copyright 2026 GiddyUp Data LLC (see `LICENSE`). Third-party tools keep their own licences. **The
GiddyUp Data name and logo are not licensed for reuse.** Questions or errors: open an issue. Pull requests are not
accepted for now. For anything sensitive, see [`SECURITY.md`](SECURITY.md).
