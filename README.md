# AI documentation pipeline: a worked example

**This is an example from a real project, not software that runs unmodified.** It is the set of scripts an AI agent
(Claude Code) and I used to update a 317-page training manual for QuickSight (AWS), a business-intelligence product
whose screens had changed. It won't run on your computer as it is: it needs the course manual, the per-exercise step
scripts and a QuickSight account, none of which are published. Read it to see how the parts fit together, then
borrow the ideas.

AWS has since renamed the product (the screen now says Quick Sight, part of Quick Suite), so the scripts and the
style guide use whichever name the screen showed at the time; this README says QuickSight.

By David Baldwin, GiddyUp Data LLC. Part of the takeaway from the talk "Move Beyond the Chatbot" (October 2026).

**New to AI agents?** Start with the starter kit,
[ai-workspace-blueprints](https://github.com/david-giddyupdata/ai-workspace-blueprints): it sets up a workspace in
about 15 minutes with no programming. The other worked example is
[ai-video-pipeline](https://github.com/david-giddyupdata/ai-video-pipeline).

## What it did

- Drove a real browser through each exercise, the way a student would, and captured screenshots at double resolution
  with the positions of the elements each step marks saved alongside.
- Annotated those screenshots in my own style (rounded boxes, arrows, numbered circles, torn edges), with the marks
  computed from the saved positions rather than placed by hand.
- Rebuilt a **draft** Word manual from a **master** copy that is never edited, so a change is a re-run, not a
  re-edit. 244 pictures re-render in about 20 seconds; 317 pages rebuild in about 35.
- Rendered the draft to PDF and checked every page: blank pages, step numbering, picture sizes, contact sheets.
- Built a review page that shows only what changed since my last review.
- Ran an "AI student" through the whole manual overnight, told to use only screenshots, a mouse and a keyboard, and
  turned what it reported into a findings list for me to rule on.

## Ground rules the agent worked under

These are the habits that made the pipeline safe to hand over. They matter more than the code.

- **Never write the master.** Every build starts by copying the master to a draft and applying the changes in order.
  I merge into the master myself.
- **Word must be closed when building.** If the draft is locked, the build stops and says so. The agent never
  stops Word itself.
- **I sign in myself.** The agent never types an AWS sign-in. In one exercise it connects to the course's training
  database with the login printed in the manual, as students do; that login is rotated for every class, and the
  database is switched off between classes.
- **A separate browser.** Chrome with its own profile on its own debugging port, never my everyday browser.
- **Screenshots must look like a student's.** Work in a copy trimmed to the exercise's starting state, so no
  finished later work shows.
- **Match my style.** The style guide and my review rules are in `steering/style.md` (steering: the instructions
  the agent reads every session; in Claude Code that's CLAUDE.md). The agent applies them without being asked, and
  adds a rule there whenever I give a new one.
- **Deletions need my OK, by name.** Before deleting anything in the product, the agent confirms the object by name
  and waits.

## The files

All scripts are in `automation/`, in their original layout, because they import each other and find files by
relative path. That layout also mixes tools and their output in `automation/_work/` (`render.pdf`, `sheets/`,
`student_walk/`, `fit_report.json`); `.gitignore` keeps the output out. Comments mention "session 6", "session 9"
and so on: those are the nine working sessions with the agent, 2026-10-03 to 2026-10-13.

| File | Its job |
|---|---|
| `automation/build.py` | One command: build the draft, render it with Word, scan the step numbers, and make contact sheets of the exercises that changed since the last build |
| `automation/make_draft.py` | Copies the master to the draft and applies each exercise's changes in order. Its list names per-exercise scripts that are course material and not published |
| `automation/build_lib.py` | The editing library: rebuild an exercise's instruction table, replace text by style, swap pictures, fix numbering, and the layout passes (picture sizes, spacing, page breaks) |
| `automation/units.py` | Splits a Word document into exercises and finds each exercise's PDF pages |
| `automation/review_pack.py` | A review page: master and draft side by side, changes only, per exercise |
| `automation/review_new.py` | A review page showing only what changed since my last review, with "at your last review" and "now" side by side |
| `automation/start_browser.ps1` | Starts the agent's own Chrome on its own profile and debugging port |
| `automation/qs.py` | Browser helpers: connect to that Chrome, capture a screenshot with the positions of the elements a step marks, peek at the screen |
| `automation/annotate.py` | Snagit-style annotation from those positions: crop, box, arrow, numbered callout, cut, tear, combine |
| `automation/_work/common.py` | Shared helpers the step scripts import (find a control, open a menu, drag a field). Set `<ANALYSIS_ID>` to your own analysis |
| `automation/_work/render.ps1` | Renders the draft to PDF in its own Word process and always closes it |
| `automation/_work/scan_numbers.py` | Reads the rendered step numbers so the build can check them |
| `automation/_work/pdf_page.py` | Renders one PDF page, or zooms into part of one, to see what students see |
| `automation/_work/ocr_find.py` | Reads the text inside every picture in a Word file and lists matches |
| `automation/_work/student_walk.py` | The AI student: its instructions, its safety rules, and the run list |
| `automation/_work/student_server.py` | The student's browser tools: a small local server that can screenshot, click, drag, type and scroll in the agent's browser. It is the only code that touches the browser during a student run |
| `automation/_work/student_extract.py` | Pulls the student's findings out of each run, with best-effort masking of the course-database password |
| `automation/_work/student_report.py` | Turns the findings into a review page |
| `steering/style.md` | The manual's style guide and "David's Review Rules": my corrections, turned into rules the agent applies every time |
| `requirements.txt` | The Python packages the scripts import |

**What an `ex_*.py` module looks like.** The per-exercise modules that `make_draft.py` imports aren't published,
but the contract is small. Each defines `HEADING` (the exercise's heading, which `make_draft.py` prints) and
`apply(d)`, which edits the python-docx `Document` `d` in place; `make_draft.py` calls them in the order of its
`EXERCISES` list, then fixes the step numbering and runs the layout passes. A module that rewrites a whole
instruction table calls `build_lib.rebuild(d, heading, steps, shots, completed)`: `heading` is the heading text
exactly as in the manual, `steps` is a list of step dicts (the keys and the text mini-markup are in `build_lib.py`'s
docstring; `shot` names an annotated screenshot), `shots` is the folder of annotated PNGs, and `completed` names
the Completed Results picture. Smaller changes use helpers such as `set_para`, `add_bullet_after`, `swap_run` and
`swap_image`.

### How a run went

1. `start_browser.ps1` opens the agent's Chrome, and I sign in to QuickSight in it.
2. For each exercise, a step script (not published) imports `_work/common.py`, works through the exercise in that
   browser and calls `qs.capture()`, which saves each screenshot with a JSON file of the marked elements' boxes.
3. An annotation script per exercise (not published) uses `annotate.py` to crop, mark and number those
   screenshots.
4. `build.py` runs `make_draft.py` (master copied to the draft, every `ex_*.py` applied, layout passes), renders
   the draft with `_work/render.ps1`, checks the step numbers with `_work/scan_numbers.py` and makes contact
   sheets. `_work/pdf_page.py` and `_work/ocr_find.py` are for a closer look.
5. `review_pack.py` builds the master-versus-draft page; `review_new.py` builds the "changed since your last
   review" page, and `review_new.py --mark-reviewed` takes a snapshot once I've finished a review.
6. I rule on what I see; the agent changes the scripts and goes back to step 4, or to step 2 for a recapture.
7. For the AI student, `_work/student_walk.py prepare` makes one folder per run (manual pages and course
   downloads), `_work/student_server.py` starts in the background, and `student_walk.py prompt` prints the
   instructions for one subagent, which works through its exercises.
8. `_work/student_extract.py` saves each run's findings and prints its "Where I stopped" note, which goes into the
   next run's prompt.
9. `_work/student_report.py` combines the findings into one page, and I rule on them.

## What it needs, and what it costs

Windows (Word is driven through COM, a Windows-only automation interface), Python 3.8 or later, Microsoft Word,
Google Chrome, Tesseract OCR, and the Python packages in `requirements.txt` (Playwright, python-docx, PyMuPDF,
Pillow, pytesseract): `pip install -r requirements.txt`. Set the `TESSERACT_CMD` environment variable if Tesseract
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
| Chrome, own profile and debugging port | The browser the manual is walked and captured in | Free | n/a |
| AWS CLI | Listing and deleting objects by name in the product being documented; used by the agent in chat, not by these scripts | Free tool; your AWS account costs apply | n/a |
| The product you document (mine: QuickSight) | What the manual teaches | Your own account's costs | Any product you document |

The AI student ran on a Claude Sonnet subagent inside a paid Claude plan; budget several hours for a full walk of
the manual.

**PyMuPDF is AGPL-3.0** (or a commercial license). It isn't included here. If you distribute software that bundles
it, or offer it as a network service, the AGPL applies to you.

## What is not here

The course manual (the master and the draft), the per-exercise step, annotation and `ex_*.py` scripts, the
screenshots, the review pages, the session notes and the AI student's run records. They are course material, show
account details, or both. Some scripts mention files from that set:

- `automation/WALKTHROUGH_RULINGS.md`: my rulings on the AI student's findings and an "A1 number changes" table.
  `review_pack.py` adds them to its page when the file exists.
- `automation/review/baseline_s7.json` and `automation/_work/s9_since_s7.py`: the picture list from the session 7
  review page and the script that explained each change since. `review_new.py` needs them until the first
  `--mark-reviewed` snapshot exists.
- `automation/review/pdf_flags.json`: optional screenshot-check flags for `review_pack.py`.
- `automation/review/edge_samples.html`: the sample page of torn-edge styles that `annotate.py` mentions.
- `automation/_work/student_walk/draft_pages.json`, the exercise-to-page map the student scripts read, and
  `highlights.md` beside it, an optional "Read this first" section for the student report.
- The course download data: `student_walk.py` copies it from a `QuickSightJourney1/Data` folder next to the
  project folder.

## Safety

- **Keys never go in files or chats.** Nothing here contains a key. Placeholders in angle brackets, such as
  `<ANALYSIS_ID>`, mark values I removed.
- **The agent drives its own browser, and I sign in.** The scripts connect to a separate Chrome profile on its own
  debugging port, never an everyday browser.
- **Two local doors are open during a run.** While the debugging browser is open (port 9334) or the student server
  is running (port 8765), any program on the same computer can drive the signed-in session; neither asks for a
  token. Close the browser after a run, and don't leave it signed in overnight on a shared machine.
- **I run my agent with its permission prompts off.** Don't copy that. Keep the prompts on, and on a company
  computer start from the stricter settings in the starter kit's `use/settings/`.
- **Prompt injection is not solved.** An agent that reads a web page can be misled by hidden instructions in it.
  The AI student is a Claude subagent told to act only through the student tool (screenshots, clicks and typing in
  one browser), with a cap of 300 actions per run. That limit is an instruction plus the cap, not a sandbox; the
  only code that touches the browser is the local server, `_work/student_server.py`. It reduces the damage but
  doesn't prevent it.

## License and contact

MIT License, copyright 2026 GiddyUp Data LLC (see `LICENSE`). Third-party tools keep their own licenses. **The
GiddyUp Data name and logo are not licensed for reuse.** Questions or errors: open an issue. Pull requests are not
accepted for now. For anything sensitive, see [`SECURITY.md`](SECURITY.md).
