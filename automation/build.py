"""One command: build the draft, render it with Word, check step numbers, contact-sheet what changed.

    python build.py                       build + render + number scan + sheets of changed exercises
    python build.py --no-render           build only (still reports which exercises changed)
    python build.py --sheets all          contact-sheet every exercise (or: none)
    python build.py --only "Line Chart" "Sparklines"    sheets for these exercises (any part of the name)

"Changed" means changed since the previous build (the draft on disk before this run).
Sheets go to _work/sheets/. Stops before building if the draft or render.pdf is open somewhere;
it never stops Word itself.
"""
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRAFT = HERE.parent / "QuickSight Journey 1 - draft.docx"
PDF = HERE / "_work" / "render.pdf"
SHEETS = HERE / "_work" / "sheets"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8")

import units  # noqa: E402

# Known scan_numbers result that is not a defect (handoff section 9: the Login URL wraps in the PDF)
KNOWN_SCAN = ("Login",)
# Pictures David accepted under 90% (session 9, 2026-10-13): (exercise, start of the row text). Counted, not listed.
ACCEPTED_UNDER_90 = [("Create Analysis", "Position the bar chart above the line chart"),
                     ("Create Analysis", "Completed Results"), ("Pivot Table", "Completed Results"),
                     ("Heat Map", "Completed Results"), ("Clustered Bar", "Completed Results"),
                     ("Line Chart", "Completed Results")]


def locked(path):
    if not path.exists():
        return False
    try:
        with open(path, "r+b"):
            return False
    except PermissionError:
        return True


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, cwd=HERE, **kw)


def contact_sheet(pdf, first, last, out):
    import io
    from PIL import Image
    ims = [Image.open(io.BytesIO(pdf[i - 1].get_pixmap(dpi=60).tobytes("png"))) for i in range(first, last + 1)]
    cols = 3
    rows = (len(ims) + cols - 1) // cols
    W, H = ims[0].size
    sheet = Image.new("RGB", (W * cols, H * rows), "gray")
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * W, (k // cols) * H))
    sheet.save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--sheets", choices=["changed", "all", "none"], default="changed")
    ap.add_argument("--only", nargs="+", metavar="NAME")
    a = ap.parse_args()

    for f in (DRAFT, PDF):
        if locked(f):
            ps = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE"], capture_output=True, text=True).stdout
            sys.exit(f"STOP: {f.name} is open in another program (close it and re-run).\n{ps.strip()}")

    before = {u.name: u.fingerprint() for u in units.load(DRAFT)[0]} if DRAFT.exists() else {}

    t0 = time.time()
    if run([sys.executable, "make_draft.py"], capture_output=True, text=True, encoding="utf-8").returncode:
        sys.exit("STOP: make_draft.py failed; run it directly to see the traceback.")
    after, _ = units.load(DRAFT)
    changed = [u for u in after if before.get(u.name) != u.fingerprint()]
    print(f"\nBuilt the draft. Exercises changed since the previous build: {len(changed)}")
    for u in changed:
        print("  -", u.name)
    fit = HERE / "_work" / "fit_report.json"
    if fit.exists():
        import json
        short = json.loads(fit.read_text(encoding="utf-8"))
        ok = [s for s in short if any(s["exercise"] == e and s["row"].strip().startswith(r) for e, r in ACCEPTED_UNDER_90)]
        short = [s for s in short if s not in ok]
        print(f"\nPictures under 90% (need a crop, cut-out, tear or recapture): {len(short)}"
              + (f" (+{len(ok)} accepted by David)" if ok else ""))
        for s in short:
            print(f"   {s['scale']:>3}% {s['width']:.2f}in ({s['limit']}) {s['exercise']}: {s['row'][:60]}")

    if a.no_render:
        return

    r = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "_work" / "render.ps1")],
            capture_output=True, text=True)
    if not PDF.exists() or PDF.stat().st_mtime < t0:
        sys.exit(f"STOP: Word did not write render.pdf.\n{r.stdout}\n{r.stderr}")
    import fitz
    pdf = fitz.open(PDF)
    blank = [i + 1 for i, pg in enumerate(pdf)
             if not re.sub(r"©\s*GiddyUp Data \d{4}|Page \d+|\s", "", pg.get_text()) and not pg.get_images()]
    print(f"Rendered {PDF.name}: {len(pdf)} pages." + (f" BLANK PAGES: {blank}" if blank else " No blank pages."))

    r = run([sys.executable, str(HERE / "_work" / "scan_numbers.py"), str(DRAFT), str(PDF)],
            capture_output=True, text=True, encoding="utf-8")
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    bad = [l for l in lines if not l.startswith("ok ")]
    unexpected = [l for l in bad if not any(k in l for k in KNOWN_SCAN)]
    print(f"\nStep numbering: {len(lines) - len(bad)} of {len(lines)} groups read 1, 2, 3...")
    for l in bad:
        print("  ", l, "" if l in unexpected else "(known: URL wraps in the PDF)")

    if a.only:
        pick = [u for u in after if any(n.lower() in u.name.lower() for n in a.only)]
    elif a.sheets == "all":
        pick = after
    elif a.sheets == "changed":
        pick = changed
    else:
        pick = []
    if pick:
        import fitz
        pdf = fitz.open(PDF)
        pages = units.locate_pages(after, pdf)
        SHEETS.mkdir(parents=True, exist_ok=True)
        for old in SHEETS.glob("*.png"):
            old.unlink()
        print(f"\nContact sheets ({SHEETS.relative_to(HERE)}):")
        names = {u.name for u in pick}
        for k, u in enumerate(after):
            if u.name not in names:
                continue
            if u.name not in pages:
                print(f"   ?? {u.name}: not found in the PDF")
                continue
            first, last = pages[u.name]
            slug = re.sub(r"[^A-Za-z0-9]+", "_", u.leaf).strip("_")[:40]
            out = SHEETS / f"{k:02d}_{slug}.png"
            contact_sheet(pdf, first, last, out)
            print(f"   pages {first}-{last}  {out.name}")

    sys.exit(1 if unexpected else 0)


if __name__ == "__main__":
    main()
