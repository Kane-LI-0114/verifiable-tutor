# The best chunking strategy: experiment report

Chinese version: [REPORT.zh.md](REPORT.zh.md)

## Work overview

This task answers one question: **which chunking strategy is best for RAG over the course slides.** The corpus is 13 documents and 365 pages exported from lecture slides. The system answers student questions and cites the exact page, so the retrieval unit is a chunk and the evaluation unit is a page.

The current production rule is `page_first_450`: a page at or below 450 estimated tokens is one chunk; a longer page is split by title and block; tables, formulas, and images are never split. The experiment checks whether it is the best choice and whether a more aggressive rule is worth adopting.

We ran three experiments. The first compares nine chunking cells and answers "which strategy is best". The second changes only the RRF lexical/dense weights and asks whether fusion tuning can add what chunking cannot. The third builds a dual-granularity index, with page chunks for BM25 and 128-token subchunks for dense retrieval, and asks whether each arm can use its preferred granularity. All three use the same 65 questions (14 dev, 51 test), the same BGE-M3 + BM25 + RRF stack, and the same page-level metrics.

The conclusion comes first: **the current production rule `page_first_450` is the best overall choice.** It is statistically tied with `page_only` on hybrid quality, but it uses 122 fewer tokens for the first five pages, reduces the BGE truncation rate from 12.33% to 10.99%, keeps one chunk per page for citation, and needs no extra model or tuning. The reason is the corpus: the course material is a set of lecture slides exported to PDF, and a slide usually stays on one topic. Of 365 pages, 354 are already one chunk at 450 tokens; the median cosine similarity between adjacent blocks inside a page is 0.509, against 0.387 across a page boundary. The page itself is the natural semantic unit. Splitting it further usually destroys a complete slide context rather than adding useful information, so the gain is small. Dual granularity can improve the score slightly, but the gain is not significant and the cost is clearly higher, so it is not worth adopting now.

## Experiment 1: nine chunking cells

Purpose: compare `page_only`, `page_first` at 128/256/450, `recursive` at 128/256/450, `semantic_450`, and `cross_page_450`, and find which one puts the correct page first at the lowest cost.

Design: each cell gets its own index and retrieves the same 65 questions. The primary metric is page-level nDCG@5 on hybrid retrieval; we also report hit@3, hit@5, top-five-page token cost, and the real BGE truncation rate. Comparisons are paired by question, with a 2000-sample bootstrap 95% confidence interval and an exact McNemar test for hit rates. Everything except the chunking rule is fixed: BGE-M3, FTS5 BM25, RRF `k=60`, 30 candidates per arm, and the raw question text.

The overall result on the 51 test questions:

| Cell | nDCG@5 | tokens@5 | BGE truncation (>512) |
|---|---:|---:|---:|
| `page_only` | 0.8512 | 1059 | 12.33% |
| `page_first_128` | 0.8405 | 586 | 1.57% |
| `page_first_256` | 0.8384 | 760 | 4.66% |
| `page_first_450` | 0.8487 | 937 | 10.99% |
| `recursive_128` | 0.8130 | 596 | 1.66% |
| `recursive_256` | 0.8488 | 811 | 5.62% |
| `recursive_450` | 0.8562 | 1008 | 10.79% |
| `semantic_450` | 0.8562 | 1008 | 10.76% |
| `cross_page_450` | 0.8368 | 944 | 16.26% |

`recursive_450` and `semantic_450` look highest, but they are only 0.005 above `page_only`: 1 win, 49 ties, and 1 loss over 51 questions, with a confidence interval of [-0.0077, 0.0228] that crosses zero. Every other cell also has an interval that crosses zero. No chunking rule significantly beats `page_only`. `page_first_450` is almost identical to `page_only` (50 of 51 questions have the same page rank; only q058 drops from second to third), but it uses 122 fewer tokens and truncates 1.34 points less.

The most informative result is the ablation. The lexical arm prefers large chunks: `page_first_450` scores 0.7786, while `page_first_128` scores 0.7270. The dense arm prefers small chunks: `page_first_128` scores 0.8941, `page_only` 0.8323, and `recursive_128` 0.8747. Dense `page_first_128` is +0.0618 over baseline, 9 wins and 3 losses, with 454 fewer tokens, but its interval [-0.0031, 0.1353] just touches zero, so it is not significant. Hybrid retrieval ties because the lexical preference for large chunks cancels the dense preference for small chunks.

Page length shows the same pattern. On short pages `page_only` scores 0.921 and smaller chunks drop to 0.902; on long pages `page_only` scores 0.824, `recursive_450` 0.844, and `cross_page` 0.857. Splitting gains a little on long pages and loses a little on short pages, so the average is a wash. In this corpus 354 of 365 pages are already one chunk at 450 tokens, and only 11 long pages are split. The headroom for a global chunking change is therefore small.

Semantic chunking does not win. The dev split selected threshold 0.25, producing 381 chunks, almost the same as `recursive_450` at 380; the test metrics are identical. Threshold 0.30 also scores 0.8562, and 0.35 drops to 0.8393. Semantic chunking also needs 3469 block embeddings and threshold tuning, so its extra cost is not repaid. `cross_page` scores 0.8368 with 16.26% truncation, the worst cell; it is a rough boundary stress test, not a production candidate.

Conclusion of Experiment 1: **no chunking rule significantly beats `page_only`; `page_first_450` is statistically tied but cheaper, truncates less, and keeps one chunk per page for citation; `page_first_256` is the cost-first alternative; the high scores of `recursive_450` and `semantic_450` are noise; `cross_page` is not suitable for production.**

## Experiment 2: RRF weights

Purpose: Experiment 1 showed that lexical retrieval prefers large chunks and dense retrieval prefers small chunks. A cheap question is whether changing only the RRF weights can bring the dense gain into the hybrid path.

Design: use the three strongest distinct hybrid cells, `recursive_450`, `page_only`, and `page_first_450`; `semantic_450` is excluded because it duplicates `recursive_450`. We tried dense:lexical weights 1:1, 2:1, and 1:2. Everything else is fixed.

| Cell | 1:1 | dense 2:1 | lexical 2:1 |
|---|---:|---:|---:|
| `recursive_450` | 0.8562 | 0.8302 | 0.8412 |
| `page_only` | 0.8512 | 0.8302 | 0.8218 |
| `page_first_450` | 0.8487 | 0.8302 | 0.8337 |

Every adjustment is worse than 1:1. The only interval that excludes zero is `page_only` at lexical 2:1, but it is -0.0295, a significant loss. All three 2:1 rows collapse to 0.8302 because these cells are page-level and have almost identical dense-only scores; when the dense weight dominates, the fused result becomes the same dense ranking.

Conclusion of Experiment 2: **on the current page-level cells, 1:1 is already best; weight tuning is not an improvement path.**

## Experiment 3: dual-granularity index

Purpose: since lexical retrieval prefers page chunks and dense retrieval prefers 128-token subchunks, let each arm use its preferred granularity and fuse at the page level.

Design: the lexical arm uses `page_first_450` page chunks; the dense arm uses `page_first_128` subchunks. Both rankings are expanded to pages and deduplicated, then fused with page-level RRF at `k=60`. The model receives the full page text, so token cost is counted per page. We ran 1:1 and dense 2:1.

| System | nDCG@5 | hit@3 | hit@5 | page tokens@5 |
|---|---:|---:|---:|---:|
| `page_first_450` hybrid | 0.8487 | 0.882 | 0.882 | 1147.9 |
| `page_first_128` dense only | 0.8941 | 0.941 | 0.980 | 1141.5 |
| dual 1:1 | 0.8567 | 0.863 | 0.902 | 1144.8 |
| dual dense 2:1 | 0.8596 | 0.902 | 0.941 | 1136.5 |

Dual 1:1 is +0.0081 over baseline, interval [-0.0059, 0.0305], 2 wins and 1 loss; dual dense 2:1 is +0.0110, interval [-0.0333, 0.0595], 5 wins and 4 losses. Both intervals cross zero, so neither is significant. But dense 2:1 raises hit@3 from 0.863 to 0.902 and hit@5 from 0.902 to 0.941, while tokens drop slightly to 1136.5. It is the only setting that moves toward the dense arm without an obvious loss.

It is still below dense-only 0.8941, which means page-level fusion still loses part of the dense signal. The extra cost is offline: 1020 chunks (382 page + 638 subchunk) need vectors, about 2.7 times `page_first_450`; online tokens are slightly higher because the model receives the full page.

Conclusion of Experiment 3: **dual granularity can improve the score slightly, especially hit@3 and hit@5, but the nDCG gain is not significant and the cost is clearly higher. It may be an optimization direction, but the cost-benefit ratio is too low to adopt now.**

## Conclusion: the best strategy

Taken together, the answer is clear: **the current production rule `page_first_450` is the best overall chunking strategy.** It is not the highest nDCG, but it is the only option that satisfies four things at once: quality statistically tied with `page_only`, 122 fewer tokens for the first five pages, truncation reduced from 12.33% to 10.99%, and one chunk per page for citation, with no extra model or tuning cost. The 0.8562 of `recursive_450` and `semantic_450` is noise; semantic chunking also needs an extra block-embedding pass and threshold tuning. `cross_page` and weight tuning are not worth adopting.

This conclusion also has a corpus-level explanation. The course material is a set of lecture slides exported to PDF. A slide is usually organized around one topic, with its title, bullets, and figures on the same page, so the page itself is already a concentrated semantic unit. The data supports this: 354 of 365 pages are one chunk at 450 tokens, and only 11 pages are split; adjacent blocks within a page have a median cosine similarity of 0.509, against 0.387 across a page boundary. Splitting further usually destroys a complete slide context rather than adding semantic information. The production rule, keep the page whole and split only when it exceeds the budget, therefore matches the structure of this corpus, and more aggressive chunking has little headroom.

Cost comparison:

| Method | Offline index | Online tokens@5 | Complexity | Verdict |
|---|---|---:|---|---|
| `page_first_450` | 382 chunk vectors | 937 | low, already in production | recommended |
| `page_first_256` | 451 chunk vectors | 760 | low | cost-first alternative |
| `page_first_128` | 638 chunk vectors | 586 | low | cheapest, but more per-question variance |
| `recursive_450` | 380 chunk vectors | 1008 | low | high score, not significant |
| `semantic_450` | 381 chunks + 3469 block vectors | 1008 | high | not recommended |
| `cross_page_450` | 289 chunk vectors | 944 | medium, multi-page mapping | not recommended |
| dual dense 2:1 | 1020 chunk vectors | 1136.5 | medium-high, two indexes | small, non-significant gain; not adopted |

If higher quality is needed later, the question set could be expanded to about 100 questions and dual granularity re-evaluated; at the current cost-benefit ratio it is not worth investing in now. More budget sweeps over a single chunking rule have very low expected return.

In one sentence: **the page is the natural retrieval unit on this corpus, chunking is not the bottleneck, `page_first_450` is the best current choice, `page_first_256` is the cost-first alternative, and dual granularity may improve slightly but does not justify its cost.**
