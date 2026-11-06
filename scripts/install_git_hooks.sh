#!/usr/bin/env bash
# Install the repository hooks for this clone.
#
# The pre-commit hook keeps docs/physical-data-model.md and its Graphviz source
# and PNG in sync with the SQLite schema defined in Storage.initialize.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
echo "Installed .githooks as core.hooksPath."
echo "pre-commit refreshes the physical data model when storage.py or schema_docs.py is staged."
