#!/usr/bin/env python3
"""OCR smoke: run PaddleOCR-VL through the vLLM server on selected pages.

Layout detection (PP-DocLayoutV2) runs on CPU through PaddlePaddle, recognition
runs on the vLLM OpenAI-compatible server. One JSONL record is written per page
with the ADR-0002 fields plus a compact validation summary.

Usage:
  run_proot "$VT_PYTHON" ocr_pages.py \
      --manifest render-manifest.json --server-url http://127.0.0.1:8000/v1 \
      --api-model-name PaddleOCR-VL-1.6-0.9B \
      --layout-model-dir "$HOME/models/PP-DocLayoutV2" \
      --out-jsonl pages.jsonl --out-dir "$OUT" --out-summary summary.json
"""

import argparse
import json
import os
import statistics
import sys
import time
import traceback
from pathlib import Path


def iso_now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def normalise_bbox(bbox, width, height):
    if not bbox or len(bbox) < 4:
        return None
    x1, y1, x2, y2 = (float(value) for value in bbox[:4])
    return [
        round(x1 / width, 5),
        round(y1 / height, 5),
        round(x2 / width, 5),
        round(y2 / height, 5),
    ]


def save_result_json(result, stem, records_dir):
    """Persist the raw PaddleX JSON and return the parsed payload.

    The PaddleX API accepts either a directory (writing ``<basename>_res.json``)
    or a file path; both forms have been observed across versions, so try both
    and fall back to the in-memory result object.
    """
    errors = []
    candidates = []
    try:
        result.save_to_json(save_path=str(records_dir))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"dir: {type(exc).__name__}: {exc}")
    candidates.extend(sorted(records_dir.glob(f"{stem}*_res.json")))
    try:
        file_path = records_dir / f"{stem}.json"
        result.save_to_json(save_path=str(file_path))
        candidates.append(file_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"file: {type(exc).__name__}: {exc}")
    for candidate in candidates:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raw = getattr(result, "json", None)
    if callable(raw):
        raw = raw()
    if raw is not None:
        return raw
    raise RuntimeError(f"no JSON payload saved ({'; '.join(errors)})")


def save_result_markdown(result, stem, records_dir):
    """Return the page markdown, tolerating dict-or-file save semantics."""
    try:
        result.save_to_markdown(save_path=str(records_dir))
    except Exception:  # noqa: BLE001 - markdown is informative, not critical
        pass
    for candidate in sorted(records_dir.glob(f"{stem}*.md")):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    try:
        file_path = records_dir / f"{stem}.md"
        result.save_to_markdown(save_path=str(file_path))
        return file_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""


def extract_page(raw, entry, args, markdown_text):
    """Convert one PaddleOCRVL JSON payload into the project page record."""
    if not isinstance(raw, dict):
        raise RuntimeError(f"unexpected JSON payload type: {type(raw).__name__}")
    payload = raw.get("res", raw)

    width = int(entry["width_px"])
    height = int(entry["height_px"])
    blocks = []
    for block in payload.get("parsing_res_list") or []:
        bbox = block.get("block_bbox")
        block_px = [round(float(value), 1) for value in bbox[:4]] if bbox is not None else None
        block_norm = normalise_bbox(bbox, width, height)
        blocks.append(
            {
                "block_id": block.get("block_id"),
                "block_order": block.get("block_order"),
                "label": block.get("block_label"),
                "content": block.get("block_content") or "",
                "bbox_px": block_px,
                "bbox_norm": block_norm,
            }
        )

    layout_boxes = []
    layout = payload.get("layout_det_res") or {}
    for box in layout.get("boxes") or []:
        layout_boxes.append(
            {
                "label": box.get("label"),
                "score": round(float(box.get("score", 0.0)), 4) if box.get("score") is not None else None,
                "bbox_px": [round(float(value), 1) for value in (box.get("coordinate") or [])[:4]],
            }
        )

    text = "\n".join(block["content"] for block in blocks if block["content"])
    labels = {}
    for block in blocks:
        labels[block["label"]] = labels.get(block["label"], 0) + 1

    return {
        "schema": "vt-page-record/1",
        "doc_id": entry["doc_id"],
        "pdf": entry["pdf"],
        "pdf_sha256": entry["pdf_sha256"],
        "page_no": int(entry["page_no"]),
        "tags": entry.get("tags", []),
        "width_px": width,
        "height_px": height,
        "dpi": entry["dpi"],
        "pipeline_version": args.pipeline_version,
        "layout_model": "PP-DocLayoutV2",
        "recognition_model": args.api_model_name,
        "image": entry["png"],
        "webp": entry["webp"],
        "pdf_text_chars": entry.get("pdf_text_chars"),
        "markdown": markdown_text,
        "text": text,
        "blocks": blocks,
        "layout_boxes": layout_boxes,
        "label_counts": labels,
        "pipeline_page_index": payload.get("page_index"),
        "status": "ok",
    }


def validate_record(record):
    """Return a list of validation problems for one page record."""
    problems = []
    width = record["width_px"]
    height = record["height_px"]
    blocks = record["blocks"]
    if not blocks:
        problems.append("no_blocks")
    ids = [block["block_id"] for block in blocks]
    if ids and None not in ids and len(set(ids)) != len(ids):
        problems.append("duplicate_block_ids")
    for block in blocks:
        bbox = block["bbox_px"]
        if not bbox or len(bbox) != 4:
            problems.append(f"bad_bbox:{block['block_id']}")
            continue
        x1, y1, x2, y2 = bbox
        if x1 > x2 or y1 > y2:
            problems.append(f"inverted_bbox:{block['block_id']}")
        if x1 < -2 or y1 < -2 or x2 > width + 2 or y2 > height + 2:
            problems.append(f"out_of_bounds:{block['block_id']}")
        if not block["label"]:
            problems.append(f"missing_label:{block['block_id']}")
    orders = [block["block_order"] for block in blocks if block["block_order"] is not None]
    if orders and orders != sorted(orders):
        problems.append("reading_order_not_monotonic")
    return problems


def write_init_error(args, init_seconds, error):
    Path(args.out_jsonl).write_text("", encoding="utf-8")
    summary = {
        "schema": "vt-ocr-smoke/1",
        "generated_at": iso_now(),
        "server_url": args.server_url,
        "api_model_name": args.api_model_name,
        "pipeline_version": args.pipeline_version,
        "pipeline_init_seconds": init_seconds,
        "pages_total": 0,
        "pages_ok": 0,
        "pages_failed": 0,
        "blocks_total": 0,
        "page_seconds": {"min": None, "median": None, "max": None},
        "pipeline_init_error": error,
        "per_page": [],
    }
    Path(args.out_summary).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--server-url", required=True)
    parser.add_argument("--api-model-name", default="PaddleOCR-VL-1.6-0.9B")
    parser.add_argument("--layout-model-dir", default="")
    parser.add_argument("--pipeline-version", default="v1.6")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--layout-threshold", type=float, default=0.3)
    parser.add_argument("--max-concurrency", type=int, default=8)
    parser.add_argument("--cpu-threads", type=int, default=0)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out-summary", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    cpu_threads = args.cpu_threads or min(8, os.cpu_count() or 1)

    manifest = [entry for entry in json.loads(Path(args.manifest).read_text(encoding="utf-8")) if entry.get("status") == "ok"]
    if args.limit:
        manifest = manifest[: args.limit]
    out_dir = Path(args.out_dir)
    records_dir = out_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    print(f"[ocr] pages={len(manifest)} server={args.server_url} model={args.api_model_name}", flush=True)

    import paddle  # noqa: PLC0415

    # Paddle 3.2.1 does not expose paddle.set_num_threads; try the documented
    # setters in order and never fail the run over CPU thread tuning.
    thread_setters = [
        ("paddle.set_num_threads", getattr(paddle, "set_num_threads", None)),
        ("paddle.device.set_num_threads", getattr(getattr(paddle, "device", None), "set_num_threads", None)),
        ("paddle.base.core.set_num_threads", getattr(getattr(getattr(paddle, "base", None), "core", None), "set_num_threads", None)),
    ]
    applied = "none"
    for name, setter in thread_setters:
        if callable(setter):
            try:
                setter(cpu_threads)
                applied = name
                break
            except Exception as exc:  # noqa: BLE001
                print(f"[ocr] {name} failed: {exc}", flush=True)
    if applied == "none":
        try:
            paddle.set_flags({"FLAGS_omp_num_threads": cpu_threads})
            applied = "FLAGS_omp_num_threads"
        except Exception as exc:  # noqa: BLE001
            print(f"[ocr] paddle.set_flags failed: {exc}", flush=True)
    print(f"[ocr] paddle cpu threads requested={cpu_threads} applied={applied}", flush=True)

    from paddleocr import PaddleOCRVL  # noqa: PLC0415

    started = time.time()
    pipeline_kwargs = {
        "pipeline_version": args.pipeline_version,
        "device": args.device,
        "layout_detection_model_name": "PP-DocLayoutV2",
        "layout_threshold": args.layout_threshold,
        "vl_rec_backend": "vllm-server",
        "vl_rec_server_url": args.server_url,
        "vl_rec_api_model_name": args.api_model_name,
        "vl_rec_max_concurrency": args.max_concurrency,
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
    }
    if args.layout_model_dir:
        pipeline_kwargs["layout_detection_model_dir"] = args.layout_model_dir
    try:
        pipeline = PaddleOCRVL(**pipeline_kwargs)
    except Exception as exc:  # noqa: BLE001
        init_seconds = round(time.time() - started, 2)
        error = f"{type(exc).__name__}: {exc}"
        print(f"[ocr] pipeline init FAILED after {init_seconds}s: {error}", flush=True)
        traceback.print_exc()
        write_init_error(args, init_seconds, error)
        return 2
    init_seconds = round(time.time() - started, 2)
    print(f"[ocr] pipeline initialised in {init_seconds}s", flush=True)

    records = []
    for index, entry in enumerate(manifest, start=1):
        stem = f"{entry['doc_id']}.p{int(entry['page_no']):03d}"
        print(f"[ocr] ({index}/{len(manifest)}) {stem} tags={entry.get('tags')}", flush=True)
        page_started = time.time()
        record = {
            "schema": "vt-page-record/1",
            "doc_id": entry["doc_id"],
            "pdf": entry["pdf"],
            "page_no": int(entry["page_no"]),
            "tags": entry.get("tags", []),
            "status": "failed",
        }
        try:
            outputs = list(pipeline.predict(str(entry["png"])))
            if not outputs:
                raise RuntimeError("pipeline returned no result")
            result = outputs[0]
            raw = save_result_json(result, stem, records_dir)
            markdown_text = save_result_markdown(result, stem, records_dir)
            record = extract_page(raw, entry, args, markdown_text)
            record.update(
                {
                    "status": "ok",
                    "latency_seconds": round(time.time() - page_started, 3),
                    "timestamp": iso_now(),
                }
            )
            record["validation_problems"] = validate_record(record)
            print(
                f"[ocr] ok {stem} blocks={len(record['blocks'])} "
                f"labels={record['label_counts']} chars={len(record['text'])} "
                f"seconds={record['latency_seconds']}",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["traceback_tail"] = traceback.format_exc().splitlines()[-8:]
            record["latency_seconds"] = round(time.time() - page_started, 3)
            print(f"[ocr] FAILED {stem}: {record['error']}", flush=True)
        records.append(record)

    jsonl_path = Path(args.out_jsonl)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    ok_records = [record for record in records if record.get("status") == "ok"]
    latencies = [record["latency_seconds"] for record in ok_records if record.get("latency_seconds") is not None]
    all_problems = {
        record["doc_id"] + f".p{record['page_no']:03d}": record["validation_problems"]
        for record in ok_records
        if record.get("validation_problems")
    }
    label_totals = {}
    for record in ok_records:
        for label, count in record["label_counts"].items():
            label_totals[label] = label_totals.get(label, 0) + count
    text_ratios = []
    for record in ok_records:
        pdf_chars = record.get("pdf_text_chars") or 0
        if pdf_chars > 200:
            text_ratios.append(round(len(record["text"]) / pdf_chars, 2))

    summary = {
        "schema": "vt-ocr-smoke/1",
        "generated_at": iso_now(),
        "server_url": args.server_url,
        "api_model_name": args.api_model_name,
        "pipeline_version": args.pipeline_version,
        "layout_model": "PP-DocLayoutV2",
        "device": args.device,
        "max_concurrency": args.max_concurrency,
        "cpu_threads": cpu_threads,
        "pipeline_init_seconds": init_seconds,
        "pages_total": len(records),
        "pages_ok": len(ok_records),
        "pages_failed": len(records) - len(ok_records),
        "blocks_total": sum(len(record["blocks"]) for record in ok_records),
        "label_totals": label_totals,
        "page_seconds": {
            "min": round(min(latencies), 3) if latencies else None,
            "median": round(statistics.median(latencies), 3) if latencies else None,
            "max": round(max(latencies), 3) if latencies else None,
        },
        "ocr_to_pdf_text_ratio": {
            "min": min(text_ratios) if text_ratios else None,
            "median": statistics.median(text_ratios) if text_ratios else None,
            "max": max(text_ratios) if text_ratios else None,
        },
        "validation_problems": all_problems,
        "per_page": [
            {
                "doc_id": record["doc_id"],
                "page_no": record["page_no"],
                "tags": record.get("tags", []),
                "status": record.get("status"),
                "blocks": len(record.get("blocks", [])),
                "chars": len(record.get("text", "")),
                "seconds": record.get("latency_seconds"),
                "problems": record.get("validation_problems", record.get("error")),
            }
            for record in records
        ],
    }
    Path(args.out_summary).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"[ocr] done ok={len(ok_records)}/{len(records)} blocks={summary['blocks_total']} "
        f"median_page_s={summary['page_seconds']['median']} jsonl={jsonl_path}",
        flush=True,
    )
    return 0 if len(ok_records) == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
