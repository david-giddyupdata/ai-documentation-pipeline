"""Review pack: what changed between the master and the draft, side by side, one exercise at a time.

    python review_pack.py            -> review/index.html (+ review/img/); open it in a browser

Left = master (what students have now), right = draft. Only changed text and pictures are shown;
step numbers are automatic in Word, so renumbering alone never shows up. Each exercise also lists
its walkthrough rulings and A1 number changes (both from WALKTHROUGH_RULINGS.md, which is not published;
skipped when the file is missing), and any screenshot-check flags from review/pdf_flags.json:

    [{"unit": "Line Chart", "page": 210, "where": "step 5", "severity": "fix" | "check", "issue": "..."}]

"unit" is the exercise heading as printed (case ignored); unmatched flags are reported when the pack is built.
"""
import html
import io
import json
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image

import units

HERE = Path(__file__).resolve().parent
MASTER = HERE.parent / "QuickSight Journey 1.docx"
DRAFT = HERE.parent / "QuickSight Journey 1 - draft.docx"
OUT = HERE / "review"
FLAGS = OUT / "pdf_flags.json"
RULINGS = HERE / "WALKTHROUGH_RULINGS.md"
MAX_W = 1600

# WALKTHROUGH_RULINGS.md exercise column -> unit leaf (heading text)
EX_MAP = {
    "A / Connect to Data": "Connect to Data", "A / Create Analysis": "Create Analysis",
    "B / Athena": "Connect to Athena", "B / S3 Union": "Connect to S3 and Union",
    "B / Redshift": "Join Using Redshift", "B / PostgreSQL": "Extra Credit: PostgreSQL",
    "C / Row vs Agg": "Row vs Aggregate Level Calculations", "C / Row Level": "Row Level",
    "C / Table Calcs": "Table Calculations", "C / LACs": "Level-Aware Calculations",
    "D / Background": "No Code Conditional Formatting: Background",
    "D / Icon": "No Code Conditional Formatting: Icon", "D / Themes": "Themes",
    "Add / Table": "Table", "Add / Pivot": "Pivot Table", "Add / Heat Map": "Heat Map",
    "Add / Clustered": "Clustered Bar", "Add / Stacked": "Stacked Bar", "Add / Side-by-Side": "Side-by-Side Bar",
}
# A1 table "Where" prefixes -> unit leaf (hard-coded for one review cycle, like EX_MAP above)
A1_MAP = [("Explanation of Datasets", "Explanation of Datasets"), ("Table Calculations", "Table Calculations"),
          ("Heat Map", "Heat Map"), ("Addendum > Table", "Table"), ("Row Level", "Row Level")]

TOK = re.compile(r"\s+|[\w’'%.,:/-]+|[^\w\s]")


# ---------- text ----------

def norm(segs):
    """Collapse spacing, ignore bold on blank runs, merge neighbors; for comparing and diffing."""
    out = []
    for t, b in segs:
        t = re.sub(r"[ \t ]+", " ", t)
        b = b and bool(t.strip())
        if out and out[-1][1] == b:
            out[-1] = (out[-1][0] + t, b)
        elif t:
            out.append((t, b))
    if out:
        out[0] = (out[0][0].lstrip(), out[0][1])
        out[-1] = (out[-1][0].rstrip(), out[-1][1])
    return [s for s in out if s[0]]


def tokens(segs):
    return [(tok, b) for t, b in norm(segs) for tok in TOK.findall(t)]


def render(toks):
    out = []
    for tok, b in toks:
        t = html.escape(tok).replace("\n", "<br>")
        out.append(f"<b>{t}</b>" if b and tok.strip() else t)
    return "".join(out)


def diff_html(a, b):
    ta, tb = tokens(a), tokens(b)
    sm = SequenceMatcher(None, ta, tb, autojunk=False)
    left, right = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            left.append(render(ta[i1:i2])); right.append(render(tb[j1:j2]))
        else:
            if i2 > i1: left.append(f"<del>{render(ta[i1:i2])}</del>")
            if j2 > j1: right.append(f"<ins>{render(tb[j1:j2])}</ins>")
    return "".join(left), "".join(right)


# ---------- alignment ----------

def same(a, b):
    return norm(a.segs) == norm(b.segs) and a.images == b.images


def pair(olds, news):
    """Pair blocks inside a replaced range, keeping document order: the in-order pairing with the highest
    total text similarity (each pair at least 0.4). Leftovers are removed / added. Greedy best-match
    paired a step with a look-alike step further down (Themes "Create theme" vs "select the theme")."""
    def sim(a, b):
        if (a.key == "<image>") != (b.key == "<image>"):
            return 0.0
        if a.key == "<image>":
            return 1.0
        s = SequenceMatcher(None, a.key, b.key, autojunk=False).ratio()
        return s if s >= 0.4 else 0.0

    n, m = len(olds), len(news)
    S = [[sim(o, nb) for nb in news] for o in olds]
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            take = S[i][j] + best[i + 1][j + 1] if S[i][j] else 0.0
            best[i][j] = max(best[i + 1][j], best[i][j + 1], take)
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if S[i][j] and best[i][j] == S[i][j] + best[i + 1][j + 1]:
            pairs.append((olds[i], news[j])); i += 1; j += 1
        elif best[i][j] == best[i + 1][j]:
            pairs.append((olds[i], None)); i += 1
        else:
            pairs.append((None, news[j])); j += 1
    return pairs + [(o, None) for o in olds[i:]] + [(None, nb) for nb in news[j:]]


def changes(mu, du):
    # blank paragraphs (only a line or page break) are layout, not content: the build moves page breaks
    # onto headings, which would otherwise show as "removed" in a dozen exercises
    mb = [b for b in mu.blocks if b.text.strip() or b.images]
    db = [b for b in du.blocks if b.text.strip() or b.images]
    sm = SequenceMatcher(None, [b.key for b in mb], [b.key for b in db], autojunk=False)
    items = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            prs = list(zip(mb[i1:i2], db[j1:j2]))
        else:
            prs = pair(mb[i1:i2], db[j1:j2])
        for o, n in prs:
            if o and n and same(o, n):
                continue
            items.append((o, n))
    return items


def label(o, n):
    if o is None:
        return "added"
    if n is None:
        return "removed"
    text = norm(o.segs) != norm(n.segs)
    fmt = text and re.sub(r"\s+", " ", o.text).strip() == re.sub(r"\s+", " ", n.text).strip()
    img = o.images != n.images
    parts = (["formatting"] if fmt else ["text"] if text else []) + (["picture"] if img else [])
    return " + ".join(parts)


# ---------- notes ----------

def rulings():
    by_leaf, seen = {}, set()
    if not RULINGS.exists():
        return by_leaf
    for line in RULINGS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|(.*)", line)
        if not m:
            continue
        cols = [c.strip() for c in m.group(2).split("|")]
        if len(cols) < 7:
            continue
        ex, step, sev, issue, ruling, note, status = cols[:7]
        k = (m.group(1), issue)
        if k in seen or ex not in EX_MAP:
            continue
        seen.add(k)
        by_leaf.setdefault(EX_MAP[ex], []).append(dict(n=m.group(1), step=step, sev=sev, issue=issue,
                                                       ruling=ruling, note=note, status=status))
    return by_leaf


def a1_changes():
    if not RULINGS.exists():
        return {}
    text = RULINGS.read_text(encoding="utf-8")
    sec = text.split("## A1 number changes", 1)[-1].split("\n## ", 1)[0]
    by_leaf, last = {}, None
    for line in sec.splitlines():
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 3 or cols[0] in ("Where", "---") or set(cols[0]) <= set("-"):
            continue
        where = cols[0]
        leaf = next((v for k, v in A1_MAP if k in where), None)
        if leaf is None and where.startswith("…"):
            leaf = last
        if leaf:
            last = leaf
            by_leaf.setdefault(leaf, []).append(dict(where=where, before=cols[1], after=cols[2]))
    return by_leaf


def status_html(f):
    st = f.get("status")
    if not st:
        return ""
    cls = "st-fixed" if st.startswith("fixed") else "st-left"
    return f' <span class="{cls}">→ {html.escape(st)}</span>'


def flags():
    if not FLAGS.exists():
        return []
    return json.loads(FLAGS.read_text(encoding="utf-8"))


# ---------- images ----------

def save_image(h, blobs, done):
    if h in done:
        return done[h]
    name, blob = blobs[h]
    out = OUT / "img" / f"{h[:16]}.png"
    if not out.exists():
        im = Image.open(io.BytesIO(blob))
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        im.save(out, optimize=True)
    done[h] = f"img/{out.name}"
    return done[h]


PX_PER_IN = 100   # pictures show at their width in the manual, so old and new compare like-for-like


def imgs_html(block, blobs, done):
    out = []
    for h, w in zip(block.images, block.widths or [None] * len(block.images)):
        src = save_image(h, blobs, done)
        style = f' style="width:{w * PX_PER_IN:.0f}px"' if w else ""
        out.append(f'<a href="{src}" target="_blank"><img loading="lazy" src="{src}"{style}></a>')
    return "".join(out)


# ---------- page ----------

CSS = """
:root { --bg:#fff; --fg:#1d1d1f; --muted:#6b6b70; --line:#e2e2e6; --panel:#f6f6f8; --del:#fde2e1; --delfg:#9b1c1c;
        --ins:#dcf5e3; --insfg:#14632f; --accent:#c77800; --flag:#fff4d6; --flagline:#f4ac08; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 "Segoe UI", system-ui, sans-serif; }
nav { position:fixed; top:0; left:0; bottom:0; width:290px; overflow:auto; background:var(--panel);
      border-right:1px solid var(--line); padding:16px 12px; font-size:13px; }
nav h2 { font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); margin:16px 4px 6px; }
nav a { display:flex; gap:6px; align-items:baseline; padding:3px 4px; color:var(--fg); text-decoration:none; border-radius:4px; }
nav a:hover { background:var(--line); }
nav a.done { color:var(--muted); text-decoration:line-through; }
nav .n { margin-left:auto; color:var(--muted); font-variant-numeric:tabular-nums; }
nav .f { color:var(--accent); font-weight:600; }
main { margin-left:290px; padding:24px 32px 80px; max-width:1700px; }
h1 { font-size:24px; margin:0 0 4px; }
.lede { color:var(--muted); margin:0 0 20px; max-width:900px; }
section.unit { border-top:2px solid var(--fg); margin-top:40px; padding-top:12px; }
section.unit > header { display:flex; align-items:baseline; gap:16px; flex-wrap:wrap; }
section.unit h2 { font-size:20px; margin:0; }
.path { color:var(--muted); font-size:13px; }
.reviewed { margin-left:auto; font-size:13px; }
details { margin:10px 0; background:var(--panel); border-radius:6px; padding:6px 12px; }
summary { cursor:pointer; font-weight:600; font-size:14px; }
table.notes { border-collapse:collapse; font-size:13px; margin:8px 0; width:100%; }
table.notes td, table.notes th { border-top:1px solid var(--line); padding:4px 8px; text-align:left; vertical-align:top; }
.flags { background:var(--flag); border-left:4px solid var(--flagline); padding:8px 12px; margin:10px 0; border-radius:4px; }
.flags li { margin:4px 0; }
.sev-fix { color:var(--delfg); font-weight:700; }
.st-fixed { color:var(--insfg); font-weight:600; }
.st-left { color:var(--muted); font-style:italic; }
.item { border:1px solid var(--line); border-radius:6px; margin:14px 0; overflow:hidden; }
.item > .kind { background:var(--panel); padding:4px 12px; font-size:12px; text-transform:uppercase;
                letter-spacing:.05em; color:var(--muted); border-bottom:1px solid var(--line); }
.cols { display:grid; grid-template-columns:1fr 1fr; }
.cols > div { padding:10px 12px; min-width:0; }
.cols > div + div { border-left:1px solid var(--line); }
.side { font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin-bottom:4px; }
.txt { white-space:normal; }
.shared { padding:10px 12px; border-bottom:1px solid var(--line); }
.below { padding:6px 12px 10px; border-top:1px solid var(--line); background:var(--panel); }
.none { color:var(--muted); font-style:italic; }
del { background:var(--del); color:var(--delfg); text-decoration:line-through; }
ins { background:var(--ins); color:var(--insfg); text-decoration:none; }
img { max-width:100%; height:auto; display:block; margin:8px 0; border:1px solid var(--line); }
.empty { color:var(--muted); }
@media (max-width:900px) { nav { display:none; } main { margin-left:0; padding:16px; } .cols { grid-template-columns:1fr; }
  .cols > div + div { border-left:0; border-top:1px solid var(--line); } }
"""

JS = """
const KEY = 'qsj1-reviewed';
let st = {}; try { st = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
function paint(id) { const a = document.querySelector('nav a[href="#' + id + '"]'); if (a) a.classList.toggle('done', !!st[id]); }
document.querySelectorAll('input.rv').forEach(cb => {
  cb.checked = !!st[cb.dataset.id]; paint(cb.dataset.id);
  cb.addEventListener('change', () => { st[cb.dataset.id] = cb.checked; paint(cb.dataset.id);
    try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} });
});
"""


def main():
    (OUT / "img").mkdir(parents=True, exist_ok=True)
    mus, mblobs = units.load(MASTER)
    dus, dblobs = units.load(DRAFT)
    blobs = {**mblobs, **dblobs}
    rl, a1, fl = rulings(), a1_changes(), flags()
    done = {}

    # pair units by heading path (spacing / case folded)
    sm = SequenceMatcher(None, [u.key for u in mus], [u.key for u in dus], autojunk=False)
    upairs = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (i2 - i1) == (j2 - j1):
            upairs += list(zip(mus[i1:i2], dus[j1:j2]))
        else:
            upairs += [(m, None) for m in mus[i1:i2]] + [(None, d) for d in dus[j1:j2]]

    nav, body, flag_rows = [], [], []
    tot = dict(items=0, units=0, flags=len(fl))
    current_h1 = None
    for k, (mu, du) in enumerate(upairs):
        u = du or mu
        uid = f"u{k}"
        items = changes(mu, du) if (mu and du) else [(b, None) for b in mu.blocks] if mu else [(None, b) for b in du.blocks]
        ufl = [f for f in fl if f.get("unit", "").lower() == u.leaf.lower()]
        notes_r, notes_a = rl.get(u.leaf, []), a1.get(u.leaf, [])
        if not items and not ufl:
            continue
        flag_rows += [(f, uid, u.leaf) for f in ufl]
        tot["items"] += len(items); tot["units"] += 1
        h1 = u.name.split(" > ")[0]
        if h1 != current_h1:
            nav.append(f"<h2>{html.escape(h1)}</h2>"); current_h1 = h1
        fmark = f' <span class="f">⚑{len(ufl)}</span>' if ufl else ""
        nav.append(f'<a href="#{uid}">{html.escape(u.leaf)}{fmark}<span class="n">{len(items)}</span></a>')

        s = [f'<section class="unit" id="{uid}"><header><h2>{html.escape(u.leaf)}</h2>'
             f'<span class="path">{html.escape(u.name)}</span>'
             f'<label class="reviewed"><input type="checkbox" class="rv" data-id="{uid}"> Reviewed</label></header>']
        if ufl:
            s.append('<div class="flags"><b>Screenshot check flags</b><ul>' + "".join(
                f'<li><span class="sev-{html.escape(f.get("severity", "check"))}">{html.escape(f.get("severity", "check").upper())}</span> '
                f'page {f.get("page", f.get("page_s7", "?"))}{" (session 7)" if "page_s7" in f else ""}, {html.escape(str(f.get("where", "")))}: {html.escape(f.get("issue", ""))}'
                f'{status_html(f)}</li>' for f in ufl) + "</ul></div>")
        if notes_r:
            s.append(f"<details><summary>Walkthrough rulings for this exercise ({len(notes_r)})</summary>"
                     '<table class="notes"><tr><th>#</th><th>Step</th><th>Severity</th><th>Issue</th><th>Ruling</th><th>Note</th><th>Status</th></tr>'
                     + "".join(f"<tr><td>{r['n']}</td><td>{html.escape(r['step'])}</td><td>{html.escape(r['sev'])}</td>"
                               f"<td>{html.escape(r['issue'])}</td><td>{html.escape(r['ruling'])}</td>"
                               f"<td>{html.escape(r['note'])}</td><td>{html.escape(r['status'])}</td></tr>" for r in notes_r)
                     + "</table></details>")
        if notes_a:                     # "72-month data": the data refresh of that review cycle (hard-coded)
            s.append(f"<details><summary>Number changes from the 72-month data ({len(notes_a)})</summary>"
                     '<table class="notes"><tr><th>Where</th><th>Before</th><th>After</th></tr>'
                     + "".join(f"<tr><td>{html.escape(a['where'])}</td><td>{html.escape(a['before'])}</td>"
                               f"<td>{html.escape(a['after'])}</td></tr>" for a in notes_a) + "</table></details>")
        if not items:
            s.append('<p class="empty">No text or picture changes.</p>')
        for o, n in items:
            kind = label(o, n)
            shared = below = ""
            if o and n and norm(o.segs) == norm(n.segs):          # picture only: text once, above
                shared = f'<div class="shared txt">{render(tokens(n.segs))}</div>' if n.text.strip() else ""
                left, right = imgs_html(o, blobs, done), imgs_html(n, blobs, done)
            else:
                if o and n:
                    lt, rt = diff_html(o.segs, n.segs)
                else:
                    lt = render(tokens(o.segs)) if o else ""
                    rt = render(tokens(n.segs)) if n else ""
                pic_same = bool(o and n and o.images == n.images)
                lt = (f'<div class="txt">{lt}</div>' if lt else "") + (imgs_html(o, blobs, done) if o and not pic_same else "")
                rt = (f'<div class="txt">{rt}</div>' if rt else "") + (imgs_html(n, blobs, done) if n and not pic_same else "")
                left = lt if o else '<p class="none">(not in the master)</p>'
                right = rt if n else '<p class="none">(removed in the draft)</p>'
                if pic_same and n.images:                            # text only: unchanged picture once, below
                    below = f'<div class="below"><div class="side">Picture (unchanged)</div>{imgs_html(n, blobs, done)}</div>'
            s.append(f'<div class="item"><div class="kind">{html.escape(kind)}</div>{shared}'
                     f'<div class="cols"><div><div class="side">Master</div>{left}</div>'
                     f'<div><div class="side">Draft</div>{right}</div></div>{below}</div>')
        s.append("</section>")
        body.append("".join(s))

    unplaced = [f for f in fl if not any(f is r[0] for r in flag_rows)]
    if unplaced:
        print("WARNING: flags with no matching exercise:", [f.get("unit") for f in unplaced])
    summary = ""
    if flag_rows:
        nfix = sum(1 for f, _, _ in flag_rows if f.get("severity") == "fix")
        nres = sum(1 for f, _, _ in flag_rows if f.get("status", "").startswith("fixed"))
        summary = (f'<div class="flags"><b>Screenshot check of the rendered draft (session 7): {len(flag_rows)} flags '
                   f'({nfix} fix, {len(flag_rows) - nfix} check); {nres} fixed in session 8.</b> Page numbers are from the session 7 render. '
                   '<b>FIX</b> = text and picture disagree; <b>CHECK</b> = needs your eye (legibility, layout, a stray mark).<ul>'
                   + "".join(f'<li><span class="sev-{html.escape(f.get("severity", "check"))}">{html.escape(f.get("severity", "check").upper())}</span> '
                             f'<a href="#{uid}">{html.escape(leaf)}</a>, page {f.get("page", f.get("page_s7", "?"))}, {html.escape(str(f.get("where", "")))}: '
                             f'{html.escape(f.get("issue", ""))}{status_html(f)}</li>'
                             for f, uid, leaf in sorted(flag_rows, key=lambda r: r[0].get("page", r[0].get("page_s7", 0))))
                   + "</ul></div>")

    when = datetime.now().strftime("%Y-%m-%d %H:%M")
    # The summary above and the lede below are worded for one review cycle (sessions 6-8): hard-coded.
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Journey 1 Review Pack</title>
<style>{CSS}</style></head><body>
<nav><b>Journey 1 review pack</b><div class="path">{tot['units']} exercises · {tot['items']} changes{f" · ⚑ {tot['flags']} flags" if tot['flags'] else ""}</div>{''.join(nav)}</nav>
<main><h1>Quick Sight Journey 1: master vs draft</h1>
<p class="lede">Left is the master (what students have now); right is the draft. Only changed text and pictures are shown.
<del>Red</del> was removed, <ins>green</ins> was added; bold is kept, so a change in bold shows as "formatting".
Step numbers are automatic in Word, so renumbering alone never appears. Most picture changes are the session 6 retakes on the
72-month data (Jan 2020 through Dec 2025). Click a picture to open it full size. Tick <b>Reviewed</b> to cross an exercise off in the
list (this browser only). Built {when} from the draft of {datetime.fromtimestamp(DRAFT.stat().st_mtime):%Y-%m-%d %H:%M}.</p>
{summary}{''.join(body)}</main><script>{JS}</script></body></html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    used = set(done.values())
    for other in OUT.glob("*.html"):                    # new.html (review_new.py) shares img/
        if other.name != "index.html":
            used |= set(re.findall(r'src="(img/[0-9a-f]{16}\.png)"', other.read_text(encoding="utf-8")))
    for f in (OUT / "img").glob("*.png"):
        if f"img/{f.name}" not in used:
            f.unlink()
    size = sum(f.stat().st_size for f in (OUT / "img").glob("*.png")) / 1e6
    print(f"{OUT / 'index.html'}: {tot['units']} exercises, {tot['items']} changes, {len(used)} pictures ({size:.0f} MB), {tot['flags']} flags")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
