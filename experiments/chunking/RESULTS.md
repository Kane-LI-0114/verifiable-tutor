# Results

Data and conclusions for the chunking experiments. The task report is
[REPORT.md](REPORT.md) (English) or [REPORT.zh.md](REPORT.zh.md) (Chinese); the
runbook is [README.md](README.md).

## Setup

13 documents, 365 pages, 65 questions (14 dev, 51 test). Main matrix: nine
chunking cells. Retrieval: BGE-M3 dense plus SQLite FTS5 BM25, reciprocal rank
fusion `k=60`, 30 candidates per arm, page-level deduplication. Primary metric:
page-level nDCG@5 on hybrid retrieval. Paired bootstrap 2000 samples, 95% CI;
McNemar for hit rates. Query rewrite is frozen to the identity plan.

## Chunk statistics

| Cell | Chunks | Mean est. tokens | Median | Max | Oversize | Multi-page | BGE mean | BGE >512 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `page_only` | 365 | 147.1 | 98 | 1211 | 8 | 0 | 213.7 | 12.33% |
| `page_first_128` | 638 | 83.8 | 81 | 512 | 48 | 0 | 123.1 | 1.57% |
| `page_first_256` | 451 | 118.9 | 98 | 512 | 9 | 0 | 173.3 | 4.66% |
| `page_first_450` | 382 | 140.5 | 101 | 512 | 2 | 0 | 204.3 | 10.99% |
| `recursive_128` | 604 | 88.5 | 88 | 512 | 29 | 0 | 129.9 | 1.66% |
| `recursive_256` | 427 | 125.6 | 103 | 512 | 7 | 0 | 182.9 | 5.62% |
| `recursive_450` | 380 | 141.2 | 99 | 512 | 2 | 0 | 205.3 | 10.79% |
| `semantic_450` | 381 | 140.9 | 99 | 512 | 2 | 0 | 204.8 | 10.76% |
| `cross_page_450` | 289 | 186.0 | 155 | 512 | 2 | 53 | 269.3 | 16.26% |

354 of 365 pages are one chunk at 450 tokens; only 11 pages are split. 237 pages
are at or below 128 tokens, 83 are 129 to 256, 34 are 257 to 450, and 11 are
above 450.

## Main experiment: hybrid, test split

| Cell | nDCG@5 (95% CI) | hit@3 | hit@5 | MRR | tokens@5 |
|---|---:|---:|---:|---:|---:|
| `page_only` | 0.8512 [0.7562, 0.9330] | 0.882 | 0.882 | 0.845 | 1059 |
| `page_first_128` | 0.8405 [0.7563, 0.9160] | 0.882 | 0.922 | 0.824 | 586 |
| `page_first_256` | 0.8384 [0.7463, 0.9197] | 0.882 | 0.902 | 0.826 | 760 |
| `page_first_450` | 0.8487 [0.7532, 0.9314] | 0.882 | 0.882 | 0.842 | 937 |
| `recursive_128` | 0.8130 [0.7188, 0.8949] | 0.824 | 0.902 | 0.799 | 596 |
| `recursive_256` | 0.8488 [0.7580, 0.9272] | 0.882 | 0.902 | 0.840 | 811 |
| `recursive_450` | 0.8562 [0.7677, 0.9343] | 0.882 | 0.902 | 0.842 | 1008 |
| `semantic_450` | 0.8562 [0.7677, 0.9343] | 0.882 | 0.902 | 0.842 | 1008 |
| `cross_page_450` | 0.8368 [0.7463, 0.9143] | 0.902 | 0.902 | 0.821 | 944 |

## Paired comparison against `page_only`, hybrid

| Cell | ΔnDCG@5 (95% CI) | W/T/L | McNemar p (hit@5) | Δtokens@5 |
|---|---:|---:|---:|---:|
| `page_first_128` | -0.0107 [-0.0546, 0.0312] | 3/44/4 | 0.5000 | -473 |
| `page_first_256` | -0.0128 [-0.0516, 0.0235] | 3/44/4 | 1.0000 | -299 |
| `page_first_450` | -0.0026 [-0.0077, 0.0000] | 0/50/1 | 1.0000 | -122 |
| `recursive_128` | -0.0382 [-0.0983, 0.0122] | 3/42/6 | 1.0000 | -464 |
| `recursive_256` | -0.0025 [-0.0347, 0.0299] | 2/46/3 | 1.0000 | -249 |
| `recursive_450` | +0.0050 [-0.0077, 0.0228] | 1/49/1 | 1.0000 | -51 |
| `semantic_450` | +0.0050 [-0.0077, 0.0228] | 1/49/1 | 1.0000 | -51 |
| `cross_page_450` | -0.0145 [-0.0563, 0.0247] | 1/47/3 | 1.0000 | -116 |

All intervals cross zero. No chunking cell significantly beats `page_only`.

## Ablation: lexical and dense

nDCG@5 on the test split.

| Cell | Lexical | Dense | Hybrid |
|---|---:|---:|---:|
| `page_only` | 0.7531 | 0.8323 | 0.8512 |
| `page_first_128` | 0.7270 | 0.8941 | 0.8405 |
| `page_first_256` | 0.7215 | 0.8486 | 0.8384 |
| `page_first_450` | 0.7786 | 0.8319 | 0.8487 |
| `recursive_128` | 0.7309 | 0.8747 | 0.8130 |
| `recursive_256` | 0.7588 | 0.8560 | 0.8488 |
| `recursive_450` | 0.7702 | 0.8323 | 0.8562 |
| `semantic_450` | 0.7688 | 0.8323 | 0.8562 |
| `cross_page_450` | 0.7803 | 0.8342 | 0.8368 |

Dense-only paired comparisons against `page_only`: `page_first_128` +0.0618
[-0.0031, 0.1353], 9/39/3, -454 tokens; `recursive_128` +0.0424 [-0.0292,
0.1196], 9/38/4, -449 tokens; `recursive_256` +0.0237 [-0.0139, 0.0733],
3/47/1. The intervals touch or cross zero, but the direction is consistent:
dense retrieval prefers smaller chunks.

## Category and page-length breakdown, hybrid

| Category | `page_only` | `page_first_128` | `page_first_256` | `page_first_450` | `recursive_450` | `cross_page_450` |
|---|---:|---:|---:|---:|---:|---:|
| assignment | 0.909 | 0.887 | 0.876 | 0.909 | 0.909 | 0.909 |
| concept | 0.912 | 0.912 | 0.919 | 0.912 | 0.912 | 0.861 |
| mechanism | 0.875 | 0.829 | 0.829 | 0.875 | 0.875 | 0.812 |
| table | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| tutorial | 0.628 | 0.634 | 0.624 | 0.617 | 0.652 | 0.686 |

| Stratum | `page_only` | `page_first_128` | `page_first_256` | `page_first_450` | `recursive_450` | `cross_page_450` |
|---|---:|---:|---:|---:|---:|---:|
| short | 0.921 | 0.902 | 0.909 | 0.921 | 0.921 | 0.875 |
| medium | 0.789 | 0.828 | 0.779 | 0.779 | 0.779 | 0.751 |
| long | 0.824 | 0.788 | 0.809 | 0.824 | 0.844 | 0.857 |

Table questions are saturated at 1.0 for every cell. Tutorial questions are the
hardest and the most variable. Splitting helps the long stratum slightly and
hurts the short stratum; the average is a wash.

## Semantic calibration

| Threshold | Chunks | Mean est. tokens | Dev nDCG@5 | Test nDCG@5 | Test hit@5 | Test tokens@5 |
|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 381 | 140.9 | 0.8682 | 0.8562 | 0.902 | 1008 |
| 0.30 | 452 | 118.7 | 0.8588 | 0.8562 | 0.902 | 974 |
| 0.35 | 630 | 85.1 | 0.8445 | 0.8393 | 0.8824 | 903 |

At 0.25 the semantic chunks are nearly identical to `recursive_450`; at 0.35
the score drops. Semantic grouping has no winning setting on this corpus and
adds 3469 block embeddings plus threshold tuning.

## RRF weight sweep

Three strongest distinct cells. Weights are written as dense:lexical.

| Cell | 1:1 | 2:1 | 1:2 |
|---|---:|---:|---:|
| `recursive_450` | 0.8562 | 0.8302 | 0.8412 |
| `page_only` | 0.8512 | 0.8302 | 0.8218 |
| `page_first_450` | 0.8487 | 0.8302 | 0.8337 |

Every adjustment is worse than 1:1. The only interval excluding zero is
`page_only` at 1:2, a loss of 0.0295 [-0.0584, -0.0072]. The 2:1 rows all
collapse to 0.8302 because these cells are page-level and have nearly identical
dense-only scores.

## Dual-granularity index

Lexical uses `page_first_450` pages; dense uses `page_first_128` subchunks;
both are expanded to pages and fused with page-level RRF.

| System | nDCG@5 (95% CI) | hit@3 | hit@5 | page tokens@5 |
|---|---:|---:|---:|---:|
| `page_first_450` hybrid | 0.8487 [0.7532, 0.9314] | 0.882 | 0.882 | 1147.9 |
| `page_first_128` dense only | 0.8941 [0.8280, 0.9525] | 0.941 | 0.980 | 1141.5 |
| dual 1:1 | 0.8567 [0.7652, 0.9340] | 0.863 | 0.902 | 1144.8 |
| dual dense 2:1 | 0.8596 [0.7819, 0.9293] | 0.902 | 0.941 | 1136.5 |

Dual 1:1 is +0.0081 over `page_first_450` [-0.0059, 0.0305], 2/48/1. Dual dense
2:1 is +0.0110 [-0.0333, 0.0595], 5/42/4; versus dual 1:1 it is +0.0029
[-0.0374, 0.0447], 5/43/3. Neither nDCG interval excludes zero. The dense 2:1
variant raises hit@3 from 0.882 to 0.902 and hit@5 from 0.882 to 0.941, which is
the first setting that moves toward the dense arm without an obvious loss. It
remains below dense-only 0.8941.

## Conclusions

`page_first_450` is the best overall production choice. It is statistically tied
with `page_only`, but uses 122 fewer tokens, truncates less, keeps one chunk per
page for citation, and adds no extra model or tuning cost. `page_first_256` is
the cost-first alternative: 760 tokens, 4.66% truncation, and a non-significant
nDCG loss. `page_first_128` is the cheapest and has the strongest dense-only
score, but its hybrid result is not better and it has 48 oversize chunks.

The corpus explains why page-level chunking is enough. The course material is a
set of lecture slides exported to PDF. A slide is usually organized around one
topic, with its title, bullets, and figures on the same page, so the page is
already a concentrated semantic unit. In this corpus 354 of 365 pages are one
chunk at 450 tokens, and only 11 pages are split. Adjacent blocks within a page
have a median cosine similarity of 0.509, against 0.387 across a page boundary.
Splitting further usually destroys a complete slide context rather than adding
semantic information. This is why the production rule, keep the page whole and
split only when it exceeds the budget, matches the corpus.

`recursive_450` and `semantic_450` are nominally highest at 0.8562, but the gain
over `page_only` is 1 win, 49 ties, and 1 loss. `semantic` also costs an extra
3469 block embeddings and threshold tuning. `cross_page_450` is not a production
candidate: 0.8368 and 16.26% truncation.

RRF weight tuning does not help: 1:1 is best. Dual granularity is the only
promising direction: dense 2:1 reaches 0.8596 and improves hit@3/hit@5, but the
nDCG interval still crosses zero and the score is below dense-only 0.8941. It
needs more questions before adoption.

Raw per-question rows are under `results/<run>/raw/` and are ignored by Git.
Curated summaries are under `results/full-01/`, `results/rrf-weights-01/`,
`results/dual-granularity-01/`, and `results/dual-dense2-01/`.
