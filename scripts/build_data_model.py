#!/usr/bin/env python3
"""Regenerate or check the committed physical data model documentation.

The page and its Graphviz source are derived from the SQLite schema that
``Storage.initialize`` creates. Render the PNG after regenerating:

    dot -Gdpi=200 -Tpng docs/figures/physical-db.dot -o docs/figures/physical-db.png

Usage:
    .venv/bin/python scripts/build_data_model.py           # regenerate
    .venv/bin/python scripts/build_data_model.py --check   # fail when stale

Exit codes: 0 current, 1 stale or missing documents, 2 schema cannot be read.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from verifiable_tutor.schema_docs import (  # noqa: E402
    SchemaDocsError,
    check_bundle,
    write_bundle,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the committed physical model documents are stale",
    )
    args = parser.parse_args(argv)

    if args.check:
        try:
            problems = check_bundle()
        except SchemaDocsError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            print(
                "run .venv/bin/python scripts/build_data_model.py",
                file=sys.stderr,
            )
            return 1
        print("docs/physical-data-model.md is current")
        return 0

    try:
        paths = write_bundle()
    except SchemaDocsError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for path in paths:
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    print(
        "render the PNG with: dot -Gdpi=200 -Tpng "
        "docs/figures/physical-db.dot -o docs/figures/physical-db.png"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
