#!/usr/bin/env python3
"""CPU layout probe for the TACC environment spike.

Detects document layout with PP-DocLayoutV2 without touching the GPU. Tries the
PaddleX model API first, then a PaddleOCR layout pipeline, and records which one
works plus the block boxes it returns. Runs under the public Python through
PRoot with PYTHONPATH pointing at the project dependency cache.

Usage:
  run_proot "$VT_PYTHON" layout_probe.py --image page.png --out probe.json
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

RECORD = {"attempts": [], "ok": False}


def summarize_boxes(boxes):
    """Reduce a PaddleX layout box list to a compact, checkable summary."""
    labels = {}
    for box in boxes:
        label = box.get("label", "?")
        labels[label] = labels.get(label, 0) + 1
    first = []
    for box in boxes[:5]:
        coordinate = box.get("coordinate") or box.get("bbox") or []
        first.append(
            {
                "label": box.get("label"),
                "score": round(float(box.get("score", 0.0)), 3),
                "coordinate": [round(float(value), 1) for value in coordinate],
            }
        )
    return {"num_boxes": len(boxes), "labels": labels, "first_boxes": first}


def find_box_lists(node, depth=0):
    """Yield dicts that look like layout boxes from nested PaddleX output."""
    if depth > 6:
        return
    if isinstance(node, dict):
        if "coordinate" in node and ("label" in node or "cls_id" in node):
            yield node
            return
        for value in node.values():
            yield from find_box_lists(value, depth + 1)
    elif isinstance(node, list):
        for value in node:
            yield from find_box_lists(value, depth + 1)


def attempt_paddlex(image, model_dir, out_dir):
    from paddlex import create_model  # noqa: PLC0415

    kwargs = {"model_name": "PP-DocLayoutV2"}
    if model_dir and Path(model_dir, "inference.json").is_file():
        kwargs["model_dir"] = model_dir
    loaded_at = time.time()
    model = create_model(**kwargs)
    load_seconds = round(time.time() - loaded_at, 2)

    predict_at = time.time()
    outputs = list(model.predict(image))
    predict_seconds = round(time.time() - predict_at, 2)

    raw_path = out_dir / "layout-raw.json"
    results = []
    for index, output in enumerate(outputs):
        if hasattr(output, "save_to_json"):
            target = out_dir / f"layout-raw-{index}.json"
            try:
                output.save_to_json(str(target))
                results.append(json.loads(target.read_text(encoding="utf-8")))
                continue
            except Exception:  # noqa: BLE001 - fall through to attribute access
                pass
        data = getattr(output, "json", None)
        if data is not None:
            results.append(data)
    if results:
        raw_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    boxes = list(find_box_lists(results)) if results else []
    if not boxes and hasattr(outputs[0] if outputs else None, "boxes"):
        boxes = list(outputs[0].boxes)
    return {
        "load_seconds": load_seconds,
        "predict_seconds": predict_seconds,
        "summary": summarize_boxes(boxes),
        "raw_json": str(raw_path) if results else "",
        "raw_head": json.dumps(results[0])[:400] if results else "",
    }


def attempt_paddleocr_layout(image, out_dir):
    import paddleocr  # noqa: PLC0415

    pipeline_cls = getattr(paddleocr, "LayoutDetection", None)
    if pipeline_cls is None:
        raise RuntimeError("paddleocr.LayoutDetection is not exported")
    loaded_at = time.time()
    pipeline = pipeline_cls(model_name="PP-DocLayoutV2")
    load_seconds = round(time.time() - loaded_at, 2)
    predict_at = time.time()
    outputs = list(pipeline.predict(image))
    predict_seconds = round(time.time() - predict_at, 2)
    results = []
    for index, output in enumerate(outputs):
        if hasattr(output, "save_to_json"):
            target = out_dir / f"layout-ocr-raw-{index}.json"
            try:
                output.save_to_json(str(target))
                results.append(json.loads(target.read_text(encoding="utf-8")))
                continue
            except Exception:  # noqa: BLE001
                pass
        data = getattr(output, "json", None)
        if data is not None:
            results.append(data)
    boxes = list(find_box_lists(results)) if results else []
    return {
        "load_seconds": load_seconds,
        "predict_seconds": predict_seconds,
        "summary": summarize_boxes(boxes),
        "raw_head": json.dumps(results[0])[:400] if results else "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model-dir", default="")
    parser.add_argument("--out-dir", default="/tmp/layout-probe")
    args = parser.parse_args()

    image = Path(args.image)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not image.is_file():
        print(f"[layout] ERROR image missing: {image}", flush=True)
        Path(args.out).write_text(json.dumps({"ok": False, "error": f"image missing: {image}"}, indent=2))
        return 2

    print(f"[layout] image={image} size={image.stat().st_size} model_dir={args.model_dir or '<auto>'}", flush=True)

    for name, fn, needs_dir in [
        ("paddlex.create_model", attempt_paddlex, True),
        ("paddleocr.LayoutDetection", attempt_paddleocr_layout, False),
    ]:
        started = time.time()
        try:
            if needs_dir:
                payload = fn(str(image), args.model_dir, out_dir)
            else:
                payload = fn(str(image), out_dir)
            RECORD["attempts"].append({"api": name, "ok": True, "seconds": round(time.time() - started, 2), **payload})
            RECORD["ok"] = True
            RECORD["api"] = name
            print(f"[layout] PASS {name} {json.dumps(payload['summary'])}", flush=True)
            break
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            RECORD["attempts"].append(
                {
                    "api": name,
                    "ok": False,
                    "seconds": round(time.time() - started, 2),
                    "error": error,
                    "traceback_tail": traceback.format_exc().splitlines()[-10:],
                }
            )
            print(f"[layout] FAIL {name}: {error}", flush=True)

    Path(args.out).write_text(json.dumps(RECORD, indent=2), encoding="utf-8")
    print(f"[layout] wrote {args.out} ok={RECORD['ok']}", flush=True)
    return 0 if RECORD["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
