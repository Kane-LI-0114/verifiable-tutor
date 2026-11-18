# Chunking strategy experiment: results and analysis

Run `full-01`, 2026-11-18. All artifacts are under `experiments/chunking/`.

## Executive summary

The experiment compared nine chunking configurations on the same 13-document,
365-page course corpus, the same 65 questions, and the same retrieval stack.
The primary metric is page-level nDCG@5 on hybrid retrieval.

1. **No strategy significantly beats `page_only` on the primary metric.** Every
   paired 95% confidence interval against `page_only` contains zero. The best
   hybrid score is `recursive_450` and `semantic_450` at 0.8562, against 0.8512
   for `page_only`; the difference is +0.0050, with 1 win, 49 ties, and 1 loss,
   and a McNemar p-value of 1.0.
2. **The current production rule, `page_first_450`, is statistically
   indistinguishable from `page_only`** (0.8487 versus 0.8512, one loss and 50
   ties), but it needs 122 fewer tokens to produce the first five pages and
   reduces the share of chunks truncated at 512 BGE tokens from 12.33% to
   10.99%. Keeping it is the safe decision.
3. **`page_first_256` is the best cost and truncation compromise.** It scores
   0.8384 (not significantly different), uses 760 tokens instead of 1059
   (-28%), and cuts truncation from 12.33% to 4.66%. `page_first_128` saves even
   more tokens (586, -45%) and truncates only 1.57%, but it creates 48 oversize
   chunks and shows more per-question variance.
4. **The dense arm prefers smaller chunks.** With dense retrieval alone,
   `page_first_128` reaches 0.8941 against 0.8323 for `page_only` (+0.0618,
   95% CI [-0.0031, 0.1353], 9 wins, 3 losses, 39 ties) while using 454 fewer
   tokens. The hybrid fusion dilutes this because the lexical arm prefers
   page-level chunks. This is the most promising follow-up, not a reason to
   change the default today.
5. **Cross-page merging does not help.** `cross_page_450` scores 0.8368 and
   truncates 16.26% of chunks, the worst of the nine cells. The page boundary
   is not the limiting factor on this corpus.
6. **The remaining failures are mostly query and OCR problems, not chunk
   boundaries.** Formula-heavy pages, near-duplicate pages, and overview pages
   that outrank the detail page fail under every strategy.
7. **Splitting only long pages does not help hybrid retrieval.** The naive
   version of that rule is exactly `recursive`; a genuine "keep medium pages,
   split only pages above 200 or 256 tokens" rule reduces truncation and helps
   dense retrieval, but lowers hybrid nDCG@5 and loses on the affected long-page
   questions. `page_first_450` and `recursive_256` already handle those pages
   best.

## What was held fixed

| Item | Value |
|---|---|
| Corpus | 13 documents, 365 pages, snapshot in `data/pages/` |
| Page records | `vt-page-record/1`, rebuilt from OCR blocks |
| Embedding model | `BAAI/bge-m3`, 1024 dimensions, CLS pooling, L2 normalised |
| Device | CPU, `max_length=512`, batch 16, 12 torch threads |
| Lexical arm | SQLite FTS5 `unicode61 remove_diacritics 2`, BM25 |
| Fusion | reciprocal rank fusion, `k=60`, weights 1:1, 30 candidates per arm |
| Query text | the question itself (`fallback_plan`); questions are English |
| Ranking | chunks expanded to pages, pages deduplicated, `k` measured in pages |
| k values | 3, 5, 10 |
| Questions | 65 total: 14 dev, 51 test |

The query rewrite was deliberately frozen to the identity plan. The questions
are English, so the lexical arm can search the English corpus without a model
call. This removes DeepSeek variance from the comparison; the production path
uses a rewrite, but the rewrite is identical for every cell and therefore
cannot explain a difference between cells.

## Environment

| Component | Version |
|---|---|
| Python | 3.12.7 |
| torch | 2.15.0+cpu |
| transformers | 5.22.1 |
| numpy | 2.5.4 |
| Platform | Windows 11 |
| Model files | `config.json`, `pytorch_model.bin` (2.27 GB), `tokenizer.json` |

The experiment virtual environment, model weights, page snapshot, indexes, and
vector cache all live under `experiments/chunking/`. No production file was
modified.

## Question set

`questions/retrieval_v1.jsonl` contains 65 questions written from the page
records, not from chunk output. Each question has one gold page, except q027,
which has two.

| View | Counts |
|---|---|
| Split | 14 dev, 51 test |
| Category | concept 21, mechanism 14, tutorial 13, assignment 11, table 6 |
| Page-length stratum | short 21, medium 16, long 28 |
| Gold pages per question | 1 page: 64 questions, 2 pages: 1 question |
| Gold page estimated tokens | min 44, median 239.5, mean 255.7, p90 446, max 713 |

The set over-samples long and table-heavy pages on purpose. Those are the pages
where chunk boundaries can change retrieval; a set dominated by one-chunk
slides would make every strategy tie by construction.

## Matrix and chunk statistics

| Cell | Strategy | Budget | Chunks | Mean est. tokens | Median | Max | Oversize | Multi-page |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `page_only` | one chunk per page | none | 365 | 147.1 | 98 | 1211 | 8 | 0 |
| `page_first_128` | production rules | 128 | 638 | 83.8 | 81 | 512 | 48 | 0 |
| `page_first_256` | production rules | 256 | 451 | 118.9 | 98 | 512 | 9 | 0 |
| `page_first_450` | production rules | 450 | 382 | 140.5 | 101 | 512 | 2 | 0 |
| `recursive_128` | recursive separators | 128 | 604 | 88.5 | 88 | 512 | 29 | 0 |
| `recursive_256` | recursive separators | 256 | 427 | 125.6 | 103 | 512 | 7 | 0 |
| `recursive_450` | recursive separators | 450 | 380 | 141.2 | 99 | 512 | 2 | 0 |
| `semantic_450` | adjacent-block similarity | 450 | 381 | 140.9 | 99 | 512 | 2 | 0 |
| `cross_page_450` | repeated page title | 450 | 289 | 186.0 | 155 | 512 | 2 | 53 |

The estimator is the production one: one token per CJK character and one token
per four other characters. The real BGE-M3 tokenizer is stricter, so the table
below is the one that matters for truncation.

| Cell | BGE mean | BGE median | BGE p90 | BGE max | Over 512 | Over 512 share |
|---|---:|---:|---:|---:|---:|---:|
| `page_only` | 213.7 | 109 | 560 | 1944 | 45 | 12.33% |
| `page_first_128` | 123.1 | 91 | 261 | 1271 | 10 | 1.57% |
| `page_first_256` | 173.3 | 110 | 389 | 1271 | 21 | 4.66% |
| `page_first_450` | 204.3 | 112 | 546 | 1271 | 42 | 10.99% |
| `recursive_128` | 129.9 | 102 | 237 | 1271 | 10 | 1.66% |
| `recursive_256` | 182.9 | 116 | 410 | 1271 | 24 | 5.62% |
| `recursive_450` | 205.3 | 112 | 546 | 1271 | 41 | 10.79% |
| `semantic_450` | 204.8 | 112 | 542 | 1271 | 41 | 10.76% |
| `cross_page_450` | 269.3 | 169 | 625 | 1271 | 47 | 16.26% |

The max column shows that a single protected block can exceed the budget under
every strategy. Under `page_first_128`, 48 chunks are marked oversize because
one block is larger than 128 tokens. The chunker refuses to split tables,
formulas, and images, so this is expected rather than a bug.

## Semantic threshold calibration

The threshold grid was chosen from the observed adjacent-block similarity
distribution: median 0.51, p25 0.43, p10 0.36. Thresholds above 0.4 fragment the
slides into hundreds of very small chunks, so the grid is 0.25, 0.30, and 0.35.
Selection used the 14 dev questions only; the test columns are reported for
sensitivity, not for selection.

| Threshold | Chunks | Mean est. tokens | Dev nDCG@5 | Test nDCG@5 | Test hit@5 | Test tokens@5 |
|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 381 | 140.9 | 0.8682 | 0.8562 | 0.902 | 1008 |
| 0.30 | 452 | 118.7 | 0.8588 | 0.8562 | 0.902 | 974 |
| 0.35 | 630 | 85.1 | 0.8445 | 0.8393 | 0.882 | 903 |

The dev split selected 0.25. At that threshold semantic grouping is almost the
same as page-level chunking: only 2.3% of adjacent block pairs fall below 0.25,
so most pages stay whole. The test result is correspondingly identical to
`recursive_450`: the two chunk sets differ by one chunk (381 versus 380), and
that chunk never enters the top five, so every reported metric is the same. The
0.30 threshold is the more interesting semantic setting:
it produces 452 chunks, the same test nDCG@5, and 34 fewer tokens. The 0.35
setting loses 0.017 nDCG. Semantic chunking is stable in the 0.25 to 0.30
range and does not produce a gain.

## Main results: hybrid retrieval, test split

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

All confidence intervals overlap heavily. The observed spread of 0.043 nDCG is
about one question's worth of score, not a stable ranking of strategies.

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

The only change under `page_first_450` is q058, where the gold page moves from
rank 2 to rank 3; every other question has the same page rank as `page_only`.
That is why the mean difference is small and the win/tie/loss row is almost all
ties. The production rule is not buying a retrieval gain on this corpus, but it
is buying a 12% token reduction and a small truncation reduction.

## Ablation: lexical and dense arms

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

The arms disagree. The lexical arm prefers page-level or large chunks:
`page_first_450` is 0.7786, `page_first_128` is 0.7270. The dense arm prefers
small chunks: `page_first_128` is 0.8941 against 0.8323 for `page_only`, and
`recursive_128` is 0.8747. The hybrid fusion sits between them and washes out
the dense gain.

Dense paired comparisons against `page_only`:

| Cell | ΔnDCG@5 (95% CI) | W/T/L | Δtokens@5 |
|---|---:|---:|---:|
| `page_first_128` | +0.0618 [-0.0031, 0.1353] | 9/39/3 | -454 |
| `recursive_128` | +0.0424 [-0.0292, 0.1196] | 9/38/4 | -449 |
| `page_first_256` | +0.0163 [-0.0490, 0.0824] | 4/44/3 | -306 |
| `recursive_256` | +0.0237 [-0.0139, 0.0733] | 3/47/1 | -278 |
| `page_first_450` | -0.0003 [-0.0228, 0.0217] | 1/49/1 | -109 |
| `recursive_450` | 0.0000 [0.0000, 0.0000] | 0/51/0 | -75 |
| `cross_page_450` | +0.0020 [-0.0374, 0.0413] | 3/45/3 | -126 |

The dense result is the strongest signal in the experiment, but its confidence
interval still touches zero because 51 questions are few. It is consistent with
the truncation table: smaller chunks reach more of the page within the 512-token
embedding window. It should be treated as a hypothesis for a follow-up, not as
a production switch.

## Category and page-length breakdown, hybrid

nDCG@5 on the test split.

| Category | page_only | page_first_128 | page_first_256 | page_first_450 | recursive_450 | cross_page_450 |
|---|---:|---:|---:|---:|---:|---:|
| assignment | 0.909 | 0.887 | 0.876 | 0.909 | 0.909 | 0.909 |
| concept | 0.912 | 0.912 | 0.919 | 0.912 | 0.912 | 0.861 |
| mechanism | 0.875 | 0.829 | 0.829 | 0.875 | 0.875 | 0.812 |
| table | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| tutorial | 0.628 | 0.634 | 0.624 | 0.617 | 0.652 | 0.686 |

| Stratum | page_only | page_first_128 | page_first_256 | page_first_450 | recursive_450 | cross_page_450 |
|---|---:|---:|---:|---:|---:|---:|
| short | 0.921 | 0.902 | 0.909 | 0.921 | 0.921 | 0.875 |
| medium | 0.789 | 0.828 | 0.779 | 0.779 | 0.779 | 0.751 |
| long | 0.824 | 0.788 | 0.809 | 0.824 | 0.844 | 0.857 |

The expected pattern appears weakly. Small chunks help some long tutorial pages
(`cross_page` and `recursive_450` reach 0.686 and 0.652 on tutorial questions)
but hurt short pages. The table category is saturated at 1.0 for every cell, so
the corpus does not discriminate table preservation; all strategies keep tables
whole. The tutorial category is the hardest and the most variable, which is why
the overall difference is small.

## Error analysis

The same failures recur across cells. They are not fixed by changing the
boundary.

| Question | Gold | What the retriever returns | Cause |
|---|---|---|---|
| q011 stable softmax | Tutorial_4 p23 | p30, p29, p24 | The definition page is formula-heavy; OCR text is noisy and the code pages share vocabulary. p23 appears only at rank 10 under `cross_page_450` and nowhere else in the top 10. |
| q025 attention score S_ij | Tutorial_3 p25 | p22, Tutorial_4 p39, p5 | p25 is a formula page. `recursive_450` and `cross_page` move p25 to rank 5 or 7, but no cell puts it first. |
| q042 prerequisites | Lecture_0 p5 | p6, p7, p11 | p6 is the adjacent "what this course does not do" page. Both pages are short and share course-policy vocabulary. |
| q054 vector-add host steps | Tutorial_3 p21 | p20, p28, p2 | p20 is the overview; p21 is the full code listing. The question matches the overview's prose better. |
| q062 submitted file name | Assignment_1 p5 | p1, Assignment_2 p1, p3 | p1 contains general submission notes; p5 contains the exact naming rule but is long and buried. p5 is rank 9 or 10. |
| q057 first `__syncthreads` | Tutorial_4 p19 | p14, p40, p16 | p14 contains the same code with a partial explanation. The chunk boundary cannot separate two near-identical code pages. |

Question-level deltas explain the aggregate. `page_first_128` gains on q027
and q055 (long tiled-GEMM pages) and loses on q046, q057, q061, and q063. The
gains and losses are both real, but they cancel. The corpus contains a small
number of genuinely multi-topic long pages, and many short pages where any
split only adds noise.

## Decision

The pre-registered rule was: adopt a cell only if the primary metric improves
with a confidence interval that excludes zero, hit@3 does not regress, and
context cost does not exceed twice the baseline. No cell meets the first
condition.

**Keep `page_first_450` as the production default.** It is statistically tied
with `page_only`, uses 122 fewer tokens for the first five pages, and truncates
slightly less. There is no evidence that any alternative rule is better on this
corpus.

**If context cost becomes the priority, use `page_first_256`.** It gives up
0.013 nDCG, which is not distinguishable from zero, saves 28% of the top-5
tokens, and cuts the truncation rate from 12.33% to 4.66%. `page_first_128` is
the aggressive version: 45% fewer tokens and 1.57% truncation, but 48 oversize
chunks and a more variable per-question result.

**Do not adopt `cross_page_450`.** It is the worst cell on truncation and does
not improve nDCG. The page boundary is not the limiting constraint.

**Do not adopt a long-page-only split as a hybrid change.** The follow-up in
`long-pages-01` shows that protecting medium pages and splitting only long ones
does not help the hybrid path; `page_first_450` and `recursive_256` are already
better on the affected pages. The dense gain from fine splits is a fusion
opportunity, not a chunking rule.

**Do not adopt `semantic_450` as configured.** At the dev-selected threshold it
converges to page-level chunks; at 0.30 it matches `recursive_450` while using
34 fewer tokens. Neither is a gain.

The most useful follow-up is not another chunk size. It is the retrieval
configuration that consumes the chunks:

1. The dense arm clearly prefers 128-token chunks. Tune the RRF weights, or use
   a dense-first path for concept and mechanism questions, and measure again.
2. Fix the query side for q054 and q062: the question wording matches an
   overview page, not the detail page. A rewrite or a reranker is the right
   lever, not a smaller chunk.
3. Improve the OCR of formula pages before judging q011 and q025. The gold
   content is there, but the text layer is weak.
4. Add a span-level check for the long pages, because page-level nDCG cannot
   see that the retrieved page's answer was in the truncated tail.

## Follow-up: splitting only long pages

The first follow-up idea was to keep short pages whole and apply the recursive
split only to long pages. A naive version of that rule is not a separate
strategy: `recursive` already keeps a page whole when it fits the budget, so a
cell that keeps pages up to the budget and splits the rest is exactly
`recursive`. The chunk counts confirm it: 604, 427, and 380 for the naive
"long recursive" cells, identical to `recursive_128`, `recursive_256`, and
`recursive_450`.

A genuine version of the idea protects medium pages from splitting and applies
a finer split only to pages above a keep threshold. The run `long-pages-01`
tested three such cells: `keep200_split128`, `keep256_split128`, and
`keep450_split128`. A page at or below the keep threshold stays whole; a longer
page is recursively split to 128 tokens. The affected page counts are 63, 45,
and 11, with 30, 19, and 5 test questions on those pages.

| Cell | Chunks | Affected pages | Test questions | Hybrid nDCG@5 | Dense nDCG@5 | tokens@5 | Over 512 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `page_first_450` | 382 | 11 | 5 | 0.8487 | 0.8319 | 937 | 10.99% |
| `recursive_256` | 427 | 45 | 19 | 0.8488 | 0.8560 | 811 | 5.62% |
| `keep200_split128` | 536 | 63 | 30 | 0.8251 | 0.8881 | 654 | 2.24% |
| `keep256_split128` | 508 | 45 | 19 | 0.8070 | 0.8745 | 694 | 3.15% |
| `keep450_split128` | 416 | 11 | 5 | 0.8316 | 0.8323 | 876 | 8.89% |

The hybrid result is worse than `page_first_450` in all three cells. On the
subset of questions whose gold page is actually above the keep threshold, the
same pattern holds: `keep200_split128` scores 0.761 against 0.793 for
`page_first_450` and 0.801 for `recursive_256`; `keep256_split128` scores 0.724
against 0.824 and 0.837; `keep450_split128` scores 0.800 against 1.000, but that
subset has only five questions. The paired difference against `page_first_450`
on the affected-page subset is -0.032 [-0.133, 0.054] for keep200, -0.099
[-0.249, 0.016] for keep256, and -0.200 [-0.600, 0.000] for keep450. None is a
gain.

The dense arm tells the opposite story: `keep200_split128` reaches 0.8881
against 0.8319 for `page_first_450`, and `keep256_split128` reaches 0.8745.
Fine splitting helps the embedding arm on long pages, but the lexical arm and
the hybrid fusion lose more than the dense arm gains. `page_first_450` and
`recursive_256` are already the best hybrid choices on the affected long pages,
so the "split only long pages" idea does not improve the production retrieval
path. It remains a possible part of a dense-first or multi-resolution index,
not a standalone chunking change.

## Threats to validity

- **Small test set.** 51 test questions give wide confidence intervals. The
  experiment can rule out large effects, not small ones.
- **One gold page per question.** 64 of 65 questions have a single gold page.
  Page-level nDCG rewards a long chunk that contains the page incidentally.
  The token-cost column and the `context_tokens@5` metric are the mitigation.
- **Page-level metric cannot see truncation inside a retrieved page.** A page
  can be retrieved while its answer was in the part of the chunk that BGE-M3
  truncated. The `over 512` table is a diagnostic, not part of the score.
- **English questions, identity query plan.** Production uses a DeepSeek
  rewrite. The rewrite is identical for every cell, so it cannot bias the
  relative comparison, but it may change the absolute scores.
- **Single corpus, single model, CPU only.** The result should not be
  generalised to other courses or to GPU embeddings without re-running.
- **Semantic threshold.** The dev split has 14 questions. The sensitivity table
  shows the semantic result is stable between 0.25 and 0.30 and weaker at 0.35;
  a larger dev set could move the selected point.
- **Estimator versus tokenizer.** The chunker uses a character-based estimate;
  the BGE tokenizer counts more tokens. Both are reported, and the decision
  uses retrieval metrics rather than the estimate.

## Reproduce

From the repository root, in PowerShell:

```powershell
python -m venv experiments/chunking/.venv
experiments/chunking/.venv/Scripts/python -m pip install -r requirements.txt

$env:HF_HOME = "D:\6000U\verifiable-tutor\experiments\chunking\models\.hf-cache"
experiments/chunking/.venv/Scripts/hf.exe download BAAI/bge-m3 `
  --local-dir experiments/chunking/models/bge-m3

$env:PYTHONPATH = "D:\6000U\verifiable-tutor\src;D:\6000U\verifiable-tutor\experiments\chunking"
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py validate
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/run_experiment.py run `
  --cells full --calibrate-semantic --run-id full-01
experiments/chunking/.venv/Scripts/python experiments/chunking/scripts/token_stats.py `
  experiments/chunking/results/full-01/summary.json
python experiments/chunking/scripts/report.py `
  experiments/chunking/results/full-01/summary.json
```

The vector cache is content addressed, so the second run only embeds chunk texts
that were not seen before. The page snapshot hash manifest is
`results/page_manifest.json`; the environment record is
`results/environment.json`. The question set, summary, raw per-question rows,
BGE token statistics, and semantic sensitivity table are all in this folder.
