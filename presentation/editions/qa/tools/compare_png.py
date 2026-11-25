#!/usr/bin/env python3
"""Compare each deck's shipped PNGs with a fresh headless render, and measure blank bottom bands."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

QA = Path(__file__).resolve().parents[1]
ED = QA.parent
OUT = {}


def compare(label: str, shipped: Path, fresh: Path) -> dict:
    rows = []
    for i in range(1, 21):
        name = f"slide-{i:02d}.png"
        a = Image.open(shipped / name).convert("RGB")
        b = Image.open(fresh / name).convert("RGB")
        same_size = a.size == b.size
        if not same_size:
            b = b.resize(a.size)
        diff = ImageChops.difference(a, b).convert("L")
        stat = ImageStat.Stat(diff)
        hist = diff.histogram()
        total = a.size[0] * a.size[1]
        over8 = sum(hist[9:])
        rows.append({
            "slide": i,
            "shippedSize": list(a.size),
            "freshSize": list(Image.open(fresh / name).size),
            "meanAbsDiff": round(stat.mean[0], 4),
            "maxDiff": max(i for i, c in enumerate(hist) if c),
            "pctOver8": round(100.0 * over8 / total, 3),
        })
    worst = max(rows, key=lambda r: r["meanAbsDiff"])
    return {"shipped": str(shipped), "fresh": str(fresh), "identical": all(r["meanAbsDiff"] == 0 for r in rows), "worst": worst, "slides": rows}


def blank_band(path: Path) -> dict:
    img = Image.open(path).convert("L")
    w, h = img.size
    px = img.load()
    # row activity: mean absolute vertical gradient, ignoring the outer 24 px margins
    row_activity = []
    for y in range(1, h):
        s = 0
        for x in range(24, w - 24, 4):
            d = px[x, y] - px[x, y - 1]
            s += d if d >= 0 else -d
        row_activity.append(s / ((w - 48) / 4))
    threshold = 1.2
    last = 0
    for y in range(h - 1, 0, -1):
        if row_activity[y - 1] > threshold:
            last = y
            break
    return {"lastActiveRow": last, "blankPct": round(100.0 * (h - last) / h, 2)}


def deck_stats(label: str, folder: Path, prefix: str = "slide") -> dict:
    rows = []
    for i in range(1, 21):
        p = folder / f"{prefix}-{i:02d}.png"
        img = Image.open(p)
        rows.append({"slide": i, "size": list(img.size), "blank": blank_band(p)})
    return rows


out = {}
out["stage_compare"] = compare("stage", ED / "stage-html" / "exports" / "png", QA / "audits" / "render-stage")
out["custom_compare"] = compare("custom", ED / "custom-html" / "exports" / "slides", QA / "audits" / "render-custom")
out["stage_stats"] = deck_stats("stage", ED / "stage-html" / "exports" / "png")
out["custom_stats"] = deck_stats("custom", ED / "custom-html" / "exports" / "slides")
out["v2_stats"] = deck_stats("v2", ED / "v2-pptx" / "pages", prefix="page")
(QA / "audits" / "png-compare.json").write_text(json.dumps(out, indent=2))
for key in ("stage_compare", "custom_compare"):
    c = out[key]
    print(f"=== {key}: identical={c['identical']} worst={c['worst']}")
    for r in c["slides"]:
        print(f"  {r['slide']:02d} shipped={r['shippedSize']} fresh={r['freshSize']} mean={r['meanAbsDiff']} max={r['maxDiff']} pct>8={r['pctOver8']}%")
for key in ("stage_stats", "custom_stats", "v2_stats"):
    print(f"=== {key} blank bands ===")
    print("  " + " ".join(f"{r['slide']:02d}:{r['blank']['blankPct']}" for r in out[key]))