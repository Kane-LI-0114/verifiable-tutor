"""The committed physical data model document tracks the live SQLite schema."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "physical-data-model.md"
DOT_PATH = REPO_ROOT / "docs" / "figures" / "physical-db.dot"
SCRIPT = REPO_ROOT / "scripts" / "build_data_model.py"


def test_committed_physical_data_model_is_current():
    from verifiable_tutor import schema_docs

    assert DOC_PATH.is_file(), "run .venv/bin/python scripts/build_data_model.py"
    assert DOT_PATH.is_file(), "run .venv/bin/python scripts/build_data_model.py"
    assert schema_docs.check_bundle() == []


def test_every_physical_table_and_column_has_a_note():
    from verifiable_tutor import schema_docs

    assert schema_docs.missing_notes() == []


def test_the_document_separates_the_logical_and_physical_models():
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "logical" in text.lower()
    assert "physical" in text.lower()
    assert "prd.md" in text
    assert "figures/prd-er.png" in text
    assert "figures/physical-db.png" in text
    for table in ("messages", "message_steps", "citations", "tool_calls"):
        assert table in text
    # Generate this document, never hand-edit it.
    assert "do not edit" in text.lower()


def test_build_script_check_mode_passes():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
