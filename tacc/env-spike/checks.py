#!/usr/bin/env python3
"""Environment checks for the TACC environment mechanics spike.

Runs under the public Python 3.12 through the PRoot runtime with PYTHONPATH
pointing at the project dependency cache. Every check is independent: a
failure is recorded in the JSON report instead of aborting the run.

Usage:
  run_proot "$VT_PYTHON" checks.py --pdf <pdf> --out-dir <dir> --out <json>
"""

import argparse
import importlib.metadata as md
import json
import os
import platform
import shutil
import sqlite3
import sys
import time
import traceback
import urllib.request
from pathlib import Path

RECORDS = []

CANDIDATE_MODELS = [
    "PaddlePaddle/PaddleOCR-VL-1.6",
    "PaddlePaddle/PaddleOCR-VL",
    "PaddlePaddle/PP-DocLayoutV2",
    "PaddlePaddle/PP-DocLayoutV3",
    "rednote-hilab/dots.ocr",
]

CANDIDATE_PACKAGES = ["paddlepaddle", "paddleocr", "paddlex", "pypdfium2", "pytest"]


def dist_version(dist):
    try:
        return md.version(dist)
    except Exception:
        return "missing"


def run_check(name, fn, critical=False):
    record = {"name": name, "critical": critical, "ok": False, "seconds": 0.0}
    started = time.time()
    try:
        record["result"] = fn()
        record["ok"] = True
        status = "PASS"
    except Exception as exc:  # noqa: BLE001 - report, do not abort
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["traceback_tail"] = traceback.format_exc().splitlines()[-10:]
        status = "FAIL"
    record["seconds"] = round(time.time() - started, 3)
    RECORDS.append(record)
    detail = record.get("result") if record["ok"] else record["error"]
    print(f"[check] {status} {name} ({record['seconds']}s): {detail}", flush=True)
    return record


def http_json(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "vt-env-spike/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# ---------------------------------------------------------------- checks


def check_python():
    return {
        "version": sys.version.split()[0],
        "executable": sys.executable,
        "prefix": sys.prefix,
        "platform": platform.platform(),
        "libc": platform.libc_ver(),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "sys_path_first": sys.path[:4],
    }


def check_fts5():
    con = sqlite3.connect(":memory:")
    options = [row[0] for row in con.execute("pragma compile_options")]
    con.execute("create virtual table docs using fts5(doc_id, page_no, text)")
    rows = [
        ("lecture1", 3, "attention is all you need"),
        ("lecture1", 7, "the softmax of the scaled dot product"),
        ("lecture2", 2, "backpropagation through the attention block"),
    ]
    con.executemany("insert into docs values (?, ?, ?)", rows)
    hits = con.execute(
        "select doc_id, page_no, bm25(docs) as rank from docs "
        "where docs match 'attention' order by rank limit 3"
    ).fetchall()
    con.close()
    return {
        "sqlite": sqlite3.sqlite_version,
        "fts5_enabled": any("ENABLE_FTS5" in option for option in options),
        "compile_options_sample": [o for o in options if "FTS" in o or "JSON" in o][:6],
        "match_rows": [list(hit) for hit in hits],
    }


def check_pypdfium2(pdf_path, out_dir):
    import pypdfium2  # noqa: PLC0415
    from PIL import Image  # noqa: F401,PLC0415 - pillow is in the public env

    result = {"version": dist_version("pypdfium2"), "module": pypdfium2.__file__, "pages": {}}
    if not pdf_path or not Path(pdf_path).is_file():
        result["skipped"] = f"pdf not found: {pdf_path}"
        return result
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pypdfium2.PdfDocument(pdf_path)
    result["page_count"] = len(doc)
    pages = sorted({0, min(4, len(doc) - 1)})
    for index in pages:
        started = time.time()
        page = doc[index]
        scale = 200 / 72  # 200 DPI
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        png_path = out_dir / f"sample-p{index + 1:03d}.png"
        webp_path = out_dir / f"sample-p{index + 1:03d}.webp"
        image.save(png_path)
        image.save(webp_path, format="WEBP", quality=90)
        text = page.get_textpage().get_text_range()
        result["pages"][str(index + 1)] = {
            "width_px": image.width,
            "height_px": image.height,
            "png": str(png_path),
            "webp_bytes": webp_path.stat().st_size,
            "text_chars": len(text),
            "text_head": text[:120].replace("\n", " "),
            "render_seconds": round(time.time() - started, 3),
        }
        page.close()
    doc.close()
    return result


def check_pytest():
    import pytest  # noqa: PLC0415

    return {"version": pytest.__version__, "module": pytest.__file__}


def check_paddle():
    import paddle  # noqa: PLC0415

    device = paddle.get_device()
    tiny = paddle.to_tensor([[1.0, 2.0], [3.0, 4.0]]) + 1
    return {
        "version": paddle.__version__,
        "module": paddle.__file__,
        "device": device,
        "compiled_with_cuda": paddle.is_compiled_with_cuda(),
        "cuda_device_count": paddle.device.get_device_count("gpu") if paddle.is_compiled_with_cuda() else 0,
        "tiny_op_sum": float(tiny.sum()),
    }


def check_cv2():
    import cv2  # noqa: PLC0415

    build = cv2.getBuildInformation()
    gui = [line.strip() for line in build.splitlines() if "GUI" in line or "GTK" in line][:3]
    return {"version": cv2.__version__, "module": cv2.__file__, "gui_build": gui}


def check_paddleocr():
    import paddleocr  # noqa: PLC0415

    interesting = [
        "PaddleOCRVL",
        "PaddleOCR",
        "PPStructureV3",
        "LayoutDetection",
        "DocPreprocessor",
        "FormulaRecognitionPipeline",
    ]
    return {
        "version": dist_version("paddleocr"),
        "module": paddleocr.__file__,
        "classes_present": [name for name in interesting if hasattr(paddleocr, name)],
        "classes_missing": [name for name in interesting if not hasattr(paddleocr, name)],
    }


def check_paddlex():
    import paddlex  # noqa: PLC0415

    return {
        "version": dist_version("paddlex"),
        "module": paddlex.__file__,
        "has_create_model": hasattr(paddlex, "create_model"),
    }


def check_paddleocr_vl_api():
    import inspect  # noqa: PLC0415

    from paddleocr import PaddleOCRVL  # noqa: PLC0415

    signature = inspect.signature(PaddleOCRVL.__init__)
    parameters = {
        name: (None if parameter.default is inspect.Parameter.empty else repr(parameter.default))
        for name, parameter in signature.parameters.items()
        if name != "self"
    }
    interesting = {
        name: value
        for name, value in parameters.items()
        if any(marker in name for marker in ("vl_rec", "layout", "pipeline_version", "device", "engine"))
    }
    return {"n_parameters": len(parameters), "interesting_parameters": interesting}


def check_hf_hub():
    import huggingface_hub  # noqa: PLC0415

    return {
        "version": dist_version("huggingface_hub"),
        "module": os.path.dirname(huggingface_hub.__file__),
        "HF_ENDPOINT": os.environ.get("HF_ENDPOINT", ""),
        "cli_present": shutil.which("hf") is not None,
    }


def check_hf_models():
    result = {}
    for repo_id in CANDIDATE_MODELS:
        entry = {}
        try:
            info = http_json(f"https://hf-mirror.com/api/models/{repo_id}?blobs=true")
            siblings = info.get("siblings") or []
            total = sum((sibling.get("size") or 0) for sibling in siblings)
            entry = {
                "http": 200,
                "sha": info.get("sha", "")[:12],
                "files": len(siblings),
                "total_mb": round(total / 1e6, 1),
                "has_safetensors": any(s.get("rfilename", "").endswith(".safetensors") for s in siblings),
            }
        except Exception as exc:  # noqa: BLE001
            entry = {"error": f"{type(exc).__name__}: {exc}"}
        result[repo_id] = entry
    if all("error" in entry for entry in result.values()):
        raise RuntimeError("no Hugging Face model metadata was reachable")
    return result


def check_pypi():
    result = {}
    for package in CANDIDATE_PACKAGES:
        try:
            info = http_json(f"https://pypi.org/pypi/{package}/json")
            result[package] = {
                "latest": info["info"]["version"],
                "requires_python": info["info"].get("requires_python"),
                "installed_here": dist_version(package),
            }
        except Exception as exc:  # noqa: BLE001
            result[package] = {"error": f"{type(exc).__name__}: {exc}"}
    if all("error" in entry for entry in result.values()):
        raise RuntimeError("PyPI metadata was not reachable")
    return result


def check_disk():
    result = {}
    for label, path in [
        ("home", os.environ.get("HOME")),
        ("userdir", os.environ.get("TACC_USERDIR")),
        ("tmp", "/tmp"),
        ("mnt_home", "/mnt/home"),
    ]:
        if not path:
            continue
        try:
            usage = shutil.disk_usage(path)
            result[label] = {
                "path": path,
                "total_gb": round(usage.total / 1e9, 1),
                "used_gb": round(usage.used / 1e9, 1),
                "free_gb": round(usage.free / 1e9, 1),
            }
        except Exception as exc:  # noqa: BLE001
            result[label] = {"path": path, "error": str(exc)}
    return result


def check_model_caches():
    result = {}
    home = Path(os.environ.get("HOME", "/root"))
    for name in [".paddlex", ".cache/huggingface", ".cache/uv", ".cache/vt-bootstrap", "models", "vt-deps"]:
        path = home / name
        if path.exists():
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            result[name] = {"exists": True, "mb": round(size / 1e6, 1)}
        else:
            result[name] = {"exists": False}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default="")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    print(f"[checks] python={sys.version.split()[0]} exe={sys.executable}", flush=True)
    print(f"[checks] PYTHONPATH={os.environ.get('PYTHONPATH', '')}", flush=True)

    run_check("python_platform", check_python, critical=True)
    run_check("sqlite_fts5", check_fts5, critical=True)
    run_check("pypdfium2_render", lambda: check_pypdfium2(args.pdf, args.out_dir), critical=True)
    run_check("pytest", check_pytest)
    run_check("paddle", check_paddle)
    run_check("cv2", check_cv2)
    run_check("paddleocr", check_paddleocr)
    run_check("paddlex", check_paddlex)
    run_check("paddleocr_vl_api", check_paddleocr_vl_api)
    run_check("huggingface_hub", check_hf_hub)
    run_check("hf_model_availability", check_hf_models)
    run_check("pypi_current_versions", check_pypi)
    run_check("disk", check_disk)
    run_check("model_caches", check_model_caches)

    critical_failed = [r["name"] for r in RECORDS if r["critical"] and not r["ok"]]
    report = {
        "schema": "vt-env-spike/1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "host": platform.node(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", ""),
        "critical_failed": critical_failed,
        "checks": RECORDS,
    }
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[checks] wrote {args.out}; critical_failed={critical_failed}", flush=True)
    return 1 if critical_failed else 0


if __name__ == "__main__":
    sys.exit(main())
