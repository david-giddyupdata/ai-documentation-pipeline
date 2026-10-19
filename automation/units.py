"""Split a manual .docx into exercises ("units") of ordered blocks. Used by build.py and review_pack.py.

A unit starts at every Heading 1 and Heading 2, and at Heading 3 under the Addendum (each chart is
its own exercise there). Blocks are body paragraphs and table rows, in document order:

    Block.kind    'p' (paragraph) or 'row' (one table row; nested tables flattened into it)
    Block.segs    [(text, bold)] runs, paragraphs joined by newlines; '• ' marks a bullet, '› ' a step
    Block.images  [sha1] of the pictures in the block; units.load() also returns {sha1: (name, bytes)}
    Block.widths  [inches] each picture's width in the document (None if unknown)
"""
import hashlib
import re
from dataclasses import dataclass, field

import docx
from docx.oxml.ns import qn

ADDENDUM = "Addendum-Visualization Types"


@dataclass
class Block:
    kind: str
    style: str
    segs: list = field(default_factory=list)
    images: list = field(default_factory=list)
    widths: list = field(default_factory=list)

    @property
    def text(self):
        return "".join(t for t, _ in self.segs)

    @property
    def key(self):
        """Alignment key: the plain text, case and spacing folded; picture-only blocks share one key."""
        t = re.sub(r"\s+", " ", self.text).strip().lower()
        return t or "<image>"

    def same(self, other):
        return self.segs == other.segs and self.images == other.images


@dataclass
class Unit:
    name: str                    # "H1 > H2" or "Addendum-Visualization Types > H2 > H3"
    leaf: str
    blocks: list = field(default_factory=list)

    @property
    def key(self):
        return re.sub(r"[^a-z0-9>]", "", self.name.lower())

    def fingerprint(self):
        h = hashlib.sha1()
        for b in self.blocks:
            h.update(repr((b.kind, b.style, b.segs, b.images)).encode("utf-8"))
        return h.hexdigest()

    def first_text(self, n=40):
        """First body text of the unit (not a heading), to find the unit in a rendered PDF."""
        for b in self.blocks:
            t = re.sub(r"\s+", " ", b.text.replace("• ", "").replace("› ", "")).strip()
            if not b.style.startswith("Heading") and len(t) >= 25:
                return t[:n]
        return self.leaf


def _style(p):
    s = p.find(qn("w:pPr") + "/" + qn("w:pStyle"))
    return s.get(qn("w:val")) if s is not None else "Normal"


def _runs(p):
    """[(text, bold)] for a paragraph, adjacent runs with the same weight merged."""
    out = []
    for r in p.iter(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        b = rpr.find(qn("w:b")) if rpr is not None else None
        bold = b is not None and b.get(qn("w:val")) not in ("0", "false")
        t = ""
        for c in r:
            if c.tag == qn("w:t"):
                t += c.text or ""
            elif c.tag == qn("w:tab"):
                t += " "
            elif c.tag in (qn("w:br"), qn("w:cr")):
                t += "\n"
        if not t:
            continue
        if out and out[-1][1] == bold:
            out[-1] = (out[-1][0] + t, bold)
        else:
            out.append((t, bold))
    return out


class _Reader:
    def __init__(self, d):
        self.rels = d.part.rels
        self.blobs = {}

    def images(self, el):
        """[(sha1, width in inches or None)] for the pictures in el, in document order."""
        found, width = [], None
        for e in el.iter():
            rid = None
            if e.tag == qn("wp:extent"):
                width = int(e.get("cx")) / 914400
            elif e.tag == qn("a:blip"):
                rid = e.get(qn("r:embed"))
            elif e.tag.endswith("}imagedata"):
                rid, width = e.get(qn("r:id")), None
            if rid and rid in self.rels and not self.rels[rid].is_external:
                part = self.rels[rid].target_part
                h = hashlib.sha1(part.blob).hexdigest()
                self.blobs.setdefault(h, (part.partname.split("/")[-1], part.blob))
                found.append((h, width))
        return found

    def para_segs(self, p):
        segs = _runs(p)
        if not segs:
            return segs
        st = _style(p)
        if "Bullet" in st:
            segs.insert(0, ("• ", False))
        elif p.find(qn("w:pPr") + "/" + qn("w:numPr")) is not None:
            segs.insert(0, ("› ", False))
        return segs

    def row(self, tr):
        segs, imgs = [], []

        def walk(container):
            for c in container:
                if c.tag == qn("w:p"):
                    s = self.para_segs(c)
                    if s:
                        if segs:
                            segs.append(("\n", False))
                        segs.extend(s)
                    imgs.extend(self.images(c))
                elif c.tag == qn("w:tbl"):
                    for tr2 in c.findall(qn("w:tr")):
                        for tc2 in tr2.findall(qn("w:tc")):
                            walk(tc2)
                elif c.tag == qn("w:sdt"):
                    content = c.find(qn("w:sdtContent"))
                    if content is not None:
                        walk(content)

        for tc in tr.findall(qn("w:tc")):
            walk(tc)
        return Block("row", "table", segs, [h for h, _ in imgs], [w for _, w in imgs])


def load(path):
    """Return (units, blobs) for a .docx."""
    d = docx.Document(path)
    rd = _Reader(d)
    units, chain = [], {}

    def start(level, text):
        for k in [k for k in chain if k >= level]:
            del chain[k]
        chain[level] = text
        if level <= 2 or (level == 3 and chain.get(1) == ADDENDUM):
            units.append(Unit(" > ".join(chain[k] for k in sorted(chain)), text))

    for el in d.element.body.iterchildren():
        if el.tag == qn("w:p"):
            st = _style(el)
            text = "".join(t for t, _ in _runs(el)).strip()
            m = re.fullmatch(r"Heading([1-9])", st)
            if m and text:
                start(int(m.group(1)), text)
            if not units:
                units.append(Unit("(front)", "(front)"))
            segs, imgs = rd.para_segs(el), rd.images(el)
            if segs or imgs:
                units[-1].blocks.append(Block("p", st, segs, [h for h, _ in imgs], [w for _, w in imgs]))
        elif el.tag == qn("w:tbl"):
            if not units:
                units.append(Unit("(front)", "(front)"))
            for tr in el.findall(qn("w:tr")):
                b = rd.row(tr)
                if b.segs or b.images:
                    units[-1].blocks.append(b)
    return units, rd.blobs


def locate_pages(units, pdf):
    """{unit name: (first page, last page)} (1-based) in a rendered fitz PDF, found in order by
    each unit's first body text. Units not found are left out."""
    starts, offs, parts = [], [], []
    pos = 0
    for pg in pdf:
        offs.append(pos)
        t = re.sub(r"\s+", " ", pg.get_text()) + " "
        parts.append(t)
        pos += len(t)
    flat = "".join(parts)
    cur = 0
    for u in units:
        i = flat.find(u.first_text(), cur)
        starts.append(i)
        if i >= 0:
            cur = i + 1

    def page_of(i):
        lo = 0
        for k, o in enumerate(offs):
            if o <= i:
                lo = k
        return lo + 1

    out = {}
    for k, u in enumerate(units):
        if starts[k] < 0:
            continue
        nxt = next((s for s in starts[k + 1:] if s >= 0), len(flat) - 1)
        out[u.name] = (page_of(starts[k]), page_of(max(starts[k], nxt - 1)))
    return out
