# Verifiable AI Tutoring on TACC

*A course-grounded agent with evidence-checked answers, executable practice labs, and enforced course policy*

Course project for CSIT6000V Advanced AI Computing and Systems (Fall 2026) by LI Jinchuan (21188271), TIAN Yujia (21201619), and XIE Yifeng (21322152). Instructor: Prof. Kai Chen.

| Item | Value |
|---|---|
| Repository | [https://github.com/Kane-LI-0114/verifiable-tutor](https://github.com/Kane-LI-0114/verifiable-tutor), public |
| Artifact form | source checkout with the tracked course corpus and TACC results; no VM image, no Docker |
| Reviewer account | `demo.student@ust.hk` / `vt-demo-2026`, seeded at startup and shown on the login page |
| First result | about 25 minutes, dominated by the dependency install and the 2.3 GB embedding weights |
| Test suite | `.venv/bin/python -m pytest`: 455 tests |

This README follows the two-section structure the NSDI '27 Call for Artifacts requires. [Getting Started Instructions](#getting-started-instructions) is the 30-minute kick-the-tires check: install, start, sign in with the seeded student account, and ask one question whose answer cites a page. [Detailed Instructions](#detailed-instructions) is the full evaluation: what each experiment measures, the data and commands that rerun it, the numbers to expect, and the known limitations. The project description, the architecture, and the directory layout follow those two sections.

## Getting Started Instructions

### Prerequisites

| Requirement | Version used | Needed for |
|---|---|---|
| macOS or Linux | macOS 15, Ubuntu 22.04 | everything; the commands below are POSIX |
| Python | 3.12 (developed on 3.12.13) | backend, tests, both experiments |
| Node.js and npm | 18 or later (developed on 25.9) | building the browser UI |
| Free disk | about 6 GB | 2.3 GB weights, about 2.5 GB virtual environment, 0.5 GB checkout |
| Network | PyPI and huggingface.co | installing dependencies and the weights |
| DeepSeek API key | any active key | live chat in the end-to-end example |
| TACC account and `tcloud` | optional | only to rerun the OCR, index, and Qwen jobs |

The repository ships the material the default path needs: 16 documents, 593 page records, 612 chunk vectors, and 16 document summaries under `data/corpus/`, `data/index/`, and `data/kb/`. A fresh checkout does not rerun OCR and does not submit a TACC job.

### 1. Clone and install

```bash
git clone https://github.com/Kane-LI-0114/verifiable-tutor.git
cd verifiable-tutor
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

`requirements.txt` is generated from `pyproject.toml` and `uv.lock` and pins every dependency to an exact version. The install pulls the embedding stack (torch and transformers, about 2 GB). If that stack is not wanted, replace the last two commands with `pip install -e '.[dev]'`; the backend then runs with the lexical retrieval arm only.

### 2. Configure secrets

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # paste this as SESSION_SECRET
```

Set `SESSION_SECRET` and `DEEPSEEK_API_KEY` in `.env`. `MIMO_API_KEY` enables the voice routes. The `SMTP_*` keys are only for registration email, which the reviewer account makes unnecessary. `LANGFUSE_*` is optional local tracing. `.env` is gitignored.

### 3. Download the query embedder

```bash
.venv/bin/hf download BAAI/bge-m3 --local-dir models/bge-m3
```

The weights are 2.3 GB and live inside the checkout, gitignored. Without them the backend still starts and retrieval reports `"dense": false`, so only the lexical arm answers, with coarser results.

### 4. Restore the course store

```bash
.venv/bin/python scripts/ingest_corpus.py import
.venv/bin/python scripts/ingest_corpus.py status
```

`import` rebuilds the chunks from the tracked page records, applies the tracked `vectors.npy` and `row_map.jsonl`, and writes the local SQLite store. `status` prints one row per document and ends with:

```
documents=16 pages=593 chunks=612 vectors=612 summaries=16 done=16 failed=0 ok=true
```

### 5. Start the backend

```bash
.venv/bin/fastapi dev --port 8000     # API only; interactive schema at /docs
# or, for the browser UI served on the same origin:
./start.sh
```

Startup also seeds the reviewer account. Expected tail:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 6. End-to-end example

Five requests check the whole path from storage to a cited answer. Run them from the repository root in a second terminal.

```bash
# a. liveness and store health
curl -s http://127.0.0.1:8000/api/health

# b. the reviewer account, exactly as the login page shows it
curl -s http://127.0.0.1:8000/api/auth/demo

# c. sign in; the session cookie goes to cookies.txt
curl -s -c cookies.txt -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"demo.student@ust.hk","password":"vt-demo-2026"}'

# d. hybrid retrieval over the course corpus
curl -s -b cookies.txt \
  'http://127.0.0.1:8000/api/knowledge/retrieve?q=What%20is%20the%20memory%20wall%3F&k=2'

# e. one streamed tutor turn
curl -s -N -b cookies.txt -X POST http://127.0.0.1:8000/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"According to Lecture 2, what is the memory wall? Cite the page."}'
```

Expected output, trimmed to the fields worth checking. Observed on 24 November 2026.

```text
# a
{"status":"ok","version":"0.1.0","database":"ok"}

# b
{"email":"demo.student@ust.hk","password":"vt-demo-2026"}

# c
{"user":{"id":"...","email":"demo.student@ust.hk","role":"student"}}

# d
{"query":"What is the memory wall?","need_retrieval":true,"lexical":true,"dense":true,
 "chunks":[{"chunk_id":"ACS_lecture_2_2026F:p011:c00","doc_id":"ACS_lecture_2_2026F",
            "page_no":11,"section":"Memory Wall","sources":["lexical","dense"]}, ...]}

# e, one server-sent event per line
data: {"type": "start", "messageId": "..."}
data: {"type": "data-step", "data": {"step": "retrieve", "status": "started", ...}}
data: {"type": "data-tool", "data": {"tool_name": "search_course", ...}}
data: {"type": "data-tool", "data": {"tool_name": "verify_span", ...}}
data: {"type": "text-delta", "delta": "## The Memory Wall (Lecture 2)"}
data: {"type": "data-sources", "data": {"sources": [{"doc_id": "ACS_lecture_2_2026F",
                                                     "page_no": 11, ...}]}}
data: {"type": "finish"}
```

Three checks tell you the system works:

- Retrieval answers with `"dense": true` and puts `ACS_lecture_2_2026F` page 11, the "Memory Wall" slide, in the first two chunks.
- The chat stream runs `search_course`, `read_course_page`, and `verify_span` tool frames before the answer text, so every quoted span was checked against its page.
- The final turn carries numbered sources. Our run produced 16, from 14 tool calls (six `search_course`, four `read_course_page`, four `verify_span`).

The browser path is the same backend. Open `http://127.0.0.1:8000/` after `./start.sh`, click **Use demo account** on the login page, and ask the same question in the composer. The answer streams with numbered citation chips that open the cited page image.

### 7. Run the tests

```bash
.venv/bin/python -m pytest                       # 455 tests, all pass
cd src/verifiable_tutor/ui/web
npm ci && npm run typecheck && npm run test
```

The Python suite is green: 455 passed in about two minutes on the development laptop. The Vitest suite passes 264 of 276 tests; the 12 failures are in `tests/practice-page.test.tsx` and `tests/chat-live.test.tsx` and predate this commit (see [Known limitations](#known-limitations-and-expected-variation)).

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `start.sh` exits asking for `SESSION_SECRET` | `.env` missing or empty | step 2 |
| Retrieval returns `"dense": false` | weights absent | step 3 |
| `Address already in use` | port 8000 busy | `--port 8001`, or `fastapi dev --port 8001` |
| Login returns 401 with the hint account | backend started before the account existed | restart the backend and check `/api/auth/demo` |
| Chat returns a timeout or unavailable message | no network, or an exhausted key | check `DEEPSEEK_API_KEY` and the provider status |
| `/` returns 404 | the UI was never built | run `./start.sh` without `--no-build` |
| `import` fails on SQLite | a stale local store from an older schema | delete `data/app/app.sqlite3` and repeat step 4 |

## Detailed Instructions

Everything below runs from the repository root. The default path needs no TACC account; the TACC jobs in section D are optional and exist to rebuild the corpus artifacts that are already tracked.

### What can be reproduced

| Result | Data in the repository | Rerun with | Numbers live in |
|---|---|---|---|
| Chunking matrix, RRF sweep, dual-granularity index | 65 questions, a 13-document page snapshot, 9 cells | `experiments/chunking/scripts/run_experiment.py` | [experiments/chunking/RESULTS.md](experiments/chunking/RESULTS.md), [REPORT.md](experiments/chunking/REPORT.md) |
| Citation accuracy, control against treatment | 15 answers, 11 generated questions, two judged question sets | [benchmarks/results/run_eval.py](benchmarks/results/run_eval.py), plus the manual web baseline | [benchmarks/results/](benchmarks/results/) notes |
| Self-test generation and grading metrics | a frozen mock run: questions, answers, grades, ground truth | `python -m verifiable_tutor.eval.cli` | [benchmarks/self_test/](benchmarks/self_test/) `metrics.json` |
| OCR, index, and Qwen knowledge-base jobs | job directories and tracked outputs | `scripts/tacc/` and `tcloud` | [docs/tacc-notes.md](docs/tacc-notes.md) |

### A. Chunking and hybrid retrieval

This is the main quantitative result: which chunking rule puts the correct page in front of the model, and at what token cost. Nine cells share one retrieval stack, so a difference comes only from how pages are cut.

Fixed design, identical in every cell: BGE-M3 dense retrieval plus SQLite FTS5 BM25, reciprocal rank fusion with `k=60`, 30 candidates per arm, page-level deduplication, the raw question text with no rewrite, temperature 0. Primary metric: page-level nDCG@5 on hybrid retrieval over the 51 test questions, with a paired bootstrap (2000 samples, 95 percent interval) and an exact McNemar test for hit rates.

Data:

- `experiments/chunking/questions/retrieval_v1.jsonl`: 65 questions, 14 dev and 51 test, each with gold pages.
- `data/corpus/pages/`: the tracked page records, now 16 documents.
- `experiments/chunking/results/page_manifest.json`: the 13 documents and 365 pages the questions were written against.

The corpus grew to 16 documents on 2026-11-23, after the experiment ran. Use the manifest to rebuild the smaller snapshot, so the numbers below are the numbers you get:

```bash
python3 - <<'PY'
import json, shutil, pathlib
manifest = json.load(open("experiments/chunking/results/page_manifest.json"))
out = pathlib.Path("/tmp/vt-chunking-pages"); out.mkdir(exist_ok=True)
for name in manifest["files"]:
    shutil.copy(pathlib.Path("data/corpus/pages") / name, out / name)
print(len(list(out.glob("*.jsonl"))), "documents,", manifest["pages"], "pages")
PY
```

Expected: `13 documents, 365 pages`.

The project virtual environment already holds torch, transformers, and the package, so no second environment is needed. The embedder downloads to `models/bge-m3` in step 3 of Getting Started.

```bash
export PYTHONPATH="$PWD/src:$PWD/experiments/chunking"
.venv/bin/python experiments/chunking/scripts/run_experiment.py \
  --pages /tmp/vt-chunking-pages \
  run --cells full --calibrate-semantic --run-id repro-01 --model-path models/bge-m3
```

The run calibrates the semantic threshold on the dev split first and prints, in order, `[calibrate] threshold=0.25 dev_ndcg@5=0.8682 chunks=381`, `threshold=0.3 dev_ndcg@5=0.8588`, `threshold=0.35 dev_ndcg@5=0.8445`, then `selected threshold=0.25`, then one line per cell, then the summary table. It writes `experiments/chunking/results/repro-01/summary.json`.

Expected results on the 51 test questions, hybrid retrieval. This is the table the report cites.

| Cell | nDCG@5 (95 percent CI) | hit@5 | tokens@5 |
|---|---:|---:|---:|
| `page_only` | 0.8512 [0.7562, 0.9330] | 0.882 | 1059 |
| `page_first_128` | 0.8405 [0.7563, 0.9160] | 0.922 | 586 |
| `page_first_256` | 0.8384 [0.7463, 0.9197] | 0.902 | 760 |
| `page_first_450` | 0.8487 [0.7532, 0.9314] | 0.882 | 937 |
| `recursive_128` | 0.8130 [0.7188, 0.8949] | 0.902 | 596 |
| `recursive_256` | 0.8488 [0.7580, 0.9272] | 0.902 | 811 |
| `recursive_450` | 0.8562 [0.7677, 0.9343] | 0.902 | 1008 |
| `semantic_450` | 0.8562 [0.7677, 0.9343] | 0.902 | 1008 |
| `cross_page_450` | 0.8368 [0.7463, 0.9143] | 0.902 | 944 |

What the numbers mean, and what to check:

- Every paired interval against `page_only` crosses zero, so no cell significantly beats it. `recursive_450` and `semantic_450` lead by 0.005 with 1 win, 49 ties, and 1 loss, which is noise.
- `page_first_450` is statistically tied with `page_only` and uses 122 fewer tokens for the top five pages, which is why it is the production rule.
- The lexical arm prefers large chunks and the dense arm prefers small ones; the ablation table in `RESULTS.md` shows `page_first_450` at 0.7786 lexical against `page_first_128` at 0.7270, and dense at 0.8319 against 0.8941. Hybrid ties because the two preferences cancel.

Two optional runs complete the report:

```bash
# Experiment 2: RRF weight sweep on the three strongest distinct cells
.venv/bin/python experiments/chunking/scripts/rrf_weights.py --run-id rrf-weights-01

# Experiment 3: dual-granularity index, 1:1 and dense 2:1
.venv/bin/python experiments/chunking/scripts/dual_granularity.py --run-id dual-granularity-01
.venv/bin/python experiments/chunking/scripts/dual_granularity.py --run-id dual-dense2-01 --weights 2:1
```

Expected, RRF (nDCG@5, dense:lexical weights 1:1, 2:1, 1:2): `recursive_450` 0.8562, 0.8302, 0.8412; `page_only` 0.8512, 0.8302, 0.8218; `page_first_450` 0.8487, 0.8302, 0.8337. Every change is worse than 1:1.

Expected, dual granularity (nDCG@5, hit@3, hit@5): `page_first_450` hybrid 0.8487, 0.882, 0.882; `page_first_128` dense only 0.8941, 0.941, 0.980; dual 1:1 0.8567, 0.863, 0.902; dual dense 2:1 0.8596, 0.902, 0.941. Both dual intervals cross zero, and the index costs about 2.7 times as many vectors.

Runtime: the full matrix took 8 minutes on an Apple M-series laptop with MPS, about 4 of them the first embedding pass (2,844 new texts; 4,510 distinct chunk texts across the calibration cells). Vectors are cached by content in `experiments/chunking/data/cache/vectors.db`, so a second run over the same cells takes about a minute. `.venv/bin/python experiments/chunking/scripts/report.py experiments/chunking/results/repro-01/summary.json` prints the Markdown tables from a summary.

### B. Citation accuracy against a hosted chatbot

Experiment Part 2 asks whether each system cites what it says, and whether the citation can be checked without trusting the model. Control: DeepSeek web with the course PDF uploaded. Treatment: this tutor, which retrieves from all 16 documents and verifies each quoted span against its page.

Data and state: `benchmarks/results/part2b_answers.jsonl` holds the treatment's 15 answers with numbered `[ref_N]` sources; `part3a_questions.json` holds 11 generated FlashAttention questions with knowledge points; the two result notes record the judged control and treatment behaviour.

```bash
# with the backend running (step 5 of Getting Started), regenerate the treatment side
.venv/bin/python benchmarks/results/run_eval.py
```

The script logs in with the account in its `main` function, posts the 15 questions to `/api/chat`, parses the AI SDK stream, and writes both files. Change the email and password in the script if you seeded a different account. It prints one line per question with latency, answer length, and source count.

Expected: 15 answers, each with numbered sources, in about four minutes. The judged result to reproduce is in [citation-accuracy-lecture2-q1-q5.md](benchmarks/results/citation-accuracy-lecture2-q1-q5.md) and [citation-accuracy-tutorial4-q6-q10.md](benchmarks/results/citation-accuracy-tutorial4-q6-q10.md):

- The control's positive citations are all correct: 18 of 18 quoted spans are on the page it names.
- The control's negative claims are all wrong: 4 of 4 "the PDF does not mention X" claims point at material that is present (CXL on pages 60, 66, and 67; bank conflict on page 51; locality on pages 22 to 24; registers and shared memory on pages 43 and 50).
- The treatment answers those three questions and cites the pages.
- On a 40-page tutorial the control stopped at page 12; the treatment retrieved across all pages.

Checking a treatment citation needs no model: the span verifier compares the quoted text with the tracked page record, and the same check runs in the chat stream as `verify_span`. The control side is judged by hand, because the web product exposes no API; the notes date each run.

### C. Self-test generation and grading

This is RQ2. The protocol is [docs/benchmark-protocol.md](docs/benchmark-protocol.md): two topics, two systems (this agent and DeepSeek web with the chapter PDF), blind annotation, a frozen shared grading set of 8 questions with 4 simulated answers each, developer ground truth, and both graders run on the same items. Metrics: knowledge-point coverage, question validity, reference-answer verifiability, citation validity, and for grading exact match, within-one-point agreement, normalized mean absolute error, false-pass rate, and false-fail rate.

Data layout and the step-by-step checklist are in [benchmarks/self_test/](benchmarks/self_test/) (`RQ2_checklist.md`, `annotation_template.md`, `knowledge_points.yaml`). The committed `run-mock` directories are a frozen fixture that proves the metric arithmetic; the FlashAttention generation runs hold the web transcripts.

```bash
.venv/bin/python -m verifiable_tutor.eval.cli rq2a benchmarks/self_test/generation/run-mock --expected-points 5
.venv/bin/python -m verifiable_tutor.eval.cli rq2b benchmarks/self_test/grading_shared/run-mock --grader b
```

Expected output, byte for byte the committed `metrics.json`:

```json
{"run_id": "run-mock", "knowledge_point_coverage": 0.8, "question_validity_rate": 0.8,
 "reference_answer_verifiability": 0.8, "citation_validity": 0.75}
{"run_id": "run-mock", "grader": "b", "exact_match_rate": 1.0,
 "within_one_point_agreement": 1.0, "normalized_mae": 0.0,
 "false_pass_rate": 0.0, "false_fail_rate": 0.0}
```

A live RQ2 run needs two annotators, one DeepSeek web session per topic, and the simulated answers from `scripts/simulate_student_answers.py`; the checklist is the procedure and the numbers are written back to `metrics.json`. This is a small-sample course benchmark, and the protocol states that a tie is reported as a tie.

### D. Optional: the TACC model-serving path

The corpus artifacts under `data/` were produced by three submitted jobs, and the tracked results mean a reviewer never has to run them. To rerun them, configure the platform CLI with `tcloud config -u <user> -f <key>` and `tcloud init`, then:

```bash
.venv/bin/python scripts/ingest_corpus.py ocr --batch lectures     # GPU OCR job
.venv/bin/python scripts/ingest_corpus.py index --force            # BGE-M3 index job
.venv/bin/python scripts/ingest_corpus.py summarize --resume       # Qwen knowledge cards
```

Recorded evidence: OCR and index jobs 28201, 28215, 28227, 28214, 28237, and 28242 on 2026-11-05, refreshed as jobs 31009 to 31014 on 2026-11-23 for lectures 3 to 5; the Qwen knowledge-base round trip is job 28067 with a 434 s vLLM cold start and 8 of 8 valid records. `index --force` is required over the whole corpus, because an index job replaces the vector file with the rows it computed. Job budgets, queue behaviour, and the one-hour limit are in [docs/tacc-notes.md](docs/tacc-notes.md).

### Mapping from results to the report

| Reported item | Repository artifact that holds it | Command that produces it |
|---|---|---|
| Table 1, nine-cell chunking matrix (nDCG, hit, tokens, truncation) | `experiments/chunking/REPORT.md` Experiment 1, `RESULTS.md` main table | the `run_experiment.py` command in section A |
| Table 2, RRF weight sweep | `REPORT.md` Experiment 2, `RESULTS.md` RRF section | `rrf_weights.py` |
| Table 3, dual-granularity index | `REPORT.md` Experiment 3, `RESULTS.md` dual section | `dual_granularity.py` |
| Lexical and dense ablation, category and page-length breakdown | `RESULTS.md` ablation and breakdown sections | `report.py` on `summary.json` |
| Citation accuracy: precision, negative claims, long-document recall | the two `citation-accuracy-*.md` notes | `run_eval.py`, plus the dated manual control run |
| RQ2a and RQ2b tables | `benchmarks/self_test/*/metrics.json` | `verifiable_tutor.eval.cli` |
| System and container diagram | `proposal/figs/fig2_components_v3.png` and its `.dot` source | `dot -Gdpi=300 -Tpng proposal/figs/fig2_components_v3.dot -o proposal/figs/fig2_components_v3.png` |

### Known limitations and expected variation

- **The corpus grew after the chunking run.** The experiment used 13 documents and 365 pages; the tracked corpus now has 16 documents and 593 pages. Section A pins the snapshot from `page_manifest.json`. Run against the current corpus on 2026-11-24, the same command gives `page_only` 0.8316 and `page_first_450` 0.8487 on the test split; every paired interval still crosses zero, and `page_first_450` stays tied and cheaper, so the conclusion does not change.
- **Page records were regenerated after the run.** The sha256 values recorded in `page_manifest.json` no longer match the tracked files, because the OCR stage re-exported them. Page numbering and page text are unchanged. A rerun on 2026-11-24 on macOS with MPS reproduced six of the nine hybrid cells exactly and the other three within 0.005 nDCG. The dense arms of three small-chunk cells moved by up to 0.015, because those cells carry up to 48 oversize chunks that BGE truncates at 512 tokens, so the weight of the last tokens depends on the device. Every paired interval still crosses zero, and the ordering among statistically tied cells can swap, which is what the intervals are for.
- **Embedding device and library version.** Ranking is stable across CPU and MPS; the fourth decimal of nDCG can move. The original environment is recorded in `experiments/chunking/results/environment.json`.
- **Live model output varies.** Chat answers differ between runs. The citation verdicts do not depend on the model: the span verifier compares quoted text with the tracked page record. The response cache under `data/caches/` reduces paid calls; delete it to force fresh calls.
- **The control arm is a moving product.** DeepSeek web changes without notice, so the control side of section B is dated, transcribed, and judged by hand. The notes are the reproducibility mechanism.
- **RQ2 committed numbers are a mock run.** They validate the harness, not the hypothesis. A live run needs annotators and web sessions, as the protocol states.
- **Twelve stale UI tests.** `npm run test` reports 264 of 276 passing; `tests/practice-page.test.tsx` and `tests/chat-live.test.tsx` still assert the pre-live practice and chat pages. The Python suite, which covers the backend contract, is green.
- **Small samples.** 65 retrieval questions, 15 citation answers, and 8 graded items with 4 variants each. These are course-project signals, not validated benchmarks; the protocol says a tie is a tie.
- **TACC timing is queue dependent.** Job ids and measured cold starts are recorded, not promised. The one-hour partition limit is why the knowledge-base job is sharded.
- **Some UI surfaces are preview-only.** The knowledge-card browser and the build console render fixtures; the build itself needs a TACC account.

### Cost and runtime

| Step | Wall time | Notes |
|---|---|---|
| `pip install -r requirements.txt` | 5 to 10 minutes | about 2 GB of wheels |
| BGE-M3 download | 3 to 10 minutes | 2.3 GB |
| `ingest_corpus.py import` | about 30 seconds | 612 chunks from tracked records |
| `.venv/bin/python -m pytest` | 2 to 4 minutes | 455 tests, no network |
| Chunking matrix, section A | about 8 minutes | 9 cells, first embedding pass |
| RRF sweep and dual granularity | about 2 and 4 minutes | reuse the vector cache |
| Citation run, section B | about 4 minutes | 15 chat turns, paid model calls |
| RQ2 metrics on the frozen run | under a second | no model calls |

## What it is

A tutoring agent for one course whose outputs are checkable in three ways: text claims against cited page spans, code artifacts against executable tests, and disclosure against a dated policy. The scope is deliberately narrow: this course's own materials, assignments, and deadlines. The full argument, including motivation and design rationale, is in [proposal/proposal_v3.md](proposal/proposal_v3.md) (current; the submitted v1 is [proposal/proposal.md](proposal/proposal.md) and v2 is a previous draft); this README is the entry point, not a second proposal.

## Use cases

Students can:
- Ask course questions and receive answers that cite the exact page and quoted span.
- Ask by voice: record in the composer for transcription, or attach an audio file for MiMo 2.6 to analyze; play assistant answers as speech.
- Request a review outline or self-test questions on a topic; answer them and receive graded feedback with citations.
- Practise with a generated exercise at the scale and environment of the corresponding assignment, receiving a reference solution, tests, and a stepwise explanation; code answers are graded by the model against the scoring points.
- Submit their own solution and receive line-anchored teaching.
- Browse the course knowledge base built by Qwen on TACC; the agent uses the cards for review outlines and self-tests.

Instructors and TAs can:
- Maintain the deadline registry that drives the disclosure policy.
- Trigger knowledge-base builds and watch the TACC Qwen job from the UI.

## Disclosure policy

A five-state policy decides what the agent may reveal. The states are pre-release, active, extension window, post-deadline, and unknown.

| Policy state | What the agent does |
|---|---|
| Pre-release, active, extension window | Refuses complete homework solutions and offers hints. Explains a user-provided solution only at the level provided and never fills in missing parts. |
| Post-deadline | Replaces refusal with full teaching plus a verified solution. |
| Unknown | Abstains rather than guesses; insufficient evidence also leads to abstention. |

The gate is code, not a prompt: a versioned registry of release and due dates with extensions, an intent classifier, and a log of every decision. The proposal covers the policy in [section 2](proposal/proposal_v3.md#2-task-definition-and-outputs) and [section 3](proposal/proposal_v3.md#3-proposed-system).

## Architecture

The system has four moving parts: a React browser UI served by the agent backend, the local FastAPI backend and its stores, a model-client abstraction over external OpenAI-compatible APIs (DeepSeek primary, Xiaomi MiMo selectable, with no automatic cross-model fallback), and a required TACC model-serving path. TACC runs two submitted model jobs: the BGE-M3 index job and the Qwen knowledge-base enrichment job. The Qwen job reads course chunks and a request from `USERDIR`, writes cited knowledge cards as JSONL, and exits; the local backend polls, downloads, validates, and stores them. TACC is reached only through job submission, with no SSH forwarding or inbound service ([ADR-0011](docs/adr/0011-tacc-as-required-model-serving-backend.md)). The agent workflow is a LangGraph `StateGraph` ([ADR-0008](docs/adr/0008-langgraph-as-agent-orchestration-runtime.md)), and local development traces model calls and graph steps into a self-hosted Langfuse instance ([ADR-0007](docs/adr/0007-langfuse-for-local-model-call-tracing.md), [docs/langfuse-local.md](docs/langfuse-local.md)). The retrieval index is built on TACC with BGE-M3, and query embedding runs on the laptop ([ADR-0004](docs/adr/0004-hybrid-retrieval-with-bge-m3.md)). The project environment is a pinned layer installed into the user workspace; the platform does not support custom images ([ADR-0001](docs/adr/0001-pinned-python-environment-without-docker.md)).

![System containers and components](proposal/figs/fig2_components_v3.png)

The Qwen knowledge-base job loads Qwen3.8-27B-AWQ-INT4 with vLLM at TP=2 and 32K context inside one submitted job per document shard and exits; no endpoint is exposed. Interactive text generation uses external APIs configured in `config/models.yaml` with keys in `.env` ([ADR-0005](docs/adr/0005-external-model-apis-as-primary.md)); Qwen is the required offline text-processing backend ([ADR-0011](docs/adr/0011-tacc-as-required-model-serving-backend.md)). The figure source is [proposal/figs/fig2_components_v3.dot](proposal/figs/fig2_components_v3.dot).

The subsystems inside the backend:
- Agent loop (implemented 2026-11-06): a two-node LangGraph graph calls the model, executes a closed typed tool set (course search, page reading, DeepSeek search, DeepSeek fetch), returns the results to the model, and streams step, tool, text, and reasoning frames; reasoning and tool calls persist as ordered work-chain events with their step association in schema version 5 ([ADR-0016](docs/adr/0016-minimal-agent-loop-and-typed-tools.md), [ADR-0017](docs/adr/0017-ordered-work-chain-events.md), [ADR-0019](docs/adr/0019-step-event-association.md)).
- Accounts: email and password sign-in restricted to course student domains, with a verification code, password reset, scrypt hashing, and server-side sessions; a student and an instructor role. The requirements are in [docs/prd.md](docs/prd.md) and the QQ Mail procedure in [docs/email-local.md](docs/email-local.md).
- Evidence: a TACC OCR job parses PDF files, one file per request, into page records with page numbers, block boxes, reading order, and page images ([ADR-0002](docs/adr/0002-ocr-on-tacc-with-paddleocr-vl.md), [docs/corpus-schema.md](docs/corpus-schema.md)); `scripts/tacc/parse_pdf.py` runs the whole local-to-TACC round trip and returns per-page JSONL plus one document markdown; hybrid retrieval fuses SQLite FTS5 BM25 with BGE-M3 dense embeddings and an optional reranker ([ADR-0004](docs/adr/0004-hybrid-retrieval-with-bge-m3.md)); a deterministic span verifier requires every quoted span to occur on its cited page, with one repair round or abstention.
- Practice lab and self-test: generated questions in the types the student asks for or the agent chooses, with cited reference answers; choice questions are graded deterministically and open and code answers are graded by the model against the scoring points, with citations. The pack design is MPI/GEMM with the same toolchain, Makefile, public datasets, and an sdk-test-style harness; a generated reference solution is accepted only after it compiles and passes the pack's tests.
- Knowledge base: a TACC Qwen job builds cited knowledge cards for course chunks; the backend polls the job, downloads and validates the records, and stores them locally for browsing, review outlines, and self-tests ([ADR-0011](docs/adr/0011-tacc-as-required-model-serving-backend.md), [docs/knowledge-schema.md](docs/knowledge-schema.md)).
- Policy gate: the code-level gate described above, plus the versioned deadline registry it reads.
- Teaching explainer: cites page spans, code lines, and test outcomes, and never invents missing content before the deadline.
- Model client and trace logger: external OpenAI-compatible APIs are primary for interactive text (DeepSeek, and Xiaomi MiMo when the user or config selects it, including audio). A failed call retries the selected model and then shows a timeout or unavailable message; it never switches models, configured in `config/models.yaml` with keys in `.env`; Qwen on TACC is the required offline knowledge-base backend, not a chat provider; every call is labelled and cached; audio-file input is supported when a MiMo 2.6 model is selected, the composer microphone uses MiMo ASR, and assistant text can be spoken with MiMo TTS ([model-providers.md](docs/model-providers.md)); traces, tests, and results follow the required execution path from task to visible result ([ADR-0005](docs/adr/0005-external-model-apis-as-primary.md)).

The browser UI is a React single-page application with shadcn and AI Elements components, served as static assets by the backend on one origin. The page structure, routes, component map, and preview fixtures are in [docs/ui-structure.md](docs/ui-structure.md); the preview build makes no API request. Streaming uses the AI SDK UI message stream protocol, so the same frontend path serves live and replay sessions ([ADR-0003](docs/adr/0003-react-spa-with-ai-elements.md)). The job topology, batch windows, and demo modes are in [docs/tech-selection.md](docs/tech-selection.md#jobs-and-demo-modes).

## Implementation status

Everything marked implemented runs on the development laptop and is covered by the Python suite; the rest is stated so a reviewer does not look for it.

| Area | State |
|---|---|
| Model layer | implemented: DeepSeek and MiMo adapters, streaming, ASR, TTS, content-addressed cache, live smoke |
| Backend | implemented: health, accounts and sessions, streamed chat, history and replay, voice, knowledge browser, corpus page images, practice |
| Agent loop | implemented: two-node LangGraph, typed tools (course search, page read, DeepSeek search and fetch, span verify), ordered work-chain events, numbered sources |
| Retrieval | implemented: FTS5 BM25 plus BGE-M3 with RRF and page deduplication; the span verifier is implemented, claim support is pending |
| Policy gate | implemented: five states, versioned deadline registry, intent classification, decision log |
| Practice | implemented: question generation, deterministic grading for choice questions, model grading for open and code answers |
| Knowledge base | implemented: the Qwen job, record validation, the local store, and browsing; the card browser and the build console are preview pages |
| Corpus pipeline | implemented on TACC: OCR, the BGE-M3 index, and document summaries; the artifacts are tracked |
| Evaluation | implemented: the chunking matrix, the citation study, and the RQ2 harness |
| Not built | the SQLite checkpointer, the six-node topology, TACC code execution, multi-course support |

## Repository layout

All paths are repository-relative. Planned roles are statements of intent, not descriptions of implemented behavior.

| Path | Intended role | State |
|---|---|---|
| `.githooks/` | Versioned Git hooks; the pre-commit hook keeps the physical data model documents in sync with the SQLite schema | present: pre-commit |
| `src/verifiable_tutor/auth/` | Accounts, authentication, sessions, and roles | present: accounts, sessions, email seam, seeding |
| `src/verifiable_tutor/api/` | FastAPI application, routers, dependencies, and the AI SDK UI message stream adapter; serves the API and the built UI on one origin | present: factory, routers, chat and replay services, stream encoder |
| `src/verifiable_tutor/policy/` | Code-level disclosure gate and deadline registry | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/orchestrator/` | Request routing and context budget | present: two-node LangGraph loop, typed tool registry, course and web tools |
| `src/verifiable_tutor/evidence/` | Hybrid retrieval (query plan, FTS5 and dense arms, reciprocal rank fusion) and the deterministic span verifier | present: retrieval; verifier pending |
| `src/verifiable_tutor/practice/` | Practice pack generation and executable tests | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/teaching/` | Line-anchored explanations | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/eval/` | Evaluation harness | placeholder (`.gitkeep`) |
| `src/verifiable_tutor/corpus/` | Page records, the page-first chunker, and the local knowledge store | present: chunker, store, pages |
| `src/verifiable_tutor/knowledge/` | Knowledge-base build orchestration, record validation, local storage, and build state; present: chunk, request and schema validation helpers, card reader, and build lifecycle | present: helpers, cards, builds |
| `src/verifiable_tutor/llm/` | Model configuration loader, unified provider adapter, and file-backed response cache; replay and mock backends pending | present: config, adapter, cache, search and fetch used by the agent tools |
| `src/verifiable_tutor/prompts/` | Model prompt texts in one editable home: the chat system prompt and the knowledge-base job template, loaded by the code that sends them | present: chat and kb prompts |
| `src/verifiable_tutor/ui/web/` | React UI source: routes, layout, page components, preview fixtures, and Vitest tests; built assets are written to the ignored `src/verifiable_tutor/ui/static/` | present: live API wiring and preview build |
| `tacc/serve/` | Required Qwen knowledge-base job: one submitted GPU job per document shard, records written to `USERDIR` | present: job, worker, prompt |
| `tacc/env-spike/` | Committed CPU spike: environment bootstrap, FTS5, and platform checks | present: spike job |
| `tacc/ocr-smoke/` | Committed GPU spike: PaddleOCR-VL smoke on representative pages | present: spike job |
| `tacc/pdf-parse/` | Committed GPU job: parses one complete PDF file end to end (enumerate, render, layout, recognition, document markdown) | present: demo path spike |
| `tacc/ocr/` | TACC GPU job for page rendering, layout, and OCR; batch manifest, private jobhome, one images archive | present: batch job |
| `tacc/index/` | TACC GPU job for BGE-M3 chunk embeddings (vectors, row map, summary) | present: index job |
| `tacc/exec/` | TACC CPU job that runs reference tests and self-test code answers | planned (not created yet) |
| `tacc/client/` | TACC CPU job for the offline evaluation harness | placeholder (`.gitkeep`) |
| `benchmarks/questions/`, `benchmarks/policy_scenarios/`, `benchmarks/results/` | Course questions, policy scenarios, and recorded results; `results/` holds the citation study data, its notes, and the evaluation script | `results/`: present; `questions/` and `policy_scenarios/`: placeholder (`.gitkeep`) |
| `benchmarks/self_test/` | Self-test generation and grading benchmark data for RQ2 | planned (not created yet) |
| `data/corpus/`, `data/index/`, `data/caches/`, `data/kb/` | Course PDFs, OCR output and page images, dense plus BM25 index, the document-summary snapshot, cached embeddings and retrieval snapshots, knowledge-base records and build state | `data/corpus/`, `data/index/`, and `data/kb/` are tracked; `data/app/` and `data/caches/` are gitignored runtime state |
| `models/` | Local model weights: BGE-M3 for query embedding, downloaded at setup and read through `embedding.model_path` in `config/models.yaml` | present: local weights, gitignored |
| `config/` | Runtime configuration: `models.yaml` owns provider endpoints, model ids, roles, request parameters, cache, and embedding settings; `knowledge.yaml` owns Qwen job resources, shard size, prompt version, paths, and polling; `app.yaml` owns the allowed registration domains, cookie flags, local data paths, and replay speed | present: model, knowledge, and app config |
| `scripts/` | Utility scripts: TACC bootstrap, submit helper, shared OCR stage helpers, the local PDF parse request interface, the local knowledge-base driver, the live model smoke, the API documentation build and vendor scripts, and the physical data model build script | present: scripts |
| `experiments/` | Self-contained experiments that import the application read only: the chunking and hybrid-retrieval study, its 65 questions, tracked summaries, and its English and Chinese reports | present: chunking experiment |
| `tests/` | Test suites under `tests/llm/` (configuration, chat, streaming, transcription, search, fetch), `tests/knowledge/` (chunks, request, schema), `tests/tacc/` (Qwen job worker, driver validation), `tests/api/` (HTTP contracts, accounts, chat, replay, voice, knowledge, corpus, SPA deep links), `tests/storage/` (schema upgrade, turn metadata), and `tests/docs/` (generated data model drift); the UI tests live inside the Vite project at `src/verifiable_tutor/ui/web/tests/` | present: tests |
| `pyproject.toml`, `uv.lock`, `requirements.txt` | Python packaging, dependencies, pytest configuration, and locked local environment; `requirements.txt` is generated from the lock with exact version pins for the runtime, the `dev` extra, and the `embedding` extra | present: packaging |
| `start.sh` | One-command local start: install UI dependencies when needed, build the SPA, and run the backend on one origin; flags for the Vite dev server, skipping the build, and the backend port | present: start script |
| `examples/` | Usage examples | placeholder (`.gitkeep`) |
| `docs/figures/` | PRD diagram sources and renders (use case, containers, sequence examples, ER), the generated physical schema diagram, and future report figures | present: PRD diagrams and the physical schema diagram |
| `docs/prd.md` | Product requirements, scope, acceptance criteria, and milestones | present: PRD |
| `docs/todo.md` | Ordered backlog, priorities, and item state, with the lead directives of 2026-11-06 | present: backlog |
| `docs/research/` | Dated research notes that check a plan against first-party sources; evidence, not a source of truth | present: 2026-11-06 agent loop check |
| `GLOSSARY.md` | Domain vocabulary used across the docs and code | present: glossary |
| `docs/tech-selection.md`, `docs/adr/` | Technology decisions and the ADRs that argue them | present: decisions |
| `docs/fastapi-reference.md` | FastAPI conventions for the local backend, distilled from the official documentation, for agents writing backend code | present: reference |
| `docs/api/` | Committed offline Swagger UI API documentation: deterministic `openapi.json`, generated `index.html`, pinned vendored Swagger UI assets, and regeneration instructions | present: API docs bundle |
| `docs/physical-data-model.md` | Generated physical SQLite data model: tables, columns, types, keys, checks, indexes, and the versioned migration, distinct from the logical PRD ER model | present: generated data model |
| `docs/ui-structure.md` | Browser UI page structure: routes, layout regions, component map, preview states, data coverage, and TDD seams | present: UI structure |
| `docs/corpus-schema.md` | Field-level contract for page, block, document and chunk records | present: schema |
| `docs/knowledge-schema.md` | Request, progress, and record contracts for the knowledge-base build | present: schema |
| `docs/paddleocr-vl-api.md` | PaddleOCR-VL request and response construction across the local, serving, and hosted paths | present: API notes |
| `docs/langfuse-local.md` | Local development tracing runbook | present: runbook |
| `docs/email-local.md` | Registration and reset email runbook | present: runbook |
| `docs/tacc-notes.md` | Platform constraints, budgets, and mechanics | present: notes |
| `proposal/` | Proposal sources: v1 `proposal.md`, v2 `proposal_v2.md`, and v3 `proposal_v3.md`, `build_proposal.py`, figure `.dot` sources, rendered PDFs, DOCX files, and v3 previews | present: proposal sources |

## Documentation

- [experiments/chunking/REPORT.md](experiments/chunking/REPORT.md): the chunking experiment report, with [RESULTS.md](experiments/chunking/RESULTS.md) for the data and [README.md](experiments/chunking/README.md) for the runbook.
- [proposal/proposal_v3.md](proposal/proposal_v3.md): readable Markdown text of the current proposal, generated by `proposal/build_proposal.py --version 3`.
- [proposal/proposal_v2.md](proposal/proposal_v2.md): Markdown text of the previous draft, kept for history.
- [proposal/proposal.md](proposal/proposal.md): Markdown text of the submitted v1 proposal, kept frozen.
- [docs/prd.md](docs/prd.md): product requirements, scope, acceptance criteria, and milestones.
- [GLOSSARY.md](GLOSSARY.md): the project's domain vocabulary.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v3.pdf](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v3.pdf): the two-page proposal prepared for submission on 2026-11-01, exported from the v3 DOCX with LibreOffice.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v3.docx](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v3.docx): editable v3 DOCX.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v2.pdf](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v2.pdf): previous draft PDF.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v2.docx](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE_v2.docx): previous draft DOCX.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.pdf](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.pdf): the submitted v1 PDF, kept frozen.
- [CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.docx](proposal/CSIT6000V_Project_Proposal_2026F_LI_TIAN_XIE.docx): the submitted v1 DOCX, kept frozen.
- [docs/figures/](docs/figures/): PRD diagram sources (`.dot`) and rendered PNGs: use cases, containers, sequence examples including the knowledge-base build, and the entity relationship model.
- [docs/tech-selection.md](docs/tech-selection.md): technology choices, job topology, demo modes, and the week-one verification spikes.
- [docs/fastapi-reference.md](docs/fastapi-reference.md): agent-facing FastAPI reference for the local backend: the planned layout, implementation rules, streaming, sessions, testing, and the official documentation behind each rule.
- [docs/api/](docs/api/): committed offline Swagger UI for the local API: deterministic OpenAPI schema, generated page with pinned vendored assets, and the regeneration and upgrade procedure.
- [docs/physical-data-model.md](docs/physical-data-model.md): the generated physical SQLite data model with its Graphviz diagram, guarded against drift by `tests/docs/`, and explicitly separate from the logical PRD ER model.
- [docs/corpus-schema.md](docs/corpus-schema.md): page, block, document and chunk record fields produced by the OCR pipeline.
- [docs/knowledge-schema.md](docs/knowledge-schema.md): request, progress, and knowledge-record contracts for the Qwen knowledge-base build.
- [docs/benchmark-protocol.md](docs/benchmark-protocol.md): the RQ2 self-test generation and grading benchmark: baseline, shared set, simulated answers, ground truth, and metrics.
- [docs/paddleocr-vl-api.md](docs/paddleocr-vl-api.md): PaddleOCR-VL request and response construction for the local pipeline, the recognition service, the self-hosted parsing service, and the hosted official API.
- [docs/model-providers.md](docs/model-providers.md): agent-facing API notes for DeepSeek and Xiaomi MiMo, model switching, image and audio input, thinking control, web search, JSON output, and tool calling.
- [docs/adr/](docs/adr/): decision records for the environment, the OCR pipeline, the UI stack, the retrieval model, the model backend, retry behaviour, local model-call tracing, the orchestration runtime, typed agent tools, the local backend, the required TACC model-serving backend with the knowledge base, the FastAPI backend structure and sessions, the local offline Swagger UI, and the persisted conversation turn metadata with its generated physical data model.
- [docs/langfuse-local.md](docs/langfuse-local.md): runbook for the optional local Langfuse instance used for development tracing.
- [docs/email-local.md](docs/email-local.md): runbook for registration and password reset email over QQ Mail SMTP.
- [config/models.yaml](config/models.yaml): provider endpoints, model ids, role routing, request parameters, and embedding settings. [config/knowledge.yaml](config/knowledge.yaml): Qwen knowledge-base job resources, shard size, prompt version, paths, and polling. Secrets stay in the ignored `.env`; [.env.example](.env.example) is the committed template.
- [docs/tacc-notes.md](docs/tacc-notes.md): platform constraints, budgets, and measured platform mechanics.
- [AGENTS.md](AGENTS.md): agent and contributor guide covering sources of truth, commands, and conventions.

## Team

- LI Jinchuan (21188271)
- TIAN Yujia (21201619)
- XIE Yifeng (21322152)

CSIT6000V Advanced AI Computing and Systems, Fall 2026. Instructor: Prof. Kai Chen. Proposal v1 dated October 27, 2026; v2 draft dated October 30, 2026; v3 dated November 1, 2026, for submission on 2026-11-01. Repository: https://github.com/Kane-LI-0114/verifiable-tutor
