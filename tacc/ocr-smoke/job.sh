#!/usr/bin/env bash
# TACC OCR smoke job (1 GPU).
#
# One job: bootstrap the cached project layer, ensure the OCR weights are in
# $HOME/models, render 10 selected course pages at 200 DPI, serve
# PaddleOCR-VL-1.6 with vLLM on one RTX 3090, run PP-DocLayoutV2 layout on CPU
# plus recognition on the server for every page, and write page JSONL records.
#
# Exit criterion: all 10 pages produce records, block boxes validate, and the
# measured startup plus per-page time leaves room for 342 pages inside one hour.
set -u
export PS1="${PS1:-}"

HERE="${TACC_WORKDIR:-$(cd "$(dirname "$0")" && pwd)}"
OUT="${TACC_USERDIR:-$HOME}/ocr-smoke"
PDF_DIR="${TACC_USERDIR:-$HOME}/corpus-pdf"
PUBLIC_ROOT="${PUBLIC_ROOT:-/mnt/home/public/course-envs/CSIT6000V/project/qwen3.8-27b-v1}"
JOB="${SLURM_JOB_ID:-manual}"
VLLM_PORT="${VLLM_PORT:-8000}"
SERVED_NAME="${SERVED_NAME:-PaddleOCR-VL-1.6-0.9B}"
VRAM_CSV="$OUT/logs/vram-${JOB}.csv"

mkdir -p "$OUT" "$OUT/logs" "$OUT/records" "$OUT/pages" "$OUT/images"
# A resubmission must never inherit the previous job's canonical results.
rm -f "$OUT/summary.json" "$OUT/pages.jsonl" "$OUT/records.json"
LOG="$OUT/ocr-smoke-${JOB}.log"
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
# The vLLM server and the public-environment probe must not see the project
# dependency target on PYTHONPATH: its numpy/OpenCV/protobuf builds would shadow
# the public environment and can break engine initialisation.
run_proot_clean() { env -u PYTHONPATH bash "$PUBLIC_ROOT/runtime.sh" "$@"; }
# Keep every stage inside the one-hour slot with a margin for teardown/summary.
DEADLINE=$(( SECONDS + 3300 ))
time_left() { echo $(( DEADLINE - SECONDS )); }

echo "=== OCR smoke ==="
echo "job=$JOB host=$(hostname) date=$(date -Is)"
echo "task_dir=$HERE userdir=${TACC_USERDIR:-<unset>}"
ls -la "$HERE" | sed 's/^/  /'

# Platform quirk measured on 2026-10-27: the tacc container exports a host-global
# CUDA index that does not map to the container's devices.
unset CUDA_VISIBLE_DEVICES
echo
echo "--- gpu before ---"
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

# PaddleX resolves local model dirs only; keep any residual download on the mirror
# and skip the model-hoster connectivity probe.
export PADDLE_PDX_CACHE_HOME="$HOME/models/paddlex"
export PADDLE_PDX_CPU_NUM_THREADS="${PADDLE_PDX_CPU_NUM_THREADS:-8}"
export PADDLE_PDX_MODEL_SOURCE="${PADDLE_PDX_MODEL_SOURCE:-huggingface}"
export PADDLE_PDX_HUGGING_FACE_ENDPOINT="${PADDLE_PDX_HUGGING_FACE_ENDPOINT:-https://hf-mirror.com}"
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK="${PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK:-True}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

# ------------------------------------------------------- 2. model weights
echo; echo "===== 2. model weights ====="
HF_BIN="$PUBLIC_ROOT/vllm-env/bin/hf"
mkdir -p "$HOME/models"
download_model() {
    local repo=$1 dir=$2 marker=$3 attempt started rc
    if [ -f "$HOME/models/$dir/$marker" ]; then
        echo "[models] already present: $dir ($(du -sh "$HOME/models/$dir" 2>/dev/null | cut -f1))"
        return 0
    fi
    for attempt in 1 2; do
        started=$(date +%s)
        timeout 900 env -u PYTHONPATH bash "$PUBLIC_ROOT/runtime.sh" "$HF_BIN" download "$repo" \
            --local-dir "$HOME/models/$dir" --max-workers 4
        rc=$?
        echo "[models] $repo attempt $attempt rc=$rc seconds=$(( $(date +%s) - started )) size=$(du -sh "$HOME/models/$dir" 2>/dev/null | cut -f1)"
        if [ "$rc" -eq 0 ] && [ -f "$HOME/models/$dir/$marker" ]; then
            return 0
        fi
        sleep 5
    done
    return 1
}
MODELS_OK=1
download_model "PaddlePaddle/PaddleOCR-VL-1.6" "PaddleOCR-VL-1.6" "model.safetensors" || MODELS_OK=0
# The HF mirror download in PRoot hit TLS verification failures and stalls; the
# environment spike proved PaddleX fetches PP-DocLayoutV2 reliably from
# modelscope into PADDLE_PDX_CACHE_HOME. Prefer that copy, and let the client
# auto-download into the same cache if it is absent.
LAYOUT_MODEL_DIR=""
for candidate in "$HOME/models/paddlex/official_models/PP-DocLayoutV2" "$HOME/models/PP-DocLayoutV2"; do
    if [ -f "$candidate/inference.pdiparams" ]; then LAYOUT_MODEL_DIR="$candidate"; break; fi
done
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
if [ "$MODELS_OK" -eq 1 ] && [ -n "$OCR_MODEL_DIR" ]; then
    record PASS model_weights "rec=$OCR_MODEL_NAME $(du -sh "$OCR_MODEL_DIR" 2>/dev/null | cut -f1) layout=${LAYOUT_MODEL_DIR:-<paddlex-cache-autodownload>}"
else
    record FAIL model_weights "OCR weights incomplete (rec_dir=${OCR_MODEL_DIR:-missing})"
fi

# ------------------------------------------------------- 3. render selected pages
echo; echo "===== 3. render selected pages ====="
PREFLIGHT_OK=1
MISSING_PDFS=""
for pdf in Tutorial_5.pdf Tutorial_4.pdf Tutorial_3.pdf ACS_Lecture_1_2026F.pdf \
           ACS_lecture_2_2026F.pdf course_project.pdf Tutorial_1.pdf Tutorial_2.pdf \
           Assignment_1_final.pdf; do
    if [ ! -f "$PDF_DIR/$pdf" ]; then MISSING_PDFS="$MISSING_PDFS $pdf"; PREFLIGHT_OK=0; fi
done
if [ "$PREFLIGHT_OK" -eq 1 ]; then
    record PASS preflight_pdfs "9 staged PDFs present in $PDF_DIR"
else
    echo "[render] missing PDFs:$MISSING_PDFS"
    record FAIL preflight_pdfs "missing:$MISSING_PDFS"
fi
RENDER_RC=1
if [ "$PREFLIGHT_OK" -eq 1 ] && [ -n "${VT_PYTHON:-}" ]; then
    RENDER_TIMEOUT=$(( $(time_left) - 1500 ))
    [ "$RENDER_TIMEOUT" -gt 300 ] && RENDER_TIMEOUT=300
    timeout "$RENDER_TIMEOUT" bash "$PUBLIC_ROOT/runtime.sh" "$VT_PYTHON" "$HERE/_staged/render_pages.py" \
        --pages "$HERE/selected-pages.json" \
        --pdf-root "$PDF_DIR" \
        --out-dir "$OUT" \
        --dpi 200
    RENDER_RC=$?
fi
RENDERED_PAGES=0
if [ -s "$OUT/render-manifest.json" ]; then
    RENDERED_PAGES=$(grep -c '"status": "ok"' "$OUT/render-manifest.json" 2>/dev/null)
    RENDERED_PAGES=${RENDERED_PAGES:-0}
fi
if [ "$RENDER_RC" -eq 0 ] && [ "$RENDERED_PAGES" -ge 1 ] && [ -s "$OUT/render-manifest.json" ]; then
    record PASS render_pages "pages_ok=$RENDERED_PAGES at 200 DPI"
else
    record FAIL render_pages "rc=$RENDER_RC pages_ok=$RENDERED_PAGES"
fi

# Prefer a freshly rendered page; fall back to the page rendered by the
# environment spike job (a real course page too).
FALLBACK_IMAGE="${TACC_USERDIR:-$HOME}/env-spike/rendered/sample-p001.png"
PROBE_IMAGE=""
if ls "$OUT/pages"/*.png >/dev/null 2>&1; then
    PROBE_IMAGE=$(ls "$OUT/pages"/*.png | head -1)
elif [ -f "$FALLBACK_IMAGE" ]; then
    PROBE_IMAGE="$FALLBACK_IMAGE"
fi
echo "probe image: ${PROBE_IMAGE:-<none>}"

# ------------------------------------------------------- 4. serve with vLLM
echo; echo "===== 4. vLLM server ====="
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
    pkill -f "VLLM::EngineCore" 2>/dev/null || true
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
if [ "$PREFLIGHT_OK" -ne 1 ]; then
    echo "[vllm] skipping GPU stages: PDF preflight failed"
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
    # The 27855 run proved vLLM needs roughly 3 minutes to load this model and
    # capture graphs; the first attempt was killed after only 120 s.
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
    echo "--- models ---"; cat "$OUT/logs/models-${JOB}.json" 2>/dev/null | head -20
    echo "--- gpu during serve ---"
    nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv 2>&1 || true
else
    record FAIL vllm_serve "startup_seconds=$STARTUP_SECONDS"
fi

if [ "$VLLM_OK" -eq 1 ]; then
    nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits -l 2 > "$VRAM_CSV" 2>&1 &
    VRAM_PID=$!
else
    VRAM_PID=""
fi

# ------------------------------------------------------- 5. recognition probe
echo; echo "===== 5. recognition-only probe ====="
if [ "$VLLM_OK" -eq 1 ] && [ -n "$PROBE_IMAGE" ]; then
    timeout 300 env -u PYTHONPATH bash "$PUBLIC_ROOT/runtime.sh" "$PUBLIC_ROOT/vllm-env/bin/python" "$HERE/_staged/recognition_probe.py" \
        --image "$PROBE_IMAGE" \
        --server-url "http://127.0.0.1:${VLLM_PORT}/v1" \
        --model "$SERVED_NAME" \
        --out "$OUT/probe-${JOB}.json"
    if [ $? -eq 0 ]; then record PASS recognition_probe "one page via OpenAI endpoint"; else record FAIL recognition_probe "request failed"; fi
else
    echo "skipping recognition probe"
    record FAIL recognition_probe "server or image unavailable"
fi

# ------------------------------------------------------- 6. full OCR pipeline
echo; echo "===== 6. layout + recognition on 10 pages ====="
CLIENT_RC=1
CLIENT_TIMEOUT=$(( $(time_left) - 120 ))
[ "$CLIENT_TIMEOUT" -gt 1800 ] && CLIENT_TIMEOUT=1800
[ "$CLIENT_TIMEOUT" -lt 180 ] && CLIENT_TIMEOUT=180
if [ "$VLLM_OK" -eq 1 ] && [ "$RENDERED_PAGES" -ge 1 ] && [ -s "$OUT/render-manifest.json" ]; then
    timeout "$CLIENT_TIMEOUT" bash "$PUBLIC_ROOT/runtime.sh" "$VT_PYTHON" "$HERE/_staged/ocr_pages.py" \
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
JSONL_LINES=0
RECORDED_OK=0
if [ -f "$OUT/pages-${JOB}.jsonl" ]; then
    JSONL_LINES=$(wc -l < "$OUT/pages-${JOB}.jsonl" | tr -d ' ')
fi
if [ -f "$OUT/records-${JOB}.json" ] && [ -n "${VT_PYTHON:-}" ]; then
    RECORDED_OK=$(bash "$PUBLIC_ROOT/runtime.sh" "$VT_PYTHON" -c \
        "import json;d=json.load(open('$OUT/records-${JOB}.json'));print(d.get('pages_ok',0))" 2>/dev/null || echo 0)
fi
if [ "$CLIENT_RC" -eq 0 ] && [ "$JSONL_LINES" -ge 10 ] && [ "$RECORDED_OK" -eq "$JSONL_LINES" ]; then
    cp "$OUT/pages-${JOB}.jsonl" "$OUT/pages.jsonl"
    cp "$OUT/records-${JOB}.json" "$OUT/records.json" 2>/dev/null || true
    record PASS ocr_pipeline "pages_ok=$RECORDED_OK/$JSONL_LINES, jsonl written"
else
    record FAIL ocr_pipeline "rc=$CLIENT_RC jsonl_lines=$JSONL_LINES pages_ok=$RECORDED_OK"
fi

# ------------------------------------------------------- 7. teardown
echo; echo "===== 7. teardown ====="
if [ -n "${VRAM_PID:-}" ]; then kill "$VRAM_PID" 2>/dev/null || true; fi
if [ -n "${VLLM_PID:-}" ]; then stop_vllm "$VLLM_PID"; fi
sleep 2
echo "--- gpu after ---"
nvidia-smi --query-gpu=index,memory.used --format=csv 2>&1 || true

VRAM_PEAK=""
if [ -f "$VRAM_CSV" ]; then
    VRAM_PEAK=$(awk -F, '{gsub(/ /, ""); if ($1 + 0 > peak) peak = $1 + 0} END {print peak + 0}' "$VRAM_CSV")
    echo "vram peak: ${VRAM_PEAK} MiB"
fi

# ------------------------------------------------------- 8. budget extrapolation
PROJECTED=""
MEDIAN_PAGE=""
TOTAL_BLOCKS=""
PAGES_OK=""
FIT="unknown"
if [ -f "$OUT/records-${JOB}.json" ] && [ -f "$OUT/render-manifest.json" ] && [ -n "${VT_PYTHON:-}" ] \
   && [ "${RECORDED_OK:-0}" -eq "${JSONL_LINES:-0}" ] && [ "${JSONL_LINES:-0}" -ge 10 ]; then
    PROJ_LINE=$(bash "$PUBLIC_ROOT/runtime.sh" "$VT_PYTHON" "$HERE/projection.py" \
        --records "$OUT/records-${JOB}.json" \
        --manifest "$OUT/render-manifest.json" \
        --startup-seconds "$STARTUP_SECONDS" \
        --overhead-seconds "$DEPS_SECONDS" \
        --out "$OUT/projection-${JOB}.json" 2>/dev/null)
    echo "$PROJ_LINE"
    MEDIAN_PAGE=$(printf '%s\n' "$PROJ_LINE" | sed -n 's/.*median=\([^ ]*\).*/\1/p')
    PROJECTED=$(printf '%s\n' "$PROJ_LINE" | sed -n 's/.*projected=\([0-9]*\).*/\1/p')
    FIT=$(printf '%s\n' "$PROJ_LINE" | sed -n 's/.*fits=\([a-z]*\).*/\1/p')
    TOTAL_BLOCKS=$(printf '%s\n' "$PROJ_LINE" | sed -n 's/.*blocks=\([0-9]*\).*/\1/p')
    PAGES_OK=$(bash "$PUBLIC_ROOT/runtime.sh" "$VT_PYTHON" -c "import json;print(json.load(open('$OUT/projection-${JOB}.json'))['pages_ok'])" 2>/dev/null || echo "")
fi
if [ -z "$PROJECTED" ]; then
    FIT="unknown"
    echo "projection skipped: incomplete run"
fi

# ------------------------------------------------------- 9. summary
echo; echo "===== 9. summary ====="
NOW=$(date -Is)
cat > "$OUT/summary-${JOB}.json" <<EOF
{
  "schema": "vt-ocr-smoke/1",
  "job_id": "${JOB}",
  "host": "$(hostname)",
  "generated_at": "${NOW}",
  "pass": ${PASS},
  "fail": ${FAIL},
  "bootstrap_seconds": ${DEPS_SECONDS},
  "vllm_startup_seconds": ${STARTUP_SECONDS},
  "served_model_name": "${SERVED_NAME}",
  "ocr_model_dir": "${OCR_MODEL_DIR:-}",
  "ocr_model_name": "${OCR_MODEL_NAME:-}",
  "vram_peak_mib": "${VRAM_PEAK}",
  "pages_total": 10,
  "pages_rendered": ${RENDERED_PAGES:-0},
  "elapsed_seconds": ${SECONDS},
  "pages_ok": "${PAGES_OK}",
  "median_page_seconds": "${MEDIAN_PAGE}",
  "blocks_total": "${TOTAL_BLOCKS}",
  "projected_342p_seconds": "${PROJECTED}",
  "fits_one_hour": "${FIT}",
  "records_json": "records-${JOB}.json",
  "pages_jsonl": "pages.jsonl",
  "probe_json": "probe-${JOB}.json",
  "vllm_log": "logs/vllm-${JOB}.log",
  "log": "ocr-smoke-${JOB}.log"
}
EOF
cp "$OUT/summary-${JOB}.json" "$OUT/summary.json"
cat "$RESULTS"
echo
echo "pass=$PASS fail=$FAIL"
echo "summary: $OUT/summary-${JOB}.json"
echo "=== OCR smoke done $(date -Is) ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
