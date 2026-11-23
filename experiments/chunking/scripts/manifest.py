"""Write a reproducibility manifest for the page snapshot."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "data" / "pages"


def main() -> int:
    files = sorted(PAGES.glob("*.jsonl"))
    manifest = {"source": "data/corpus/pages", "files": {}, "pages": 0}
    for path in files:
        data = path.read_bytes()
        pages = sum(1 for line in data.splitlines() if line.strip())
        manifest["files"][path.name] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "pages": pages,
        }
        manifest["pages"] += pages
    out = PAGES / "MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tracked = ROOT / "results" / "page_manifest.json"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {out} and {tracked}: {manifest['pages']} pages, {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
