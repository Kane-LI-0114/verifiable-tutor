#!/usr/bin/env python3
"""Audit the final deck for language and scope consistency."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "CSIT6000V_VerifiableTutor_Final_2026F.pptx"

CJK = re.compile(r"[\u3400-\u9fff]")
FORBIDDEN = [
    "every claim is verified",
    "all citations are verified",
    "every citation is verified",
]

def frame_text(frame) -> str:
    if not hasattr(frame, "text"):
        return ""
    return frame.text or ""

def main() -> int:
    presentation = Presentation(DECK)
    problems: list[str] = []
    instructor_slides: list[int] = []
    for index, slide in enumerate(presentation.slides, start=1):
        texts: list[str] = []
        for shape in slide.shapes:
            texts.append(frame_text(shape))
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    for cell in row.cells:
                        texts.append(cell.text or "")
        visible = "\n".join(texts)
        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text or ""
        joined = visible + "\n" + notes
        if CJK.search(joined):
            problems.append(f"slide {index}: CJK characters found")
        lower = visible.lower()
        for phrase in FORBIDDEN:
            if phrase in lower:
                problems.append(f"slide {index}: forbidden phrase {phrase!r}")
        if re.search(r"instructor|\bTA\b", visible, re.IGNORECASE):
            instructor_slides.append(index)

    if len(presentation.slides) != 20:
        problems.append(f"expected 20 slides, found {len(presentation.slides)}")
    allowed = {17, 18}
    unexpected = [n for n in instructor_slides if n not in allowed]
    if unexpected:
        problems.append(f"instructor/TA appears outside slides 17/18: {unexpected}")

    print(f"slides: {len(presentation.slides)}")
    print(f"instructor/TA slide numbers: {instructor_slides}")
    if problems:
        for problem in problems:
            print("FAIL:", problem)
        return 1
    print("PASS: language and scope audit")
    return 0

if __name__ == "__main__":
    sys.exit(main())
