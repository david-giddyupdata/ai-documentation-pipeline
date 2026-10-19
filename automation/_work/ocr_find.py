"""ocr_find.py <docx> <regex>: OCR every image in the docx (2x upscale) and list matches with the heading they sit under."""
import os, sys, re, io, zipfile, docx, pytesseract
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = os.environ.get("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
path, pat = sys.argv[1], re.compile(sys.argv[2], re.I)
d = docx.Document(path)
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
rels = d.part.rels
heads = {}; seen = {}
only = set(sys.argv[3].split(',')) if len(sys.argv) > 3 else None
for p in d.element.body.iter(W + 'p'):
    st = p.find(W + 'pPr/' + W + 'pStyle')
    if st is not None and st.get(W + 'val', '').startswith('Heading'):
        t = ''.join(x.text or '' for x in p.iter(W + 't')).strip()
        if t:
            lv = int(re.sub(r'\D', '', st.get(W + 'val')) or 9)
            heads = {k: v for k, v in heads.items() if k < lv}; heads[lv] = t
    for b in p.iter(A + 'blip'):
        rid = b.get(R + 'embed')
        if rid not in rels: continue
        name = rels[rid].target_ref
        if only and name not in only: continue
        if name not in seen:
            im = Image.open(io.BytesIO(rels[rid].target_part.blob)).convert('RGB')
            im = im.resize((im.width * 2, im.height * 2))
            seen[name] = pytesseract.image_to_string(im)
        hits = sorted(set(m.group(0) for m in pat.finditer(seen[name])))
        if hits: print(' > '.join(heads[k] for k in sorted(heads)) + f" | {name} | {hits}")
