#!/usr/bin/env python3
"""Combine the 1920x1080 PNG slides into a 16:9 PDF and verify the page count."""
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SLIDES = ROOT / "exports" / "slides"
OUT = ROOT / "exports" / "CSIT6000V_VerifiableTutor_CustomHTML_2026F.pdf"

files = sorted(SLIDES.glob("slide-*.png"))
if len(files) != 20:
    sys.exit(f"expected 20 slide PNGs, found {len(files)}")

images = [Image.open(path).convert("RGB") for path in files]
for path, image in zip(files, images):
    if image.size != (1920, 1080):
        sys.exit(f"{path.name}: expected 1920x1080, got {image.size}")

images[0].save(OUT, "PDF", resolution=144.0, save_all=True, append_images=images[1:])
print(f"wrote {OUT} with {len(images)} pages at 144 dpi (13.333 x 7.5 in)")
