"""Render one page (or part of one) of _work/render.pdf to PNG, for looking at what students see.

    python _work/pdf_page.py <page> <out_dir> [dpi] [x0 y0 x1 y1]

page = the printed page number (same as the PDF page). The optional box is in fractions of the page
(0-1, left/top origin), e.g. `0.5 0 1 0.5` = top-right quarter; use it with a high dpi (200-300)
to read small text inside a screenshot. Prints the PNG path and the page's text.
"""
import sys
from pathlib import Path

import fitz

page, out_dir = int(sys.argv[1]), Path(sys.argv[2])
dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 110
box = [float(v) for v in sys.argv[4:8]] if len(sys.argv) >= 8 else None
pdf = fitz.open(Path(__file__).resolve().parent / "render.pdf")
pg = pdf[page - 1]
clip = None
suffix = ""
if box:
    r = pg.rect
    clip = fitz.Rect(r.x0 + box[0] * r.width, r.y0 + box[1] * r.height, r.x0 + box[2] * r.width, r.y0 + box[3] * r.height)
    suffix = "_" + "_".join(f"{v:g}" for v in box)
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"p{page:03d}_{dpi}{suffix}.png"
pg.get_pixmap(dpi=dpi, clip=clip).save(out)
sys.stdout.reconfigure(encoding="utf-8")
print(out)
if not box:
    print(pg.get_text())
