#!/usr/bin/env python3
"""Static integrity checks: asset references, external URLs, CJK, notes, theme fonts."""
from __future__ import annotations

import json
import re
from pathlib import Path

ED = Path(__file__).resolve().parents[2]
QA = ED / "qa"
CJK = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af\uff00-\uffef]")
report = {}

# --- stage assets ---
stage = ED / "stage-html"
html = (stage / "index.html").read_text()
refs = set(re.findall(r'(?:src|href)="([^"]+)"', html))
css_refs = set()
for css in re.findall(r'url\(([^)]+)\)', html):
    css_refs.add(css.strip("'\""))
missing_stage = []
for ref in sorted(refs | css_refs):
    if ref.startswith(("http:", "https:", "data:", "#", "mailto:")):
        continue
    target = (stage / ref.split("?")[0].split("#")[0]).resolve()
    if not target.exists():
        missing_stage.append(ref)
stage_http = sorted({u for u in (refs | css_refs) if u.startswith(("http:", "https:"))})
report["stage"] = {
    "refCount": len(refs), "cssRefCount": len(css_refs),
    "missingRefs": missing_stage, "externalRefs": stage_http,
    "httpInCss": len(re.findall(r'@import\s+["\']?https?:', html)),
}

# --- custom assets ---
custom = ED / "custom-html"
html_c = (custom / "index.html").read_text()
css_c = (custom / "assets" / "vt.css").read_text()
refs_c = set(re.findall(r'(?:src|href)="([^"]+)"', html_c))
css_refs_c = set(re.findall(r'url\(([^)]+)\)', html_c + "\n" + css_c))
missing_c = []
for ref in sorted(refs_c | css_refs_c):
    if ref.startswith(("http:", "https:", "data:", "#", "mailto:")):
        continue
    target = (custom / ref.split("?")[0].split("#")[0]).resolve()
    if not target.exists():
        missing_c.append(ref)
custom_http = sorted({u for u in (refs_c | css_refs_c) if u.startswith(("http:", "https:"))})
report["custom"] = {
    "refCount": len(refs_c), "cssRefCount": len(css_refs_c),
    "missingRefs": missing_c, "externalRefs": custom_http,
    "httpInCss": len(re.findall(r'@import\s+["\']?https?:', html_c + css_c)),
}

# --- CJK classification in built HTML ---
def classify_cjk(path: Path) -> dict:
    text = path.read_text()
    # strip comments (html + js block + line comments) and svg namespace urls
    stripped = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.S)
    stripped = re.sub(r"(?m)^\s*//.*$", "", stripped)
    visible = re.sub(r"<script.*?</script>", "", stripped, flags=re.S)
    visible = re.sub(r"<style.*?</style>", "", visible, flags=re.S)
    visible = re.sub(r"<[^>]+>", " ", visible)
    return {
        "cjkInRawFile": len(CJK.findall(text)),
        "cjkInCommentsOrScripts": len(CJK.findall(text)) - len(CJK.findall(stripped)),
        "cjkInMarkupText": len(CJK.findall(visible)),
    }

report["stage"]["cjk"] = classify_cjk(stage / "index.html")
report["custom"]["cjk"] = classify_cjk(custom / "index.html")

# --- speaker notes ---
notes_js = (stage / "src" / "notes.js").read_text()
ids = re.findall(r"id: '([^']+)'", notes_js)
minutes = [float(x) for x in re.findall(r"minutes: ([0-9.]+)", notes_js)]
report["stage"]["notes"] = {"count": len(ids), "minutes": minutes, "totalMinutes": round(sum(minutes), 3),
                            "cjk": len(CJK.findall(notes_js))}

content_js = (Path(__file__).resolve().parents[4] / "presentation" / "deck" / "content.js").read_text()
report["contentJs"] = {"cjk": len(CJK.findall(content_js))}

# --- v2 theme fonts ---
import zipfile
v2 = ED / "v2-pptx" / "CSIT6000V_VerifiableTutor_v2.pptx"
with zipfile.ZipFile(v2) as z:
    theme = z.read("ppt/theme/theme1.xml").decode("utf-8")
latin = re.findall(r'<a:latin typeface="([^"]*)"', theme)
report["v2theme"] = {"latinFaces": latin}

# --- v2 notes: timing first lines / English ---
from pptx import Presentation
prs = Presentation(str(v2))
notes = []
for i, slide in enumerate(prs.slides, start=1):
    text = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
    notes.append({"slide": i, "chars": len(text), "cjk": len(CJK.findall(text)),
                  "head": text.strip()[:40]})
report["v2notes"] = {"missing": [n["slide"] for n in notes if n["chars"] == 0],
                     "cjk": sum(n["cjk"] for n in notes), "heads": [n["head"] for n in notes[:3]]}

# --- custom notes content: check first lines / timings ---
audit_c = json.loads((QA / "audits" / "html-custom.json").read_text())
report["customNotes"] = {"count": sum(1 for s in audit_c["slides"] if s["notesChars"] > 0),
                         "cjk": sum(s["cjkCount"] for s in audit_c["slides"]),
                         "heads": [s["notes"][:32] for s in audit_c["slides"][:3]]}

out = QA / "audits" / "static-checks.json"
out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
print(json.dumps(report, indent=2, ensure_ascii=False))