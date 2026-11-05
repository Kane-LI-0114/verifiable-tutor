# ADR-0015: Local knowledge store, page-first chunking, and the deferred citation and injection stages

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-05 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The knowledge base needs a browsable, searchable home for the course corpus. Today the only stored knowledge artifact is the Qwen card JSONL under `data/kb/records/`, read by `CardStore` at request time. There is no document table, no chunk table, no full-text index, and no vector store; `src/verifiable_tutor/evidence/` is an empty package and `data/index/` holds only `.gitkeep`.

The corpus is 12 PDFs and 342 pages, already scoped in [tech-selection.md](../tech-selection.md#corpus-and-ocr-pipeline). The browser UI needs folders, files, per-file metadata, and a page-accurate preview. The future retrieval tool needs chunks with page and box provenance, a lexical arm, and a dense arm fused by reciprocal rank fusion ([ADR-0004](0004-hybrid-retrieval-with-bge-m3.md)).

Two product constraints shape the record shapes. First, every future citation must point at a page the reader can open, so chunks may not cross pages. Second, the course PDFs include dense lecture slides whose text exceeds the embedding model's 512-token window, so a pure page-level chunker silently truncates content and makes the tail of a slide unreachable.

## Decision

**One local SQLite store owns the corpus.** Five additive tables in `storage.py` (`SCHEMA_VERSION` 2): `kb_folders`, `kb_documents`, `kb_chunks`, the FTS5 external-content table `kb_chunks_fts`, and the single-row `kb_index_state`. Uploads, folders, and files that the browser shows are rows in this store, not files on disk that the UI walks.

**Documents are flat until a user organizes them.** Ingestion writes every document with `folder_id` NULL. Folders are created by the user from the `+` menu and may nest; `folder_id` is a self-referencing foreign key with `ON DELETE CASCADE`, and the application deletes a folder's mirror files and chunks before deleting the rows.

**Chunking is page-first, split only when over budget.** A chunk never spans pages. Text is rebuilt from `blocks`, not from `page.text`, so headers and footers are dropped and table and formula content stays inline. A page at or under 450 estimated tokens becomes one chunk; a longer page splits at `paragraph_title` boundaries, then at the largest inter-block gap, keeping `table`, `display_formula`, and `image` blocks whole. A single block above 500 tokens becomes its own chunk marked `oversize`. The estimate is `characters / 4` for English and one character per token for Chinese, so no tokenizer dependency is introduced. Each chunk carries `block_ids` and the union `bbox_norm` so a future citation can highlight the source boxes.

**Vectors live in SQLite.** `kb_chunks.embedding` stores a `float32` BLOB (1024 dimensions for BGE-M3). The retriever materializes the matrix from those rows and caches it in process, keyed by `kb_index_state` (`chunks`, `dimension`, `model`, `chunker_version`, `built_at`). There is no separate NumPy file and row map to drift from the rows; ADR-0004's "NumPy array plus row map" is satisfied by materializing that array at load.

**Bulk vectors are computed on TACC; query vectors are computed locally.** `tacc/index/` embeds chunks with BGE-M3 on the platform and returns `vectors.npy` plus a row map, and the local backend materializes the same matrix for queries with a local BGE-M3 CPU encoder configured in `config/models.yaml`. This keeps the embedding index a required platform job ([ADR-0011](0011-tacc-as-required-model-serving-backend.md)) while interactive query embedding stays local. A missing local encoder degrades retrieval to the lexical arm and says so in the response.

**The lexical arm uses FTS5 `unicode61`.** The corpus is English; Chinese queries reach BM25 through the English query variant the rewrite step produces, and the dense arm serves the original Chinese string. A trigram tokenizer is the documented fallback if mixed-script content proves it necessary.

**Document summaries come from Qwen on the platform.** A second request schema (`vt-summary-request/1`) runs in the existing `tacc/serve` job and emits one `vt-doc-summary/1` record per document. Course text used for the summary does not leave the platform.

**Citation construction and model injection are out of scope for this stage.** Chunks, hits, and their metadata are produced and served; turning a hit into a stored citation, verifying its span, and injecting top-k chunks into the chat prompt are recorded as TODO in the code and in [prd.md](../prd.md). The retrieval entry point exists so the next stage can call it without changing the store.

## Deferred: chunking strategy evaluation

The page-first rules above are the first implementation, not a settled answer. An offline optimization pass still has to choose the chunking strategy against the retrieval benchmark, because the four known strategies trade recall, coherence, and cost differently:

| Strategy | Shape | Why it is still on the table |
|---|---|---|
| Fixed token window | split every page by a token budget, optionally with overlap | cheapest and most uniform, but cuts tables and formulas and ignores slide structure |
| Recursive | split on the largest separator that fits, then recurse into the pieces | structure-aware without needing layout labels, and cheap to add |
| Structure-aware | use the `paragraph_title`, `table`, `display_formula`, and `image` labels as the boundaries | what the current rules approximate; a real section builder that merges the slides under one title is still missing |
| Semantic | group adjacent blocks while their embeddings stay close | the best topic purity, but it needs an embedding pass at ingestion and its own evaluation |

The evaluation seam is the retrieval question set with known answer pages: report page-hit@k and nDCG for each strategy on the same corpus, then keep the winner. `chunker_version` stays in the chunk record and in the index key so a rule change forces a rebuild instead of mixing two chunk shapes in one store. TODO, not scheduled.

## Consequences

**Positive:**

- One store answers browsing, search, and retrieval, so there is no index-versus-database drift.
- Page-anchored chunks make every hit openable in the PDF preview, which is what the citation and evidence layers need next.
- The page-first rule keeps the natural retrieval unit (a slide) and still bounds every chunk under the embedding window.
- Document status is a first-class column, so the reserved upload states need no schema change when the upload chain lands.

**Negative:**

- A dense slide can still exceed the window when one block is oversized; the chunk is marked and the truncation rate must be observed in evaluation.
- Storing 1024-dimension BLOBs in SQLite trades a little load time for one authoritative store.
- Bulk embedding and query embedding run on different hardware and precision, so scores are close but not bit-identical.

**Neutral:**

- The existing page-level `knowledge/chunks.py` stays for the Qwen card job; the corpus chunker is a separate module with a different contract.
- The chunker version is part of the index key, so changing the rules forces a rebuild rather than silently mixing two chunk shapes.

## Alternatives considered

**One chunk per page.** Simplest and smallest, but dense lecture pages exceed the model window and are truncated without a trace, and a page holding two unrelated topics retrieves poorly for either.

**Section-level chunks merged across pages.** Produces fewer, more coherent chunks, but a chunk then spans pages, which breaks page anchoring for the preview highlight and for any future citation.

**Fixed windows with overlap.** Ignores slide structure, cuts tables and formulas in half, and duplicates content across chunks, which double-counts in reciprocal rank fusion.

**Vectors in a separate `.npy` plus row map, as written in ADR-0004.** Faster to load, but two artifacts must stay in sync with the rows, and the accepted requirement here is one store the UI and the retriever share. The matrix is still materialized as a NumPy array in memory.

## References

- Retrieval decision: [ADR-0004](0004-hybrid-retrieval-with-bge-m3.md)
- Platform model serving: [ADR-0011](0011-tacc-as-required-model-serving-backend.md)
- Page and chunk record fields: [../corpus-schema.md](../corpus-schema.md)
- Knowledge request, progress, record, and summary fields: [../knowledge-schema.md](../knowledge-schema.md)
- Physical schema, generated from `Storage`: [../physical-data-model.md](../physical-data-model.md)
- Embedding settings: [../../config/models.yaml](../../config/models.yaml)
