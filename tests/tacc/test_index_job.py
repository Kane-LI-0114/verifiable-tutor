"""The embedding-index request and result seam.

Seam: ``build_index_request``, ``read_npy`` and ``vectors_by_chunk``. They catch
a request that drops or duplicates a chunk, a row map that does not line up with
the vectors, and a vector matrix in the wrong dtype or shape; they do not catch
an embedding that is numerically poor.
"""

import importlib.util
import json
import struct
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

ROWS = [
    {
        "chunk_id": "ACS_Lecture_0_2026F:p001:c00",
        "doc_id": "ACS_Lecture_0_2026F",
        "page_no": 1,
        "text": "Lecture zero page one",
    },
    {
        "chunk_id": "ACS_Lecture_0_2026F:p002:c00",
        "doc_id": "ACS_Lecture_0_2026F",
        "page_no": 2,
        "text": "Lecture zero page two",
    },
]


def load_driver():
    path = REPO_ROOT / "scripts" / "tacc" / "run_index_job.py"
    spec = importlib.util.spec_from_file_location("run_index_job", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_npy(path: Path, rows: list[list[float]]) -> Path:
    """Write a C-order float32 .npy file with one row per row of ``rows``."""

    dimension = len(rows[0])
    header = "{'descr': '<f4', 'fortran_order': False, 'shape': (%d, %d), }" % (
        len(rows),
        dimension,
    )
    padding = 16 - (10 + len(header) + 1) % 16
    header_bytes = (header + " " * padding + "\n").encode("latin1")
    with path.open("wb") as handle:
        handle.write(b"\x93NUMPY\x01\x00")
        handle.write(struct.pack("<H", len(header_bytes)))
        handle.write(header_bytes)
        for row in rows:
            handle.write(struct.pack("<%df" % dimension, *row))
    return path


def make_row_map(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "".join(
            json.dumps(
                {
                    "row": index,
                    "chunk_id": row["chunk_id"],
                    "doc_id": row["doc_id"],
                    "page_no": row["page_no"],
                }
            )
            + "\n"
            for index, row in enumerate(rows)
        ),
        encoding="utf-8",
    )
    return path


def test_the_index_request_covers_every_chunk_once(tmp_path: Path) -> None:
    driver = load_driver()

    request = driver.build_index_request(
        batch_id="index-20261105-01",
        rows=ROWS,
        userdir="/mnt/home/lijinchuan/USERDIR",
        model_config={
            "model": "BAAI/bge-m3",
            "model_path": "~/models/bge-m3",
            "dimension": 1024,
            "batch_size": 16,
            "max_length": 512,
            "device": "cuda",
        },
    )

    assert request["schema"] == "vt-index-request/1"
    assert request["input_path"].endswith(
        "/USERDIR/index/requests/index-20261105-01/input.jsonl"
    )
    assert request["out_dir"].endswith("/USERDIR/index/results/index-20261105-01")
    assert request["model"] == "BAAI/bge-m3"
    assert request["dimension"] == 1024

    input_path = tmp_path / "input.jsonl"
    driver.write_index_input(ROWS, input_path)
    lines = [json.loads(line) for line in input_path.read_text().splitlines() if line]
    assert [line["chunk_id"] for line in lines] == [row["chunk_id"] for row in ROWS]
    assert len({line["chunk_id"] for line in lines}) == 2


def test_the_index_request_refuses_a_duplicate_chunk(tmp_path: Path) -> None:
    driver = load_driver()

    with pytest.raises(ValueError, match="duplicate"):
        driver.build_index_request(
            batch_id="index-20261105-01",
            rows=[ROWS[0], dict(ROWS[0])],
            userdir="/mnt/home/lijinchuan/USERDIR",
            model_config={"model": "BAAI/bge-m3", "dimension": 1024},
        )


def test_the_index_request_refuses_an_empty_batch() -> None:
    driver = load_driver()

    with pytest.raises(ValueError, match="chunk"):
        driver.build_index_request(
            batch_id="index-20261105-01",
            rows=[],
            userdir="/mnt/home/lijinchuan/USERDIR",
            model_config={"model": "BAAI/bge-m3", "dimension": 1024},
        )


def test_the_row_map_and_the_vectors_agree(tmp_path: Path) -> None:
    driver = load_driver()
    npy_path = write_npy(tmp_path / "vectors.npy", [[0.5, 0.25], [0.125, 0.0625]])
    row_map = make_row_map(tmp_path / "row_map.jsonl", ROWS)
    loaded_rows = [
        json.loads(line) for line in row_map.read_text().splitlines() if line
    ]

    matrix = driver.read_npy(npy_path)
    vectors = driver.vectors_by_chunk(loaded_rows, matrix)

    assert matrix["rows"] == 2
    assert matrix["dimension"] == 2
    assert sorted(vectors) == [row["chunk_id"] for row in ROWS]
    assert len(vectors[ROWS[0]["chunk_id"]]) == 2 * 4
    assert struct.unpack("<2f", vectors[ROWS[0]["chunk_id"]]) == (0.5, 0.25)
    assert struct.unpack("<2f", vectors[ROWS[1]["chunk_id"]]) == (0.125, 0.0625)


def test_a_row_map_with_a_foreign_chunk_is_rejected(tmp_path: Path) -> None:
    driver = load_driver()
    npy_path = write_npy(tmp_path / "vectors.npy", [[0.5, 0.25], [0.125, 0.0625]])
    row_map = [
        {"row": 0, "chunk_id": ROWS[0]["chunk_id"], "doc_id": ROWS[0]["doc_id"]},
        {"row": 1, "chunk_id": "not-a-chunk", "doc_id": "unknown"},
    ]

    issues = driver.validate_index_result(
        ROWS, row_map, driver.read_npy(npy_path)
    )

    assert any("not-a-chunk" in issue for issue in issues)


def test_a_short_vector_matrix_is_rejected(tmp_path: Path) -> None:
    driver = load_driver()
    npy_path = write_npy(tmp_path / "vectors.npy", [[0.5, 0.25]])
    row_map = [
        {"row": 0, "chunk_id": ROWS[0]["chunk_id"], "doc_id": ROWS[0]["doc_id"]},
        {"row": 1, "chunk_id": ROWS[1]["chunk_id"], "doc_id": ROWS[1]["doc_id"]},
    ]

    issues = driver.validate_index_result(ROWS, row_map, driver.read_npy(npy_path))

    assert any("row" in issue for issue in issues)


def test_the_uploaded_input_name_is_the_name_the_worker_reads() -> None:
    """Seam: the USERDIR root filename. tcloud upload keeps the local basename
    and cannot create nested directories, so the driver must upload a file whose
    name the worker looks for when it moves the input into place."""

    driver = load_driver()
    worker = load_worker()

    uploaded = driver.index_input_upload_name("index-20261105-01")
    request = {
        "schema": "vt-index-request/1",
        "batch_id": "index-20261105-01",
        "input_path": "/mnt/home/lijinchuan/USERDIR/index/requests/index-20261105-01/input.jsonl",
    }
    candidates = [
        Path(path).name
        for path in worker.input_candidates(
            request,
            Path("/mnt/home/lijinchuan/USERDIR"),
            Path("/tmp/task/request.json"),
        )
    ]

    assert uploaded in candidates


def load_worker():
    path = REPO_ROOT / "tacc" / "index" / "index_worker.py"
    spec = importlib.util.spec_from_file_location("index_worker", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
