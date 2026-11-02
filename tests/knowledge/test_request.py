from verifiable_tutor.knowledge.request import build_request, corpus_hash

USERDIR = "/mnt/home/student/USERDIR"
PARAMS = {
    "temperature": 0.0,
    "max_output_tokens": 1024,
    "chunk_count": 2,
    "max_repair_attempts": 1,
}
CHUNKS = [
    {
        "chunk_id": "course_project:p001:c00",
        "doc_id": "course_project",
        "page_no": 1,
        "section": "Course Project",
        "source_block_ids": ["0", "1"],
        "text": "Course Project\nBuilding an End-to-End Agent System",
    },
    {
        "chunk_id": "course_project:p003:c00",
        "doc_id": "course_project",
        "page_no": 3,
        "section": None,
        "source_block_ids": ["0"],
        "text": "Lecture notes about MPI",
    },
]


def make_request(**overrides):
    fields = {
        "build_id": "kb-20261102-01",
        "chunks": CHUNKS,
        "userdir": USERDIR,
        "prompt_version": "kb-v1",
        "model": "qwen3.8-27b",
        "params": PARAMS,
    }
    fields.update(overrides)
    return build_request(**fields)


def test_build_request_has_the_schema_and_userdir_paths() -> None:
    request = make_request()

    assert request["schema"] == "vt-kb-request/1"
    assert request["build_id"] == "kb-20261102-01"
    assert request["doc_ids"] == ["course_project"]
    base = f"{USERDIR}/kb/requests/kb-20261102-01"
    assert request["input_path"] == f"{base}/input.jsonl"
    assert request["record_path"] == f"{USERDIR}/kb/results/kb-20261102-01/records.jsonl"
    assert (
        request["progress_path"]
        == f"{USERDIR}/kb/results/kb-20261102-01/progress.json"
    )


def test_build_request_carries_the_model_and_prompt_version() -> None:
    request = make_request()

    assert request["model"] == "qwen3.8-27b"
    assert request["prompt_version"] == "kb-v1"
    assert request["params"] == PARAMS
    assert request["corpus_hash"] == corpus_hash(CHUNKS)


def test_build_request_derives_the_shard_id_from_the_pages() -> None:
    request = make_request()

    assert request["shard_id"] == "course_project-p001-p003"


def test_build_request_rejects_empty_chunks() -> None:
    try:
        make_request(chunks=[])
    except ValueError:
        return
    raise AssertionError("empty chunks must be rejected")


def test_corpus_hash_is_stable_for_equal_chunks() -> None:
    assert corpus_hash(CHUNKS) == corpus_hash([dict(chunk) for chunk in CHUNKS])


def test_corpus_hash_changes_when_text_changes() -> None:
    changed = [dict(chunk) for chunk in CHUNKS]
    changed[0]["text"] = "different text"

    assert corpus_hash(changed) != corpus_hash(CHUNKS)
