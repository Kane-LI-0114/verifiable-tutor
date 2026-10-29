# Corpus output schema

Owner: this file is the field-level contract for everything the OCR pipeline emits and for the chunk records that retrieval consumes. [tech-selection.md](tech-selection.md#corpus-and-ocr-pipeline) owns the pipeline decisions and [ADR-0002](adr/0002-ocr-on-tacc-with-paddleocr-vl.md) argues them; this file owns the record shapes. Bump the schema version when a field changes meaning.

Status on 2026-10-29: the page, block and document formats are implemented and verified in spike jobs 27884, 27887 and 27889. The chunk record is proposed for `src/verifiable_tutor/corpus/` and is not implemented yet.

## Artifacts per parse request

One request parses one PDF and writes these files under its output directory:

| Artifact | Content |
|---|---|
| `pages.jsonl` | One JSON object per page, in `page_no` order, `vt-page-record/1` |
| `records.json` | Aggregate counts, label totals, latency statistics, per-page status |
| `summary.json` | Job level result: request, page counts, timings, model and version, pass and fail |
| `document/<doc_id>-ocr.md` | The whole document as markdown with `<!-- page: N -->` markers |
| `pages/<doc>.p<NNN>.png` | Rendered page at 200 DPI, OCR input |
| `images/<doc>.p<NNN>.webp` | Compressed page image for the citation panel |
| `doc-pages.json` | Requested page subset resolved against the PDF |
| `render-manifest.json` | Page geometry and render timings |

## Page record (`vt-page-record/1`)

One object per page in `pages.jsonl`.

| Field | Type | Meaning | Consumer |
|---|---|---|---|
| `schema` | string | `vt-page-record/1` | Version checks |
| `doc_id` | string | Document identifier, the original PDF stem | Chunking, citation |
| `pdf` | string | Original file name, without the request prefix | Audit |
| `pdf_sha256` | string | SHA-256 of the uploaded PDF | Corpus hashing, cache keys |
| `page_no` | integer | 1-based page number, owned by the render loop | Citation, span verifier |
| `tags` | array of string | Request tags such as `table` or `formula`, empty for demo requests | Evaluation slices |
| `width_px`, `height_px` | integer | Rendered page geometry at `dpi` | Box normalisation, highlight |
| `dpi` | integer | Render resolution, 200 | Reproducibility |
| `pipeline_version` | string | PaddleOCR pipeline version, `v1.6` | Reproducibility |
| `layout_model` | string | `PP-DocLayoutV2` | Reproducibility |
| `recognition_model` | string | Served vLLM model id, `PaddleOCR-VL-1.6-0.9B` | Reproducibility |
| `image` | string | Path of the page PNG used for recognition | Re-run and audit |
| `webp` | string | Path of the page WebP used by the citation panel | UI |
| `pdf_text_chars` | integer | Characters in the PDF text layer, 0 for image-only PDFs | Quality signal |
| `markdown` | string | Page markdown as returned by the model and the markdown exporter | Document assembly, display |
| `text` | string | Plain text, the block contents joined in reading order | Span verifier, retrieval |
| `blocks` | array of block | Structured page content, see below | Chunking, citation |
| `layout_boxes` | array of layout box | Raw detector output before recognition | Debug, box score |
| `label_counts` | object | Label name to block count for this page | Quality monitoring |
| `pipeline_page_index` | integer or null | Index inside the model batch, 0 for one page per call | Debug |
| `status` | string | `ok` or `failed` | Resume and filtering |
| `latency_seconds` | float | End-to-end time for this page | Budget measurement |
| `timestamp` | string | ISO-8601 local time of the page | Audit |
| `validation_problems` | array of string | Empty when clean, otherwise identifiers such as `out_of_bounds:<block_id>` | Acceptance gate |
| `error`, `traceback_tail` | string, array | Present only on `status=failed` | Diagnosis |

## Block object

One element of `blocks[]`, in reading order.

| Field | Type | Meaning |
|---|---|---|
| `block_id` | integer | Stable id inside the page |
| `block_order` | integer or null | Reading order returned by the layout model |
| `label` | string | Layout label, for example `text`, `paragraph_title`, `table`, `display_formula`, `image`, `header_image`, `footer`, `number`, `vision_footnote`, `figure_title`, `algorithm` |
| `content` | string | Recognised content, markdown for tables and formulas |
| `bbox_px` | array of 4 floats | `[x1, y1, x2, y2]` in rendered page pixels |
| `bbox_norm` | array of 4 floats | The same box divided by page width and height, for the UI overlay |

## Layout box object

One element of `layout_boxes[]`, the detector output before recognition: `label` (string), `score` (float), `bbox_px` (array of 4 floats). Per-block detection scores live here rather than on the block, joined by label and box, because recognition does not return a score.

## Document markdown

`document/<doc_id>-ocr.md` contains a short front matter and one section per page in ascending order:

```
# <doc_id>

- source pdf: ...
- pdf sha256: ...
- pages: 8 (8 parsed ok)
- blocks: 121
- characters: 8430

<!-- page: 1 -->
<page 1 markdown>
<!-- page: 2 -->
...
```

The `<!-- page: N -->` markers are the anchor the UI uses to jump from a citation to the page. Page markdown can contain `imgs/...` image references exported by PaddleX that this pipeline does not write; the citation overlay should use `images/<doc>.p<NNN>.webp` plus `bbox_norm` instead, and the assembler may strip those references later.

## Chunk record (proposed, `vt-chunk-record/1`)

Chunking is owned by `src/verifiable_tutor/corpus/` and is not implemented yet. The planned record keeps every chunk traceable to a page and a box:

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | `vt-chunk-record/1` |
| `chunk_id` | string | Stable id, for example `sha256(doc_id):p<NNN>:c<NN>` |
| `doc_id`, `page_no` | string, integer | Source page |
| `chunk_index` | integer | Order inside the page |
| `section_title` | string or null | Nearest preceding `paragraph_title` block |
| `text` | string | Chunk text with table and formula content kept inline |
| `markdown` | string or null | Optional markdown version for display |
| `block_ids` | array of integer | Source blocks, so a quote maps back to boxes |
| `label_types` | array of string | Labels included, for example `text`, `table` |
| `bbox_union_px` | array of 4 floats | Union of the member boxes in page pixels |
| `bbox_union_norm` | array of 4 floats | Union normalised for the citation overlay |
| `page_image`, `page_webp` | string | Page image references for the citation panel |
| `pdf_sha256` | string | Corpus hash |
| `pipeline_version`, `layout_model`, `recognition_model` | string | Provenance |
| `token_estimate` | integer | Approximate tokens, for budget accounting |
| `tags` | array of string | Inherited request or page tags |
| `created_at` | string | ISO-8601 timestamp |

Chunking rules for the first implementation: split at `paragraph_title` boundaries, keep each `table`, `display_formula` and `image` block whole, target 256 to 512 tokens, and never merge across pages. Retrieval adds derived data outside this record: the FTS5 row id and BM25 index, and the dense vector row position in the NumPy array plus its row map. Those index files live under `USERDIR/index/`, not in the chunk record.

## Relationship to ADR-0002

ADR-0002 describes the output in conceptual terms and names separate `figures[]`, `tables[]` and `formulas[]` arrays. The implemented record keeps one `blocks[]` array with a `label` field, and raw detector scores in `layout_boxes[]`; figure crops are not emitted yet, because the page WebP plus `bbox_norm` covers the citation use case. If figure crops become a requirement, they are appended as `figures[]` with `block_id`, `label`, `crop_path`, and `bbox_px` under a `vt-page-record/2` version.
