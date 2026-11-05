#!/usr/bin/env bash
# TACC batched OCR job (1 GPU, 59 minutes).
#
# One submitted job parses the documents of one corpus batch (Lectures,
# Tutorials, or Misc). It bootstraps the project layer, serves PaddleOCR-VL-1.6
# with vLLM inside the job, then runs the shared OCR stages per document through
# ocr_batch.py: enumerate, render at 200 DPI, PP-DocLayoutV2 layout on CPU plus
# recognition on the local OpenAI endpoint, and one document markdown. It caps
# the recognition stage at 1800 s and the whole body at 3300 s, records which
# documents finished, and writes everything to USERDIR for the local driver.
#
# Env knobs: PUBLIC_ROOT, VLLM_PORT, SERVED_NAME.
set -u
export PS1="${PS1:-}"

HERE="${TACC_WORKDIR:-$(cd "$(dirname "$0")" && pwd)}"
USERDIR="${TACC_USERDIR:-$HOME}"
JOB="${SLURM_JOB_ID:-manual}"
JOB_STARTED_EPOCH=$(date +%s)
VLLM_PORT="${VLLM_PORT:-8000}"
SERVED_NAME="${SERVED_NAME:-PaddleOCR-VL-1.6-0.9B}"
PUBLIC_ROOT="${PUBLIC_ROOT:-/mnt/home/public/course-envs/CSIT6000V/project/qwen3.8-27b-v1}"
REQUEST_FILE="$HERE/request.json"

if [ ! -f "$REQUEST_FILE" ]; then
    echo "[fatal] no request.json next to job.sh"
    exit 2
fi
REQ_OUT=$(sed -n 's/.*"out_dir"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REQUEST_FILE")
OUT="${REQ_OUT:-$USERDIR/ocr/manual-$JOB}"
mkdir -p "$OUT/logs"
LOG="$OUT/logs/ocr-${JOB}.log"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

# A later submit from the same account re-syncs TACC_WORKDIR; keep this job's
# own copy of its scripts so a running job never loses them.
JOBHOME="$OUT/jobhome-${JOB}"
mkdir -p "$JOBHOME"
cp -a "$HERE/." "$JOBHOME/" 2>/dev/null || true
HERE="$JOBHOME"
REQUEST_FILE="$HERE/request.json"

VLLM_PID=""
STARTUP_SECONDS=0

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    if [ -n "$VLLM_PID" ]; then kill "$VLLM_PID" 2>/dev/null || true; fi
    pkill -f "vllm serve" 2>/dev/null || true
    pkill -f "EngineCore" 2>/dev/null || true
    sleep 2
    echo "--- gpu after ---"
    nvidia-smi --query-gpu=index,memory.used --format=csv 2>&1 || true
    echo "=== vt-ocr job done date=$(date -Is) rc=$rc ==="
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

echo "=== vt-ocr batch job ==="
echo "job=$JOB host=$(hostname) date=$(date -Is)"
echo "task_dir=$HERE out=$OUT"
ls -la "$HERE" | sed 's/^/  /'

unset CUDA_VISIBLE_DEVICES
echo "--- gpu before ---"
nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv 2>&1 || true

# ------------------------------------------------------- 1. runtime + project layer
echo; echo "===== 1. runtime and project layer ====="
set +u
# shellcheck disable=SC1090
source "$PUBLIC_ROOT/activate.sh"
ACTIVATE_RC=$?
set -u
if [ "$ACTIVATE_RC" -ne 0 ] || [ -z "${QWEN_RUN_DIR:-}" ]; then
    echo "[fatal] public environment activation failed rc=$ACTIVATE_RC"
    exit 1
fi
echo "QWEN_RUN_DIR=$QWEN_RUN_DIR"

DEPS_STARTED=$(date +%s)
BOOT_RC=1
if boot_stdout=$(bash "$HERE/_staged/bootstrap.sh" "$HERE/_staged/requirements.txt"); then
    eval "$boot_stdout"
    BOOT_RC=0
fi
DEPS_SECONDS=$(( $(date +%s) - DEPS_STARTED ))
if [ "$BOOT_RC" -ne 0 ]; then
    echo "[fatal] project layer bootstrap failed after ${DEPS_SECONDS}s"
    exit 1
fi
echo "[bootstrap] mode=$(cat "$VT_DEPS_DIR/.ready" 2>/dev/null || echo unknown) seconds=$DEPS_SECONDS"

export PADDLE_PDX_CACHE_HOME="$HOME/models/paddlex"
export PADDLE_PDX_CPU_NUM_THREADS="${PADDLE_PDX_CPU_NUM_THREADS:-8}"
export PADDLE_PDX_MODEL_SOURCE="${PADDLE_PDX_MODEL_SOURCE:-huggingface}"
export PADDLE_PDX_HUGGING_FACE_ENDPOINT="${PADDLE_PDX_HUGGING_FACE_ENDPOINT:-https://hf-mirror.com}"
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK="${PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK:-True}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

# ------------------------------------------------------- 2. model weights
echo; echo "===== 2. model weights ====="
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
if [ -z "$OCR_MODEL_DIR" ]; then
    echo "[fatal] no complete PaddleOCR-VL checkpoint under \$HOME/models"
    exit 1
fi
echo "[weights] rec=$OCR_MODEL_NAME layout=${LAYOUT_MODEL_DIR:-<paddlex-cache-autodownload>}"

# ------------------------------------------------------- 3. vLLM server
echo; echo "===== 3. vLLM server ====="
VLLM_BIN="$PUBLIC_ROOT/vllm-env/bin/vllm"
VLLM_LOG="$OUT/logs/vllm-${JOB}.log"
VLLM_MODEL="$OCR_MODEL_DIR"

time_left() { echo $(( JOB_STARTED_EPOCH + 3300 - $(date +%s) )); }
# The vLLM server must not see the Paddle project-layer PYTHONPATH.
run_clean() { env -u PYTHONPATH bash "$PUBLIC_ROOT/runtime.sh" "$@"; }

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
    echo "[vllm] attempt $label (budget ${budget}s)"
    run_clean "$VLLM_BIN" serve "$VLLM_MODEL" "$@" > "$VLLM_LOG" 2>&1 &
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
FIRST_BUDGET=$(( $(time_left) - 2100 ))
[ "$FIRST_BUDGET" -gt 600 ] && FIRST_BUDGET=600
[ "$FIRST_BUDGET" -lt 300 ] && FIRST_BUDGET=300
VLLM_OK=0
if start_vllm_attempt full "$FIRST_BUDGET" "${FULL_ARGS[@]}"; then
    VLLM_OK=1
else
    echo "[vllm] retrying with the minimal, eager-mode argument set"
    SECOND_BUDGET=$(( $(time_left) - 1500 ))
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
if [ "$VLLM_OK" -ne 1 ]; then
    echo "[fatal] vLLM never became ready"
    exit 1
fi
curl -s "http://127.0.0.1:${VLLM_PORT}/v1/models" > "$OUT/logs/models-${JOB}.json" 2>/dev/null || true
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits -l 2 > "$OUT/logs/vram-${JOB}.csv" 2>&1 &
VRAM_PID=$!

# ------------------------------------------------------- 4. per-document stages
echo; echo "===== 4. per-document OCR ====="
WORKER_RC=1
qwen-python "$HERE/ocr_batch.py" \
    --request "$REQUEST_FILE" \
    --staged "$HERE/_staged" \
    --vt-python "$VT_PYTHON" \
    --server-url "http://127.0.0.1:${VLLM_PORT}/v1" \
    --served-name "$SERVED_NAME" \
    --layout-model-dir "$LAYOUT_MODEL_DIR" \
    --pipeline-version v1.6 \
    --device cpu \
    --max-concurrency 8 \
    --job-id "$JOB" \
    --job-started-epoch "$JOB_STARTED_EPOCH" \
    --vllm-startup-seconds "$STARTUP_SECONDS" \
    --launcher serve.sh \
    --userdir "$USERDIR"
WORKER_RC=$?
echo "[worker] exit=$WORKER_RC"

# ------------------------------------------------------- 5. teardown and archive
echo; echo "===== 5. teardown and archive ====="
if [ -n "${VRAM_PID:-}" ]; then kill "$VRAM_PID" 2>/dev/null || true; fi
if [ -n "$VLLM_PID" ]; then stop_vllm "$VLLM_PID"; fi

VRAM_PEAK=""
if [ -f "$OUT/logs/vram-${JOB}.csv" ]; then
    VRAM_PEAK=$(awk -F, '{gsub(/ /, ""); if ($1 + 0 > peak) peak = $1 + 0} END {print peak + 0}' "$OUT/logs/vram-${JOB}.csv")
fi
echo "vram_peak_mib=$VRAM_PEAK"
mkdir -p "$OUT/images" "$OUT/pages" "$OUT/document" "$OUT/logs"
tar -czf "$OUT/images.tar.gz" -C "$OUT" images
# One archive for everything else keeps the download to four calls; the local
# driver falls back to per-file downloads when it is missing.
tar -czf "$OUT/artifacts.tar.gz" -C "$OUT" pages document logs

echo "summary: $OUT/summary.json"
cat "$OUT/summary.json" 2>/dev/null | head -60 || true
exit "$WORKER_RC"
