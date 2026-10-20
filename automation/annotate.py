"""Snagit-style annotation for manual screenshots, matching the existing Quick Sight
Journey 1 images: #F4AC08 rounded boxes and filled arrows with a soft shadow, orange
numbered circles, a thin gray border on the top/left and a torn edge on the right/bottom.

All coordinates are CSS px (as recorded by qs.capture); the PNGs are at devicePixelRatio,
so drawing is done at that scale.

    s = Shot("Table_Calculations", "07_percent_of_total")
    s.crop(240, 500, 760, 720)
    s.box(s.b("pill2"), pad=2)
    s.arrow((520, 470), s.b("menu_btn"))
    s.callout(2, (238, 526))
    s.save()

Shortening a picture (David's rules: crop or cut rather than shrink below 90%):
    s.cut_x(620, 900)          # remove a vertical strip of dead space and join the sides
    s.tear_y(400, 700)         # remove a horizontal band; torn edges with a small gap
Marks always use the capture's own coordinates; they follow cuts and tears (a box spanning a
cut gets shorter). compose() builds a composite capture from regions of several captures.
"""
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ORANGE = (244, 172, 8, 255)
SHADOW = (0, 0, 0, 90)

# Torn-edge look (frame and tear_y). line = the jagged outline color (None = no line), line_w in CSS px;
# shadow = soft drop shadow behind the torn shape (alpha 0-255; dx, dy, blur in CSS px), as in David's Snagit
# images; fine = Snagit-like finer, irregular teeth instead of the even 3 px teeth.
# Samples (not published): review/edge_samples.html
EDGE_STYLES = {
    "black": dict(line=(0, 0, 0, 255), line_w=1.5, shadow=0, dx=0, dy=0, blur=0, fine=False),    # sessions 1-8
    "gray_light": dict(line=(160, 160, 160, 255), line_w=1, shadow=70, dx=1.5, dy=1.5, blur=2, fine=False),
    "gray_shadow": dict(line=(170, 170, 170, 255), line_w=1, shadow=130, dx=2, dy=2, blur=2.5, fine=False),
    "snagit": dict(line=None, line_w=0, shadow=140, dx=1.5, dy=1.5, blur=2, fine=True),
}
EDGE = EDGE_STYLES["gray_light"]          # gray_light chosen 2026-10-13 (session 9)


def _teeth(rnd, length, k, amp):
    """Depths (0..amp image px) along an edge of `length` image px: [(position, depth)].
    Even teeth every 3 CSS px (the original look), or EDGE["fine"]: Snagit-like irregular teeth."""
    if not EDGE["fine"]:
        return [(p, rnd.randint(0, amp)) for p in range(0, length, int(3 * k))]
    out, p, d = [], 0.0, amp / 2
    while p < length:
        d = min(amp, max(0, d + rnd.uniform(-0.45, 0.45) * amp))
        out.append((int(p), int(amp * rnd.uniform(0.6, 1.0)) if rnd.random() < 0.12 else int(d)))
        p += rnd.uniform(0.8, 2.2) * k
    return out


def _shadow(canvas, mask, at, k):
    """Composite a soft drop shadow of `mask` (L, 255 = picture) placed at `at` onto RGBA `canvas`."""
    if not EDGE["shadow"]:
        return
    m = Image.new("L", canvas.size, 0)
    m.paste(mask, (at[0] + round(EDGE["dx"] * k), at[1] + round(EDGE["dy"] * k)))
    m = m.filter(ImageFilter.GaussianBlur(EDGE["blur"] * k)).point(lambda v: v * EDGE["shadow"] // 255)
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sh.putalpha(m)
    canvas.alpha_composite(sh)


def _font(px):
    for name in ("segoeuib.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


class Shot:
    def __init__(self, exercise, name):
        self.src = HERE / "screenshots" / exercise / f"{name}.png"
        self.out = HERE / "screenshots_annotated" / exercise / f"{name}.png"
        meta = json.loads(self.src.with_suffix(".json").read_text())
        self.boxes = meta["boxes"]
        self.k = meta["dpr"]
        self.img = Image.open(self.src).convert("RGBA")
        self.ox = self.oy = 0          # crop origin, CSS px
        self.marks = []                # deferred drawing ops (drawn after crop)
        self.cuts = []                 # (x0, x1) vertical strips removed, CSS px
        self.tears = []                # (y0, y1, gap) horizontal bands removed, CSS px
        self.gaps = []                 # (y0, y1) image px of tear gaps (the frame skips them)

    # ---- geometry helpers (CSS px) -------------------------------------------------
    def b(self, label, grow=(0, 0, 0, 0)):
        """Recorded box (x0, y0, x1, y1), optionally grown by (left, top, right, bottom)."""
        x, y, w, h = self.boxes[label]
        l, t, r, bt = grow
        return (x - l, y - t, x + w + r, y + h + bt)

    @staticmethod
    def mid(rect):
        x0, y0, x1, y1 = rect
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    def crop(self, x0, y0, x1, y1):
        k = self.k
        self.img = self.img.crop((int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k)))
        self.ox, self.oy = x0, y0
        return self

    def _px(self, x, y):
        X, Y = x, y
        for a, b in self.cuts:
            X -= (b - a) if x >= b else max(0, x - a)
        for a, b, gap in self.tears:
            Y -= (b - a - gap) if y >= b else max(0, y - a)
        return ((X - self.ox) * self.k, (Y - self.oy) * self.k)

    def cut_x(self, x0, x1):
        """Remove the vertical strip x0..x1 (CSS px) and join the two sides (Snagit cut-out), for dead
        space such as the empty stretch of a wide dropdown or a pane behind full-width boxes."""
        ia = int(round(self._px(x0, 0)[0])); ib = ia + int(round((x1 - x0) * self.k))
        W, H = self.img.size
        out = Image.new("RGBA", (W - (ib - ia), H))
        out.paste(self.img.crop((0, 0, ia, H)), (0, 0))
        out.paste(self.img.crop((ib, 0, W, H)), (ia, 0))
        self.img = out
        self.cuts.append((x0, x1))
        return self

    def tear_y(self, y0, y1, gap=8):
        """Remove the horizontal band y0..y1 (CSS px) and show the cut as two torn edges with a small
        white gap, the way David shortens a tall picture."""
        k = self.k
        ia = int(round(self._px(0, y0)[1])); ib = ia + int(round((y1 - y0) * k)); g = int(gap * k)
        W, H = self.img.size
        top, bottom = self.img.crop((0, 0, W, ia)), self.img.crop((0, ib, W, H))
        out = Image.new("RGBA", (W, ia + g + bottom.height), (255, 255, 255, 255))
        rnd = random.Random(W * 13 + ia)
        amp, step = int(5 * k), int(3 * k)
        edge_t = [(x, ia - t) for x, t in _teeth(rnd, W + step, k, amp)]
        edge_b = [(x, ia + g + t) for x, t in _teeth(rnd, W + step, k, amp)]
        mt = Image.new("L", (W, ia), 0)
        ImageDraw.Draw(mt).polygon([(0, 0), (W, 0)] + [(min(x, W), y) for x, y in reversed(edge_t)], fill=255)
        _shadow(out, mt, (0, 0), k)                    # the upper piece casts its shadow into the gap
        out.paste(top, (0, 0), mt)
        mb = Image.new("L", (W, bottom.height), 0)
        ImageDraw.Draw(mb).polygon([(min(x, W), y - ia - g) for x, y in edge_b] + [(W, bottom.height), (0, bottom.height)], fill=255)
        out.paste(bottom, (0, ia + g), mb)
        if EDGE["line"]:
            d = ImageDraw.Draw(out)
            for edge in (edge_t, edge_b):
                d.line([(min(x, W), y) for x, y in edge], fill=EDGE["line"], width=max(1, int(EDGE["line_w"] * k)),
                       joint="curve")
        self.img = out
        self.gaps.append((ia - amp, ia + g + amp))
        self.tears.append((y0, y1, gap))
        return self

    def cut_y(self, y0, y1):
        """Remove the horizontal band y0..y1 (CSS px) and join seamlessly (no torn edge), e.g. to drop one
        row from a list that a student wouldn't have."""
        ia = int(round(self._px(0, y0)[1])); ib = ia + int(round((y1 - y0) * self.k))
        W, H = self.img.size
        out = Image.new("RGBA", (W, H - (ib - ia)))
        out.paste(self.img.crop((0, 0, W, ia)), (0, 0))
        out.paste(self.img.crop((0, ib, W, H)), (0, ia))
        self.img = out
        self.tears.append((y0, y1, 0))
        return self

    def erase(self, rect, fill=None):
        """Paint over a region (e.g. a stray tooltip) with `fill`, default the color just left of it."""
        x0, y0 = self._px(*rect[:2]); x1, y1 = self._px(*rect[2:])
        col = fill or self.img.getpixel((max(0, int(x0) - 2), int(y0)))
        ImageDraw.Draw(self.img).rectangle((x0, y0, x1, y1), fill=col)
        return self

    # ---- marks ---------------------------------------------------------------------
    def box(self, rect, pad=3):
        x0, y0, x1, y1 = rect
        self.marks.append(("box", (x0 - pad, y0 - pad, x1 + pad, y1 + pad)))
        return self

    def arrow(self, start, end, gap=4):
        """Filled arrow from start to end (points, or rects -> nearest edge midpoint)."""
        if len(end) == 4:
            end = self._edge_point(end, start, gap)
        if len(start) == 4:
            start = self.mid(start)
        self.marks.append(("arrow", start, end))
        return self

    def callout(self, n, at):
        self.marks.append(("callout", n, at))
        return self

    @staticmethod
    def _edge_point(rect, toward, gap):
        x0, y0, x1, y1 = rect
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = toward[0] - cx, toward[1] - cy
        hw, hh = (x1 - x0) / 2 + gap, (y1 - y0) / 2 + gap
        s = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
        return (cx + dx * s, cy + dy * s)

    # ---- rendering -----------------------------------------------------------------
    def _draw_marks(self):
        k = self.k
        W, H = self.img.size
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd, td = ImageDraw.Draw(shadow), ImageDraw.Draw(top)
        off = 2 * k
        for m in self.marks:
            if m[0] == "box":
                x0, y0 = self._px(*m[1][:2]); x1, y1 = self._px(*m[1][2:])
                for d, dx, col in ((sd, off, SHADOW), (td, 0, ORANGE)):
                    d.rounded_rectangle((x0 + dx, y0 + dx, x1 + dx, y1 + dx), radius=6 * k,
                                        outline=col, width=int(3 * k))
            elif m[0] == "arrow":
                pts = self._arrow_poly(self._px(*m[1]), self._px(*m[2]))
                sd.polygon([(x + off, y + off) for x, y in pts], fill=SHADOW)
                td.polygon(pts, fill=ORANGE)
            elif m[0] == "callout":
                cx, cy = self._px(*m[2]); r = 11 * k
                sd.ellipse((cx - r + off, cy - r + off, cx + r + off, cy + r + off), fill=SHADOW)
                td.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ORANGE)
                f = _font(int(15 * k))
                td.text((cx, cy + k), str(m[1]), font=f, fill="white", anchor="mm")
        shadow = shadow.filter(ImageFilter.GaussianBlur(2 * k))
        self.img = Image.alpha_composite(Image.alpha_composite(self.img, shadow), top)

    def _arrow_poly(self, a, b):
        import math
        k = self.k
        ax, ay = a; bx, by = b
        L = math.hypot(bx - ax, by - ay) or 1
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = -uy, ux
        head_len, head_w, tail_w, neck_w = 22 * k, 13 * k, 2.5 * k, 5 * k
        hx, hy = bx - ux * head_len, by - uy * head_len
        return [(ax + nx * tail_w, ay + ny * tail_w), (hx + nx * neck_w, hy + ny * neck_w),
                (hx + nx * head_w, hy + ny * head_w), (bx, by),
                (hx - nx * head_w, hy - ny * head_w), (hx - nx * neck_w, hy - ny * neck_w),
                (ax - nx * tail_w, ay - ny * tail_w)]

    def _frame(self, pad=10):
        """Gray 1px border top/left, torn edge right/bottom, white margin all round."""
        k = self.k
        W, H = self.img.size
        rnd = random.Random(W * 7 + H)
        tear = int(5 * k)
        out = Image.new("RGBA", (W + 2 * int(pad * k), H + 2 * int(pad * k)), "white")
        px = py = int(pad * k)
        # jagged right and bottom outline
        if EDGE["fine"]:
            right = [(W - t, y) for y, t in _teeth(rnd, H, k, tear)] + [(W - tear // 2, H)]
            bottom = [(W - x, H - t) for x, t in _teeth(rnd, W + 1, k, tear)] + [(0, H - tear // 2)]
        else:
            right = [(W - rnd.randint(0, tear), y) for y in range(0, H, int(3 * k))] + [(W - tear // 2, H)]
            bottom = [(x, H - rnd.randint(0, tear)) for x in range(W, -1, -int(3 * k))] + [(0, H - tear // 2)]
        poly = [(0, 0)] + right + bottom
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        _shadow(out, mask, (px, py), k)
        out.paste(self.img, (px, py), mask)
        d = ImageDraw.Draw(out)
        gray = (160, 160, 160, 255)
        d.line([(px, py), (px + W - tear, py)], fill=gray, width=max(1, int(k)))
        y = 0
        for g0, g1 in sorted(self.gaps) + [(H - tear, H)]:
            if g0 > y:
                d.line([(px, py + y), (px, py + g0)], fill=gray, width=max(1, int(k)))
            y = max(y, g1)
        if EDGE["line"]:
            d.line([(x + px, y + py) for x, y in right + bottom], fill=EDGE["line"],
                   width=max(1, int(EDGE["line_w"] * k)), joint="curve")
        return out

    def save(self):
        self._draw_marks()
        out = self._frame().convert("RGB")
        self.out.parent.mkdir(parents=True, exist_ok=True)
        out.save(self.out, dpi=(96 * self.k, 96 * self.k))
        print(self.out, out.size)
        return self.out


def compose(exercise, name, parts, size, fill=(255, 255, 255)):
    """Write screenshots/<exercise>/<name>.png (+ .json) built from regions of other raw captures, for a
    composite picture (David: two screenshots joined into one image). Annotate it with Shot as usual.
        parts = [(source capture name, (x0, y0, x1, y1) region, (dx, dy) where it goes), ...]  CSS px
        size  = (width, height) of the composite, CSS px
    Later parts paste over earlier ones. Recorded boxes inside each region come along, renamed
    "<n>:<label>" (n = part index) and moved to their new place."""
    base = HERE / "screenshots" / exercise
    metas = [json.loads((base / f"{src}.json").read_text()) for src, _, _ in parts]
    k = metas[0]["dpr"]
    out = Image.new("RGB", (int(size[0] * k), int(size[1] * k)), fill)
    boxes = {}
    for n, ((src, (x0, y0, x1, y1), (dx, dy)), meta) in enumerate(zip(parts, metas)):
        im = Image.open(base / f"{src}.png").convert("RGB")
        out.paste(im.crop((int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k))), (int(dx * k), int(dy * k)))
        for label, (bx, by, bw, bh) in meta["boxes"].items():
            if bx >= x0 and by >= y0 and bx + bw <= x1 and by + bh <= y1:
                boxes[f"{n}:{label}"] = (bx - x0 + dx, by - y0 + dy, bw, bh)
    out.save(base / f"{name}.png")
    (base / f"{name}.json").write_text(json.dumps({"dpr": k, "viewport": list(size), "boxes": boxes,
                                                   "composite_of": [p[0] for p in parts]}, indent=1))
    print(base / f"{name}.png", out.size)
    return base / f"{name}.png"
