"""Agentic "student" walkthrough of the draft (session 9): an AI follows the manual like a new student, using only
screenshots, mouse and keyboard (`_work/student_server.py`), and reports what was clear and what wasn't.

    python _work/student_walk.py prepare <base dir>          # one folder per run: manual pages + course downloads
    python _work/student_walk.py prompt <base dir> <run id>  # the student's instructions for that run
    python _work/student_server.py <base dir>/<run id>       # (background) then launch one subagent with the prompt

Runs go in order in one browser, signed in as a fresh student user; each continues where the last stopped.
Results: <run dir>/steps.md, findings in the subagent's final reply (copied to _work/student_walk/).
"""
import json
import shutil
import sys
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent.parent
PDF = HERE / "_work" / "render.pdf"
PAGES = HERE / "_work" / "student_walk" / "draft_pages.json"      # {leaf: [unit name, first page, last page]}
DOWNLOADS = HERE.parent.parent / "QuickSightJourney1" / "Data"    # the course download material

RUNS = [
    ("01_A", ["Connect to Data", "Create Analysis"]),
    ("02_B_athena", ["Connect to Athena"]),
    ("03_B_s3", ["Connect to S3 and Union"]),
    ("04_B_redshift", ["Join Using Redshift"]),
    ("05_B_postgres", ["Extra Credit: PostgreSQL"]),
    ("06_C1", ["Row vs Aggregate Level Calculations", "Row Level"]),
    ("07_C2", ["Table Calculations", "Level-Aware Calculations"]),
    ("08_D", ["No Code Conditional Formatting: Background", "No Code Conditional Formatting: Icon", "Themes"]),
    ("09_Add1", ["Table", "Pivot Table", "Heat Map"]),
    # runs 10+ split to <= 2 exercises (session 9: runs of 3 lost early screenshots to the image limit)
    ("10_Add2a", ["Clustered Bar", "Stacked Bar"]),
    ("10_Add2b", ["Side-by-Side Bar"]),
    ("11_Add3a", ["Line Chart", "Sparklines"]),
    ("11_Add3b", ["Stacked Area", "Combo Chart"]),
    ("12_Add4a", ["Donut", "Tree Map"]),
    ("12_Add4b", ["Word Cloud"]),
    ("13_Add5a", ["Filled Map", "Point Map"]),
    ("13_Add5b", ["Scatter Plot"]),
]

PROMPT = """You are playing a STUDENT in a usability test of a training manual for Quick Sight (AWS), a BI tool. You are a business analyst who knows Excel well but is new to Quick Sight. You follow the manual literally, one step at a time, using only what you see on the screen and what the manual tells you. Your job is to tell the author, honestly and specifically, what was clear, what was confusing, and where the manual and the screen disagree.

## This run
Exercises, in order: {exercises}.
{context}

## Your materials (read only these)
Run folder: {run}
- manual\\page_NNN.png: the manual pages exactly as students get them (two-column tables: step text left, screenshot right; orange boxes, arrows and numbers mark what to click). manual\\page_NNN.txt has the same page's text. Pages {first}-{last}. Start at the heading of the first exercise and stop after the last exercise's Completed Results / commentary; ignore other exercises on the first and last pages. Do every part of each exercise, including any Extra Credit, as a student who wants the full course would.
- downloads\\: the course download material a student has on their computer (only reachable through a file picker, see below).

Do NOT read, list or search any other files or folders, and do not use the web. Use Bash only for the student tool below and Read/Write only for the manual pages, the screenshots the tool returns, and your own notes in the run folder.

## How you use the computer
The only way to act is the student tool (run with Bash, absolute path):
  python "{run}\\student.py" shot
  python "{run}\\student.py" click X Y            [--right] [--double]
  python "{run}\\student.py" move X Y             (hover)
  python "{run}\\student.py" drag X1 Y1 X2 Y2
  python "{run}\\student.py" down X Y             (press and hold the mouse button; `move X Y` while held shows drop hints)
  python "{run}\\student.py" up X Y               (move there and release). Use down / move / up when the drop spot matters.
  python "{run}\\student.py" type "text"
  python "{run}\\student.py" key Enter            (Escape, Tab, Backspace, Control+A, ...)
  python "{run}\\student.py" scroll X Y DY        (DY > 0 scrolls down)
  python "{run}\\student.py" wait SECONDS         (max 10; use when the screen is still loading)
  python "{run}\\student.py" files                (when a file picker is open: list your course download folder)
  python "{run}\\student.py" upload NAME          (choose that file in the open file picker)
Every command prints the path of a NEW screenshot (1200 x 841 px). Read it after every action. X, Y are pixels in that screenshot, origin top-left. You have about {limit} actions; use them sensibly. Begin with `shot`.

## How to work each step
1. Read the step text and look at the step's picture on the manual page.
2. Find the control on the screen. If you can't find it right away, say so in your notes before trying alternatives.
3. Act, then check the new screenshot against what the manual says or shows should happen.
4. If you're stuck, make at most 3 sensible attempts (as a new user would: look around, hover, try the obvious place). If still stuck, record it and continue with the next step if you can. Don't use Quick Sight knowledge a newcomer wouldn't have; if you relied on outside knowledge or a guess, record that.
5. If something fails for a reason outside the manual (network, permissions, a database that doesn't answer, a service error), record it as an ENVIRONMENT issue, not a manual finding, and carry on as far as you can.

## Safety rules (absolute)
- Never delete anything unless a manual step tells you to. Never choose "Replace an existing dashboard" or overwrite anything you didn't create in this run.
- Never share, never change account or user settings, never sign out, never close the tab.
- Never type AWS sign-in credentials. If a sign-in page or AWS password prompt appears, STOP and report it. (Connection details for a course database that the manual itself gives you are part of the exercise: enter them exactly as the manual shows.)
- If a dialog asks something the manual doesn't cover, choose the option that changes the least (often Cancel), unless you need it to continue; note it.

## What to record
Keep "{run}\\steps.md" up to date as you go (one entry per manual step: exercise, step number, what you looked for, what you did, whether the screen matched the manual's picture/text (yes / partly / no, and how), confidence 1-5), so nothing is lost if you run out of actions.

Your FINAL REPLY must contain the full findings table (files may not save):
| # | Exercise | Step | Type | Severity | Manual says | What actually happened | Suggested fix |
Type = can't find control | picture doesn't match screen | step missing or out of order | ambiguous wording | had to guess / outside knowledge | unexpected result | environment | other.
Severity = Blocker (a student can't continue) | Wrong (text or picture doesn't match the screen or data) | Unclear (it works, but a student would hesitate) | Polish (typo, style, naming, capitalization).
Quote the manual exactly in "Manual says". Be specific (button and label names as they appear on screen). Record small things too: label wording or capitalization, dialogs that look different, extra or missing options, results that differ from the pictures.
After the table: "Completed Results comparison" for each exercise (your screen vs its Completed Results picture), "What was clear", and "Where I stopped" (the screen you left the browser on and anything you created: names of datasets, analyses, sheets, dashboards, themes)."""

CONTEXT = {
    "01_A": "The student user is brand new: this account has no datasets or analyses of yours yet, and you are already signed in (the Login exercise is done). The browser shows the Quick home page.",
    "default": "You are continuing the course in the same account. Earlier exercises were done by the previous part of this test (same student user), so the objects the manual expects from earlier exercises should exist. Here is the previous part's own note on where it stopped:\n{prev}",
}


def prepare(base):
    pages = json.loads(PAGES.read_text(encoding="utf-8"))
    pdf = fitz.open(PDF)
    for rid, exs in RUNS:
        run = base / rid
        (run / "manual").mkdir(parents=True, exist_ok=True)
        first, last = pages[exs[0]][1], pages[exs[-1]][2]
        for n in range(first, last + 1):
            pg = pdf[n - 1]
            (run / "manual" / f"page_{n:03d}.png").write_bytes(pg.get_pixmap(dpi=120).tobytes("png"))
            (run / "manual" / f"page_{n:03d}.txt").write_text(pg.get_text(), encoding="utf-8")
        if not (run / "downloads").exists():
            shutil.copytree(DOWNLOADS, run / "downloads")
        print(rid, exs, f"pages {first}-{last}")


def prompt(base, rid, prev="(no note)", limit=280):
    pages = json.loads(PAGES.read_text(encoding="utf-8"))
    exs = dict(RUNS)[rid]
    ctx = CONTEXT.get(rid) or CONTEXT["default"].format(prev=prev)
    return PROMPT.format(exercises=", ".join(f'"{e}"' for e in exs), context=ctx, run=str(base / rid),
                         first=pages[exs[0]][1], last=pages[exs[-1]][2], limit=limit)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, base = sys.argv[1], Path(sys.argv[2]).resolve()
    if cmd == "prepare":
        prepare(base)
    elif cmd == "prompt":
        print(prompt(base, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "(no note)"))
