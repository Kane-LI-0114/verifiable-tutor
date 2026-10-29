#!/usr/bin/env python3
"""Enumerate every page of one PDF into the render manifest input format.

This is the whole-document counterpart of the page-selection manifest used by
the OCR smoke job: a demo user supplies one PDF file, so every page is parsed,
not a hand-picked subset.

Usage:
  run_proot "$VT_PYTHON" enumerate_pages.py --pdf input/course_project.pdf \
      --out input/doc-pages.json
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_pages(spec, page_count):
    if not spec:
        return list(range(1, page_count + 1))
    wanted = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            wanted.update(range(int(start), int(end) + 1))
        else:
            wanted.add(int(part))
    return sorted(page for page in wanted if 1 <= page <= page_count)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--pages", default="", help="page subset, for example 1-3 or 1,2,5")
    args = parser.parse_args()

    import pypdfium2  # noqa: PLC0415

    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        raise SystemExit(f"pdf not found: {pdf_path}")

    document = pypdfium2.PdfDocument(str(pdf_path))
    page_count = len(document)
    document.close()

    doc_id = pdf_path.stem
    selected = parse_pages(args.pages, page_count)
    if not selected:
        raise SystemExit(f"page subset {args.pages!r} selects no page from 1..{page_count}")
    entries = [
        {
            "doc_id": doc_id,
            "pdf": pdf_path.name,
            "page_no": page_no,
            "tags": [],
            "rationale": "demo request parse",
        }
        for page_no in selected
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(
        f"[enumerate] pdf={pdf_path.name} pages_total={page_count} selected={len(selected)} "
        f"sha256={sha256_file(pdf_path)[:16]} out={out}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
