#!/usr/bin/env python3
"""Content and fact audit across the three deck editions (read-only)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]  # presentation/editions/qa
EDITIONS = ROOT.parent

EXPECTED_TITLES = [
    "Verifiable Tutor",
    "A study loop students can trust",
    "One local product. One batch backend on TACC",
    "The data model makes the evidence chain durable",
    "A small stack with one job per layer",
    "A typed loop, not a prompt",
    "Watch the loop work",
    "Build the evidence base on TACC",
    "Retrieve pages, then let the model read",
    "Every paragraph names its source",
    "A conversation that lives beside the file",
    "From a marker to the exact page",
    "A source is not a citation until the span passes",
    "Practice and integrity",
    "Practice, then check",
    "We win on coverage. We tie on grading",
    "Tutorials are the hard slice",
    "Verifiability is a system property",
    "One question, end to end",
    "Evaluation method and TACC evidence",
]

CJK = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af\uff00-\uffef]")
NUM = re.compile(r"\b\d+(?:\.\d+)?(?:/\d+)?\b")

FACTS = {
    "17 tables": re.compile(r"\b17\b[^.]{0,24}\b(tables?)\b", re.I),
    "16 documents": re.compile(r"\b16\b[^.]{0,20}\b(docs?|documents?)\b", re.I),
    "593 pages": re.compile(r"\b593\b", re.I),
    "612 chunks": re.compile(r"\b612\b", re.I),
    "nDCG 0.849": re.compile(r"\b0\.849\b"),
    "hit 0.882": re.compile(r"\b0\.882\b"),
    "937 tokens": re.compile(r"\b937\b"),
    "10/10": re.compile(r"\b10/10\b"),
    "5/5": re.compile(r"\b5/5\b"),
    "0.617": re.compile(r"\b0\.617\b"),
    "434 s": re.compile(r"\b434\b"),
    "43.9 s": re.compile(r"\b43\.9\b"),
    "8/8": re.compile(r"\b8/8\b"),
}


def norm_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = text.strip(" .")
    return text.lower()


def pptx_slides(path: Path):
    prs = Presentation(str(path))
    slides = []
    for idx, slide in enumerate(prs.slides, start=1):
        runs = []  # (size, text, top, left)
        def walk(shapes):
            for shape in shapes:
                if shape.shape_type == 6 and hasattr(shape, "shapes"):  # group
                    walk(shape.shapes)
                    continue
                top = shape.top if shape.top is not None else 0
                left = shape.left if shape.left is not None else 0
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        t = "".join(r.text for r in para.runs).strip()
                        if not t:
                            continue
                        size = max((r.font.size.pt for r in para.runs if r.font.size), default=0)
                        runs.append((size, t, top, left))
                if getattr(shape, "has_table", False) and shape.has_table:
                    for row in shape.table.rows:
                        for cell in row.cells:
                            t = cell.text.strip()
                            if t:
                                runs.append((0, t, top, left))
        walk(slide.shapes)
        display = [r for r in runs if r[0] >= 40]
        display.sort(key=lambda r: (r[2], r[3]))
        title = display[0][1] if display else (runs[0][1] if runs else "")
        visible = " ".join(r[1] for r in runs)
        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text
        slides.append({"index": idx, "title": title, "visible": visible, "notes": notes,
                       "display_texts": [r[1] for r in display], "sizes": sorted({round(r[0], 1) for r in runs if r[0]})})
    return slides


def html_slides(path: Path):
    data = json.loads(path.read_text())
    out = []
    for s in data["slides"]:
        out.append({"index": s["index"], "title": s["titleDisplay"], "titleAttr": s.get("titleAttr", ""),
                    "visible": s.get("visibleText", ""), "notes": s.get("notes", ""),
                    "sizes": s.get("sizeKeys", []), "id": s.get("id", ""),
                    "imgCount": s.get("imgCount", 0), "svgCount": s.get("svgCount", 0),
                    "badSizes": s.get("badSizes", []), "badFamilies": s.get("badFamilies", []),
                    "brokenImages": s.get("brokenImages", []), "outOfBounds": s.get("outOfBounds", [])})
    return out


def check_deck(name: str, slides, source_path: Path):
    report = {"deck": name, "source": str(source_path.relative_to(EDITIONS.parent.parent)),
              "slideCount": len(slides), "issues": [], "titles": [], "facts": {}, "instructor": {},
              "yoga": [], "cjk": [], "numbers": [], "notes": []}
    if len(slides) != 20:
        report["issues"].append(f"slide count {len(slides)} != 20")
    for s in slides:
        exp = EXPECTED_TITLES[s["index"] - 1]
        got = s["title"]
        ok = norm_title(got) == norm_title(exp) or norm_title(s.get("titleAttr", "")) == norm_title(exp)
        report["titles"].append({"index": s["index"], "expected": exp, "got": got, "titleAttr": s.get("titleAttr", ""), "ok": ok})
        if not ok:
            report["issues"].append(f"slide {s['index']} title mismatch: {got!r} vs {exp!r}")
    all_visible = " \n".join(s["visible"] for s in slides)
    all_notes = " \n".join(s["notes"] for s in slides)
    # facts per slide
    for label, rx in FACTS.items():
        hits = [s["index"] for s in slides if rx.search(s["visible"])]
        note_hits = [s["index"] for s in slides if rx.search(s["notes"])]
        report["facts"][label] = {"slides": hits, "notes": note_hits}
        if not hits:
            report["issues"].append(f"fact {label} not in visible slide text")
    # instructor / TA mentions
    instructor = [s["index"] for s in slides if re.search(r"\bInstructor\b", s["visible"], re.I)]
    ta = [s["index"] for s in slides if re.search(r"\bTAs?\b", s["visible"])]
    instructor_notes = [s["index"] for s in slides if re.search(r"\bInstructor\b", s["notes"], re.I)]
    ta_notes = [s["index"] for s in slides if re.search(r"\bTAs?\b", s["notes"])]
    report["instructor"] = {"visible": instructor, "ta": ta, "notes_instructor": instructor_notes, "notes_ta": ta_notes}
    bad_mentions = [i for i in instructor + ta if i not in (17, 18)]
    if bad_mentions:
        report["issues"].append(f"Instructor/TA mentioned outside slides 17/18: {sorted(set(bad_mentions))}")
    # yoga mentions
    for s in slides:
        if re.search(r"\bYoga\b", s["visible"] + " " + s["notes"]):
            report["yoga"].append(s["index"])
    # cjk
    for s in slides:
        if CJK.search(s["visible"] + " " + s["notes"]):
            report["cjk"].append(s["index"])
            report["issues"].append(f"CJK text on slide {s['index']}")
    # numeric tokens with context
    seen = set()
    for s in slides:
        for m in NUM.finditer(s["visible"]):
            token = m.group(0)
            if token in seen:
                continue
            seen.add(token)
            a = max(0, m.start() - 34); b = min(len(s["visible"]), m.end() + 34)
            report["numbers"].append({"token": token, "slide": s["index"], "context": s["visible"][a:b].strip()})
    report["numbers"].sort(key=lambda r: (float(r["token"].split("/")[0]), r["token"]))
    report["notesPresent"] = [s["index"] for s in slides if s["notes"].strip()]
    if len(report["notesPresent"]) != 20:
        report["issues"].append(f"missing speaker notes on slides {sorted(set(range(1,21)) - set(report['notesPresent']))}")
    return report


def main():
    out = {"decks": {}}
    v2 = pptx_slides(EDITIONS / "v2-pptx" / "CSIT6000V_VerifiableTutor_v2.pptx")
    out["decks"]["v2"] = check_deck("v2", v2, EDITIONS / "v2-pptx" / "CSIT6000V_VerifiableTutor_v2.pptx")
    for key, jf, src in [
        ("stage", ROOT / "audits" / "html-stage.json", EDITIONS / "stage-html" / "index.html"),
        ("custom", ROOT / "audits" / "html-custom.json", EDITIONS / "custom-html" / "index.html"),
    ]:
        out["decks"][key] = check_deck(key, html_slides(jf), src)
    path = ROOT / "audits" / "content-audit.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    for key, rep in out["decks"].items():
        print(f"=== {key}: {rep['slideCount']} slides, {len(rep['issues'])} issues ===")
        for issue in rep["issues"]:
            print("  ISSUE:", issue)
        print("  instructor visible:", rep["instructor"]["visible"], "notes:", rep["instructor"]["notes_instructor"])
        print("  TA visible:", rep["instructor"]["ta"], "notes:", rep["instructor"]["notes_ta"])
        print("  yoga slides:", rep["yoga"])
        missing_notes = sorted(set(range(1, 21)) - set(rep["notesPresent"]))
        print("  notes present:", len(rep["notesPresent"]), "missing:", missing_notes)
        print("  facts:", {k: v["slides"] for k, v in rep["facts"].items()})
        print("  titles ok:", sum(1 for t in rep["titles"] if t["ok"]), "/ 20")
        for t in rep["titles"]:
            if not t["ok"]:
                print("    title:", t)
        print("  numbers:", len(rep["numbers"]))
    print("\nwrote", path)


if __name__ == "__main__":
    main()
