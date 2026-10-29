# PaddleOCR-VL parsing requests and responses

Reference for constructing a PaddleOCR-VL parsing request and reading its response. It covers the four invocation surfaces in the official PaddleOCR documentation, the page result schema they share, and the way this project consumes that schema. It does not argue the OCR decision ([ADR-0002](adr/0002-ocr-on-tacc-with-paddleocr-vl.md)) and does not repeat TACC measurements ([tacc-notes.md](tacc-notes.md)).

The field names below are the wire names, not Python names, unless a column says otherwise. Shapes were verified against the PaddleOCR 3.x documentation (main branch at commit `dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf`, 2026-09-16) and the PaddleX `v3.7.2` source, which matches the PaddleOCR 3.7.0 and PaddleX 3.7.2 packages installed in this project's environment ([tacc-notes.md](tacc-notes.md#verification-spike-results-2026-10-29)). The source table in section 8 lists every reference, and each DTO names the source that owns it.

## 1. Choosing a surface

| Surface | Transport | Stages the caller runs | Recognition backend | Used by this project |
|---|---|---|---|---|
| A. Local Python pipeline | in process | data loading, layout, recognition | local Paddle model or remote VLM | yes, the TACC OCR job |
| B. VLM recognition service | HTTP, OpenAI-compatible chat | data loading and layout | vLLM, SGLang, FastDeploy, MLX-VLM, llama.cpp | yes, indirectly through A; the recognition probe calls it directly |
| C. Self-hosted parsing service | HTTP, JSON | none, the server runs the full pipeline | vLLM or FastDeploy behind PaddleX serving | no, available if OCR moves to a hosted server |
| D. Hosted official API | HTTPS, JSON or multipart upload | none, Baidu AI Studio runs the full pipeline | vendor-hosted PaddleOCR-VL | no, external OCR was rejected in ADR-0002 |

Surfaces A, C, and D return the same per-page result schema. Surface B returns plain text, because the caller keeps the layout stage and sends one cropped block at a time. If the goal is page text with block boxes, use A, C, or D; B is an implementation detail behind A.

The project's model is PaddleOCR-VL-1.6, a 0.9B-parameter vision-language model that pairs a NaViT-style dynamic-resolution visual encoder with an ERNIE-4.5-0.3B language model. It handles page-level parsing and element-level recognition (text, tables, formulas, charts, seals, and text spotting), and it shares the 1.5 architecture, so the two generations have identical inference speed ([ALG16](#8-sources-and-versions), [ALG](#8-sources-and-versions)). The `pipeline_version` value selects the generation: `v1`, `v1.5`, or `v1.6`, with `v1.6` the default. Two defaults shape the response: chart recognition is off unless enabled, and layout detection can be turned off entirely for non-standard images such as receipts or ID cards ([ALG](#8-sources-and-versions) FAQ).

Two one-line constructions decide which surface is available:

- A and C run the whole pipeline: data loading, layout detection through PaddlePaddle, and recognition through a VLM. In A the caller runs it; in C a server runs it. A can point its recognition stage at a remote service with `vl_rec_backend` and `vl_rec_server_url`, which is the configuration the TACC job uses. D runs the same pipeline on vendor hardware.
- B needs only a VLM inference server, and the official docs state that such a server provides no end-to-end document parsing API and should not be called with plain HTTP clients or OpenAI clients to parse documents ([TUT](#8-sources-and-versions) §3.1). The project calls it directly only in `tacc/pdf-parse/_staged/recognition_probe.py` to prove the server works.

## 2. The shared page result

### 2.1 Wrapper and top-level fields

Surface A returns a `Result` object whose `json` attribute is a dict with one top-level key, `res`. The same object is written by `save_to_json()`. Surface C and D return the same object as `prunedResult` after recursively removing two keys, `input_path` and `page_index` (TUT §4.3; PX-COMMON `prune_result`).

Source: TUT §2.2 and the PaddleX `paddlex/inference/pipelines/paddleocr_vl/result.py` `_to_json` method ([PX-RESULT](#8-sources-and-versions)).

| Field | Type | Present | Meaning |
|---|---|---|---|
| `input_path` | string or null | A only | Input path recorded by the pipeline; null for array input |
| `page_index` | integer or null | A only | Page number when the input is a PDF, otherwise null |
| `page_count` | integer or null | A, C, D | Page count of the input PDF, otherwise null |
| `width` | integer | A, C, D | Width of the parsed page image in pixels |
| `height` | integer | A, C, D | Height of the parsed page image in pixels |
| `model_settings` | object (`ModelSettings`) | A, C, D | Effective settings used for this page |
| `doc_preprocessor_res` | object or absent | when document preprocessing is enabled | Output of orientation classification and unwarping |
| `layout_det_res` | object or absent | when layout detection is enabled | Layout boxes in page coordinates |
| `parsing_res_list` | array of `ParsingBlock` | A, C, D | Blocks in reading order |
| `spotting_res` | object or array, absent | when a spotting block was recognized | Text spotting result, added by the PaddleX pipeline |

`page_count` and the pixel dimensions are part of the saved JSON in the source, but the tutorial's `save_to_json` field list omits them (section 3.4). Use the source as the shape of record for A, C, and D.

### 2.2 `ModelSettings`

Source: PX-PIPE `predict` and `get_model_settings`; TUT §2.2 documents a subset.

| Field | Type | Meaning |
|---|---|---|
| `use_doc_preprocessor` | boolean | Whether orientation classification or unwarping ran |
| `use_layout_detection` | boolean | Whether layout detection ran |
| `use_chart_recognition` | boolean | Whether chart parsing ran |
| `use_seal_recognition` | boolean | Whether seal recognition ran |
| `use_ocr_for_image_block` | boolean | Whether text inside image blocks was OCRed |
| `format_block_content` | boolean | Whether `block_content` is Markdown-formatted |
| `merge_layout_blocks` | boolean | Whether adjacent layout boxes were merged |
| `markdown_ignore_labels` | array of strings | Labels excluded from Markdown and from reading-order numbering |
| `return_layout_polygon_points` | boolean | Source-added flag; true unless `layout_shape_mode` is `rect` |

The first eight keys are also the settings that change what the response contains, so a stored response is only interpretable together with them.

### 2.3 `LayoutDetectionResult`

Source: TUT §2.2 and the layout detection module page [LAYOUT](#8-sources-and-versions) for the box fields; the nesting comes from PX-RESULT, which stores the layout module's own `res` object.

| Field | Type | Meaning |
|---|---|---|
| `input_path` | string or null | Page image path, null when the input is an array |
| `page_index` | integer or null | Page number for PDF input, otherwise null |
| `boxes` | array of `LayoutBox` | One entry per detected layout region |

`LayoutBox` fields:

| Field | Type | Meaning |
|---|---|---|
| `cls_id` | integer | Class id |
| `label` | string | Class name, for example `text`, `table`, `image` |
| `score` | number | Confidence |
| `coordinate` | array of 4 numbers | `[xmin, ymin, xmax, ymax]` in page pixel coordinates |

### 2.4 `ParsingBlock`

Source: PX-RESULT `_to_json`; TUT §2.2 documents `block_bbox`, `block_label`, `block_content`, `block_id`, and `block_order`.

| Field | Type | Meaning |
|---|---|---|
| `block_label` | string | Layout label of the block, for example `text`, `table`, `image`, `formula` |
| `block_content` | string | Recognized content; Markdown/HTML when `format_block_content` or table post-processing applies |
| `block_bbox` | array of 4 integers | `[xmin, ymin, xmax, ymax]` in page pixel coordinates |
| `block_id` | integer | Zero-based index in `parsing_res_list` |
| `block_order` | integer or null | Reading order, numbered from 1; null for labels excluded from order |
| `group_id` | integer | Group id assigned during block merging; the source falls back to `block_id` |
| `global_block_id`, `global_group_id` | integer, absent by default | Present only for cross-page restructure results |
| `block_polygon_points` | array, absent by default | Present when the layout shape mode is not `rect` |
| `image` | object, absent by default | Present only when the saver is asked to keep block images |

`block_order` is null for the labels in `SKIP_ORDER_LABELS` plus `markdown_ignore_labels`: `figure_title`, `vision_footnote`, `image`, `chart`, `table`, `header`, `header_image`, `footer`, `footer_image`, `footnote`, `aside_text`. The default `markdown_ignore_labels` is `number`, `footnote`, `header`, `header_image`, `footer`, `footer_image`, `aside_text` (PX-CONFIG). Numbering restarts at 1 on every page and follows `parsing_res_list` order for the labels that are not skipped.

`block_bbox` is a list of integers in the saved JSON because NumPy arrays are converted on save; the in-memory value is a NumPy array. Coordinates are relative to the page image that was parsed, not to the original PDF points.

### 2.5 Markdown view

The same blocks also produce a Markdown rendering, which is what this project stores for the corpus.

| Surface | Where it appears | Fields |
|---|---|---|
| A | `Result.markdown` attribute and `save_to_markdown()` file | `markdown_texts`, `markdown_images`, `page_continuation_flags` |
| C and D | `layoutParsingResults[i].markdown` | `text`, `images` |

`markdown_images` maps relative image paths to PIL images in A; C encodes them as Base64 strings by default; D returns pre-signed URLs in the examples; C switches to URLs when URL-return mode is on. `page_continuation_flags` is a pair of booleans for whether the first block starts a paragraph and the last block ends one ([TUT](#8-sources-and-versions) §2.2).

### 2.6 Illustrative shape

Values below are placeholders, not a measured output. The keys and nesting are what matters.

```json
{
  "res": {
    "input_path": "course_project.pdf",
    "page_index": 0,
    "page_count": 8,
    "width": 1654,
    "height": 2339,
    "model_settings": {
      "use_doc_preprocessor": false,
      "use_layout_detection": true,
      "use_chart_recognition": false,
      "use_seal_recognition": false,
      "use_ocr_for_image_block": false,
      "format_block_content": false,
      "merge_layout_blocks": true,
      "markdown_ignore_labels": ["number", "footnote", "header", "header_image", "footer", "footer_image", "aside_text"]
    },
    "layout_det_res": {
      "input_path": "course_project.pdf",
      "page_index": 0,
      "boxes": [
        {"cls_id": 2, "label": "text", "score": 0.98, "coordinate": [34.1, 349.9, 358.6, 611.1]}
      ]
    },
    "parsing_res_list": [
      {
        "block_label": "text",
        "block_content": "Example paragraph.",
        "block_bbox": [34, 349, 358, 611],
        "block_id": 0,
        "block_order": 1,
        "group_id": 0
      }
    ]
  }
}
```

## 3. Surface A: the local Python pipeline

### 3.1 Constructing the pipeline

`PaddleOCRVL(**kwargs)` loads the layout model locally and either loads the VLM locally or points recognition at a service. The tutorial documents the full constructor in §2.2; the parameters that shape requests and responses are below.

| Parameter | Type | Default | Effect on the request or response |
|---|---|---|---|
| `pipeline_version` | string | `"v1.6"` | Selects the PaddleOCR-VL model generation; values are `"v1"`, `"v1.5"`, `"v1.6"` |
| `layout_detection_model_name` | string or null | null, pipeline config decides (the PaddleX default config uses `PP-DocLayoutV2`; the PaddleOCR 1.6 serving config uses `PP-DocLayoutV3`) | Layout model; the source accepts `PP-DocLayoutV2` and `PP-DocLayoutV3` |
| `layout_detection_model_dir` | string or null | null, downloaded | Local layout weights |
| `layout_threshold` | number, dict, or null | null, pipeline config decides (per class in the PaddleX default config; scalar 0.3 in the PaddleOCR 1.6 serving config) | Layout score threshold, one value or per class id |
| `layout_nms` | boolean or null | null, config `true` | Whether NMS runs on layout boxes |
| `layout_unclip_ratio` | number, pair, or dict, or null | null, config `[1.0, 1.0]` | Box expansion factor |
| `layout_merge_bboxes_mode` | string, dict, or null | null, config per class | `large`, `small`, or `union` |
| `vl_rec_backend` | string or null | null, local model | `vllm-server`, `sglang-server`, `fastdeploy-server`, `mlx-vlm-server`, or `llama-cpp-server` |
| `vl_rec_server_url` | string or null | null | Base URL of the recognition service, including `/v1` |
| `vl_rec_api_model_name` | string or null | null | Model id expected by the service |
| `vl_rec_api_key` | string or null | null | Key for a managed service |
| `vl_rec_max_concurrency` | integer or null | null | Maximum in-flight recognition requests |
| `use_doc_orientation_classify` | boolean or null | null, config `false` | Enables orientation classification; the preprocessor sub-pipeline must be loaded in the pipeline config |
| `use_doc_unwarping` | boolean or null | null, config `false` | Enables unwarping; the preprocessor sub-pipeline must be loaded in the pipeline config |
| `use_layout_detection` | boolean or null | null, config `true` | If false, the page is one block and `prompt_label` selects the task |
| `use_chart_recognition` | boolean or null | null, config `false` | Whether chart blocks are parsed instead of kept as images |
| `use_seal_recognition` | boolean or null | null, config `false` | Whether seal blocks are parsed as text |
| `use_ocr_for_image_block` | boolean or null | null, config `false` | Whether image blocks are treated as text to OCR |
| `format_block_content` | boolean or null | null, config `false` | Whether `block_content` is converted to Markdown-style text |
| `merge_layout_blocks` | boolean or null | null, config `true` | Whether adjacent layout boxes are merged before recognition |
| `markdown_ignore_labels` | list or null | null, config list | Labels excluded from Markdown and reading order |
| `use_queues` | boolean or null | null, config `true` | Threaded pipeline stages for multi-page input |
| `device` | string or null | null, GPU 0 if available else CPU | Inference device, for example `cpu`, `gpu:0` |
| `cpu_threads` | integer | 10 | CPU threads for layout detection |

The project's TACC job sets `pipeline_version="v1.6"`, `device="cpu"`, `layout_detection_model_name="PP-DocLayoutV2"`, `layout_threshold=0.3`, `vl_rec_backend="vllm-server"`, `vl_rec_server_url`, `vl_rec_api_model_name`, `vl_rec_max_concurrency=8`, and disables both document preprocessor modules (`scripts/tacc/ocr_pages.py`). Passing the preprocessor flags as false avoids loading the two extra models on the CPU-only layout stage.

### 3.2 Constructing the prediction call

`predict()` returns a list of results, one per page or image; `predict_iter()` returns the same results as a generator. The call accepts input and per-call overrides of the constructor settings. Source: TUT §2.2 `predict` table and PX-PIPE.

`input` accepts:

- a NumPy array of image data;
- a string path to an image or a PDF, a URL to an image or a PDF, or a directory of images (a directory of PDFs is not supported);
- a list of any of the above.

Per-call parameters:

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `input` | array, string, or list | required | Page image, image path, PDF path, URL, or directory |
| `use_doc_orientation_classify` | boolean or null | null | Overrides the constructor value |
| `use_doc_unwarping` | boolean or null | null | Overrides the constructor value |
| `use_layout_detection` | boolean or null | null | Overrides the constructor value |
| `use_chart_recognition` | boolean or null | null | Overrides the constructor value |
| `use_seal_recognition` | boolean or null | null | Overrides the constructor value |
| `use_ocr_for_image_block` | boolean or null | null | Overrides the constructor value |
| `layout_threshold` | number, dict, or null | null | Overrides the constructor value |
| `layout_nms` | boolean or null | null | Overrides the constructor value |
| `layout_unclip_ratio` | number, pair, dict, or null | null | Overrides the constructor value |
| `layout_merge_bboxes_mode` | string, dict, or null | null | Overrides the constructor value |
| `layout_shape_mode` | string | `"auto"` | `rect`, `quad`, `poly`, or `auto`; also controls polygon points in the JSON |
| `prompt_label` | string or null | null, treated as `"ocr"` | Task for a block when layout detection is off |
| `format_block_content` | boolean or null | null | Overrides the constructor value |
| `repetition_penalty` | number or null | null | Recognition sampling parameter |
| `temperature` | number or null | null | Recognition sampling parameter |
| `top_p` | number or null | null | Recognition sampling parameter |
| `min_pixels` | integer or null | null, pipeline default 112896 | Minimum VLM input pixels |
| `max_pixels` | integer or null | null, pipeline default 1003520 | Maximum VLM input pixels |
| `max_new_tokens` | integer or null | null, pipeline default 4096 | Maximum generated tokens |
| `merge_layout_blocks` | boolean or null | null | Overrides the constructor value |
| `markdown_ignore_labels` | list or null | null | Overrides the constructor value |
| `vlm_extra_args` | dict or null | null | Per-element pixel budgets, see section 4.3 |

When `use_layout_detection=False`, the pipeline builds one synthetic layout box covering the whole page whose `label` is `prompt_label` and whose `score` is 1 (PX-PIPE). The response then has one parsing block with the page-level bbox. This is the mode the official FAQ recommends for non-standard images such as receipts and ID cards ([ALG](#8-sources-and-versions) FAQ).

### 3.3 Reading the response

Each result is a `Result` object with three accessors and several savers (TUT §2.2):

| Accessor or method | Returns or writes |
|---|---|
| `result.json` | dict `{"res": <page result>}`; identical content to `save_to_json()` |
| `result.img` | dict of visualization images: `layout_det_res`, `overall_ocr_res`, `text_paragraphs_ocr_res`, `formula_res_region1`, `table_cell_img`, `seal_res_region1`, depending on enabled modules |
| `result.markdown` | dict with `markdown_texts`, `markdown_images`, `page_continuation_flags` |
| `save_to_json(save_path)` | JSON file; a directory argument writes `<input_basename>_res.json` |
| `save_to_markdown(save_path)` | Markdown file per page; a directory argument writes `<input_basename>.md` |
| `save_to_img(save_path)` | Visualization images, PNG |
| `save_to_html(save_path)` | HTML for tables |
| `save_to_xlsx(save_path)` | XLSX for tables |
| `save_to_word(save_path)` | DOCX for the page |

NumPy arrays become JSON lists on save, so `block_bbox` and `coordinate` are lists in the file and arrays in memory. `save_to_markdown()` accepts `pretty` and `show_formula_number`; `save_to_json()` accepts `indent` and `ensure_ascii`.

For a multi-page PDF, `restructure_pages()` accepts the list of page results and returns restructured results. Parameters are `merge_tables` (default true), `relevel_titles` (default true), and `concatenate_pages` (default false). Restructured blocks gain `global_block_id` and `global_group_id` (PX-RESULT).

### 3.4 What the tutorial leaves out

The tutorial's `save_to_json` section lists `input_path`, `page_index`, `model_settings`, `doc_preprocessor_res`, and `parsing_res_list` only. The source writes more, and the extra fields are the ones the citation panel needs:

- `page_count`, `width`, and `height` at the top level.
- `layout_det_res` with the layout boxes.
- `block_id`, `block_order`, and `group_id` on each parsing block, plus optional `global_block_id`, `global_group_id`, and `block_polygon_points`.

The tutorial's printed-output list does include `width`, `height`, and `page_count`, so the omission is in the file-format section, not in the pipeline behavior. Treat this document's field table as the file shape.

### 3.5 Project use

The TACC OCR stage helper calls the pipeline once per rendered page, saves the raw JSON, and maps fields into the project's `vt-page-record/1` record (`scripts/tacc/ocr_pages.py`, extracted from the week-one spike at `tacc/ocr-smoke/`):

```python
from paddleocr import PaddleOCRVL

pipeline = PaddleOCRVL(
    pipeline_version="v1.6",
    device="cpu",
    layout_detection_model_name="PP-DocLayoutV2",
    layout_threshold=0.3,
    vl_rec_backend="vllm-server",
    vl_rec_server_url="http://127.0.0.1:8000/v1",
    vl_rec_api_model_name="PaddleOCR-VL-1.6-0.9B",
    vl_rec_max_concurrency=8,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
)

result = next(iter(pipeline.predict("page.png")))
raw = result.json          # {"res": {...}}
payload = raw["res"]
blocks = payload["parsing_res_list"]
```

Two project-specific notes: the helper accepts either a `_res.json` file or the in-memory `json` attribute because `save_to_json()` naming differs between directory and file arguments; and the pipeline reads `payload["parsing_res_list"]` and `payload["layout_det_res"]["boxes"]` rather than the Markdown rendering.

## 4. Surface B: the VLM recognition service

### 4.1 Starting and addressing the service

The project runs the recognition model under vLLM 0.26.0 on one RTX 3090. The vLLM recipe gives the launch command ([VLLM](#8-sources-and-versions)):

```bash
vllm serve PaddlePaddle/PaddleOCR-VL \
    --trust-remote-code \
    --max-num-batched-tokens 16384 \
    --no-enable-prefix-caching \
    --mm-processor-cache-gb 0
```

The project additionally sets `--served-model-name PaddleOCR-VL-1.6-0.9B` and `--max-model-len 32768`; the recipe notes that clients must use a served name that the server reports when the default name cannot be resolved. The OpenAI base URL is `http://<host>:<port>/v1`; the API key is a placeholder such as `EMPTY`.

`paddleocr genai_server --model_name PaddleOCR-VL-1.6-0.9B --backend vllm --port 8118` starts the same kind of recognition-only server through PaddleOCR's own wrapper. The tutorial is explicit that this service covers only the VLM stage and provides no document parsing API, and it discourages direct HTTP or OpenAI calls to it ([TUT](#8-sources-and-versions) §3.1). Use it as the back end of surface A, not as a parsing endpoint.

### 4.2 Request

Source: PX-PRED `_doc_vlm_genai_build_request_specs`; prompt strings from PX-PIPE and [VLLM](#8-sources-and-versions).

```http
POST {base_url}/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json
```

| Field | Type | Value the PaddleOCR client sends |
|---|---|---|
| `model` | string | `vl_rec_api_model_name`, or the served model name |
| `messages` | array | One user message whose content array is the image followed by the text prompt |
| `messages[0].content[0]` | object | `{"type": "image_url", "image_url": {"url": <URL or data URI>}}` |
| `messages[0].content[1]` | object | `{"type": "text", "text": <prompt string>}` |
| `temperature` | number | 0 if not configured |
| `top_p` | number | Sent only when configured |
| `max_completion_tokens` | integer | `max_new_tokens`; the pipeline path defaults to 4096 |
| `extra_body.skip_special_tokens` | boolean | True unless the page contains a spotting block |
| `extra_body.repetition_penalty` | number | Sent only when configured |
| `extra_body.mm_processor_kwargs.min_pixels` | integer | Sent only when configured, `vllm-server` backend only |
| `extra_body.mm_processor_kwargs.max_pixels` | integer | Sent only when configured, `vllm-server` backend only |

The image is sent as a Base64 JPEG data URI by the PaddleOCR client (`data:image/jpeg;base64,...`), or as an `http(s)` URL when the caller passed a URL. The project's recognition probe uses the same data-URI form with a PNG and the prompt `OCR:`.

Direct callers can use the OpenAI field `max_tokens` instead of `max_completion_tokens`; the project probe does so and the vLLM server accepts it. The PaddleOCR tutorial describes no direct-call contract for its own server and discourages direct calls, while the vLLM recipe does show direct OpenAI calls to a vLLM-served model, so treat field compatibility as a property of the served API rather than a documented PaddleOCR contract.

### 4.3 Prompts and pixel budgets

The pipeline maps each layout label to a fixed prompt (PX-PIPE). This mapping is the normalization the recognition stage depends on; direct callers must reproduce it if they want the same output as surface A.

| Layout label | Prompt text | Prompt value in `prompt_label` | Default pixel range |
|---|---|---|---|
| Text-like labels (`text`, `aside_text`, `paragraph_title`, `doc_title`, and similar) | `OCR:` | `ocr` | 112896 to 1003520 |
| `table` | `Table Recognition:` | `table` | 112896 to 1003520 |
| `chart` with `use_chart_recognition` on | `Chart Recognition:` | `chart` | 112896 to 1003520 |
| Labels containing `formula`, except `formula_number` | `Formula Recognition:` | `formula` | 112896 to 1003520 |
| `spotting` | `Spotting:` | `spotting` | 112896 to 1605632 |
| `seal` with `use_seal_recognition` on | `Seal Recognition:` | `seal` | 112896 to 1003520 |

Image-like labels (`image`, `header_image`, `footer_image`) are not sent to the VLM; they are carried as images, and their blocks have empty content unless `use_ocr_for_image_block` is enabled. Chart and seal blocks are treated the same way when their recognition flags are off.

`vlm_extra_args` overrides the pixel range per element type: `ocr_min_pixels`, `ocr_max_pixels`, `table_min_pixels`, `table_max_pixels`, `chart_min_pixels`, `chart_max_pixels`, `formula_min_pixels`, `formula_max_pixels`, `seal_min_pixels`, `seal_max_pixels` ([TUT](#8-sources-and-versions) §2.2). The spotting defaults come from PX-PIPE and match the model card's spotting recommendation ([HF](#8-sources-and-versions)).

Table output is post-processed from the model's OTSL tokens into HTML before it lands in `block_content`; spotting output retains special tokens and is parsed into `spotting_res`. Raw recognition text alone is not the finished block content.

### 4.4 Response

The service is an OpenAI-compatible chat completion. The PaddleOCR client reads exactly one field:

| Path | Type | Meaning |
|---|---|---|
| `choices[0].message.content` | string | Recognized text for the block |

Other OpenAI fields (`id`, `model`, `usage`, `finish_reason`) are present but unused by the PaddleOCR client. The client waits 600 seconds per request and collects responses in submission order (PX-PRED).

## 5. Surface C: the self-hosted parsing service

### 5.1 Deployment and endpoints

Two deployment paths produce the same API ([TUT](#8-sources-and-versions) §4):

- Docker Compose: the `paddleocr-vl-api` container listens on host port 8080 and calls an internal `paddleocr-vlm-server` container.
- Manual: `paddlex --install serving`, then `paddlex --serve --pipeline PaddleOCR-VL`. Port 8080 by default, options `--device`, `--host`, `--port`, `--use_hpip`, `--hpi_config`.

For higher concurrency than the basic service, the docs point to the high-performance serving stack, which exposes the same two endpoints through a FastAPI gateway in front of Triton and vLLM.

| Method | Path | Purpose |
|---|---|---|
| POST | `/layout-parsing` | Parse one image, PDF, or multi-page TIFF |
| POST | `/restructure-pages` | Restructure previously parsed pages |
| GET | `/health` | Health check, not part of the tutorial's API section |

There is no path prefix, no multipart form, and no authentication. The file travels inside the JSON request body as a URL or a Base64 string. The server's own docs put it plainly: both request and response bodies are JSON objects, and the request method is POST ([TUT](#8-sources-and-versions) §4.3).

### 5.2 `POST /layout-parsing` request

Source: TUT §4.3 and PX-SCHEMA `InferRequest`. All fields except `file` are optional. HTTP names are camelCase; the Python equivalents are surface A's `predict` parameters.

| Field | Type | Required | Default | Python equivalent |
|---|---|---|---|---|
| `file` | string | yes | none | `input` (path, URL, array, or directory) |
| `fileType` | integer or null | no | inferred from URL | none |
| `useDocOrientationClassify` | boolean or null | no | pipeline config `false` | `use_doc_orientation_classify` |
| `useDocUnwarping` | boolean or null | no | pipeline config `false` | `use_doc_unwarping` |
| `useLayoutDetection` | boolean or null | no | pipeline config `true` | `use_layout_detection` |
| `useChartRecognition` | boolean or null | no | pipeline config `false` | `use_chart_recognition` |
| `useSealRecognition` | boolean or null | no | pipeline config `false` | `use_seal_recognition` |
| `useOcrForImageBlock` | boolean or null | no | pipeline config `false` | `use_ocr_for_image_block` |
| `layoutThreshold` | number, object, or null | no | pipeline config decides (scalar 0.3 in the PaddleOCR 1.6 serving config) | `layout_threshold` |
| `layoutNms` | boolean or null | no | pipeline config `true` | `layout_nms` |
| `layoutUnclipRatio` | number, array, object, or null | no | pipeline config `[1.0, 1.0]` | `layout_unclip_ratio` |
| `layoutMergeBboxesMode` | string, object, or null | no | pipeline config per class | `layout_merge_bboxes_mode` |
| `layoutShapeMode` | string | no | `"auto"` | `layout_shape_mode` |
| `promptLabel` | string or null | no | null, treated as `"ocr"` | `prompt_label` |
| `formatBlockContent` | boolean or null | no | pipeline config `false` | `format_block_content` |
| `repetitionPenalty` | number or null | no | null | `repetition_penalty` |
| `temperature` | number or null | no | null | `temperature` |
| `topP` | number or null | no | null | `top_p` |
| `minPixels` | integer or null | no | null | `min_pixels` |
| `maxPixels` | integer or null | no | null | `max_pixels` |
| `maxNewTokens` | integer or null | no | null | `max_new_tokens` |
| `mergeLayoutBlocks` | boolean or null | no | pipeline config `true` | `merge_layout_blocks` |
| `markdownIgnoreLabels` | array or null | no | pipeline config list | `markdown_ignore_labels` |
| `vlmExtraArgs` | object or null | no | null | `vlm_extra_args` |
| `prettifyMarkdown` | boolean | no | `true` | `save_to_markdown(pretty=...)` |
| `showFormulaNumber` | boolean | no | `false` | `save_to_markdown(show_formula_number=...)` |
| `restructurePages` | boolean | no | `false` | `restructure_pages(...)` |
| `mergeTables` | boolean | no | source `true` | `merge_tables` |
| `relevelTitles` | boolean | no | source `true` | `relevel_titles` |
| `returnMarkdownImages` | boolean | no | `true` | none |
| `outputFormats` | array or null | no | none, only `"docx"` accepted | none |
| `visualize` | boolean or null | no | config `Serving.visualize`, else images returned | none |
| `logId` | string or null | no, source only | none, server generates a UUID | none |

Construction rules that are easy to get wrong:

- `file` is either an `http(s)` URL that the server fetches, or the Base64 encoding of the file bytes. A local path is not a valid value; the server tries to Base64-decode any non-URL string, so a path fails as an invalid file. Data URIs are not documented.
- `fileType` is required when `file` is Base64 and there is no URL to infer from: `0` means PDF, `1` means image including TIFF. When `file` is a URL, the type is inferred from the URL's MIME type and a missing or unsupported type is a 422.
- `useDocOrientationClassify` and `useDocUnwarping` need the document preprocessor to be present in the loaded pipeline. The shipped pipeline configuration sets `use_doc_preprocessor: False`, so a request that enables them fails with a 500 whose `errorMsg` reports that the model settings are invalid, unless the service was started with a config that enables the preprocessor.
- `promptLabel` is accepted only in lower case: `ocr`, `formula`, `table`, `chart`, `seal`, `spotting`. It takes effect only when `useLayoutDetection` is false.
- `outputFormats` accepts only `"docx"`; other values are rejected before the pipeline runs.
- Constraint checks in the source: `topP` must be greater than 0 and at most 1; `temperature` must be at least 0; `repetitionPenalty` must be greater than 0; `minPixels` and `maxPixels` must be greater than 0 and `minPixels` must not exceed `maxPixels`; `layoutThreshold` values must be between 0 and 1; `layoutUnclipRatio` values must be greater than 0; `layoutMergeBboxesMode` must be `large`, `small`, or `union`.

### 5.3 `POST /layout-parsing` response

Source: TUT §4.3 and PX-SCHEMA `InferResult`.

The success envelope is:

| Field | Type | Value |
|---|---|---|
| `logId` | string | Request id; the request's `logId` when supplied, otherwise a generated UUID |
| `errorCode` | integer | `0` |
| `errorMsg` | string | `"Success"` |
| `result` | object | `InferResult` |

`result` has two fields:

| Field | Type | Meaning |
|---|---|---|
| `layoutParsingResults` | array of `LayoutParsingResult` | One element for an image; one element per processed page for a PDF, in page order |
| `dataInfo` | object | Input metadata: `{"type": "image", "width": ..., "height": ...}`, `{"type": "pdf", "numPages": ..., "pages": [{"width": ..., "height": ...}, ...]}`, or the TIFF variant with `"tiff"` |

Each `LayoutParsingResult` has:

| Field | Type | Meaning |
|---|---|---|
| `prunedResult` | object | The page result from section 2 with `input_path` and `page_index` removed at every nesting level (PX-COMMON) |
| `markdown` | object | `text` string, `images` map of relative path to Base64 or URL, or absent/null when `returnMarkdownImages` is false |
| `outputImages` | object or absent | Visualization images keyed like `Result.img` minus the input image; absent when `visualize` is off |
| `inputImage` | string or absent | Input page image, Base64 or URL |
| `exports` | object or absent | Present only with `outputFormats`; `{"docx": {"content": "...", "fileName": "..."}}` |

Because `page_index` is stripped from `prunedResult`, the page number is recoverable only from the array index; `dataInfo.numPages` is the processed page count and `dataInfo.pages` gives per-page pixel sizes, not page numbers. Fields whose value is null are omitted from the response, not serialized as null (PX-FASTAPI sets `response_model_exclude_none=True`). The docs say "null or omitted"; prefer treating the key as absent.

Images are Base64 by default. With `Serving.return_urls: true` and a `bos` file storage configured under `Serving.extra`, the same image fields become pre-signed URLs while the JSON types stay strings ([SERVING](#8-sources-and-versions)). The hosted services use that URL mode, which is why their examples download images with a GET.

### 5.4 `POST /restructure-pages` request and response

Source: TUT §4.3 and PX-SCHEMA `RestructurePagesRequest`.

The request passes back the pieces needed to rebuild pages, so it carries no `file` or `visualize`:

| Field | Type | Required | Default |
|---|---|---|---|
| `pages` | array of `{prunedResult, markdownImages}` | yes | none |
| `mergeTables` | boolean | no | source `true` |
| `relevelTitles` | boolean | no | source `true` |
| `concatenatePages` | boolean | no | source `false` |
| `prettifyMarkdown` | boolean | no | `true` |
| `showFormulaNumber` | boolean | no | `false` |
| `returnMarkdownImages` | boolean | no | `true` |
| `outputFormats` | array or null | no | none, only `"docx"` |
| `logId` | string or null | no | none |

`pages[i].prunedResult` is the object returned by `/layout-parsing`; `pages[i].markdownImages` is that page's `markdown.images`. The response envelope is the same; `result.layoutParsingResults` holds restructured pages. With `concatenatePages=true` the array has one element, otherwise one element per input page. Restructured elements carry `prunedResult` and `markdown`, plus `exports` when requested, without `outputImages` or `inputImage`.

### 5.5 Errors

Source: TUT §4.3 for the envelope and `errorCode == status code`; PX-FASTAPI for the handler bodies.

| Status | Body | When |
|---|---|---|
| 200 | `{logId, errorCode: 0, errorMsg: "Success", result}` | Parsed |
| 422 | `{logId, errorCode: 422, errorMsg: "<JSON-encoded error list>"}` | Request validation failed; the list entries look like `{"type", "loc", "msg"}` |
| 422 | `{logId, errorCode: 422, errorMsg: "Invalid input file"}` | The file bytes could not be read |
| 422 | `{logId, errorCode: 422, errorMsg: "Unsupported file type"}` | URL MIME type is not PDF or image |
| 422 | `{logId, errorCode: 422, errorMsg: "File type cannot be determined"}` | Non-URL file without `fileType` |
| 422 | `{logId, errorCode: 422, errorMsg: "<pixel limit message>"}` | Decoded image exceeds the pixel limit |
| 500 | `{logId, errorCode: 500, errorMsg: "<pipeline error>"}` | The pipeline yielded an error record, for example invalid model settings such as enabling the preprocessor on a pipeline that does not load it |
| 500 | `{logId, errorCode: 500, errorMsg: "Internal server error"}` | An unhandled exception, including one raised during prediction |

The server does not document a request-size limit, a request timeout, or a rate limit. Treat them as unspecified and control them at the client and reverse proxy.

### 5.6 Limits and concurrency

| Limit | Value | Scope |
|---|---|---|
| Pages per request | `Serving.extra.max_num_input_imgs`; source default 10 when the key is absent, shipped Compose config sets null (no limit) | Self-hosted |
| Pages per request | 100 by default, remove with `Serving.extra.max_num_input_imgs: null` | Hosted synchronous API |
| Pages per request | 1000 | Hosted asynchronous API |
| Image pixels | 178,956,970 | Server input decode |
| PDF render scale | 2.0 (144 DPI), minimum 0.1 | Server-side PDF rendering |
| Output image size | resized to fit 2000 by 2000 | Visualization images |
| Concurrent pipeline calls | one at a time by default | Basic serving; HPS raises this |

The numeric limits above come from [PX-COMMON-OCR] (page cap, output-image cap), [PX-RENDER] (input pixel ceiling), and [PX-FLAGS] (render scale, serial-call default); enforcement is in [PX-UTILS]. The 10-page default is a source default for a service started without a config override; the Compose deployment ships `max_num_input_imgs: null`. A whole-corpus request that relies on a default has a silent truncation risk: the server processes the pages it allows and reports the processed count in `dataInfo.numPages`, not the PDF's true page count.

## 6. Surface D: the hosted official API

This path is recorded because the official site documents it and because it is the only path that returns the page result schema without a local GPU. The project does not use it: [ADR-0002](adr/0002-ocr-on-tacc-with-paddleocr-vl.md) rejected external OCR for the corpus build on cost and offline reproducibility.

### 6.1 Authentication and model names

All hosted calls authenticate with an AI Studio access token, exported as `PADDLEOCR_ACCESS_TOKEN` for the SDKs and CLI ([OFFICIAL-API](#8-sources-and-versions)). The HTTP services use `Authorization: Bearer {token}` on the asynchronous API and `Authorization: token {token}` on the legacy synchronous API. Document parsing models are `PaddleOCR-VL`, `PaddleOCR-VL-1.5`, `PaddleOCR-VL-1.6`, and `PP-StructureV3`; the default for document parsing is `PaddleOCR-VL-1.6`.

### 6.2 Synchronous hosted endpoint

The AI Studio PaddleOCR-VL API takes the same request body shape and returns the same envelope as surface C: `POST <API_URL>` with `file` as Base64, `fileType` 0 or 1, and a subset of the same optional camelCase payload (for example `useDocOrientationClassify`, `useChartRecognition`, `layoutThreshold`, `restructurePages`, `prettifyMarkdown`), returning `result.layoutParsingResults` and `result.dataInfo` ([HOSTED](#8-sources-and-versions)). `API_URL` is issued per account from the AI Studio PaddleOCR task page, so it is not a fixed public path. The default page limit is 100 pages.

### 6.3 Asynchronous hosted API

The current documented job API is asynchronous ([ASYNC](#8-sources-and-versions)):

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v2/ocr/jobs` | Submit a parsing job |
| GET | `/api/v2/ocr/jobs/{jobId}` | Poll state and result location |
| GET | `/api/v2/ocr/jobs/batch/{batchId}` | Batch status |

Base URL: `https://paddleocr.aistudio-app.com/`. Submission has two body forms:

- URL mode, `Content-Type: application/json`: `{"fileUrl": "...", "model": "PaddleOCR-VL-1.6", "optionalPayload": {...}, "pageRanges": "2,4-6", "batchId": "..."}`. File size up to 200 MB.
- Local upload mode, `Content-Type: multipart/form-data`: form fields `file` (the bytes), `model`, `optionalPayload` as a JSON string, and the optional fields. File size up to 50 MB.

The submission response is `{traceId, code, msg, data: {jobId}}`; `code` is 0 on success. Polling returns `{traceId, code, msg, data}` where `data.state` is `pending`, `running`, `done`, or `failed`, `data.errorMsg` explains a failure, `data.resultUrl` holds `jsonUrl` and `markdownUrl` when done, and `data.extractProgress` reports `startTime`, `endTime`, `totalPages`, and `extractedPages`. Fetch `jsonUrl` as JSONL, one line per page: each line is `{"result": {"layoutParsingResults": [...]}}`, using the same page element as surface C. The hosted response mode returns image fields as URLs, so the client downloads them rather than Base64-decoding them.

Error codes at the envelope level are integers with meanings such as 401 invalid token, 10002 unrecognized file URL, 10004 unsupported format, 10006 page limit exceeded, 10007 model error, 11001 unknown job id, 11003 parsing failed, 12002 rate limited. The full table is in [ASYNC](#8-sources-and-versions).

### 6.4 SDK and CLI

The `paddleocr` package ships `PaddleOCRClient` and `AsyncPaddleOCRClient`. The construction that matters is:

```python
from paddleocr import Model, PaddleOCRClient

client = PaddleOCRClient(request_timeout=300.0, poll_timeout=600.0)
result = client.parse_document(file_path="in.pdf", model=Model.PADDLE_OCR_VL_16)
print(result.job_id, len(result.pages))
```

`parse_document`, `submit_document_parsing`, `wait_document_parsing_result`, and `get_status` wrap the job API; `save_document_parsing_result_resources` downloads referenced images. Options are passed through `PaddleOCRVLOptions` (snake_case in Python, camelCase on the wire): `use_layout_detection`, `use_chart_recognition`, `temperature`, `prettify_markdown` are the common ones ([OFFICIAL-API](#8-sources-and-versions)). The CLI equivalent is `paddleocr api --model_type doc_parsing --file_path in.pdf`; output is JSON with `jobId` plus each page's `prunedResult`, `markdownText`, `markdownImages`, and `outputImages`.

## 7. Project construction recipes

### 7.1 Current TACC path

The live path is surface A with surface B behind it: `scripts/tacc/ocr_pages.py` starts or connects to a vLLM server, builds one `PaddleOCRVL` pipeline for the job, calls `predict()` once per rendered page image, writes one JSON record per page, and assembles the document Markdown. The job also stores each page's raw pipeline JSON next to the records, so a later schema check does not require re-running OCR.

### 7.2 Mapping the response onto the project record

The record contract is owned by [corpus-schema.md](corpus-schema.md); this table only maps the response fields onto it. The mapping used by the TACC helper:

| Project record field | Source field |
|---|---|
| `markdown` | `result.markdown["markdown_texts"]` or the saved `.md` file |
| `text` | join of `parsing_res_list[*].block_content` |
| `blocks[*].block_id` | `block_id` |
| `blocks[*].block_order` | `block_order` |
| `blocks[*].label` | `block_label` |
| `blocks[*].content` | `block_content` |
| `blocks[*].bbox_px` | `block_bbox` |
| `blocks[*].bbox_norm` | `block_bbox` divided by `width` and `height` |
| `layout_boxes[*].label` | `layout_det_res.boxes[*].label` |
| `layout_boxes[*].score` | `layout_det_res.boxes[*].score` |
| `layout_boxes[*].bbox_px` | `layout_det_res.boxes[*].coordinate` |
| `pipeline_page_index` | `page_index` |

The project's `page_no` comes from its own render loop, not from `page_index`, because the pipeline PDF page number and the project's PDF page numbering must not be assumed equal.

### 7.3 Pitfalls

- The saved JSON is wrapped in `res`; reading `json["parsing_res_list"]` at the top level returns nothing.
- `page_index` and `input_path` are stripped by the serving surfaces, so a response stored from C or D has no page number unless the array index or `dataInfo` is kept.
- `block_order` is null for skip labels; sorting by `block_order` alone loses table and figure blocks.
- `block_bbox` is in page pixels of the parsed image, which is the rendered page for the project, not the PDF point space.
- `markdown` and `text` differ: Markdown performs table and image formatting and drops ignored labels; use one consistently per use case.
- `model_settings` changes which result fields exist. A parser that expects `layout_det_res` breaks if a later configuration disables layout detection.
- A Base64 request for a 200 DPI page image is about one third larger than the image, and a long PDF request compounds it; the self-hosted service has no documented body limit, so a reverse proxy limit is the practical bound.
- `useDocOrientationClassify` and `useDocUnwarping` fail with a 500 unless the service's pipeline config enables the preprocessor.

### 7.4 If the backend switches to a hosted service

Surface C and D remove the local Paddle install and the GPU. The construction changes are small:

```python
import base64, requests

page_b64 = base64.b64encode(open("page.webp", "rb").read()).decode("ascii")
response = requests.post(
    "http://localhost:8080/layout-parsing",
    json={"file": page_b64, "fileType": 1, "useLayoutDetection": True},
    timeout=600,
)
payload = response.json()
page = payload["result"]["layoutParsingResults"][0]
blocks = page["prunedResult"]["parsing_res_list"]
markdown = page["markdown"]["text"]
```

The page record needed by the corpus is then `blocks` plus `markdown`; the page number must be tracked by the caller, and the same 10-page or 100-page page-limit rule applies depending on the service.

## 8. Sources and versions

Fetched 2026-10-29. Docs are the PaddleOCR 3.x documentation on the main branch at commit `dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf` (2026-09-16); the latest released version at that commit is PaddleOCR 3.7.0, and the `PaddleOCR-VL.en.md` file is identical at the `v3.7.0` tag. Source evidence comes from PaddleX `v3.7.2`, the version installed in the project environment.

| Tag | Source | What it owns |
|---|---|---|
| [TUT] | https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PaddleOCR-VL.html (source: `docs/version3.x/pipeline_usage/PaddleOCR-VL.en.md` at `v3.7.0`) | Surfaces A, B, C: constructor, predict, result methods, serving API |
| [ALG16] | https://www.paddleocr.ai/main/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL-1.6.html | Model generation facts, 0.9B size, 1.6 performance |
| [ALG] | https://www.paddleocr.ai/main/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL.html | Architecture, pipeline stages, FAQ on disabling layout detection |
| [SERVING] | https://www.paddleocr.ai/main/en/version3.x/inference_deployment/serving/serving.html | Self-hosted serving basics, URL-return mode |
| [OFFICIAL-API] | https://www.paddleocr.ai/main/en/version3.x/inference_deployment/serving/paddleocr_official_api/overview.html and `python.html` | Hosted SDK, models, options, errors |
| [HOSTED] | https://ai.baidu.com/ai-doc/AISTUDIO/Vmkz2nz1p | Hosted synchronous `/layout-parsing` API |
| [ASYNC] | https://ai.baidu.com/ai-doc/AISTUDIO/Mml7n69e7 | Hosted asynchronous job API, limits, error codes |
| [VLLM] | https://docs.vllm.ai/projects/recipes/en/latest/PaddlePaddle/PaddleOCR-VL.html | vLLM launch command, direct OpenAI client call, task prompts |
| [HF] | https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6 | Model card, element prompts, spotting pixel guidance |
| [LAYOUT] | https://www.paddleocr.ai/main/en/version3.x/module_usage/layout_detection.html | Layout box fields |
| [PX-RESULT] | `PaddleX v3.7.2 paddlex/inference/pipelines/paddleocr_vl/result.py` | Page JSON construction, block fields, restructure fields |
| [PX-PIPE] | `PaddleX v3.7.2 paddlex/inference/pipelines/paddleocr_vl/pipeline.py` | Label-to-prompt mapping, pixel defaults, synthetic block mode |
| [PX-PRED] | `PaddleX v3.7.2 paddlex/inference/models/doc_vlm/predictor.py` | OpenAI request construction, sampling defaults, timeout |
| [PX-SCHEMA] | `PaddleX v3.7.2 paddlex/inference/serving/schemas/paddleocr_vl.py` | Serving request and response classes |
| [PX-APP] | `PaddleX v3.7.2 paddlex/inference/serving/basic_serving/_pipeline_apps/paddleocr_vl.py` | Serving response construction |
| [PX-COMMON] | `PaddleX v3.7.2 paddlex/inference/serving/basic_serving/_pipeline_apps/_common/common.py` | `prune_result`, recursive removal of `input_path` and `page_index` |
| [PX-COMMON-OCR] | `PaddleX v3.7.2 paddlex/inference/serving/basic_serving/_pipeline_apps/_common/ocr.py` | File error messages, 10-page default, 2000 by 2000 output-image default |
| [PX-FLAGS] | `PaddleX v3.7.2 paddlex/utils/flags.py` | PDF render scale 2.0 and minimum 0.1, serial pipeline-call default |
| [PX-RENDER] | `PaddleX v3.7.2 paddlex/inference/utils/pdf_rendering.py` | Maximum input image pixel count |
| [PX-FASTAPI] | `PaddleX v3.7.2 paddlex/inference/serving/basic_serving/_app.py` | Envelope handlers, error bodies, null omission |
| [PX-UTILS] | `PaddleX v3.7.2 paddlex/inference/serving/infra/utils.py` | File decoding, URL fetch, Base64 decode, page-cap and pixel-limit enforcement |
| [PX-CONFIG] | `PaddleX v3.7.2 paddlex/configs/pipelines/PaddleOCR-VL.yaml` | Shipped pipeline defaults |

Documented versus source-derived in this file:

- Documented by the tutorial: the constructor table, `predict` parameters, result accessors, serving request and response tables, endpoints, and the synchronous envelope.
- Source-derived, because the docs are silent or incomplete: `page_count`, `width`, `height`, and `layout_det_res` in the saved JSON; block `group_id`; the request-side `logId`; `dataInfo` subfields; null-field omission; recursive pruning of `input_path` and `page_index`; the `fileName` field in `docx` exports; file decoding (URL versus Base64); request validation rules; page-cap defaults; the 2000 by 2000 output-image cap; the input pixel ceiling and the PDF render scale; the serial pipeline-call default; error bodies; `skip_special_tokens` and `mm_processor_kwargs` in the OpenAI request.
- Unspecified: request body size limits, request timeouts, rate limits for the self-hosted service, data-URI support in `file`, and the exact rounding of `block_bbox` values.

Documentation disagreements worth knowing:

- The tutorial's `save_to_json` field list omits fields the source writes (section 3.4).
- The tutorial's serving section does not document the request-side `logId`, which the schema accepts.
- The self-hosted page-cap default differs by deployment: the Compose config sets no limit, a bare `paddlex --serve` falls back to the source default of 10, and the hosted synchronous API documents 100.
- The hosted synchronous API docs show images downloaded with GET, while the self-hosted docs describe Base64 defaults; the difference is the configured URL-return mode, not a schema difference.

## 9. References

1. PaddleOCR-VL usage tutorial: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PaddleOCR-VL.html
2. PaddleOCR-VL-1.6 introduction: https://www.paddleocr.ai/main/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL-1.6.html
3. PaddleOCR-VL introduction: https://www.paddleocr.ai/main/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL.html
4. Self-hosted serving guide: https://www.paddleocr.ai/main/en/version3.x/inference_deployment/serving/serving.html
5. PaddleOCR official API overview: https://www.paddleocr.ai/main/en/version3.x/inference_deployment/serving/paddleocr_official_api/overview.html
6. PaddleOCR official API Python SDK: https://www.paddleocr.ai/main/en/version3.x/inference_deployment/serving/paddleocr_official_api/python.html
7. Hosted PaddleOCR-VL API: https://ai.baidu.com/ai-doc/AISTUDIO/Vmkz2nz1p
8. Asynchronous API usage guide: https://ai.baidu.com/ai-doc/AISTUDIO/Mml7n69e7
9. vLLM PaddleOCR-VL recipe: https://docs.vllm.ai/projects/recipes/en/latest/PaddlePaddle/PaddleOCR-VL.html
10. PaddleOCR-VL-1.6 model card: https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6
11. Layout detection module: https://www.paddleocr.ai/main/en/version3.x/module_usage/layout_detection.html

PaddleX source files cited above are under `https://github.com/PaddlePaddle/PaddleX/tree/v3.7.2/paddlex/`.
