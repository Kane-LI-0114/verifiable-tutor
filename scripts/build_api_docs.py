#!/usr/bin/env python3
"""Regenerate or check the committed Swagger UI API documentation bundle.

The bundle under ``docs/api/`` is the maintained, offline API documentation:
``openapi.json`` is the deterministic OpenAPI export and ``index.html`` is a
Swagger UI page that embeds the same schema and loads vendored local assets.

Usage:
    .venv/bin/python scripts/build_api_docs.py           # regenerate
    .venv/bin/python scripts/build_api_docs.py --check   # fail when stale

Exit codes: 0 current, 1 stale docs, 2 missing or corrupt vendored assets.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from verifiable_tutor.api.docs import (  # noqa: E402
    DocsBundleError,
    check_bundle,
    vendor_problems,
    write_bundle,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the committed docs are missing or stale",
    )
    args = parser.parse_args(argv)

    if args.check:
        vendor_issues = vendor_problems()
        if vendor_issues:
            for issue in vendor_issues:
                print(issue, file=sys.stderr)
            print("run bash scripts/vendor_swagger_ui.sh", file=sys.stderr)
            return 2
        problems = check_bundle()
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            print(
                "run .venv/bin/python scripts/build_api_docs.py",
                file=sys.stderr,
            )
            return 1
        print("docs/api is current")
        return 0

    try:
        paths = write_bundle()
    except DocsBundleError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for path in paths:
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
