# Experiments

This directory contains experiments that import the application read only and
keep all of their own environments, models, data, results, and tests.

| Directory | Topic | Report |
|---|---|---|
| `chunking/` | Chunking strategies and hybrid retrieval on the course corpus | [REPORT.zh.md](chunking/REPORT.zh.md) (Chinese academic report), [RESULTS.md](chunking/RESULTS.md) (English detailed results) |

The experiments do not modify `src/`, `tests/`, `benchmarks/`, `scripts/`, or
`config/`. Each experiment lives in its own folder with a local `.gitignore`;
its virtual environment, model weights, temporary indexes, vector caches, and
raw per-question rows are ignored by Git.
