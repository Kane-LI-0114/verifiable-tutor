# ADR-0002: OCR on TACC with PaddleOCR-VL-1.6

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-10-28 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

RQ1 requires every quoted span to occur on the page it cites, so the corpus needs a page number and page text for every slide. The existing PaddleOCR-VL transcripts in the course workspace cannot carry that requirement:

- A search of all 10 transcripts finds no page markers, and their image links are temporary hosted URLs.
- Two tutorial PDFs (`Tutorial_1.pdf`, `Tutorial_2.pdf`) have no text layer at all, so a PDF-text-only pipeline loses them.
- The corpus is small and known: 12 course PDFs, 342 pages, about 58 MB, including the assignment briefs.

The project decided that the system will not consume the existing transcripts. It will run a real OCR model on TACC and produce page text with metadata, including page numbers. The platform constrains the job: one GPU job at a time on a node, a one-hour policy cap, open egress, a read-only public environment with vLLM 0.26.0 and PyTorch 2.11, and 100 GB of group storage.

## Decision

We run a resumable OCR job on TACC with three stages, all inside `tacc/ocr/`:

1. **Render.** `pypdfium2` renders each PDF page at 200 DPI and writes a WebP page image plus the PDF text layer when one exists. The page number comes from this loop, not from the model.
2. **Layout.** PP-DocLayoutV2, through the PaddleOCR 3.6 client running on CPU, detects layout blocks and reading order.
3. **Recognition.** PaddleOCR-VL-1.6 (958.6M parameters, 1.92 GB, Apache-2.0) runs under vLLM 0.26.0 on one RTX 3090 and returns the block text. The vLLM recipe supplies the serving flags; the exact flags are re-checked in the first spike.

The job writes one JSONL record per page: `doc_id`, `pdf_sha256`, `page_no`, `width_px`, `height_px`, `dpi`, model and pipeline versions, `markdown`, `text`, `blocks[]` with block id, reading order, label, pixel and normalized boxes, and content, `layout_boxes[]` with detector scores, page image paths, `status`, latency, timestamp, and validation problems. It also writes one assembled document markdown with `<!-- page: N -->` markers. The field-level definition is [../corpus-schema.md](../corpus-schema.md); figure crops and separate table or formula arrays are deferred, and tables and formulas appear as `blocks[]` entries with those labels.

The job is resumable: output is flushed and fsynced every 25 pages, a sidecar records completed `(pdf_sha256, page_no)` keys, and the job stops starting new pages at 50 minutes and exits cleanly. Page images and page records are stored under `USERDIR`, not in the task directory.

Layout runs on CPU because the GPU is the throughput bottleneck for recognition and a second CUDA stack in the project environment adds installation and driver risk. If the first spike measures layout as material against the one-hour budget, the fallback is `paddlepaddle-gpu`.

## Consequences

**Positive:**
- Page numbers, block boxes, reading order, and figure crops in one schema, which RQ1 and the citation panel both need.
- The weights are small (1.92 GB) and the model family is the one that produced the existing transcripts, so its failure modes on these PDFs are partly known.
- Page images and page records support a deterministic span verifier and a visual citation panel without a PDF viewer in the browser.
- The job is restartable inside one-hour windows and can be split by document.

**Negative:**
- The PaddleOCR client and PaddlePaddle CPU wheel are new dependencies of about 1 to 2 GB; their installation under the PRoot runtime is unverified and is the main technical risk of week one.
- CPU layout serialises a stage that a GPU could overlap with recognition.
- OCR output differs from PDF text and from the old transcripts, so citation spans are against OCR text; the old transcripts are useful only as a human quality reference.
- Figure captions may be absent or weak, which limits answers about figure-only slides. This remains a known failure mode, not a solved problem.
- A one-hour job may not cover all 342 pages on a slow first run; resume logic is mandatory, not optional.

**Neutral:**
- The corpus is generated, ignored by Git, and staged from `USERDIR`; there is no committed corpus artifact.

## Alternatives considered

**dots.ocr and dots.mocr, evaluated on 2026-10-28.** For: vLLM 0.26.0 supports the `DotsOCRForCausalLM` architecture natively, so the stack would be one model with no PaddlePaddle and no layout model; weights are 6.08 GB; the license is MIT plus an acceptable-use overlay. Against: lower shared-protocol text accuracy than PaddleOCR-VL-1.6 (v1.5 TextEdit 0.048 versus 0.035), 3.04B parameters meaning roughly 43 to 85 minutes for the corpus and likely two jobs (estimate), no official vLLM recipe, and JSON output that needs repair plus a validity metric. Why not chosen: the project keeps span accuracy and throughput; this is the first fallback if the Paddle stack cannot be installed.

**Pure vLLM whole-page prompts, no layout model.** For: the fewest dependencies (no PaddlePaddle), the simplest job, and a clean fallback. Against: markdown only, with no block boxes or reading order, so the citation panel cannot highlight a span and figures cannot be linked. Why not chosen as the default: it loses the metadata the project wants. Kept as the last-resort fallback.

**MinerU 4.x with MinerU2.5-Pro.** For: mature pipeline and a comparable page and block schema with permissive weights. Against: heavier install, its own serving stack, and the AGPL weights of the 2509 variant. Why not chosen: more moving parts for a similar schema and no page-number advantage.

**External hosted OCR.** For: no local install and high quality. Against: cost the course does not reimburse, no offline reproducibility, and a network dependency in the critical path. Why not chosen: the platform rules push external calls off the critical path.

**PDF text layer only.** For: no model, exact page text, minimal dependencies. Against: two tutorials have no text layer, figures and formulas are lost, and the project has decided against the existing transcripts. Why not chosen: cannot cover the corpus.

## References

- PaddleOCR-VL-1.6 model card: https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6
- vLLM deployment recipe: https://docs.vllm.ai/projects/recipes/en/latest/PaddlePaddle/PaddleOCR-VL.html
- PaddleOCR pipeline output schema: https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html
- The 96.33 OmniDocBench v1.6 score is vendor-reported and is not treated as a measurement of this project.
- Corpus survey: 12 PDFs and 342 pages, measured on 2026-10-28 from the course workspace PDFs
- Verification items: [../tech-selection.md](../tech-selection.md#verification-spikes)
- Verified on 2026-10-29 (job 27879): vLLM 0.26.0 serves `PaddleOCR-VL-1.6` with `--trust-remote-code --served-model-name PaddleOCR-VL-1.6-0.9B`, PP-DocLayoutV2 runs on CPU from the PaddleX modelscope cache, and 10 pages produced 171 validated blocks at a median 4.26 s per page. Projected 342 pages: 1,934 s.
- Verified on 2026-10-29 (job 27884): one complete 8-page PDF parsed end to end, 121 blocks, one document markdown with 8 page markers, median 3.9 s per page, 414 s job body. Measurements: [../tacc-notes.md](../tacc-notes.md#verification-spike-results-2026-10-29).
