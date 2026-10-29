#!/usr/bin/env python3
"""Project a full-corpus OCR job from the smoke measurements.

Reads the page record summary and the render manifest, adds the measured setup
cost, and extrapolates to the 342-page corpus against the one-hour budget.

Usage:
  run_proot "$VT_PYTHON" projection.py --records records.json --manifest render-manifest.json \
      --startup-seconds 90 --overhead-seconds 3 --out projection.json
"""

import argparse
import json
import statistics
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--startup-seconds", type=float, default=0.0)
    parser.add_argument("--overhead-seconds", type=float, default=0.0)
    parser.add_argument("--pages", type=int, default=342)
    parser.add_argument("--budget-seconds", type=float, default=3300.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    records = json.load(open(args.records, encoding="utf-8"))
    manifest = json.load(open(args.manifest, encoding="utf-8"))

    page_median = float(records["page_seconds"]["median"] or 0.0)
    render_latencies = [entry["render_seconds"] for entry in manifest if entry.get("status") == "ok"]
    render_median = statistics.median(render_latencies) if render_latencies else 0.0
    per_page = page_median + render_median

    setup = args.startup_seconds + args.overhead_seconds
    projected = setup + per_page * args.pages
    result = {
        "pages_measured": records.get("pages_total"),
        "pages_ok": records.get("pages_ok"),
        "median_page_seconds": round(page_median, 3),
        "median_render_seconds": round(render_median, 3),
        "per_page_seconds": round(per_page, 3),
        "setup_seconds": round(setup, 1),
        "projected_pages": args.pages,
        "projected_seconds": int(round(projected)),
        "budget_seconds": args.budget_seconds,
        "fits_budget": projected < args.budget_seconds,
        "blocks_total": records.get("blocks_total"),
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(
        f"PROJECTION median={result['median_page_seconds']} per_page={result['per_page_seconds']} "
        f"projected={result['projected_seconds']} fits={str(result['fits_budget']).lower()} "
        f"blocks={result['blocks_total']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
