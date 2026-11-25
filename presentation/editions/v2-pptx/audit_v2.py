# Audit the v2 deck: per-slide font sizes, fonts, palette, word counts, page fill.
import os, re, zipfile, tempfile, json
from xml.etree import ElementTree as ET
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PPTX = os.path.join(HERE, "CSIT6000V_VerifiableTutor_v2.pptx")
PDF = os.path.join(HERE, "CSIT6000V_VerifiableTutor_v2.pdf")
PAGES = os.path.join(HERE, "pages")

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
A = "{%s}" % NS["a"]

ALLOWED = {"FAFAFA", "FFFFFF", "09090B", "1447E6", "E5E5E5", "0A0A0A", "171717", "C10007"}
FOOTER_WORDS = {"verifiable tutor / csit6000v"}

VISUALS = {
    1: "course page thumbnail + evidence chips",
    2: "course page thumbnail + 3 icons",
    3: "architecture icon cluster + flow",
    4: "source pane screenshot + 4 icons",
    5: "5 layer icons + stack diagram",
    6: "4 icons + agent/tools loop diagram",
    7: "large work-chain screenshot + ratio stats",
    8: "course thumbnails + pipeline icons + 4 stat figures",
    9: "retrieval flow icons + 3 metric figures",
    10: "large answer screenshot + source pane screenshot",
    11: "page-chat screenshot + 3 step icons",
    12: "before/after course thumbnails + chat screenshot",
    13: "pass/fail cards + course page thumbnail + 4 icons",
    14: "practice card + policy ladder + 2 icons",
    15: "practice screenshot + policy refusal screenshot",
    16: "comparison table + 3 scorecards + 3 icons",
    17: "bar chart + tutorial thumbnail + 4 limit icons",
    18: "3 icons + QR code",
    19: "9-step icon sequence + legend",
    20: "method list + TACC stat figures + 2 icons",
}

tmp = tempfile.mkdtemp()
with zipfile.ZipFile(PPTX) as z:
    z.extractall(tmp)
    names = z.namelist()

slides = sorted(
    [n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)],
    key=lambda n: int(re.search(r"slide(\d+)", n).group(1)),
)

# ---- pptx-wide font audit
font_parts = {}
for n in names:
    if n.endswith(".xml"):
        x = open(os.path.join(tmp, n), encoding="utf-8", errors="ignore").read()
        faces = set(re.findall(r'typeface="([^"]*)"', x))
        faces = {f for f in faces if f and not f.startswith("+")}
        if faces:
            font_parts[n] = sorted(faces)
all_faces = sorted({f for fs in font_parts.values() for f in fs})
print("PPTX fonts:", all_faces)
print("PPTX font parts:", {k: v for k, v in font_parts.items() if k.startswith("ppt/slides/")} or "slides use theme fonts")

# ---- per slide
report = []
for i, n in enumerate(slides, 1):
    x = open(os.path.join(tmp, n), encoding="utf-8").read()
    root = ET.fromstring(x)
    sizes = []
    fonts = []
    colors = set()
    words = []
    words_all = []
    for r in root.iter(A + "r"):
        rpr = r.find(A + "rPr")
        t = r.find(A + "t")
        sz = None
        face = None
        if rpr is not None:
            sz = rpr.get("sz")
            latin = rpr.find(A + "latin")
            if latin is not None:
                face = latin.get("typeface")
            if sz:
                sizes.append(int(sz))
        if face:
            fonts.append(face)
        if t is not None and t.text:
            text = t.text.strip()
            if text:
                words_all.append(text)
                if sz == "1600" and text != "Verifiable Tutor  /  CSIT6000V" and not re.match(r"^(?:\d\d|A\d) / 20$", text):
                    words.extend(re.findall(r"[A-Za-z][A-Za-z0-9@_./-]*", text))
    for e in root.iter(A + "endParaRPr"):
        if e.get("sz"):
            sizes.append(int(e.get("sz")))
    for c in root.iter(A + "srgbClr"):
        colors.add(c.get("val").upper())
    distinct = sorted(set(sizes))
    allowed_sizes = {1600, 6400} if i == 1 else {1600, 4000}
    size_ok = set(distinct).issubset(allowed_sizes) and 1600 in distinct
    report.append({
        "page": i,
        "sizes": distinct,
        "sizes_ok": size_ok,
        "fonts": sorted(set(fonts)),
        "colors": sorted(colors),
        "prose_words": len(words),
        "all_word_tokens": len(re.findall(r"[A-Za-z0-9][A-Za-z0-9@_./-]*", " ".join(words_all))),
        "visual": VISUALS.get(i, "?"),
    })

bad_sizes = [r for r in report if not r["sizes_ok"]]
bad_fonts = [r for r in report if any(f not in {"Georgia", "Arial", "Courier New"} for f in r["fonts"])]
bad_colors = [r for r in report if any(c not in ALLOWED for c in r["colors"])]
over_words = [r for r in report if r["prose_words"] > 45]

print("\nPer slide:")
print(f"{'pg':>3} {'sizes(1/100pt)':<18} {'fonts':<26} {'prose':>5} {'visual'}")
for r in report:
    print(f"{r['page']:>3} {str(r['sizes']):<18} {','.join(r['fonts']):<26} {r['prose_words']:>5} {r['visual']}")
print("\nsize violations:", [(r["page"], r["sizes"]) for r in bad_sizes])
print("font violations:", [(r["page"], r["fonts"]) for r in bad_fonts])
print("palette violations:", [(r["page"], r["colors"]) for r in bad_colors])
print("prose > 45:", [(r["page"], r["prose_words"]) for r in over_words])

# ---- bottom fill from rendered pages
print("\nBottom fill (last significant content row above footer):")
pages = sorted([p for p in os.listdir(PAGES) if p.startswith("page-") and p.endswith(".png")],
               key=lambda p: int(p.split("-")[1].split(".")[0]))
for idx, p in enumerate(pages, 1):
    im = Image.open(os.path.join(PAGES, p)).convert("RGB")
    w, h = im.size
    bg = im.getpixel((3, 3))
    last = 0
    footer_limit = int(h * 6.88 / 7.5)
    for yy in range(0, footer_limit):
        row = [im.getpixel((xx, yy)) for xx in range(0, w, 8)]
        diff = sum(1 for px in row if max(abs(px[0]-bg[0]), abs(px[1]-bg[1]), abs(px[2]-bg[2])) > 14)
        if diff > len(row) * 0.02:
            last = yy
    blank = (h - last) / h * 100
    flag = "  <-- >15%" if blank > 15 else ""
    print(f"  page {idx:>2}: last content y={last}/{h}  bottom blank {blank:5.1f}%{flag}")
