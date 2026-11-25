#!/usr/bin/env python3
"""Audit a deck for page count, fonts, and strict two-size typography."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from pptx import Presentation

ALLOWED_FONTS = {"Georgia", "Arial", "Courier New"}
ALLOWED_SIZES = {40.0, 64.0, 16.0, 14.0}


def main(path: str) -> int:
    prs = Presentation(path)
    problems: list[str] = []
    print(f"slides: {len(prs.slides)}")
    if len(prs.slides) != 20:
        problems.append(f"expected 20 slides, got {len(prs.slides)}")
    all_fonts: Counter[str] = Counter()
    for index, slide in enumerate(prs.slides, start=1):
        sizes: Counter[float] = Counter()
        fonts: Counter[str] = Counter()
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    text = run.text.strip()
                    if not text:
                        continue
                    if run.font.size is not None:
                        sizes[round(run.font.size.pt, 1)] += 1
                    name = run.font.name or "(inherited)"
                    fonts[name] += 1
                    all_fonts[name] += 1
        visible_sizes = sorted(s for s in sizes if s not in (0.0,))
        if len(visible_sizes) > 2:
            problems.append(f"slide {index}: {len(visible_sizes)} font sizes {visible_sizes}")
        if visible_sizes:
            low = min(visible_sizes)
            if low < 14:
                problems.append(f"slide {index}: body size below 14pt: {visible_sizes}")
        print(f"  {index:02d} sizes={visible_sizes} fonts={dict(fonts)}")
    bad_fonts = sorted(name for name in all_fonts if name not in ALLOWED_FONTS and name != "(inherited)")
    print(f"fonts: {dict(all_fonts)}")
    if bad_fonts:
        problems.append(f"disallowed fonts: {bad_fonts}")
    if problems:
        for problem in problems:
            print("FAIL:", problem)
        return 1
    print("PASS: page count, fonts, and two-size typography")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "deck.pptx"))
