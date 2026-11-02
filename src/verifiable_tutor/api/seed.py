"""Seed command for the instructor account.

Usage: ``python -m verifiable_tutor.api.seed --instructor-email a@ust.hk
--instructor-password '...'``. The command is idempotent and never prints the
password. FR-A9.
"""

from __future__ import annotations

import argparse
import sys

from ..auth.service import AuthError, bootstrap_instructor
from ..settings import ensure_runtime_directories, load_settings
from ..storage import Storage
from ..trace import utc_now


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instructor-email", required=True)
    parser.add_argument("--instructor-password", required=True)
    args = parser.parse_args(argv)

    settings = load_settings()
    ensure_runtime_directories(settings)
    storage = Storage(settings.database_path)
    storage.initialize()
    try:
        result = bootstrap_instructor(
            storage=storage,
            email=args.instructor_email,
            password=args.instructor_password,
            clock=utc_now,
        )
    except AuthError as exc:
        print(f"seed failed: {exc.detail}", file=sys.stderr)
        return 1
    action = "created" if result["created"] else "updated"
    print(f"instructor {result['email']} {action} (role={result['role']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
