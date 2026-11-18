# Chunking experiment

Self-contained experiment for the course RAG chunking question. It imports
`verifiable_tutor` read only and writes its environment, model, data, indexes,
caches, and results under this folder. The task report is [REPORT.md](REPORT.md)
(English) or [REPORT.zh.md](REPORT.zh.md) (Chinese); the data and conclusions
are [RESULTS.md](RESULTS.md).

## Layout

| Path | Contents |
|---|---|
| `chunking_eval/metrics.py` | page expansion, hit, nDCG, MRR, context tokens |
| `chunking_eval/strategies.py` | chunking strategies |
| `chunking_eval/index.py` | evaluation-only SQLite store with FTS5 |
| `chunking_eval/retrieval.py` | lexical, dense, hybrid retrieval |
| `chunking_eval/runner.py` | cell build, evaluation, bootstrap, summary |
| `chunking_eval/dual.py` | page-level fusion for the dual-granularity experiment |
| `scripts/run_experiment.py` | main experiment entry point |
| `scripts/rrf_weights.py` | RRF weight sweep |
| `scripts/dual_granularity.py` | dual-granularity experiment |
| `scripts/report.py` | Markdown tables from a summary |
| `scripts/token_stats.py` | real BGE token length and truncation |
| `questions/retrieval_v1.jsonl` | 65 questions with gold pages |
| `data/pages/` | page snapshot copied from `data/corpus/pages/` |
| `data/index/` | per-cell SQLite indexes (ignored) |
| `data/cache/` | content-addressed BGE-M3 vectors (ignored) |
| `results/` | tracked summaries, ignored raw per-question rows |
| `tests/` | 30 unit tests |

## Environment

All commands run from the repository root, so `$PWD` is the checkout root on
any machine. The examples are PowerShell; on macOS or Linux replace
`.venv/Scripts/python` with `.venv/bin/python`, `hf.exe` with `hf`, `;` in
`PYTHONPATH` with `:`, and `$env:NAME = "value"` with `export NAME="value"`.

```powershell
python -m venv experiments/chunking/.venv
experiments/chunking/.venv/Scripts/python -m pip install -r requirements.txt

$env:HF_HOME = "$PWD/experiments/chunking/models/.hf-cache"
experiments/chunking/.venv/Scripts/hf.exe download BAAI/bge-m3 `
  --local-dir experiments/chunking/models/bge-m3
```

The page snapshot is already copied into `experiments/chunking/data/pages/`.
The model weights are about 2.3 GB and are ignored by Git.

## Run

```powershell
# both the project source and this folder are needed
$env:PYTHONPATH = "$PWD/src;$PWD/experiments/chunking"

# tests
experiments/chunking/.venv/Scripts/python -m pytest experiments/chunking/tests -q

# validate the question set
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py validate

# main matrix with semantic calibration
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py run `
  --cells full --calibrate-semantic --run-id full-01

# RRF weight sweep on the three strongest distinct cells
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/rrf_weights.py `
  --run-id rrf-weights-01

# dual-granularity index, 1:1 and dense 2:1
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/dual_granularity.py `
  --run-id dual-granularity-01
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/dual_granularity.py `
  --run-id dual-dense2-01 --weights 2:1
```

The vector cache at `experiments/chunking/data/cache/vectors.db` is content
addressed, so a rerun only embeds texts that have not been seen before. Delete
that file or change the model to invalidate the cache.

## Outputs

Each run writes `experiments/chunking/results/<run-id>/summary.json` and, for the
main matrix, `experiments/chunking/results/<run-id>/raw/<cell>.jsonl`. The raw
rows are ignored by Git; the summaries and the BGE token statistics are tracked.
`scripts/report.py` renders the Markdown tables from a summary:

```powershell
python experiments/chunking/scripts/report.py `
  experiments/chunking/results/full-01/summary.json
```

The experiment does not modify `src/`, `tests/`, `benchmarks/`, `scripts/`,
`config/`, or `data/`.
