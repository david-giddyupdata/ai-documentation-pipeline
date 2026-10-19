"""Save a student subagent's final reply (findings) from its transcript, and pull out its "Where I stopped" note.

    python _work/student_extract.py <transcript .output/.jsonl> <out .md>   # prints the "Where I stopped" section
"""
import json
import re
import sys
from pathlib import Path


def final_text(path):
    last = None
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"] \
            if isinstance(content, list) else [content] if isinstance(content, str) else []
        t = "\n".join(x for x in texts if x and x.strip())
        if t.strip():
            last = t
    return last


def manual_passwords(run):
    """Course-database passwords printed in the run's manual pages (the line after "Password"); they must not
    land in files inside a cloud-synced folder."""
    out = set()
    for f in Path(run, "manual").glob("*.txt"):
        lines = [l.strip() for l in f.read_text(encoding="utf-8").splitlines()]
        out |= {lines[i + 1] for i, l in enumerate(lines[:-1]) if l == "Password" and len(lines[i + 1]) >= 6}
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    text = final_text(sys.argv[1])
    if not text:
        sys.exit("no assistant text found")
    if "--run" in sys.argv:                      # python ... <transcript> <out> --run <run dir>
        for pw in manual_passwords(sys.argv[sys.argv.index("--run") + 1]):
            text = text.replace(pw, "(password from the manual)")
    Path(sys.argv[2]).write_text(text, encoding="utf-8")
    m = re.search(r"#+\s*Where I stopped\s*\n(.*?)(\n#+\s|\Z)", text, re.S | re.I)
    print(m.group(1).strip() if m else "(no 'Where I stopped' section)")
