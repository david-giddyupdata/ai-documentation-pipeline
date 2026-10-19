"""Helpers for driving the Quick Sight walkthrough browser.

The browser is a normal Chrome window started by start_browser.ps1 with its own
profile (outside any cloud-synced folder) and remote-debugging port 9334. Step scripts connect
to it, act, and save numbered screenshots for the manual.

    from qs import page, shot, peek
    p = page("quicksight")
    shot(p, "new_sheet", clip=(x, y, w, h))   # -> screenshots/<EXERCISE>/NN_new_sheet.png
"""
import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9334"
HERE = Path(__file__).resolve().parent
EXERCISE = os.environ.get("QS_EXERCISE", "Table_Calculations")
SHOT_DIR = HERE / "screenshots" / EXERCISE
WORK = HERE / "_work"

_pw = None
_browser = None
# CDP session that set the device-metrics override (common.py sets it). Playwright's own
# screenshot ignores the emulated devicePixelRatio when the window's real dpr is 1, so
# full-viewport shots go through this session to stay at 2x.
CDP = None


def browser():
    global _pw, _browser
    if _browser is None:
        _pw = sync_playwright().start()
        _browser = _pw.chromium.connect_over_cdp(CDP_URL)
    return _browser


def page(url_contains=None):
    """Return the tab whose URL contains url_contains, else the last tab."""
    ctx = browser().contexts[0]
    pages = ctx.pages
    if url_contains:
        for pg in pages:
            if url_contains in pg.url:
                pg.bring_to_front()
                return pg
    return pages[-1] if pages else ctx.new_page()


def _next_number():
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for f in SHOT_DIR.glob("*.png")
            if (m := re.match(r"(\d+)_", f.name))]
    return max(nums, default=0) + 1


def shot(pg, name, clip=None, full_page=False):
    """Save a numbered screenshot and print its path. clip = (x, y, w, h) in CSS px."""
    path = SHOT_DIR / f"{_next_number():02d}_{name}.png"
    if CDP is not None and not clip and not full_page:
        import base64
        path.write_bytes(base64.b64decode(CDP.send("Page.captureScreenshot", {"format": "png"})["data"]))
        print(path)
        return path
    kwargs = {"path": str(path), "full_page": full_page}
    if clip:
        kwargs["clip"] = dict(zip(("x", "y", "width", "height"), clip))
    pg.screenshot(**kwargs)
    print(path)
    return path


def capture(pg, name, marks=None):
    """Full-viewport numbered screenshot plus a JSON sidecar with the CSS-px boxes of
    marks ({label: locator or (x, y, w, h)}) and the device pixel ratio, so crops and
    annotations are computed instead of hand-measured."""
    path = shot(pg, name)
    boxes = {}
    for label, m in (marks or {}).items():
        boxes[label] = m if isinstance(m, tuple) else box(m)
    meta = {"dpr": pg.evaluate("devicePixelRatio"),
            "viewport": pg.evaluate("[innerWidth, innerHeight]"),
            "boxes": boxes}
    path.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    return path


def peek(pg, name="_peek"):
    """Unnumbered working screenshot (not for the manual)."""
    path = WORK / f"{name}.png"
    path.parent.mkdir(exist_ok=True)
    if CDP is not None:
        import base64
        path.write_bytes(base64.b64decode(CDP.send("Page.captureScreenshot", {"format": "png"})["data"]))
    else:
        pg.screenshot(path=str(path))
    print(path)
    return path


def box(loc):
    """Bounding box of a locator as (x, y, w, h) in CSS px."""
    try:
        b = loc.bounding_box(timeout=2000)
    except Exception:
        print("  (no box for", loc, ")")
        return None
    return (b["x"], b["y"], b["width"], b["height"]) if b else None


def tabs():
    for i, pg in enumerate(browser().contexts[0].pages):
        print(i, pg.url)


if __name__ == "__main__":
    # python qs.py tabs | python qs.py peek [url_part]
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tabs"
    if cmd == "tabs":
        tabs()
    elif cmd == "peek":
        peek(page(sys.argv[2] if len(sys.argv) > 2 else None))
