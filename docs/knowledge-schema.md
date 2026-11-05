# Knowledge-base record schema

Status: draft, version 0.2, 2026-11-05; the record and progress contracts were validated in spike 10 on 2026-11-02 (job 28067, eight page-level chunks, 8 of 8 records valid). Version 0.2 adds the document-summary request and record used to fill the file AI summary in the knowledge-base browser ([ADR-0015](adr/0015-local-knowledge-store-and-chunking.md)). Owner: LI Jinchuan. This document owns the record contract for the Qwen knowledge-base build ([ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)). The requirements are in [prd.md](prd.md) FR-K1 to FR-K4; the job topology is in [tech-selection.md](tech-selection.md).

## 1. Scope

The knowledge base is built by one submitted TACC Qwen job per document shard. The local backend writes a request manifest and input JSONL into `USERDIR`, submits the job, polls it, downloads the result JSONL and progress file, validates them, and stores the records locally.

The contract has five objects:

| Object | Version | Writer | Reader |
|---|---|---|---|
| Build request | `vt-kb-request/1` | Local backend | TACC Qwen job |
| Build progress | `vt-kb-progress/1` | TACC Qwen job | Local backend |
| Knowledge record | `vt-kb-record/1` | TACC Qwen job | Local backend, knowledge-base UI, agent tools |
| Summary request | `vt-summary-request/1` | Local backend | TACC Qwen job |
| Document summary | `vt-doc-summary/1` | TACC Qwen job | Local backend, knowledge-base browser |

## 2. Storage layout

On TACC (`USERDIR`):

```
kb/
  requests/<build_id>/request.json      # one vt-kb-request/1 object
  requests/<build_id>/input.jsonl       # one source chunk per line
  results/<build_id>/records.jsonl      # one vt-kb-record/1 object per line
  results/<build_id>/progress.json      # one vt-kb-progress/1 object
  results/<build_id>/summary.json       # job timings and counts for NFR-12 evidence
```

Locally:

```
data/kb/
  records/<build_id>.jsonl              # downloaded, validated copy
  builds.sqlite                         # or the shared SQLite database
```

The local SQLite tables are `kb_builds` (one row per build) and `knowledge_cards` (one row per record, plus an FTS5 index for search). The JSONL artifact is the canonical record; the tables are a query index.

## 3. `vt-kb-request/1`

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema` | string | yes | `vt-kb-request/1` |
| `build_id` | string | yes | Stable id, for example `kb-20261101-01` |
| `shard_id` | string | yes | Document or section shard covered by this job |
| `doc_ids` | array of string | yes | Source course documents in this shard |
| `input_path` | string | yes | `USERDIR` path of the input JSONL |
| `record_path` | string | yes | `USERDIR` path where the result JSONL must be written |
| `progress_path` | string | yes | `USERDIR` path where progress must be written |
| `prompt_version` | string | yes | Prompt template version, for example `kb-v1` |
| `model` | string | yes | Model id, for example `qwen3.8-27b` |
| `params` | object | yes | Decoding and batching parameters (temperature, max output tokens, chunk count) |
| `corpus_hash` | string | yes | Hash of the source corpus used to build the shard |
| `created_at` | string | yes | ISO 8601 timestamp |

The input JSONL has one source chunk per line with `chunk_id`, `doc_id`, `page_no`, `section`, `source_block_ids`, and `text`. The chunk contract is in [corpus-schema.md](corpus-schema.md).

## 4. `vt-kb-record/1`

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema` | string | yes | `vt-kb-record/1` |
| `build_id` | string | yes | Build that produced this record |
| `job_id` | string | yes | TACC job id |
| `chunk_id` | string | yes | Source chunk |
| `doc_id` | string | yes | Source document |
| `page_no` | integer | yes | Page number of the chunk |
| `section` | string or null | no | Section title when known |
| `source_block_ids` | array of string | yes | OCR block ids covered by the record |
| `summary` | string | yes | Two to four sentences grounded in the chunk text |
| `key_terms` | array of string | yes | Key concepts or terms, at most eight |
| `study_questions` | array of string | yes | Two to five study questions answerable from the chunk |
| `citations` | array of object | yes | Each object has `doc_id`, `page_no`, and `quote` |
| `model` | string | yes | Model id |
| `prompt_version` | string | yes | Prompt template version |
| `corpus_hash` | string | yes | Corpus hash of the build |
| `created_at` | string | yes | ISO 8601 timestamp |

Every `citations[].quote` must occur on the cited page after whitespace and case normalization; the local validator applies the same rule as the span verifier ([ADR-0004](adr/0004-hybrid-retrieval-with-bge-m3.md)). A record with no valid citation is rejected.

## 5. `vt-kb-progress/1`

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema` | string | yes | `vt-kb-progress/1` |
| `build_id` | string | yes | Build id |
| `job_id` | string | yes | TACC job id |
| `status` | string | yes | `running`, `done`, or `failed` |
| `done_chunks` | integer | yes | Chunks completed so far |
| `total_chunks` | integer | yes | Total chunks in the shard |
| `error` | string or null | no | Short failure reason when `status` is `failed` |
| `updated_at` | string | yes | ISO 8601 timestamp |

## 6. `vt-summary-request/1` and `vt-doc-summary/1`

The document summary is the file-level AI summary the knowledge-base browser shows. One job covers the whole corpus: the request lists every document once, and the job loads Qwen once and writes one summary per document.

### `vt-summary-request/1`

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema` | string | yes | `vt-summary-request/1` |
| `build_id` | string | yes | Request id, for example `sum-20261105-01` |
| `input_path` | string | yes | `USERDIR` path of the input JSONL |
| `record_path` | string | yes | `USERDIR` path where the summaries JSONL must be written |
| `progress_path` | string | yes | `USERDIR` path where progress must be written |
| `prompt_version` | string | yes | Prompt template version, for example `doc-summary-v1` |
| `model` | string | yes | Model id, for example `qwen3.8-27b` |
| `params` | object | yes | Decoding parameters (`temperature`, `max_output_tokens`) |
| `corpus_hash` | string | yes | Hash of the whole corpus used for the request |
| `created_at` | string | yes | ISO 8601 timestamp |

Each input line carries `doc_id`, `pdf_sha256`, `page_count`, `outline` (the `paragraph_title` blocks of the document in page order, one line each, `p<page>: <title>`) and `excerpt` (the text of the first two pages). The outline is what lets Qwen summarise a 69-page deck without reading all of it.

### `vt-doc-summary/1`

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema` | string | yes | `vt-doc-summary/1` |
| `build_id` | string | yes | Request that produced the record |
| `job_id` | string | yes | TACC job id |
| `doc_id` | string | yes | Source document |
| `summary` | string | yes | Three to five sentences describing what the document covers |
| `topics` | array of string | yes | Three to eight short topic labels |
| `page_count` | integer | yes | Page count the summary was written against |
| `model` | string | yes | Model id |
| `prompt_version` | string | yes | Prompt template version |
| `corpus_hash` | string | yes | Corpus hash of the request |
| `created_at` | string | yes | ISO 8601 timestamp |

A summary that is empty after trimming, or that names a document other than its `doc_id`, is rejected by the local validator and the document keeps `summary` NULL; the browser then shows that the summary has not been generated yet rather than displaying a wrong one.

## 7. Document status

The local store tracks one status per document ([ADR-0015](adr/0015-local-knowledge-store-and-chunking.md)). `uploading`, `uploaded` and `upload_failed` are reserved for the upload chain that does not exist yet; ingestion writes `processing` while a job runs and `ready` when the document has chunks and vectors, or `failed` with a reason in the status detail.

| Status | Meaning |
|---|---|
| `uploading` | Upload in progress (reserved, no endpoint yet) |
| `uploaded` | Upload accepted, waiting for parsing (reserved) |
| `upload_failed` | Upload failed (reserved) |
| `processing` | Parsing, chunking, or embedding in progress |
| `ready` | Chunks and vectors exist; the document is searchable |
| `failed` | A stage failed; the reason is in the status detail |

## 8. Validation and failure handling

- The local backend validates every record against this schema before storing it. A malformed record is counted as a failure; the job may attempt one repair pass on malformed JSON before writing the failed record.
- A build is retried at the shard level when the job fails, times out, or returns an incomplete record set. Completed shards are not rebuilt.
- A build cache key is `(corpus_hash, prompt_version, model)`. An unchanged key reuses the stored records without submitting a new job.
- The knowledge base is read-only for students; only an instructor or TA account can trigger a build.
- Course text used for a build stays on the platform and TACC; it is not sent to an external model API.

## 9. Related documents

- Requirements and acceptance: [prd.md](prd.md), FR-K1 to FR-K4 and section 8
- Job topology and demo: [tech-selection.md](tech-selection.md)
- Build decision: [ADR-0011](adr/0011-tacc-as-required-model-serving-backend.md)
- Local store, chunking, and status: [ADR-0015](adr/0015-local-knowledge-store-and-chunking.md)
- Source chunk fields: [corpus-schema.md](corpus-schema.md)
- Physical tables: [physical-data-model.md](physical-data-model.md)
- Job settings: [../config/knowledge.yaml](../config/knowledge.yaml)
