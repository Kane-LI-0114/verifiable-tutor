"""Record the interpreter, library versions, and model files of a run."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def display_path(value: str) -> str:
    path = Path(value)
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.name


def main() -> int:
    import numpy
    import torch
    import transformers

    model = ROOT / "models" / "bge-m3"
    files = {}
    if model.is_dir():
        for name in ("config.json", "pytorch_model.bin", "tokenizer.json"):
            path = model / name
            if path.is_file():
                files[name] = path.stat().st_size
    payload = {
        "python": sys.version,
        "executable": display_path(sys.executable),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "numpy": numpy.__version__,
        "model": "BAAI/bge-m3",
        "model_files": files,
        "device": "cpu",
        "max_length": 512,
    }
    out = ROOT / "results" / "environment.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
