#!/usr/bin/env python3
"""Crop the English UI screenshots used by the final deck."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
RAW = Path("/tmp/vt-deck-capture")
OUT = ROOT / "assets" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

# Crop boxes are in the 3200 x 2000 raw image produced by
# agent-browser at viewport 1600 x 1000 with device scale factor 2.
CROPS = {
    "agent-workchain": (1090, 170, 2590, 1345),
    "rag-source-pane": (500, 170, 3200, 1740),
    "rag-answer-detail": (500, 170, 2500, 1500),
    "rag-source-detail": (2500, 120, 3200, 1500),
    "kb-page9": (480, 90, 3200, 1910),
    "kb-page10": (480, 90, 3200, 1910),
    "kb-chat-before": (2410, 140, 3180, 1250),
    "kb-page9-detail": (480, 80, 2320, 1700),
    "kb-page10-detail": (480, 80, 2320, 1700),
    "practice-question": (990, 285, 2720, 1550),
    "policy-refusal": (1180, 85, 2630, 600),
}

CAPTURES = {
    "agent-workchain": "agent-workchain-raw.png",
    "rag-source-pane": "rag-source-pane-raw.png",
    "rag-answer-detail": "rag-source-pane-raw.png",
    "rag-source-detail": "rag-source-pane-raw.png",
    "kb-page9": "kb-page9-raw.png",
    "kb-page10": "kb-page10-raw.png",
    "kb-chat-before": "kb-page9-raw.png",
    "kb-page9-detail": "kb-page9-raw.png",
    "kb-page10-detail": "kb-page10-raw.png",
    "practice-question": "practice-question-raw.png",
    "policy-refusal": "policy-refusal-raw.png",
}


def rounded_with_shadow(image: Image.Image, radius: int = 22, pad: int = 28) -> Image.Image:
    image = image.convert("RGB")
    w, h = image.size
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (pad + 2, pad + 8, pad + w + 2, pad + h + 8),
        radius=radius,
        fill=(9, 9, 11, 90),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.alpha_composite(shadow)

    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(image, (0, 0), mask)
    canvas.alpha_composite(card, (pad, pad))

    border = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border)
    bd.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, outline=(229, 229, 229, 180), width=2)
    canvas.alpha_composite(border, (pad, pad))
    return canvas


def main() -> None:
    manifest = {
        "commit": "2b2b3a8",
        "viewport": "1600x1000 @2x",
        "language": "en",
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "assets": [],
    }
    for name, box in CROPS.items():
        src = RAW / CAPTURES[name]
        image = Image.open(src)
        crop = image.crop(box)
        card = rounded_with_shadow(crop)
        dest = OUT / f"{name}.png"
        card.save(dest, format="PNG", optimize=True)
        manifest["assets"].append(
            {
                "name": name,
                "source": src.name,
                "crop": list(box),
                "output": dest.name,
                "size": card.size,
            }
        )
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest['assets'])} assets to {OUT}")


if __name__ == "__main__":
    main()
