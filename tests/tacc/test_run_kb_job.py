import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "tacc" / "run_kb_job.py"


def load_driver():
    spec = importlib.util.spec_from_file_location("run_kb_job", DRIVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def valid_record(corpus_hash: str) -> dict:
    return {
        "schema": "vt-kb-record/1",
        "build_id": "kb-test",
        "job_id": "28001",
        "chunk_id": "course_project:p001:c00",
        "doc_id": "course_project",
        "page_no": 1,
        "section": "Course Project",
        "source_block_ids": ["0"],
        "summary": "A summary.",
        "key_terms": ["agent"],
        "study_questions": ["q1", "q2"],
        "citations": [
            {
                "doc_id": "course_project",
                "page_no": 1,
                "quote": "Building an End-to-End Agent System",
            }
        ],
        "model": "qwen3.8-27b",
        "prompt_version": "kb-v1",
        "corpus_hash": corpus_hash,
        "created_at": "2026-11-02T02:00:00+00:00",
    }


def make_inputs(tmp_path: Path) -> dict:
    chunk = {
        "chunk_id": "course_project:p001:c00",
        "doc_id": "course_project",
        "page_no": 1,
        "section": "Course Project",
        "source_block_ids": ["0"],
        "text": "Course Project\nBuilding an End-to-End Agent System",
    }
    request = {
        "schema": "vt-kb-request/1",
        "build_id": "kb-test",
        "corpus_hash": "abc123",
        "input_path": str(tmp_path / "USERDIR" / "kb" / "requests" / "kb-test" / "input.jsonl"),
        "record_path": str(tmp_path / "USERDIR" / "kb" / "results" / "kb-test" / "records.jsonl"),
        "progress_path": str(tmp_path / "USERDIR" / "kb" / "results" / "kb-test" / "progress.json"),
    }
    request_path = tmp_path / "request.json"
    input_path = tmp_path / "input.jsonl"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    input_path.write_text(json.dumps(chunk) + "\n", encoding="utf-8")
    return {
        "build_id": "kb-test",
        "request": request,
        "chunks": [chunk],
        "local_root": tmp_path,
        "request_path": request_path,
        "input_path": input_path,
        "task_dir": tmp_path / "task",
        "userdir": str(tmp_path / "USERDIR"),
        "job_name": "vt-kb",
    }


def write_results(tmp_path: Path, *, quote: str) -> Path:
    results = tmp_path / "results"
    results.mkdir()
    record = valid_record("abc123")
    record["citations"][0]["quote"] = quote
    (results / "records.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
    (results / "progress.json").write_text(
        json.dumps(
            {
                "schema": "vt-kb-progress/1",
                "build_id": "kb-test",
                "job_id": "28001",
                "status": "done",
                "done_chunks": 1,
                "total_chunks": 1,
                "error": None,
                "updated_at": "2026-11-02T02:01:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    return results


def test_validate_build_accepts_a_complete_result_set(tmp_path: Path) -> None:
    driver = load_driver()
    build = make_inputs(tmp_path)
    results = write_results(tmp_path, quote="Building an End-to-End Agent System")

    validation = driver.validate_build(build, results, {})

    assert validation["pass"] is True
    assert validation["records_valid"] == 1
    assert validation["invalid_records"] == []


def test_validate_build_rejects_a_quote_missing_from_the_page(tmp_path: Path) -> None:
    driver = load_driver()
    build = make_inputs(tmp_path)
    results = write_results(tmp_path, quote="not on this page")

    validation = driver.validate_build(build, results, {})

    assert validation["pass"] is False
    assert validation["invalid_records"]


def test_store_build_creates_the_storage_directories(
    tmp_path: Path, monkeypatch
) -> None:
    driver = load_driver()
    monkeypatch.setattr(driver, "REPO_ROOT", tmp_path)
    build = make_inputs(tmp_path)
    results = write_results(tmp_path, quote="Building an End-to-End Agent System")
    validation = driver.validate_build(build, results, {})
    summary = {
        "job_id": "28001",
        "submitted_epoch": 1000.0,
        "upload_mode": "userdir_root",
        "upload": {"mode": "userdir_root", "remote_names": {}},
        "job_summary": {"job_started_epoch": 1002.0, "total_seconds": 479.0},
    }

    build_record = driver.store_build(build, results, summary, validation)

    records = tmp_path / "data" / "kb" / "records" / "kb-test.jsonl"
    summary_path = tmp_path / "data" / "kb" / "builds" / "kb-test.json"
    assert records.is_file()
    assert summary_path.is_file()
    stored = json.loads(summary_path.read_text(encoding="utf-8"))
    assert stored["queue_seconds"] == 2.0
    assert build_record["job_id"] == "28001"
