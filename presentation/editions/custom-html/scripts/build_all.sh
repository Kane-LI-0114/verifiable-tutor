#!/usr/bin/env bash
# Full custom-html build: typography audit, runtime check, PNG export, PDF build.
set -euo pipefail
cd "$(dirname "$0")/.."

node scripts/check_type.mjs
node scripts/check_runtime.mjs
node scripts/render.mjs
python3 scripts/build_pdf.py

if command -v pdfinfo >/dev/null 2>&1; then
  pages="$(pdfinfo exports/CSIT6000V_VerifiableTutor_CustomHTML_2026F.pdf | awk '/^Pages:/ {print $2}')"
  if [ "$pages" != "20" ]; then
    echo "error: PDF has $pages pages, expected 20" >&2
    exit 1
  fi
  echo "PDF pages: $pages"
fi
