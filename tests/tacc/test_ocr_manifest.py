"""The OCR batch-request seam.

Seam: ``build_ocr_request`` plus the corpus batch table. It catches a request
that misses a PDF, parses one twice, or asks for a job that cannot finish in the
platform's one-hour cap; it does not catch a PDF whose page count differs from
the recorded one, because the job enumerates pages itself.
"""

import json
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_driver():
    import importlib.util

    path = REPO_ROOT / "scripts" / "tacc" / "run_ocr_job.py"
    spec = importlib.util.spec_from_file_location("run_ocr_job", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_the_ocr_manifest_covers_every_pdf_once() -> None:
    driver = load_driver()

    parsed: list[tuple[str, str]] = []
    for batch in ("lectures", "tutorials", "misc"):
        documents = driver.batch_documents(batch)
        parsed.extend((document["doc_id"], document["pdf"]) for document in documents)

    assert [doc_id for batch in ("lectures", "tutorials", "misc") for doc_id in
            [document["doc_id"] for document in driver.batch_documents(batch)]] == [
        "ACS_Lecture_0_2026F",
        "ACS_Lecture_1_2026F",
        "ACS_lecture_2_2026F",
        "ACS_Lecture_3_2026F",
        "ACS_Lecture_4_2026F",
        "ACS_Lecture_5_2026F",
        "Tutorial_1",
        "Tutorial_2",
        "Tutorial_3",
        "Tutorial_4",
        "Tutorial_5",
        "Tutorial_6",
        "TACC_Toturial",
        "Assignment_1_final",
        "Assignment_2",
    ]
    assert len({doc_id for doc_id, _pdf in parsed}) == len(parsed) == 15
    assert all(pdf.endswith(".pdf") for _doc_id, pdf in parsed)


def test_each_batch_fits_the_recorded_page_budget() -> None:
    driver = load_driver()

    pages = {
        batch: sum(document["expected_pages"] for document in driver.batch_documents(batch))
        for batch in ("lectures", "tutorials", "misc")
    }
    # Lecture pages 11 + 67 + 69 + 89 + 71 + 68, tutorial pages
    # 16 + 25 + 28 + 40 + 33 + 23 + 34, assignment pages 6 + 5, all counted from
    # the course PDFs.
    assert pages == {"lectures": 375, "tutorials": 199, "misc": 11}
    assert sum(pages.values()) + 8 == 593  # plus the already parsed course_project.pdf


def test_the_ocr_request_carries_the_ocr_cap_and_the_body_deadline() -> None:
    driver = load_driver()
    documents = driver.batch_documents("lectures")

    request = driver.build_ocr_request(
        batch_id="ocr-20261105-01",
        batch="lectures",
        documents=documents,
        userdir="/mnt/home/lijinchuan/USERDIR",
    )

    assert request["schema"] == "vt-ocr-request/1"
    assert request["batch_id"] == "ocr-20261105-01"
    assert request["ocr_stage_seconds"] == 1800
    assert request["body_deadline_seconds"] == 3300
    assert request["dpi"] == 200
    assert request["out_dir"].endswith("/USERDIR/ocr/ocr-20261105-01")
    assert [document["doc_id"] for document in request["documents"]] == [
        "ACS_Lecture_0_2026F",
        "ACS_Lecture_1_2026F",
        "ACS_lecture_2_2026F",
        "ACS_Lecture_3_2026F",
        "ACS_Lecture_4_2026F",
        "ACS_Lecture_5_2026F",
    ]


def test_the_ocr_request_and_job_config_stay_inside_the_hour() -> None:
    driver = load_driver()

    tuxiv = (driver.JOB_TEMPLATE / "tuxiv.conf").read_text(encoding="utf-8")

    assert "time=00:59:00" in tuxiv
    assert "gres=gpu:1" in tuxiv


def test_the_job_summary_records_which_documents_finished() -> None:
    driver = load_driver()
    summary = {
        "schema": "vt-ocr-batch/1",
        "batch_id": "ocr-20261105-01",
        "job_id": "28200",
        "documents": [
            {
                "doc_id": "ACS_Lecture_0_2026F",
                "status": "done",
                "pages": 11,
                "pages_ok": 11,
                "seconds": 96,
                "log_path": "logs/ACS_Lecture_0_2026F-28200.log",
            },
            {
                "doc_id": "ACS_Lecture_1_2026F",
                "status": "skipped",
                "pages": 0,
                "pages_ok": 0,
                "seconds": 0,
                "error": "deadline exceeded",
                "log_path": "logs/ACS_Lecture_1_2026F-28200.log",
            },
        ],
    }

    documents = driver.parse_job_summary(summary)

    assert documents["ACS_Lecture_0_2026F"]["status"] == "done"
    assert documents["ACS_Lecture_0_2026F"]["log_path"].endswith(
        "ACS_Lecture_0_2026F-28200.log"
    )
    assert documents["ACS_Lecture_1_2026F"]["status"] == "skipped"
    assert "deadline" in documents["ACS_Lecture_1_2026F"]["error"]


def test_the_page_archive_extracts_one_image_per_page(tmp_path: Path) -> None:
    driver = load_driver()
    source = tmp_path / "images"
    source.mkdir()
    (source / "ACS_Lecture_0_2026F.p001.webp").write_bytes(b"webp-1")
    (source / "ACS_Lecture_0_2026F.p002.webp").write_bytes(b"webp-2")
    archive = tmp_path / "images.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(source, arcname="images")

    extracted = driver.extract_page_images(archive, tmp_path / "out")

    assert sorted(path.name for path in extracted) == [
        "ACS_Lecture_0_2026F.p001.webp",
        "ACS_Lecture_0_2026F.p002.webp",
    ]
    assert (tmp_path / "out" / "ACS_Lecture_0_2026F.p001.webp").read_bytes() == b"webp-1"


def test_a_resumed_run_drops_the_documents_that_already_finished() -> None:
    driver = load_driver()
    documents = driver.batch_documents("lectures")
    state = {
        "ACS_Lecture_0_2026F": {"ocr": {"status": "done"}},
        "ACS_Lecture_1_2026F": {"ocr": {"status": "failed"}},
    }

    remaining = driver.documents_to_ocr(documents, state, resume=True, force=False)

    assert [document["doc_id"] for document in remaining] == [
        "ACS_Lecture_1_2026F",
        "ACS_lecture_2_2026F",
        "ACS_Lecture_3_2026F",
        "ACS_Lecture_4_2026F",
        "ACS_Lecture_5_2026F",
    ]


def test_the_staged_task_tree_holds_every_script_the_job_runs(tmp_path: Path) -> None:
    """Seam: the driver preflight before submit. The job re-reads its scripts a
    second time after vLLM is ready, so a file lost by the WORKDIR sync or by a
    typo fails the whole GPU job; this catches it locally."""

    import shutil
    import subprocess

    driver = load_driver()
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    for name in ("job.sh", "ocr_batch.py", "tuxiv.conf"):
        shutil.copyfile(driver.JOB_TEMPLATE / name, task_dir / name)
    (task_dir / "request.json").write_text("{}", encoding="utf-8")
    staging = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts" / "tacc" / "submit.sh"),
            str(task_dir),
            "--no-submit",
        ],
        capture_output=True,
        text=True,
    )
    assert staging.returncode == 0, staging.stderr

    staged = driver.preflight_task_dir(task_dir)
    assert any(path.endswith("ocr_batch.py") for path in staged)
    assert any(path.endswith("_staged/ocr_pages.py") for path in staged)

    (task_dir / "ocr_batch.py").unlink()
    with pytest.raises(SystemExit, match="ocr_batch.py"):
        driver.preflight_task_dir(task_dir)


def test_a_partial_manifest_records_the_documents_that_finished() -> None:
    """Seam: the job writes manifest.json after every document, summary.json
    only at the end. A job cancelled by the hour cap still leaves the finished
    documents resumable, so the driver must read the manifest too."""

    driver = load_driver()
    manifest = {
        "schema": "vt-ocr-manifest/1",
        "batch_id": "ocr-tutorials-20261105-01",
        "job_id": "28202",
        "documents": [
            {
                "doc_id": "Tutorial_3",
                "status": "done",
                "pages": 28,
                "pages_ok": 28,
                "seconds": 410.2,
                "log_path": "logs/Tutorial_3-28202.log",
            }
        ],
    }

    documents = driver.parse_job_summary(manifest)

    assert documents["Tutorial_3"]["status"] == "done"
    assert documents["Tutorial_3"]["pages_ok"] == 28


def test_the_ocr_stage_stops_after_the_recognition_budget() -> None:
    """Seam: the job's OCR-stage budget. It caps the summed recognition time at
    1800 s while render and assembly stay inside the 3300 s body deadline; it
    does not cap a single page's latency."""

    import importlib.util

    path = REPO_ROOT / "tacc" / "ocr" / "ocr_batch.py"
    spec = importlib.util.spec_from_file_location("ocr_batch", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.ocr_stage_exhausted(1799.0, 1800) is False
    assert module.ocr_stage_exhausted(1800.0, 1800) is True
    assert module.ocr_stage_exhausted(1800.1, 1800) is True


def test_a_slow_download_is_retried_and_a_partial_file_is_not_trusted(
    tmp_path: Path, monkeypatch
) -> None:
    """Seam: the TACC download boundary. A gateway timeout must not kill the
    driver, and a truncated file left by a killed transfer must not be reported
    as the artifact."""

    import subprocess

    driver = load_driver()
    target = tmp_path / "images.tar.gz"
    target.write_bytes(b"partial")
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(command, kwargs.get("timeout") or 0)

        class Completed:
            returncode = 0
            stdout = ""
            stderr = ""

        target.write_bytes(b"complete")
        return Completed()

    monkeypatch.setattr(driver, "run", fake_run)

    assert driver.download_artifact("ocr/x/images.tar.gz", target) is True
    assert target.read_bytes() == b"complete"
    assert len(calls) == 2
