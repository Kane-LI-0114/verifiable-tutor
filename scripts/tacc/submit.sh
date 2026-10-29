#!/usr/bin/env bash
# Stage the shared TACC scripts into a task directory and submit it.
#
# The SDK uploads only the task directory, so bootstrap.sh and the pinned
# requirements are copied into <task>/_staged/ (gitignored) right before submit.
#
# Usage: scripts/tacc/submit.sh tacc/env-spike [--no-submit]
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TASK_DIR=${1:?usage: submit.sh <task-dir-relative-to-repo> [--no-submit]}
case "$TASK_DIR" in
    /*) ;;
    *) TASK_DIR="$REPO_ROOT/$TASK_DIR" ;;
esac
[ -f "$TASK_DIR/tuxiv.conf" ] || { echo "ERROR: no tuxiv.conf in $TASK_DIR" >&2; exit 1; }

mkdir -p "$TASK_DIR/_staged"
cp "$REPO_ROOT/scripts/tacc/bootstrap.sh" "$TASK_DIR/_staged/bootstrap.sh"
cp "$REPO_ROOT/scripts/tacc/requirements-tacc.txt" "$TASK_DIR/_staged/requirements.txt"
# Shared OCR stage helpers: a single source under scripts/tacc/ is staged into
# every task directory that runs render, layout or recognition.
for helper in render_pages.py ocr_pages.py assemble_document.py recognition_probe.py; do
    if [ -f "$REPO_ROOT/scripts/tacc/$helper" ]; then
        cp "$REPO_ROOT/scripts/tacc/$helper" "$TASK_DIR/_staged/$helper"
    fi
done
printf 'staged %s\n' "$TASK_DIR/_staged"

if [ "${2:-}" = "--no-submit" ]; then
    exit 0
fi

cd "$TASK_DIR"
tcloud submit
