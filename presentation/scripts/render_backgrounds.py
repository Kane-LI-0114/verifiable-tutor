#!/usr/bin/env python3
"""Render the deck backgrounds: paper, graphite, and the title stage."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "backgrounds"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 3200, 1800


def base(color: tuple[int, int, int], grid: tuple[int, int, int, int], aura_xy: tuple[int, int], aura_strength: float, step: int = 96) -> Image.Image:
    image = Image.new("RGBA", (W, H), (*color, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    if grid[3] > 0:
        for x in range(0, W, step):
            draw.line((x, 0, x, H), fill=grid, width=1)
        for y in range(0, H, step):
            draw.line((0, y, W, y), fill=grid, width=1)

    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = aura_xy
    dist = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)
    alpha = np.clip(1.0 - dist * 2.2, 0.0, 1.0) ** 2 * aura_strength
    aura = np.zeros((H, W, 4), dtype=np.uint8)
    aura[..., 0] = 20
    aura[..., 1] = 71
    aura[..., 2] = 230
    aura[..., 3] = (alpha * 255).astype(np.uint8)
    image.alpha_composite(Image.fromarray(aura, "RGBA"))
    return image


def title_stage() -> Image.Image:
    image = base((10, 10, 10), (255, 255, 255, 0), (2700, 120), 0.30, step=128)
    shot = Image.open(ROOT / "assets" / "screenshots" / "rag-source-pane.png").convert("RGBA")
    shot = shot.resize((1900, int(shot.height * 1900 / shot.width)), Image.LANCZOS)
    shot = shot.filter(ImageFilter.GaussianBlur(32))
    # Make the screenshot a faint texture instead of a bright rectangle.
    sw, sh = shot.size
    mask = np.zeros((sh, sw), dtype=np.uint8)
    for px in range(sw):
        mask[:, px] = int(58 * (px / max(1, sw - 1)) ** 0.7)
    mask[:120, :] = (mask[:120, :] * np.linspace(0, 1, 120)[:, None]).astype(np.uint8)
    mask[-120:, :] = (mask[-120:, :] * np.linspace(1, 0, 120)[:, None]).astype(np.uint8)
    shot.putalpha(Image.fromarray(mask))
    x = W - shot.width + 60
    y = (H - shot.height) // 2 - 120
    image.alpha_composite(shot, (x, y))

    # Fade the left edge into graphite.
    fade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fade)
    for i in range(1000):
        fd.rectangle((i, 0, i + 1, H), fill=(10, 10, 10, int(235 * (1 - i / 1000))))
    image.alpha_composite(fade)
    return image


def main() -> None:
    paper = base((250, 250, 250), (9, 9, 11, 0), (2920, 120), 0.10, step=128)
    graphite = base((10, 10, 10), (255, 255, 255, 0), (2920, 120), 0.26, step=128)
    paper.convert("RGB").save(OUT / "paper.jpg", quality=93, optimize=True)
    graphite.convert("RGB").save(OUT / "graphite.jpg", quality=93, optimize=True)
    title_stage().convert("RGB").save(OUT / "title.jpg", quality=93, optimize=True)
    print("wrote backgrounds")


if __name__ == "__main__":
    main()
