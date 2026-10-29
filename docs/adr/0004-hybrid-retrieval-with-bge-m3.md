# ADR-0004: Hybrid retrieval with BGE-M3

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-28 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The proposal promises a hybrid index over BM25 and dense embeddings, with an ablation over BM25 only, dense only, and hybrid. The corpus is English course material; students may ask in Chinese or English, so cross-lingual query to document retrieval decides whether the system works for the team's own demos and for RQ1.

The scale is small: 342 pages, an estimated 3,000 to 6,000 chunks. A vector database is unnecessary. The public environment already ships PyTorch 2.11 and Transformers 5.10.4 but no `faiss`, `rank_bm25`, or `sentence-transformers`, and the project layer may add a small pinned delta only (ADR-0001). Embedding computation must fit batch windows inside one-hour jobs, and query embedding must run in the CPU backend at request time.

The embedding model must be multilingual with at least Chinese and English, and must fit the RTX 3090 hardware with headroom.

## Decision

We build the index in two arms and fuse them with reciprocal rank fusion.

- **BM25:** SQLite FTS5 through the Python standard library, which provides a real BM25 ranking without an extra package.
- **Dense:** BGE-M3 (568M parameters, 1024 dimensions, 8192 tokens, MIT, about 2.27 GB fp32 or 1.14 GB fp16). Dense vectors are computed once in a GPU batch job with Transformers, cached as a NumPy array, and searched exactly with one matrix multiplication.
- **Fusion:** reciprocal rank fusion, with configurable weights and top-k. Reranking is optional and only added after the evaluation shows it pays.
- **Cross-lingual handling:** for a Chinese query, the Qwen service produces one English query variant, cached by query hash, and the BM25 arm runs on that variant. The dense arm runs on the original query.

The index build job lives in `tacc/index/` and skips work when the corpus hash, model hash, and index parameters match the cached artifacts. Query embeddings are cached by query hash so the 50-question benchmark and demos do not repeat them.

The primary model is BGE-M3. The fallbacks are Qwen3-Embedding-0.6B as a drop-in alternative and Qwen3-Embedding-4B as an upgrade path, both evaluated only if the bake-off on course questions shows a gap.

## Consequences

**Positive:**
- Cross-lingual retrieval works in both directions with one local model.
- One forward pass yields dense, sparse, and multi-vector signals, so later improvements do not require a new model.
- No vector database, no FAISS, and no external API; the index is a NumPy array plus a SQLite table.
- The model runs on CPU for query embedding and on GPU for batch embedding, which suits both the backend job and the batch window.

**Negative:**
- Two retrieval artifacts must stay in sync; a corpus or model change forces an index rebuild.
- Query embedding on CPU adds about one second per uncached query (estimate, to measure in the spike).
- The translation step adds one model call for Chinese queries, which affects RQ4 cost accounting.
- BGE-M3's sparse and ColBERT outputs are unused in the first version, so their benefit is left on the table until the ablation says otherwise.
- The model imposes a 1024-dimension index and an 8192-token chunk ceiling, which constrains long pages.

**Neutral:**
- The index is generated, ignored by Git, and staged from `USERDIR`.

## Alternatives considered

**Qwen3-Embedding-0.6B as primary.** For: better MTEB v1 and C-MTEB averages, 32k context, instruction-aware, Apache-2.0, slightly smaller. Against: an independent Chinese to English benchmark measured it about 0.011 nDCG below BGE-M3, and its MTEB advantage does not transfer to this query direction. Why not chosen: the direction this project exercises is the cross-lingual one; kept as the first fallback.

**BM25 only.** For: no model, no GPU job, fastest to build. Against: Chinese queries carry no English terms, so BM25 alone cannot serve the bilingual requirement, and the proposal promises a dense ablation arm. Why not chosen: it drops a research question.

**External embedding API.** For: no local model and no GPU window. Against: the course does not reimburse costs, results are not reproducible offline, and the primary path must not depend on an external key. Why not chosen: violates the cost and reproducibility rules in [../tacc-notes.md](../tacc-notes.md).

**Qwen3-Embedding-4B as primary.** For: the best Chinese to English numbers in the candidate set. Against: 8.04 GB of weights, several times the embedding time, and no measured need before evaluation. Why not chosen: premature cost; kept as the upgrade path.

## References

- BGE-M3 model card: https://huggingface.co/BAAI/bge-m3
- Qwen3-Embedding model card: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- Independent Chinese to English retrieval benchmark, published 2026-10-28: https://github.com/gregorytsai/zh-en-retrieval-benchmark
- Public environment package list: course workspace `tacc-env-docs/requirements-installed.txt`, outside this repository
- Verification items: [../tech-selection.md](../tech-selection.md#verification-spikes)
