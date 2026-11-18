# Chunking strategy evaluation

This folder is a self-contained experiment. It imports `verifiable_tutor` read
only and writes every artifact here: the virtual environment, the BGE-M3
weights, the question set, the temporary indexes, the vector cache, the raw
per-question rows, and the summaries. No file under `src/`, `tests/`,
`benchmarks/`, `scripts/`, `config/`, or `data/` is modified.

## Question

Which chunking strategy and token budget make the correct course page easiest
to retrieve, at what context cost, on this corpus?

The production pipeline is hybrid retrieval: SQLite FTS5 BM25 plus BGE-M3 dense
vectors fused with reciprocal rank fusion. The experiment changes only the
chunk boundaries. The embedding model, the BM25 tokenizer, the RRF constant,
the number of candidates per arm, and the query text are fixed.

## Why the page is the evaluation unit

A chunk is the retrieval unit, but a citation opens a page. The ranked chunks
are therefore expanded into a ranked page list: each chunk contributes the
pages it covers, and a page keeps the rank of its first occurrence. This stops
a long chunk from winning merely because it carries more pages.

## Matrix

`page_only` is the baseline: one chunk per page, never split. It is the null
hypothesis "chunking is unnecessary". `page_first` is the production rule with
a configurable budget. `recursive` is a generic structure-free baseline that
splits at paragraph, sentence, word, and character boundaries. `semantic` uses
BGE-M3 cosine similarity between adjacent blocks. `cross_page` merges a repeated
section title across consecutive pages and is the only strategy that can cover
more than one page.

Fixed-token windows were deliberately excluded: they cut tables, formulas, and
sentences, and the corpus is a set of structured lecture slides, so the
comparison would mostly measure damage that is already known.

| Cell | Strategy | Budget | Role |
|---|---|---|---|
| `page_only` | one chunk per page | none | baseline |
| `page_first_128` | production rules | 128 | small budget |
| `page_first_256` | production rules | 256 | medium budget |
| `page_first_450` | production rules | 450 | current production |
| `recursive_128` | recursive separators | 128 | generic small |
| `recursive_256` | recursive separators | 256 | generic medium |
| `recursive_450` | recursive separators | 450 | generic large |
| `semantic_450` | adjacent-block similarity | 450 | topic purity |
| `cross_page_450` | repeated section merge | 450 | page-bound stress test |

The semantic threshold is selected on the dev split only, from
`0.25, 0.30, 0.35`, by dev hybrid nDCG@5. The adjacent-block similarity median
on this corpus is 0.51, so this grid spans roughly 380 to 630 chunks; higher
thresholds fragment the slides into very small pieces. The test split is then
run once with the selected threshold.

## Question set

`questions/retrieval_v1.jsonl` contains 65 English questions written from the
page records in `data/corpus/pages/`, not from any chunk output. Each question
carries its gold page or pages, a category, a page-length stratum, and a short
answer gist used for human review.

| Split | Questions |
|---|---|
| dev (`D`) | 14 |
| test (`T`) | 51 |

The strata are based on the total estimated tokens of the gold page: short is
under 128, medium is 128 to 249, and long is 250 or more. The set deliberately
over-samples long, table-heavy, and multi-topic pages, because those are the
pages where chunking can change the outcome.

`scripts/run_experiment.py validate` checks that every `doc_id` and `page_no`
exists in the page snapshot.

## Metrics

The primary metric is page-level `nDCG@5` on hybrid retrieval. Secondary metrics
are `hit@3`, `hit@5`, `MRR`, and `context_tokens@5`, the number of chunk tokens
needed to produce the first five distinct pages. Chunk count, mean tokens,
oversize count, and multi-page count are reported per cell.

Comparisons are paired by question against `page_only`. The report includes the
mean difference, a 2000-sample bootstrap 95% confidence interval, win/tie/loss
counts for nDCG, and an exact McNemar p-value for the hit rate.

## Environment

All commands are PowerShell from the repository root unless stated otherwise.

```powershell
python -m venv experiments/chunking/.venv
experiments/chunking/.venv/Scripts/python -m pip install -r requirements.txt

$env:HF_HOME = "D:\6000U\verifiable-tutor\experiments\chunking\models\.hf-cache"
experiments/chunking/.venv/Scripts/hf.exe download BAAI/bge-m3 `
  --local-dir experiments/chunking/models/bge-m3
```

The page snapshot is copied from `data/corpus/pages/` into `data/pages/`. The
JSONL files are the experiment input; the rest of the repository is not read at
run time.

## Run

```powershell
$env:PYTHONPATH = "D:\6000U\verifiable-tutor\src;D:\6000U\verifiable-tutor\experiments\chunking"

# tests
cd experiments/chunking
$env:PYTHONPATH = "D:\6000U\verifiable-tutor\src"
.venv/Scripts/python -m pytest tests -q
cd ../..

# validate the questions
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py validate

# pilot
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py run `
  --cells pilot --run-id pilot-01

# full matrix with semantic calibration
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py run `
  --cells full --calibrate-semantic --run-id full-01

# Markdown tables from a summary
python experiments/chunking/scripts/report.py `
  experiments/chunking/results/full-01/summary.json
```

The vector cache at `data/cache/vectors.db` is content addressed, so a rerun
only embeds chunk texts that have not been seen before.

## Layout

| Path | Contents |
|---|---|
| `chunking_eval/metrics.py` | page expansion, hit, nDCG, MRR, context tokens |
| `chunking_eval/strategies.py` | the six chunking implementations |
| `chunking_eval/index.py` | evaluation-only SQLite store with FTS5 |
| `chunking_eval/retrieval.py` | lexical, dense, and hybrid retrieval |
| `chunking_eval/runner.py` | cell build, evaluation, bootstrap, summary |
| `scripts/run_experiment.py` | validate, calibrate, run |
| `scripts/report.py` | Markdown tables from `summary.json` |
| `questions/retrieval_v1.jsonl` | 65 questions with gold pages |
| `data/pages/` | read-only page snapshot |
| `data/index/` | per-cell SQLite indexes |
| `data/cache/` | content-addressed BGE-M3 vectors |
| `results/<run>/summary.json` | metrics, cell configs, comparisons |
| `results/<run>/raw/` | per-question rows per cell |

## Results

The full report is in [RESULTS.md](RESULTS.md): configuration, chunk statistics,
BGE token truncation, semantic calibration, hybrid and ablation tables, paired
confidence intervals, category and page-length breakdowns, error analysis, and
the decision.

Run `scripts/report.py` on a new `summary.json` to regenerate the tables. Raw
per-question rows are written under `results/<run>/raw/` and are ignored by Git;
the curated `summary.json`, `bge_token_stats.json`, and
`semantic_sensitivity.json` are tracked. Run `scripts/failures.py` to inspect
one cell's failures from the raw rows.
