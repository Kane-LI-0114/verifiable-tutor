#!/usr/bin/env bash
# TACC whole-document PDF parse job (1 GPU).
#
# One submitted job parses one complete PDF file the way the demo will: copy the
# user file into the job workspace, enumerate every page, render each page at
# 200 DPI, serve PaddleOCR-VL-1.6 with vLLM, run PP-DocLayoutV2 layout on CPU
# plus recognition on the server for every page, and assemble one document
# markdown with per-page markers.
#
# Env knobs: PDF_NAME (default course_project.pdf), PDF_DIR (default
# $TACC_USERDIR/corpus-pdf), SERVED_NAME, VLLM_PORT.
set -u
export PS1="${PS1:-}"

HERE="${TACC_WORKDIR:-$(cd "$(dirname "$0")" && pwd)}"
OUT="${TACC_USERDIR:-$HOME}/pdf-parse"
PDF_NAME="${PDF_NAME:-course_project.pdf}"
PDF_DIR="${PDF_DIR:-${TACC_USERDIR:-$HOME}/corpus-pdf}"
PUBLIC_ROOT="${PUBLIC_ROOT:-/mnt/home/public/course-envs/CSIT6000V/project/qwen3.8-27b-v1}"
JOB="${SLURM_JOB_ID:-manual}"
VLLM_PORT="${VLLM_PORT:-8000}"
SERVED_NAME="${SERVED_NAME:-PaddleOCR-VL-1.6-0.9B}"

# A demo request can override the PDF, its directory, the output directory and
# the page subset through request.json next to this script (written by the local
# interface). Absent that file the job keeps the batch defaults above.
REQUEST_FILE="$HERE/request.json"
REQ_PAGES=""
if [ -f "$REQUEST_FILE" ]; then
    REQ_PDF=$(sed -n 's/.*"pdf_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REQUEST_FILE")
    REQ_DIR=$(sed -n 's/.*"pdf_dir"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REQUEST_FILE")
    REQ_OUT=$(sed -n 's/.*"out_dir"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REQUEST_FILE")
    REQ_DOC_ID=$(sed -n 's/.*"doc_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REQUEST_FILE")
    REQ_PAGES=$(sed -n 's/.*"pages"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REQUEST_FILE")
    if [ -z "$REQ_PAGES" ]; then
        REQ_PAGES=$(sed -n 's/.*"pages"[[:space:]]*:[[:space:]]*\[\([^]]*\)\].*/\1/p' "$REQUEST_FILE" | tr -d ' ')
    fi
    [ -n "$REQ_PDF" ] && PDF_NAME="$REQ_PDF"
    [ -n "$REQ_DIR" ] && PDF_DIR="$REQ_DIR"
    [ -n "$REQ_OUT" ] && OUT="${TACC_USERDIR:-$HOME}/$REQ_OUT"
fi
DOC_ID="${PDF_NAME%.pdf}"
if [ -n "${REQ_DOC_ID:-}" ]; then DOC_ID="$REQ_DOC_ID"; fi
VRAM_CSV="$OUT/logs/vram-${JOB}.csv"

mkdir -p "$OUT" "$OUT/logs" "$OUT/records" "$OUT/pages" "$OUT/images" "$OUT/input" "$OUT/document"
rm -f "$OUT/summary.json" "$OUT/pages.jsonl" "$OUT/document/${DOC_ID}-ocr.md"
LOG="$OUT/pdf-parse-${JOB}.log"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

PASS=0
FAIL=0
RESULTS="$OUT/results-${JOB}.txt"
: > "$RESULTS"
record() {
    local status=$1 name=$2 detail=${3:-}
    printf '%s|%s|%s\n' "$status" "$name" "$detail" >> "$RESULTS"
    if [ "$status" = PASS ]; then PASS=$((PASS + 1)); else FAIL=$((FAIL + 1)); fi
    printf '[result] %s %s %s\n' "$status" "$name" "$detail"
}
run_proot() { bash "$PUBLIC_ROOT/runtime.sh" "$@"; }
run_proot_clean() { env -u PYTHONPATH bash "$PUBLIC_ROOT/runtime.sh" "$@"; }
# Never wrap a shell function with `timeout`: wrap the real interpreter call.
run_proot_timed() { local t=$1; shift; timeout "$t" bash "$PUBLIC_ROOT/runtime.sh" "$@"; }
run_proot_clean_timed() { local t=$1; shift; timeout "$t" env -u PYTHONPATH bash "$PUBLIC_ROOT/runtime.sh" "$@"; }
DEADLINE=$(( SECONDS + 3300 ))
time_left() { echo $(( DEADLINE - SECONDS )); }

echo "=== whole-document PDF parse ==="
echo "job=$JOB host=$(hostname) date=$(date -Is)"
echo "pdf_name=$PDF_NAME pdf_dir=$PDF_DIR task_dir=$HERE"
ls -la "$HERE" | sed 's/^/  /'

unset CUDA_VISIBLE_DEVICES
echo; echo "--- gpu before ---"
nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv 2>&1 || true

# ------------------------------------------------------- 1. runtime + project layer
echo; echo "===== 1. runtime and project layer ====="
set +u
# shellcheck disable=SC1090
source "$PUBLIC_ROOT/activate.sh"
ACTIVATE_RC=$?
set -u
if [ "$ACTIVATE_RC" -eq 0 ] && [ -n "${QWEN_RUN_DIR:-}" ]; then
    record PASS proot_runtime "$QWEN_RUN_DIR"
else
    record FAIL proot_runtime "activate.sh rc=$ACTIVATE_RC"
fi

DEPS_STARTED=$(date +%s)
BOOT_RC=1
if boot_stdout=$(bash "$HERE/_staged/bootstrap.sh" "$HERE/_staged/requirements.txt"); then
    eval "$boot_stdout"
    BOOT_RC=0
fi
DEPS_SECONDS=$(( $(date +%s) - DEPS_STARTED ))
if [ "$BOOT_RC" -eq 0 ]; then
    record PASS bootstrap "mode=$(cat "$VT_DEPS_DIR/.ready" 2>/dev/null || echo unknown) seconds=$DEPS_SECONDS imports=$(tr '\n' ' ' < "$VT_DEPS_DIR/.imports.txt" 2>/dev/null)"
else
    record FAIL bootstrap "install failed"
fi

export PADDLE_PDX_CACHE_HOME="$HOME/models/paddlex"
export PADDLE_PDX_CPU_NUM_THREADS="${PADDLE_PDX_CPU_NUM_THREADS:-8}"
export PADDLE_PDX_MODEL_SOURCE="${PADDLE_PDX_MODEL_SOURCE:-huggingface}"
export PADDLE_PDX_HUGGING_FACE_ENDPOINT="${PADDLE_PDX_HUGGING_FACE_ENDPOINT:-https://hf-mirror.com}"
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK="${PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK:-True}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

# ------------------------------------------------------- 2. model weights
echo; echo "===== 2. model weights ====="
mkdir -p "$HOME/models"
OCR_MODEL_DIR=""
OCR_MODEL_NAME=""
for candidate in PaddleOCR-VL-1.6 PaddleOCR-VL; do
    if [ -f "$HOME/models/$candidate/config.json" ] && \
       ls "$HOME/models/$candidate"/*.safetensors >/dev/null 2>&1; then
        OCR_MODEL_DIR="$HOME/models/$candidate"
        OCR_MODEL_NAME="$candidate"
        break
    fi
done
LAYOUT_MODEL_DIR=""
for candidate in "$HOME/models/paddlex/official_models/PP-DocLayoutV2" "$HOME/models/PP-DocLayoutV2"; do
    if [ -f "$candidate/inference.pdiparams" ]; then LAYOUT_MODEL_DIR="$candidate"; break; fi
done
if [ -n "$OCR_MODEL_DIR" ]; then
    record PASS model_weights "rec=$OCR_MODEL_NAME $(du -sh "$OCR_MODEL_DIR" 2>/dev/null | cut -f1) layout=${LAYOUT_MODEL_DIR:-<paddlex-cache-autodownload>}"
else
    record FAIL model_weights "no complete PaddleOCR-VL checkpoint under \$HOME/models"
fi

# ------------------------------------------------------- 3. input pdf
echo; echo "===== 3. input pdf and page enumeration ====="
SRC_PDF="$PDF_DIR/$PDF_NAME"
INPUT_PDF="$OUT/input/$PDF_NAME"
if [ -f "$SRC_PDF" ]; then
    cp "$SRC_PDF" "$INPUT_PDF"
    PDF_SHA=$(sha256sum "$INPUT_PDF" | cut -d' ' -f1)
    record PASS input_pdf "$PDF_NAME sha256=${PDF_SHA:0:16} bytes=$(stat -c %s "$INPUT_PDF")"
else
    PDF_SHA=""
    record FAIL input_pdf "missing $SRC_PDF"
fi

PAGE_COUNT=0
ENUM_RC=1
if [ -n "${VT_PYTHON:-}" ] && [ -f "$INPUT_PDF" ]; then
    ENUM_ARGS=(--pdf "$INPUT_PDF" --out "$OUT/doc-pages.json")
    if [ -n "$REQ_PAGES" ]; then ENUM_ARGS+=(--pages "$REQ_PAGES"); fi
    run_proot_timed 300 "$VT_PYTHON" "$HERE/_staged/enumerate_pages.py" "${ENUM_ARGS[@]}"
    ENUM_RC=$?
fi
if [ "$ENUM_RC" -eq 0 ] && [ -s "$OUT/doc-pages.json" ]; then
    PAGE_COUNT=$(grep -c '"page_no"' "$OUT/doc-pages.json")
    record PASS enumerate_pages "pages=$PAGE_COUNT"
else
    record FAIL enumerate_pages "rc=$ENUM_RC"
fi

# ------------------------------------------------------- 4. render all pages
echo; echo "===== 4. render every page ====="
RENDER_RC=1
RENDERED_PAGES=0
if [ "$PAGE_COUNT" -gt 0 ] && [ -n "${VT_PYTHON:-}" ]; then
    RENDER_TIMEOUT=$(( $(time_left) - 1800 ))
    [ "$RENDER_TIMEOUT" -gt 900 ] && RENDER_TIMEOUT=900
    [ "$RENDER_TIMEOUT" -lt 120 ] && RENDER_TIMEOUT=120
    run_proot_timed "$RENDER_TIMEOUT" "$VT_PYTHON" "$HERE/_staged/render_pages.py" \
        --pages "$OUT/doc-pages.json" \
        --pdf-root "$OUT/input" \
        --out-dir "$OUT" \
        --dpi 200
    RENDER_RC=$?
fi
if [ -s "$OUT/render-manifest.json" ]; then
    RENDERED_PAGES=$(grep -c '"status": "ok"' "$OUT/render-manifest.json" 2>/dev/null)
    RENDERED_PAGES=${RENDERED_PAGES:-0}
fi
if [ "$RENDER_RC" -eq 0 ] && [ "$RENDERED_PAGES" -eq "$PAGE_COUNT" ] && [ "$PAGE_COUNT" -gt 0 ]; then
    record PASS render_pages "pages_ok=$RENDERED_PAGES/$PAGE_COUNT at 200 DPI"
else
    record FAIL render_pages "rc=$RENDER_RC pages_ok=$RENDERED_PAGES/$PAGE_COUNT"
fi

PROBE_IMAGE=""
if ls "$OUT/pages"/*.png >/dev/null 2>&1; then
    PROBE_IMAGE=$(ls "$OUT/pages"/*.png | head -1)
fi
echo "probe image: ${PROBE_IMAGE:-<none>}"

# ------------------------------------------------------- 5. vLLM server
echo; echo "===== 5. vLLM server ====="
VLLM_BIN="$PUBLIC_ROOT/vllm-env/bin/vllm"
VLLM_MODEL="${OCR_MODEL_DIR:-$HOME/models/PaddleOCR-VL-1.6}"
VLLM_LOG="$OUT/logs/vllm-${JOB}.log"
STARTUP_SECONDS=0

wait_for_vllm() {
    local pid=$1 timeout_s=$2
    local started=$(date +%s)
    while true; do
        if curl -sf -m 2 "http://127.0.0.1:${VLLM_PORT}/health" >/dev/null 2>&1; then
            STARTUP_SECONDS=$(( $(date +%s) - started ))
            return 0
        fi
        if ! kill -0 "$pid" 2>/dev/null; then
            STARTUP_SECONDS=$(( $(date +%s) - started ))
            return 1
        fi
        if [ $(( $(date +%s) - started )) -ge "$timeout_s" ]; then
            STARTUP_SECONDS=$(( $(date +%s) - started ))
            return 1
        fi
        sleep 3
    done
}

stop_vllm() {
    local pid=$1
    kill "$pid" 2>/dev/null || true
    pkill -f "vllm serve" 2>/dev/null || true
    pkill -f "EngineCore" 2>/dev/null || true
    sleep 2
}

start_vllm_attempt() {
    local label=$1 budget=$2
    shift 2
    echo "[vllm] attempt $label (budget ${budget}s): vllm serve $VLLM_MODEL $*"
    run_proot_clean "$VLLM_BIN" serve "$VLLM_MODEL" "$@" > "$VLLM_LOG" 2>&1 &
    VLLM_PID=$!
    if wait_for_vllm "$VLLM_PID" "$budget"; then
        echo "[vllm] ready after ${STARTUP_SECONDS}s (pid $VLLM_PID)"
        return 0
    fi
    echo "[vllm] attempt $label failed after ${STARTUP_SECONDS}s; last log lines:"
    tail -40 "$VLLM_LOG" | sed 's/^/  /'
    stop_vllm "$VLLM_PID"
    return 1
}

VLLM_OK=0
if [ "$RENDERED_PAGES" -eq 0 ] || [ -z "$OCR_MODEL_DIR" ]; then
    echo "[vllm] skipping GPU stages: render or weights unavailable"
elif [ -f "$VLLM_MODEL/config.json" ]; then
    FULL_ARGS=(
        --trust-remote-code
        --served-model-name "$SERVED_NAME"
        --host 127.0.0.1 --port "$VLLM_PORT"
        --dtype bfloat16
        --gpu-memory-utilization 0.85
        --max-model-len 32768
        --max-num-seqs 8
        --limit-mm-per-prompt '{"image": 1}'
        --max-num-batched-tokens 16384
        --no-enable-prefix-caching
        --mm-processor-cache-gb 0
    )
    FIRST_BUDGET=$(time_left)
    FIRST_BUDGET=$(( FIRST_BUDGET - 2100 ))
    [ "$FIRST_BUDGET" -gt 600 ] && FIRST_BUDGET=600
    [ "$FIRST_BUDGET" -lt 300 ] && FIRST_BUDGET=300
    if start_vllm_attempt full "$FIRST_BUDGET" "${FULL_ARGS[@]}"; then
        VLLM_OK=1
    else
        echo "[vllm] retrying with the minimal, eager-mode argument set"
        SECOND_BUDGET=$(time_left)
        SECOND_BUDGET=$(( SECOND_BUDGET - 1500 ))
        [ "$SECOND_BUDGET" -gt 480 ] && SECOND_BUDGET=480
        [ "$SECOND_BUDGET" -lt 240 ] && SECOND_BUDGET=240
        MINIMAL_ARGS=(
            --trust-remote-code
            --served-model-name "$SERVED_NAME"
            --host 127.0.0.1 --port "$VLLM_PORT"
            --gpu-memory-utilization 0.85
            --enforce-eager
        )
        if start_vllm_attempt minimal "$SECOND_BUDGET" "${MINIMAL_ARGS[@]}"; then
            VLLM_OK=1
        fi
    fi
else
    echo "[vllm] model dir missing: $VLLM_MODEL"
fi
if [ "$VLLM_OK" -eq 1 ]; then
    record PASS vllm_serve "startup_seconds=$STARTUP_SECONDS served=$SERVED_NAME"
    curl -s "http://127.0.0.1:${VLLM_PORT}/v1/models" > "$OUT/logs/models-${JOB}.json" 2>/dev/null || true
else
    record FAIL vllm_serve "startup_seconds=$STARTUP_SECONDS"
fi
if [ "$VLLM_OK" -eq 1 ]; then
    nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits -l 2 > "$VRAM_CSV" 2>&1 &
    VRAM_PID=$!
else
    VRAM_PID=""
fi

# ------------------------------------------------------- 6. recognition probe
echo; echo "===== 6. recognition-only probe ====="
if [ "$VLLM_OK" -eq 1 ] && [ -n "$PROBE_IMAGE" ]; then
    run_proot_clean_timed 300 "$PUBLIC_ROOT/vllm-env/bin/python" "$HERE/_staged/recognition_probe.py" \
        --image "$PROBE_IMAGE" \
        --server-url "http://127.0.0.1:${VLLM_PORT}/v1" \
        --model "$SERVED_NAME" \
        --out "$OUT/probe-${JOB}.json"
    if [ $? -eq 0 ]; then record PASS recognition_probe "first page via OpenAI endpoint"; else record FAIL recognition_probe "request failed"; fi
else
    echo "skipping recognition probe"
    record FAIL recognition_probe "server or page image unavailable"
fi

# ------------------------------------------------------- 7. full document parse
echo; echo "===== 7. parse every page ====="
CLIENT_RC=1
JSONL_LINES=0
RECORDED_OK=0
if [ "$VLLM_OK" -eq 1 ] && [ "$RENDERED_PAGES" -gt 0 ]; then
    CLIENT_TIMEOUT=$(( $(time_left) - 120 ))
    [ "$CLIENT_TIMEOUT" -gt 1800 ] && CLIENT_TIMEOUT=1800
    [ "$CLIENT_TIMEOUT" -lt 180 ] && CLIENT_TIMEOUT=180
    run_proot_timed "$CLIENT_TIMEOUT" "$VT_PYTHON" "$HERE/_staged/ocr_pages.py" \
        --manifest "$OUT/render-manifest.json" \
        --server-url "http://127.0.0.1:${VLLM_PORT}/v1" \
        --api-model-name "$SERVED_NAME" \
        --layout-model-dir "$LAYOUT_MODEL_DIR" \
        --pipeline-version v1.6 \
        --device cpu \
        --max-concurrency 8 \
        --out-jsonl "$OUT/pages-${JOB}.jsonl" \
        --out-summary "$OUT/records-${JOB}.json" \
        --out-dir "$OUT"
    CLIENT_RC=$?
fi
if [ -f "$OUT/pages-${JOB}.jsonl" ]; then
    JSONL_LINES=$(wc -l < "$OUT/pages-${JOB}.jsonl" | tr -d ' ')
fi
if [ -f "$OUT/records-${JOB}.json" ] && [ -n "${VT_PYTHON:-}" ]; then
    RECORDED_OK=$(run_proot "$VT_PYTHON" -c \
        "import json;d=json.load(open('$OUT/records-${JOB}.json'));print(d.get('pages_ok',0))" 2>/dev/null || echo 0)
fi
if [ "$CLIENT_RC" -eq 0 ] && [ "$JSONL_LINES" -eq "$PAGE_COUNT" ] && [ "$RECORDED_OK" -eq "$PAGE_COUNT" ]; then
    cp "$OUT/pages-${JOB}.jsonl" "$OUT/pages.jsonl"
    cp "$OUT/records-${JOB}.json" "$OUT/records.json" 2>/dev/null || true
    record PASS pdf_parse "pages_ok=$RECORDED_OK/$PAGE_COUNT blocks=$(run_proot "$VT_PYTHON" -c "import json;print(json.load(open('$OUT/records-${JOB}.json'))['blocks_total'])" 2>/dev/null || echo 0)"
else
    record FAIL pdf_parse "rc=$CLIENT_RC jsonl_lines=$JSONL_LINES pages_ok=$RECORDED_OK/$PAGE_COUNT"
fi

# ------------------------------------------------------- 8. assemble document markdown
echo; echo "===== 8. assemble document markdown ====="
DOC_MD="$OUT/document/${DOC_ID}-ocr.md"
ASSEMBLE_RC=1
if [ -f "$OUT/pages-${JOB}.jsonl" ] && [ "$JSONL_LINES" -gt 0 ]; then
    run_proot "$VT_PYTHON" "$HERE/_staged/assemble_document.py" \
        --jsonl "$OUT/pages-${JOB}.jsonl" \
        --out "$DOC_MD" \
        --doc-id "$DOC_ID" \
        --pdf "$PDF_NAME" \
        --pdf-sha256 "$PDF_SHA"
    ASSEMBLE_RC=$?
fi
PAGE_MARKERS=0
if [ -f "$DOC_MD" ]; then
    PAGE_MARKERS=$(grep -c '<!-- page:' "$DOC_MD" 2>/dev/null || true)
    PAGE_MARKERS=${PAGE_MARKERS:-0}
fi
if [ "$ASSEMBLE_RC" -eq 0 ] && [ "$PAGE_MARKERS" -eq "$PAGE_COUNT" ] && [ "$PAGE_COUNT" -gt 0 ]; then
    record PASS document_markdown "pages=$PAGE_MARKERS chars=$(wc -c < "$DOC_MD" | tr -d ' ') file=$DOC_MD"
else
    record FAIL document_markdown "rc=$ASSEMBLE_RC markers=$PAGE_MARKERS/$PAGE_COUNT"
fi

# ------------------------------------------------------- 9. teardown + summary
echo; echo "===== 9. teardown ====="
if [ -n "${VRAM_PID:-}" ]; then kill "$VRAM_PID" 2>/dev/null || true; fi
if [ -n "${VLLM_PID:-}" ]; then stop_vllm "$VLLM_PID"; fi
sleep 2
echo "--- gpu after ---"
nvidia-smi --query-gpu=index,memory.used --format=csv 2>&1 || true

VRAM_PEAK=""
if [ -f "$VRAM_CSV" ]; then
    VRAM_PEAK=$(awk -F, '{gsub(/ /, ""); if ($1 + 0 > peak) peak = $1 + 0} END {print peak + 0}' "$VRAM_CSV")
fi

MEDIAN_PAGE=""
TOTAL_BLOCKS=""
TOTAL_CHARS=""
if [ -f "$OUT/records-${JOB}.json" ] && [ -n "${VT_PYTHON:-}" ]; then
    MEDIAN_PAGE=$(run_proot "$VT_PYTHON" -c "import json;print(json.load(open('$OUT/records-${JOB}.json'))['page_seconds']['median'])" 2>/dev/null || echo "")
    TOTAL_BLOCKS=$(run_proot "$VT_PYTHON" -c "import json;print(json.load(open('$OUT/records-${JOB}.json'))['blocks_total'])" 2>/dev/null || echo "")
    TOTAL_CHARS=$(run_proot "$VT_PYTHON" -c "import json;print(sum(len(r.get('text','')) for r in map(json.loads, open('$OUT/pages-${JOB}.jsonl'))))" 2>/dev/null || echo "")
fi

echo; echo "===== 10. summary ====="
NOW=$(date -Is)
cat > "$OUT/summary-${JOB}.json" <<EOF
{
  "schema": "vt-pdf-parse/1",
  "job_id": "${JOB}",
  "host": "$(hostname)",
  "generated_at": "${NOW}",
  "pdf_name": "${PDF_NAME}",
  "pdf_sha256": "${PDF_SHA:-}",
  "requested_pages": "${REQ_PAGES:-all}",
  "pages": ${PAGE_COUNT},
  "pages_ok": "${RECORDED_OK}",
  "blocks_total": "${TOTAL_BLOCKS}",
  "chars_total": "${TOTAL_CHARS}",
  "median_page_seconds": "${MEDIAN_PAGE}",
  "bootstrap_seconds": ${DEPS_SECONDS},
  "vllm_startup_seconds": ${STARTUP_SECONDS},
  "vram_peak_mib": "${VRAM_PEAK}",
  "elapsed_seconds": ${SECONDS},
  "document_markdown": "document/${DOC_ID}-ocr.md",
  "pages_jsonl": "pages.jsonl",
  "pass": ${PASS},
  "fail": ${FAIL},
  "log": "pdf-parse-${JOB}.log"
}
EOF
cp "$OUT/summary-${JOB}.json" "$OUT/summary.json"
cat "$RESULTS"
echo
echo "pass=$PASS fail=$FAIL"
echo "summary: $OUT/summary-${JOB}.json"
echo "=== whole-document PDF parse done $(date -Is) ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
