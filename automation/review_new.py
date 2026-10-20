"""What changed since David's last review: review/new.html. Only the steps whose picture (or, once a
snapshot exists, text) differs from what he last reviewed. Shares review/img/ with index.html.

    python review_new.py                   -> review/new.html
    python review_new.py --mark-reviewed   -> after David finishes a review: snapshot the draft into
                                              review/baseline/ so the next new.html compares against it

With a snapshot (review/baseline/manifest.json): each changed step shows "At your last review" next to
"Now", text changes included. Before the first snapshot it falls back to review/baseline_s7.json (the
session-7 pack's picture hashes, plus a reason per changed picture from _work/s9_since_s7.py; neither is
published): pictures only, shown next to the master with the reason. Either way, a picture that
was only re-saved (same pixels inside the frame) is listed at the bottom instead of shown as a change.
"""
import html
import io
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops

import review_pack as rp
import units

OUT = rp.OUT
BASE_DIR = OUT / "baseline"
MANIFEST = BASE_DIR / "manifest.json"
S7 = OUT / "baseline_s7.json"
EDGE = 32          # image px of frame (white margin + torn edge) ignored when comparing pixels
WHY = {"retaken": "Retaken", "recropped": "Crop / marks changed", "build": "Changed in the Word build",
       "rerendered": "Re-saved only", "changed": "Changed", "new": "New picture"}


# ---------- snapshot ----------

def mark_reviewed():
    dus, dblobs = units.load(rp.DRAFT)
    if BASE_DIR.exists():
        shutil.rmtree(BASE_DIR)
    (BASE_DIR / "img").mkdir(parents=True)
    for h, (_, blob) in dblobs.items():
        review_size(blob).save(BASE_DIR / "img" / f"{h[:16]}.png", optimize=True)
    MANIFEST.write_text(json.dumps(dict(
        when=datetime.now().isoformat(timespec="minutes"),
        draft=datetime.fromtimestamp(rp.DRAFT.stat().st_mtime).isoformat(timespec="minutes"),
        units=[dict(name=u.name, leaf=u.leaf, blocks=[b.__dict__ for b in u.blocks]) for u in dus]),
        ensure_ascii=False), encoding="utf-8")
    print(f"Snapshot of the draft ({len(dus)} exercises, {len(dblobs)} pictures) -> {BASE_DIR}")


def review_size(blob):
    im = Image.open(io.BytesIO(blob)).convert("RGB")
    if im.width > rp.MAX_W:
        im = im.resize((rp.MAX_W, round(im.height * rp.MAX_W / im.width)), Image.LANCZOS)
    return im


def same_pixels(a, b):
    """Same size and no real difference inside the frame (the border/torn edge may be redrawn)."""
    if a.size != b.size or min(a.size) <= 2 * EDGE:
        return a.size == b.size and a.tobytes() == b.tobytes()
    box = (EDGE, EDGE, a.width - EDGE, a.height - EDGE)
    diff = ImageChops.difference(a.crop(box), b.crop(box)).convert("L").point(lambda v: 255 if v > 40 else 0)
    return diff.getbbox() is None


def load_snapshot():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    us = [units.Unit(u["name"], u["leaf"], [units.Block(**{**b, "segs": [tuple(s) for s in b["segs"]]})
                                             for b in u["blocks"]]) for u in m["units"]]
    return m, us


# ---------- page ----------

def img_tag(src, w):
    style = f' style="width:{w * rp.PX_PER_IN:.0f}px"' if w else ""
    return f'<a href="{src}" target="_blank"><img loading="lazy" src="{src}"{style}></a>'


def main():
    if "--mark-reviewed" in sys.argv:
        return mark_reviewed()
    (OUT / "img").mkdir(parents=True, exist_ok=True)
    mus, mblobs = units.load(rp.MASTER)
    dus, dblobs = units.load(rp.DRAFT)
    blobs = {**mblobs, **dblobs}
    done = {}
    snap = MANIFEST.exists()
    if snap:
        meta, bus = load_snapshot()
        olds = {u.key: u for u in bus}
        since = f"your last review (snapshot {meta['when'].replace('T', ' ')}, draft of {meta['draft'].replace('T', ' ')})"
        left_label = "At your last review"
    else:
        s7 = json.loads(S7.read_text(encoding="utf-8"))
        seen, reasons = set(s7["hashes"]), s7.get("reasons", {})
        master = {h[:16] for h in mblobs}
        olds = {}
        for mu, du in pair_units(mus, dus):
            if du:
                olds[du.key] = mu
        since = "the session-7 review pack (2026-10-13 15:49), which you reviewed in session 8"
        left_label = "Master (students today)"

    def old_src(h):
        if snap:
            return f"baseline/img/{h[:16]}.png"
        return rp.save_image(h, blobs, done)

    nav, body, quiet = [], [], []
    tally = {}
    for k, du in enumerate(dus):
        ou = olds.get(du.key)
        if ou is None and not snap:
            continue
        items = rp.changes(ou, du) if ou else [(None, b) for b in du.blocks]
        shown = []
        for o, n in items:
            if n is None:
                if snap and o is not None:                      # removed since the last review
                    shown.append((o, n, ["removed"], []))
                continue
            text_changed = snap and (o is None or rp.norm(o.segs) != rp.norm(n.segs))
            whys, notes = [], []
            for i, h in enumerate(n.images):
                if snap:
                    if o is not None and h in o.images:
                        continue
                    prev = o.images[i] if o is not None and i < len(o.images) else None
                    if prev and (BASE_DIR / "img" / f"{prev[:16]}.png").exists() and same_pixels(
                            Image.open(BASE_DIR / "img" / f"{prev[:16]}.png").convert("RGB"), review_size(blobs[h][1])):
                        whys.append("rerendered")
                    else:
                        whys.append("changed" if prev else "new")
                    notes.append("")
                else:
                    if h[:16] in seen or h[:16] in master:
                        continue
                    r = reasons.get(h[:16], dict(why="changed", detail=""))
                    whys.append(r["why"]); notes.append(r.get("detail", ""))
            real = [w for w in whys if w != "rerendered"]
            if not real and not text_changed:
                if whys:
                    quiet.append((du.leaf, n))
                continue
            shown.append((o, n, real or ["text"], [x for w, x in zip(whys, notes) if w != "rerendered" and x]))
            for w in set(real or ["text"]):                 # steps, not pictures
                tally[w] = tally.get(w, 0) + 1
        if not shown:
            continue
        uid = f"n{k}"
        nav.append(f'<a href="#{uid}">{html.escape(du.leaf)}<span class="n">{len(shown)}</span></a>')
        s = [f'<section class="unit" id="{uid}"><header><h2>{html.escape(du.leaf)}</h2>'
             f'<span class="path">{html.escape(du.name)}</span>'
             f'<label class="reviewed"><input type="checkbox" class="rv" data-id="{uid}"> Reviewed</label></header>']
        for o, n, whys, notes in shown:
            tag = " · ".join(dict.fromkeys(WHY.get(w, w.capitalize()) for w in whys))
            if n is None:
                text = f'<div class="shared txt">{rp.render(rp.tokens(o.segs))}</div>'
            elif snap and o is not None and rp.norm(o.segs) != rp.norm(n.segs):
                lt, rt = rp.diff_html(o.segs, n.segs)
                text = f'<div class="cols"><div class="txt">{lt}</div><div class="txt">{rt}</div></div>'
            else:
                text = f'<div class="shared txt">{rp.render(rp.tokens(n.segs))}</div>' if n.text.strip() else ""
            left = "".join(img_tag(old_src(h), w) for h, w in zip(o.images, o.widths or [None] * len(o.images))) if o else ""
            right = rp.imgs_html(n, blobs, done) if n else ""
            note = "".join(f'<div class="why">{html.escape(x)}</div>' for x in notes)
            s.append(f'<div class="item"><div class="kind">{html.escape(tag)}</div>{text}'
                     f'<div class="cols"><div><div class="side">{left_label}</div>{left or "<p class=none>(no picture)</p>"}</div>'
                     f'<div><div class="side">Now</div>{note}{right or "<p class=none>(removed)</p>"}</div></div></div>')
        s.append("</section>")
        body.append("".join(s))

    quiet_html = ""
    if quiet:
        quiet_html = (f'<section class="unit" id="quiet"><header><h2>Re-saved only: no visible change ({len(quiet)})</h2></header>'
                      '<p class="lede">Same capture, same crop and marks. The files were re-saved after a frame-code change, '
                      'and the only pixel difference is the gray left border, 1 px further right (flush with the picture). '
                      'The review pack counted them as new because the files differ. Listed so nothing is hidden; no need to look.</p>'
                      '<details><summary>Show the list</summary><table class="notes"><tr><th>Exercise</th><th>Step</th></tr>'
                      + "".join(f"<tr><td>{html.escape(leaf)}</td><td>{html.escape(rp.re.sub(r'\s+', ' ', n.text).strip()[:140] or '(picture)')}</td></tr>"
                                for leaf, n in quiet) + "</table></details></section>")
    nshown = sum(tally.values())
    counts = ", ".join(f"{v} {WHY.get(k, k)}" for k, v in sorted(tally.items(), key=lambda kv: -kv[1]))
    text_notes = "" if snap else "".join(f"<li>{html.escape(t)}</li>" for t in s7.get("text_notes", []))
    if text_notes:
        text_notes = f'<div class="flags"><b>Text changes since then</b> (not tracked automatically before the first snapshot):<ul>{text_notes}</ul></div>'
    when = datetime.now().strftime("%Y-%m-%d %H:%M")
    css = rp.CSS + """
.why { font-size:13px; color:var(--accent); font-weight:600; margin:2px 0 4px; }
.item > .kind { color:var(--accent); font-weight:700; }
"""
    js = rp.JS.replace("qsj1-reviewed", "qsj1-new-reviewed")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Journey 1 Changes</title>
<style>{css}</style></head><body>
<nav><b>Changed since your last review</b><div class="path">{len(body)} exercises · {nshown} steps</div>
<h2>Exercises</h2>{''.join(nav)}{'<h2>Not changes</h2><a href="#quiet">Re-saved only<span class="n">' + str(len(quiet)) + '</span></a>' if quiet else ''}</nav>
<main><h1>Quick Sight Journey 1: changed since your last review</h1>
<p class="lede">Only the steps whose picture changed since {since}. That's {nshown} steps in {len(body)} exercises
({counts}). Left is {left_label.lower()}; right is the draft now, with the reason in orange. Click a picture to open it
full size. Tick <b>Reviewed</b> to cross an exercise off (this browser only). The full side-by-side is still
<a href="index.html">index.html</a>. Built {when} from the draft of {datetime.fromtimestamp(rp.DRAFT.stat().st_mtime):%Y-%m-%d %H:%M}.</p>
{text_notes}{''.join(body)}{quiet_html}</main><script>{js}</script></body></html>"""
    (OUT / "new.html").write_text(page, encoding="utf-8")
    print(f"{OUT / 'new.html'}: {nshown} changed steps in {len(body)} exercises ({counts}); {len(quiet)} re-saved only")


def pair_units(mus, dus):
    """Master/draft exercise pairs by heading path (as in review_pack)."""
    sm = rp.SequenceMatcher(None, [u.key for u in mus], [u.key for u in dus], autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (i2 - i1) == (j2 - j1):
            out += list(zip(mus[i1:i2], dus[j1:j2]))
        else:
            out += [(m, None) for m in mus[i1:i2]] + [(None, d) for d in dus[j1:j2]]
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
