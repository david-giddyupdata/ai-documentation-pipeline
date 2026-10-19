"""python _work/scan_numbers.py <docx> <pdf> [filter]: rendered step numbers per instruction-table group.

Groups come from the docx (numbered-step tables keyed by their heading chain); each group's
first step text locates it in the PDF, and the numbers between it and the next group's
first step are the rendered ones. Flags any group that doesn't read 1, 2, 3...
"""
import re
import sys
from pathlib import Path

import docx
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build_lib import step_groups, text_of

docx_path, pdf_path = sys.argv[1:3]
only = sys.argv[3] if len(sys.argv) > 3 else None
d = docx.Document(docx_path)
groups = step_groups(d)

pdf = fitz.open(pdf_path)
full = "\n".join(p.get_text() for p in pdf)
flat = re.sub(r"\s+", " ", full)

pos = 0
starts = []
for key, paras in groups:
    marker = re.sub(r"\s+", " ", text_of(paras[0]))[:40]
    i = flat.find(marker, pos)
    starts.append(i)
    if i >= 0:
        pos = i + 1
starts.append(len(flat))

for k, (key, paras) in enumerate(groups):
    if only and only not in key:
        continue
    s = starts[k]
    if s < 0:
        print(f"?? {key}: first step not found in PDF")
        continue
    e = next((x for x in starts[k + 1:] if x >= 0), len(flat))
    seg = flat[max(0, s - 6):e]
    nums = [int(n) for n in re.findall(r"(?:^| )(\d{1,3})\. (?=[A-Z‘“'\"{])", seg)]
    ok = nums == list(range(1, len(nums) + 1))
    print(f"{'ok' if ok else 'XX'} {key}: {nums}")
