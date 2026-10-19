"""Combine the student walkthrough runs into one page: review/student.html.

    python _work/student_report.py

Reads _work/student_walk/NN_*_findings.md (each run's final reply: a findings table plus "Completed Results
comparison", "What was clear", "Where I stopped"). Findings are grouped by exercise in manual order and can be
filtered by severity; environment rows are kept apart from manual findings.
"""
import html
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
WALK = HERE / "_work" / "student_walk"
OUT = HERE / "review" / "student.html"
SEV = ["Blocker", "Wrong", "Unclear", "Polish"]
PAGES = WALK / "draft_pages.json"            # manual order of the exercises
ALIASES = {"PostgreSQL": "Extra Credit: PostgreSQL", "Row vs Aggregate": "Row vs Aggregate Level Calculations",
           "Table Calcs": "Table Calculations", "LACs": "Level-Aware Calculations",
           "CF: Background": "No Code Conditional Formatting: Background",
           "CF: Icon": "No Code Conditional Formatting: Icon"}
RUN_GENERIC = {"06_C1": "Row Level", "08_D": "D-Formatting (all three exercises)",
               "11_Add3a": "Line Chart"}      # rows labelled "Extra Credit", "Overall", "Both"


def exercise(name, run):
    name = ALIASES.get(name, name)
    if name in ("Extra Credit", "Overall", "Both", "All", "all", ""):
        return RUN_GENERIC.get(run, name or run)
    return name


def unesc(s):
    return html.unescape(s).replace("\\|", "|").strip()


def parse(md):
    rows, sections = [], {}
    for line in md.splitlines():
        if re.match(r"^\|\s*\d+\s*\|", line):
            cols = [unesc(c) for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            if len(cols) >= 8:
                rows.append(dict(n=cols[0], ex=cols[1], step=cols[2], type=cols[3], sev=cols[4],
                                 says=cols[5], happened=cols[6], fix=cols[7]))
    for m in re.finditer(r"^#+\s*(.+?)\s*\n(.*?)(?=^#+\s|\Z)", md, re.S | re.M):
        title = m.group(1).strip()
        if not re.search(r"findings", title, re.I):
            sections[title] = m.group(2).strip()
    return rows, sections


def md_html(s):
    """Minimal Markdown: paragraphs, bullets, bold, inline code, tables left as text."""
    out, in_ul = [], False
    for line in s.splitlines():
        t = html.escape(unesc(line))
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        if re.match(r"^\s*[-*]\s+", line):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append("<li>" + re.sub(r"^\s*[-*]\s+", "", t) + "</li>")
            continue
        if in_ul:
            out.append("</ul>"); in_ul = False
        if t.strip():
            out.append(f"<p>{t}</p>")
    if in_ul:
        out.append("</ul>")
    return "".join(out)


def sev_of(r):
    s = r["sev"].strip().split()[0].capitalize() if r["sev"].strip() else "Polish"
    if "environment" in r["type"].lower():
        return "Environment"
    return s if s in SEV else "Polish"


CSS = """
:root { --bg:#fff; --fg:#1d1d1f; --muted:#6b6b70; --line:#e2e2e6; --panel:#f6f6f8; --accent:#c77800;
        --blocker:#9b1c1c; --wrong:#b45309; --unclear:#1d4ed8; --polish:#6b6b70; --env:#047857; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 "Segoe UI", system-ui, sans-serif; }
nav { position:fixed; top:0; left:0; bottom:0; width:270px; overflow:auto; background:var(--panel);
      border-right:1px solid var(--line); padding:16px 12px; font-size:13px; }
nav a { display:flex; gap:6px; padding:3px 4px; color:var(--fg); text-decoration:none; border-radius:4px; }
nav a:hover { background:var(--line); } nav .n { margin-left:auto; color:var(--muted); }
main { margin-left:270px; padding:24px 32px 80px; max-width:1600px; }
h1 { font-size:24px; margin:0 0 4px; } h2 { font-size:19px; margin:36px 0 6px; border-top:2px solid var(--fg); padding-top:10px; }
h3 { font-size:14px; margin:14px 0 4px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
.lede { color:var(--muted); max-width:1000px; }
.bar { display:flex; gap:8px; flex-wrap:wrap; margin:12px 0; }
.bar button { border:1px solid var(--line); background:#fff; border-radius:14px; padding:3px 12px; cursor:pointer; font:inherit; }
.bar button.on { background:var(--fg); color:#fff; border-color:var(--fg); }
table { border-collapse:collapse; width:100%; font-size:13px; }
th, td { border-top:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }
th { background:var(--panel); font-weight:600; }
td.sev { font-weight:700; white-space:nowrap; }
.s-Blocker { color:var(--blocker); } .s-Wrong { color:var(--wrong); } .s-Unclear { color:var(--unclear); }
.s-Polish { color:var(--polish); } .s-Environment { color:var(--env); }
details { background:var(--panel); border-radius:6px; padding:6px 12px; margin:8px 0; }
summary { cursor:pointer; font-weight:600; }
.hl { background:#fff8e6; border-left:4px solid var(--accent); padding:4px 16px 8px; border-radius:6px; }
.hl h2 { border-top:0; margin-top:8px; } .hl li { margin:4px 0; }
code { background:var(--panel); padding:0 3px; border-radius:3px; }
@media (max-width:900px) { nav { display:none; } main { margin-left:0; padding:16px; } }
"""

JS = """
const btns = document.querySelectorAll('.bar button');
btns.forEach(b => b.addEventListener('click', () => {
  b.classList.toggle('on');
  const on = [...btns].filter(x => x.classList.contains('on')).map(x => x.dataset.s);
  document.querySelectorAll('tr[data-s]').forEach(tr => tr.style.display = on.includes(tr.dataset.s) ? '' : 'none');
}));
"""


def main():
    import json as _j
    ov = _j.loads((WALK / "overrides.json").read_text(encoding="utf-8")) if (WALK / "overrides.json").exists() else {}
    files = sorted(WALK.glob("[0-9][0-9]_*_findings.md"))
    by_ex, notes, order, tot = {}, [], [], Counter()
    for f in files:
        rows, sections = parse(f.read_text(encoding="utf-8"))
        run = f.name.replace("_findings.md", "")
        for r in rows:
            o = ov.get(f"{run}#{r['n']}")
            if o:                                     # Claude's check after the run (overrides.json)
                r["happened"] += f"  [Checked: {o['check']}]"
                r["sev"] = f"{o['sev']} (student said {r['sev'].split()[0]})"
            ex = exercise(r["ex"], run)
            if ex not in by_ex:
                by_ex[ex] = []; order.append(ex)
            by_ex[ex].append(r)
            tot[sev_of(r)] += 1
        notes.append((run, sections, len(rows)))
    import json
    manual = list(json.loads(PAGES.read_text(encoding="utf-8"))) if PAGES.exists() else []
    order.sort(key=lambda e: manual.index(e) if e in manual else
               next((manual.index(m) + 0.5 for m in manual if e.startswith(m.split(":")[0])), 999))
    nav, body = [], []
    for i, ex in enumerate(order):
        rows = sorted(by_ex[ex], key=lambda r: (["Blocker", "Wrong", "Unclear", "Polish", "Environment"].index(sev_of(r)),
                                                 [int(x) for x in re.findall(r"\d+", r["step"])[:1]] or [999]))
        c = Counter(sev_of(r) for r in rows)
        nav.append(f'<a href="#e{i}">{html.escape(ex)}<span class="n">{len(rows)}</span></a>')
        body.append(f'<h2 id="e{i}">{html.escape(ex)}</h2><p class="lede">'
                    + " · ".join(f'<span class="s-{s}">{c[s]} {s}</span>' for s in SEV + ["Environment"] if c[s]) + "</p>"
                    '<table><tr><th>Step</th><th>Severity</th><th>Type</th><th>Manual says</th><th>What happened</th><th>Suggested fix</th></tr>'
                    + "".join(f'<tr data-s="{sev_of(r)}"><td>{html.escape(r["step"])}</td><td class="sev s-{sev_of(r)}">{sev_of(r)}</td>'
                              f'<td>{html.escape(r["type"])}</td><td>{html.escape(r["says"])}</td><td>{html.escape(r["happened"])}</td>'
                              f'<td>{html.escape(r["fix"])}</td></tr>' for r in rows) + "</table>")
    run_notes = "".join(
        f'<details><summary>Run {html.escape(run)} ({n} findings)</summary>'
        + "".join(f"<h3>{html.escape(t)}</h3>{md_html(s)}" for t, s in sections.items()) + "</details>"
        for run, sections, n in notes)
    total = sum(tot.values())
    hl = WALK / "highlights.md"
    highlights = ""
    if hl.exists():
        md = hl.read_text(encoding="utf-8")
        md = re.sub(r"^## .*\n", "", md, count=1)
        highlights = '<section class="hl"><h2 id="top">Read this first</h2>' + md_html(md) + "</section>"
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Student Walkthrough</title><style>{CSS}</style></head><body>
<nav><b>Student walkthrough</b><div class="lede">{len(order)} exercises · {total} findings</div><a href="#top">Read this first</a>{''.join(nav)}<a href="#runs">Run notes</a></nav>
<main><h1>Quick Sight Journey 1: student walkthrough of the draft</h1>
<p class="lede">An AI "student" (Claude Sonnet) followed the current draft as a brand-new Quick Sight user, page by page, using only
screenshots, mouse and keyboard (no page code, no scripts). Each exercise lists what it hit, worst first. <b>Blocker</b> = can't
continue; <b>Wrong</b> = text or picture doesn't match the screen or data; <b>Unclear</b> = works, but a student would hesitate;
<b>Polish</b> = wording, capitalization, small picture differences; <b>Environment</b> = our account or setup, not the manual.
Treat these as a second reader's notes: check before acting, especially "picture doesn't match" (often an old screenshot)
and anything that depends on what an earlier run left on screen. Built {datetime.now():%Y-%m-%d %H:%M}.</p>
<p>{' · '.join(f'<span class="s-{s}"><b>{tot[s]}</b> {s}</span>' for s in SEV + ['Environment'] if tot[s])}</p>
<div class="bar">{''.join(f'<button class="on" data-s="{s}">{s}</button>' for s in SEV + ['Environment'])}</div>
{highlights}{''.join(body)}<h2 id="runs">Run notes</h2>{run_notes}</main><script>{JS}</script></body></html>"""
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT}: {len(files)} runs, {len(order)} exercises, {total} findings {dict(tot)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
