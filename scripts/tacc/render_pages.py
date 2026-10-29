#!/usr/bin/env python3
"""Render selected PDF pages for the TACC OCR smoke test.

Reads selected-pages.json (doc_id, workspace-relative pdf path, 1-based
page_no), renders each page at 200 DPI with pypdfium2, writes a PNG for
recognition and a WebP for the citation panel, extracts the PDF text layer,
and writes a manifest that the layout and recognition stages consume.

Usage:
  run_proot "$VT_PYTHON" render_pages.py \
      --pages selected-pages.json --pdf-root "$TACC_USERDIR/corpus-pdf" \
      --out-dir "$TACC_USERDIR/ocr-smoke" --dpi 200
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_pdf(pdf_root, entry):
    """Find the staged PDF for one selection entry."""
    name = Path(entry["pdf"]).name
    for candidate in (pdf_root / name, Path(entry["pdf"])):
        if candidate.is_file():
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", required=True)
    parser.add_argument("--pdf-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()

    import pypdfium2  # noqa: PLC0415

    pages = json.loads(Path(args.pages).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    png_dir = out_dir / "pages"
    webp_dir = out_dir / "images"
    png_dir.mkdir(parents=True, exist_ok=True)
    webp_dir.mkdir(parents=True, exist_ok=True)
    pdf_root = Path(args.pdf_root)

    manifest = []
    scale = args.dpi / 72.0
    documents = {}
    for entry in pages:
        pdf_path = resolve_pdf(pdf_root, entry)
        if pdf_path is None:
            manifest.append({"doc_id": entry["doc_id"], "page_no": entry["page_no"], "status": "pdf_missing"})
            print(f"[render] FAIL {entry['doc_id']} p{entry['page_no']}: pdf missing under {pdf_root}")
            continue
        if str(pdf_path) not in documents:
            documents[str(pdf_path)] = {
                "sha256": sha256_file(pdf_path),
                "doc": pypdfium2.PdfDocument(str(pdf_path)),
                "bytes": pdf_path.stat().st_size,
            }
        document = documents[str(pdf_path)]
        page_index = int(entry["page_no"]) - 1
        if page_index < 0 or page_index >= len(document["doc"]):
            manifest.append({"doc_id": entry["doc_id"], "page_no": entry["page_no"], "status": "page_out_of_range"})
            print(f"[render] FAIL {entry['doc_id']} p{entry['page_no']}: out of range")
            continue

        started = time.time()
        page = document["doc"][page_index]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        stem = f"{entry['doc_id']}.p{int(entry['page_no']):03d}"
        png_path = png_dir / f"{stem}.png"
        webp_path = webp_dir / f"{stem}.webp"
        image.save(png_path)
        image.save(webp_path, format="WEBP", quality=90)
        text = page.get_textpage().get_text_range()
        page.close()

        record = {
            "status": "ok",
            "doc_id": entry["doc_id"],
            "pdf": entry["pdf"],
            "pdf_sha256": document["sha256"],
            "pdf_bytes": document["bytes"],
            "page_no": int(entry["page_no"]),
            "tags": entry.get("tags", []),
            "width_px": image.width,
            "height_px": image.height,
            "dpi": args.dpi,
            "png": str(png_path),
            "png_bytes": png_path.stat().st_size,
            "webp": str(webp_path),
            "webp_bytes": webp_path.stat().st_size,
            "pdf_text_chars": len(text),
            "pdf_text_head": text[:200].replace("\n", " "),
            "render_seconds": round(time.time() - started, 3),
        }
        manifest.append(record)
        print(f"[render] ok {stem} {image.width}x{image.height} png={record['png_bytes']}B text_chars={len(text)}")

    for document in documents.values():
        document["doc"].close()

    manifest_path = out_dir / "render-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    ok = [record for record in manifest if record.get("status") == "ok"]
    print(f"[render] pages={len(manifest)} ok={len(ok)} manifest={manifest_path}")
    return 0 if len(ok) == len(manifest) else 1


if __name__ == "__main__":
    sys.exit(main())
