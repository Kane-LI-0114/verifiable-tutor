#!/usr/bin/env bash
set -euo pipefail

DEST="${HOME}/Library/Fonts/SourceSerif4-Variable.ttf"
URL="https://github.com/google/fonts/raw/main/ofl/sourceserif4/SourceSerif4%5Bopsz,wght%5D.ttf"

mkdir -p "${HOME}/Library/Fonts"
if [ ! -f "${DEST}" ]; then
  curl -L --fail --silent --show-error "${URL}" -o /tmp/SourceSerif4.ttf
  cp /tmp/SourceSerif4.ttf "${DEST}"
fi
fc-cache -f >/dev/null 2>&1 || true
fc-match "Source Serif 4"
